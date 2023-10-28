# -*- coding: utf-8 -*-
"""
This module implements the Denon AVR receiver communication of the Remote Two integration driver.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import asyncio
import logging
import re
from asyncio import AbstractEventLoop
from enum import IntEnum

import denonavr
import denonavr.exceptions
from pyee import AsyncIOEventEmitter

_LOG = logging.getLogger(__name__)


class Events(IntEnum):
    """Internal driver events."""

    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 2
    PAIRED = 3
    ERROR = 4
    UPDATE = 5


class States(IntEnum):
    """State of a connected AVR."""

    UNKNOWN = 0
    UNAVAILABLE = 1
    OFF = 2
    ON = 3
    PLAYING = 4
    PAUSED = 5


async def discover_denon_avrs():
    """
    Discover Denon AVRs on the network with SSDP.

    :return: array of device information objects.
    """
    _LOG.debug("Starting discovery")

    avrs = await denonavr.async_discover()
    if not avrs:
        _LOG.info("No AVRs discovered")
        return []

    _LOG.info("Found AVR(s): %s", avrs)

    return avrs


class DenonAVR:
    """Representing a Denon AVR Device."""

    def __init__(self, loop: AbstractEventLoop, ipaddress: str):
        """Create instance with given IP address of AVR."""
        self._loop: AbstractEventLoop = loop
        self.events = AsyncIOEventEmitter(self._loop)
        self._avr: denonavr.DenonAVR | None = None
        self.name: str | None = None
        self.model: str | None = None
        self.manufacturer: str | None = None
        self.id: str | None = None
        self.ipaddress: str = ipaddress
        self.getting_data: bool = False

        self.state: States = States.UNKNOWN
        self.volume: float = 0
        self.input: str | None = None
        self.input_list: list[str] = []
        self.artist: str | None = None
        self.title: str | None = None
        self.artwork: str | None = None
        self.position: int = 0
        self.duration: int = 0

        _LOG.debug("Denon AVR created: %s", self.ipaddress)

    @staticmethod
    def _map_range(value, from_min, from_max, to_min, to_max):
        return (value - from_min) * (to_max - to_min) / (from_max - from_min) + to_min

    def _convert_volume_to_percent(self, value):
        return self._map_range(value, -80.0, 0.0, 0, 100)

    def _convert_volume_to_db(self, value):
        return self._map_range(value, 0, 100, -80.0, 0.0)

    @staticmethod
    def _extract_values(input_string):
        pattern = r"(\d+:\d+)\s+(\d+%)"
        matches = re.findall(pattern, input_string)

        if matches:
            return matches[0]

        return None

    # TODO ADD METHOD FOR CHANGED IP ADDRESS

    async def connect(self):
        """Connect to AVR."""
        if self._avr is not None:
            _LOG.debug("Already connected")
            _ = asyncio.ensure_future(self._get_data())
            return

        try:
            self._avr = denonavr.DenonAVR(self.ipaddress)
            await self._avr.async_setup()
            await self._avr.async_update()
        except denonavr.exceptions.DenonAvrError as e:
            _LOG.error("[%s] Error connecting to AVR: %s", self.ipaddress, e)
            # FIXME connection retry missing! If no AVR is available at startup, the driver never connects :-(
            #       Message: NetworkError: All connection attempts failed
            self._avr = None
            return

        if self._avr is None:
            return

        self.manufacturer = self._avr.manufacturer
        self.model = self._avr.model_name
        self.name = self._avr.name
        # TODO any chance we don't get a serial number from the device?
        self.id = self._avr.serial_number

        _LOG.debug(
            "Denon AVR connected. Manufacturer=%s, Model=%s, Name=%s, Id=%s, State=%s",
            self.manufacturer,
            self.model,
            self.name,
            self.id,
            self._avr.state,
        )

        await self._subscribe_events()
        if self.id:
            self.events.emit(Events.CONNECTED, self.id)
        else:
            _LOG.error("Device communication error: no serial number retrieved from AVR!")

        self.state = self._map_denonavr_state(self._avr.state)

        self.input_list = self._avr.input_func_list
        self.input = self._avr.input_func
        self.volume = self._convert_volume_to_percent(self._avr.volume)
        self.artist = self._avr.artist
        self.title = self._avr.title
        self.artwork = self._avr.image_url
        self.position = 0
        self.duration = 0

    async def disconnect(self):
        """Disconnect from AVR."""
        await self._unsubscribe_events()
        self._avr = None
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

    async def _get_data(self):
        if self._avr is None:
            return
        if self.getting_data:
            return

        self.getting_data = True
        _LOG.debug("Getting track data.")

        try:
            await self._avr.async_update()
            if self._avr is None:
                _LOG.warning("AVR went away, cannot get data")
                return

            self.artist = self._avr.artist
            self.title = self._avr.title
            self.artwork = self._avr.image_url

            if self._avr.power == "OFF":
                self.state = States.OFF
            else:
                self.state = self._map_denonavr_state(self._avr.state)

            self.events.emit(
                Events.UPDATE,
                {
                    "state": self.state,
                    "artist": self.artist,
                    "title": self.title,
                    "artwork": self.artwork,
                },
            )
            _LOG.debug("Track data: artist: %s title: %s artwork: %s", self.artist, self.title, self.artwork)
        except denonavr.exceptions.DenonAvrError as e:
            _LOG.error("Failed to get latest status information: %s", e)

        self.getting_data = False
        _LOG.debug("Getting track data done.")

    async def _update_callback(self, zone, event, parameter):
        _LOG.debug("[%s] zone: %s, event: %s, parameter: %s", self.id, zone, event, parameter)
        if self._avr is None:
            return
        try:
            await self._avr.async_update()
        except denonavr.exceptions.DenonAvrError as e:
            _LOG.error("[%s] Failed to get latest status information: %s", self.id, e)

        # async_update() might take a while and _avr could have gone away
        if self._avr is None:
            return

        if event == "MV":
            self.volume = self._convert_volume_to_percent(self._avr.volume)
            self.events.emit(Events.UPDATE, {"volume": self.volume})
        elif event == "PW":
            if parameter == "ON":
                self.state = States.ON
            elif parameter in ("STANDBY", "OFF"):
                self.state = States.OFF
            self.events.emit(Events.UPDATE, {"state": self.state})
        else:
            _ = asyncio.ensure_future(self._get_data())
            # if self.state == STATES.OFF:
            #     self.state = STATES.ON

            # if parameter == "OFF":
            #     self.state = STATES.OFF
        # elif event == "NSE":
        #     _ = asyncio.ensure_future(self.getData())
        # TODO: the duration and position needs more digging
        # if parameter.startswith("5"):
        #     result = self._extract_values(parameter)
        #     if result:
        #         time, percentage = result
        #         hours, minutes = map(int, time.split(":"))
        #         self.duration = hours * 3600 + minutes * 60
        #         self.position = (int(percentage.strip("%")) / 100) * self.duration
        #         self.events.emit(EVENTS.UPDATE, {
        #             "position": self.position,
        #             "total_time": self.duration
        #         })

        #         LOG.debug(f"Time: {self.position}, Percentage: {self.duration}")

    async def _subscribe_events(self):
        if self._avr is None:
            return
        try:
            await self._avr.async_telnet_connect()
            await self._avr.async_update()
        except denonavr.exceptions.DenonAvrError as e:
            _LOG.error("[%s] Failed to get latest status information: %s", self.id, e)
        self._avr.register_callback("ALL", self._update_callback)
        _LOG.debug("Subscribed to events")

    async def _unsubscribe_events(self):
        if self._avr is None:
            return

        try:
            self._avr.unregister_callback("ALL", self._update_callback)
            # TODO is async_update() required?
            await self._avr.async_update()
        except denonavr.exceptions.DenonAvrError as e:
            _LOG.error("Failed to get latest status information: %s", e)
        try:
            # avr might be gone by now! Otherwise, process terminates with:
            # AttributeError: 'NoneType' object has no attribute 'async_telnet_disconnect'
            if self._avr is None:
                return
            await self._avr.async_telnet_disconnect()
        except denonavr.exceptions.DenonAvrError:
            pass
        _LOG.debug("Unsubscribed to events")

    # TODO add commands
    # FIXME #8 command execution check
    async def _command_wrapper(self, fn):
        try:
            await fn()
            return True
        except denonavr.exceptions.DenonAvrError as e:
            _LOG.error("Failed to execute command: %s", e)
            # TODO retry handling?
            return False

    async def power_on(self):
        """Send power-on command to AVR."""
        if self._avr is None:
            return
        return await self._command_wrapper(self._avr.async_power_on)

    async def power_off(self):
        """Send power-off command to AVR."""
        if self._avr is None:
            return
        return await self._command_wrapper(self._avr.async_power_off)

    async def volume_up(self):
        """Send volume-up command to AVR."""
        if self._avr is None:
            return
        return await self._command_wrapper(self._avr.async_volume_up)

    async def volume_down(self):
        """Send volume-down command to AVR."""
        if self._avr is None:
            return
        return await self._command_wrapper(self._avr.async_volume_down)

    async def play_pause(self):
        """Send toggle-play-pause command to AVR."""
        if self._avr is None:
            return
        return await self._command_wrapper(self._avr.async_toggle_play_pause)

    async def next(self):
        """Send next-track command to AVR."""
        if self._avr is None:
            return
        return await self._command_wrapper(self._avr.async_next_track)

    async def previous(self):
        """Send previous-track command to AVR."""
        if self._avr is None:
            return
        return await self._command_wrapper(self._avr.async_previous_track)

    async def mute(self, muted):
        """Send mute command to AVR."""
        if self._avr is None:
            return
        try:
            await self._avr.async_mute(muted)
            return True
        except denonavr.exceptions.DenonAvrError as e:
            _LOG.error("Failed to execute mute command: %s", e)
            return False

    async def set_input(self, input_source):
        """Send input_source command to AVR."""
        if self._avr is None:
            return
        try:
            await self._avr.async_set_input_func(input_source)
            return True
        except denonavr.exceptions.DenonAvrError as e:
            _LOG.error("Failed to execute input_source command: %s", e)
            return False
