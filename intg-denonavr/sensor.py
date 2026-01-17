"""
Sensor entity functions.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from typing import Any

import avr
import helpers
from config import AdditionalEventType, AvrDevice, SensorType, create_entity_id
from entities import DenonEntity
from ucapi import EntityTypes, IntegrationAPI, Sensor
from ucapi.media_player import Attributes as MediaAttr
from ucapi.sensor import Attributes, DeviceClasses, Options, States

_LOG = logging.getLogger(__name__)

# Mapping of an AVR state to a sensor entity state
SENSOR_STATE_MAPPING = {
    avr.States.ON: States.ON,
    avr.States.OFF: States.ON,  # a sensor does not have an OFF state
    avr.States.PAUSED: States.ON,
    avr.States.PLAYING: States.ON,
    avr.States.UNAVAILABLE: States.UNAVAILABLE,
    avr.States.UNKNOWN: States.UNKNOWN,
}


class DenonSensor(Sensor, DenonEntity):
    """Representation of a Denon/Marantz AVR Sensor entity."""

    def __init__(
        self, device: AvrDevice, receiver: avr.DenonDevice, api: IntegrationAPI, sensor_type: SensorType
    ) -> None:
        """Initialize the DenonSensor entity."""
        self._receiver = receiver
        self._device = device
        self._sensor_type = sensor_type

        # Configure sensor based on type
        sensor_config = self._get_sensor_config(sensor_type, device, receiver)

        super().__init__(
            identifier=sensor_config["id"],
            name=sensor_config["name"],
            features=[],
            attributes={
                Attributes.STATE: States.UNAVAILABLE,
                Attributes.VALUE: None,
                Attributes.UNIT: sensor_config.get("unit"),
            },
            device_class=sensor_config["device_class"],
            options=sensor_config.get("options", {}),
        )
        DenonEntity.__init__(self, api)

    def state_from_avr(self, avr_state: avr.States) -> States:
        """
        Convert AVR state to UC API sensor state.

        :param avr_state: Denon/Marantz AVR state
        :return: UC API sensor state
        """
        return SENSOR_STATE_MAPPING.get(avr_state, States.UNKNOWN)

    @staticmethod
    def _get_sensor_config(sensor_type: SensorType, device: AvrDevice, receiver: avr.DenonDevice) -> dict[str, Any]:
        """Get sensor configuration based on type."""
        sensor = {}
        match sensor_type:
            case SensorType.VOLUME_DB:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.VOLUME_DB.value),
                    "name": f"{device.name} Volume",
                    "device_class": DeviceClasses.CUSTOM,
                    "unit": "dB",
                    "options": {
                        Options.CUSTOM_UNIT: "dB",
                        Options.DECIMALS: 1,
                    },
                }
            case SensorType.SOUND_MODE:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.SOUND_MODE.value),
                    "name": f"{device.name} Audio Output",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.INPUT_SOURCE:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.INPUT_SOURCE.value),
                    "name": f"{device.name} Input Source",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.DIMMER:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.DIMMER.value),
                    "name": f"{device.name} Dimmer",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.ECO_MODE:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.ECO_MODE.value),
                    "name": f"{device.name} Eco Mode",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.SLEEP_TIMER:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.SLEEP_TIMER.value),
                    "name": f"{device.name} Sleep Timer",
                    "device_class": DeviceClasses.CUSTOM,
                    "unit": "",  # dynamically set in _get_sensor_value based on value
                }
            case SensorType.AUDIO_DELAY:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.AUDIO_DELAY.value),
                    "name": f"{device.name} Audio Delay",
                    "device_class": DeviceClasses.CUSTOM,
                    "unit": "ms",
                    "options": {
                        Options.CUSTOM_UNIT: "ms",
                        Options.DECIMALS: 0,
                    },
                }
            case SensorType.AUDIO_SIGNAL:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.AUDIO_SIGNAL.value),
                    "name": f"{device.name} Audio Signal",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.AUDIO_SAMPLING_RATE:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.AUDIO_SAMPLING_RATE.value),
                    "name": f"{device.name} Audio Sampling Rate",
                    "device_class": DeviceClasses.CUSTOM,
                    "options": {
                        Options.CUSTOM_UNIT: "kHz",
                    },
                }
            case SensorType.MUTE:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.MUTE.value),
                    "name": f"{device.name} Mute Status",
                    "device_class": DeviceClasses.BINARY,  # without a unit it's a generic on / off binary sensor
                }
            case SensorType.MONITOR_OUTPUT:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.MONITOR_OUTPUT.value),
                    "name": f"{device.name} Video Out Port",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.VIDEO_HDMI_SIGNAL_IN:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.VIDEO_HDMI_SIGNAL_IN.value),
                    "name": f"{device.name} Video In Format",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.VIDEO_HDMI_SIGNAL_OUT:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.VIDEO_HDMI_SIGNAL_OUT.value),
                    "name": f"{device.name} Video Out Format",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.INPUT_CHANNELS:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.INPUT_CHANNELS.value),
                    "name": f"{device.name} Input Channels (Beta)",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.OUTPUT_CHANNELS:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.OUTPUT_CHANNELS.value),
                    "name": f"{device.name} Output Channels (Beta)",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.MAX_RESOLUTION:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.MAX_RESOLUTION.value),
                    "name": f"{device.name} Resolution/Bandwidth",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.HDR_INPUT:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.HDR_INPUT.value),
                    "name": f"{device.name} HDR Input",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.HDR_OUTPUT:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.HDR_OUTPUT.value),
                    "name": f"{device.name} HDR Output",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.PIXEL_DEPTH_INPUT:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.PIXEL_DEPTH_INPUT.value),
                    "name": f"{device.name} Pixel Depth Input",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.PIXEL_DEPTH_OUTPUT:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.PIXEL_DEPTH_OUTPUT.value),
                    "name": f"{device.name} Pixel Depth Output",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.MAX_FRL_INPUT:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.MAX_FRL_INPUT.value),
                    "name": f"{device.name} Max FRL Input",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.MAX_FRL_OUTPUT:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.MAX_FRL_OUTPUT.value),
                    "name": f"{device.name} Max FRL Output",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case _:
                raise ValueError(f"Unsupported sensor type: {sensor_type}")
        return sensor

    def filter_changed_attributes(self, update: dict[str, Any]) -> dict[str, Any]:
        """
        Filter the given attributes from an AVR update and return only the changed values.

        For each update, the current sensor value is retrieved from the receiver and included in the returned
        dictionary if changed.

        :param update: dictionary containing the updated properties.
        :return: dictionary containing only the changed attributes.
        """
        attributes = {}

        if Attributes.STATE in update:
            state = self.state_from_avr(update[Attributes.STATE])
            attributes = helpers.key_update_helper(Attributes.STATE, state, attributes, self.attributes)

        value, unit = self._get_sensor_value(update)

        attributes = helpers.key_update_helper(Attributes.VALUE, value, attributes, self.attributes)
        attributes = helpers.key_update_helper(Attributes.UNIT, unit, attributes, self.attributes)

        return attributes

    SensorStates: dict[SensorType, Any] = {}

    # pylint: disable=broad-exception-caught, too-many-return-statements, protected-access, too-many-locals
    # pylint: disable=too-many-statements
    def _get_sensor_value(self, update: dict[str, Any]) -> tuple[Any, str | None]:
        """Get the current value and unit for this sensor type."""
        if self._receiver._receiver.state == "off":
            # If receiver is turned off, clear stored sensor state
            if update.get(MediaAttr.STATE, None):
                self.SensorStates.pop(self._sensor_type, None)
            if self._sensor_type not in (SensorType.MONITOR_OUTPUT, SensorType.INPUT_SOURCE):
                return self._update_state_and_create_return_value("--"), None

        try:
            if self._sensor_type == SensorType.VOLUME_DB:
                volume = self._get_value_or_default(self._receiver._receiver.volume, 0.0)
                return self._update_state_and_create_return_value(volume), None

            if self._sensor_type == SensorType.SOUND_MODE:
                # Prefer audio_sound as it works better with online music sources
                sound_mode = self._get_value_or_default(
                    self._receiver._receiver.audio_sound, update.get(AdditionalEventType.RAW_SOUND_MODE, None)
                )
                if sound_mode is None:
                    return None, None
                return self._update_state_and_create_return_value(sound_mode), None

            if self._sensor_type == SensorType.INPUT_SOURCE:
                input_source = self._get_value_or_default(self._receiver._receiver.input_func, "--")
                return self._update_state_and_create_return_value(input_source), None

            if self._sensor_type == SensorType.DIMMER:
                dimmer_state = self._get_value_or_default(self._receiver._receiver.dimmer, "--")
                return self._update_state_and_create_return_value(dimmer_state), None

            if self._sensor_type == SensorType.ECO_MODE:
                eco_mode = self._get_value_or_default(self._receiver._receiver.eco_mode, "--")
                return self._update_state_and_create_return_value(eco_mode), None

            if self._sensor_type == SensorType.SLEEP_TIMER:
                sleep = update.get(AdditionalEventType.SLEEP_TIMER, self._receiver._receiver.sleep)
                if sleep is not None:
                    if isinstance(sleep, int):
                        return self._update_state_and_create_return_value(sleep), "min"
                return self._update_state_and_create_return_value("Off"), ""  # clear 'min' unit

            if self._sensor_type == SensorType.AUDIO_DELAY:
                audio_delay = self._get_value_or_default(self._receiver._receiver.delay, 0)
                return self._update_state_and_create_return_value(audio_delay), None

            if self._sensor_type == SensorType.AUDIO_SIGNAL:
                audio_signal = self._get_value_or_default(self._receiver._receiver.audio_signal, "--")
                return self._update_state_and_create_return_value(audio_signal), None

            if self._sensor_type == SensorType.AUDIO_SAMPLING_RATE:
                audio_sampling_rate = self._get_value_or_default(self._receiver._receiver.audio_sampling_rate, "--")
                return self._update_state_and_create_return_value(audio_sampling_rate), None

            if self._sensor_type == SensorType.MUTE:
                on_off = "on" if self._receiver._receiver.muted else "off"
                return self._update_state_and_create_return_value(on_off), None

            if self._sensor_type == SensorType.MONITOR_OUTPUT:
                monitor_output = self._get_value_or_default(self._receiver._receiver.hdmi_output, "--")
                return self._update_state_and_create_return_value(monitor_output), None

            if self._sensor_type == SensorType.VIDEO_HDMI_SIGNAL_IN:
                hdmi_in_signal = self._get_value_or_default(self._receiver._receiver.video_hdmi_signal_in, "--")
                return self._update_state_and_create_return_value(hdmi_in_signal), None

            if self._sensor_type == SensorType.VIDEO_HDMI_SIGNAL_OUT:
                hdmi_out_signal = self._get_value_or_default(self._receiver._receiver.video_hdmi_signal_out, "--")
                return self._update_state_and_create_return_value(hdmi_out_signal), None

            if self._sensor_type == SensorType.INPUT_CHANNELS:
                input_channels = self._get_value_or_default(self._receiver._receiver.input_channels, "--")
                return self._update_state_and_create_return_value(input_channels), None

            if self._sensor_type == SensorType.OUTPUT_CHANNELS:
                output_channels = self._get_value_or_default(self._receiver._receiver.output_channels, "--")
                return self._update_state_and_create_return_value(output_channels), None

            if self._sensor_type == SensorType.MAX_RESOLUTION:
                max_resolution = self._get_value_or_default(self._receiver._receiver.max_resolution, "--")
                return self._update_state_and_create_return_value(max_resolution), None

            if self._sensor_type == SensorType.HDR_INPUT:
                hdr_input = self._get_value_or_default(self._receiver._receiver.hdr_input, "--")
                return self._update_state_and_create_return_value(hdr_input), None

            if self._sensor_type == SensorType.HDR_OUTPUT:
                hdr_output = self._get_value_or_default(self._receiver._receiver.hdr_output, "--")
                return self._update_state_and_create_return_value(hdr_output), None

            if self._sensor_type == SensorType.PIXEL_DEPTH_INPUT:
                pixel_depth_input = self._get_value_or_default(self._receiver._receiver.pixel_depth_input, "--")
                return self._update_state_and_create_return_value(pixel_depth_input), None

            if self._sensor_type == SensorType.PIXEL_DEPTH_OUTPUT:
                pixel_depth_output = self._get_value_or_default(self._receiver._receiver.pixel_depth_output, "--")
                return self._update_state_and_create_return_value(pixel_depth_output), None

            if self._sensor_type == SensorType.MAX_FRL_INPUT:
                max_frl_input = self._get_value_or_default(self._receiver._receiver.max_frl_input, "--")
                return self._update_state_and_create_return_value(max_frl_input), None

            if self._sensor_type == SensorType.MAX_FRL_OUTPUT:
                max_frl_output = self._get_value_or_default(self._receiver._receiver.max_frl_output, "--")
                return self._update_state_and_create_return_value(max_frl_output), None

        except Exception as ex:
            _LOG.warning("Error getting sensor value for %s: %s", self._sensor_type.value, ex)
            return None, None

        return None, None

    def _update_state_and_create_return_value(self, value: Any) -> Any:
        """Update sensor state and create return value."""
        if sensor_value := self.SensorStates.get(self._sensor_type, None):
            if sensor_value != value:
                self.SensorStates[self._sensor_type] = value
                return value
        else:
            self.SensorStates[self._sensor_type] = value
            return value

        return None

    @staticmethod
    def _get_value_or_default(value: Any, default: Any) -> Any:
        return value if value is not None else default


def create_sensors(device: AvrDevice, receiver: avr.DenonDevice, api: IntegrationAPI) -> list[DenonSensor]:
    """
    Create all applicable sensor entities for the given receiver.

    :param device: Device configuration
    :param receiver: DenonDevice instance
    :param api: IntegrationAPI instance
    :return: List of sensor entities
    """
    sensors = [
        DenonSensor(device, receiver, api, SensorType.VOLUME_DB),
        DenonSensor(device, receiver, api, SensorType.SOUND_MODE),
        DenonSensor(device, receiver, api, SensorType.INPUT_SOURCE),
        DenonSensor(device, receiver, api, SensorType.MUTE),
    ]

    # Only create telnet-based sensors if telnet is used
    if device.use_telnet:
        sensors.append(DenonSensor(device, receiver, api, SensorType.DIMMER))
        sensors.append(DenonSensor(device, receiver, api, SensorType.ECO_MODE))
        sensors.append(DenonSensor(device, receiver, api, SensorType.SLEEP_TIMER))
        sensors.append(DenonSensor(device, receiver, api, SensorType.AUDIO_DELAY))
        sensors.append(DenonSensor(device, receiver, api, SensorType.AUDIO_SIGNAL))
        sensors.append(DenonSensor(device, receiver, api, SensorType.AUDIO_SAMPLING_RATE))
        sensors.append(DenonSensor(device, receiver, api, SensorType.MONITOR_OUTPUT))
        sensors.append(DenonSensor(device, receiver, api, SensorType.INPUT_CHANNELS))
        sensors.append(DenonSensor(device, receiver, api, SensorType.OUTPUT_CHANNELS))
        sensors.append(DenonSensor(device, receiver, api, SensorType.MAX_RESOLUTION))
        sensors.append(DenonSensor(device, receiver, api, SensorType.VIDEO_HDMI_SIGNAL_IN))
        sensors.append(DenonSensor(device, receiver, api, SensorType.VIDEO_HDMI_SIGNAL_OUT))
        sensors.append(DenonSensor(device, receiver, api, SensorType.HDR_INPUT))
        sensors.append(DenonSensor(device, receiver, api, SensorType.HDR_OUTPUT))
        sensors.append(DenonSensor(device, receiver, api, SensorType.PIXEL_DEPTH_INPUT))
        sensors.append(DenonSensor(device, receiver, api, SensorType.PIXEL_DEPTH_OUTPUT))
        sensors.append(DenonSensor(device, receiver, api, SensorType.MAX_FRL_INPUT))
        sensors.append(DenonSensor(device, receiver, api, SensorType.MAX_FRL_OUTPUT))

    return sensors
