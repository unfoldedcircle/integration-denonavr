"""
Media-player entity functions.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
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


SimpleCommandMappings = {
    "OUTPUT_1": "VSMONI1",
    "OUTPUT_2": "VSMONI2",
    "OUTPUT_AUTO": "VSMONIAUTO",

    "DIMMER_TOGGLE": "DIM SEL",
    "DIMMER_BRIGHT": "DIM BRI",
    "DIMMER_DIM": "DIM DIM",
    "DIMMER_DARK": "DIM DAR",
    "DIMMER_OFF": "DIM OFF",

    "TRIGGER1_ON": "TR1 ON",
    "TRIGGER1_OFF": "TR1 OFF",
    "TRIGGER2_ON": "TR2 ON",
    "TRIGGER2_OFF": "TR2 OFF",

    "FRONT_LEFT_UP": "CVFL UP",
    "FRONT_LEFT_DOWN": "CVFL DOWN",
    "FRONT_RIGHT_UP": "CVFR UP",
    "FRONT_RIGHT_DOWN": "CVFR DOWN",

    "CENTER_UP": "CVC UP",
    "CENTER_DOWN": "CVC DOWN",

    "SUB1_UP": "CVSW UP",
    "SUB1_DOWN": "CVSW DOWN",
    "SUB2_UP": "CVSW2 UP",
    "SUB2_DOWN": "CVSW2 DOWN",
    "SUB3_UP": "CVSW3 UP",
    "SUB3_DOWN": "CVSW3 DOWN",
    "SUB4_UP": "CVSW4 UP",
    "SUB4_DOWN": "CVSW4 DOWN",

    "SURROUND_LEFT_UP": "CVSL UP",
    "SURROUND_LEFT_DOWN": "CVSL DOWN",
    "SURROUND_RIGHT_UP": "CVSR UP",
    "SURROUND_RIGHT_DOWN": "CVSR DOWN",

    "SURROUND_BACK_LEFT_UP": "CVSBL UP",
    "SURROUND_BACK_LEFT_DOWN": "CVSBL DOWN",
    "SURROUND_BACK_RIGHT_UP": "CVSBR UP",
    "SURROUND_BACK_RIGHT_DOWN": "CVSBR DOWN",

    "FRONT_HEIGHT_LEFT_UP": "CVFHL UP",
    "FRONT_HEIGHT_LEFT_DOWN": "CVFHL DOWN",
    "FRONT_HEIGHT_RIGHT_UP": "CVFHR UP",
    "FRONT_HEIGHT_RIGHT_DOWN": "CVFHR DOWN",

    "FRONT_WIDE_LEFT_UP": "CVFWL UP",
    "FRONT_WIDE_LEFT_DOWN": "CVFWL DOWN",
    "FRONT_WIDE_RIGHT_UP": "CVFWR UP",
    "FRONT_WIDE_RIGHT_DOWN": "CVFWR DOWN",

    "TOP_FRONT_LEFT_UP": "CVTFL UP",
    "TOP_FRONT_LEFT_DOWN": "CVTFL DOWN",
    "TOP_FRONT_RIGHT_UP": "CVTFR UP",
    "TOP_FRONT_RIGHT_DOWN": "CVTFR DOWN",

    "TOP_MIDDLE_LEFT_UP": "CVTML UP",
    "TOP_MIDDLE_LEFT_DOWN": "CVTML DOWN",
    "TOP_MIDDLE_RIGHT_UP": "CVTMR UP",
    "TOP_MIDDLE_RIGHT_DOWN": "CVTMR DOWN",

    "TOP_REAR_LEFT_UP": "CVTRL UP",
    "TOP_REAR_LEFT_DOWN": "CVTRL DOWN",
    "TOP_REAR_RIGHT_UP": "CVTRR UP",
    "TOP_REAR_RIGHT_DOWN": "CVTRR DOWN",

    "REAR_HEIGHT_LEFT_UP": "CVRHL UP",
    "REAR_HEIGHT_LEFT_DOWN": "CVRHL DOWN",
    "REAR_HEIGHT_RIGHT_UP": "CVRHR UP",
    "REAR_HEIGHT_RIGHT_DOWN": "CVRHR DOWN",

    "FRONT_DOLBY_LEFT_UP": "CVFDL UP",
    "FRONT_DOLBY_LEFT_DOWN": "CVFDL DOWN",
    "FRONT_DOLBY_RIGHT_UP": "CVFDR UP",
    "FRONT_DOLBY_RIGHT_DOWN": "CVFDR DOWN",

    "SURROUND_DOLBY_LEFT_UP": "CVSDL UP",
    "SURROUND_DOLBY_LEFT_DOWN": "CVSDL DOWN",
    "SURROUND_DOLBY_RIGHT_UP": "CVSDR UP",
    "SURROUND_DOLBY_RIGHT_DOWN": "CVSDR DOWN",

    "BACK_DOLBY_LEFT_UP": "CVBDL UP",
    "BACK_DOLBY_LEFT_DOWN": "CVBDL DOWN",
    "BACK_DOLBY_RIGHT_UP": "CVBDR UP",
    "BACK_DOLBY_RIGHT_DOWN": "CVBDR DOWN",

    "SURROUND_HEIGHT_LEFT_UP": "CVSHL UP",
    "SURROUND_HEIGHT_LEFT_DOWN": "CVSHL DOWN",
    "SURROUND_HEIGHT_RIGHT_UP": "CVSHR UP",
    "SURROUND_HEIGHT_RIGHT_DOWN": "CVSHR DOWN",

    "TOP_SURROUND_UP": "CVTS UP",
    "TOP_SURROUND_DOWN": "CVTS DOWN",

    "CENTER_HEIGHT_UP": "CVCH UP",
    "CENTER_HEIGHT_DOWN": "CVCH DOWN",

    "DELAY_UP": "PSDELAY UP",
    "DELAY_DOWN": "PSDELAY DOWN",

    "SURROUND_MODE_AUTO": "MSAUTO",
    "SURROUND_MODE_DIRECT": "MSDIRECT",
    "SURROUND_MODE_PURE_DIRECT": "MSPURE DIRECT",
    "SURROUND_MODE_DOLBY_DIGITAL": "MSDOLBY DIGITAL",
    "SURROUND_MODE_DTS_SURROUND": "MSDTS SURROUND",
    "SURROUND_MODE_AURO3D": "MSAURO3D",
    "SURROUND_MODE_AURO2DSURR": "MSAURO2DSURR",
    "SURROUND_MODE_MCH_STEREO": "MSMCH STEREO",
    "SURROUND_MODE_NEXT": "MSLEFT",
    "SURROUND_MODE_PREVIOUS": "MSRIGHT",

    "MULTIEQ_REFERENCE": "PSMULTEQ:AUDYSSEY",
    "MULTIEQ_BYPASS_LR": "MULTEQ:BYP.LR",
    "MULTIEQ_FLAT": "PSMULTEQ:FLAT",
    "MULTIEQ_OFF": "PSMULTEQ:OFF",

    "DYNAMIC_EQ_ON": "PSDYNEQ ON",
    "DYNAMIC_EQ_OFF": "PSDYNEQ OFF",

    "AUDYSSEY_LFC": "PSLFC ON",
    "AUDYSSEY_LFC_OFF": "PSLFC OFF",

    "DIRAC_LIVE_FILTER_SLOT1": "PSDIRAC 1",
    "DIRAC_LIVE_FILTER_SLOT2": "PSDIRAC 2",
    "DIRAC_LIVE_FILTER_SLOT3": "PSDIRAC 3",
    "DIRAC_LIVE_FILTER_OFF": "PSDIRAC OFF",

    "ECO_ON": "ECOON",
    "ECO_AUTO": "ECOAUTO",
    "ECO_OFF": "ECOOFF",
}


class DenonMediaPlayer(MediaPlayer):
    """Representation of a Denon Media Player entity."""

    def __init__(self, device: AvrDevice, receiver: avr.DenonDevice):
        """Initialize the class."""
        self._receiver: avr.DenonDevice = receiver

        entity_id = create_entity_id(receiver.id, EntityTypes.MEDIA_PLAYER)
        features = [
            Features.ON_OFF,
            Features.TOGGLE,
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

        self.simple_commands = [*SimpleCommandMappings]

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
            case Commands.TOGGLE:
                res = await self._receiver.power_toggle()
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
            case cmd if cmd in SimpleCommandMappings:
                res = await self._receiver.send_command(SimpleCommandMappings[cmd])
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
