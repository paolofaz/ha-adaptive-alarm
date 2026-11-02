"""Pure, non-actuating household presence consistency alerts.

Only an explicit HOME state identifies a person at home; only an explicit
ON signal from a user-selected certainly-empty binary sensor identifies a
vacant house. Missing, unknown or unavailable data cannot establish either.

Each unchanged anomalous episode produces at most one event after its own
stable delay. State is intentionally not persisted; after HA restarts, the
entire delay is observed again before any alert can be raised.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass
class PresenceAlerts:
    """Debounced, one-shot mismatch observer; NEVER alters the alarm phase."""

    first_seen: dict[str, float] = field(default_factory=dict)
    notified: set[str] = field(default_factory=set)

    def observe(
        self, *, now: float, phase: str,
        people_home: Iterable[str], empty_sensor_on: bool, lock_locked: bool,
        watch_home: bool, watch_empty: bool,
        home_delay: float = 20, empty_delay: float = 120,
    ) -> list[dict[str, Any]]:
        if home_delay <= 0 or empty_delay <= 0:
            raise ValueError("Presence alert delays must be positive")
        at_home = tuple(sorted(set(people_home)))
        conditions = {
            "armed_with_person_home": watch_home
            and phase == "armed_away" and bool(at_home),
            "empty_house_disarmed": watch_empty
            and phase == "disarmed" and empty_sensor_on and lock_locked,
        }
        delays = {
            "armed_with_person_home": home_delay,
            "empty_house_disarmed": empty_delay,
        }
        results: list[dict[str, Any]] = []
        for kind, active in conditions.items():
            if not active:
                self.first_seen.pop(kind, None)
                self.notified.discard(kind)
                continue
            if kind not in self.first_seen:
                self.first_seen[kind] = now
            if kind in self.notified or now - self.first_seen[kind] < delays[kind]:
                continue
            self.notified.add(kind)
            event: dict[str, Any] = {"type": "presence_mismatch", "kind": kind}
            if kind == "armed_with_person_home":
                event["people"] = list(at_home)
            results.append(event)
        return results
