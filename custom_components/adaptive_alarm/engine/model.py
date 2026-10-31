"""Immutable data structures for adaptive protection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ZoneState(StrEnum):
    """Fail-closed meaning of a physical contact observation."""

    CLOSED = "closed"
    OPEN = "open"
    UNAVAILABLE = "unavailable"


class RecoveryPolicy(StrEnum):
    """Response when a protected contact recovers already open."""

    NOTIFY = "notify"
    TRIGGER = "trigger"


class EventAction(StrEnum):
    """Action proposed by the pure engine; not an actual siren command."""

    IGNORE = "ignore"
    TRIGGER = "trigger"
    CRITICAL_NOTICE = "critical_notice"


@dataclass(frozen=True)
class MinimumPaths:
    """Entry and four admissible sala/bagno coverage combinations."""

    entry: str
    shutters: tuple[str, str]
    windows: tuple[str, str]

    def __post_init__(self) -> None:
        contacts = (self.entry, *self.shutters, *self.windows)
        if any(not contact for contact in contacts) or len(set(contacts)) != 5:
            raise ValueError("Five distinct nonempty contacts are required")

    def route_pairs(self) -> tuple[tuple[str, tuple[str, str]], ...]:
        """Coverage must include one sala and one bagno barrier."""
        return (
            ("shutters", self.shutters),
            ("windows", self.windows),
            ("living_window_bath_shutter", (self.windows[0], self.shutters[1])),
            ("living_shutter_bath_window", (self.shutters[0], self.windows[1])),
        )


@dataclass(frozen=True)
class Eligibility:
    """Whether arming is permitted by a supplied snapshot."""

    permitted: bool
    routes: tuple[str, ...]
    problems: tuple[str, ...]


@dataclass(frozen=True)
class Session:
    """Frozen protected/excluded zone snapshot for one armed session."""

    identifier: str
    known_zones: frozenset[str]
    protected_zones: frozenset[str]
    initial_routes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.identifier or not self.protected_zones.issubset(self.known_zones):
            raise ValueError("Invalid alarm session")
        if not self.initial_routes:
            raise ValueError("A session must have a minimum route")

    @property
    def excluded_zones(self) -> frozenset[str]:
        return self.known_zones - self.protected_zones
