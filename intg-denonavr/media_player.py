"""
Media-player entity functions.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from enum import Enum
from typing import Any

import avr
from config import AvrDevice, create_entity_id
from ucapi import EntityTypes, MediaPlayer, StatusCodes
from ucapi.media_player import (
    Attributes,
    Commands,
    DeviceClasses,
    Features,
    Options,
    States,
)

_LOG = logging.getLogger(__name__)

# Mapping of an AVR state to a media-player entity state
MEDIA_PLAYER_STATE_MAPPING = {
    avr.States.ON: States.ON,
    avr.States.OFF: States.OFF,
    avr.States.PAUSED: States.PAUSED,
    avr.States.PLAYING: States.PLAYING,
    avr.States.UNAVAILABLE: States.UNAVAILABLE,
    avr.States.UNKNOWN: States.UNKNOWN,
}


class SimpleCommands(str, Enum):
    """Additional simple commands of the Denon AVR not covered by media-player features."""

    OUTPUT_1 = "OUTPUT_1"
    """Set HDMI monitor out 1."""
    OUTPUT_2 = "OUTPUT_2"
    """Set HDMI monitor out 2."""
    OUTPUT_AUTO = "OUTPUT_AUTO"
    """Set HDMI monitor automatic detection."""


class DenonMediaPlayer(MediaPlayer):
    """Representation of a Denon Media Player entity."""

    def __init__(self, device: AvrDevice, receiver: avr.DenonDevice):
        """Initialize the class."""
        self._receiver: avr.DenonDevice = receiver

        entity_id = create_entity_id(receiver.id, EntityTypes.MEDIA_PLAYER)
        features = [
            Features.ON_OFF,
            Features.VOLUME,
            Features.VOLUME_UP_DOWN,
            Features.MUTE_TOGGLE,
            Features.PLAY_PAUSE,
            Features.NEXT,
            Features.PREVIOUS,
            Features.MEDIA_TITLE,
            Features.MEDIA_ARTIST,
            Features.MEDIA_ALBUM,
            Features.MEDIA_IMAGE_URL,
            Features.MEDIA_TYPE,
            Features.SELECT_SOURCE,
            Features.DPAD,
            Features.MENU,
            Features.CONTEXT_MENU,
            Features.INFO,
        ]
        attributes = {
            Attributes.STATE: States.UNAVAILABLE,
            Attributes.VOLUME: 0,
            Attributes.MUTED: False,
            Attributes.MEDIA_IMAGE_URL: "",
            Attributes.MEDIA_TITLE: "",
            Attributes.MEDIA_ARTIST: "",
            Attributes.MEDIA_ALBUM: "",
            Attributes.SOURCE: "",
            Attributes.SOURCE_LIST: [],
        }
        # use sound mode support & name from configuration: receiver might not yet be connected
        if device.support_sound_mode:
            features.append(Features.SELECT_SOUND_MODE)
            attributes[Attributes.SOUND_MODE] = ""
            attributes[Attributes.SOUND_MODE_LIST] = []

        self.simple_commands = [
            SimpleCommands.OUTPUT_1.value,
            SimpleCommands.OUTPUT_2.value,
            SimpleCommands.OUTPUT_AUTO.value,
        ]

        options = {Options.SIMPLE_COMMANDS: self.simple_commands}

        super().__init__(
            entity_id,
            device.name,
            features,
            attributes,
            device_class=DeviceClasses.RECEIVER,
            options=options,
        )

    async def command(self, cmd_id: str, params: dict[str, Any] | None = None) -> StatusCodes:
        """
        Media-player entity command handler.

        Called by the integration-API if a command is sent to a configured media-player entity.

        :param cmd_id: command
        :param params: optional command parameters
        :return: status code of the command request
        """
        _LOG.info("Got %s command request: %s %s", self.id, cmd_id, params)

        if self._receiver is None:
            _LOG.warning("No AVR instance for entity: %s", self.id)
            return StatusCodes.SERVICE_UNAVAILABLE

        match cmd_id:
            case Commands.PLAY_PAUSE:
                res = await self._receiver.play_pause()
            case Commands.NEXT:
                res = await self._receiver.next()
            case Commands.PREVIOUS:
                res = await self._receiver.previous()
            case Commands.VOLUME:
                res = await self._receiver.set_volume_level(params.get("volume"))
            case Commands.VOLUME_UP:
                res = await self._receiver.volume_up()
            case Commands.VOLUME_DOWN:
                res = await self._receiver.volume_down()
            case Commands.MUTE_TOGGLE:
                res = await self._receiver.mute(not self.attributes[Attributes.MUTED])
            case Commands.ON:
                res = await self._receiver.power_on()
            case Commands.OFF:
                res = await self._receiver.power_off()
            case Commands.SELECT_SOURCE:
                res = await self._receiver.select_source(params.get("source"))
            case Commands.SELECT_SOUND_MODE:
                res = await self._receiver.select_sound_mode(params.get("mode"))
            case Commands.CURSOR_UP:
                res = await self._receiver.cursor_up()
            case Commands.CURSOR_DOWN:
                res = await self._receiver.cursor_down()
            case Commands.CURSOR_LEFT:
                res = await self._receiver.cursor_left()
            case Commands.CURSOR_RIGHT:
                res = await self._receiver.cursor_right()
            case Commands.CURSOR_ENTER:
                res = await self._receiver.cursor_enter()
            case Commands.BACK:
                res = await self._receiver.back()
            case Commands.MENU:
                res = await self._receiver.setup()
            case Commands.CONTEXT_MENU:
                res = await self._receiver.options()
            case Commands.INFO:
                res = await self._receiver.info()
            case SimpleCommands.OUTPUT_1:
                res = await self._receiver.output_monitor_1()
            case SimpleCommands.OUTPUT_2:
                res = await self._receiver.output_monitor_2()
            case SimpleCommands.OUTPUT_AUTO:
                res = await self._receiver.output_monitor_auto()
            case _:
                return StatusCodes.NOT_IMPLEMENTED

        return res

    def filter_changed_attributes(self, update: dict[str, Any]) -> dict[str, Any]:
        """
        Filter the given attributes and return only the changed values.

        :param update: dictionary with attributes.
        :return: filtered entity attributes containing changed attributes only.
        """
        attributes = {}

        if Attributes.STATE in update:
            state = state_from_avr(update[Attributes.STATE])
            attributes = self._key_update_helper(Attributes.STATE, state, attributes)

        for attr in [
            Attributes.MEDIA_ARTIST,
            Attributes.MEDIA_ALBUM,
            Attributes.MEDIA_IMAGE_URL,
            Attributes.MEDIA_TITLE,
            Attributes.MUTED,
            Attributes.SOURCE,
            Attributes.VOLUME,
        ]:
            if attr in update:
                attributes = self._key_update_helper(attr, update[attr], attributes)

        if Attributes.SOURCE_LIST in update:
            if Attributes.SOURCE_LIST in self.attributes:
                if update[Attributes.SOURCE_LIST] != self.attributes[Attributes.SOURCE_LIST]:
                    attributes[Attributes.SOURCE_LIST] = update[Attributes.SOURCE_LIST]

        if Features.SELECT_SOUND_MODE in self.features:
            if Attributes.SOUND_MODE in update:
                attributes = self._key_update_helper(Attributes.SOUND_MODE, update[Attributes.SOUND_MODE], attributes)
            if Attributes.SOUND_MODE_LIST in update:
                if Attributes.SOUND_MODE_LIST in self.attributes:
                    if update[Attributes.SOUND_MODE_LIST] != self.attributes[Attributes.SOUND_MODE_LIST]:
                        attributes[Attributes.SOUND_MODE_LIST] = update[Attributes.SOUND_MODE_LIST]

        if Attributes.STATE in attributes:
            if attributes[Attributes.STATE] == States.OFF:
                attributes[Attributes.MEDIA_IMAGE_URL] = ""
                attributes[Attributes.MEDIA_ALBUM] = ""
                attributes[Attributes.MEDIA_ARTIST] = ""
                attributes[Attributes.MEDIA_TITLE] = ""
                attributes[Attributes.MEDIA_TYPE] = ""
                attributes[Attributes.SOURCE] = ""

        return attributes

    def _key_update_helper(self, key: str, value: str | None, attributes):
        if value is None:
            return attributes

        if key in self.attributes:
            if self.attributes[key] != value:
                attributes[key] = value
        else:
            attributes[key] = value

        return attributes


def state_from_avr(avr_state: avr.States) -> States:
    """
    Convert AVR state to UC API media-player state.

    :param avr_state: Denon AVR state
    :return: UC API media_player state
    """
    if avr_state in MEDIA_PLAYER_STATE_MAPPING:
        return MEDIA_PLAYER_STATE_MAPPING[avr_state]
    return States.UNKNOWN
