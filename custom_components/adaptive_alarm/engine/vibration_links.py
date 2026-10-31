"""Validate optional vibration inputs without Home Assistant dependencies."""

from __future__ import annotations

from collections.abc import Collection, Iterable


class VibrationConfigurationError(ValueError):
    """Invalid sensor-to-contact mapping. Code is also a config-flow error key."""


def validated_vibration_links(
    links: Iterable[tuple[str | None, str | None]],
    monitored_contacts: Collection[str],
) -> dict[str, str]:
    """Return sensor → contact, rejecting missing targets and duplicates.

    No inferred association is ever allowed: excluded or unpaired sensors
    must not be able to trigger an alarm.
    """
    contacts = frozenset(monitored_contacts)
    result: dict[str, str] = {}
    for sensor, contact in links:
        if not sensor and not contact:
            continue
        if not sensor or not contact:
            raise VibrationConfigurationError("unpaired_vibration")
        if contact not in contacts:
            raise VibrationConfigurationError("invalid_vibration_zone")
        if sensor in contacts or sensor in result:
            raise VibrationConfigurationError("duplicate_entities")
        result[sensor] = contact
    return result
