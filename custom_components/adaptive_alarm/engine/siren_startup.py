"""Startup siren availability gate, independent of Home Assistant imports.

A brief Zigbee2MQTT startup delay is expected. A pending startup OFF is
retried once the siren entity and service are available. Delays over two
minutes are reported once; a user-issued ON remains a normal actionable
failure when the siren is unavailable.
"""
from dataclasses import dataclass

STARTUP_SIREN_GRACE_SECONDS = 120


@dataclass
class SirenStartupOffGate:
    pending: bool = False
    deadline: float | None = None
    warned: bool = False

    def defer(self, *, initializing: bool, available: bool, now: float) -> bool:
        """Defer OFF only on startup or while an earlier startup OFF is pending."""
        if available or not (initializing or self.pending):
            return False
        if not self.pending:
            self.pending = True
            self.deadline = now + STARTUP_SIREN_GRACE_SECONDS
        return True

    def warning_due(self, now: float) -> bool:
        if (not self.pending or self.warned or self.deadline is None
                or now < self.deadline):
            return False
        self.warned = True
        return True

    def completed(self) -> None:
        self.pending = False
        self.deadline = None
        self.warned = False
