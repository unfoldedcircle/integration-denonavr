"""
Sensor entity functions.

:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from enum import Enum
from typing import Any

import avr
from config import AvrDevice
from ucapi import Sensor
from ucapi.sensor import Attributes, DeviceClasses, Options, States
from denonavrlib.denonavr.const import SOUND_MODE_MAPPING

_LOG = logging.getLogger(__name__)


class SensorType(str, Enum):
    """Sensor types for Denon AVR."""

    VOLUME_DB = "volume_db"
    SOUND_MODE = "sound_mode"
    INPUT_SOURCE = "input_source"
    DIMMER = "dimmer"
    ECO_MODE = "eco_mode"
    SLEEP_TIMER = "sleep_timer"
    AUDIO_DELAY = "audio_delay"
    MUTE = "muted"


SOUND_MODE_VALUES: list[str] = SOUND_MODE_MAPPING.values()


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
    def _get_sensor_config(sensor_type: SensorType, device: AvrDevice, receiver: avr.DenonDevice) -> dict[str, Any]:
        """Get sensor configuration based on type."""
        base_id = f"{receiver.id}_sensor"

        configs = {
            SensorType.VOLUME_DB: {
                "id": f"{base_id}_volume_db",
                "name": f"{device.name} Volume",
                "device_class": DeviceClasses.CUSTOM,
                "unit": "dB",
                "options": {
                    Options.CUSTOM_UNIT: "dB",
                    Options.DECIMALS: 1,
                },
            },
            SensorType.SOUND_MODE: {
                "id": f"{base_id}_sound_mode",
                "name": f"{device.name} Sound Mode",
                "device_class": DeviceClasses.CUSTOM,
                "unit": None,
                "options": {
                    Options.CUSTOM_UNIT: "",
                },
            },
            SensorType.INPUT_SOURCE: {
                "id": f"{base_id}_input_source",
                "name": f"{device.name} Input Source",
                "device_class": DeviceClasses.CUSTOM,
                "unit": None,
                "options": {
                    Options.CUSTOM_UNIT: "",
                },
            },
            SensorType.DIMMER: {
                "id": f"{base_id}_dimmer",
                "name": f"{device.name} Dimmer",
                "device_class": DeviceClasses.CUSTOM,
                "unit": None,
                "options": {
                    Options.CUSTOM_UNIT: "",
                },
            },
            SensorType.ECO_MODE: {
                "id": f"{base_id}_eco_mode",
                "name": f"{device.name} Eco Mode",
                "device_class": DeviceClasses.CUSTOM,
                "unit": None,
                "options": {
                    Options.CUSTOM_UNIT: "",
                },
            },
            SensorType.SLEEP_TIMER: {
                "id": f"{base_id}_sleep_timer",
                "name": f"{device.name} Sleep Timer",
                "device_class": DeviceClasses.CUSTOM,
                "unit": "min",
                "options": {
                    Options.CUSTOM_UNIT: "",
                },
            },
            SensorType.AUDIO_DELAY: {
                "id": f"{base_id}_audio_delay",
                "name": f"{device.name} Audio Delay",
                "device_class": DeviceClasses.CUSTOM,
                "unit": "ms",
                "options": {
                    Options.CUSTOM_UNIT: "ms",
                    Options.DECIMALS: 0,
                },
            },
            SensorType.MUTE: {
                "id": f"{base_id}_mute",
                "name": f"{device.name} Mute Status",
                "device_class": DeviceClasses.CUSTOM,
                "unit": None,
                "options": {
                    Options.CUSTOM_UNIT: "",
                },
            },
        }

        return configs[sensor_type]

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

    def _get_sensor_value(self, update: dict[str, Any]) -> Any:
        """Get the current value for this sensor type."""
        try:
            if self._sensor_type == SensorType.VOLUME_DB:
                return self._update_state_and_create_return_value(SensorType.VOLUME_DB, self._receiver._receiver.volume)

            elif self._sensor_type == SensorType.SOUND_MODE:
                sound_mode = update.get("RAW_SOUND_MODE", None)
                if sound_mode:
                    return self._update_state_and_create_return_value(SensorType.SOUND_MODE, sound_mode)
                return None

            elif self._sensor_type == SensorType.INPUT_SOURCE:
                return self._update_state_and_create_return_value(
                    SensorType.INPUT_SOURCE, self._receiver._receiver.input_func
                )

            elif self._sensor_type == SensorType.DIMMER:
                return self._update_state_and_create_return_value(
                    SensorType.DIMMER, f"Dimmer {self._receiver._receiver.dimmer}"
                )

            elif self._sensor_type == SensorType.ECO_MODE:
                return self._update_state_and_create_return_value(
                    SensorType.ECO_MODE, f"ECO {self._receiver._receiver.eco_mode}"
                )

            elif self._sensor_type == SensorType.SLEEP_TIMER:
                sleep = self._receiver._receiver.sleep
                if sleep is not None:
                    if isinstance(sleep, int):
                        return self._update_state_and_create_return_value(SensorType.SLEEP_TIMER, f"Sleep {sleep}")
                return self._update_state_and_create_return_value(SensorType.SLEEP_TIMER, "Sleep Off")

            elif self._sensor_type == SensorType.AUDIO_DELAY:
                return self._update_state_and_create_return_value(
                    SensorType.AUDIO_DELAY, self._receiver._receiver.delay
                )

            elif self._sensor_type == SensorType.MUTE:
                on_off = "On" if self._receiver._receiver.muted else "Off"
                return self._update_state_and_create_return_value(SensorType.MUTE, f"Mute {on_off}")

        except Exception as ex:
            _LOG.warning("Error getting sensor value for %s: %s", self._sensor_type.value, ex)
            return None

        return None

    def _update_state_and_create_return_value(self, sensor_type: SensorType, value: Any) -> Any:
        """Helper to create return value with state and value."""
        if sensor_value := self.SensorStates.get(sensor_type, None):
            if sensor_value != value:
                self.SensorStates[sensor_type] = value
                return value
        else:
            self.SensorStates[sensor_type] = value
            return value

        return None


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

    return sensors
