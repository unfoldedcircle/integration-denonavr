import logging
import asyncio

import socket
import denonavr
import re

from enum import IntEnum
from pyee import AsyncIOEventEmitter

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

MCAST_GRP = '239.255.255.250'
MCAST_PORT = 1900

SSDP_DEVICES = [
    "urn:schemas-upnp-org:device:MediaRenderer:1",
    "urn:schemas-upnp-org:device:MediaServer:1",
    "urn:schemas-denon-com:device:AiosDevice:1"
]

BACKOFF_MAX = 30
BACKOFF_SEC = 2

class EVENTS(IntEnum):
    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 2
    PAIRED = 3
    ERROR = 4
    UPDATE = 5


class STATES(IntEnum):
    OFF = 0
    ON = 1
    PLAYING = 2
    PAUSED = 3


async def discoverDenonAVRs():
    LOG.debug("Starting discovery")
    res = []

    for ssdp_device in SSDP_DEVICES:
        MESSAGE = f'M-SEARCH * HTTP/1.1\r\nHOST: {MCAST_GRP}:{MCAST_PORT}\r\nMAN: "ssdp:discover"\r\nMX: 3\r\nST: {ssdp_device}\r\n\r\n'

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)

        try:
            sock.sendto(MESSAGE.encode(), (MCAST_GRP, MCAST_PORT))

            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    LOG.debug(f"Found SSDP device at {addr}:")
                    LOG.debug(data.decode())
                    LOG.debug("-"*30)

                    info = await getDenonInfo(addr[0])
                    if info:
                        res.append(info);
                except socket.timeout:
                    break
        finally:
            sock.close()

    LOG.debug("Discovery finished")
    return res

async def getDenonInfo(ipaddress):
    LOG.debug("Trying to get device info for " + ipaddress)
    res = {}

    try:
        d = denonavr.DenonAVR(ipaddress)
        await d.async_setup()
        await d.async_update()

        res["id"] = d.serial_number
        res["manufacturer"] = d.manufacturer
        res["model"] = d.model_name
        res["name"] = d.name
        res["ipaddress"] = ipaddress
    except:
        LOG.error("Failed to get device info. Maybe not a Denon device.")

    return res


class DenonAVR(object):
    def __init__(self, loop, ipaddress):
        self._loop = loop
        self.events = AsyncIOEventEmitter(self._loop)
        self._avr = None
        self.name = ""
        self.model = ""
        self.manufacturer = ""
        self.id = ""
        self.ipaddress = ipaddress
        self.gettingData = False

        self.state = STATES.OFF
        self.volume = 0
        self.input = ""
        self.input_list = []
        self.artist = ""
        self.title = ""
        self.artowrk = ""

        LOG.debug("Denon AVR created: " + self.ipaddress)

    def backoff(self):
        if self._connectionAttempts * BACKOFF_SEC >= BACKOFF_MAX:
            return BACKOFF_MAX

        return self._connectionAttempts * BACKOFF_SEC
    
    def mapRange(self, value, from_min, from_max, to_min, to_max):
        return (value - from_min) * (to_max - to_min) / (from_max - from_min) + to_min
    
    def convertVolumeToPercent(self, value):
        return self.mapRange(value, -80.0, 0.0, 0, 100)
    
    def convertVolumeToDb(self, value):
        return self.mapRange(value, 0, 100, -80.0, 0.0)
    
    def extratValues(self, input_string):
        pattern = r'(\d+:\d+)\s+(\d+%)'
        matches = re.findall(pattern, input_string)
        
        if matches:
            return matches[0]
        else:
            return None
    
    # TODO ADD METHOD FOR CHANGED IP ADDRESS

    async def connect(self):
            if self._avr is not None:
                LOG.debug("Already connected")
                _ = asyncio.ensure_future(self.getData())
                return

            self._avr = denonavr.DenonAVR(self.ipaddress)
            await self._avr.async_setup()
            await self._avr.async_update()
            self.manufacturer = self._avr.manufacturer
            self.model = self._avr.model_name
            self.name = self._avr.name
            self.id = self._avr.serial_number
            LOG.debug("Denon AVR connected.")
            LOG.debug("Manufacturer: " + self.manufacturer)
            LOG.debug("Model: " + self.model)
            LOG.debug("Name: " + self.name)
            LOG.debug("Id: " + self.id)
            LOG.debug("State: " + self._avr.state)
            await self.subscribeEvents()
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
            self.volume = self.convertVolumeToPercent(self._avr.volume)
            self.artist = self._avr.artist
            self.title = self._avr.title
            self.artwork = self._avr.image_url
            self.position = 0
            self.duration = 0

    async def disconnect(self):
        await self.unSubscribeEvents()
        self._avr = None
        self.events.emit(EVENTS.DISCONNECTED, self.id)


    async def getData(self):
        if self.gettingData == True:
            return
        
        self.gettingData = True
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
        except:
            pass

        self.gettingData = False
        LOG.debug("Getting track data done.")
    
    async def update_callback(self, zone, event, parameter):
        LOG.debug("Zone: " + zone + " Event: " + event + " Parameter: " + parameter)
        try:
            await self._avr.async_update()
        except:
            pass

        if event == "MV":
            self.volume = self.convertVolumeToPercent(self._avr.volume)
            self.events.emit(EVENTS.UPDATE, {"volume": self.volume})
        else:
            _ = asyncio.ensure_future(self.getData())
            # if self.state == STATES.OFF:
            #     self.state = STATES.ON
            
            # if parameter == "OFF":
            #     self.state = STATES.OFF
        # elif event == "NSE":
        #     _ = asyncio.ensure_future(self.getData())
            # TODO: the duration and position needs more digging
            # if parameter.startswith("5"):
            #     result = self.extratValues(parameter)
            #     if result:
            #         time, percentage = result
            #         hours, minutes = map(int, time.split(':'))
            #         self.duration = hours * 3600 + minutes * 60
            #         self.position = (int(percentage.strip('%')) / 100) * self.duration
            #         self.events.emit(EVENTS.UPDATE, {
            #             "position": self.position,
            #             "total_time": self.duration
            #         })

            #         LOG.debug(f"Time: {self.position}, Percentage: {self.duration}")

    
    async def subscribeEvents(self):
        await self._avr.async_telnet_connect()
        await self._avr.async_update()
        self._avr.register_callback("ALL", self.update_callback)
        LOG.debug("Subscribed to events")

    async def unSubscribeEvents(self):
        self._avr.unregister_callback("ALL", self.update_callback)
        await self._avr.async_update()
        await self._avr.async_telnet_disconnect()
        LOG.debug("Unsubscribed to events")

    # TODO add commands
    async def _commandWrapper(self, fn):   
        try:
            await fn()
            return True
        except:
            return False

    async def powerOn(self):
        return await self._commandWrapper(self._avr.async_power_on)

    async def powerOff(self):
        return await self._commandWrapper(self._avr.async_power_off)
    
    async def volumeUp(self):
        return await self._commandWrapper(self._avr.async_volume_up)
    
    async def volumeDown(self):
        return await self._commandWrapper(self._avr.async_volume_down)
    
    async def playPause(self):
        return await self._commandWrapper(self._avr.async_toggle_play_pause)
    
    async def next(self):
        return await self._commandWrapper(self._avr.async_next_track)
    
    async def previous(self):
        return await self._commandWrapper(self._avr.async_previous_track)
    
    async def mute(self, muted):
        try:
            await self._avr.async_mute(muted)
            return True
        except:
            return False
        
    async def setInput(self, input):
        try:
            await self._avr.async_set_input_func(input)
            return True
        except:
            return False


