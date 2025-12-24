"""
Common entity interface for Denon/Marantz integration.

:copyright: (c) 2025 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

from abc import ABC, abstractmethod
from typing import Any

import avr
from ucapi import IntegrationAPI


# pylint: disable=R0903
class DenonEntity(ABC):
    """Common interface for Denon/Marantz entities."""

    def __init__(self, api: IntegrationAPI):
        """Initialize the DenonEntity."""
        self._api: IntegrationAPI = api

    def update_attributes(self, update: dict[str, Any], *, force: bool = False) -> None:
        """
        Update the entity attributes from the given AVR update.

        :param update: dictionary containing the updated properties.
        :param force: if True, update attributes even if they haven't changed.
        """
        if force:
            attributes = update
        else:
            attributes = self.filter_changed_attributes(update)

        if attributes:
            # pylint: disable=E1101
            self._api.configured_entities.update_attributes(self.id, attributes)

    @abstractmethod
    def filter_changed_attributes(self, update: dict[str, Any]) -> dict[str, Any]:
        """
        Filter the given attributes from an AVR update and return only the changed values.

        :param update: dictionary containing the updated properties.
        :return: dictionary containing only the changed attributes.
        """

    @abstractmethod
    def state_from_avr(self, avr_state: avr.States) -> Any:
        """
        Convert an AVR state to a UC API entity state.

        :param avr_state: Denon/Marantz AVR state
        :return: UC API entity state
        """
