"""
This module implements the Denon AVR receiver communication of the Remote Two integration driver.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import asyncio
import logging
import re
import time
from asyncio import AbstractEventLoop
from enum import IntEnum
from functools import wraps
from typing import TypeVar, ParamSpec, Callable, Awaitable, Coroutine, Any, Concatenate

import denonavr
from denonavr.exceptions import (
    AvrCommandError,
    AvrForbiddenError,
    AvrNetworkError,
    AvrTimoutError,
    DenonAvrError,
)

import discover
import ucapi
from config import AvrDevice
from pyee import AsyncIOEventEmitter

_LOG = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 5

BACKOFF_MAX = 30
MIN_RECONNECT_DELAY: float = 0.5
BACKOFF_FACTOR: float = 1.5


class Events(IntEnum):
    """Internal driver events."""

    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 2
    PAIRED = 3
    ERROR = 4
    UPDATE = 5
    IP_ADDRESS_CHANGED = 6


class States(IntEnum):
    """State of a connected AVR."""

    UNKNOWN = 0
    UNAVAILABLE = 1
    OFF = 2
    ON = 3
    PLAYING = 4
    PAUSED = 5


TELNET_EVENTS = {
    "HD",
    "MS",
    "MU",
    "MV",
    "NS",
    "NSE",
    "PS",
    "SI",
    "SS",
    "TF",
    "ZM",
    "Z2",
    "Z3",
}

_DenonDeviceT = TypeVar("_DenonDeviceT", bound="DenonDevice")
_R = TypeVar("_R")
_P = ParamSpec("_P")


# Adapted from Home Assistant `async_log_errors` in
# https://github.com/home-assistant/core/blob/fd1f0b0efeb5231d3ee23d1cb2a10cdeff7c23f1/homeassistant/components/denonavr/media_player.py
def async_handle_denonlib_errors(
    func: Callable[Concatenate[_DenonDeviceT, _P], Awaitable[_R]],
) -> Callable[Concatenate[_DenonDeviceT, _P], Coroutine[Any, Any, _R | ucapi.StatusCodes]]:
    """Log errors occurred when calling a Denon AVR receiver.

    Decorates methods of DenonDevice class.

    Taken from Home-Assistant
    """

    @wraps(func)
    async def wrapper(self: _DenonDeviceT, *args: _P.args, **kwargs: _P.kwargs) -> ucapi.StatusCodes:
        # pylint: disable=protected-access
        available = True
        result = ucapi.StatusCodes.SERVER_ERROR
        try:
            await func(self, *args, **kwargs)
            return ucapi.StatusCodes.OK
        except AvrTimoutError:
            available = False
            result = ucapi.StatusCodes.SERVICE_UNAVAILABLE
            if self.available:
                _LOG.warning(
                    "Timeout connecting to Denon AVR receiver at host %s. Device is unavailable",
                    self._receiver.host,
                )
                self._attr_available = False
        except AvrNetworkError:
            result = ucapi.StatusCodes.SERVER_ERROR
            available = False
            if self.available:
                _LOG.warning(
                    "Network error connecting to Denon AVR receiver at host %s. Device is unavailable",
                    self._receiver.host,
                )
                self._attr_available = False
        except AvrForbiddenError:
            available = False
            result = ucapi.StatusCodes.UNAUTHORIZED
            if self.available:
                _LOG.warning(
                    (
                        "Denon AVR receiver at host %s responded with HTTP 403 error. "
                        "Device is unavailable. Please consider power cycling your "
                        "receiver"
                    ),
                    self._receiver.host,
                )
                self._attr_available = False
        except AvrCommandError as err:
            available = False
            result = ucapi.StatusCodes.BAD_REQUEST
            _LOG.error(
                "Command %s failed with error: %s",
                func.__name__,
                err,
            )
        except DenonAvrError as err:
            available = False
            _LOG.exception(
                "Error %s occurred in method %s for Denon AVR receiver",
                err,
                func.__name__,
            )
        finally:
            if available and not self.available:
                _LOG.info(
                    "Denon AVR receiver at host %s is available again",
                    self._receiver.host,
                )
                self._attr_available = True
        return result

    return wrapper


class DenonDevice:
    """Representing a Denon AVR Device."""

    def __init__(
        self,
        device: AvrDevice,
        timeout: float = DEFAULT_TIMEOUT,
        loop: AbstractEventLoop | None = None,
    ):
        """Create instance with given IP or hostname of AVR."""
        self.events = AsyncIOEventEmitter(loop or asyncio.get_running_loop())
        self._zones: dict[str, str | None] = {}
        if device.zone2:
            self._zones["Zone2"] = None
        if device.zone3:
            self._zones["Zone3"] = None
        self._avr: denonavr.DenonAVR = denonavr.DenonAVR(
            host=device.address, show_all_inputs=device.show_all_inputs, timeout=timeout, add_zones=self._zones
        )
        self._use_telnet = device.use_telnet

        self._attr_available: bool = True

        self._connecting: bool = False
        self._connection_attempts: int = 0
        self._reconnect_delay: float = MIN_RECONNECT_DELAY

        self.name: str = device.name
        self.model: str | None = None
        self.manufacturer: str | None = None
        self.id: str = device.id
        self.ipaddress: str = device.address
        self._getting_data: bool = False

        self.state: States = States.UNKNOWN
        self._position: int = 0
        self._duration: int = 0

        _LOG.debug("Denon AVR created: %s", self.ipaddress)

    @property
    def available(self) -> bool:
        """Return True if device is available."""
        return self._attr_available

    # @property
    # def support_sound_mode(self) -> bool | None:
    #     """Return True if sound mode supported."""
    #     return self._avr.support_sound_mode
    #
    # @property
    # def media_image_url(self) -> str | None:
    #     """Image url of current playing media."""
    #     if self._avr.input_func in self._avr.playing_func_list:
    #         return self._avr.image_url
    #     return None
    #
    # @property
    # def media_title(self) -> str | None:
    #     """Title of current playing media."""
    #     if self._avr.input_func not in self._avr.playing_func_list:
    #         return self._avr.input_func
    #     if self._avr.title is not None:
    #         return self._avr.title
    #     return self._avr.frequency
    #
    # @property
    # def media_artist(self) -> str | None:
    #     """Artist of current playing media, music track only."""
    #     if self._avr.artist is not None:
    #         return self._avr.artist
    #     return self._avr.band
    #
    # @property
    # def media_album_name(self) -> str | None:
    #     """Album name of current playing media, music track only."""
    #     if self._avr.album is not None:
    #         return self._avr.album
    #     return self._avr.station

    @staticmethod
    def _map_range(value, from_min, from_max, to_min, to_max):
        return (value - from_min) * (to_max - to_min) / (from_max - from_min) + to_min

    # TODO is this correct? Doesn't volume go up to 18?
    def _convert_volume_to_percent(self, value):
        return self._map_range(value, -80.0, 0.0, 0, 100)

    @staticmethod
    def _extract_values(input_string):
        pattern = r"(\d+:\d+)\s+(\d+%)"
        matches = re.findall(pattern, input_string)

        if matches:
            return matches[0]

        return None

    async def connect(self, max_timeout: int | None = None) -> bool:
        """
        Connect to AVR.

        :param max_timeout: optional maximum timeout in seconds to try connecting to the device.
        """
        # TODO use asyncio.Lock?
        if self._connecting:
            _LOG.debug("Connection task already running for %s", self.id)
            return False

        if self._use_telnet and self._avr.telnet_connected:
            _LOG.debug("[%s] Already connected", self.id)
            _ = asyncio.ensure_future(self._get_data())
            return True

        self._connecting = True
        start = time.time()

        request_start = None
        success = False

        while not success:
            try:
                _LOG.debug("Connecting AVR %s on %s", self.id, self._avr.host)
                self.events.emit(Events.CONNECTING, self.id)
                request_start = time.time()
                await self._avr.async_setup()
                await self._avr.async_update()
                success = True
                self._connection_attempts = 0
                self._reconnect_delay = MIN_RECONNECT_DELAY
            except denonavr.exceptions.DenonAvrError as ex:
                if max_timeout and time.time() - start > max_timeout:
                    _LOG.error(
                        "Abort connecting after %ss: device '%s' not reachable on %s. %s",
                        max_timeout,
                        self.name,
                        self._avr.host,
                        ex,
                    )
                    self.state = States.UNAVAILABLE
                    self._connecting = False
                    return False

                await self._handle_connection_failure(time.time() - request_start, ex)

        self.manufacturer = self._avr.manufacturer
        self.model = self._avr.model_name
        self.name = self._avr.name
        if self.id != self._avr.serial_number:
            _LOG.warning("Different device serial number! Expected=%s, received=%s", self.id, self._avr.serial_number)

        _LOG.debug(
            "Denon AVR connected. Manufacturer=%s, Model=%s, Name=%s, Id=%s, State=%s",
            self.manufacturer,
            self.model,
            self.name,
            self.id,
            self._avr.state,
        )

        await self._subscribe_events()

        self.state = self._map_denonavr_state(self._avr.state)

        self._position = 0
        self._duration = 0

        self.events.emit(Events.CONNECTED, self.id)

        self._connecting = False
        return True

    async def _handle_connection_failure(self, connect_duration: float, ex):
        self._connection_attempts += 1
        # backoff delay must deduct time spent in the connection attempt
        backoff = self._backoff() - connect_duration
        if backoff <= 0:
            backoff = 0.1
        _LOG.error(
            "Cannot connect to '%s' on %s, trying again in %.1fs. %s",
            self.id if self.id else self.name,
            self._avr.host,
            backoff,
            ex,
        )

        # try resolving IP address from device name if we keep failing to connect, maybe the IP address changed
        if self._connection_attempts % 10 == 0:
            _LOG.debug("Start resolving IP address for '%s'...", self.name)
            discovered = await discover.denon_avrs()
            for item in discovered:
                if item["friendlyName"] == self.name:
                    if self._avr.host != item["host"]:
                        _LOG.info("IP address of '%s' changed: %s", self.name, item["host"])
                        self._avr._host = item["host"]  # pylint: disable=W0212 # seems to be the only way
                        self.events.emit(Events.IP_ADDRESS_CHANGED, self.id, self._avr.host)
        else:
            await asyncio.sleep(backoff)

    def _backoff(self) -> float:
        delay = self._reconnect_delay * BACKOFF_FACTOR
        if delay >= BACKOFF_MAX:
            self._reconnect_delay = BACKOFF_MAX
        else:
            self._reconnect_delay = delay
        return self._reconnect_delay

    async def disconnect(self):
        """Disconnect from AVR."""
        await self._unsubscribe_events()
        try:
            await self._avr.async_telnet_disconnect()
        except denonavr.exceptions.DenonAvrError:
            pass
        self._connecting = False
        if self.id:
            self.events.emit(Events.DISCONNECTED, self.id)

    @staticmethod
    def _map_denonavr_state(avr_state: str | None) -> States:
        """Map the DenonAVR library state to our state."""
        state = States.UNKNOWN
        if avr_state == "on":
            state = States.ON
        elif avr_state == "off":
            state = States.OFF
        elif avr_state == "playing":
            state = States.PLAYING
        elif avr_state == "paused":
            state = States.PAUSED
        return state

    @async_handle_denonlib_errors
    async def _get_data(self) -> None:
        if self._getting_data:
            return

        # TODO use asyncio.Lock?
        self._getting_data = True
        _LOG.debug("[%s] Getting track data.", self.id)

        try:
            await self._avr.async_update()

            if self._avr.power == "OFF":
                self.state = States.OFF
            else:
                self.state = self._map_denonavr_state(self._avr.state)

            volume = self._convert_volume_to_percent(self._avr.volume)

            self.events.emit(
                Events.UPDATE,
                self.id,
                {
                    "state": self.state,
                    "artist": self._avr.artist,
                    "album": self._avr.album,
                    "artwork": self._avr.image_url,
                    "title": self._avr.title,
                    "muted": self._avr.muted,
                    "source": self._avr.input_func,
                    "source_list": self._avr.input_func_list,
                    "sound_mode": self._avr.sound_mode,
                    "sound_mode_list": self._avr.sound_mode_list,
                    "volume": volume,
                },
            )
            _LOG.debug(
                "[%s] Track data: artist: %s title: %s artwork: %s",
                self.id,
                self._avr.artist,
                self._avr.title,
                self._avr.image_url,
            )
        finally:
            self._getting_data = False

    async def _telnet_callback(self, zone, event, parameter):
        """Process a telnet command callback."""
        _LOG.debug("[%s] zone: %s, event: %s, parameter: %s", self.id, zone, event, parameter)
        try:
            # TODO is this required or already handled in the denon lib?
            await self._avr.async_update()
        except denonavr.exceptions.DenonAvrError as e:
            _LOG.error("[%s] Failed to get latest status information: %s", self.id, e)

        # TODO can't we subscribe to only the events we are interested in?
        if event == "PW":  # Power
            if parameter == "ON":
                self.state = States.ON
            elif parameter in ("STANDBY", "OFF"):
                self.state = States.OFF
            self.events.emit(Events.UPDATE, self.id, {"state": self.state})
        elif event == "MV":  # Master Volume
            volume = self._convert_volume_to_percent(self._avr.volume)
            self.events.emit(Events.UPDATE, self.id, {"volume": volume})
        elif event == "CV":  # Channel Volume
            pass
        elif event == "MU":  # Muted
            muted = parameter == "ON"
            self.events.emit(Events.UPDATE, self.id, {"muted": muted})
        elif event == "SI":  # Select Input source
            self.events.emit(Events.UPDATE, self.id, {"source": self._avr.input_func})
        elif event in ("ZM", "Z2", "Z2MU", "Z2CV", "Z3"):  # Zone Main, Zone 2 and 3: not yet supported
            pass  # reduce number of _get_data() calls
        elif event in ("SD", "DC"):  # Input mode change / Digital input mode change
            pass  # TODO should not be required to handle. SI should be sent as well?
        elif event == "SV":  # Select Video
            pass  # TODO should not be required to handle. SI should be sent as well?
        elif event == "SLP":  # Sleep mode change
            pass
        elif event == "MS":  # surround Mode Setting
            self.events.emit(Events.UPDATE, self.id, {"sound_mode": self._avr.sound_mode})
        elif event == "PS":  # Parameter Setting
            pass  # reduce number of _get_data() calls
        elif event in ("TF", "TP", "TM"):  # Tuner
            pass  # reduce number of _get_data() calls
        else:
            # TODO still required?
            _ = asyncio.ensure_future(self._get_data())
            # if self.state == STATES.OFF:
            #     self.state = STATES.ON

            # if parameter == "OFF":
            #     self.state = STATES.OFF
        # elif event == "NSE":  # Onscreen display information
        #     _ = asyncio.ensure_future(self.getData())
        # TODO: the duration and position needs more digging
        # if parameter.startswith("5"):
        #     result = self._extract_values(parameter)
        #     if result:
        #         time, percentage = result
        #         hours, minutes = map(int, time.split(":"))
        #         self.duration = hours * 3600 + minutes * 60
        #         self.position = (int(percentage.strip("%")) / 100) * self.duration
        #         self.events.emit(EVENTS.UPDATE, self.id, {
        #             "position": self.position,
        #             "total_time": self.duration
        #         })

        #         LOG.debug(f"Time: {self.position}, Percentage: {self.duration}")

        # Switching inputs generates the following events with an AVR-X2700:
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: PS, parameter: CLV 455
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: SS, parameter: LEVC 455
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: SI, parameter: TV
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: CV, parameter: FL 50
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: CV, parameter: FR 50
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: SS, parameter: SMG MUS
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: CV, parameter: END
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: SS, parameter: ALSDSP OFF
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: SS, parameter: ALSSET ON
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: SS, parameter: ALSVAL 000
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: SD, parameter: NO
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: PS, parameter: RSTR OFF
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: DC, parameter: AUTO
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: VS, parameter: SCAUTO
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: VS, parameter: SCHAUTO
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: SS, parameter: HOSIPS ATH
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: VS, parameter: ASPFUL
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: SS, parameter: HOSIPM AUT
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: VS, parameter: VPMAUTO
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: PS, parameter: MULTEQ:AUDYSSEY
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: PS, parameter: DYNEQ ON
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: PS, parameter: DYNVOL OFF
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: PS, parameter: REFLEV 0
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: PS, parameter: DELAY 000
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: PV, parameter: OFF
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: SV, parameter: OFF
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: PS, parameter: HEQ OFF
        # DEBUG:avr:[DBBZ012118361] zone: Main, event: SS, parameter: HOSSHP OFF
        # DEBUG:avr:[DBBZ012118361] zone: All, event: PW, parameter: ON

    async def _subscribe_events(self):
        try:
            if self._use_telnet:
                await self._avr.async_telnet_connect()
            await self._avr.async_update()
        except denonavr.exceptions.DenonAvrError as e:
            _LOG.error("[%s] Failed to get latest status information: %s", self.id, e)
        self._avr.register_callback("ALL", self._telnet_callback)
        _LOG.debug("[%s] Subscribed to events", self.id)

    async def _unsubscribe_events(self):
        try:
            self._avr.unregister_callback("ALL", self._telnet_callback)
            # TODO is async_update() required?
            await self._avr.async_update()
        except denonavr.exceptions.DenonAvrError as e:
            _LOG.error("[%s] Failed to get latest status information: %s", self.id, e)
        try:
            await self._avr.async_telnet_disconnect()
        except denonavr.exceptions.DenonAvrError:
            pass
        _LOG.debug("[%s] Unsubscribed to events", self.id)

    @async_handle_denonlib_errors
    async def power_on(self) -> ucapi.StatusCodes:
        """Send power-on command to AVR."""
        await self._avr.async_power_on()

    @async_handle_denonlib_errors
    async def power_off(self) -> ucapi.StatusCodes:
        """Send power-off command to AVR."""
        await self._avr.async_power_off()

    @async_handle_denonlib_errors
    async def set_volume_level(self, volume: float) -> ucapi.StatusCodes:
        """Set volume level, range 0..100."""
        # Volume has to be sent in a format like -50.0. Minimum is -80.0,
        # maximum is 18.0
        volume_denon = float(volume - 80)
        if volume_denon > 18:
            volume_denon = float(18)
        await self._avr.async_set_volume(volume_denon)

    @async_handle_denonlib_errors
    async def volume_up(self) -> ucapi.StatusCodes:
        """Send volume-up command to AVR."""
        await self._avr.async_volume_up()

    @async_handle_denonlib_errors
    async def volume_down(self) -> ucapi.StatusCodes:
        """Send volume-down command to AVR."""
        await self._avr.async_volume_down()

    @async_handle_denonlib_errors
    async def play_pause(self) -> ucapi.StatusCodes:
        """Send toggle-play-pause command to AVR."""
        await self._avr.async_toggle_play_pause()

    @async_handle_denonlib_errors
    async def next(self) -> ucapi.StatusCodes:
        """Send next-track command to AVR."""
        await self._avr.async_next_track()

    @async_handle_denonlib_errors
    async def previous(self) -> ucapi.StatusCodes:
        """Send previous-track command to AVR."""
        await self._avr.async_previous_track()

    @async_handle_denonlib_errors
    async def mute(self, muted: bool) -> ucapi.StatusCodes:
        """Send mute command to AVR."""
        _LOG.debug("Sending mute: %s", muted)
        await self._avr.async_mute(muted)

    @async_handle_denonlib_errors
    async def select_source(self, source: str) -> ucapi.StatusCodes:
        """Send input_source command to AVR."""
        _LOG.debug("Set input: %s", source)
        # Ensure that the AVR is turned on, which is necessary for input
        # switch to work.
        await self.power_on()
        await self._avr.async_set_input_func(source)

    @async_handle_denonlib_errors
    async def select_sound_mode(self, sound_mode: str) -> ucapi.StatusCodes:
        """Select sound mode."""
        await self._avr.async_set_sound_mode(sound_mode)
