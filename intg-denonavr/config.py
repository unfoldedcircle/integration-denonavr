"""Configuration handling of the integration driver."""

import dataclasses
import json
import logging
import os
from dataclasses import dataclass
from typing import Iterator

from ucapi import EntityTypes

_LOG = logging.getLogger(__name__)

_CFG_FILENAME = "config.json"


def create_entity_id(avr_id: str, entity_type: EntityTypes) -> str:
    """Create a unique entity identifier for the given receiver and entity type."""
    return f"{entity_type.value}.{avr_id}"


def avr_from_entity_id(entity_id: str) -> str | None:
    """
    Return the avr_id prefix of an entity_id.

    The prefix is the part before the first dot in the name and refers to the AVR device identifier.

    :param entity_id: the entity identifier
    :return: the device prefix, or None if entity_id doesn't contain a dot
    """
    return entity_id.split(".", 1)[1]


@dataclass
class AvrDevice:
    """Denon device configuration."""

    id: str
    name: str
    address: str
    support_sound_mode: bool
    show_all_inputs: bool
    use_telnet: bool
    update_audyssey: bool
    zone2: bool
    zone3: bool


class _EnhancedJSONEncoder(json.JSONEncoder):
    """Python dataclass json encoder."""

    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)


class Devices:
    """Integration driver configuration class. Manages all configured Denon devices."""

    def __init__(self, data_path: str, add_handler, remove_handler):
        """
        Create a configuration instance for the given configuration path.

        :param data_path: configuration path for the configuration file and client device certificates.
        """
        self._data_path: str = data_path
        self._cfg_file_path: str = os.path.join(data_path, _CFG_FILENAME)
        self._config: list[AvrDevice] = []
        self._add_handler = add_handler
        self._remove_handler = remove_handler

        self.load()

    @property
    def data_path(self) -> str:
        """Return the configuration path."""
        return self._data_path

    def all(self) -> Iterator[AvrDevice]:
        """Get an iterator for all device configurations."""
        return iter(self._config)

    def contains(self, avr_id: str) -> bool:
        """Check if there's a device with the given device identifier."""
        for item in self._config:
            if item.id == avr_id:
                return True
        return False

    def add(self, atv: AvrDevice) -> None:
        """Add a new configured Denon device."""
        # TODO duplicate check
        self._config.append(atv)
        if self._add_handler is not None:
            self._add_handler(atv)

    def get(self, avr_id: str) -> AvrDevice | None:
        """Get device configuration for given identifier."""
        for item in self._config:
            if item.id == avr_id:
                # return a copy
                return dataclasses.replace(item)
        return None

    def update(self, atv: AvrDevice) -> bool:
        """Update a configured Denon device and persist configuration."""
        for item in self._config:
            if item.id == atv.id:
                item.address = atv.address
                item.name = atv.name
                return self.store()
        return False

    def remove(self, avr_id: str) -> bool:
        """Remove the given device configuration."""
        atv = self.get(avr_id)
        if atv is None:
            return False
        try:
            self._config.remove(atv)
            if self._remove_handler is not None:
                self._remove_handler(atv)
            return True
        except ValueError:
            pass
        return False

    def clear(self) -> None:
        """Remove the configuration file."""
        self._config = []

        if os.path.exists(self._cfg_file_path):
            os.remove(self._cfg_file_path)

        if self._remove_handler is not None:
            self._remove_handler(None)

    def store(self) -> bool:
        """
        Store the configuration file.

        :return: True if the configuration could be saved.
        """
        try:
            with open(self._cfg_file_path, "w+", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, cls=_EnhancedJSONEncoder)
            return True
        except OSError:
            _LOG.error("Cannot write the config file")

        return False

    def load(self) -> bool:
        """
        Load the config into the config global variable.

        :return: True if the configuration could be loaded.
        """
        try:
            with open(self._cfg_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                try:
                    self._config.append(AvrDevice(**item))
                except TypeError as ex:
                    _LOG.warning("Invalid configuration entry will be ignored: %s", ex)
            return True
        except OSError:
            _LOG.error("Cannot open the config file")
        except ValueError:
            _LOG.error("Empty or invalid config file")

        return False


devices: Devices | None = None
