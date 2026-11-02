"""Strictly virtual siren validation. Never accepts a physical output."""

from __future__ import annotations

import re

_HELPER = re.compile(r"^input_boolean\.[a-z0-9_]+$")


def validate_fake_siren_helper(value: object) -> str:
    """Only a Home Assistant input_boolean, not a switch, script, or siren."""
    if not isinstance(value, str) or not _HELPER.fullmatch(value):
        raise ValueError("fake_siren_requires_input_boolean")
    return value


def fake_siren_target(phase: str) -> str:
    """The virtual siren is ON only for a triggered alarm."""
    return "on" if phase == "triggered" else "off"
