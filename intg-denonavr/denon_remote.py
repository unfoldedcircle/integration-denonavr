"""
Remote entity functions.

:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from typing import Any, cast

from typing_extensions import override
from ucapi import EntityTypes, IntegrationAPI, Remote, StatusCodes, media_player
import ucapi.remote
from ucapi.remote import Attributes, Commands, Features
from ucapi.ui import Buttons, DeviceButtonMapping, UiPage

import avr
from command_constants import (
    AudysseyCommands,
    CoreCommands,
    DiracCommands,
    PictureModeCommands,
    SoundModeCommands,
    TunerCommands,
    VolumeCommands,
)
from config import AvrDevice, create_entity_id
from entities import DenonEntity
import helpers
from media_player import DenonMediaPlayer

# Mapping of an AVR state to a remote entity state
REMOTE_STATE_MAPPING = {
    avr.States.ON: ucapi.remote.States.ON,
    avr.States.OFF: ucapi.remote.States.OFF,
    avr.States.PAUSED: ucapi.remote.States.ON,
    avr.States.PLAYING: ucapi.remote.States.ON,
    avr.States.UNAVAILABLE: ucapi.remote.States.UNAVAILABLE,
    avr.States.UNKNOWN: ucapi.remote.States.UNKNOWN,
}

_LOG = logging.getLogger("denon_remote")  # avoid having __main__ in log messages


class DenonRemote(Remote, DenonEntity):
    """Representation of a Denon/Marantz AVR Remote entity."""

    def __init__(
        self, device: AvrDevice, receiver: avr.DenonDevice, denon_media_player: DenonMediaPlayer, api: IntegrationAPI
    ):
        """Initialize the class."""
        self._device: avr.DenonDevice = receiver
        self._denon_media_player: DenonMediaPlayer = denon_media_player
        entity_id = create_entity_id(receiver.id, EntityTypes.REMOTE)
        features = [Features.SEND_CMD, Features.ON_OFF, Features.TOGGLE]
        super().__init__(
            entity_id,
            f"{device.name} Remote",
            features,
            attributes={
                Attributes.STATE: receiver.state,
            },
            simple_commands=self._denon_media_player.get_supported_commands(include_power_state_commands=False),
            button_mapping=cast("list[DeviceButtonMapping | dict[str, Any]] | None", REMOTE_BUTTONS_MAPPING),
            ui_pages=cast(
                "list[UiPage | dict[str, Any]] | None",
                DenonRemote._get_remote_ui_pages(is_denon=device.is_denon),
            ),
        )
        DenonEntity.__init__(self, api)

    @override
    async def command(self, cmd_id: str, params: dict[str, Any] | None = None, *, websocket: Any) -> StatusCodes:
        """
        Remote entity command handler.

        Called by the integration-API if a command is sent to a configured remote entity.

        :param cmd_id: command
        :param params: optional command parameters
        :param websocket: websocket connection (not used)
        :return: status code of the command request
        """
        match cmd_id:
            case Commands.ON:
                return await self._denon_media_player.command(Commands.ON, websocket=websocket)
            case Commands.OFF:
                return await self._denon_media_player.command(Commands.OFF, websocket=websocket)
            case Commands.TOGGLE:
                return await self._denon_media_player.command(Commands.TOGGLE, websocket=websocket)
            case _:
                pass

        if cmd_id.startswith("remote."):
            _LOG.error("Command %s is not allowed.", cmd_id)
            return StatusCodes.BAD_REQUEST

        if params is None:
            return StatusCodes.BAD_REQUEST

        if params:
            repeat = self._get_int_param("repeat", params, 1)
            # temporary hack for hold-down buttons sending a repeat count.
            # This will be addressed with the upcoming press-and-hold feature.
            if repeat < 1 or repeat == 4:
                repeat = 1
            elif repeat > 20:
                repeat = 20
        else:
            repeat = 1

        if cmd_id == Commands.SEND_CMD:
            command_or_status = self._get_command_or_status_code(cmd_id, params.get("command", ""))
            if isinstance(command_or_status, StatusCodes):
                return command_or_status

            success = True
            for _ in range(repeat):
                success &= (
                    await self._denon_media_player.command(command_or_status, websocket=websocket) == StatusCodes.OK
                )

            if success:
                return StatusCodes.OK
            return StatusCodes.BAD_REQUEST

        if cmd_id == Commands.SEND_CMD_SEQUENCE:
            success = True
            for command in params.get("sequence", []):
                for _ in range(repeat):
                    command_or_status = self._get_command_or_status_code(cmd_id, command)
                    if isinstance(command_or_status, StatusCodes):
                        success = False
                    else:
                        res = await self._denon_media_player.command(command_or_status, websocket=websocket)
                        if res != StatusCodes.OK:
                            success = False
            if success:
                return StatusCodes.OK
            return StatusCodes.BAD_REQUEST

        # send "raw" commands as is to the receiver
        return await self._denon_media_player.command(cmd_id, websocket=websocket)

    @override
    def state_from_avr(self, avr_state: avr.States) -> ucapi.remote.States:
        """
        Convert AVR state to UC API remote state.

        :param avr_state: Denon/Marantz AVR state
        :return: UC API remote state
        """
        if avr_state in REMOTE_STATE_MAPPING:
            return REMOTE_STATE_MAPPING[avr_state]
        return ucapi.remote.States.UNKNOWN

    @override
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

        return attributes

    @staticmethod
    def _get_command_or_status_code(cmd_id: str, command: str) -> str | StatusCodes:
        if not command:
            _LOG.error("Command parameter is missing for cmd_id %s", cmd_id)
            return StatusCodes.BAD_REQUEST
        if command.startswith("remote."):
            _LOG.error("Command %s is not allowed for cmd_id %s.", command, cmd_id)
            return StatusCodes.BAD_REQUEST
        return command

    @staticmethod
    def _get_int_param(param: str, params: dict[str, Any], default: int) -> int:
        try:
            value = params.get(param, default)
        except AttributeError:
            return default

        if isinstance(value, str) and len(value) > 0:
            return int(float(value))

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value)

        return default

    @staticmethod
    def _get_remote_ui_pages(*, is_denon: bool):
        return [
            DenonRemote._get_main_page(),
            DenonRemote._get_sound_modes_page(),
            DenonRemote._get_sound_tweaks_page(),
            DenonRemote._get_standby_page(),
            DenonRemote._get_triggers_page(),
            DenonRemote._get_dirac_page(),
            DenonRemote._get_audyssey_page(),
            DenonRemote._get_channel_levels_page(),
            DenonRemote._get_eco_page(),
            DenonRemote._get_inputs_page(),
            DenonRemote._get_quick_select_page(is_denon=is_denon),
            DenonRemote._get_tuner_page(),
            DenonRemote._get_picture_mode_page(),
            DenonRemote._get_sleep_timer_page(),
            DenonRemote._get_zone_favorites_page(),
        ]

    @staticmethod
    def _get_main_page():
        return {
            "page_id": "denon_avr_commands_main",
            "name": "Main",
            "grid": {"width": 4, "height": 7},
            "items": [
                {
                    "command": {"cmd_id": CoreCommands.SPEAKER_PRESET_1},
                    "location": {"x": 0, "y": 0},
                    "size": {"height": 1, "width": 2},
                    "text": "Speaker Preset 1",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.SPEAKER_PRESET_1},
                    "location": {"x": 2, "y": 0},
                    "size": {"height": 1, "width": 2},
                    "text": "Speaker Preset 2",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.OUTPUT_AUTO},
                    "location": {"x": 0, "y": 1},
                    "size": {"height": 1, "width": 2},
                    "text": "HDMI Auto",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.OUTPUT_1},
                    "location": {"x": 0, "y": 2},
                    "size": {"height": 1, "width": 2},
                    "text": "HDMI 1",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.OUTPUT_2},
                    "location": {"x": 2, "y": 2},
                    "size": {"height": 1, "width": 2},
                    "text": "HDMI 2",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.DELAY_DOWN},
                    "text": "Delay Down",
                    "location": {"x": 0, "y": 4},
                    "size": {"height": 1, "width": 2},
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.DELAY_UP},
                    "text": "Delay Up",
                    "location": {"x": 2, "y": 4},
                    "size": {"height": 1, "width": 2},
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.DIMMER_OFF},
                    "text": "Dimmer Off",
                    "location": {"x": 0, "y": 5},
                    "size": {"height": 1, "width": 2},
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.DIMMER_BRIGHT},
                    "text": "Dimmer On",
                    "location": {"x": 2, "y": 5},
                    "size": {"height": 1, "width": 2},
                    "type": "text",
                },
                {
                    "command": {"cmd_id": media_player.Commands.CONTEXT_MENU},
                    "location": {"x": 0, "y": 6},
                    "size": {"height": 1, "width": 1},
                    "text": "Option",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": media_player.Commands.MENU},
                    "location": {"x": 1, "y": 6},
                    "size": {"height": 1, "width": 2},
                    "text": "Setup",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": media_player.Commands.INFO},
                    "location": {"x": 3, "y": 6},
                    "size": {"height": 1, "width": 1},
                    "text": "Info",
                    "type": "text",
                },
            ],
        }

    @staticmethod
    def _get_sound_modes_page():
        return {
            "page_id": "denon_avr_commands_sound_modes",
            "name": "Sound Modes",
            "grid": {"height": 8, "width": 4},
            "items": [
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_MODE_AUTO},
                    "location": {"x": 0, "y": 0},
                    "size": {"height": 1, "width": 2},
                    "text": "Auto",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_MODE_DOLBY_DIGITAL},
                    "location": {"x": 2, "y": 0},
                    "size": {"height": 1, "width": 2},
                    "text": "Dolby Digital",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_MODE_DIRECT},
                    "location": {"x": 0, "y": 1},
                    "size": {"height": 1, "width": 2},
                    "text": "Direct",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_MODE_DTS_SURROUND},
                    "location": {"x": 2, "y": 1},
                    "size": {"height": 1, "width": 2},
                    "text": "DTS",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_MODE_PURE_DIRECT},
                    "location": {"x": 0, "y": 2},
                    "size": {"height": 1, "width": 2},
                    "text": "Pure Direct",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_MODE_AURO3D},
                    "location": {"x": 2, "y": 2},
                    "size": {"height": 1, "width": 2},
                    "text": "Auro-3D",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_MODE_MCH_STEREO},
                    "location": {"x": 0, "y": 3},
                    "size": {"height": 1, "width": 2},
                    "text": "MCH Stereo",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_MODE_AURO2DSURR},
                    "location": {"x": 2, "y": 3},
                    "size": {"height": 1, "width": 2},
                    "text": "Auro-2D Surr",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_MODE_DOLBY_SURROUND},
                    "location": {"x": 0, "y": 4},
                    "size": {"height": 1, "width": 2},
                    "text": "Dolby Surround",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_MODE_NEURAL_X},
                    "location": {"x": 2, "y": 4},
                    "size": {"height": 1, "width": 2},
                    "text": "Neural:X",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_MODE_MULTI_CH_IN},
                    "location": {"x": 0, "y": 5},
                    "size": {"height": 1, "width": 2},
                    "text": "Multi CH In",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_MODE_STEREO},
                    "location": {"x": 2, "y": 5},
                    "size": {"height": 1, "width": 2},
                    "text": "Stereo",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SOUND_MODE_IMAX_AUTO},
                    "location": {"x": 0, "y": 6},
                    "size": {"height": 1, "width": 2},
                    "text": "IMAX Auto",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SOUND_MODE_IMAX_OFF},
                    "location": {"x": 2, "y": 6},
                    "size": {"height": 1, "width": 2},
                    "text": "IMAX Off",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_MODE_PREVIOUS},
                    "location": {"x": 0, "y": 7},
                    "size": {"height": 1, "width": 2},
                    "text": "Previous",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_MODE_NEXT},
                    "location": {"x": 2, "y": 7},
                    "size": {"height": 1, "width": 2},
                    "text": "Next",
                    "type": "text",
                },
            ],
        }

    @staticmethod
    def _get_standby_page():
        return {
            "page_id": "denon_avr_commands_standby",
            "name": "Standby",
            "grid": {"height": 4, "width": 1},
            "items": [
                {
                    "command": {"cmd_id": CoreCommands.AUTO_STANDBY_OFF},
                    "location": {"x": 0, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "Auto Standby Off",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.AUTO_STANDBY_15MIN},
                    "location": {"x": 0, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "Auto Standby 15min",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.AUTO_STANDBY_15MIN},
                    "location": {"x": 0, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "Auto Standby 30min",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.AUTO_STANDBY_60MIN},
                    "location": {"x": 0, "y": 3},
                    "size": {"height": 1, "width": 1},
                    "text": "Auto Standby 60min",
                    "type": "text",
                },
            ],
        }

    @staticmethod
    def _get_triggers_page():
        return {
            "page_id": "denon_avr_commands_triggers",
            "name": "Triggers",
            "grid": {"height": 3, "width": 2},
            "items": [
                {
                    "command": {"cmd_id": CoreCommands.TRIGGER1_OFF},
                    "location": {"x": 0, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "Trigger 1 Off",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.TRIGGER1_ON},
                    "location": {"x": 1, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "Trigger 1 On",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.TRIGGER2_OFF},
                    "location": {"x": 0, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "Trigger 2 Off",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.TRIGGER2_ON},
                    "location": {"x": 1, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "Trigger 2 On",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.TRIGGER3_OFF},
                    "location": {"x": 0, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "Trigger 3 Off",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.TRIGGER3_ON},
                    "location": {"x": 1, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "Trigger 3 On",
                    "type": "text",
                },
            ],
        }

    @staticmethod
    def _get_dirac_page():
        return {
            "page_id": "denon_avr_commands_dirac",
            "name": "Dirac",
            "grid": {"height": 4, "width": 1},
            "items": [
                {
                    "command": {"cmd_id": DiracCommands.DIRAC_LIVE_FILTER_SLOT1},
                    "location": {"x": 0, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "Dirac Slot 1",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": DiracCommands.DIRAC_LIVE_FILTER_SLOT2},
                    "location": {"x": 0, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "Dirac Slot 2",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": DiracCommands.DIRAC_LIVE_FILTER_SLOT3},
                    "location": {"x": 0, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "Dirac Slot 3",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": DiracCommands.DIRAC_LIVE_FILTER_OFF},
                    "location": {"x": 0, "y": 3},
                    "size": {"height": 1, "width": 1},
                    "text": "Dirac Off",
                    "type": "text",
                },
            ],
        }

    @staticmethod
    def _get_audyssey_page():
        return {
            "page_id": "denon_avr_commands_audyssey",
            "name": "Audyssey",
            "grid": {"height": 7, "width": 2},
            "items": [
                {
                    "command": {"cmd_id": AudysseyCommands.MULTIEQ_REFERENCE},
                    "location": {"x": 0, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "MultiEQ Reference",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": AudysseyCommands.MULTIEQ_BYPASS_LR},
                    "location": {"x": 1, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "MultiEQ Bypass LR",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": AudysseyCommands.MULTIEQ_FLAT},
                    "location": {"x": 0, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "MultiEQ Flat",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": AudysseyCommands.MULTIEQ_OFF},
                    "location": {"x": 1, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "MultiEQ Off",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": AudysseyCommands.DYNAMIC_EQ_OFF},
                    "location": {"x": 0, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "Dynamic EQ Off",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": AudysseyCommands.DYNAMIC_EQ_ON},
                    "location": {"x": 1, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "Dynamic EQ On",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": AudysseyCommands.AUDYSSEY_LFC_OFF},
                    "location": {"x": 0, "y": 3},
                    "size": {"height": 1, "width": 1},
                    "text": "LFC Off",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": AudysseyCommands.AUDYSSEY_LFC},
                    "location": {"x": 1, "y": 3},
                    "size": {"height": 1, "width": 1},
                    "text": "LFC On",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": AudysseyCommands.DYNAMIC_VOLUME_OFF},
                    "location": {"x": 0, "y": 4},
                    "size": {"height": 1, "width": 1},
                    "text": "Dyn. Vol. Off",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": AudysseyCommands.DYNAMIC_VOLUME_LIGHT},
                    "location": {"x": 1, "y": 4},
                    "size": {"height": 1, "width": 1},
                    "text": "Dyn. Vol. Light",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": AudysseyCommands.DYNAMIC_VOLUME_MEDIUM},
                    "location": {"x": 0, "y": 5},
                    "size": {"height": 1, "width": 1},
                    "text": "Dyn. Vol. Medium",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": AudysseyCommands.DYNAMIC_VOLUME_HEAVY},
                    "location": {"x": 1, "y": 5},
                    "size": {"height": 1, "width": 1},
                    "text": "Dyn. Vol. Heavy",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": AudysseyCommands.CONTAINMENT_AMOUNT_DOWN},
                    "location": {"x": 0, "y": 6},
                    "size": {"height": 1, "width": 1},
                    "text": "Containment Down",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": AudysseyCommands.CONTAINMENT_AMOUNT_UP},
                    "location": {"x": 1, "y": 6},
                    "size": {"height": 1, "width": 1},
                    "text": "Containment Up",
                    "type": "text",
                },
            ],
        }

    @staticmethod
    def _get_channel_levels_page():
        return {
            "page_id": "denon_avr_commands_channel_levels",
            "name": "Channel Levels",
            "grid": {"height": 9, "width": 2},
            "items": [
                {
                    "command": {"cmd_id": VolumeCommands.FRONT_LEFT_DOWN},
                    "location": {"x": 0, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "Front L Down",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": VolumeCommands.FRONT_LEFT_UP},
                    "location": {"x": 1, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "Front L Up",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": VolumeCommands.FRONT_RIGHT_DOWN},
                    "location": {"x": 0, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "Front R Down",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": VolumeCommands.FRONT_RIGHT_UP},
                    "location": {"x": 1, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "Front R Up",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": VolumeCommands.CENTER_DOWN},
                    "location": {"x": 0, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "Center Down",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": VolumeCommands.CENTER_UP},
                    "location": {"x": 1, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "Center Up",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": VolumeCommands.SURROUND_LEFT_DOWN},
                    "location": {"x": 0, "y": 3},
                    "size": {"height": 1, "width": 1},
                    "text": "Surr. L Down",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": VolumeCommands.SURROUND_LEFT_UP},
                    "location": {"x": 1, "y": 3},
                    "size": {"height": 1, "width": 1},
                    "text": "Surr. L Up",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": VolumeCommands.SURROUND_RIGHT_DOWN},
                    "location": {"x": 0, "y": 4},
                    "size": {"height": 1, "width": 1},
                    "text": "Surr. R Down",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": VolumeCommands.SURROUND_RIGHT_UP},
                    "location": {"x": 1, "y": 4},
                    "size": {"height": 1, "width": 1},
                    "text": "Surr. R Up",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": VolumeCommands.SURROUND_BACK_LEFT_DOWN},
                    "location": {"x": 0, "y": 5},
                    "size": {"height": 1, "width": 1},
                    "text": "Surr. Back L Down",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": VolumeCommands.SURROUND_BACK_LEFT_UP},
                    "location": {"x": 1, "y": 5},
                    "size": {"height": 1, "width": 1},
                    "text": "Surr. Back L Up",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": VolumeCommands.SURROUND_BACK_RIGHT_DOWN},
                    "location": {"x": 0, "y": 6},
                    "size": {"height": 1, "width": 1},
                    "text": "Surr. Back R Down",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": VolumeCommands.SURROUND_BACK_RIGHT_UP},
                    "location": {"x": 1, "y": 6},
                    "size": {"height": 1, "width": 1},
                    "text": "Surr. Back R Up",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": VolumeCommands.SUB1_DOWN},
                    "location": {"x": 0, "y": 7},
                    "size": {"height": 1, "width": 1},
                    "text": "Sub 1 Down",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": VolumeCommands.SUB1_UP},
                    "location": {"x": 1, "y": 7},
                    "size": {"height": 1, "width": 1},
                    "text": "Sub 1 Up",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": VolumeCommands.SUB2_DOWN},
                    "location": {"x": 0, "y": 8},
                    "size": {"height": 1, "width": 1},
                    "text": "Sub 2 Down",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": VolumeCommands.SUB2_UP},
                    "location": {"x": 1, "y": 8},
                    "size": {"height": 1, "width": 1},
                    "text": "Sub 2 Up",
                    "type": "text",
                },
            ],
        }

    @staticmethod
    def _get_eco_page():
        return {
            "page_id": "denon_avr_commands_eco",
            "name": "ECO",
            "grid": {"height": 3, "width": 1},
            "items": [
                {
                    "command": {"cmd_id": CoreCommands.ECO_AUTO},
                    "location": {"x": 0, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "ECO Auto",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.ECO_ON},
                    "location": {"x": 0, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "ECO On",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.ECO_OFF},
                    "location": {"x": 0, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "ECO Off",
                    "type": "text",
                },
            ],
        }

    @staticmethod
    def _get_inputs_page():
        return {
            "page_id": "denon_avr_commands_inputs",
            "name": "Inputs",
            "grid": {"height": 8, "width": 3},
            "items": [
                {
                    "command": {"cmd_id": CoreCommands.INPUT_PHONO},
                    "location": {"x": 0, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "Phono",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_CD},
                    "location": {"x": 1, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "CD",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_DVD},
                    "location": {"x": 2, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "DVD",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_BD},
                    "location": {"x": 0, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "Blu-ray",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_TV},
                    "location": {"x": 1, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "TV",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_SAT_CBL},
                    "location": {"x": 2, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "SAT/CBL",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_MPLAY},
                    "location": {"x": 0, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "Media Player",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_GAME},
                    "location": {"x": 1, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "Game",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_GAME1},
                    "location": {"x": 2, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "Game 1",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_GAME2},
                    "location": {"x": 0, "y": 3},
                    "size": {"height": 1, "width": 1},
                    "text": "Game 2",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_TUNER},
                    "location": {"x": 1, "y": 3},
                    "size": {"height": 1, "width": 1},
                    "text": "Tuner",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_8K},
                    "location": {"x": 2, "y": 3},
                    "size": {"height": 1, "width": 1},
                    "text": "8K",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_AUX1},
                    "location": {"x": 0, "y": 4},
                    "size": {"height": 1, "width": 1},
                    "text": "AUX 1",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_AUX2},
                    "location": {"x": 1, "y": 4},
                    "size": {"height": 1, "width": 1},
                    "text": "AUX 2",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_AUX3},
                    "location": {"x": 2, "y": 4},
                    "size": {"height": 1, "width": 1},
                    "text": "AUX 3",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_AUX4},
                    "location": {"x": 0, "y": 5},
                    "size": {"height": 1, "width": 1},
                    "text": "AUX 4",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_AUX5},
                    "location": {"x": 1, "y": 5},
                    "size": {"height": 1, "width": 1},
                    "text": "AUX 5",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_AUX6},
                    "location": {"x": 2, "y": 5},
                    "size": {"height": 1, "width": 1},
                    "text": "AUX 6",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_AUX7},
                    "location": {"x": 0, "y": 6},
                    "size": {"height": 1, "width": 1},
                    "text": "AUX 7",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_NET},
                    "location": {"x": 1, "y": 6},
                    "size": {"height": 1, "width": 1},
                    "text": "HEOS",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_BT},
                    "location": {"x": 2, "y": 6},
                    "size": {"height": 1, "width": 1},
                    "text": "Bluetooth",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.INPUT_HD_RADIO},
                    "location": {"x": 0, "y": 7},
                    "size": {"height": 1, "width": 1},
                    "text": "HD Radio",
                    "type": "text",
                },
            ],
        }

    @staticmethod
    def _get_quick_select_page(*, is_denon: bool):
        label = "Quick Select" if is_denon else "Smart Select"
        return {
            "page_id": "denon_avr_commands_quick_select",
            "name": label,
            "grid": {"height": 6, "width": 1},
            "items": [
                {
                    "command": {"cmd_id": CoreCommands.QUICK_SELECT_1 if is_denon else CoreCommands.SMART_SELECT_1},
                    "location": {"x": 0, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": f"{label} 1",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.QUICK_SELECT_2 if is_denon else CoreCommands.SMART_SELECT_2},
                    "location": {"x": 0, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": f"{label} 2",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.QUICK_SELECT_3 if is_denon else CoreCommands.SMART_SELECT_3},
                    "location": {"x": 0, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": f"{label} 3",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.QUICK_SELECT_4 if is_denon else CoreCommands.SMART_SELECT_4},
                    "location": {"x": 0, "y": 3},
                    "size": {"height": 1, "width": 1},
                    "text": f"{label} 4",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.QUICK_SELECT_5 if is_denon else CoreCommands.SMART_SELECT_5},
                    "location": {"x": 0, "y": 4},
                    "size": {"height": 1, "width": 1},
                    "text": f"{label} 5",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.QUICK_SELECT_6 if is_denon else CoreCommands.SMART_SELECT_6},
                    "location": {"x": 0, "y": 5},
                    "size": {"height": 1, "width": 1},
                    "text": f"{label} 6",
                    "type": "text",
                },
            ],
        }

    @staticmethod
    def _get_tuner_page():
        return {
            "page_id": "denon_avr_commands_tuner",
            "name": "Tuner",
            "grid": {"height": 4, "width": 2},
            "items": [
                {
                    "command": {"cmd_id": TunerCommands.TUNER_BAND_FM},
                    "location": {"x": 0, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "FM",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": TunerCommands.TUNER_BAND_AM},
                    "location": {"x": 1, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "AM",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": TunerCommands.TUNER_FREQUENCY_DOWN},
                    "location": {"x": 0, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "Freq Down",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": TunerCommands.TUNER_FREQUENCY_UP},
                    "location": {"x": 1, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "Freq Up",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": TunerCommands.TUNER_PRESET_DOWN},
                    "location": {"x": 0, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "Preset Down",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": TunerCommands.TUNER_PRESET_UP},
                    "location": {"x": 1, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "Preset Up",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": TunerCommands.TUNER_MODE_AUTO},
                    "location": {"x": 0, "y": 3},
                    "size": {"height": 1, "width": 1},
                    "text": "Auto Tune",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": TunerCommands.TUNER_MODE_MANUAL},
                    "location": {"x": 1, "y": 3},
                    "size": {"height": 1, "width": 1},
                    "text": "Manual Tune",
                    "type": "text",
                },
            ],
        }

    @staticmethod
    def _get_picture_mode_page():
        return {
            "page_id": "denon_avr_commands_picture_mode",
            "name": "Picture Mode",
            "grid": {"height": 3, "width": 3},
            "items": [
                {
                    "command": {"cmd_id": PictureModeCommands.PICTURE_MODE_MOVIE},
                    "location": {"x": 0, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "Movie",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": PictureModeCommands.PICTURE_MODE_GAME},
                    "location": {"x": 1, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "Game",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": PictureModeCommands.PICTURE_MODE_VIVID},
                    "location": {"x": 2, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "Vivid",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": PictureModeCommands.PICTURE_MODE_STREAM},
                    "location": {"x": 0, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "Stream",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": PictureModeCommands.PICTURE_MODE_BRILLIANT},
                    "location": {"x": 1, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "Brilliant",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": PictureModeCommands.PICTURE_MODE_CUSTOM},
                    "location": {"x": 2, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "Custom",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": PictureModeCommands.PICTURE_MODE_ISF_DAY},
                    "location": {"x": 0, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "ISF Day",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": PictureModeCommands.PICTURE_MODE_ISF_NIGHT},
                    "location": {"x": 1, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "ISF Night",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": PictureModeCommands.PICTURE_MODE_OFF},
                    "location": {"x": 2, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "Off",
                    "type": "text",
                },
            ],
        }

    @staticmethod
    def _get_sleep_timer_page():
        return {
            "page_id": "denon_avr_commands_sleep_timer",
            "name": "Sleep Timer",
            "grid": {"height": 5, "width": 1},
            "items": [
                {
                    "command": {"cmd_id": CoreCommands.SLEEP_TIMER_OFF},
                    "location": {"x": 0, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "Sleep Off",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.SLEEP_TIMER_30MIN},
                    "location": {"x": 0, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "Sleep 30 min",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.SLEEP_TIMER_60MIN},
                    "location": {"x": 0, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "Sleep 60 min",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.SLEEP_TIMER_90MIN},
                    "location": {"x": 0, "y": 3},
                    "size": {"height": 1, "width": 1},
                    "text": "Sleep 90 min",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.SLEEP_TIMER_120MIN},
                    "location": {"x": 0, "y": 4},
                    "size": {"height": 1, "width": 1},
                    "text": "Sleep 120 min",
                    "type": "text",
                },
            ],
        }

    @staticmethod
    def _get_sound_tweaks_page():
        return {
            "page_id": "denon_avr_commands_sound_tweaks",
            "name": "Sound Tweaks",
            "grid": {"height": 6, "width": 2},
            "items": [
                {
                    "command": {"cmd_id": SoundModeCommands.PANORAMA_ON},
                    "location": {"x": 0, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "Panorama On",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.PANORAMA_OFF},
                    "location": {"x": 1, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "Panorama Off",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.DIMENSION_DOWN},
                    "location": {"x": 0, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "Dimension Down",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.DIMENSION_UP},
                    "location": {"x": 1, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "Dimension Up",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.CENTER_WIDTH_DOWN},
                    "location": {"x": 0, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "Center Width Down",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.CENTER_WIDTH_UP},
                    "location": {"x": 1, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "Center Width Up",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_LEVEL_COMP_OFF},
                    "location": {"x": 0, "y": 3},
                    "size": {"height": 1, "width": 1},
                    "text": "Surr. Lvl Off",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_LEVEL_COMP_LIGHT},
                    "location": {"x": 1, "y": 3},
                    "size": {"height": 1, "width": 1},
                    "text": "Surr. Lvl Light",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_LEVEL_COMP_MEDIUM},
                    "location": {"x": 0, "y": 4},
                    "size": {"height": 1, "width": 1},
                    "text": "Surr. Lvl Medium",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_LEVEL_COMP_HEAVY},
                    "location": {"x": 1, "y": 4},
                    "size": {"height": 1, "width": 1},
                    "text": "Surr. Lvl Heavy",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.ALL_ZONE_STEREO_ON},
                    "location": {"x": 0, "y": 5},
                    "size": {"height": 1, "width": 1},
                    "text": "All Zone St. On",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.ALL_ZONE_STEREO_OFF},
                    "location": {"x": 1, "y": 5},
                    "size": {"height": 1, "width": 1},
                    "text": "All Zone St. Off",
                    "type": "text",
                },
            ],
        }

    @staticmethod
    def _get_zone_favorites_page():
        return {
            "page_id": "denon_avr_commands_zone_favorites",
            "name": "Zone Favorites",
            "grid": {"height": 3, "width": 2},
            "items": [
                {
                    "command": {"cmd_id": CoreCommands.ZONE_FAVORITE_1},
                    "location": {"x": 0, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "Favorite 1",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.ZONE_FAVORITE_MEMORY_1},
                    "location": {"x": 1, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "Save Fav 1",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.ZONE_FAVORITE_2},
                    "location": {"x": 0, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "Favorite 2",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.ZONE_FAVORITE_MEMORY_2},
                    "location": {"x": 1, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "Save Fav 2",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.ZONE_FAVORITE_3},
                    "location": {"x": 0, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "Favorite 3",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.ZONE_FAVORITE_MEMORY_3},
                    "location": {"x": 1, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "Save Fav 3",
                    "type": "text",
                },
            ],
        }


REMOTE_BUTTONS_MAPPING: list[dict[str, Any]] = [
    {"button": Buttons.BACK, "short_press": {"cmd_id": media_player.Commands.BACK}},
    {
        "button": Buttons.DPAD_DOWN,
        "short_press": {"cmd_id": media_player.Commands.CURSOR_DOWN},
    },
    {
        "button": Buttons.DPAD_LEFT,
        "short_press": {"cmd_id": media_player.Commands.CURSOR_LEFT},
    },
    {
        "button": Buttons.DPAD_RIGHT,
        "short_press": {"cmd_id": media_player.Commands.CURSOR_RIGHT},
    },
    {
        "button": Buttons.DPAD_MIDDLE,
        "short_press": {"cmd_id": media_player.Commands.CURSOR_ENTER},
    },
    {
        "button": Buttons.DPAD_UP,
        "short_press": {"cmd_id": media_player.Commands.CURSOR_UP},
    },
    {
        "button": Buttons.VOLUME_UP,
        "short_press": {"cmd_id": media_player.Commands.VOLUME_UP},
    },
    {
        "button": Buttons.VOLUME_DOWN,
        "short_press": {"cmd_id": media_player.Commands.VOLUME_DOWN},
    },
    {
        "button": Buttons.MUTE,
        "short_press": {"cmd_id": media_player.Commands.MUTE_TOGGLE},
    },
    {"button": Buttons.POWER, "short_press": {"cmd_id": media_player.Commands.TOGGLE}},
    {"button": Buttons.PREV, "short_press": {"cmd_id": media_player.Commands.PREVIOUS}},
    {"button": Buttons.PLAY, "short_press": {"cmd_id": media_player.Commands.PLAY_PAUSE}},
    {"button": Buttons.NEXT, "short_press": {"cmd_id": media_player.Commands.NEXT}},
    {"button": Buttons.CHANNEL_UP, "short_press": {"cmd_id": media_player.Commands.CHANNEL_UP}},
    {"button": Buttons.CHANNEL_DOWN, "short_press": {"cmd_id": media_player.Commands.CHANNEL_DOWN}},
]
