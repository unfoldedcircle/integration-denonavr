"""
Media-player entity functions.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from typing import Any

import avr
import helpers
import simplecommand
from config import AvrDevice, create_entity_id
from entities import DenonEntity
from ucapi import EntityTypes, IntegrationAPI, MediaPlayer, StatusCodes
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


class DenonMediaPlayer(MediaPlayer, DenonEntity):
    """Representation of a Denon/Marantz Media Player entity."""

    def __init__(self, device: AvrDevice, receiver: avr.DenonDevice, api: IntegrationAPI):
        """Initialize the class."""
        self._receiver: avr.DenonDevice = receiver
        self._device: AvrDevice = device
        entity_id = create_entity_id(receiver.id, EntityTypes.MEDIA_PLAYER)
        features = [
            Features.ON_OFF,
            Features.TOGGLE,
            Features.VOLUME,
            Features.VOLUME_UP_DOWN,
            Features.MUTE_TOGGLE,
            Features.MUTE,
            Features.UNMUTE,
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
            Features.CHANNEL_SWITCHER,
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

        self.simple_commands = simplecommand.get_simple_commands(device)
        # Denon has additional simple commands
        if device.is_denon:
            features.append(Features.STOP)

        options = {Options.SIMPLE_COMMANDS: self.simple_commands}

        super().__init__(
            entity_id,
            device.name,
            features,
            attributes,
            device_class=DeviceClasses.RECEIVER,
            options=options,
        )
        DenonEntity.__init__(self, api)

    async def command(self, cmd_id: str, params: dict[str, Any] | None = None, *, websocket: Any) -> StatusCodes:
        """
        Media-player entity command handler.

        Called by the integration-API if a command is sent to a configured media-player entity.

        :param cmd_id: command
        :param params: optional command parameters
        :param websocket: websocket connection (not used)
        :return: status code of the command request
        """
        # pylint: disable=R0911
        _LOG.info("Got %s command request: %s %s", self.id, cmd_id, params)

        if self._receiver is None:
            _LOG.warning("No AVR instance for entity: %s", self.id)
            return StatusCodes.SERVICE_UNAVAILABLE

        match cmd_id:
            case Commands.PLAY_PAUSE:
                return await self._receiver.play_pause()
            case Commands.STOP:
                return await self._receiver.stop()
            case Commands.NEXT:
                return await self._receiver.next()
            case Commands.PREVIOUS:
                return await self._receiver.previous()
            case Commands.VOLUME:
                return await self._receiver.set_volume_level(params.get("volume"))
            case Commands.VOLUME_UP:
                return await self._receiver.volume_up()
            case Commands.VOLUME_DOWN:
                return await self._receiver.volume_down()
            case Commands.MUTE_TOGGLE:
                return await self._receiver.mute(not self.attributes[Attributes.MUTED])
            case Commands.MUTE:
                return await self._receiver.mute(True)
            case Commands.UNMUTE:
                return await self._receiver.mute(False)
            case Commands.ON:
                return await self._receiver.power_on()
            case Commands.OFF:
                return await self._receiver.power_off()
            case Commands.TOGGLE:
                return await self._receiver.power_toggle()
            case Commands.SELECT_SOURCE:
                return await self._receiver.select_source(params.get("source"))
            case Commands.SELECT_SOUND_MODE:
                return await self._receiver.select_sound_mode(params.get("mode"))
            case Commands.CURSOR_UP:
                return await self._receiver.cursor_up()
            case Commands.CURSOR_DOWN:
                return await self._receiver.cursor_down()
            case Commands.CURSOR_LEFT:
                return await self._receiver.cursor_left()
            case Commands.CURSOR_RIGHT:
                return await self._receiver.cursor_right()
            case Commands.CURSOR_ENTER:
                return await self._receiver.cursor_enter()
            case Commands.BACK:
                return await self._receiver.back()
            case Commands.MENU:
                return await self._receiver.setup()
            case Commands.CONTEXT_MENU:
                return await self._receiver.options()
            case Commands.INFO:
                return await self._receiver.info()
            case Commands.CHANNEL_UP:
                return await self._receiver.channel_up()
            case Commands.CHANNEL_DOWN:
                return await self._receiver.channel_down()
            case _:
                return await self._receiver.send_simple_command(cmd_id)

    def get_supported_commands(self, include_power_state_commands: bool) -> list[str]:
        """
        Get the list of supported commands for this media-player entity.

        :param include_power_state_commands: Includes power state commands (on, off, toggle) if True.
        :return: list of supported commands.
        """
        power_state_commands = [Commands.ON, Commands.OFF, Commands.TOGGLE] if include_power_state_commands else []
        return [
            Commands.PLAY_PAUSE,
            Commands.STOP,
            Commands.NEXT,
            Commands.PREVIOUS,
            Commands.VOLUME,
            Commands.VOLUME_UP,
            Commands.VOLUME_DOWN,
            Commands.MUTE_TOGGLE,
            Commands.MUTE,
            Commands.UNMUTE,
            Commands.SELECT_SOURCE,
            Commands.SELECT_SOUND_MODE,
            Commands.CURSOR_UP,
            Commands.CURSOR_DOWN,
            Commands.CURSOR_LEFT,
            Commands.CURSOR_RIGHT,
            Commands.CURSOR_ENTER,
            Commands.BACK,
            Commands.MENU,
            Commands.CONTEXT_MENU,
            Commands.INFO,
            *power_state_commands,
            *simplecommand.get_simple_commands(self._device),
        ]

    def filter_changed_attributes(self, update: dict[str, Any]) -> dict[str, Any]:
        """
        Filter the given attributes and return only the changed values.

        :param update: dictionary with attributes.
        :return: filtered entity attributes containing changed attributes only.
        """
        attributes = {}

        if Attributes.STATE in update:
            state = self.state_from_avr(update[Attributes.STATE])
            attributes = helpers.key_update_helper(Attributes.STATE, state, attributes, self.attributes)

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
                attributes = helpers.key_update_helper(attr, update[attr], attributes, self.attributes)

        if Attributes.SOURCE_LIST in update:
            if Attributes.SOURCE_LIST in self.attributes:
                if update[Attributes.SOURCE_LIST] != self.attributes[Attributes.SOURCE_LIST]:
                    attributes[Attributes.SOURCE_LIST] = update[Attributes.SOURCE_LIST]

        if Features.SELECT_SOUND_MODE in self.features:
            if Attributes.SOUND_MODE in update:
                attributes = helpers.key_update_helper(
                    Attributes.SOUND_MODE, update[Attributes.SOUND_MODE], attributes, self.attributes
                )
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

    def state_from_avr(self, avr_state: avr.States) -> States:
        """
        Convert AVR state to UC API media-player state.

        :param avr_state: Denon/Marantz AVR state
        :return: UC API media_player state
        """
        if avr_state in MEDIA_PLAYER_STATE_MAPPING:
            return MEDIA_PLAYER_STATE_MAPPING[avr_state]
        return States.UNKNOWN
