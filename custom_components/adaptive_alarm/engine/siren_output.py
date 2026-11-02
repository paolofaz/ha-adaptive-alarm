"""Pure validation of a physical siren Home Assistant entity.

The controller is the only caller permitted to turn on the device.
"""
from __future__ import annotations

import re

_REAL_SIREN = re.compile(r"^(?:siren|switch)\.[a-z0-9_]+$")


def validate_real_siren(value: object) -> str:
    """Require a simple siren or switch entity ID; reject arbitrary services."""
    if not isinstance(value, str) or not _REAL_SIREN.fullmatch(value):
        raise ValueError("Siren output requires a siren or switch entity")
    return value
