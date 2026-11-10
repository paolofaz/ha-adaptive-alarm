"""Debounced, batched diagnostics: never delay or modify genuine alarm events.

These gates apply ONLY to optional informational notifications. Sensor health
and the underlying alarm engine always continue updating immediately.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

STARTUP_GRACE_SECONDS = 120
UNREADABLE_STABLE_SECONDS = 60
DIAGNOSTIC_BATCH_SECONDS = 10
DIAGNOSTIC_COOLDOWN_SECONDS = 300


@dataclass
class DiagnosticNoticeGate:
    started_at: float
    first_seen: dict[str, float] = field(default_factory=dict)
    reported: set[str] = field(default_factory=set)
    batch_started_at: float | None = None
    last_sent_at: float | None = None

    @property
    def startup_deadline(self) -> float:
        return self.started_at + STARTUP_GRACE_SECONDS

    def clear(self) -> None:
        """A newly armed episode must not inherit previous notification state."""
        self.first_seen.clear()
        self.reported.clear()
        self.batch_started_at = None
        self.last_sent_at = None

    def poll(self, *, now: float, problems: Mapping[str, str]) -> dict[str, str]:
        """Return one batch of newly persistent problems, never repeating old ones.

        A problem must stay continuously present for 60 seconds and survive the
        first 120 seconds of integration startup. First eligible problems wait
        10 seconds for other devices; subsequent batches are spaced by at least
        300 seconds. Once a problem recovers, it can be reported again only if
        it later becomes persistently unavailable again.
        """
        active = set(problems)
        for entity in tuple(self.first_seen):
            if entity not in active:
                del self.first_seen[entity]
                self.reported.discard(entity)
        for entity in active:
            self.first_seen.setdefault(entity, now)
        due = sorted(
            entity for entity in active
            if entity not in self.reported
            and now >= self.startup_deadline
            and now - self.first_seen[entity] >= UNREADABLE_STABLE_SECONDS
        )
        if not due:
            self.batch_started_at = None
            return {}
        if self.batch_started_at is None:
            self.batch_started_at = now
        if now < self.batch_started_at + DIAGNOSTIC_BATCH_SECONDS:
            return {}
        if (
            self.last_sent_at is not None
            and now < self.last_sent_at + DIAGNOSTIC_COOLDOWN_SECONDS
        ):
            return {}
        self.reported.update(due)
        self.last_sent_at = now
        self.batch_started_at = None
        return {entity: problems[entity] for entity in due}
