"""
Sensor entity functions.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from typing import Any

import avr
from config import AvrDevice, SensorType, create_entity_id
from ucapi import EntityTypes, Sensor
from ucapi.media_player import Attributes as MediaAttr
from ucapi.sensor import Attributes, DeviceClasses, Options, States

_LOG = logging.getLogger(__name__)

# Mapping of an AVR state to a sensor entity state
SENSOR_STATE_MAPPING = {
    avr.States.ON: States.ON,
    avr.States.OFF: States.ON,
    avr.States.PAUSED: States.ON,
    avr.States.PLAYING: States.ON,
    avr.States.UNAVAILABLE: States.UNAVAILABLE,
    avr.States.UNKNOWN: States.UNKNOWN,
}


class DenonSensor(Sensor):
    """Representation of a Denon/Marantz AVR Sensor entity."""

    def __init__(
        self,
        device: AvrDevice,
        receiver: avr.DenonDevice,
        sensor_type: SensorType,
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

    @staticmethod
    def state_from_avr(avr_state: avr.States) -> States:
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
                    "unit": None,
                }
            case SensorType.INPUT_SOURCE:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.INPUT_SOURCE.value),
                    "name": f"{device.name} Input Source",
                    "device_class": DeviceClasses.CUSTOM,
                    "unit": None,
                }
            case SensorType.DIMMER:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.DIMMER.value),
                    "name": f"{device.name} Dimmer",
                    "device_class": DeviceClasses.CUSTOM,
                    "unit": None,
                }
            case SensorType.ECO_MODE:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.ECO_MODE.value),
                    "name": f"{device.name} Eco Mode",
                    "device_class": DeviceClasses.CUSTOM,
                    "unit": None,
                }
            case SensorType.SLEEP_TIMER:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.SLEEP_TIMER.value),
                    "name": f"{device.name} Sleep Timer",
                    "device_class": DeviceClasses.CUSTOM,
                    "unit": "min",
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
            case SensorType.MUTE:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.MUTE.value),
                    "name": f"{device.name} Mute Status",
                    "device_class": DeviceClasses.CUSTOM,
                    "unit": None,
                }
            case SensorType.MONITOR_OUTPUT:
                sensor = {
                    "id": create_entity_id(receiver.id, EntityTypes.SENSOR, SensorType.MONITOR_OUTPUT.value),
                    "name": f"{device.name} Monitor Output",
                    "device_class": DeviceClasses.CUSTOM,
                    "unit": None,
                }
            case _:
                raise ValueError(f"Unsupported sensor type: {sensor_type}")
        return sensor

    def update_attributes(self, update: dict[str, Any]) -> dict[str, Any] | None:
        """Get current sensor value from receiver."""
        if not self._receiver.available:
            return {
                Attributes.STATE: States.UNAVAILABLE,
                Attributes.VALUE: None,
            }

        value = self._get_sensor_value(update)

        if not value:
            return None

        attributes = {
            Attributes.STATE: States.ON if value is not None else States.UNAVAILABLE,
            Attributes.VALUE: value,
        }

        return attributes

    SensorStates: dict[SensorType, Any] = {}

    # pylint: disable=broad-exception-caught, too-many-return-statements, protected-access
    def _get_sensor_value(self, update: dict[str, Any]) -> Any:
        """Get the current value for this sensor type."""
        # If receiver is turned off, clear stored sensor state
        if update.get(MediaAttr.STATE, None) and self._receiver._receiver.state == "off":
            self.SensorStates.pop(self._sensor_type, None)

        try:
            if self._sensor_type == SensorType.VOLUME_DB:
                volume = self._get_value_or_default(self._receiver._receiver.volume, 0.0)
                return self._update_state_and_create_return_value(volume)

            if self._sensor_type == SensorType.SOUND_MODE:
                sound_mode = update.get("RAW_SOUND_MODE", None)
                if sound_mode is None:
                    return None
                return self._update_state_and_create_return_value(sound_mode)

            if self._sensor_type == SensorType.INPUT_SOURCE:
                input_source = self._get_value_or_default(self._receiver._receiver.input_func, "--")
                return self._update_state_and_create_return_value(input_source)

            if self._sensor_type == SensorType.DIMMER:
                dimmer_state = self._get_value_or_default(self._receiver._receiver.dimmer, "Off")
                return self._update_state_and_create_return_value(f"Dimmer {dimmer_state}")

            if self._sensor_type == SensorType.ECO_MODE:
                eco_mode = self._get_value_or_default(self._receiver._receiver.eco_mode, "Off")
                return self._update_state_and_create_return_value(f"ECO {eco_mode}")

            if self._sensor_type == SensorType.SLEEP_TIMER:
                sleep = update.get("SLEEP_TIMER", self._receiver._receiver.sleep)
                if sleep is not None:
                    if isinstance(sleep, int):
                        return self._update_state_and_create_return_value(f"Sleep {sleep}")
                return self._update_state_and_create_return_value("Sleep Off")

            if self._sensor_type == SensorType.AUDIO_DELAY:
                audio_delay = self._get_value_or_default(self._receiver._receiver.delay, 0)
                return self._update_state_and_create_return_value(audio_delay)

            if self._sensor_type == SensorType.MUTE:
                on_off = "On" if self._receiver._receiver.muted else "Off"
                return self._update_state_and_create_return_value(f"Mute {on_off}")

            if self._sensor_type == SensorType.MONITOR_OUTPUT:
                return self._update_state_and_create_return_value(self._receiver._receiver.hdmi_output)

        except Exception as ex:
            _LOG.warning("Error getting sensor value for %s: %s", self._sensor_type.value, ex)
            return None

        return None

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


def create_sensors(device: AvrDevice, receiver: avr.DenonDevice) -> list[DenonSensor]:
    """
    Create all applicable sensor entities for the given receiver.

    :param device: Device configuration
    :param receiver: DenonDevice instance
    :return: List of sensor entities
    """
    sensors = [
        DenonSensor(device, receiver, SensorType.VOLUME_DB),
        DenonSensor(device, receiver, SensorType.SOUND_MODE),
        DenonSensor(device, receiver, SensorType.INPUT_SOURCE),
        DenonSensor(device, receiver, SensorType.MUTE),
    ]

    # Only create telnet-based sensors if telnet is used
    if device.use_telnet:
        sensors.append(DenonSensor(device, receiver, SensorType.DIMMER))
        sensors.append(DenonSensor(device, receiver, SensorType.ECO_MODE))
        sensors.append(DenonSensor(device, receiver, SensorType.SLEEP_TIMER))
        sensors.append(DenonSensor(device, receiver, SensorType.AUDIO_DELAY))
        sensors.append(DenonSensor(device, receiver, SensorType.MONITOR_OUTPUT))

    return sensors
