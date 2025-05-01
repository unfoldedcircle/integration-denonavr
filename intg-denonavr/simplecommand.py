"""
This module implements the Denon AVR receiver communication of the Remote Two integration driver.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

from typing import Awaitable, Callable

import denonavr
import ucapi

CORE_COMMANDS = {
    "OUTPUT_1",
    "OUTPUT_2",
    "OUTPUT_AUTO",
    "DIMMER_TOGGLE",
    "DIMMER_BRIGHT",
    "DIMMER_DIM",
    "DIMMER_DARK",
    "DIMMER_OFF",
    "TRIGGER1_ON",
    "TRIGGER1_OFF",
    "TRIGGER2_ON",
    "TRIGGER2_OFF",
    "TRIGGER3_ON",
    "TRIGGER3_OFF",
    "DELAY_UP",
    "DELAY_DOWN",
    "ECO_ON",
    "ECO_AUTO",
    "ECO_OFF",
    "INFO_MENU",
    "OPTIONS_MENU",
    "CHANNEL_LEVEL_ADJUST_MENU",
    "AUTO_STANDBY_OFF",
    "AUTO_STANDBY_15MIN",
    "AUTO_STANDBY_30MIN",
    "AUTO_STANDBY_60MIN",
    "DELAY_TIME_UP",
    "DELAY_TIME_DOWN",
    "HDMI_AUDIO_DECODE_AMP",
    "HDMI_AUDIO_DECODE_TV",
    "VIDEO_PROCESSING_MODE_AUTO",
    "VIDEO_PROCESSING_MODE_GAME",
    "VIDEO_PROCESSING_MODE_MOVIE",
    "VIDEO_PROCESSING_MODE_BYPASS",
    "NETWORK_RESTART",
    "SPEAKER_PRESET_1",
    "SPEAKER_PRESET_2",
    "BT_TRANSMITTER_ON",
    "BT_TRANSMITTER_OFF",
    "BT_OUTPUT_MODE_BT_SPEAKER",
    "BT_OUTPUT_MODE_BT_ONLY",
    "AUDIO_RESTORER_OFF",
    "AUDIO_RESTORER_LOW",
    "AUDIO_RESTORER_MEDIUM",
    "AUDIO_RESTORER_HIGH",
    "REMOTE_CONTROL_LOCK_ON",
    "REMOTE_CONTROL_LOCK_OFF",
    "PANEL_LOCK_PANEL",
    "PANEL_LOCK_PANEL_VOLUME",
    "PANEL_LOCK_OFF",
    "GRAPHIC_EQ_ON",
    "GRAPHIC_EQ_OFF",
    "HEADPHONE_EQ_ON",
    "HEADPHONE_EQ_OFF",
}

CORE_COMMANDS_TELNET = {
    *CORE_COMMANDS,
    "SPEAKER_PRESET_TOGGLE",
    "BT_TRANSMITTER_TOGGLE",
    "BT_OUTPUT_MODE_TOGGLE",
    "GRAPHIC_EQ_TOGGLE",
    "HEADPHONE_EQ_TOGGLE",
}

CORE_COMMANDS_DENON = {
    *CORE_COMMANDS,
    "STATUS",
}

CORE_COMMANDS_DENON_TELNET = {*CORE_COMMANDS_TELNET, "STATUS"}

SOUND_MODE_COMMANDS = {
    "SURROUND_MODE_AUTO",
    "SURROUND_MODE_DIRECT",
    "SURROUND_MODE_PURE_DIRECT",
    "SURROUND_MODE_DOLBY_DIGITAL",
    "SURROUND_MODE_DTS_SURROUND",
    "SURROUND_MODE_AURO3D",
    "SURROUND_MODE_AURO2DSURR",
    "SURROUND_MODE_MCH_STEREO",
    "SURROUND_MODE_NEXT",
    "SURROUND_MODE_PREVIOUS",
    "SOUND_MODE_NEURAL_X_ON",
    "SOUND_MODE_NEURAL_X_OFF",
    "SOUND_MODE_IMAX_AUTO",
    "SOUND_MODE_IMAX_OFF",
    "IMAX_AUDIO_SETTINGS_AUTO",
    "IMAX_AUDIO_SETTINGS_MANUAL",
    "IMAX_HPF_40HZ",
    "IMAX_HPF_60HZ",
    "IMAX_HPF_80HZ",
    "IMAX_HPF_90HZ",
    "IMAX_HPF_100HZ",
    "IMAX_HPF_110HZ",
    "IMAX_HPF_120HZ",
    "IMAX_HPF_150HZ",
    "IMAX_HPF_180HZ",
    "IMAX_HPF_200HZ",
    "IMAX_HPF_250HZ",
    "IMAX_LPF_80HZ",
    "IMAX_LPF_90HZ",
    "IMAX_LPF_100HZ",
    "IMAX_LPF_110HZ",
    "IMAX_LPF_120HZ",
    "IMAX_LPF_150HZ",
    "IMAX_LPF_180HZ",
    "IMAX_LPF_200HZ",
    "IMAX_LPF_250HZ",
    "IMAX_SUBWOOFER_ON",
    "IMAX_SUBWOOFER_OFF",
    "IMAX_SUBWOOFER_OUTPUT_LFE_MAIN",
    "IMAX_SUBWOOFER_OUTPUT_LFE",
    "CINEMA_EQ_ON",
    "CINEMA_EQ_OFF",
    "CENTER_SPREAD_ON",
    "CENTER_SPREAD_OFF",
    "LOUDNESS_MANAGEMENT_ON",
    "LOUDNESS_MANAGEMENT_OFF",
    "DIALOG_ENHANCER_OFF",
    "DIALOG_ENHANCER_LOW",
    "DIALOG_ENHANCER_MEDIUM",
    "DIALOG_ENHANCER_HIGH",
    "AUROMATIC_3D_PRESET_SMALL",
    "AUROMATIC_3D_PRESET_MEDIUM",
    "AUROMATIC_3D_PRESET_LARGE",
    "AUROMATIC_3D_PRESET_SPEECH",
    "AUROMATIC_3D_PRESET_MOVIE",
    "AUROMATIC_3D_STRENGTH_UP",
    "AUROMATIC_3D_STRENGTH_DOWN",
    "AURO_3D_MODE_DIRECT",
    "AURO_3D_MODE_CHANNEL_EXPANSION",
    "DIALOG_CONTROL_UP",
    "DIALOG_CONTROL_DOWN",
    "SPEAKER_VIRTUALIZER_ON",
    "SPEAKER_VIRTUALIZER_OFF",
    "EFFECT_SPEAKER_SELECTION_FLOOR",
    "EFFECT_SPEAKER_SELECTION_FRONT",
    "EFFECT_SPEAKER_SELECTION_FRONT_HEIGHT",
    "EFFECT_SPEAKER_SELECTION_FRONT_WIDE",
    "EFFECT_SPEAKER_SELECTION_HEIGHT_FLOOR",
    "EFFECT_SPEAKER_SELECTION_SURROUND_BACK",
    "EFFECT_SPEAKER_SELECTION_SURROUND_BACK_FRONT_HEIGHT",
    "EFFECT_SPEAKER_SELECTION_SURROUND_BACK_FRONT_WIDE",
    "DRC_AUTO",
    "DRC_LOW",
    "DRC_MID",
    "DRC_HI",
    "DRC_OFF",
}

SOUND_MODE_COMMANDS_TELNET = {
    *SOUND_MODE_COMMANDS,
    "SOUND_MODE_NEURAL_X_TOGGLE",
    "SOUND_MODE_IMAX_TOGGLE",
    "IMAX_AUDIO_SETTINGS_TOGGLE",
    "CINEMA_EQ_TOGGLE",
    "CENTER_SPREAD_TOGGLE",
    "LOUDNESS_MANAGEMENT_TOGGLE",
    "SPEAKER_VIRTUALIZER_TOGGLE",
}

AUDYSSEY_COMMANDS = {
    "MULTIEQ_REFERENCE",
    "MULTIEQ_BYPASS_LR",
    "MULTIEQ_FLAT",
    "MULTIEQ_OFF",
    "DYNAMIC_EQ_ON",
    "DYNAMIC_EQ_OFF",
    "DYNAMIC_EQ_TOGGLE",
    "AUDYSSEY_LFC",
    "AUDYSSEY_LFC_OFF",
    "AUDYSSEY_LFC_TOGGLE",
    "DYNAMIC_VOLUME_OFF",
    "DYNAMIC_VOLUME_LIGHT",
    "DYNAMIC_VOLUME_MEDIUM",
    "DYNAMIC_VOLUME_HEAVY",
    "CONTAINMENT_AMOUNT_UP",
    "CONTAINMENT_AMOUNT_DOWN",
}

DIRAC_COMMANDS = {
    "DIRAC_LIVE_FILTER_SLOT1",
    "DIRAC_LIVE_FILTER_SLOT2",
    "DIRAC_LIVE_FILTER_SLOT3",
    "DIRAC_LIVE_FILTER_OFF",
}

VOLUME_COMMANDS = {
    "FRONT_LEFT_UP",
    "FRONT_LEFT_DOWN",
    "FRONT_RIGHT_UP",
    "FRONT_RIGHT_DOWN",
    "CENTER_UP",
    "CENTER_DOWN",
    "SUB1_UP",
    "SUB1_DOWN",
    "SUB2_UP",
    "SUB2_DOWN",
    "SUB3_UP",
    "SUB3_DOWN",
    "SUB4_UP",
    "SUB4_DOWN",
    "SURROUND_LEFT_UP",
    "SURROUND_LEFT_DOWN",
    "SURROUND_RIGHT_UP",
    "SURROUND_RIGHT_DOWN",
    "SURROUND_BACK_LEFT_UP",
    "SURROUND_BACK_LEFT_DOWN",
    "SURROUND_BACK_RIGHT_UP",
    "SURROUND_BACK_RIGHT_DOWN",
    "FRONT_HEIGHT_LEFT_UP",
    "FRONT_HEIGHT_LEFT_DOWN",
    "FRONT_HEIGHT_RIGHT_UP",
    "FRONT_HEIGHT_RIGHT_DOWN",
    "FRONT_WIDE_LEFT_UP",
    "FRONT_WIDE_LEFT_DOWN",
    "FRONT_WIDE_RIGHT_UP",
    "FRONT_WIDE_RIGHT_DOWN",
    "TOP_FRONT_LEFT_UP",
    "TOP_FRONT_LEFT_DOWN",
    "TOP_FRONT_RIGHT_UP",
    "TOP_FRONT_RIGHT_DOWN",
    "TOP_MIDDLE_LEFT_UP",
    "TOP_MIDDLE_LEFT_DOWN",
    "TOP_MIDDLE_RIGHT_UP",
    "TOP_MIDDLE_RIGHT_DOWN",
    "TOP_REAR_LEFT_UP",
    "TOP_REAR_LEFT_DOWN",
    "TOP_REAR_RIGHT_UP",
    "TOP_REAR_RIGHT_DOWN",
    "REAR_HEIGHT_LEFT_UP",
    "REAR_HEIGHT_LEFT_DOWN",
    "REAR_HEIGHT_RIGHT_UP",
    "REAR_HEIGHT_RIGHT_DOWN",
    "FRONT_DOLBY_LEFT_UP",
    "FRONT_DOLBY_LEFT_DOWN",
    "FRONT_DOLBY_RIGHT_UP",
    "FRONT_DOLBY_RIGHT_DOWN",
    "SURROUND_DOLBY_LEFT_UP",
    "SURROUND_DOLBY_LEFT_DOWN",
    "SURROUND_DOLBY_RIGHT_UP",
    "SURROUND_DOLBY_RIGHT_DOWN",
    "BACK_DOLBY_LEFT_UP",
    "BACK_DOLBY_LEFT_DOWN",
    "BACK_DOLBY_RIGHT_UP",
    "BACK_DOLBY_RIGHT_DOWN",
    "SURROUND_HEIGHT_LEFT_UP",
    "SURROUND_HEIGHT_LEFT_DOWN",
    "SURROUND_HEIGHT_RIGHT_UP",
    "SURROUND_HEIGHT_RIGHT_DOWN",
    "TOP_SURROUND_UP",
    "TOP_SURROUND_DOWN",
    "CENTER_HEIGHT_UP",
    "CENTER_HEIGHT_DOWN",
    "CHANNEL_VOLUMES_RESET",
    "SUBWOOFER_ON",
    "SUBWOOFER_OFF",
    "SUBWOOFER1_LEVEL_UP",
    "SUBWOOFER1_LEVEL_DOWN",
    "SUBWOOFER2_LEVEL_UP",
    "SUBWOOFER2_LEVEL_DOWN",
    "SUBWOOFER3_LEVEL_UP",
    "SUBWOOFER3_LEVEL_DOWN",
    "SUBWOOFER4_LEVEL_UP",
    "SUBWOOFER4_LEVEL_DOWN",
    "LFE_UP",
    "LFE_DOWN",
    "BASS_SYNC_UP",
    "BASS_SYNC_DOWN",
}

VOLUME_COMMANDS_TELNET = {
    *VOLUME_COMMANDS,
    "SUBWOOFER_TOGGLE",
}

ALL_COMMANDS = {
    *CORE_COMMANDS,
    *SOUND_MODE_COMMANDS,
    *AUDYSSEY_COMMANDS,
    *DIRAC_COMMANDS,
    *VOLUME_COMMANDS,
}

ALL_COMMANDS_DENON = {
    # Same as ALL_COMMANDS but with STATUS
    *CORE_COMMANDS_DENON,
    *SOUND_MODE_COMMANDS,
    *AUDYSSEY_COMMANDS,
    *DIRAC_COMMANDS,
    *VOLUME_COMMANDS,
}

ALL_COMMANDS_TELNET = {
    # Same as ALL_COMMANDS but with support for toggle commands
    *CORE_COMMANDS_TELNET,
    *SOUND_MODE_COMMANDS_TELNET,
    *AUDYSSEY_COMMANDS,
    *DIRAC_COMMANDS,
    *VOLUME_COMMANDS_TELNET,
}

ALL_COMMANDS_TELNET_DENON = {
    # Same as ALL_COMMANDS_TELNET but with support for toggle commands and STATUS
    *CORE_COMMANDS_DENON_TELNET,
    *SOUND_MODE_COMMANDS_TELNET,
    *AUDYSSEY_COMMANDS,
    *DIRAC_COMMANDS,
    *VOLUME_COMMANDS_TELNET,
}


# pylint: disable=R0903
class SimpleCommand:
    """Handles mapping and sending of Simple Commands to the receiver."""

    def __init__(self, receiver: denonavr.DenonAVR, send_command: Callable[[str], Awaitable[ucapi.StatusCodes]]):
        """
        Create a SimpleCommand instance.

        :param receiver: Denon receiver instance
        :param send_command: Function to send a raw command to the receiver
        """
        self._receiver = receiver
        self._send_command = send_command

    async def send_simple_command(self, cmd: str) -> ucapi.StatusCodes:
        """Send a simple command to the AVR."""
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
        return ucapi.StatusCodes.NOT_IMPLEMENTED

    async def _handle_core_command(self, cmd: str) -> ucapi.StatusCodes:
        # pylint: disable=R0915
        match cmd:
            case "OUTPUT_1":
                await self._receiver.async_hdmi_output("HDMI1")
            case "OUTPUT_2":
                await self._receiver.async_hdmi_output("HDMI2")
            case "OUTPUT_AUTO":
                await self._receiver.async_hdmi_output("Auto")
            case "DIMMER_TOGGLE":
                await self._receiver.async_dimmer_toggle()
            case "DIMMER_BRIGHT":
                await self._receiver.async_dimmer("Bright")
            case "DIMMER_DIM":
                await self._receiver.async_dimmer("Dim")
            case "DIMMER_DARK":
                await self._receiver.async_dimmer("Dark")
            case "DIMMER_OFF":
                await self._receiver.async_dimmer("Off")
            case "TRIGGER1_ON":
                await self._receiver.async_trigger_on(1)
            case "TRIGGER1_OFF":
                await self._receiver.async_trigger_off(1)
            case "TRIGGER2_ON":
                await self._receiver.async_trigger_on(2)
            case "TRIGGER2_OFF":
                await self._receiver.async_trigger_off(2)
            case "TRIGGER3_ON":
                await self._receiver.async_trigger_on(3)
            case "TRIGGER3_OFF":
                await self._receiver.async_trigger_off(3)
            case "DELAY_UP":
                await self._receiver.async_delay_up()
            case "DELAY_DOWN":
                await self._receiver.async_delay_down()
            case "ECO_AUTO":
                await self._receiver.async_eco_mode("Auto")
            case "ECO_ON":
                await self._receiver.async_eco_mode("On")
            case "ECO_OFF":
                await self._receiver.async_eco_mode("Off")
            case "INFO_MENU":
                await self._receiver.async_info()
            case "OPTIONS_MENU":
                await self._receiver.async_options()
            case "CHANNEL_LEVEL_ADJUST_MENU":
                await self._receiver.async_channel_level_adjust()
            case "AUTO_STANDBY_OFF":
                await self._receiver.async_auto_standby("OFF")
            case "AUTO_STANDBY_15MIN":
                await self._receiver.async_auto_standby("15M")
            case "AUTO_STANDBY_30MIN":
                await self._receiver.async_auto_standby("30M")
            case "AUTO_STANDBY_60MIN":
                await self._receiver.async_auto_standby("60M")
            case "DELAY_TIME_UP":
                await self._receiver.async_delay_time_up()
            case "DELAY_TIME_DOWN":
                await self._receiver.async_delay_time_down()
            case "HDMI_AUDIO_DECODE_AMP":
                await self._receiver.async_hdmi_audio_decode("AMP")
            case "HDMI_AUDIO_DECODE_TV":
                await self._receiver.async_hdmi_audio_decode("TV")
            case "VIDEO_PROCESSING_MODE_AUTO":
                await self._receiver.async_video_processing_mode("Auto")
            case "VIDEO_PROCESSING_MODE_GAME":
                await self._receiver.async_video_processing_mode("Game")
            case "VIDEO_PROCESSING_MODE_MOVIE":
                await self._receiver.async_video_processing_mode("Movie")
            case "VIDEO_PROCESSING_MODE_BYPASS":
                await self._receiver.async_video_processing_mode("Bypass")
            case "NETWORK_RESTART":
                await self._receiver.async_network_restart()
            case "SPEAKER_PRESET_1":
                await self._receiver.async_speaker_preset(1)
            case "SPEAKER_PRESET_2":
                await self._receiver.async_speaker_preset(2)
            case "SPEAKER_PRESET_TOGGLE":
                await self._receiver.async_speaker_preset_toggle()
            case "BT_TRANSMITTER_ON":
                await self._receiver.async_bt_transmitter_on()
            case "BT_TRANSMITTER_OFF":
                await self._receiver.async_bt_transmitter_off()
            case "BT_TRANSMITTER_TOGGLE":
                await self._receiver.async_bt_transmitter_toggle()
            case "BT_OUTPUT_MODE_BT_SPEAKER":
                await self._receiver.async_bt_output_mode("Bluetooth + Speakers")
            case "BT_OUTPUT_MODE_BT_ONLY":
                await self._receiver.async_bt_output_mode("Bluetooth Only")
            case "BT_OUTPUT_MODE_TOGGLE":
                await self._receiver.async_bt_output_mode_toggle()
            case "AUDIO_RESTORER_OFF":
                await self._receiver.async_audio_restorer("Off")
            case "AUDIO_RESTORER_LOW":
                await self._receiver.async_audio_restorer("Low")
            case "AUDIO_RESTORER_MEDIUM":
                await self._receiver.async_audio_restorer("Medium")
            case "AUDIO_RESTORER_HIGH":
                await self._receiver.async_audio_restorer("High")
            case "REMOTE_CONTROL_LOCK_ON":
                await self._receiver.async_remote_control_lock()
            case "REMOTE_CONTROL_LOCK_OFF":
                await self._receiver.async_remote_control_unlock()
            case "PANEL_LOCK_PANEL":
                await self._receiver.async_panel_lock("Panel")
            case "PANEL_LOCK_PANEL_VOLUME":
                await self._receiver.async_panel_lock("Panel + Master Volume")
            case "PANEL_LOCK_OFF":
                await self._receiver.async_panel_unlock()
            case "GRAPHIC_EQ_ON":
                await self._receiver.async_graphic_eq_on()
            case "GRAPHIC_EQ_OFF":
                await self._receiver.async_graphic_eq_off()
            case "GRAPHIC_EQ_TOGGLE":
                await self._receiver.async_graphic_eq_toggle()
            case "HEADPHONE_EQ_ON":
                await self._receiver.async_headphone_eq_on()
            case "HEADPHONE_EQ_OFF":
                await self._receiver.async_headphone_eq_off()
            case "HEADPHONE_EQ_TOGGLE":
                await self._receiver.async_headphone_eq_toggle()
            case "STATUS":
                await self._receiver.async_status()
            case _:
                return ucapi.StatusCodes.NOT_IMPLEMENTED

        return ucapi.StatusCodes.OK

    async def _handle_volume_command(self, cmd: str) -> ucapi.StatusCodes:
        # pylint: disable=R0915
        match cmd:
            case "FRONT_LEFT_UP":
                await self._receiver.vol.async_channel_volume_up("Front Left")
            case "FRONT_LEFT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Front Left")
            case "FRONT_RIGHT_UP":
                await self._receiver.vol.async_channel_volume_up("Front Right")
            case "FRONT_RIGHT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Front Right")
            case "CENTER_UP":
                await self._receiver.vol.async_channel_volume_up("Center")
            case "CENTER_DOWN":
                await self._receiver.vol.async_channel_volume_down("Center")
            case "SUB1_UP":
                await self._receiver.vol.async_channel_volume_up("Subwoofer")
            case "SUB1_DOWN":
                await self._receiver.vol.async_channel_volume_down("Subwoofer")
            case "SUB2_UP":
                await self._receiver.vol.async_channel_volume_up("Subwoofer 2")
            case "SUB2_DOWN":
                await self._receiver.vol.async_channel_volume_down("Subwoofer 2")
            case "SUB3_UP":
                await self._receiver.vol.async_channel_volume_up("Subwoofer 3")
            case "SUB3_DOWN":
                await self._receiver.vol.async_channel_volume_down("Subwoofer 3")
            case "SUB4_UP":
                await self._receiver.vol.async_channel_volume_up("Subwoofer 4")
            case "SUB4_DOWN":
                await self._receiver.vol.async_channel_volume_down("Subwoofer 4")
            case "SURROUND_LEFT_UP":
                await self._receiver.vol.async_channel_volume_up("Surround Left")
            case "SURROUND_LEFT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Surround Left")
            case "SURROUND_RIGHT_UP":
                await self._receiver.vol.async_channel_volume_up("Surround Right")
            case "SURROUND_RIGHT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Surround Right")
            case "SURROUND_BACK_LEFT_UP":
                await self._receiver.vol.async_channel_volume_up("Surround Back Left")
            case "SURROUND_BACK_LEFT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Surround Back Left")
            case "SURROUND_BACK_RIGHT_UP":
                await self._receiver.vol.async_channel_volume_up("Surround Back Right")
            case "SURROUND_BACK_RIGHT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Surround Back Right")
            case "FRONT_HEIGHT_LEFT_UP":
                await self._receiver.vol.async_channel_volume_up("Front Height Left")
            case "FRONT_HEIGHT_LEFT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Front Height Left")
            case "FRONT_HEIGHT_RIGHT_UP":
                await self._receiver.vol.async_channel_volume_up("Front Height Right")
            case "FRONT_HEIGHT_RIGHT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Front Height Right")
            case "FRONT_WIDE_LEFT_UP":
                await self._receiver.vol.async_channel_volume_up("Front Wide Left")
            case "FRONT_WIDE_LEFT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Front Wide Left")
            case "FRONT_WIDE_RIGHT_UP":
                await self._receiver.vol.async_channel_volume_up("Front Wide Right")
            case "FRONT_WIDE_RIGHT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Front Wide Right")
            case "TOP_FRONT_LEFT_UP":
                await self._receiver.vol.async_channel_volume_up("Top Front Left")
            case "TOP_FRONT_LEFT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Top Front Left")
            case "TOP_FRONT_RIGHT_UP":
                await self._receiver.vol.async_channel_volume_up("Top Front Right")
            case "TOP_FRONT_RIGHT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Top Front Right")
            case "TOP_MIDDLE_LEFT_UP":
                await self._receiver.vol.async_channel_volume_up("Top Middle Left")
            case "TOP_MIDDLE_LEFT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Top Middle Left")
            case "TOP_MIDDLE_RIGHT_UP":
                await self._receiver.vol.async_channel_volume_up("Top Middle Right")
            case "TOP_MIDDLE_RIGHT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Top Middle Right")
            case "TOP_REAR_LEFT_UP":
                await self._receiver.vol.async_channel_volume_up("Top Rear Left")
            case "TOP_REAR_LEFT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Top Rear Left")
            case "TOP_REAR_RIGHT_UP":
                await self._receiver.vol.async_channel_volume_up("Top Rear Right")
            case "TOP_REAR_RIGHT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Top Rear Right")
            case "REAR_HEIGHT_LEFT_UP":
                await self._receiver.vol.async_channel_volume_up("Rear Height Left")
            case "REAR_HEIGHT_LEFT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Rear Height Left")
            case "REAR_HEIGHT_RIGHT_UP":
                await self._receiver.vol.async_channel_volume_up("Rear Height Right")
            case "REAR_HEIGHT_RIGHT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Rear Height Right")
            case "FRONT_DOLBY_LEFT_UP":
                await self._receiver.vol.async_channel_volume_up("Front Dolby Left")
            case "FRONT_DOLBY_LEFT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Front Dolby Left")
            case "FRONT_DOLBY_RIGHT_UP":
                await self._receiver.vol.async_channel_volume_up("Front Dolby Right")
            case "FRONT_DOLBY_RIGHT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Front Dolby Right")
            case "SURROUND_DOLBY_LEFT_UP":
                await self._receiver.vol.async_channel_volume_up("Surround Dolby Left")
            case "SURROUND_DOLBY_LEFT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Surround Dolby Left")
            case "SURROUND_DOLBY_RIGHT_UP":
                await self._receiver.vol.async_channel_volume_up("Surround Dolby Right")
            case "BACK_DOLBY_LEFT_UP":
                await self._receiver.vol.async_channel_volume_up("Back Dolby Left")
            case "BACK_DOLBY_LEFT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Back Dolby Left")
            case "BACK_DOLBY_RIGHT_UP":
                await self._receiver.vol.async_channel_volume_up("Back Dolby Right")
            case "BACK_DOLBY_RIGHT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Back Dolby Right")
            case "SURROUND_HEIGHT_LEFT_UP":
                await self._receiver.vol.async_channel_volume_up("Surround Height Left")
            case "SURROUND_HEIGHT_LEFT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Surround Height Left")
            case "SURROUND_HEIGHT_RIGHT_UP":
                await self._receiver.vol.async_channel_volume_up("Surround Height Right")
            case "SURROUND_HEIGHT_RIGHT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Surround Height Right")
            case "TOP_SURROUND_UP":
                await self._receiver.vol.async_channel_volume_up("Top Surround")
            case "TOP_SURROUND_DOWN":
                await self._receiver.vol.async_channel_volume_down("Top Surround")
            case "CENTER_HEIGHT_UP":
                await self._receiver.vol.async_channel_volume_up("Center Height")
            case "CENTER_HEIGHT_DOWN":
                await self._receiver.vol.async_channel_volume_down("Center Height")
            case "CHANNEL_VOLUMES_RESET":
                await self._receiver.vol.async_channel_volumes_reset()
            case "SUBWOOFER_ON":
                await self._receiver.vol.async_subwoofer_on()
            case "SUBWOOFER_OFF":
                await self._receiver.vol.async_subwoofer_off()
            case "SUBWOOFER_TOGGLE":
                await self._receiver.vol.async_subwoofer_toggle()
            case "SUBWOOFER1_LEVEL_UP":
                await self._receiver.vol.async_subwoofer_level_up("Subwoofer")
            case "SUBWOOFER1_LEVEL_DOWN":
                await self._receiver.vol.async_subwoofer_level_down("Subwoofer")
            case "SUBWOOFER2_LEVEL_UP":
                await self._receiver.vol.async_subwoofer_level_up("Subwoofer 2")
            case "SUBWOOFER2_LEVEL_DOWN":
                await self._receiver.vol.async_subwoofer_level_down("Subwoofer 2")
            case "SUBWOOFER3_LEVEL_UP":
                await self._receiver.vol.async_subwoofer_level_up("Subwoofer 3")
            case "SUBWOOFER3_LEVEL_DOWN":
                await self._receiver.vol.async_subwoofer_level_down("Subwoofer 3")
            case "SUBWOOFER4_LEVEL_UP":
                await self._receiver.vol.async_subwoofer_level_up("Subwoofer 4")
            case "SUBWOOFER4_LEVEL_DOWN":
                await self._receiver.vol.async_subwoofer_level_down("Subwoofer 4")
            case "LFE_UP":
                await self._receiver.vol.async_lfe_up()
            case "LFE_DOWN":
                await self._receiver.vol.async_lfe_down()
            case "BASS_SYNC_UP":
                await self._receiver.vol.async_bass_sync_up()
            case "BASS_SYNC_DOWN":
                await self._receiver.vol.async_bass_sync_down()
            case _:
                return ucapi.StatusCodes.NOT_IMPLEMENTED

        return ucapi.StatusCodes.OK

    async def _handle_sound_mode_command(self, cmd: str) -> ucapi.StatusCodes:
        # pylint: disable=R0915, R0911
        match cmd:
            case "SURROUND_MODE_AUTO":
                return await self._send_command("MSAUTO")
            case "SURROUND_MODE_DIRECT":
                return await self._send_command("MSDIRECT")
            case "SURROUND_MODE_PURE_DIRECT":
                return await self._send_command("MSPURE DIRECT")
            case "SURROUND_MODE_DOLBY_DIGITAL":
                return await self._send_command("MSDOLBY DIGITAL")
            case "SURROUND_MODE_DTS_SURROUND":
                return await self._send_command("MSDTS SURROUND")
            case "SURROUND_MODE_AURO3D":
                return await self._send_command("MSAURO3D")
            case "SURROUND_MODE_AURO2DSURR":
                return await self._send_command("MSAURO2DSURR")
            case "SURROUND_MODE_MCH_STEREO":
                return await self._send_command("MSMCH STEREO")
            case "SURROUND_MODE_NEXT":
                await self._receiver.soundmode.async_sound_mode_next()
            case "SURROUND_MODE_PREVIOUS":
                await self._receiver.soundmode.async_sound_mode_previous()
            case "SOUND_MODE_NEURAL_X_ON":
                await self._receiver.soundmode.async_neural_x_on()
            case "SOUND_MODE_NEURAL_X_OFF":
                await self._receiver.soundmode.async_neural_x_off()
            case "SOUND_MODE_NEURAL_X_TOGGLE":
                await self._receiver.soundmode.async_neural_x_toggle()
            case "SOUND_MODE_IMAX_AUTO":
                await self._receiver.soundmode.async_imax_auto()
            case "SOUND_MODE_IMAX_OFF":
                await self._receiver.soundmode.async_imax_off()
            case "SOUND_MODE_IMAX_TOGGLE":
                await self._receiver.soundmode.async_imax_toggle()
            case "IMAX_AUDIO_SETTINGS_AUTO":
                await self._receiver.soundmode.async_imax_audio_settings("AUTO")
            case "IMAX_AUDIO_SETTINGS_MANUAL":
                await self._receiver.soundmode.async_imax_audio_settings("MANUAL")
            case "IMAX_AUDIO_SETTINGS_TOGGLE":
                await self._receiver.soundmode.async_imax_audio_settings_toggle()
            case "IMAX_HPF_40HZ":
                await self._receiver.soundmode.async_imax_hpf("40")
            case "IMAX_HPF_60HZ":
                await self._receiver.soundmode.async_imax_hpf("60")
            case "IMAX_HPF_80HZ":
                await self._receiver.soundmode.async_imax_hpf("80")
            case "IMAX_HPF_90HZ":
                await self._receiver.soundmode.async_imax_hpf("90")
            case "IMAX_HPF_100HZ":
                await self._receiver.soundmode.async_imax_hpf("100")
            case "IMAX_HPF_110HZ":
                await self._receiver.soundmode.async_imax_hpf("110")
            case "IMAX_HPF_120HZ":
                await self._receiver.soundmode.async_imax_hpf("120")
            case "IMAX_HPF_150HZ":
                await self._receiver.soundmode.async_imax_hpf("150")
            case "IMAX_HPF_180HZ":
                await self._receiver.soundmode.async_imax_hpf("180")
            case "IMAX_HPF_200HZ":
                await self._receiver.soundmode.async_imax_hpf("200")
            case "IMAX_HPF_250HZ":
                await self._receiver.soundmode.async_imax_hpf("250")
            case "IMAX_LPF_80HZ":
                await self._receiver.soundmode.async_imax_lpf("80")
            case "IMAX_LPF_90HZ":
                await self._receiver.soundmode.async_imax_lpf("90")
            case "IMAX_LPF_100HZ":
                await self._receiver.soundmode.async_imax_lpf("100")
            case "IMAX_LPF_110HZ":
                await self._receiver.soundmode.async_imax_lpf("110")
            case "IMAX_LPF_120HZ":
                await self._receiver.soundmode.async_imax_lpf("120")
            case "IMAX_LPF_150HZ":
                await self._receiver.soundmode.async_imax_lpf("150")
            case "IMAX_LPF_180HZ":
                await self._receiver.soundmode.async_imax_lpf("180")
            case "IMAX_LPF_200HZ":
                await self._receiver.soundmode.async_imax_lpf("200")
            case "IMAX_LPF_250HZ":
                await self._receiver.soundmode.async_imax_lpf("250")
            case "IMAX_SUBWOOFER_ON":
                await self._receiver.soundmode.async_imax_subwoofer_mode("ON")
            case "IMAX_SUBWOOFER_OFF":
                await self._receiver.soundmode.async_imax_subwoofer_mode("OFF")
            case "IMAX_SUBWOOFER_OUTPUT_LFE_MAIN":
                await self._receiver.soundmode.async_imax_subwoofer_output("L+M")
            case "IMAX_SUBWOOFER_OUTPUT_LFE":
                await self._receiver.soundmode.async_imax_subwoofer_output("LFE")
            case "CINEMA_EQ_ON":
                await self._receiver.soundmode.async_cinema_eq_on()
            case "CINEMA_EQ_OFF":
                await self._receiver.soundmode.async_cinema_eq_off()
            case "CINEMA_EQ_TOGGLE":
                await self._receiver.soundmode.async_cinema_eq_toggle()
            case "CENTER_SPREAD_ON":
                await self._receiver.soundmode.async_center_spread_on()
            case "CENTER_SPREAD_OFF":
                await self._receiver.soundmode.async_center_spread_off()
            case "CENTER_SPREAD_TOGGLE":
                await self._receiver.soundmode.async_center_spread_toggle()
            case "LOUDNESS_MANAGEMENT_ON":
                await self._receiver.soundmode.async_loudness_management_on()
            case "LOUDNESS_MANAGEMENT_OFF":
                await self._receiver.soundmode.async_loudness_management_off()
            case "LOUDNESS_MANAGEMENT_TOGGLE":
                await self._receiver.soundmode.async_loudness_management_toggle()
            case "DIALOG_ENHANCER_OFF":
                await self._receiver.soundmode.async_dialog_enhancer("Off")
            case "DIALOG_ENHANCER_LOW":
                await self._receiver.soundmode.async_dialog_enhancer("Low")
            case "DIALOG_ENHANCER_MEDIUM":
                await self._receiver.soundmode.async_dialog_enhancer("Medium")
            case "DIALOG_ENHANCER_HIGH":
                await self._receiver.soundmode.async_dialog_enhancer("High")
            case "AUROMATIC_3D_PRESET_SMALL":
                await self._receiver.soundmode.async_auromatic_3d_preset("Small")
            case "AUROMATIC_3D_PRESET_MEDIUM":
                await self._receiver.soundmode.async_auromatic_3d_preset("Medium")
            case "AUROMATIC_3D_PRESET_LARGE":
                await self._receiver.soundmode.async_auromatic_3d_preset("Large")
            case "AUROMATIC_3D_PRESET_SPEECH":
                await self._receiver.soundmode.async_auromatic_3d_preset("Speech")
            case "AUROMATIC_3D_PRESET_MOVIE":
                await self._receiver.soundmode.async_auromatic_3d_preset("Movie")
            case "AUROMATIC_3D_STRENGTH_UP":
                await self._receiver.soundmode.async_auromatic_3d_strength_up()
            case "AUROMATIC_3D_STRENGTH_DOWN":
                await self._receiver.soundmode.async_auromatic_3d_strength_down()
            case "AURO_3D_MODE_DIRECT":
                await self._receiver.soundmode.async_auro_3d_mode("Direct")
            case "AURO_3D_MODE_CHANNEL_EXPANSION":
                await self._receiver.soundmode.async_auro_3d_mode("Channel Expansion")
            case "DIALOG_CONTROL_UP":
                await self._receiver.soundmode.async_dialog_control_up()
            case "DIALOG_CONTROL_DOWN":
                await self._receiver.soundmode.async_dialog_control_down()
            case "SPEAKER_VIRTUALIZER_ON":
                await self._receiver.soundmode.async_speaker_virtualizer_on()
            case "SPEAKER_VIRTUALIZER_OFF":
                await self._receiver.soundmode.async_speaker_virtualizer_off()
            case "SPEAKER_VIRTUALIZER_TOGGLE":
                await self._receiver.soundmode.async_speaker_virtualizer_toggle()
            case "EFFECT_SPEAKER_SELECTION_FLOOR":
                await self._receiver.soundmode.async_effect_speaker_selection("Floor")
            case "EFFECT_SPEAKER_SELECTION_FRONT":
                await self._receiver.soundmode.async_effect_speaker_selection("Front")
            case "EFFECT_SPEAKER_SELECTION_FRONT_HEIGHT":
                await self._receiver.soundmode.async_effect_speaker_selection("Front Height")
            case "EFFECT_SPEAKER_SELECTION_FRONT_HEIGHT_WIDE":
                await self._receiver.soundmode.async_effect_speaker_selection("Front Height + Front Wide")
            case "EFFECT_SPEAKER_SELECTION_FRONT_WIDE":
                await self._receiver.soundmode.async_effect_speaker_selection("Front Wide")
            case "EFFECT_SPEAKER_SELECTION_HEIGHT_FLOOR":
                await self._receiver.soundmode.async_effect_speaker_selection("Height + Floor")
            case "EFFECT_SPEAKER_SELECTION_SURROUND_BACK":
                await self._receiver.soundmode.async_effect_speaker_selection("Surround Back")
            case "EFFECT_SPEAKER_SELECTION_SURROUND_BACK_FRONT_HEIGHT":
                await self._receiver.soundmode.async_effect_speaker_selection("Surround Back + Front Height")
            case "EFFECT_SPEAKER_SELECTION_SURROUND_BACK_FRONT_WIDE":
                await self._receiver.soundmode.async_effect_speaker_selection("Surround Back + Front Wide")
            case "DRC_AUTO":
                await self._receiver.soundmode.async_drc("AUTO")
            case "DRC_LOW":
                await self._receiver.soundmode.async_drc("LOW")
            case "DRC_MID":
                await self._receiver.soundmode.async_drc("MID")
            case "DRC_HI":
                await self._receiver.soundmode.async_drc("HI")
            case "DRC_OFF":
                await self._receiver.soundmode.async_drc("OFF")
            case _:
                return ucapi.StatusCodes.NOT_IMPLEMENTED

        return ucapi.StatusCodes.OK

    async def _handle_audyssey_command(self, cmd: str) -> ucapi.StatusCodes:
        # pylint: disable=R0911
        match cmd:
            case "MULTIEQ_REFERENCE":
                return await self._send_command("PSMULTEQ:AUDYSSEY")
            case "MULTIEQ_BYPASS_LR":
                return await self._send_command("PSMULTEQ:BYP.LR")
            case "MULTIEQ_FLAT":
                return await self._send_command("PSMULTEQ:FLAT")
            case "MULTIEQ_OFF":
                return await self._send_command("PSMULTEQ:OFF")
            case "DYNAMIC_EQ_ON":
                await self._receiver.audyssey.async_dynamiceq_on()
            case "DYNAMIC_EQ_OFF":
                await self._receiver.audyssey.async_dynamiceq_off()
            case "DYNAMIC_EQ_TOGGLE":
                await self._receiver.audyssey.async_toggle_dynamic_eq()
            case "AUDYSSEY_LFC":
                await self._receiver.audyssey.async_lfc_on()
            case "AUDYSSEY_LFC_OFF":
                await self._receiver.audyssey.async_lfc_off()
            case "DYNAMIC_VOLUME_OFF":
                await self._receiver.audyssey.async_set_dynamicvol("Off")
            case "DYNAMIC_VOLUME_LIGHT":
                await self._receiver.audyssey.async_set_dynamicvol("Light")
            case "DYNAMIC_VOLUME_MEDIUM":
                await self._receiver.audyssey.async_set_dynamicvol("Medium")
            case "DYNAMIC_VOLUME_HEAVY":
                await self._receiver.audyssey.async_set_dynamicvol("Heavy")
            case "CONTAINMENT_AMOUNT_UP":
                await self._receiver.audyssey.async_containment_amount_up()
            case "CONTAINMENT_AMOUNT_DOWN":
                await self._receiver.audyssey.async_containment_amount_down()
            case _:
                return ucapi.StatusCodes.NOT_IMPLEMENTED

        return ucapi.StatusCodes.OK

    async def _handle_dirac_command(self, cmd: str) -> ucapi.StatusCodes:
        # pylint: disable=R0911
        match cmd:
            case "DIRAC_LIVE_FILTER_SLOT1":
                await self._receiver.dirac.async_dirac_filter("Slot 1")
            case "DIRAC_LIVE_FILTER_SLOT2":
                await self._receiver.dirac.async_dirac_filter("Slot 2")
            case "DIRAC_LIVE_FILTER_SLOT3":
                await self._receiver.dirac.async_dirac_filter("Slot 3")
            case "DIRAC_LIVE_FILTER_OFF":
                await self._receiver.dirac.async_dirac_filter("Off")
            case _:
                return ucapi.StatusCodes.NOT_IMPLEMENTED

        return ucapi.StatusCodes.OK
