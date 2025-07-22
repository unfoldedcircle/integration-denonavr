# pylint: disable=C0302
"""
Remote entity functions.

:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""
import logging
from typing import Any

import avr
import helpers
import ucapi.remote
from command_constants import (
    AudysseyCommands,
    CoreCommands,
    DiracCommands,
    SoundModeCommands,
    VolumeCommands,
)
from config import AvrDevice, create_entity_id
from media_player import DenonMediaPlayer
from ucapi import EntityTypes, Remote, StatusCodes, media_player
from ucapi.remote import Attributes, Commands, Features
from ucapi.ui import Buttons

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


# pylint: disable=R0903
class DenonRemote(Remote):
    """Representation of a Denon/Marantz AVR Remote entity."""

    def __init__(self, device: AvrDevice, receiver: avr.DenonDevice, denon_media_player: DenonMediaPlayer):
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
            simple_commands=self._denon_media_player.get_supported_commands(False),
            button_mapping=REMOTE_BUTTONS_MAPPING,
            ui_pages=DenonRemote._get_remote_ui_pages(device.is_denon),
        )

    async def command(self, cmd_id: str, params: dict[str, Any] | None = None) -> StatusCodes:
        """
        Remote entity command handler.

        Called by the integration-API if a command is sent to a configured remote entity.

        :param cmd_id: command
        :param params: optional command parameters
        :return: status code of the command request
        """
        # pylint: disable=R0911
        match cmd_id:
            case Commands.ON:
                return await self._denon_media_player.command(Commands.ON)
            case Commands.OFF:
                await self._denon_media_player.command(Commands.OFF)
            case Commands.TOGGLE:
                return await self._denon_media_player.command(Commands.TOGGLE)

        if cmd_id.startswith("remote."):
            _LOG.error("Command %s is not allowed.", cmd_id)
            return StatusCodes.BAD_REQUEST

        if params is None:
            return StatusCodes.BAD_REQUEST

        if params:
            repeat = self._get_int_param("repeat", params, 1)
        else:
            repeat = 1

        if cmd_id == Commands.SEND_CMD:
            command_or_status = self._get_command_or_status_code(cmd_id, params.get("command", ""))
            if isinstance(command_or_status, StatusCodes):
                return command_or_status

            success = True
            for _ in range(0, repeat):
                success |= await self._denon_media_player.command(command_or_status) == StatusCodes.OK

        if cmd_id == Commands.SEND_CMD_SEQUENCE:
            success = True
            for command in params.get("sequence", []):
                for _ in range(0, repeat):
                    command_or_status = self._get_command_or_status_code(cmd_id, command)
                    if isinstance(command_or_status, StatusCodes):
                        success = False
                    else:
                        res = await self._denon_media_player.command(command_or_status)
                        if res != StatusCodes.OK:
                            success = False
            if success:
                return StatusCodes.OK
            return StatusCodes.BAD_REQUEST

        # send "raw" commands as is to the receiver
        return await self._denon_media_player.command(cmd_id)

    @staticmethod
    def state_from_avr(avr_state: avr.States) -> ucapi.remote.States:
        """
        Convert AVR state to UC API remote state.

        :param avr_state: Denon/Marantz AVR state
        :return: UC API remote state
        """
        if avr_state in REMOTE_STATE_MAPPING:
            return REMOTE_STATE_MAPPING[avr_state]
        return ucapi.remote.States.UNKNOWN

    def filter_changed_attributes(self, update: dict[str, Any]) -> dict[str, Any]:
        """
        Filter the given attributes and return only the changed values.

        :param update: dictionary with attributes.
        :return: filtered entity attributes containing changed attributes only.
        """
        attributes = {}

        if Attributes.STATE in update:
            state = DenonRemote.state_from_avr(update[Attributes.STATE])
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
        return default

    @staticmethod
    def _get_remote_ui_pages(is_denon: bool):
        return [
            DenonRemote._get_main_page(),
            DenonRemote._get_sound_modes_page(),
            DenonRemote._get_standby_page(),
            DenonRemote._get_triggers_page(),
            DenonRemote._get_dirac_page(),
            DenonRemote._get_audyssey_page(),
            DenonRemote._get_channel_levels_page(),
            DenonRemote._get_eco_page(),
            DenonRemote._get_quick_select_page(is_denon),
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
            "grid": {"height": 7, "width": 4},
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
                    "text": "Dolby",
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
                    "text": "Multi Channel Stereo",
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
                    "text": "Multi Channel Stereo",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_MODE_AURO2DSURR},
                    "location": {"x": 2, "y": 3},
                    "size": {"height": 1, "width": 2},
                    "text": "Auro-2D Surround",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SOUND_MODE_IMAX_AUTO},
                    "location": {"x": 0, "y": 4},
                    "size": {"height": 1, "width": 2},
                    "text": "IMAX Auto",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SOUND_MODE_NEURAL_X_ON},
                    "location": {"x": 2, "y": 4},
                    "size": {"height": 1, "width": 2},
                    "text": "Neural X On",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SOUND_MODE_IMAX_OFF},
                    "location": {"x": 0, "y": 5},
                    "size": {"height": 1, "width": 2},
                    "text": "IMAX Off",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SOUND_MODE_NEURAL_X_OFF},
                    "location": {"x": 2, "y": 5},
                    "size": {"height": 1, "width": 2},
                    "text": "Neural X Off",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_MODE_PREVIOUS},
                    "location": {"x": 0, "y": 6},
                    "size": {"height": 1, "width": 2},
                    "text": "Previous",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": SoundModeCommands.SURROUND_MODE_NEXT},
                    "location": {"x": 2, "y": 6},
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
            "name": "Triggers",
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
            "name": "Triggers",
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
                    "text": "ECO On",
                    "type": "text",
                },
            ],
        }

    @staticmethod
    def _get_quick_select_page(is_denon: bool):
        return {
            "page_id": "denon_avr_commands_quick_select",
            "name": "Quick Select" if is_denon else "Smart Select",
            "grid": {"height": 5, "width": 1},
            "items": [
                {
                    "command": {"cmd_id": CoreCommands.QUICK_SELECT_1 if is_denon else CoreCommands.SMART_SELECT_1},
                    "location": {"x": 0, "y": 0},
                    "size": {"height": 1, "width": 1},
                    "text": "Quick Select 1" if is_denon else "Smart Select 1",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.QUICK_SELECT_2 if is_denon else CoreCommands.SMART_SELECT_2},
                    "location": {"x": 0, "y": 1},
                    "size": {"height": 1, "width": 1},
                    "text": "Quick Select 2" if is_denon else "Smart Select 2",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.QUICK_SELECT_3 if is_denon else CoreCommands.SMART_SELECT_3},
                    "location": {"x": 0, "y": 2},
                    "size": {"height": 1, "width": 1},
                    "text": "Quick Select 3" if is_denon else "Smart Select 3",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.QUICK_SELECT_4 if is_denon else CoreCommands.SMART_SELECT_4},
                    "location": {"x": 0, "y": 3},
                    "size": {"height": 1, "width": 1},
                    "text": "Quick Select 4" if is_denon else "Smart Select 4",
                    "type": "text",
                },
                {
                    "command": {"cmd_id": CoreCommands.QUICK_SELECT_5 if is_denon else CoreCommands.SMART_SELECT_5},
                    "location": {"x": 0, "y": 4},
                    "size": {"height": 1, "width": 1},
                    "text": "Quick Select 5" if is_denon else "Smart Select 5",
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
]
