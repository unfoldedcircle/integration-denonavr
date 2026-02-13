"""
Select entity functions.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from typing import Any, get_args

import avr
import helpers
from config import AvrDevice, SelectType, create_entity_id
from denonavr.const import (
    DimmerModes,
    DiracFilters,
    DynamicVolumeSettings,
    EcoModes,
    HDMIOutputs,
    ReferenceLevelOffsets,
)
from entities import DenonEntity
from ucapi import EntityTypes, IntegrationAPI, Select, StatusCodes
from ucapi.media_player import Attributes as MediaAttr
from ucapi.select import Attributes, States

_LOG = logging.getLogger(__name__)

_dimmer_modes: list[DimmerModes] = list(get_args(DimmerModes))
_eco_modes: list[EcoModes] = list(get_args(EcoModes))
_hdmi_outputs: list[HDMIOutputs] = list(get_args(HDMIOutputs))
_dirac_filters: list[DiracFilters] = list(get_args(DiracFilters))
_speaker_presets = [1, 2]
_reference_level_offsets: list[ReferenceLevelOffsets] = list(get_args(ReferenceLevelOffsets))
_dynamic_volumes: list[DynamicVolumeSettings] = list(get_args(DynamicVolumeSettings))

# Mapping of an AVR state to a select entity state
# pylint: disable=R0801
SELECT_STATE_MAPPING = {
    avr.States.ON: States.ON,
    avr.States.OFF: States.ON,  # a select does not have an OFF state
    avr.States.PAUSED: States.ON,
    avr.States.PLAYING: States.ON,
    avr.States.UNAVAILABLE: States.UNAVAILABLE,
    avr.States.UNKNOWN: States.UNKNOWN,
}

_EMPTY_VALUE = "--"


# pylint: disable=protected-access
class DenonSelect(Select, DenonEntity):
    """Select entity for Denon AVR receivers."""

    def __init__(
        self,
        device: AvrDevice,
        receiver: avr.DenonDevice,
        api: IntegrationAPI,
        select_type: SelectType,
    ) -> None:
        """Initialize the DenonSelect entity."""
        self._receiver = receiver
        self._device = device
        self._select_type = select_type
        self._select_state_key = select_type + receiver.id

        # Configure select based on type
        identifier, name = self._get_select_config(select_type, device, receiver)
        super().__init__(
            identifier,
            name,
            attributes={
                Attributes.STATE: States.UNAVAILABLE,
                Attributes.CURRENT_OPTION: None,
                Attributes.OPTIONS: None,
            },
        )
        DenonEntity.__init__(self, api)

    SelectStates: dict[str, Any] = {}

    # pylint: disable=too-many-return-statements, too-many-branches
    async def command(self, cmd_id: str, params: dict[str, Any] | None = None, *, websocket: Any) -> StatusCodes:
        """
        Select entity command handler.

        Called by the integration-API if a command is sent to a configured select entity.

        Note: If the receiver is powered off, only input source select commands are processed.
        :param cmd_id: command
        :param params: optional command parameters
        :param websocket: websocket connection (not used)
        :return: status code of the command request
        """
        # Skip commands that can't be processed when receiver is off
        if self._receiver._receiver.state == "off" and self._select_type != SelectType.INPUT_SOURCE:
            _LOG.info("Skipping command for select %s because receiver is off", self._select_type)
            return StatusCodes.OK

        if cmd_id == "select_option":
            option = params.get("option", None) if params else None
            if option is None:
                _LOG.warning("No option provided for select_option command")
                return StatusCodes.BAD_REQUEST
            return await self._handle_option_command(option)
        if cmd_id == "select_first":
            return await self._handle_first_last_command(use_first=True)
        if cmd_id == "select_last":
            return await self._handle_first_last_command(use_first=False)
        if cmd_id == "select_next":
            cycle = params.get("cycle", False) if params else False
            return await self._handle_next_previous_command(use_next=True, cycle=cycle)
        if cmd_id == "select_previous":
            cycle = params.get("cycle", False) if params else False
            return await self._handle_next_previous_command(use_next=False, cycle=cycle)

        _LOG.warning("Unknown command %s", cmd_id)
        return StatusCodes.BAD_REQUEST

    def state_from_avr(self, avr_state: avr.States) -> States:
        """
        Convert AVR state to UC API select state.

        :param avr_state: Denon/Marantz AVR state
        :return: UC API select state
        """
        return SELECT_STATE_MAPPING.get(avr_state, States.UNKNOWN)

    def filter_changed_attributes(self, update: dict[str, Any]) -> dict[str, Any]:
        """
        Filter the given attributes from an AVR update and return only the changed values.

        For each update, the current select value is retrieved from the receiver and included in the returned
        dictionary if changed.

        :param update: dictionary containing the updated properties.
        :return: dictionary containing only the changed attributes.
        """
        attributes = {}

        if Attributes.STATE in update:
            state = self.state_from_avr(update[Attributes.STATE])
            attributes = helpers.key_update_helper(Attributes.STATE, state, attributes, self.attributes)

        current_option, options = self._get_select_value(update)

        attributes = helpers.key_update_helper(Attributes.CURRENT_OPTION, current_option, attributes, self.attributes)
        attributes = helpers.key_update_helper(Attributes.OPTIONS, options, attributes, self.attributes)

        return attributes

    async def _handle_option_command(self, option: Any) -> StatusCodes:
        try:
            match self._select_type:
                case SelectType.SOUND_MODE:
                    await self._receiver.select_sound_mode(option)
                case SelectType.INPUT_SOURCE:
                    await self._receiver.select_source(option)
                case SelectType.DIMMER:
                    await self._receiver._receiver.async_dimmer(option)
                case SelectType.ECO_MODE:
                    await self._receiver._receiver.async_eco_mode(option)
                case SelectType.MONITOR_OUTPUT:
                    await self._receiver._receiver.async_hdmi_output(option)
                case SelectType.DIRAC_FILTER:
                    await self._receiver._receiver.dirac.async_dirac_filter(option)
                case SelectType.SPEAKER_PRESET:
                    await self._receiver._receiver.async_speaker_preset(int(option))
                case SelectType.REFERENCE_LEVEL_OFFSET:
                    await self._receiver._receiver.async_set_reflevoffset(option)
                case SelectType.DYNAMIC_VOLUME:
                    await self._receiver._receiver.async_set_dynamicvol(option)

            return StatusCodes.OK

        except Exception as ex:  # pylint: disable=broad-exception-caught
            _LOG.error("Error executing select command for %s: %s", self._select_type.value, ex)
            return StatusCodes.SERVER_ERROR

    async def _handle_first_last_command(self, use_first: bool) -> StatusCodes:
        index = 0 if use_first else -1
        try:
            match self._select_type:
                case SelectType.SOUND_MODE:
                    await self._receiver.select_sound_mode(self._receiver.sound_mode_list[index])
                case SelectType.INPUT_SOURCE:
                    await self._receiver.select_source(self._receiver.source_list[index])
                case SelectType.DIMMER:
                    await self._receiver._receiver.async_dimmer(_dimmer_modes[index])
                case SelectType.ECO_MODE:
                    await self._receiver._receiver.async_eco_mode(_eco_modes[index])
                case SelectType.MONITOR_OUTPUT:
                    await self._receiver._receiver.async_hdmi_output(_hdmi_outputs[index])
                case SelectType.DIRAC_FILTER:
                    await self._receiver._receiver.dirac.async_dirac_filter(_dirac_filters[index])
                case SelectType.SPEAKER_PRESET:
                    await self._receiver._receiver.async_speaker_preset(_speaker_presets[index])
                case SelectType.REFERENCE_LEVEL_OFFSET:
                    await self._receiver._receiver.async_set_reflevoffset(_reference_level_offsets[index])
                case SelectType.DYNAMIC_VOLUME:
                    await self._receiver._receiver.async_set_dynamicvol(_dynamic_volumes[index])

            return StatusCodes.OK

        except Exception as ex:  # pylint: disable=broad-exception-caught
            _LOG.error("Error executing select command for %s: %s", self._select_type.value, ex)
            return StatusCodes.SERVER_ERROR

    async def _handle_next_previous_command(self, use_next: bool, cycle: bool) -> StatusCodes:
        def get_new_value(value: Any, index_list: list[Any]) -> Any | None:
            try:
                current_index = index_list.index(value)
            except ValueError:
                _LOG.error(
                    "Current value %s not found in options list for %s select",
                    value,
                    self._select_type.value,
                )
                return None
            new_index = current_index + 1 if use_next else current_index - 1
            if new_index < 0 or new_index >= len(index_list):
                if cycle:
                    new_index = 0 if use_next else len(index_list) - 1
                else:
                    return None
            return index_list[new_index]

        match self._select_type:
            case SelectType.SOUND_MODE:
                target_list = self._receiver.sound_mode_list
                current_value = self._receiver.sound_mode
            case SelectType.INPUT_SOURCE:
                target_list = self._receiver.source_list
                current_value = self._receiver.source
            case SelectType.DIMMER:
                target_list = _dimmer_modes
                current_value = self._receiver.dimmer
            case SelectType.ECO_MODE:
                target_list = _eco_modes
                current_value = self._receiver.eco_mode
            case SelectType.MONITOR_OUTPUT:
                target_list = _hdmi_outputs
                current_value = self._receiver._receiver.hdmi_output
            case SelectType.DIRAC_FILTER:
                target_list = _dirac_filters
                current_value = self._receiver._receiver.dirac.dirac_filter
            case SelectType.SPEAKER_PRESET:
                target_list = _speaker_presets
                current_value = self._receiver._receiver.speaker_preset
            case SelectType.REFERENCE_LEVEL_OFFSET:
                target_list = _reference_level_offsets
                current_value = self._receiver._receiver.reference_level_offset
            case SelectType.DYNAMIC_VOLUME:
                target_list = _dynamic_volumes
                current_value = self._receiver._receiver.dynamic_volume

        new_value = get_new_value(current_value, target_list)
        if new_value is None:
            _LOG.error("Index out of bounds for %s select and cycling is false", self._select_type.value)
            return StatusCodes.BAD_REQUEST

        try:
            match self._select_type:
                case SelectType.SOUND_MODE:
                    await self._receiver.select_sound_mode(new_value)
                case SelectType.INPUT_SOURCE:
                    await self._receiver.select_source(new_value)
                case SelectType.DIMMER:
                    await self._receiver._receiver.async_dimmer(new_value)  # type: ignore
                case SelectType.ECO_MODE:
                    await self._receiver._receiver.async_eco_mode(new_value)  # type: ignore
                case SelectType.MONITOR_OUTPUT:
                    await self._receiver._receiver.async_hdmi_output(new_value)  # type: ignore
                case SelectType.DIRAC_FILTER:
                    await self._receiver._receiver.dirac.async_dirac_filter(new_value)  # type: ignore
                case SelectType.SPEAKER_PRESET:
                    await self._receiver._receiver.async_speaker_preset(new_value)  # type: ignore
                case SelectType.REFERENCE_LEVEL_OFFSET:
                    await self._receiver._receiver.async_set_reflevoffset(new_value)  # type: ignore
                case SelectType.DYNAMIC_VOLUME:
                    await self._receiver._receiver.async_set_dynamicvol(new_value)  # type: ignore

            return StatusCodes.OK

        except Exception as ex:  # pylint: disable=broad-exception-caught
            _LOG.error("Error executing select command for %s: %s", self._select_type.value, ex)
            return StatusCodes.SERVER_ERROR

    @staticmethod
    def _get_select_config(select_type: SelectType, device: AvrDevice, receiver: avr.DenonDevice) -> tuple[str, str]:
        """Get select configuration based on type."""
        match select_type:
            case SelectType.SOUND_MODE:
                return (
                    create_entity_id(receiver.id, EntityTypes.SELECT, SelectType.SOUND_MODE.value),
                    f"{device.name} Sound Mode",
                )
            case SelectType.INPUT_SOURCE:
                return (
                    create_entity_id(receiver.id, EntityTypes.SELECT, SelectType.INPUT_SOURCE.value),
                    f"{device.name} Input Source",
                )
            case SelectType.DIMMER:
                return (
                    create_entity_id(receiver.id, EntityTypes.SELECT, SelectType.DIMMER.value),
                    f"{device.name} Dimmer",
                )
            case SelectType.ECO_MODE:
                return (
                    create_entity_id(receiver.id, EntityTypes.SELECT, SelectType.ECO_MODE.value),
                    f"{device.name} Eco Mode",
                )
            case SelectType.MONITOR_OUTPUT:
                return (
                    create_entity_id(receiver.id, EntityTypes.SELECT, SelectType.MONITOR_OUTPUT.value),
                    f"{device.name} Monitor Output",
                )
            case SelectType.DIRAC_FILTER:
                return (
                    create_entity_id(receiver.id, EntityTypes.SELECT, SelectType.DIRAC_FILTER.value),
                    f"{device.name} Dirac Filter",
                )
            case SelectType.SPEAKER_PRESET:
                return (
                    create_entity_id(receiver.id, EntityTypes.SELECT, SelectType.SPEAKER_PRESET.value),
                    f"{device.name} Speaker Preset",
                )
            case SelectType.REFERENCE_LEVEL_OFFSET:
                return (
                    create_entity_id(receiver.id, EntityTypes.SELECT, SelectType.REFERENCE_LEVEL_OFFSET.value),
                    f"{device.name} Reference Level",
                )
            case SelectType.DYNAMIC_VOLUME:
                return (
                    create_entity_id(receiver.id, EntityTypes.SELECT, SelectType.DYNAMIC_VOLUME.value),
                    f"{device.name} Dynamic Volume",
                )
            case _:
                raise ValueError(f"Unsupported select type: {select_type}")

    # pylint: disable=broad-exception-caught, too-many-return-statements, protected-access, too-many-locals
    # pylint: disable=too-many-statements
    def _get_select_value(self, update: dict[str, Any]) -> tuple[Any, list[Any] | None]:
        """Get the current value and unit for this select type."""
        if self._receiver._receiver.state == "off":
            # If receiver is turned off, clear stored select state
            if update.get(MediaAttr.STATE, None):
                self.SelectStates.pop(self._select_state_key, None)
            offline_options = (
                self._receiver.source_list if self._select_type == SelectType.INPUT_SOURCE else [_EMPTY_VALUE]
            )
            return self._update_state_and_create_return_value(_EMPTY_VALUE), offline_options

        try:
            if self._select_type == SelectType.SOUND_MODE:
                sound_mode = self._get_value_or_default(self._receiver.sound_mode, _EMPTY_VALUE)
                return self._update_state_and_create_return_value(sound_mode), self._receiver.sound_mode_list

            if self._select_type == SelectType.INPUT_SOURCE:
                input_source = self._get_value_or_default(self._receiver.source, _EMPTY_VALUE)
                return self._update_state_and_create_return_value(input_source), self._receiver.source_list

            if self._select_type == SelectType.DIMMER:
                dimmer_state = self._get_value_or_default(self._receiver.dimmer, _EMPTY_VALUE)
                return self._update_state_and_create_return_value(dimmer_state), _dimmer_modes

            if self._select_type == SelectType.ECO_MODE:
                eco_mode = self._get_value_or_default(self._receiver.eco_mode, _EMPTY_VALUE)
                return self._update_state_and_create_return_value(eco_mode), _eco_modes

            if self._select_type == SelectType.MONITOR_OUTPUT:
                monitor_output = self._get_value_or_default(self._receiver._receiver.hdmi_output, _EMPTY_VALUE)
                return self._update_state_and_create_return_value(monitor_output), _hdmi_outputs

            if self._select_type == SelectType.DIRAC_FILTER:
                dirac_filter = self._get_value_or_default(self._receiver._receiver.dirac.dirac_filter, _EMPTY_VALUE)
                return self._update_state_and_create_return_value(dirac_filter), _dirac_filters

            if self._select_type == SelectType.SPEAKER_PRESET:
                speaker_preset = self._get_value_or_default(self._receiver._receiver.speaker_preset, _EMPTY_VALUE)
                return self._update_state_and_create_return_value(speaker_preset), _speaker_presets

            if self._select_type == SelectType.REFERENCE_LEVEL_OFFSET:
                ref_level = self._get_value_or_default(self._receiver._receiver.reference_level_offset, _EMPTY_VALUE)
                return (
                    self._update_state_and_create_return_value(ref_level),
                    self._receiver._receiver.reference_level_offset_setting_list,
                )

            if self._select_type == SelectType.DYNAMIC_VOLUME:
                dynamic_vol = self._get_value_or_default(self._receiver._receiver.dynamic_volume, _EMPTY_VALUE)
                return (
                    self._update_state_and_create_return_value(dynamic_vol),
                    self._receiver._receiver.dynamic_volume_setting_list,
                )

        except Exception as ex:
            _LOG.warning("Error getting select value for %s: %s", self._select_type.value, ex)
            return None, None

        return None, None

    def _update_state_and_create_return_value(self, value: Any) -> Any:
        """Update select state and create return value."""
        if self._select_state_key in self.SelectStates:
            current_value = self.SelectStates[self._select_state_key]
            if current_value != value:
                self.SelectStates[self._select_state_key] = value
                return value
        else:
            self.SelectStates[self._select_state_key] = value
            return value

        return None

    @staticmethod
    def _get_value_or_default(value: Any, default: Any) -> Any:
        return value if value is not None else default


def create_selects(device: AvrDevice, receiver: avr.DenonDevice, api: IntegrationAPI) -> list[DenonSelect]:
    """
    Create all applicable select entities for the given receiver.

    :param device: Device configuration
    :param receiver: DenonDevice instance
    :param api: IntegrationAPI instance
    :return: List of select entities
    """
    selects = [
        DenonSelect(device, receiver, api, SelectType.SOUND_MODE),
        DenonSelect(device, receiver, api, SelectType.INPUT_SOURCE),
        DenonSelect(device, receiver, api, SelectType.REFERENCE_LEVEL_OFFSET),
        DenonSelect(device, receiver, api, SelectType.DYNAMIC_VOLUME),
        DenonSelect(device, receiver, api, SelectType.DIMMER),
        DenonSelect(device, receiver, api, SelectType.ECO_MODE),
    ]

    # Only create telnet-based selects if telnet is used
    if device.use_telnet:
        selects.append(DenonSelect(device, receiver, api, SelectType.MONITOR_OUTPUT))
        selects.append(DenonSelect(device, receiver, api, SelectType.SPEAKER_PRESET))
        if device.is_dirac_supported:
            selects.append(DenonSelect(device, receiver, api, SelectType.DIRAC_FILTER))

    return selects
