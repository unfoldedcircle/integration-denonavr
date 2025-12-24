"""
Common entity interface for Denon/Marantz integration.

:copyright: (c) 2025 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

from abc import ABC, abstractmethod
from typing import Any

import avr


# pylint: disable=R0903
class DenonEntity(ABC):
    """Common interface for Denon/Marantz entities."""

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
