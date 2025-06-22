"""
This module implements the Denon AVR receiver communication of the Remote Two integration driver.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import asyncio
import logging
import time
from asyncio import AbstractEventLoop, Lock
from enum import IntEnum
from functools import wraps
from typing import Any, Awaitable, Callable, Concatenate, Coroutine, ParamSpec, TypeVar

import denonavr
import discover
import ucapi
from config import AvrDevice
from denonavr.const import (
    ALL_TELNET_EVENTS,
    ALL_ZONES,
    STATE_OFF,
    STATE_ON,
    STATE_PAUSED,
    STATE_PLAYING,
)
from denonavr.exceptions import (
    AvrCommandError,
    AvrForbiddenError,
    AvrNetworkError,
    AvrTimoutError,
    DenonAvrError,
)
from pyee.asyncio import AsyncIOEventEmitter
from simplecommand import SimpleCommand
from ucapi.media_player import Attributes as MediaAttr

_LOG = logging.getLogger(__name__)

SETUP_TIMEOUT = 5000
"""AVR connection timeout to retrieve setup information in milliseconds."""

BACKOFF_MAX: float = 30
MIN_RECONNECT_DELAY: float = 0.5
BACKOFF_FACTOR: float = 1.5

DISCOVERY_AFTER_CONNECTION_ERRORS = 10

AVR_COMMAND_URL = "/goform/formiPhoneAppDirect.xml"


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


DENON_STATE_MAPPING = {
    STATE_ON: States.ON,
    STATE_OFF: States.OFF,
    STATE_PLAYING: States.PLAYING,
    STATE_PAUSED: States.PAUSED,
}

TELNET_EVENTS = {
    "PW",  # Power
    "HD",  # HD radio station
    "MS",  # surround Mode Setting
    "MU",  # Muted
    "MV",  # Master Volume
    "NS",  # Preset
    "NSE",  # Onscreen display information (mServer/iRadio)
    "PS",  # Parameter Setting
    "SI",  # Select Input source
    "SS",  # ??
    "TF",  # Tuner Frequency (?)
    "ZM",  # Zone Main
    "Z2",  # Zone 2
    "Z3",  # Zone 3
}

_DenonDeviceT = TypeVar("_DenonDeviceT", bound="DenonDevice")
_P = ParamSpec("_P")


# Adapted from Home Assistant `async_log_errors` in
# https://github.com/home-assistant/core/blob/fd1f0b0efeb5231d3ee23d1cb2a10cdeff7c23f1/homeassistant/components/denonavr/media_player.py
def async_handle_denonlib_errors(
    func: Callable[Concatenate[_DenonDeviceT, _P], Awaitable[ucapi.StatusCodes | None]],
) -> Callable[Concatenate[_DenonDeviceT, _P], Coroutine[Any, Any, ucapi.StatusCodes | None]]:
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
            if result := await func(self, *args, **kwargs):
                return result
            return ucapi.StatusCodes.OK
        except AvrTimoutError:
            available = False
            result = ucapi.StatusCodes.SERVICE_UNAVAILABLE
            if self.available:
                _LOG.warning(
                    "Timeout connecting to Denon AVR receiver at host %s. Device is unavailable. (%s%s)",
                    self._receiver.host,
                    func.__name__,
                    args,
                )
                self.available = False
        except AvrNetworkError:
            result = ucapi.StatusCodes.SERVICE_UNAVAILABLE
            available = False
            if self.available:
                _LOG.warning(
                    "Network error connecting to Denon AVR receiver at host %s. Device is unavailable. (%s%s)",
                    self._receiver.host,
                    func.__name__,
                    args,
                )
                self.available = False
        except AvrForbiddenError:
            available = False
            result = ucapi.StatusCodes.UNAUTHORIZED
            if self.available:
                _LOG.warning(
                    (
                        "Denon AVR receiver at host %s responded with HTTP 403 error. "
                        "Device is unavailable. Please consider power cycling your "
                        "receiver. (%s%s)"
                    ),
                    self._receiver.host,
                    func.__name__,
                    args,
                )
                self.available = False
        except AvrCommandError as err:
            available = False
            result = ucapi.StatusCodes.BAD_REQUEST
            _LOG.error(
                "Command %s%s failed with error: %s",
                func.__name__,
                args,
                err,
            )
        except DenonAvrError as err:
            available = False
            _LOG.exception(
                "Error %s occurred in method %s%s for Denon AVR receiver",
                err,
                func.__name__,
                args,
            )
        finally:
            if available and not self.available:
                _LOG.info(
                    "Denon AVR receiver at host %s is available again",
                    self._receiver.host,
                )
                self.available = True
        return result

    return wrapper


class DenonDevice:
    """Representing a Denon AVR Device."""

    def __init__(
        self,
        device: AvrDevice,
        loop: AbstractEventLoop | None = None,
    ):
        """Create instance with given IP or hostname of AVR."""
        # identifier from configuration
        self.id: str = device.id
        # friendly name from configuration
        self._name: str = device.name
        self._event_loop = loop or asyncio.get_running_loop()
        self.events = AsyncIOEventEmitter(self._event_loop)
        self._zones: dict[str, str | None] = {}
        if device.zone2:
            self._zones["Zone2"] = None
        if device.zone3:
            self._zones["Zone3"] = None
        self._receiver: denonavr.DenonAVR = denonavr.DenonAVR(
            host=device.address,
            show_all_inputs=device.show_all_inputs,
            timeout=device.timeout / 1000.0,
            add_zones=self._zones,
        )
        self._update_audyssey = device.update_audyssey
        self._simple_command = SimpleCommand(self._receiver, self._send_command)

        self._active: bool = False
        self._use_telnet = device.use_telnet
        self._telnet_was_healthy: bool | None = None
        self._attr_available: bool = True
        # expected volume feedback value if telnet isn't used
        self._expected_volume: float | None = None

        self._connecting: bool = False
        self._connection_attempts: int = 0
        self._reconnect_delay: float = MIN_RECONNECT_DELAY

        # Workaround for weird state behaviour. Sometimes "off" is always returned from the denonlib!
        self._expected_state: States = States.UNKNOWN
        self._volume_step = device.volume_step
        self._update_lock = Lock()

        _LOG.debug("Denon AVR created: %s", device.address)

    @property
    def active(self) -> bool:
        """Return true if device is active and should have an established connection."""
        return self._active

    @property
    def available(self) -> bool:
        """Return True if device is available."""
        return self._attr_available

    @available.setter
    def available(self, value: bool):
        """Set device availability and emit CONNECTED / DISCONNECTED event on change."""
        if self._attr_available != value:
            self._attr_available = value
            self.events.emit(Events.CONNECTED if value else Events.DISCONNECTED, self.id)

    @property
    def name(self) -> str | None:
        """Return the name of the device as string."""
        return self._receiver.name

    @property
    def host(self) -> str:
        """Return the host of the device as string."""
        return self._receiver.host

    @property
    def manufacturer(self) -> str | None:
        """Return the manufacturer of the device as string."""
        return self._receiver.manufacturer

    @property
    def model_name(self) -> str | None:
        """Return the model name of the device as string."""
        return self._receiver.model_name

    @property
    def serial_number(self) -> str | None:
        """Return the serial number of the device as string."""
        return self._receiver.serial_number

    @property
    def support_sound_mode(self) -> bool | None:
        """Return True if sound mode supported."""
        return self._receiver.support_sound_mode

    @property
    def state(self) -> States:
        """Return the cached state of the device."""
        reported_state = self._map_denonavr_state(self._receiver.state)
        # Dirty workaround for state reporting issue. Couldn't be reproduced yet.
        if self._use_telnet and reported_state == States.OFF and self._expected_state != States.OFF:
            _LOG.warning("State mismatch! Reported: %s. Using expected: %s", reported_state, self._expected_state)
            return self._expected_state
        return reported_state

    def _set_expected_state(self, state: States):
        """Set expected receiver state and emit update event if changed."""
        old = self._expected_state
        if state == States.ON:
            # only override ON state if it's not in on-related state already
            if self._expected_state in (States.UNKNOWN, States.UNAVAILABLE, States.OFF):
                self._expected_state = state
        else:
            self._expected_state = state

        if old != self._expected_state:
            self.events.emit(Events.UPDATE, self.id, {MediaAttr.STATE: self._expected_state})

    @property
    def source_list(self) -> list[str]:
        """Return a list of available input sources."""
        return self._receiver.input_func_list

    @property
    def is_volume_muted(self) -> bool:
        """Return boolean if volume is currently muted."""
        return self._receiver.muted

    @property
    def volume_level(self) -> float | None:
        """Volume level of the media player (0..100)."""
        # Volume is sent in a format like -50.0. Minimum is -80.0,
        # maximum is 18.0
        if self._receiver.volume is None:
            return None
        volume = min(self._receiver.volume + 80, 100)
        volume = max(volume, 0)
        return volume

    @property
    def source(self) -> str:
        """Return the current input source."""
        if self._receiver.input_func is not None:
            return self._receiver.input_func
        return ""

    @property
    def sound_mode_list(self) -> list[str]:
        """Return the available sound modes."""
        return self._receiver.sound_mode_list

    @property
    def sound_mode(self) -> str:
        """Return the current matched sound mode."""
        if self._receiver.sound_mode is not None:
            return self._receiver.sound_mode
        return ""

    @property
    def media_image_url(self) -> str:
        """Image url of current playing media."""
        if self._receiver.input_func in self._receiver.playing_func_list:
            if self._receiver.image_url is not None:
                return self._receiver.image_url
        return ""

    @property
    def media_title(self) -> str:
        """Title of current playing media."""
        if self._receiver.input_func not in self._receiver.playing_func_list:
            return self._receiver.input_func
        if self._receiver.title is not None:
            return self._receiver.title
        if self._receiver.frequency is not None:
            return self._receiver.frequency
        return ""

    @property
    def media_artist(self) -> str:
        """Artist of current playing media, music track only."""
        if self._receiver.artist is not None:
            return self._receiver.artist
        if self._receiver.band is not None:
            return self._receiver.band
        return ""

    @property
    def media_album_name(self) -> str:
        """Album name of current playing media, music track only."""
        if self._receiver.album is not None:
            return self._receiver.album
        if self._receiver.station is not None:
            return self._receiver.station
        return ""

    async def connect(self):
        """
        Connect to AVR.

        Automatically retry if connection fails. This method will not return
        until the connection could be established, or disconnect() has been
        called.

        The call is ignored if a connection is already being established.
        """
        if self._connecting:
            _LOG.debug("Connection task already running for %s", self.id)
            return

        if self._active:
            _LOG.debug("[%s] Already connected", self.id)
            return

        self._connecting = True
        try:
            request_start = None
            success = False
            _LOG.debug("Starting connection task for %s", self.id)

            while not success:
                try:
                    _LOG.info("Connecting AVR %s on %s", self.id, self._receiver.host)
                    self.events.emit(Events.CONNECTING, self.id)
                    request_start = time.time()

                    await self._receiver.async_update()
                    if self._use_telnet:
                        if self._update_audyssey:
                            await self._receiver.async_update_audyssey()
                        await self._receiver.async_telnet_connect()

                        self._receiver.register_callback(ALL_TELNET_EVENTS, self._telnet_callback)

                    success = True
                    self._connection_attempts = 0
                    self._reconnect_delay = MIN_RECONNECT_DELAY
                except denonavr.exceptions.DenonAvrError as ex:
                    await self._handle_connection_failure(time.time() - request_start, ex)

            if self.id != self._receiver.serial_number:
                _LOG.warning(
                    "Different device serial number! Expected=%s, received=%s", self.id, self._receiver.serial_number
                )

            _LOG.info(
                "Denon AVR connected. Manufacturer=%s, Model=%s, Name=%s, Id=%s, State=%s",
                self.manufacturer,
                self.model_name,
                self.name,
                self.id,
                self._receiver.state,
            )

            self._active = True
            self._expected_state = self._map_denonavr_state(self._receiver.state)
            self.events.emit(Events.CONNECTED, self.id)
        finally:
            self._connecting = False

    async def _handle_connection_failure(self, connect_duration: float, ex):
        self._connection_attempts += 1
        # backoff delay must deduct time spent in the connection attempt
        backoff = self._backoff() - connect_duration
        if backoff <= 0:
            backoff = 0.1
        _LOG.error(
            "Cannot connect to '%s' on %s, trying again in %.1fs (connect: %.1fs). %s",
            self.id if self.id else self._name,
            self._receiver.host,
            backoff,
            connect_duration,
            ex,
        )

        # try resolving IP address from device name if we keep failing to connect, maybe the IP address changed
        if self._connection_attempts % DISCOVERY_AFTER_CONNECTION_ERRORS == 0:
            _LOG.debug("Start resolving IP address for '%s'...", self._name)
            discovered = await discover.denon_avrs()
            for item in discovered:
                if item["friendlyName"] == self._name:
                    if self._receiver.host != item["host"]:
                        _LOG.info("IP address of '%s' changed: %s", self._name, item["host"])
                        self._receiver._host = item["host"]  # pylint: disable=W0212 # seems to be the only way
                        self.events.emit(Events.IP_ADDRESS_CHANGED, self.id, self._receiver.host)
                        break
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
        _LOG.debug("Disconnect %s", self.id)
        self._reconnect_delay = MIN_RECONNECT_DELAY
        # Note: disconnecting during a connection task is currently not supported!
        # Simply setting self._connecting = False doesn't work, and will start even more connection tasks after wakeup!
        # This requires a state machine, or at least a separate connection task which can be cancelled.
        if self._connecting:
            return
        self._active = False

        try:
            if self._use_telnet:
                try:
                    self._receiver.unregister_callback(ALL_TELNET_EVENTS, self._telnet_callback)
                except ValueError:
                    pass
                await self._receiver.async_telnet_disconnect()
        except denonavr.exceptions.DenonAvrError:
            pass
        if self.id:
            self.events.emit(Events.DISCONNECTED, self.id)

    @staticmethod
    def _map_denonavr_state(avr_state: str | None) -> States:
        """Map the DenonAVR library state to our state."""
        if avr_state and avr_state in DENON_STATE_MAPPING:
            return DENON_STATE_MAPPING[avr_state]
        return States.UNKNOWN

    @async_handle_denonlib_errors
    async def async_update_receiver_data(self):
        """
        Get the latest status information from device.

        The call is ignored if:
        - the device is not active (i.e. has not been connected yet, or after a disconnect() call).
        - an async_update task is still running.
        - a (re-)connection task is currently running.
        """
        if self._update_lock.locked() or not self._active or self._connecting:
            return

        await self._update_lock.acquire()

        try:
            receiver = self._receiver

            # We can only skip the update if telnet was healthy after
            # the last update and is still healthy now to ensure that
            # we don't miss any state changes while telnet is down
            # or reconnecting.
            # TODO: is this still needed?
            if (
                telnet_is_healthy := receiver.telnet_connected and receiver.telnet_healthy
            ) and self._telnet_was_healthy:
                self._notify_updated_data()
                return

            _LOG.debug("[%s] Fetching status", self.id)

            # if async_update raises an exception, we don't want to skip the next update
            # so we set _telnet_was_healthy to None here and only set it to the value
            # before the update if the update was successful
            self._telnet_was_healthy = None

            await receiver.async_update()

            self._telnet_was_healthy = telnet_is_healthy

            if self._update_audyssey:
                await receiver.async_update_audyssey()

            self._notify_updated_data()
        finally:
            self._update_lock.release()

    def _notify_updated_data(self):
        """Notify listeners that the AVR data has been updated."""
        # adjust to the real volume level
        self._expected_volume = self.volume_level

        # None update object means data are up to date & client can fetch required data.
        self.events.emit(Events.UPDATE, self.id, None)

    async def _telnet_callback(self, zone: str, event: str, parameter: str) -> None:
        """Process a telnet command callback."""
        _LOG.debug("[%s] zone: %s, event: %s, parameter: %s", self.id, zone, event, parameter)

        # *** Start logic from HA
        # There are multiple checks implemented which reduce unnecessary updates
        if zone not in (self._receiver.zone, ALL_ZONES):
            return
        if event not in TELNET_EVENTS:
            return
        # Some updates trigger multiple events like one for artist and one for title for one change
        # We skip every event except the last one
        if event == "NSE" and not parameter.startswith("4"):
            return
        if event == "TA" and not parameter.startswith("ANNAME"):
            return
        if event == "HD" and not parameter.startswith("ALBUM"):
            return
        # *** End logic from HA

        if event == "PW":  # Power
            if parameter == "ON":
                self._set_expected_state(States.ON)
            elif parameter in ("STANDBY", "OFF"):
                self._set_expected_state(States.OFF)
        elif event == "MV":  # Master Volume
            self._set_expected_state(States.ON)
            level = self.volume_level
            if level is None:
                level = int(parameter)
            self.events.emit(Events.UPDATE, self.id, {MediaAttr.VOLUME: level})
        elif event == "MU":  # Muted
            self._set_expected_state(States.ON)
            muted = parameter == "ON"
            self.events.emit(Events.UPDATE, self.id, {MediaAttr.MUTED: muted})
        elif event == "SI":  # Select Input source
            self._set_expected_state(States.ON)
            self.events.emit(Events.UPDATE, self.id, {MediaAttr.SOURCE: self._receiver.input_func})
        elif event == "MS":  # surround Mode Setting
            self._set_expected_state(States.ON)
            self.events.emit(Events.UPDATE, self.id, {MediaAttr.SOUND_MODE: self._receiver.sound_mode})
        elif event == "PS":  # Parameter Setting
            return  # reduce number of updates. TODO check if we need to handle certain parameters, likely Audyssey

        self._notify_updated_data()

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

    @async_handle_denonlib_errors
    async def power_on(self) -> ucapi.StatusCodes:
        """Send power-on command to AVR."""
        await self._receiver.async_power_on()
        if not self._use_telnet:
            self._set_expected_state(States.ON)

        # kick off an update in case of http communication or if the telnet connection is not healthy
        await self._event_loop.create_task(self.async_update_receiver_data())
        return ucapi.StatusCodes.OK

    @async_handle_denonlib_errors
    async def power_off(self) -> ucapi.StatusCodes:
        """Send power-off command to AVR."""
        await self._receiver.async_power_off()
        if not self._use_telnet:
            self._set_expected_state(States.OFF)

        # kick off an update in case of http communication or if the telnet connection is not healthy
        await self._event_loop.create_task(self.async_update_receiver_data())
        return ucapi.StatusCodes.OK

    async def power_toggle(self) -> ucapi.StatusCodes:
        """Send power-on or -off command to AVR based on current power state."""
        if self._receiver.power is not None and self._receiver.power == "ON":
            return await self.power_off()
        return await self.power_on()

    @async_handle_denonlib_errors
    async def set_volume_level(self, volume: float | None) -> ucapi.StatusCodes:
        """Set volume level, range 0..100."""
        if volume is None:
            return ucapi.StatusCodes.BAD_REQUEST
        # Volume has to be sent in a format like -50.0. Minimum is -80.0,
        # maximum is 18.0
        volume_denon = float(volume - 80)
        if volume_denon > 18:
            volume_denon = float(18)
        await self._receiver.async_set_volume(volume_denon)
        self.events.emit(Events.UPDATE, self.id, {MediaAttr.VOLUME: volume})
        if not self._use_telnet or self._update_lock.locked():
            self._expected_volume = volume

        # kick off an update in case of http communication or if the telnet connection is not healthy
        await self._event_loop.create_task(self.async_update_receiver_data())
        return ucapi.StatusCodes.OK

    @async_handle_denonlib_errors
    async def volume_up(self) -> ucapi.StatusCodes:
        """Send volume-up command to AVR."""
        if self._use_telnet and self._expected_volume is not None and self._volume_step != 0.5:
            self._expected_volume = min(self._expected_volume + self._volume_step, 100)
            await self.set_volume_level(self._expected_volume)
        else:
            await self._receiver.async_volume_up()
            self._increase_expected_volume()
        return ucapi.StatusCodes.OK

    @async_handle_denonlib_errors
    async def volume_down(self) -> ucapi.StatusCodes:
        """Send volume-down command to AVR."""
        if self._use_telnet and self._expected_volume is not None and self._volume_step != 0.5:
            self._expected_volume = max(self._expected_volume - self._volume_step, 0)
            await self.set_volume_level(self._expected_volume)
        else:
            await self._receiver.async_volume_down()
            self._decrease_expected_volume()
        return ucapi.StatusCodes.OK

    @async_handle_denonlib_errors
    async def play_pause(self) -> ucapi.StatusCodes:
        """Send toggle-play-pause command to AVR."""
        await self._receiver.async_toggle_play_pause()
        return ucapi.StatusCodes.OK

    @async_handle_denonlib_errors
    async def next(self) -> ucapi.StatusCodes:
        """Send next-track command to AVR."""
        await self._receiver.async_next_track()
        return ucapi.StatusCodes.OK

    @async_handle_denonlib_errors
    async def previous(self) -> ucapi.StatusCodes:
        """Send previous-track command to AVR."""
        await self._receiver.async_previous_track()
        return ucapi.StatusCodes.OK

    @async_handle_denonlib_errors
    async def mute(self, muted: bool) -> ucapi.StatusCodes:
        """Send mute command to AVR."""
        _LOG.debug("Sending mute: %s", muted)
        await self._receiver.async_mute(muted)
        if not self._use_telnet:
            self.events.emit(Events.UPDATE, self.id, {MediaAttr.MUTED: muted})

        # kick off an update in case of http communication or if the telnet connection is not healthy
        await self._event_loop.create_task(self.async_update_receiver_data())
        return ucapi.StatusCodes.OK

    @async_handle_denonlib_errors
    async def select_source(self, source: str | None) -> ucapi.StatusCodes:
        """Send input_source command to AVR."""
        if not source:
            return ucapi.StatusCodes.BAD_REQUEST
        _LOG.debug("Set input: %s", source)
        # Ensure that the AVR is turned on, which is necessary for input
        # switch to work.
        await self.power_on()
        await self._receiver.async_set_input_func(source)
        return ucapi.StatusCodes.OK

    @async_handle_denonlib_errors
    async def select_sound_mode(self, sound_mode: str | None) -> ucapi.StatusCodes:
        """Select sound mode."""
        if not sound_mode:
            return ucapi.StatusCodes.BAD_REQUEST
        await self._receiver.async_set_sound_mode(sound_mode)
        return ucapi.StatusCodes.OK

    @async_handle_denonlib_errors
    async def cursor_up(self) -> ucapi.StatusCodes:
        """Send cursor up command to AVR."""
        await self._receiver.async_cursor_up()
        return ucapi.StatusCodes.OK

    @async_handle_denonlib_errors
    async def cursor_down(self) -> ucapi.StatusCodes:
        """Send cursor down command to AVR."""
        await self._receiver.async_cursor_down()
        return ucapi.StatusCodes.OK

    @async_handle_denonlib_errors
    async def cursor_left(self) -> ucapi.StatusCodes:
        """Send cursor left command to AVR."""
        await self._receiver.async_cursor_left()
        return ucapi.StatusCodes.OK

    @async_handle_denonlib_errors
    async def cursor_right(self) -> ucapi.StatusCodes:
        """Send cursor right command to AVR."""
        await self._receiver.async_cursor_right()
        return ucapi.StatusCodes.OK

    @async_handle_denonlib_errors
    async def cursor_enter(self) -> ucapi.StatusCodes:
        """Send cursor enter command to AVR."""
        await self._receiver.async_cursor_enter()
        return ucapi.StatusCodes.OK

    @async_handle_denonlib_errors
    async def info(self) -> ucapi.StatusCodes:
        """Send info OSD command to AVR."""
        await self._receiver.async_info()
        return ucapi.StatusCodes.OK

    @async_handle_denonlib_errors
    async def options(self) -> ucapi.StatusCodes:
        """Send options menu command to AVR."""
        await self._receiver.async_options()
        return ucapi.StatusCodes.OK

    @async_handle_denonlib_errors
    async def back(self) -> ucapi.StatusCodes:
        """Send back command to AVR."""
        await self._receiver.async_back()
        return ucapi.StatusCodes.OK

    @async_handle_denonlib_errors
    async def setup(self) -> ucapi.StatusCodes:
        """Send toggle open/close menu command to AVR."""
        # Toggle only works when receiving events via Telnet
        # Users using HTTP will have to use the back/return button
        if self._use_telnet:
            await self._receiver.async_settings_menu()
            return ucapi.StatusCodes.OK
        return await self._send_command("MNMEN ON")

    @async_handle_denonlib_errors
    async def send_command(self, cmd: str) -> ucapi.StatusCodes:
        """
        Send a command to the AVR.

        The command is either sent over telnet, if it is active, or with a http request.
        """
        return await self._send_command(cmd)

    @async_handle_denonlib_errors
    async def send_simple_command(self, cmd: str) -> ucapi.StatusCodes:
        """Send a simple command to the AVR."""
        return await self._simple_command.send_simple_command(cmd)

    async def _send_command(self, cmd: str) -> ucapi.StatusCodes:
        """Send a command without error wrapper."""
        if self._use_telnet:
            await self._receiver.async_send_telnet_commands(cmd)
        else:
            url = AVR_COMMAND_URL + "?" + cmd.replace(" ", "%20")
            # HACK only _receiver.async_get_command(url) is exposed which returns the body content
            # pylint: disable=protected-access
            res = await self._receiver._device.api.async_get(url)
            if res.is_client_error:
                return ucapi.StatusCodes.BAD_REQUEST
            if not res.is_success:
                return ucapi.StatusCodes.SERVER_ERROR
        return ucapi.StatusCodes.OK

    def _increase_expected_volume(self):
        """Without telnet, increase expected volume and send update event."""
        if not self._use_telnet or self._expected_volume is None:
            return
        self._expected_volume = min(self._expected_volume + self._volume_step, 100)
        # Send updated volume if no update task in progress
        if not self._update_lock.locked():
            self._event_loop.create_task(self._receiver.async_update())

    def _decrease_expected_volume(self):
        """Without telnet, decrease expected volume and send update event."""
        if not self._use_telnet or self._expected_volume is None:
            return
        self._expected_volume = max(self._expected_volume - self._volume_step, 0)
        # Send updated volume if no update task in progress
        if not self._update_lock.locked():
            self._event_loop.create_task(self._receiver.async_update())
