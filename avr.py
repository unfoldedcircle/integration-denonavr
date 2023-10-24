# -*- coding: utf-8 -*-
"""
This module implements the Denon AVR receiver communication of the Remote Two integration driver.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
import asyncio
import socket
import re

from enum import IntEnum
from pyee import AsyncIOEventEmitter

import denonavr
import denonavr.exceptions

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

MCAST_GRP = "239.255.255.250"
MCAST_PORT = 1900
# is this correct? denonavr uses 2
SSDP_MX = 3

SSDP_DEVICES = [
    "urn:schemas-upnp-org:device:MediaRenderer:1",
    "urn:schemas-upnp-org:device:MediaServer:1",
    "urn:schemas-denon-com:device:AiosDevice:1"
]


class EVENTS(IntEnum):
    """Internal driver events."""

    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 2
    PAIRED = 3
    ERROR = 4
    UPDATE = 5


class STATES(IntEnum):
    """State of a connected AVR."""

    OFF = 0
    ON = 1
    PLAYING = 2
    PAUSED = 3


def ssdp_request(ssdp_st: str, ssdp_mx: float = SSDP_MX) -> bytes:
    """Return request bytes for given st and mx."""
    return "\r\n".join(
        [
            "M-SEARCH * HTTP/1.1",
            f"ST: {ssdp_st}",
            f"MX: {ssdp_mx:d}",
            'MAN: "ssdp:discover"',
            f"HOST: {MCAST_GRP}:{MCAST_PORT}",
            "",
            "",
        ]
    ).encode("utf-8")


async def discover_denon_avrs():
    LOG.debug("Starting discovery")
    res = []

    for ssdp_device in SSDP_DEVICES:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)

        try:
            request = ssdp_request(ssdp_device)
            sock.sendto(request, (MCAST_GRP, MCAST_PORT))

            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    LOG.info("Found SSDP device at %s: %s", addr, data.decode())
                    # TODO pre-filter out known non-Denon devices. Check keys: hue-bridgeid, X-RINCON-HOUSEHOLD
                    # LOG.debug("-"*30)

                    info = await get_denon_info(addr[0])
                    if info:
                        LOG.info("Found Denon device %s", info)
                        res.append(info)
                except socket.timeout:
                    break
        finally:
            sock.close()

    LOG.debug("Discovery finished")
    return res


async def get_denon_info(ipaddress):
    LOG.debug("Trying to get device info for %s", ipaddress)
    d = None

    try:
        d = denonavr.DenonAVR(ipaddress)
    except denonavr.exceptions.DenonAvrError as e:
        LOG.error("[%s] Failed to get device info. Maybe not a Denon device. %s", ipaddress, e)
        return None

    try:
        await d.async_setup()
        await d.async_update()
    except denonavr.exceptions.DenonAvrError as e:
        LOG.error("[%s] Error initializing device: %s", ipaddress, e)
        return None

    return {
        "id": d.serial_number,
        "manufacturer": d.manufacturer,
        "model": d.model_name,
        "name": d.name,
        "ipaddress": ipaddress
    }


class DenonAVR:
    """Representing a Denon AVR Device."""

    def __init__(self, loop, ipaddress):
        """Create instance with given IP address of AVR."""
        self._loop = loop
        self.events = AsyncIOEventEmitter(self._loop)
        self._avr = None
        self.name = ""
        self.model = ""
        self.manufacturer = ""
        self.id = ""
        self.ipaddress = ipaddress
        self.getting_data = False

        self.state = STATES.OFF
        self.volume = 0
        self.input = ""
        self.input_list = []
        self.artist = ""
        self.title = ""
        self.artwork = ""
        self.position = 0
        self.duration = 0

        LOG.debug("Denon AVR created: %s", self.ipaddress)

    @staticmethod
    def map_range(value, from_min, from_max, to_min, to_max):
        return (value - from_min) * (to_max - to_min) / (from_max - from_min) + to_min

    def convert_volume_to_percent(self, value):
        return self.map_range(value, -80.0, 0.0, 0, 100)

    def convert_volume_to_db(self, value):
        return self.map_range(value, 0, 100, -80.0, 0.0)

    @staticmethod
    def extract_values(input_string):
        pattern = r"(\d+:\d+)\s+(\d+%)"
        matches = re.findall(pattern, input_string)

        if matches:
            return matches[0]

        return None

    # TODO ADD METHOD FOR CHANGED IP ADDRESS

    async def connect(self):
        if self._avr is not None:
            LOG.debug("Already connected")
            _ = asyncio.ensure_future(self.get_data())
            return

        try:
            self._avr = denonavr.DenonAVR(self.ipaddress)
            await self._avr.async_setup()
            await self._avr.async_update()
        except denonavr.exceptions.DenonAvrError as e:
            LOG.error("[%s] Error connecting to AVR: %s", self.ipaddress, e)
            self._avr = None
            return

        self.manufacturer = self._avr.manufacturer
        self.model = self._avr.model_name
        self.name = self._avr.name
        self.id = self._avr.serial_number
        LOG.debug("Denon AVR connected. Manufacturer=%s, Model=%s, Name=%s, Id=%s, State=%s",
                  self.manufacturer, self.model, self.name, self.id, self._avr.state)
        await self.subscribe_events()
        self.events.emit(EVENTS.CONNECTED, self.id)

        if self._avr.state == "on":
            self.state = STATES.ON
        elif self._avr.state == "off":
            self.state = STATES.OFF
        elif self._avr.state == "playing":
            self.state = STATES.PLAYING
        elif self._avr.state == "paused":
            self.state = STATES.PAUSED

        self.input_list = self._avr.input_func_list
        self.input = self._avr.input_func
        self.volume = self.convert_volume_to_percent(self._avr.volume)
        self.artist = self._avr.artist
        self.title = self._avr.title
        self.artwork = self._avr.image_url
        self.position = 0
        self.duration = 0

    async def disconnect(self):
        await self.unsubscribe_events()
        self._avr = None
        self.events.emit(EVENTS.DISCONNECTED, self.id)

    async def get_data(self):
        if self.getting_data:
            return

        self.getting_data = True
        LOG.debug("Getting track data.")

        try:
            await self._avr.async_update()
            self.artist = self._avr.artist
            self.title = self._avr.title
            self.artwork = self._avr.image_url

            if self._avr.power == "OFF":
                self.state = STATES.OFF
            else:
                if self._avr.state == "on":
                    self.state = STATES.ON
                elif self._avr.state == "off":
                    self.state = STATES.OFF
                elif self._avr.state == "playing":
                    self.state = STATES.PLAYING
                elif self._avr.state == "paused":
                    self.state = STATES.PAUSED

            self.events.emit(EVENTS.UPDATE, {
                "state": self.state,
                "artist": self.artist,
                "title": self.title,
                "artwork": self.artwork,
            })
            LOG.debug("Track data, artist: " + self.artist + " title: " + self.title + " artwork: " + self.artwork)
        except denonavr.exceptions.DenonAvrError:
            pass

        self.getting_data = False
        LOG.debug("Getting track data done.")

    async def update_callback(self, zone, event, parameter):
        LOG.debug("Zone: " + zone + " Event: " + event + " Parameter: " + parameter)
        try:
            await self._avr.async_update()
        except denonavr.exceptions.DenonAvrError:
            pass

        if event == "MV":
            self.volume = self.convert_volume_to_percent(self._avr.volume)
            self.events.emit(EVENTS.UPDATE, {"volume": self.volume})
        else:
            _ = asyncio.ensure_future(self.get_data())
            # if self.state == STATES.OFF:
            #     self.state = STATES.ON

            # if parameter == "OFF":
            #     self.state = STATES.OFF
        # elif event == "NSE":
        #     _ = asyncio.ensure_future(self.getData())
        # TODO: the duration and position needs more digging
        # if parameter.startswith("5"):
        #     result = self.extract_values(parameter)
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

    async def subscribe_events(self):
        # FIXME #9 add exception handling
        await self._avr.async_telnet_connect()
        await self._avr.async_update()
        self._avr.register_callback("ALL", self.update_callback)
        LOG.debug("Subscribed to events")

    async def unsubscribe_events(self):
        # FIXME #9 add exception handling
        self._avr.unregister_callback("ALL", self.update_callback)
        await self._avr.async_update()
        await self._avr.async_telnet_disconnect()
        LOG.debug("Unsubscribed to events")

    # TODO add commands
    # FIXME #8 command execution check
    async def _command_wrapper(self, fn):
        try:
            await fn()
            return True
        except denonavr.exceptions.DenonAvrError:
            # TODO logging & retry handling
            return False

    async def power_on(self):
        return await self._command_wrapper(self._avr.async_power_on)

    async def power_off(self):
        return await self._command_wrapper(self._avr.async_power_off)

    async def volume_up(self):
        return await self._command_wrapper(self._avr.async_volume_up)

    async def volume_down(self):
        return await self._command_wrapper(self._avr.async_volume_down)

    async def play_pause(self):
        return await self._command_wrapper(self._avr.async_toggle_play_pause)

    async def next(self):
        return await self._command_wrapper(self._avr.async_next_track)

    async def previous(self):
        return await self._command_wrapper(self._avr.async_previous_track)

    async def mute(self, muted):
        try:
            await self._avr.async_mute(muted)
            return True
        except denonavr.exceptions.DenonAvrError:
            return False

    async def set_input(self, input_source):
        try:
            await self._avr.async_set_input_func(input_source)
            return True
        except denonavr.exceptions.DenonAvrError:
            return False
