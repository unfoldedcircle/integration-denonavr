"""
Helper functions.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

from typing import Any


def key_update_helper(key: str, value: str | None, attributes: dict, original_attributes: dict[str, Any]):
    """Update the attributes dictionary with the given key and value."""
    if value is None:
        return attributes

    if key in original_attributes:
        if original_attributes[key] != value:
            attributes[key] = value
    else:
        attributes[key] = value

    return attributes


def relative_volume_to_absolute(relative: float) -> float:
    """Convert relative volume (-80 dB - 18 dB) to absolute volume (0-98)."""
    absolute = min(relative + 80, 98)
    return max(absolute, 0)


def absolute_volume_to_relative(absolute: float) -> float:
    """Convert absolute volume (0-98) to relative volume (-80 dB - 18 dB)."""
    absolute = min(absolute, 98)
    absolute = max(absolute, 0)
    return absolute - 80
