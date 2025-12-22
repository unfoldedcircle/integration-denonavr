"""
This module implements the Denon/Marantz AVR receiver communication of the Remote Two/3 integration driver.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

from enum import Enum

# pylint: disable=C0302
from typing import Awaitable, Callable

import denonavr
import ucapi
from command_constants import (
    AudysseyCommands,
    CoreCommands,
    DiracCommands,
    SoundModeCommands,
    VolumeCommands,
)
from config import AvrDevice


class DeviceProtocol(Enum):
    """Protocol Enum."""

    ALL = "All"
    TELNET = "Telnet"


class DeviceType(Enum):
    """Device Type Enum."""

    ALL = ("All",)
    DENON = "Denon"
    MARANTZ = "Marantz"


CORE_COMMANDS: dict[str, tuple[DeviceProtocol, DeviceType]] = {
    CoreCommands.OUTPUT_1: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.OUTPUT_2: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.OUTPUT_AUTO: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.DIMMER_TOGGLE: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.DIMMER_BRIGHT: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.DIMMER_DIM: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.DIMMER_DARK: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.DIMMER_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.TRIGGER1_ON: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.TRIGGER1_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.TRIGGER2_ON: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.TRIGGER2_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.TRIGGER3_ON: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.TRIGGER3_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.DELAY_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.DELAY_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.ECO_ON: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.ECO_AUTO: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.ECO_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INFO_MENU: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.CHANNEL_LEVEL_ADJUST_MENU: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.AUTO_STANDBY_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.AUTO_STANDBY_15MIN: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.AUTO_STANDBY_30MIN: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.AUTO_STANDBY_60MIN: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.DELAY_TIME_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.DELAY_TIME_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.HDMI_AUDIO_DECODE_AMP: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.HDMI_AUDIO_DECODE_TV: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.VIDEO_PROCESSING_MODE_AUTO: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.VIDEO_PROCESSING_MODE_GAME: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.VIDEO_PROCESSING_MODE_MOVIE: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.VIDEO_PROCESSING_MODE_BYPASS: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.NETWORK_RESTART: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.SPEAKER_PRESET_1: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.SPEAKER_PRESET_2: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.BT_TRANSMITTER_ON: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.BT_TRANSMITTER_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.BT_OUTPUT_MODE_BT_SPEAKER: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.BT_OUTPUT_MODE_BT_ONLY: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.AUDIO_RESTORER_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.AUDIO_RESTORER_LOW: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.AUDIO_RESTORER_MEDIUM: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.AUDIO_RESTORER_HIGH: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.REMOTE_CONTROL_LOCK_ON: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.REMOTE_CONTROL_LOCK_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.PANEL_LOCK_PANEL: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.PANEL_LOCK_PANEL_VOLUME: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.PANEL_LOCK_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.GRAPHIC_EQ_ON: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.GRAPHIC_EQ_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.HEADPHONE_EQ_ON: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.HEADPHONE_EQ_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_PHONO: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_CD: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_DVD: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_BD: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_TV: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_SAT_CBL: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_MPLAY: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_GAME: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_GAME1: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_GAME2: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_TUNER: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_8K: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_AUX1: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_AUX2: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_AUX3: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_AUX4: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_AUX5: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_AUX6: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_AUX7: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_NET: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_BT: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.INPUT_HD_RADIO: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.HDMI_CEC_ON: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.HDMI_CEC_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.SPEAKER_PRESET_TOGGLE: (DeviceProtocol.ALL, DeviceType.ALL),
    CoreCommands.BT_TRANSMITTER_TOGGLE: (DeviceProtocol.TELNET, DeviceType.ALL),
    CoreCommands.BT_OUTPUT_MODE_TOGGLE: (DeviceProtocol.TELNET, DeviceType.ALL),
    CoreCommands.GRAPHIC_EQ_TOGGLE: (DeviceProtocol.TELNET, DeviceType.ALL),
    CoreCommands.HEADPHONE_EQ_TOGGLE: (DeviceProtocol.TELNET, DeviceType.ALL),
    CoreCommands.QUICK_SELECT_1: (DeviceProtocol.ALL, DeviceType.DENON),
    CoreCommands.QUICK_SELECT_2: (DeviceProtocol.ALL, DeviceType.DENON),
    CoreCommands.QUICK_SELECT_3: (DeviceProtocol.ALL, DeviceType.DENON),
    CoreCommands.QUICK_SELECT_4: (DeviceProtocol.ALL, DeviceType.DENON),
    CoreCommands.QUICK_SELECT_5: (DeviceProtocol.ALL, DeviceType.DENON),
    CoreCommands.STATUS: (DeviceProtocol.ALL, DeviceType.DENON),
    CoreCommands.SMART_SELECT_1: (DeviceProtocol.ALL, DeviceType.MARANTZ),
    CoreCommands.SMART_SELECT_2: (DeviceProtocol.ALL, DeviceType.MARANTZ),
    CoreCommands.SMART_SELECT_3: (DeviceProtocol.ALL, DeviceType.MARANTZ),
    CoreCommands.SMART_SELECT_4: (DeviceProtocol.ALL, DeviceType.MARANTZ),
    CoreCommands.SMART_SELECT_5: (DeviceProtocol.ALL, DeviceType.MARANTZ),
    CoreCommands.ILLUMINATION_AUTO: (DeviceProtocol.ALL, DeviceType.MARANTZ),
    CoreCommands.ILLUMINATION_BRIGHT: (DeviceProtocol.ALL, DeviceType.MARANTZ),
    CoreCommands.ILLUMINATION_DIM: (DeviceProtocol.ALL, DeviceType.MARANTZ),
    CoreCommands.ILLUMINATION_DARK: (DeviceProtocol.ALL, DeviceType.MARANTZ),
    CoreCommands.ILLUMINATION_OFF: (DeviceProtocol.ALL, DeviceType.MARANTZ),
    CoreCommands.AUTO_LIP_SYNC_ON: (DeviceProtocol.ALL, DeviceType.MARANTZ),
    CoreCommands.AUTO_LIP_SYNC_OFF: (DeviceProtocol.ALL, DeviceType.MARANTZ),
}

SOUND_MODE_COMMANDS: dict[str, tuple[DeviceProtocol, DeviceType]] = {
    SoundModeCommands.SURROUND_MODE_AUTO: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.SURROUND_MODE_DIRECT: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.SURROUND_MODE_PURE_DIRECT: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.SURROUND_MODE_DOLBY_DIGITAL: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.SURROUND_MODE_DTS_SURROUND: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.SURROUND_MODE_AURO3D: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.SURROUND_MODE_AURO2DSURR: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.SURROUND_MODE_MCH_STEREO: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.SURROUND_MODE_STEREO: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.SURROUND_MODE_MONO: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.SURROUND_MODE_NEXT: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.SURROUND_MODE_PREVIOUS: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.SOUND_MODE_NEURAL_X_ON: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.SOUND_MODE_NEURAL_X_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.SOUND_MODE_IMAX_AUTO: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.SOUND_MODE_IMAX_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_AUDIO_SETTINGS_AUTO: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_AUDIO_SETTINGS_MANUAL: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_HPF_40HZ: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_HPF_60HZ: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_HPF_80HZ: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_HPF_90HZ: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_HPF_100HZ: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_HPF_110HZ: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_HPF_120HZ: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_HPF_150HZ: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_HPF_180HZ: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_HPF_200HZ: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_HPF_250HZ: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_LPF_80HZ: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_LPF_90HZ: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_LPF_100HZ: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_LPF_110HZ: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_LPF_120HZ: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_LPF_150HZ: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_LPF_180HZ: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_LPF_200HZ: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_LPF_250HZ: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_SUBWOOFER_ON: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_SUBWOOFER_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_SUBWOOFER_OUTPUT_LFE_MAIN: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.IMAX_SUBWOOFER_OUTPUT_LFE: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.CINEMA_EQ_ON: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.CINEMA_EQ_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.CENTER_SPREAD_ON: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.CENTER_SPREAD_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.LOUDNESS_MANAGEMENT_ON: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.LOUDNESS_MANAGEMENT_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.DIALOG_ENHANCER_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.DIALOG_ENHANCER_LOW: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.DIALOG_ENHANCER_MEDIUM: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.DIALOG_ENHANCER_HIGH: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.AUROMATIC_3D_PRESET_SMALL: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.AUROMATIC_3D_PRESET_MEDIUM: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.AUROMATIC_3D_PRESET_LARGE: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.AUROMATIC_3D_PRESET_SPEECH: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.AUROMATIC_3D_PRESET_MOVIE: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.AUROMATIC_3D_STRENGTH_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.AUROMATIC_3D_STRENGTH_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.AURO_3D_MODE_DIRECT: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.AURO_3D_MODE_CHANNEL_EXPANSION: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.DIALOG_CONTROL_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.DIALOG_CONTROL_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.SPEAKER_VIRTUALIZER_ON: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.SPEAKER_VIRTUALIZER_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.EFFECT_SPEAKER_SELECTION_FLOOR: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.EFFECT_SPEAKER_SELECTION_FRONT: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.EFFECT_SPEAKER_SELECTION_FRONT_HEIGHT: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.EFFECT_SPEAKER_SELECTION_FRONT_HEIGHT_WIDE: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.EFFECT_SPEAKER_SELECTION_FRONT_WIDE: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.EFFECT_SPEAKER_SELECTION_HEIGHT_FLOOR: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.EFFECT_SPEAKER_SELECTION_SURROUND_BACK: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.EFFECT_SPEAKER_SELECTION_SURROUND_BACK_FRONT_HEIGHT: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.EFFECT_SPEAKER_SELECTION_SURROUND_BACK_FRONT_WIDE: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.DRC_AUTO: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.DRC_LOW: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.DRC_MID: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.DRC_HI: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.DRC_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    SoundModeCommands.MDAX_OFF: (DeviceProtocol.ALL, DeviceType.MARANTZ),
    SoundModeCommands.MDAX_LOW: (DeviceProtocol.ALL, DeviceType.MARANTZ),
    SoundModeCommands.MDAX_MEDIUM: (DeviceProtocol.ALL, DeviceType.MARANTZ),
    SoundModeCommands.MDAX_HIGH: (DeviceProtocol.ALL, DeviceType.MARANTZ),
    SoundModeCommands.DAC_FILTER_MODE_1: (DeviceProtocol.ALL, DeviceType.MARANTZ),
    SoundModeCommands.DAC_FILTER_MODE_2: (DeviceProtocol.ALL, DeviceType.MARANTZ),
    SoundModeCommands.SOUND_MODE_NEURAL_X_TOGGLE: (DeviceProtocol.TELNET, DeviceType.ALL),
    SoundModeCommands.SOUND_MODE_IMAX_TOGGLE: (DeviceProtocol.TELNET, DeviceType.ALL),
    SoundModeCommands.IMAX_AUDIO_SETTINGS_TOGGLE: (DeviceProtocol.TELNET, DeviceType.ALL),
    SoundModeCommands.CINEMA_EQ_TOGGLE: (DeviceProtocol.TELNET, DeviceType.ALL),
    SoundModeCommands.CENTER_SPREAD_TOGGLE: (DeviceProtocol.TELNET, DeviceType.ALL),
    SoundModeCommands.LOUDNESS_MANAGEMENT_TOGGLE: (DeviceProtocol.TELNET, DeviceType.ALL),
    SoundModeCommands.SPEAKER_VIRTUALIZER_TOGGLE: (DeviceProtocol.TELNET, DeviceType.ALL),
}

AUDYSSEY_COMMANDS: dict[str, tuple[DeviceProtocol, DeviceType]] = {
    AudysseyCommands.MULTIEQ_REFERENCE: (DeviceProtocol.ALL, DeviceType.ALL),
    AudysseyCommands.MULTIEQ_BYPASS_LR: (DeviceProtocol.ALL, DeviceType.ALL),
    AudysseyCommands.MULTIEQ_FLAT: (DeviceProtocol.ALL, DeviceType.ALL),
    AudysseyCommands.MULTIEQ_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    AudysseyCommands.DYNAMIC_EQ_ON: (DeviceProtocol.ALL, DeviceType.ALL),
    AudysseyCommands.DYNAMIC_EQ_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    AudysseyCommands.DYNAMIC_EQ_TOGGLE: (DeviceProtocol.ALL, DeviceType.ALL),
    AudysseyCommands.AUDYSSEY_LFC: (DeviceProtocol.ALL, DeviceType.ALL),
    AudysseyCommands.AUDYSSEY_LFC_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    AudysseyCommands.AUDYSSEY_LFC_TOGGLE: (DeviceProtocol.ALL, DeviceType.ALL),
    AudysseyCommands.DYNAMIC_VOLUME_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    AudysseyCommands.DYNAMIC_VOLUME_LIGHT: (DeviceProtocol.ALL, DeviceType.ALL),
    AudysseyCommands.DYNAMIC_VOLUME_MEDIUM: (DeviceProtocol.ALL, DeviceType.ALL),
    AudysseyCommands.DYNAMIC_VOLUME_HEAVY: (DeviceProtocol.ALL, DeviceType.ALL),
    AudysseyCommands.CONTAINMENT_AMOUNT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    AudysseyCommands.CONTAINMENT_AMOUNT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
}

DIRAC_COMMANDS: dict[str, tuple[DeviceProtocol, DeviceType]] = {
    DiracCommands.DIRAC_LIVE_FILTER_SLOT1: (DeviceProtocol.ALL, DeviceType.ALL),
    DiracCommands.DIRAC_LIVE_FILTER_SLOT2: (DeviceProtocol.ALL, DeviceType.ALL),
    DiracCommands.DIRAC_LIVE_FILTER_SLOT3: (DeviceProtocol.ALL, DeviceType.ALL),
    DiracCommands.DIRAC_LIVE_FILTER_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
}

VOLUME_COMMANDS: dict[str, tuple[DeviceProtocol, DeviceType]] = {
    VolumeCommands.FRONT_LEFT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.FRONT_LEFT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.FRONT_RIGHT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.FRONT_RIGHT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.CENTER_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.CENTER_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SUB1_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SUB1_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SUB2_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SUB2_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SUB3_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SUB3_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SUB4_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SUB4_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SURROUND_LEFT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SURROUND_LEFT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SURROUND_RIGHT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SURROUND_RIGHT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SURROUND_BACK_LEFT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SURROUND_BACK_LEFT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SURROUND_BACK_RIGHT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SURROUND_BACK_RIGHT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.FRONT_HEIGHT_LEFT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.FRONT_HEIGHT_LEFT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.FRONT_HEIGHT_RIGHT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.FRONT_HEIGHT_RIGHT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.FRONT_WIDE_LEFT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.FRONT_WIDE_LEFT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.FRONT_WIDE_RIGHT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.FRONT_WIDE_RIGHT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.TOP_FRONT_LEFT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.TOP_FRONT_LEFT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.TOP_FRONT_RIGHT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.TOP_FRONT_RIGHT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.TOP_MIDDLE_LEFT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.TOP_MIDDLE_LEFT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.TOP_MIDDLE_RIGHT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.TOP_MIDDLE_RIGHT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.TOP_REAR_LEFT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.TOP_REAR_LEFT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.TOP_REAR_RIGHT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.TOP_REAR_RIGHT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.REAR_HEIGHT_LEFT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.REAR_HEIGHT_LEFT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.REAR_HEIGHT_RIGHT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.REAR_HEIGHT_RIGHT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.FRONT_DOLBY_LEFT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.FRONT_DOLBY_LEFT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.FRONT_DOLBY_RIGHT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.FRONT_DOLBY_RIGHT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SURROUND_DOLBY_LEFT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SURROUND_DOLBY_LEFT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SURROUND_DOLBY_RIGHT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SURROUND_DOLBY_RIGHT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.BACK_DOLBY_LEFT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.BACK_DOLBY_LEFT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.BACK_DOLBY_RIGHT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.BACK_DOLBY_RIGHT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SURROUND_HEIGHT_LEFT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SURROUND_HEIGHT_LEFT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SURROUND_HEIGHT_RIGHT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SURROUND_HEIGHT_RIGHT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.TOP_SURROUND_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.TOP_SURROUND_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.CENTER_HEIGHT_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.CENTER_HEIGHT_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.CHANNEL_VOLUMES_RESET: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SUBWOOFER_ON: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SUBWOOFER_OFF: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SUBWOOFER1_LEVEL_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SUBWOOFER1_LEVEL_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SUBWOOFER2_LEVEL_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SUBWOOFER2_LEVEL_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SUBWOOFER3_LEVEL_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SUBWOOFER3_LEVEL_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SUBWOOFER4_LEVEL_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SUBWOOFER4_LEVEL_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.LFE_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.LFE_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.BASS_SYNC_UP: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.BASS_SYNC_DOWN: (DeviceProtocol.ALL, DeviceType.ALL),
    VolumeCommands.SUBWOOFER_TOGGLE: (DeviceProtocol.TELNET, DeviceType.ALL),
}

ALL_COMMANDS: dict[str, tuple[DeviceProtocol, DeviceType]] = {
    **CORE_COMMANDS,
    **SOUND_MODE_COMMANDS,
    **AUDYSSEY_COMMANDS,
    **DIRAC_COMMANDS,
    **VOLUME_COMMANDS,
}


def get_simple_commands(device: AvrDevice):
    """Get the list of simple commands for the given device."""
    allowed_types = {DeviceType.ALL, DeviceType.DENON} if device.is_denon else {DeviceType.ALL, DeviceType.MARANTZ}
    allowed_protocols = {DeviceProtocol.ALL, DeviceProtocol.TELNET} if device.use_telnet else {DeviceProtocol.ALL}

    return [
        cmd
        for cmd, (protocol, device_type) in ALL_COMMANDS.items()
        if protocol in allowed_protocols and device_type in allowed_types
    ]


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
        if cmd in CORE_COMMANDS:
            return await self._handle_core_command(cmd)
        if cmd in VOLUME_COMMANDS:
            return await self._handle_volume_command(cmd)
        if cmd in SOUND_MODE_COMMANDS:
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
            case CoreCommands.INPUT_HD_RADIO:
                await self._send_command("SIHDRADIO")
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
            case CoreCommands.HDMI_CEC_ON:
                await self._receiver.async_hdmi_cec_on()
            case CoreCommands.HDMI_CEC_OFF:
                await self._receiver.async_hdmi_cec_off()
            case CoreCommands.ILLUMINATION_AUTO:
                await self._receiver.async_illumination("Auto")
            case CoreCommands.ILLUMINATION_BRIGHT:
                await self._receiver.async_illumination("Bright")
            case CoreCommands.ILLUMINATION_DIM:
                await self._receiver.async_illumination("Dim")
            case CoreCommands.ILLUMINATION_DARK:
                await self._receiver.async_illumination("Dark")
            case CoreCommands.ILLUMINATION_OFF:
                await self._receiver.async_illumination("Off")
            case CoreCommands.AUTO_LIP_SYNC_ON:
                await self._receiver.async_auto_lip_sync_on()
            case CoreCommands.AUTO_LIP_SYNC_OFF:
                await self._receiver.async_auto_lip_sync_off()
            case CoreCommands.INPUT_MODE_SELECT:
                await self._receiver.async_input_mode("Select")
            case CoreCommands.INPUT_MODE_AUTO:
                await self._receiver.async_input_mode("Auto")
            case CoreCommands.INPUT_MODE_HDMI:
                await self._receiver.async_input_mode("HDMI")
            case CoreCommands.INPUT_MODE_DIGITAL:
                await self._receiver.async_input_mode("Digital")
            case CoreCommands.INPUT_MODE_ANALOG:
                await self._receiver.async_input_mode("Analog")
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
            case SoundModeCommands.SURROUND_MODE_STEREO:
                return await self._send_command("MSSTEREO")
            case SoundModeCommands.SURROUND_MODE_STEREO:
                return await self._send_command("MSMONO MOVIE")
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
            case SoundModeCommands.MDAX_OFF:
                await self._receiver.soundmode.async_mdax("Off")
            case SoundModeCommands.MDAX_LOW:
                await self._receiver.soundmode.async_mdax("Low")
            case SoundModeCommands.MDAX_MEDIUM:
                await self._receiver.soundmode.async_mdax("Medium")
            case SoundModeCommands.MDAX_HIGH:
                await self._receiver.soundmode.async_mdax("High")
            case SoundModeCommands.DAC_FILTER_MODE_1:
                await self._receiver.soundmode.async_dac_filter("Mode 1")
            case SoundModeCommands.DAC_FILTER_MODE_2:
                await self._receiver.soundmode.async_dac_filter("Mode 2")
            case SoundModeCommands.DOLBY_ATMOS_TOGGLE:
                await self._receiver.soundmode.async_dolby_atmos_toggle()
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
