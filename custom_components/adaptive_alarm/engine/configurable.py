"""User-defined protection rules. No Home Assistant imports.

A configured rule is mandatory contacts AND every (OR) alternative group;
an optional lock can also be mandatory. A siren is inert metadata in alpha.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class AlternativeGroup:
    name: str
    contacts: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.contacts or len(set(self.contacts)) != len(self.contacts):
            raise ValueError("Group needs a name and distinct contacts")
        if any(not c.startswith("binary_sensor.") for c in self.contacts):
            raise ValueError("Group contacts must be binary sensors")


@dataclass(frozen=True)
class ProtectionRules:
    mandatory: tuple[str, ...] = ()
    groups: tuple[AlternativeGroup, ...] = ()
    optional: tuple[str, ...] = ()
    lock: str | None = None
    siren: str | None = None

    def __post_init__(self) -> None:
        contacts = (*self.mandatory, *self.optional, *(c for g in self.groups for c in g.contacts))
        if any(not c.startswith("binary_sensor.") for c in contacts):
            raise ValueError("Protection contacts must be binary sensors")
        if len(set(contacts)) != len(contacts):
            raise ValueError("A contact must appear in exactly one rule/group")
        if len({g.name.casefold() for g in self.groups}) != len(self.groups):
            raise ValueError("Alternative group names must be unique")
        if self.lock is not None and not self.lock.startswith("lock."):
            raise ValueError("Expected lock entity")
        if self.siren is not None and not self.siren.startswith(("switch.", "siren.")):
            raise ValueError("Expected siren/switch entity")

    @property
    def known_contacts(self) -> frozenset[str]:
        return frozenset((
            *self.mandatory,
            *self.optional,
            *(c for group in self.groups for c in group.contacts),
        ))

    @property
    def configured(self) -> bool:
        return bool(self.mandatory or self.groups)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mandatory": list(self.mandatory),
            "groups": [{"name": g.name, "contacts": list(g.contacts)} for g in self.groups],
            "optional": list(self.optional),
            "lock": self.lock,
            "siren": self.siren,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> ProtectionRules:
        return cls(
            mandatory=tuple(raw.get("mandatory", [])),
            groups=tuple(
                AlternativeGroup(str(g["name"]), tuple(g["contacts"]))
                for g in raw.get("groups", [])
            ),
            optional=tuple(raw.get("optional", [])),
            lock=raw.get("lock") or None,
            siren=raw.get("siren") or None,
        )


def legacy_to_rules(data: Mapping[str, Any], options: Mapping[str, Any]) -> ProtectionRules:
    """Losslessly map existing 0.3.x homes to two (OR) groups and required door."""
    if not data.get("entry_contact"):
        return ProtectionRules()
    return ProtectionRules(
        mandatory=(data["entry_contact"],),
        groups=(
            AlternativeGroup("Sala", (data["window_living"], data["shutter_living"])),
            AlternativeGroup("Bagno", (data["window_bath"], data["shutter_bath"])),
        ),
        optional=tuple(options.get("extra_contacts", [])),
        lock=data.get("entry_lock"),
    )


def rules_for_config(data: Mapping[str, Any], options: Mapping[str, Any]) -> ProtectionRules:
    """Support old config entries before or during their in-place migration."""
    if "protection" in options:
        return ProtectionRules.from_dict(options["protection"])
    return legacy_to_rules(data, options)
