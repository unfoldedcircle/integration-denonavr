"""
Sensor entity functions.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from typing import Any

import avr
import helpers
from config import AvrDevice, SensorType, create_entity_id
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
                    "name": f"{device.name} Sound Mode",
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
            case SensorType.AUDIO_INPUT_MODE:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.AUDIO_INPUT_MODE.value),
                    "name": f"{device.name} Audio Input Mode",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.AUDIO_SIGNAL:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.AUDIO_SIGNAL.value),
                    "name": f"{device.name} Audio Signal",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.AUDIO_SOUND:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.AUDIO_SOUND.value),
                    "name": f"{device.name} Audio Sound",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.AUDIO_SAMPLING_RATE:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.AUDIO_SAMPLING_RATE.value),
                    "name": f"{device.name} Audio Sampling Rate",
                    "device_class": DeviceClasses.CUSTOM,
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
                    "name": f"{device.name} Monitor Output",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.VIDEO_HDMI_SIGNAL_IN:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.VIDEO_HDMI_SIGNAL_IN.value),
                    "name": f"{device.name} Video HDMI Signal In",
                    "device_class": DeviceClasses.CUSTOM,
                }
            case SensorType.VIDEO_HDMI_SIGNAL_OUT:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.VIDEO_HDMI_SIGNAL_OUT.value),
                    "name": f"{device.name} Video HDMI Signal Out",
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
    def _get_sensor_value(self, update: dict[str, Any]) -> tuple[Any, str | None]:
        """Get the current value and unit for this sensor type."""
        # If receiver is turned off, clear stored sensor state
        if update.get(MediaAttr.STATE, None) and self._receiver._receiver.state == "off":
            self.SensorStates.pop(self._sensor_type, None)

        try:
            if self._sensor_type == SensorType.VOLUME_DB:
                volume = self._get_value_or_default(self._receiver._receiver.volume, 0.0)
                return self._update_state_and_create_return_value(volume), None

            if self._sensor_type == SensorType.SOUND_MODE:
                sound_mode = update.get("RAW_SOUND_MODE", None)
                if sound_mode is None:
                    return None, None
                return self._update_state_and_create_return_value(sound_mode), None

            if self._sensor_type == SensorType.INPUT_SOURCE:
                input_source = self._get_value_or_default(self._receiver._receiver.input_func, "--")
                return self._update_state_and_create_return_value(input_source), None

            if self._sensor_type == SensorType.DIMMER:
                dimmer_state = self._get_value_or_default(self._receiver._receiver.dimmer, "Off")
                return self._update_state_and_create_return_value(dimmer_state), None

            if self._sensor_type == SensorType.ECO_MODE:
                eco_mode = self._get_value_or_default(self._receiver._receiver.eco_mode, "Off")
                return self._update_state_and_create_return_value(eco_mode), None

            if self._sensor_type == SensorType.SLEEP_TIMER:
                sleep = update.get("SLEEP_TIMER", self._receiver._receiver.sleep)
                if sleep is not None:
                    if isinstance(sleep, int):
                        return self._update_state_and_create_return_value(sleep), "min"
                return self._update_state_and_create_return_value("Off"), ""  # clear 'min' unit

            if self._sensor_type == SensorType.AUDIO_DELAY:
                audio_delay = self._get_value_or_default(self._receiver._receiver.delay, 0)
                return self._update_state_and_create_return_value(audio_delay), None

            if self._sensor_type == SensorType.AUDIO_INPUT_MODE:
                audio_input_mode = self._get_value_or_default(self._receiver._receiver.audio_input_mode, "--")
                return self._update_state_and_create_return_value(audio_input_mode), None

            if self._sensor_type == SensorType.AUDIO_SIGNAL:
                audio_signal = self._get_value_or_default(self._receiver._receiver.audio_signal, "--")
                return self._update_state_and_create_return_value(audio_signal), None

            if self._sensor_type == SensorType.AUDIO_SOUND:
                audio_sound = self._get_value_or_default(self._receiver._receiver.audio_sound, "--")
                return self._update_state_and_create_return_value(audio_sound), None

            if self._sensor_type == SensorType.AUDIO_SAMPLING_RATE:
                audio_sampling_rate = self._get_value_or_default(self._receiver._receiver.audio_sampling_rate, "--")
                return self._update_state_and_create_return_value(audio_sampling_rate), None

            if self._sensor_type == SensorType.MUTE:
                on_off = "on" if self._receiver._receiver.muted else "off"
                return self._update_state_and_create_return_value(on_off), None

            if self._sensor_type == SensorType.MONITOR_OUTPUT:
                if self._receiver._receiver.video_output:
                    return self._update_state_and_create_return_value(self._receiver._receiver.video_output), None
                return self._update_state_and_create_return_value(self._receiver._receiver.hdmi_output), None

            if self._sensor_type == SensorType.VIDEO_HDMI_SIGNAL_IN:
                hdmi_in_signal = self._get_value_or_default(self._receiver._receiver.video_hdmi_signal_in, "--")
                return self._update_state_and_create_return_value(hdmi_in_signal), None

            if self._sensor_type == SensorType.VIDEO_HDMI_SIGNAL_OUT:
                hdmi_out_signal = self._get_value_or_default(self._receiver._receiver.video_hdmi_signal_out, "--")
                return self._update_state_and_create_return_value(hdmi_out_signal), None

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
        sensors.append(DenonSensor(device, receiver, api, SensorType.MONITOR_OUTPUT))

    # Audio and video sensors are only available on AVR 2016 and newer models
    if device.support_2016_update:
        sensors.append(DenonSensor(device, receiver, api, SensorType.AUDIO_INPUT_MODE))
        sensors.append(DenonSensor(device, receiver, api, SensorType.AUDIO_SIGNAL))
        sensors.append(DenonSensor(device, receiver, api, SensorType.AUDIO_SOUND))
        sensors.append(DenonSensor(device, receiver, api, SensorType.AUDIO_SAMPLING_RATE))
        sensors.append(DenonSensor(device, receiver, api, SensorType.VIDEO_HDMI_SIGNAL_IN))
        sensors.append(DenonSensor(device, receiver, api, SensorType.VIDEO_HDMI_SIGNAL_OUT))

    return sensors
