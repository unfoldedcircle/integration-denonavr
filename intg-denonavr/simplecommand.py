"""
This module implements the Denon/Marantz AVR receiver communication of the Remote Two/3 integration driver.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

# pylint: disable=C0302
from typing import Awaitable, Callable

import ucapi

from denonavrlib import denonavr

from command_constants import (
    AudysseyCommands,
    CoreCommands,
    DiracCommands,
    SoundModeCommands,
    VolumeCommands,
)
from config import AvrDevice

CORE_COMMANDS = {
    CoreCommands.OUTPUT_1,
    CoreCommands.OUTPUT_2,
    CoreCommands.OUTPUT_AUTO,
    CoreCommands.DIMMER_TOGGLE,
    CoreCommands.DIMMER_BRIGHT,
    CoreCommands.DIMMER_DIM,
    CoreCommands.DIMMER_DARK,
    CoreCommands.DIMMER_OFF,
    CoreCommands.TRIGGER1_ON,
    CoreCommands.TRIGGER1_OFF,
    CoreCommands.TRIGGER2_ON,
    CoreCommands.TRIGGER2_OFF,
    CoreCommands.TRIGGER3_ON,
    CoreCommands.TRIGGER3_OFF,
    CoreCommands.DELAY_UP,
    CoreCommands.DELAY_DOWN,
    CoreCommands.ECO_ON,
    CoreCommands.ECO_AUTO,
    CoreCommands.ECO_OFF,
    CoreCommands.INFO_MENU,
    CoreCommands.CHANNEL_LEVEL_ADJUST_MENU,
    CoreCommands.AUTO_STANDBY_OFF,
    CoreCommands.AUTO_STANDBY_15MIN,
    CoreCommands.AUTO_STANDBY_30MIN,
    CoreCommands.AUTO_STANDBY_60MIN,
    CoreCommands.DELAY_TIME_UP,
    CoreCommands.DELAY_TIME_DOWN,
    CoreCommands.HDMI_AUDIO_DECODE_AMP,
    CoreCommands.HDMI_AUDIO_DECODE_TV,
    CoreCommands.VIDEO_PROCESSING_MODE_AUTO,
    CoreCommands.VIDEO_PROCESSING_MODE_GAME,
    CoreCommands.VIDEO_PROCESSING_MODE_MOVIE,
    CoreCommands.VIDEO_PROCESSING_MODE_BYPASS,
    CoreCommands.NETWORK_RESTART,
    CoreCommands.SPEAKER_PRESET_1,
    CoreCommands.SPEAKER_PRESET_2,
    CoreCommands.BT_TRANSMITTER_ON,
    CoreCommands.BT_TRANSMITTER_OFF,
    CoreCommands.BT_OUTPUT_MODE_BT_SPEAKER,
    CoreCommands.BT_OUTPUT_MODE_BT_ONLY,
    CoreCommands.AUDIO_RESTORER_OFF,
    CoreCommands.AUDIO_RESTORER_LOW,
    CoreCommands.AUDIO_RESTORER_MEDIUM,
    CoreCommands.AUDIO_RESTORER_HIGH,
    CoreCommands.REMOTE_CONTROL_LOCK_ON,
    CoreCommands.REMOTE_CONTROL_LOCK_OFF,
    CoreCommands.PANEL_LOCK_PANEL,
    CoreCommands.PANEL_LOCK_PANEL_VOLUME,
    CoreCommands.PANEL_LOCK_OFF,
    CoreCommands.GRAPHIC_EQ_ON,
    CoreCommands.GRAPHIC_EQ_OFF,
    CoreCommands.HEADPHONE_EQ_ON,
    CoreCommands.HEADPHONE_EQ_OFF,
    CoreCommands.INPUT_PHONO,
    CoreCommands.INPUT_CD,
    CoreCommands.INPUT_DVD,
    CoreCommands.INPUT_BD,
    CoreCommands.INPUT_TV,
    CoreCommands.INPUT_SAT_CBL,
    CoreCommands.INPUT_MPLAY,
    CoreCommands.INPUT_GAME,
    CoreCommands.INPUT_GAME1,
    CoreCommands.INPUT_GAME2,
    CoreCommands.INPUT_TUNER,
    CoreCommands.INPUT_8K,
    CoreCommands.INPUT_AUX1,
    CoreCommands.INPUT_AUX2,
    CoreCommands.INPUT_AUX3,
    CoreCommands.INPUT_AUX4,
    CoreCommands.INPUT_AUX5,
    CoreCommands.INPUT_AUX6,
    CoreCommands.INPUT_AUX7,
    CoreCommands.INPUT_NET,
    CoreCommands.INPUT_BT,
}

CORE_COMMANDS_TELNET = {
    *CORE_COMMANDS,
    CoreCommands.SPEAKER_PRESET_TOGGLE,
    CoreCommands.BT_TRANSMITTER_TOGGLE,
    CoreCommands.BT_OUTPUT_MODE_TOGGLE,
    CoreCommands.GRAPHIC_EQ_TOGGLE,
    CoreCommands.HEADPHONE_EQ_TOGGLE,
}

CORE_COMMANDS_QUICK_SELECT = {
    CoreCommands.STATUS,
    CoreCommands.QUICK_SELECT_1,
    CoreCommands.QUICK_SELECT_2,
    CoreCommands.QUICK_SELECT_3,
    CoreCommands.QUICK_SELECT_4,
    CoreCommands.QUICK_SELECT_5,
}

CORE_COMMANDS_DENON = {
    *CORE_COMMANDS,
    CoreCommands.STATUS,
    *CORE_COMMANDS_QUICK_SELECT,
}

CORE_COMMANDS_DENON_TELNET = {
    *CORE_COMMANDS_TELNET,
    CoreCommands.STATUS,
    *CORE_COMMANDS_QUICK_SELECT,
}

CORE_COMMANDS_SMART_SELECT = {
    CoreCommands.SMART_SELECT_1,
    CoreCommands.SMART_SELECT_2,
    CoreCommands.SMART_SELECT_3,
    CoreCommands.SMART_SELECT_4,
    CoreCommands.SMART_SELECT_5,
}

CORE_COMMANDS_MARANTZ = {
    *CORE_COMMANDS,
    *CORE_COMMANDS_SMART_SELECT,
}

CORE_COMMANDS_MARANTZ_TELNET = {
    *CORE_COMMANDS_TELNET,
    *CORE_COMMANDS_SMART_SELECT,
}

SOUND_MODE_COMMANDS = {
    SoundModeCommands.SURROUND_MODE_AUTO,
    SoundModeCommands.SURROUND_MODE_DIRECT,
    SoundModeCommands.SURROUND_MODE_PURE_DIRECT,
    SoundModeCommands.SURROUND_MODE_DOLBY_DIGITAL,
    SoundModeCommands.SURROUND_MODE_DTS_SURROUND,
    SoundModeCommands.SURROUND_MODE_AURO3D,
    SoundModeCommands.SURROUND_MODE_AURO2DSURR,
    SoundModeCommands.SURROUND_MODE_MCH_STEREO,
    SoundModeCommands.SURROUND_MODE_NEXT,
    SoundModeCommands.SURROUND_MODE_PREVIOUS,
    SoundModeCommands.SOUND_MODE_NEURAL_X_ON,
    SoundModeCommands.SOUND_MODE_NEURAL_X_OFF,
    SoundModeCommands.SOUND_MODE_IMAX_AUTO,
    SoundModeCommands.SOUND_MODE_IMAX_OFF,
    SoundModeCommands.IMAX_AUDIO_SETTINGS_AUTO,
    SoundModeCommands.IMAX_AUDIO_SETTINGS_MANUAL,
    SoundModeCommands.IMAX_HPF_40HZ,
    SoundModeCommands.IMAX_HPF_60HZ,
    SoundModeCommands.IMAX_HPF_80HZ,
    SoundModeCommands.IMAX_HPF_90HZ,
    SoundModeCommands.IMAX_HPF_100HZ,
    SoundModeCommands.IMAX_HPF_110HZ,
    SoundModeCommands.IMAX_HPF_120HZ,
    SoundModeCommands.IMAX_HPF_150HZ,
    SoundModeCommands.IMAX_HPF_180HZ,
    SoundModeCommands.IMAX_HPF_200HZ,
    SoundModeCommands.IMAX_HPF_250HZ,
    SoundModeCommands.IMAX_LPF_80HZ,
    SoundModeCommands.IMAX_LPF_90HZ,
    SoundModeCommands.IMAX_LPF_100HZ,
    SoundModeCommands.IMAX_LPF_110HZ,
    SoundModeCommands.IMAX_LPF_120HZ,
    SoundModeCommands.IMAX_LPF_150HZ,
    SoundModeCommands.IMAX_LPF_180HZ,
    SoundModeCommands.IMAX_LPF_200HZ,
    SoundModeCommands.IMAX_LPF_250HZ,
    SoundModeCommands.IMAX_SUBWOOFER_ON,
    SoundModeCommands.IMAX_SUBWOOFER_OFF,
    SoundModeCommands.IMAX_SUBWOOFER_OUTPUT_LFE_MAIN,
    SoundModeCommands.IMAX_SUBWOOFER_OUTPUT_LFE,
    SoundModeCommands.CINEMA_EQ_ON,
    SoundModeCommands.CINEMA_EQ_OFF,
    SoundModeCommands.CENTER_SPREAD_ON,
    SoundModeCommands.CENTER_SPREAD_OFF,
    SoundModeCommands.LOUDNESS_MANAGEMENT_ON,
    SoundModeCommands.LOUDNESS_MANAGEMENT_OFF,
    SoundModeCommands.DIALOG_ENHANCER_OFF,
    SoundModeCommands.DIALOG_ENHANCER_LOW,
    SoundModeCommands.DIALOG_ENHANCER_MEDIUM,
    SoundModeCommands.DIALOG_ENHANCER_HIGH,
    SoundModeCommands.AUROMATIC_3D_PRESET_SMALL,
    SoundModeCommands.AUROMATIC_3D_PRESET_MEDIUM,
    SoundModeCommands.AUROMATIC_3D_PRESET_LARGE,
    SoundModeCommands.AUROMATIC_3D_PRESET_SPEECH,
    SoundModeCommands.AUROMATIC_3D_PRESET_MOVIE,
    SoundModeCommands.AUROMATIC_3D_STRENGTH_UP,
    SoundModeCommands.AUROMATIC_3D_STRENGTH_DOWN,
    SoundModeCommands.AURO_3D_MODE_DIRECT,
    SoundModeCommands.AURO_3D_MODE_CHANNEL_EXPANSION,
    SoundModeCommands.DIALOG_CONTROL_UP,
    SoundModeCommands.DIALOG_CONTROL_DOWN,
    SoundModeCommands.SPEAKER_VIRTUALIZER_ON,
    SoundModeCommands.SPEAKER_VIRTUALIZER_OFF,
    SoundModeCommands.EFFECT_SPEAKER_SELECTION_FLOOR,
    SoundModeCommands.EFFECT_SPEAKER_SELECTION_FRONT,
    SoundModeCommands.EFFECT_SPEAKER_SELECTION_FRONT_HEIGHT,
    SoundModeCommands.EFFECT_SPEAKER_SELECTION_FRONT_HEIGHT_WIDE,
    SoundModeCommands.EFFECT_SPEAKER_SELECTION_FRONT_WIDE,
    SoundModeCommands.EFFECT_SPEAKER_SELECTION_HEIGHT_FLOOR,
    SoundModeCommands.EFFECT_SPEAKER_SELECTION_SURROUND_BACK,
    SoundModeCommands.EFFECT_SPEAKER_SELECTION_SURROUND_BACK_FRONT_HEIGHT,
    SoundModeCommands.EFFECT_SPEAKER_SELECTION_SURROUND_BACK_FRONT_WIDE,
    SoundModeCommands.DRC_AUTO,
    SoundModeCommands.DRC_LOW,
    SoundModeCommands.DRC_MID,
    SoundModeCommands.DRC_HI,
    SoundModeCommands.DRC_OFF,
}

SOUND_MODE_COMMANDS_TELNET = {
    *SOUND_MODE_COMMANDS,
    SoundModeCommands.SOUND_MODE_NEURAL_X_TOGGLE,
    SoundModeCommands.SOUND_MODE_IMAX_TOGGLE,
    SoundModeCommands.IMAX_AUDIO_SETTINGS_TOGGLE,
    SoundModeCommands.CINEMA_EQ_TOGGLE,
    SoundModeCommands.CENTER_SPREAD_TOGGLE,
    SoundModeCommands.LOUDNESS_MANAGEMENT_TOGGLE,
    SoundModeCommands.SPEAKER_VIRTUALIZER_TOGGLE,
}

AUDYSSEY_COMMANDS = {
    AudysseyCommands.MULTIEQ_REFERENCE,
    AudysseyCommands.MULTIEQ_BYPASS_LR,
    AudysseyCommands.MULTIEQ_FLAT,
    AudysseyCommands.MULTIEQ_OFF,
    AudysseyCommands.DYNAMIC_EQ_ON,
    AudysseyCommands.DYNAMIC_EQ_OFF,
    AudysseyCommands.DYNAMIC_EQ_TOGGLE,
    AudysseyCommands.AUDYSSEY_LFC,
    AudysseyCommands.AUDYSSEY_LFC_OFF,
    AudysseyCommands.AUDYSSEY_LFC_TOGGLE,
    AudysseyCommands.DYNAMIC_VOLUME_OFF,
    AudysseyCommands.DYNAMIC_VOLUME_LIGHT,
    AudysseyCommands.DYNAMIC_VOLUME_MEDIUM,
    AudysseyCommands.DYNAMIC_VOLUME_HEAVY,
    AudysseyCommands.CONTAINMENT_AMOUNT_UP,
    AudysseyCommands.CONTAINMENT_AMOUNT_DOWN,
}

DIRAC_COMMANDS = {
    DiracCommands.DIRAC_LIVE_FILTER_SLOT1,
    DiracCommands.DIRAC_LIVE_FILTER_SLOT2,
    DiracCommands.DIRAC_LIVE_FILTER_SLOT3,
    DiracCommands.DIRAC_LIVE_FILTER_OFF,
}

VOLUME_COMMANDS = {
    VolumeCommands.FRONT_LEFT_UP,
    VolumeCommands.FRONT_LEFT_DOWN,
    VolumeCommands.FRONT_RIGHT_UP,
    VolumeCommands.FRONT_RIGHT_DOWN,
    VolumeCommands.CENTER_UP,
    VolumeCommands.CENTER_DOWN,
    VolumeCommands.SUB1_UP,
    VolumeCommands.SUB1_DOWN,
    VolumeCommands.SUB2_UP,
    VolumeCommands.SUB2_DOWN,
    VolumeCommands.SUB3_UP,
    VolumeCommands.SUB3_DOWN,
    VolumeCommands.SUB4_UP,
    VolumeCommands.SUB4_DOWN,
    VolumeCommands.SURROUND_LEFT_UP,
    VolumeCommands.SURROUND_LEFT_DOWN,
    VolumeCommands.SURROUND_RIGHT_UP,
    VolumeCommands.SURROUND_RIGHT_DOWN,
    VolumeCommands.SURROUND_BACK_LEFT_UP,
    VolumeCommands.SURROUND_BACK_LEFT_DOWN,
    VolumeCommands.SURROUND_BACK_RIGHT_UP,
    VolumeCommands.SURROUND_BACK_RIGHT_DOWN,
    VolumeCommands.FRONT_HEIGHT_LEFT_UP,
    VolumeCommands.FRONT_HEIGHT_LEFT_DOWN,
    VolumeCommands.FRONT_HEIGHT_RIGHT_UP,
    VolumeCommands.FRONT_HEIGHT_RIGHT_DOWN,
    VolumeCommands.FRONT_WIDE_LEFT_UP,
    VolumeCommands.FRONT_WIDE_LEFT_DOWN,
    VolumeCommands.FRONT_WIDE_RIGHT_UP,
    VolumeCommands.FRONT_WIDE_RIGHT_DOWN,
    VolumeCommands.TOP_FRONT_LEFT_UP,
    VolumeCommands.TOP_FRONT_LEFT_DOWN,
    VolumeCommands.TOP_FRONT_RIGHT_UP,
    VolumeCommands.TOP_FRONT_RIGHT_DOWN,
    VolumeCommands.TOP_MIDDLE_LEFT_UP,
    VolumeCommands.TOP_MIDDLE_LEFT_DOWN,
    VolumeCommands.TOP_MIDDLE_RIGHT_UP,
    VolumeCommands.TOP_MIDDLE_RIGHT_DOWN,
    VolumeCommands.TOP_REAR_LEFT_UP,
    VolumeCommands.TOP_REAR_LEFT_DOWN,
    VolumeCommands.TOP_REAR_RIGHT_UP,
    VolumeCommands.TOP_REAR_RIGHT_DOWN,
    VolumeCommands.REAR_HEIGHT_LEFT_UP,
    VolumeCommands.REAR_HEIGHT_LEFT_DOWN,
    VolumeCommands.REAR_HEIGHT_RIGHT_UP,
    VolumeCommands.REAR_HEIGHT_RIGHT_DOWN,
    VolumeCommands.FRONT_DOLBY_LEFT_UP,
    VolumeCommands.FRONT_DOLBY_LEFT_DOWN,
    VolumeCommands.FRONT_DOLBY_RIGHT_UP,
    VolumeCommands.FRONT_DOLBY_RIGHT_DOWN,
    VolumeCommands.SURROUND_DOLBY_LEFT_UP,
    VolumeCommands.SURROUND_DOLBY_LEFT_DOWN,
    VolumeCommands.SURROUND_DOLBY_RIGHT_UP,
    VolumeCommands.SURROUND_DOLBY_RIGHT_DOWN,
    VolumeCommands.BACK_DOLBY_LEFT_UP,
    VolumeCommands.BACK_DOLBY_LEFT_DOWN,
    VolumeCommands.BACK_DOLBY_RIGHT_UP,
    VolumeCommands.BACK_DOLBY_RIGHT_DOWN,
    VolumeCommands.SURROUND_HEIGHT_LEFT_UP,
    VolumeCommands.SURROUND_HEIGHT_LEFT_DOWN,
    VolumeCommands.SURROUND_HEIGHT_RIGHT_UP,
    VolumeCommands.SURROUND_HEIGHT_RIGHT_DOWN,
    VolumeCommands.TOP_SURROUND_UP,
    VolumeCommands.TOP_SURROUND_DOWN,
    VolumeCommands.CENTER_HEIGHT_UP,
    VolumeCommands.CENTER_HEIGHT_DOWN,
    VolumeCommands.CHANNEL_VOLUMES_RESET,
    VolumeCommands.SUBWOOFER_ON,
    VolumeCommands.SUBWOOFER_OFF,
    VolumeCommands.SUBWOOFER1_LEVEL_UP,
    VolumeCommands.SUBWOOFER1_LEVEL_DOWN,
    VolumeCommands.SUBWOOFER2_LEVEL_UP,
    VolumeCommands.SUBWOOFER2_LEVEL_DOWN,
    VolumeCommands.SUBWOOFER3_LEVEL_UP,
    VolumeCommands.SUBWOOFER3_LEVEL_DOWN,
    VolumeCommands.SUBWOOFER4_LEVEL_UP,
    VolumeCommands.SUBWOOFER4_LEVEL_DOWN,
    VolumeCommands.LFE_UP,
    VolumeCommands.LFE_DOWN,
    VolumeCommands.BASS_SYNC_UP,
    VolumeCommands.BASS_SYNC_DOWN,
}

VOLUME_COMMANDS_TELNET = {
    *VOLUME_COMMANDS,
    VolumeCommands.SUBWOOFER_TOGGLE,
}

ALL_COMMANDS_DENON = {
    # Same as ALL_COMMANDS but with STATUS and quick select
    *CORE_COMMANDS_DENON,
    *SOUND_MODE_COMMANDS,
    *AUDYSSEY_COMMANDS,
    *DIRAC_COMMANDS,
    *VOLUME_COMMANDS,
}

ALL_COMMANDS_MARANTZ = {
    # Same as ALL_COMMANDS but with smart select
    *CORE_COMMANDS_MARANTZ,
    *SOUND_MODE_COMMANDS,
    *AUDYSSEY_COMMANDS,
    *DIRAC_COMMANDS,
    *VOLUME_COMMANDS,
}

ALL_COMMANDS_TELNET_DENON = {
    # Same as ALL_COMMANDS_TELNET but with support for toggle commands, STATUS and quick select
    *CORE_COMMANDS_DENON_TELNET,
    *SOUND_MODE_COMMANDS_TELNET,
    *AUDYSSEY_COMMANDS,
    *DIRAC_COMMANDS,
    *VOLUME_COMMANDS_TELNET,
}

ALL_COMMANDS_TELNET_MARANTZ = {
    # Same as ALL_COMMANDS_TELNET but with support for toggle commands and smart select
    *CORE_COMMANDS_MARANTZ_TELNET,
    *SOUND_MODE_COMMANDS_TELNET,
    *AUDYSSEY_COMMANDS,
    *DIRAC_COMMANDS,
    *VOLUME_COMMANDS_TELNET,
}


def get_simple_commands(device: AvrDevice):
    """Get the list of simple commands for the given device."""
    # Denon has additional simple commands
    if device.is_denon:
        if device.use_telnet:
            return [*ALL_COMMANDS_TELNET_DENON]
        return [*ALL_COMMANDS_DENON]
    if device.use_telnet:
        return [*ALL_COMMANDS_TELNET_MARANTZ]
    return [*ALL_COMMANDS_MARANTZ]


# pylint: disable=R0903
class SimpleCommand:
    """Handles mapping and sending of Simple Commands to the receiver."""

    def __init__(self, receiver: denonavr.DenonAVR, send_command: Callable[[str], Awaitable[ucapi.StatusCodes]]):
        """
        Create a SimpleCommand instance.

        :param receiver: Denon/Marantz receiver instance
        :param send_command: Function to send a raw command to the receiver
        """
        self._receiver = receiver
        self._send_command = send_command

    async def send_simple_command(self, cmd: str) -> ucapi.StatusCodes:
        """Send a simple command to the AVR."""
        # pylint: disable=R0911
        if cmd in CORE_COMMANDS_DENON_TELNET:
            return await self._handle_core_command(cmd)
        if cmd in VOLUME_COMMANDS_TELNET:
            return await self._handle_volume_command(cmd)
        if cmd in SOUND_MODE_COMMANDS_TELNET:
            return await self._handle_sound_mode_command(cmd)
        if cmd in AUDYSSEY_COMMANDS:
            return await self._handle_audyssey_command(cmd)
        if cmd in DIRAC_COMMANDS:
            return await self._handle_dirac_command(cmd)

        # Unknown command, validate the string before sending
        # Denon/Marantz API only supports length (COMMAND + PARAMETER[25]) with ascii 0x20-0x7F
        # Add some buffer to the length to support the command text and spaces
        if len(cmd) > 28 or (not all(0x20 <= ord(c) <= 0x7F for c in cmd)):
            return ucapi.StatusCodes.BAD_REQUEST

        return await self._send_command(cmd)

    async def _handle_core_command(self, cmd: str) -> ucapi.StatusCodes:
        # pylint: disable=R0915
        match cmd:
            case CoreCommands.OUTPUT_1:
                await self._receiver.async_hdmi_output("HDMI1")
            case CoreCommands.OUTPUT_2:
                await self._receiver.async_hdmi_output("HDMI2")
            case CoreCommands.OUTPUT_AUTO:
                await self._receiver.async_hdmi_output("Auto")
            case CoreCommands.DIMMER_TOGGLE:
                await self._receiver.async_dimmer_toggle()
            case CoreCommands.DIMMER_BRIGHT:
                await self._receiver.async_dimmer("Bright")
            case CoreCommands.DIMMER_DIM:
                await self._receiver.async_dimmer("Dim")
            case CoreCommands.DIMMER_DARK:
                await self._receiver.async_dimmer("Dark")
            case CoreCommands.DIMMER_OFF:
                await self._receiver.async_dimmer("Off")
            case CoreCommands.TRIGGER1_ON:
                await self._receiver.async_trigger_on(1)
            case CoreCommands.TRIGGER1_OFF:
                await self._receiver.async_trigger_off(1)
            case CoreCommands.TRIGGER2_ON:
                await self._receiver.async_trigger_on(2)
            case CoreCommands.TRIGGER2_OFF:
                await self._receiver.async_trigger_off(2)
            case CoreCommands.TRIGGER3_ON:
                await self._receiver.async_trigger_on(3)
            case CoreCommands.TRIGGER3_OFF:
                await self._receiver.async_trigger_off(3)
            case CoreCommands.DELAY_UP:
                await self._receiver.async_delay_up()
            case CoreCommands.DELAY_DOWN:
                await self._receiver.async_delay_down()
            case CoreCommands.ECO_AUTO:
                await self._receiver.async_eco_mode("Auto")
            case CoreCommands.ECO_ON:
                await self._receiver.async_eco_mode("On")
            case CoreCommands.ECO_OFF:
                await self._receiver.async_eco_mode("Off")
            case CoreCommands.INFO_MENU:
                await self._receiver.async_info()
            case CoreCommands.CHANNEL_LEVEL_ADJUST_MENU:
                await self._receiver.async_channel_level_adjust()
            case CoreCommands.AUTO_STANDBY_OFF:
                await self._receiver.async_auto_standby("OFF")
            case CoreCommands.AUTO_STANDBY_15MIN:
                await self._receiver.async_auto_standby("15M")
            case CoreCommands.AUTO_STANDBY_30MIN:
                await self._receiver.async_auto_standby("30M")
            case CoreCommands.AUTO_STANDBY_60MIN:
                await self._receiver.async_auto_standby("60M")
            case CoreCommands.DELAY_TIME_UP:
                await self._receiver.async_delay_time_up()
            case CoreCommands.DELAY_TIME_DOWN:
                await self._receiver.async_delay_time_down()
            case CoreCommands.HDMI_AUDIO_DECODE_AMP:
                await self._receiver.async_hdmi_audio_decode("AMP")
            case CoreCommands.HDMI_AUDIO_DECODE_TV:
                await self._receiver.async_hdmi_audio_decode("TV")
            case CoreCommands.VIDEO_PROCESSING_MODE_AUTO:
                await self._receiver.async_video_processing_mode("Auto")
            case CoreCommands.VIDEO_PROCESSING_MODE_GAME:
                await self._receiver.async_video_processing_mode("Game")
            case CoreCommands.VIDEO_PROCESSING_MODE_MOVIE:
                await self._receiver.async_video_processing_mode("Movie")
            case CoreCommands.VIDEO_PROCESSING_MODE_BYPASS:
                await self._receiver.async_video_processing_mode("Bypass")
            case CoreCommands.NETWORK_RESTART:
                await self._receiver.async_network_restart()
            case CoreCommands.SPEAKER_PRESET_1:
                await self._receiver.async_speaker_preset(1)
            case CoreCommands.SPEAKER_PRESET_2:
                await self._receiver.async_speaker_preset(2)
            case CoreCommands.SPEAKER_PRESET_TOGGLE:
                await self._receiver.async_speaker_preset_toggle()
            case CoreCommands.BT_TRANSMITTER_ON:
                await self._receiver.async_bt_transmitter_on()
            case CoreCommands.BT_TRANSMITTER_OFF:
                await self._receiver.async_bt_transmitter_off()
            case CoreCommands.BT_TRANSMITTER_TOGGLE:
                await self._receiver.async_bt_transmitter_toggle()
            case CoreCommands.BT_OUTPUT_MODE_BT_SPEAKER:
                await self._receiver.async_bt_output_mode("Bluetooth + Speakers")
            case CoreCommands.BT_OUTPUT_MODE_BT_ONLY:
                await self._receiver.async_bt_output_mode("Bluetooth Only")
            case CoreCommands.BT_OUTPUT_MODE_TOGGLE:
                await self._receiver.async_bt_output_mode_toggle()
            case CoreCommands.AUDIO_RESTORER_OFF:
                await self._receiver.async_audio_restorer("Off")
            case CoreCommands.AUDIO_RESTORER_LOW:
                await self._receiver.async_audio_restorer("Low")
            case CoreCommands.AUDIO_RESTORER_MEDIUM:
                await self._receiver.async_audio_restorer("Medium")
            case CoreCommands.AUDIO_RESTORER_HIGH:
                await self._receiver.async_audio_restorer("High")
            case CoreCommands.REMOTE_CONTROL_LOCK_ON:
                await self._receiver.async_remote_control_lock()
            case CoreCommands.REMOTE_CONTROL_LOCK_OFF:
                await self._receiver.async_remote_control_unlock()
            case CoreCommands.PANEL_LOCK_PANEL:
                await self._receiver.async_panel_lock("Panel")
            case CoreCommands.PANEL_LOCK_PANEL_VOLUME:
                await self._receiver.async_panel_lock("Panel + Master Volume")
            case CoreCommands.PANEL_LOCK_OFF:
                await self._receiver.async_panel_unlock()
            case CoreCommands.GRAPHIC_EQ_ON:
                await self._receiver.async_graphic_eq_on()
            case CoreCommands.GRAPHIC_EQ_OFF:
                await self._receiver.async_graphic_eq_off()
            case CoreCommands.GRAPHIC_EQ_TOGGLE:
                await self._receiver.async_graphic_eq_toggle()
            case CoreCommands.HEADPHONE_EQ_ON:
                await self._receiver.async_headphone_eq_on()
            case CoreCommands.HEADPHONE_EQ_OFF:
                await self._receiver.async_headphone_eq_off()
            case CoreCommands.HEADPHONE_EQ_TOGGLE:
                await self._receiver.async_headphone_eq_toggle()
            case CoreCommands.STATUS:
                await self._receiver.async_status()
            case CoreCommands.INPUT_PHONO:
                await self._send_command("SIPHONO")
            case CoreCommands.INPUT_CD:
                await self._send_command("SICD")
            case CoreCommands.INPUT_DVD:
                await self._send_command("SIDVD")
            case CoreCommands.INPUT_BD:
                await self._send_command("SIBD")
            case CoreCommands.INPUT_TV:
                await self._send_command("SITV")
            case CoreCommands.INPUT_SAT_CBL:
                await self._send_command("SISAT/CBL")
            case CoreCommands.INPUT_MPLAY:
                await self._send_command("SIMPLAY")
            case CoreCommands.INPUT_GAME:
                await self._send_command("SIGAME")
            case CoreCommands.INPUT_GAME1:
                await self._send_command("SIGAME1")
            case CoreCommands.INPUT_GAME2:
                await self._send_command("SIGAME2")
            case CoreCommands.INPUT_TUNER:
                await self._send_command("SITUNER")
            case CoreCommands.INPUT_8K:
                await self._send_command("SI8K")
            case CoreCommands.INPUT_AUX1:
                await self._send_command("SIAUX1")
            case CoreCommands.INPUT_AUX2:
                await self._send_command("SIAUX2")
            case CoreCommands.INPUT_AUX3:
                await self._send_command("SIAUX3")
            case CoreCommands.INPUT_AUX4:
                await self._send_command("SIAUX4")
            case CoreCommands.INPUT_AUX5:
                await self._send_command("SIAUX5")
            case CoreCommands.INPUT_AUX6:
                await self._send_command("SIAUX6")
            case CoreCommands.INPUT_AUX7:
                await self._send_command("SIAUX7")
            case CoreCommands.INPUT_NET:
                await self._send_command("SINET")
            case CoreCommands.INPUT_BT:
                await self._send_command("SIBT")
            case CoreCommands.QUICK_SELECT_1 | CoreCommands.SMART_SELECT_1:
                await self._receiver.async_quick_select_mode(1)
            case CoreCommands.QUICK_SELECT_2 | CoreCommands.SMART_SELECT_2:
                await self._receiver.async_quick_select_mode(2)
            case CoreCommands.QUICK_SELECT_3 | CoreCommands.SMART_SELECT_3:
                await self._receiver.async_quick_select_mode(3)
            case CoreCommands.QUICK_SELECT_4 | CoreCommands.SMART_SELECT_4:
                await self._receiver.async_quick_select_mode(4)
            case CoreCommands.QUICK_SELECT_5 | CoreCommands.SMART_SELECT_5:
                await self._receiver.async_quick_select_mode(5)

            case _:
                return ucapi.StatusCodes.NOT_IMPLEMENTED

        return ucapi.StatusCodes.OK

    async def _handle_volume_command(self, cmd: str) -> ucapi.StatusCodes:
        # pylint: disable=R0915
        match cmd:
            case VolumeCommands.FRONT_LEFT_UP:
                await self._receiver.vol.async_channel_volume_up("Front Left")
            case VolumeCommands.FRONT_LEFT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Front Left")
            case VolumeCommands.FRONT_RIGHT_UP:
                await self._receiver.vol.async_channel_volume_up("Front Right")
            case VolumeCommands.FRONT_RIGHT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Front Right")
            case VolumeCommands.CENTER_UP:
                await self._receiver.vol.async_channel_volume_up("Center")
            case VolumeCommands.CENTER_DOWN:
                await self._receiver.vol.async_channel_volume_down("Center")
            case VolumeCommands.SUB1_UP:
                await self._receiver.vol.async_channel_volume_up("Subwoofer")
            case VolumeCommands.SUB1_DOWN:
                await self._receiver.vol.async_channel_volume_down("Subwoofer")
            case VolumeCommands.SUB2_UP:
                await self._receiver.vol.async_channel_volume_up("Subwoofer 2")
            case VolumeCommands.SUB2_DOWN:
                await self._receiver.vol.async_channel_volume_down("Subwoofer 2")
            case VolumeCommands.SUB3_UP:
                await self._receiver.vol.async_channel_volume_up("Subwoofer 3")
            case VolumeCommands.SUB3_DOWN:
                await self._receiver.vol.async_channel_volume_down("Subwoofer 3")
            case VolumeCommands.SUB4_UP:
                await self._receiver.vol.async_channel_volume_up("Subwoofer 4")
            case VolumeCommands.SUB4_DOWN:
                await self._receiver.vol.async_channel_volume_down("Subwoofer 4")
            case VolumeCommands.SURROUND_LEFT_UP:
                await self._receiver.vol.async_channel_volume_up("Surround Left")
            case VolumeCommands.SURROUND_LEFT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Surround Left")
            case VolumeCommands.SURROUND_RIGHT_UP:
                await self._receiver.vol.async_channel_volume_up("Surround Right")
            case VolumeCommands.SURROUND_RIGHT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Surround Right")
            case VolumeCommands.SURROUND_BACK_LEFT_UP:
                await self._receiver.vol.async_channel_volume_up("Surround Back Left")
            case VolumeCommands.SURROUND_BACK_LEFT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Surround Back Left")
            case VolumeCommands.SURROUND_BACK_RIGHT_UP:
                await self._receiver.vol.async_channel_volume_up("Surround Back Right")
            case VolumeCommands.SURROUND_BACK_RIGHT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Surround Back Right")
            case VolumeCommands.FRONT_HEIGHT_LEFT_UP:
                await self._receiver.vol.async_channel_volume_up("Front Height Left")
            case VolumeCommands.FRONT_HEIGHT_LEFT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Front Height Left")
            case VolumeCommands.FRONT_HEIGHT_RIGHT_UP:
                await self._receiver.vol.async_channel_volume_up("Front Height Right")
            case VolumeCommands.FRONT_HEIGHT_RIGHT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Front Height Right")
            case VolumeCommands.FRONT_WIDE_LEFT_UP:
                await self._receiver.vol.async_channel_volume_up("Front Wide Left")
            case VolumeCommands.FRONT_WIDE_LEFT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Front Wide Left")
            case VolumeCommands.FRONT_WIDE_RIGHT_UP:
                await self._receiver.vol.async_channel_volume_up("Front Wide Right")
            case VolumeCommands.FRONT_WIDE_RIGHT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Front Wide Right")
            case VolumeCommands.TOP_FRONT_LEFT_UP:
                await self._receiver.vol.async_channel_volume_up("Top Front Left")
            case VolumeCommands.TOP_FRONT_LEFT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Top Front Left")
            case VolumeCommands.TOP_FRONT_RIGHT_UP:
                await self._receiver.vol.async_channel_volume_up("Top Front Right")
            case VolumeCommands.TOP_FRONT_RIGHT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Top Front Right")
            case VolumeCommands.TOP_MIDDLE_LEFT_UP:
                await self._receiver.vol.async_channel_volume_up("Top Middle Left")
            case VolumeCommands.TOP_MIDDLE_LEFT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Top Middle Left")
            case VolumeCommands.TOP_MIDDLE_RIGHT_UP:
                await self._receiver.vol.async_channel_volume_up("Top Middle Right")
            case VolumeCommands.TOP_MIDDLE_RIGHT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Top Middle Right")
            case VolumeCommands.TOP_REAR_LEFT_UP:
                await self._receiver.vol.async_channel_volume_up("Top Rear Left")
            case VolumeCommands.TOP_REAR_LEFT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Top Rear Left")
            case VolumeCommands.TOP_REAR_RIGHT_UP:
                await self._receiver.vol.async_channel_volume_up("Top Rear Right")
            case VolumeCommands.TOP_REAR_RIGHT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Top Rear Right")
            case VolumeCommands.REAR_HEIGHT_LEFT_UP:
                await self._receiver.vol.async_channel_volume_up("Rear Height Left")
            case VolumeCommands.REAR_HEIGHT_LEFT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Rear Height Left")
            case VolumeCommands.REAR_HEIGHT_RIGHT_UP:
                await self._receiver.vol.async_channel_volume_up("Rear Height Right")
            case VolumeCommands.REAR_HEIGHT_RIGHT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Rear Height Right")
            case VolumeCommands.FRONT_DOLBY_LEFT_UP:
                await self._receiver.vol.async_channel_volume_up("Front Dolby Left")
            case VolumeCommands.FRONT_DOLBY_LEFT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Front Dolby Left")
            case VolumeCommands.FRONT_DOLBY_RIGHT_UP:
                await self._receiver.vol.async_channel_volume_up("Front Dolby Right")
            case VolumeCommands.FRONT_DOLBY_RIGHT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Front Dolby Right")
            case VolumeCommands.SURROUND_DOLBY_LEFT_UP:
                await self._receiver.vol.async_channel_volume_up("Surround Dolby Left")
            case VolumeCommands.SURROUND_DOLBY_LEFT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Surround Dolby Left")
            case VolumeCommands.SURROUND_DOLBY_RIGHT_UP:
                await self._receiver.vol.async_channel_volume_up("Surround Dolby Right")
            case VolumeCommands.BACK_DOLBY_LEFT_UP:
                await self._receiver.vol.async_channel_volume_up("Back Dolby Left")
            case VolumeCommands.BACK_DOLBY_LEFT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Back Dolby Left")
            case VolumeCommands.BACK_DOLBY_RIGHT_UP:
                await self._receiver.vol.async_channel_volume_up("Back Dolby Right")
            case VolumeCommands.BACK_DOLBY_RIGHT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Back Dolby Right")
            case VolumeCommands.SURROUND_HEIGHT_LEFT_UP:
                await self._receiver.vol.async_channel_volume_up("Surround Height Left")
            case VolumeCommands.SURROUND_HEIGHT_LEFT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Surround Height Left")
            case VolumeCommands.SURROUND_HEIGHT_RIGHT_UP:
                await self._receiver.vol.async_channel_volume_up("Surround Height Right")
            case VolumeCommands.SURROUND_HEIGHT_RIGHT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Surround Height Right")
            case VolumeCommands.TOP_SURROUND_UP:
                await self._receiver.vol.async_channel_volume_up("Top Surround")
            case VolumeCommands.TOP_SURROUND_DOWN:
                await self._receiver.vol.async_channel_volume_down("Top Surround")
            case VolumeCommands.CENTER_HEIGHT_UP:
                await self._receiver.vol.async_channel_volume_up("Center Height")
            case VolumeCommands.CENTER_HEIGHT_DOWN:
                await self._receiver.vol.async_channel_volume_down("Center Height")
            case VolumeCommands.CHANNEL_VOLUMES_RESET:
                await self._receiver.vol.async_channel_volumes_reset()
            case VolumeCommands.SUBWOOFER_ON:
                await self._receiver.vol.async_subwoofer_on()
            case VolumeCommands.SUBWOOFER_OFF:
                await self._receiver.vol.async_subwoofer_off()
            case VolumeCommands.SUBWOOFER_TOGGLE:
                await self._receiver.vol.async_subwoofer_toggle()
            case VolumeCommands.SUBWOOFER1_LEVEL_UP:
                await self._receiver.vol.async_subwoofer_level_up("Subwoofer")
            case VolumeCommands.SUBWOOFER1_LEVEL_DOWN:
                await self._receiver.vol.async_subwoofer_level_down("Subwoofer")
            case VolumeCommands.SUBWOOFER2_LEVEL_UP:
                await self._receiver.vol.async_subwoofer_level_up("Subwoofer 2")
            case VolumeCommands.SUBWOOFER2_LEVEL_DOWN:
                await self._receiver.vol.async_subwoofer_level_down("Subwoofer 2")
            case VolumeCommands.SUBWOOFER3_LEVEL_UP:
                await self._receiver.vol.async_subwoofer_level_up("Subwoofer 3")
            case VolumeCommands.SUBWOOFER3_LEVEL_DOWN:
                await self._receiver.vol.async_subwoofer_level_down("Subwoofer 3")
            case VolumeCommands.SUBWOOFER4_LEVEL_UP:
                await self._receiver.vol.async_subwoofer_level_up("Subwoofer 4")
            case VolumeCommands.SUBWOOFER4_LEVEL_DOWN:
                await self._receiver.vol.async_subwoofer_level_down("Subwoofer 4")
            case VolumeCommands.LFE_UP:
                await self._receiver.vol.async_lfe_up()
            case VolumeCommands.LFE_DOWN:
                await self._receiver.vol.async_lfe_down()
            case VolumeCommands.BASS_SYNC_UP:
                await self._receiver.vol.async_bass_sync_up()
            case VolumeCommands.BASS_SYNC_DOWN:
                await self._receiver.vol.async_bass_sync_down()
            case _:
                return ucapi.StatusCodes.NOT_IMPLEMENTED

        return ucapi.StatusCodes.OK

    async def _handle_sound_mode_command(self, cmd: str) -> ucapi.StatusCodes:
        # pylint: disable=R0915, R0911
        match cmd:
            case SoundModeCommands.SURROUND_MODE_AUTO:
                return await self._send_command("MSAUTO")
            case SoundModeCommands.SURROUND_MODE_DIRECT:
                return await self._send_command("MSDIRECT")
            case SoundModeCommands.SURROUND_MODE_PURE_DIRECT:
                return await self._send_command("MSPURE DIRECT")
            case SoundModeCommands.SURROUND_MODE_DOLBY_DIGITAL:
                return await self._send_command("MSDOLBY DIGITAL")
            case SoundModeCommands.SURROUND_MODE_DTS_SURROUND:
                return await self._send_command("MSDTS SURROUND")
            case SoundModeCommands.SURROUND_MODE_AURO3D:
                return await self._send_command("MSAURO3D")
            case SoundModeCommands.SURROUND_MODE_AURO2DSURR:
                return await self._send_command("MSAURO2DSURR")
            case SoundModeCommands.SURROUND_MODE_MCH_STEREO:
                return await self._send_command("MSMCH STEREO")
            case SoundModeCommands.SURROUND_MODE_NEXT:
                await self._receiver.soundmode.async_sound_mode_next()
            case SoundModeCommands.SURROUND_MODE_PREVIOUS:
                await self._receiver.soundmode.async_sound_mode_previous()
            case SoundModeCommands.SOUND_MODE_NEURAL_X_ON:
                await self._receiver.soundmode.async_neural_x_on()
            case SoundModeCommands.SOUND_MODE_NEURAL_X_OFF:
                await self._receiver.soundmode.async_neural_x_off()
            case SoundModeCommands.SOUND_MODE_NEURAL_X_TOGGLE:
                await self._receiver.soundmode.async_neural_x_toggle()
            case SoundModeCommands.SOUND_MODE_IMAX_AUTO:
                await self._receiver.soundmode.async_imax_auto()
            case SoundModeCommands.SOUND_MODE_IMAX_OFF:
                await self._receiver.soundmode.async_imax_off()
            case SoundModeCommands.SOUND_MODE_IMAX_TOGGLE:
                await self._receiver.soundmode.async_imax_toggle()
            case SoundModeCommands.IMAX_AUDIO_SETTINGS_AUTO:
                await self._receiver.soundmode.async_imax_audio_settings("AUTO")
            case SoundModeCommands.IMAX_AUDIO_SETTINGS_MANUAL:
                await self._receiver.soundmode.async_imax_audio_settings("MANUAL")
            case SoundModeCommands.IMAX_AUDIO_SETTINGS_TOGGLE:
                await self._receiver.soundmode.async_imax_audio_settings_toggle()
            case SoundModeCommands.IMAX_HPF_40HZ:
                await self._receiver.soundmode.async_imax_hpf("40")
            case SoundModeCommands.IMAX_HPF_60HZ:
                await self._receiver.soundmode.async_imax_hpf("60")
            case SoundModeCommands.IMAX_HPF_80HZ:
                await self._receiver.soundmode.async_imax_hpf("80")
            case SoundModeCommands.IMAX_HPF_90HZ:
                await self._receiver.soundmode.async_imax_hpf("90")
            case SoundModeCommands.IMAX_HPF_100HZ:
                await self._receiver.soundmode.async_imax_hpf("100")
            case SoundModeCommands.IMAX_HPF_110HZ:
                await self._receiver.soundmode.async_imax_hpf("110")
            case SoundModeCommands.IMAX_HPF_120HZ:
                await self._receiver.soundmode.async_imax_hpf("120")
            case SoundModeCommands.IMAX_HPF_150HZ:
                await self._receiver.soundmode.async_imax_hpf("150")
            case SoundModeCommands.IMAX_HPF_180HZ:
                await self._receiver.soundmode.async_imax_hpf("180")
            case SoundModeCommands.IMAX_HPF_200HZ:
                await self._receiver.soundmode.async_imax_hpf("200")
            case SoundModeCommands.IMAX_HPF_250HZ:
                await self._receiver.soundmode.async_imax_hpf("250")
            case SoundModeCommands.IMAX_LPF_80HZ:
                await self._receiver.soundmode.async_imax_lpf("80")
            case SoundModeCommands.IMAX_LPF_90HZ:
                await self._receiver.soundmode.async_imax_lpf("90")
            case SoundModeCommands.IMAX_LPF_100HZ:
                await self._receiver.soundmode.async_imax_lpf("100")
            case SoundModeCommands.IMAX_LPF_110HZ:
                await self._receiver.soundmode.async_imax_lpf("110")
            case SoundModeCommands.IMAX_LPF_120HZ:
                await self._receiver.soundmode.async_imax_lpf("120")
            case SoundModeCommands.IMAX_LPF_150HZ:
                await self._receiver.soundmode.async_imax_lpf("150")
            case SoundModeCommands.IMAX_LPF_180HZ:
                await self._receiver.soundmode.async_imax_lpf("180")
            case SoundModeCommands.IMAX_LPF_200HZ:
                await self._receiver.soundmode.async_imax_lpf("200")
            case SoundModeCommands.IMAX_LPF_250HZ:
                await self._receiver.soundmode.async_imax_lpf("250")
            case SoundModeCommands.IMAX_SUBWOOFER_ON:
                await self._receiver.soundmode.async_imax_subwoofer_mode("ON")
            case SoundModeCommands.IMAX_SUBWOOFER_OFF:
                await self._receiver.soundmode.async_imax_subwoofer_mode("OFF")
            case SoundModeCommands.IMAX_SUBWOOFER_OUTPUT_LFE_MAIN:
                await self._receiver.soundmode.async_imax_subwoofer_output("L+M")
            case SoundModeCommands.IMAX_SUBWOOFER_OUTPUT_LFE:
                await self._receiver.soundmode.async_imax_subwoofer_output("LFE")
            case SoundModeCommands.CINEMA_EQ_ON:
                await self._receiver.soundmode.async_cinema_eq_on()
            case SoundModeCommands.CINEMA_EQ_OFF:
                await self._receiver.soundmode.async_cinema_eq_off()
            case SoundModeCommands.CINEMA_EQ_TOGGLE:
                await self._receiver.soundmode.async_cinema_eq_toggle()
            case SoundModeCommands.CENTER_SPREAD_ON:
                await self._receiver.soundmode.async_center_spread_on()
            case SoundModeCommands.CENTER_SPREAD_OFF:
                await self._receiver.soundmode.async_center_spread_off()
            case SoundModeCommands.CENTER_SPREAD_TOGGLE:
                await self._receiver.soundmode.async_center_spread_toggle()
            case SoundModeCommands.LOUDNESS_MANAGEMENT_ON:
                await self._receiver.soundmode.async_loudness_management_on()
            case SoundModeCommands.LOUDNESS_MANAGEMENT_OFF:
                await self._receiver.soundmode.async_loudness_management_off()
            case SoundModeCommands.LOUDNESS_MANAGEMENT_TOGGLE:
                await self._receiver.soundmode.async_loudness_management_toggle()
            case SoundModeCommands.DIALOG_ENHANCER_OFF:
                await self._receiver.soundmode.async_dialog_enhancer("Off")
            case SoundModeCommands.DIALOG_ENHANCER_LOW:
                await self._receiver.soundmode.async_dialog_enhancer("Low")
            case SoundModeCommands.DIALOG_ENHANCER_MEDIUM:
                await self._receiver.soundmode.async_dialog_enhancer("Medium")
            case SoundModeCommands.DIALOG_ENHANCER_HIGH:
                await self._receiver.soundmode.async_dialog_enhancer("High")
            case SoundModeCommands.AUROMATIC_3D_PRESET_SMALL:
                await self._receiver.soundmode.async_auromatic_3d_preset("Small")
            case SoundModeCommands.AUROMATIC_3D_PRESET_MEDIUM:
                await self._receiver.soundmode.async_auromatic_3d_preset("Medium")
            case SoundModeCommands.AUROMATIC_3D_PRESET_LARGE:
                await self._receiver.soundmode.async_auromatic_3d_preset("Large")
            case SoundModeCommands.AUROMATIC_3D_PRESET_SPEECH:
                await self._receiver.soundmode.async_auromatic_3d_preset("Speech")
            case SoundModeCommands.AUROMATIC_3D_PRESET_MOVIE:
                await self._receiver.soundmode.async_auromatic_3d_preset("Movie")
            case SoundModeCommands.AUROMATIC_3D_STRENGTH_UP:
                await self._receiver.soundmode.async_auromatic_3d_strength_up()
            case SoundModeCommands.AUROMATIC_3D_STRENGTH_DOWN:
                await self._receiver.soundmode.async_auromatic_3d_strength_down()
            case SoundModeCommands.AURO_3D_MODE_DIRECT:
                await self._receiver.soundmode.async_auro_3d_mode("Direct")
            case SoundModeCommands.AURO_3D_MODE_CHANNEL_EXPANSION:
                await self._receiver.soundmode.async_auro_3d_mode("Channel Expansion")
            case SoundModeCommands.DIALOG_CONTROL_UP:
                await self._receiver.soundmode.async_dialog_control_up()
            case SoundModeCommands.DIALOG_CONTROL_DOWN:
                await self._receiver.soundmode.async_dialog_control_down()
            case SoundModeCommands.SPEAKER_VIRTUALIZER_ON:
                await self._receiver.soundmode.async_speaker_virtualizer_on()
            case SoundModeCommands.SPEAKER_VIRTUALIZER_OFF:
                await self._receiver.soundmode.async_speaker_virtualizer_off()
            case SoundModeCommands.SPEAKER_VIRTUALIZER_TOGGLE:
                await self._receiver.soundmode.async_speaker_virtualizer_toggle()
            case SoundModeCommands.EFFECT_SPEAKER_SELECTION_FLOOR:
                await self._receiver.soundmode.async_effect_speaker_selection("Floor")
            case SoundModeCommands.EFFECT_SPEAKER_SELECTION_FRONT:
                await self._receiver.soundmode.async_effect_speaker_selection("Front")
            case SoundModeCommands.EFFECT_SPEAKER_SELECTION_FRONT_HEIGHT:
                await self._receiver.soundmode.async_effect_speaker_selection("Front Height")
            case SoundModeCommands.EFFECT_SPEAKER_SELECTION_FRONT_HEIGHT_WIDE:
                await self._receiver.soundmode.async_effect_speaker_selection("Front Height + Front Wide")
            case SoundModeCommands.EFFECT_SPEAKER_SELECTION_FRONT_WIDE:
                await self._receiver.soundmode.async_effect_speaker_selection("Front Wide")
            case SoundModeCommands.EFFECT_SPEAKER_SELECTION_HEIGHT_FLOOR:
                await self._receiver.soundmode.async_effect_speaker_selection("Height + Floor")
            case SoundModeCommands.EFFECT_SPEAKER_SELECTION_SURROUND_BACK:
                await self._receiver.soundmode.async_effect_speaker_selection("Surround Back")
            case SoundModeCommands.EFFECT_SPEAKER_SELECTION_SURROUND_BACK_FRONT_HEIGHT:
                await self._receiver.soundmode.async_effect_speaker_selection("Surround Back + Front Height")
            case SoundModeCommands.EFFECT_SPEAKER_SELECTION_SURROUND_BACK_FRONT_WIDE:
                await self._receiver.soundmode.async_effect_speaker_selection("Surround Back + Front Wide")
            case SoundModeCommands.DRC_AUTO:
                await self._receiver.soundmode.async_drc("AUTO")
            case SoundModeCommands.DRC_LOW:
                await self._receiver.soundmode.async_drc("LOW")
            case SoundModeCommands.DRC_MID:
                await self._receiver.soundmode.async_drc("MID")
            case SoundModeCommands.DRC_HI:
                await self._receiver.soundmode.async_drc("HI")
            case SoundModeCommands.DRC_OFF:
                await self._receiver.soundmode.async_drc("OFF")
            case _:
                return ucapi.StatusCodes.NOT_IMPLEMENTED

        return ucapi.StatusCodes.OK

    async def _handle_audyssey_command(self, cmd: str) -> ucapi.StatusCodes:
        # pylint: disable=R0911
        match cmd:
            case AudysseyCommands.MULTIEQ_REFERENCE:
                return await self._send_command("PSMULTEQ:AUDYSSEY")
            case AudysseyCommands.MULTIEQ_BYPASS_LR:
                return await self._send_command("PSMULTEQ:BYP.LR")
            case AudysseyCommands.MULTIEQ_FLAT:
                return await self._send_command("PSMULTEQ:FLAT")
            case AudysseyCommands.MULTIEQ_OFF:
                return await self._send_command("PSMULTEQ:OFF")
            case AudysseyCommands.DYNAMIC_EQ_ON:
                await self._receiver.audyssey.async_dynamiceq_on()
            case AudysseyCommands.DYNAMIC_EQ_OFF:
                await self._receiver.audyssey.async_dynamiceq_off()
            case AudysseyCommands.DYNAMIC_EQ_TOGGLE:
                await self._receiver.audyssey.async_toggle_dynamic_eq()
            case AudysseyCommands.AUDYSSEY_LFC:
                await self._receiver.audyssey.async_lfc_on()
            case AudysseyCommands.AUDYSSEY_LFC_OFF:
                await self._receiver.audyssey.async_lfc_off()
            case AudysseyCommands.DYNAMIC_VOLUME_OFF:
                await self._receiver.audyssey.async_set_dynamicvol("Off")
            case AudysseyCommands.DYNAMIC_VOLUME_LIGHT:
                await self._receiver.audyssey.async_set_dynamicvol("Light")
            case AudysseyCommands.DYNAMIC_VOLUME_MEDIUM:
                await self._receiver.audyssey.async_set_dynamicvol("Medium")
            case AudysseyCommands.DYNAMIC_VOLUME_HEAVY:
                await self._receiver.audyssey.async_set_dynamicvol("Heavy")
            case AudysseyCommands.CONTAINMENT_AMOUNT_UP:
                await self._receiver.audyssey.async_containment_amount_up()
            case AudysseyCommands.CONTAINMENT_AMOUNT_DOWN:
                await self._receiver.audyssey.async_containment_amount_down()
            case _:
                return ucapi.StatusCodes.NOT_IMPLEMENTED

        return ucapi.StatusCodes.OK

    async def _handle_dirac_command(self, cmd: str) -> ucapi.StatusCodes:
        # pylint: disable=R0911
        match cmd:
            case DiracCommands.DIRAC_LIVE_FILTER_SLOT1:
                await self._receiver.dirac.async_dirac_filter("Slot 1")
            case DiracCommands.DIRAC_LIVE_FILTER_SLOT2:
                await self._receiver.dirac.async_dirac_filter("Slot 2")
            case DiracCommands.DIRAC_LIVE_FILTER_SLOT3:
                await self._receiver.dirac.async_dirac_filter("Slot 3")
            case DiracCommands.DIRAC_LIVE_FILTER_OFF:
                await self._receiver.dirac.async_dirac_filter("Off")
            case _:
                return ucapi.StatusCodes.NOT_IMPLEMENTED

        return ucapi.StatusCodes.OK
