"""Deterministic session machine: no Home Assistant imports.

All calls must be serialized by the adapter. Event timestamps are UTC epoch
seconds; no background callbacks or independent state writers exist here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from .configurable import ProtectionRules
from .model import EventAction, MinimumPaths, RecoveryPolicy, Session, ZoneState
from .policy import classify_opening, evaluate_eligibility, new_session


class Phase(StrEnum):
    DISARMED = "disarmed"
    ARMING = "arming"
    ARMED_AWAY = "armed_away"
    TRIGGERED = "triggered"
    FAULT = "fault"


@dataclass
class AlarmMachine:
    """State transitions for one monitored alarm instance.

    No physical actuation. Callers persist snapshot before publishing events.
    """

    paths: MinimumPaths | ProtectionRules
    zones: frozenset[str]
    phase: Phase = Phase.DISARMED
    session: Session | None = None
    arming_until: float | None = None
    fault: str = ""
    vibration_hits: list[tuple[float, str]] = field(default_factory=list)
    vibration_last: dict[str, float] = field(default_factory=dict)
    vibration_prealarms: int = 0
    vibration_filtered: int = 0
    # Persisted so HA restarts cannot repeat a one-time light request.
    deterrent_requested: bool = False

    def __post_init__(self) -> None:
        required = (
            set(self.paths.known_contacts)
            if isinstance(self.paths, ProtectionRules)
            else {self.paths.entry, *self.paths.shutters, *self.paths.windows}
        )
        if not required.issubset(self.zones):
            raise ValueError("Required contacts not present in zone catalogue")

    @property
    def active(self) -> bool:
        return self.phase in (Phase.ARMED_AWAY, Phase.TRIGGERED)

    def arm(
        self, states: Mapping[str, ZoneState], *, locked: bool,
        now: float, delay: int = 60,
    ) -> list[dict[str, Any]]:
        """Start an exit delay; final eligibility is checked at commit.

        Zero-delay arming is checked immediately and never enters an invalid
        armed state. Readiness remains a live diagnostic, not a gate for an
        exit countdown while the homeowner is still leaving.
        """
        if self.phase != Phase.DISARMED:
            return [{"type": "command_ignored", "reason": self.phase.value}]
        if delay < 0 or delay > 600:
            raise ValueError("Invalid arming delay")
        if delay == 0:
            eligibility = evaluate_eligibility(self.paths, states, lock_locked=locked)
            if not eligibility.permitted:
                self.fault = "Arming rejected: " + ", ".join(eligibility.problems)
                return [{"type": "arm_rejected", "problems": list(eligibility.problems)}]
        self.fault = ""
        self.deterrent_requested = False
        self.phase = Phase.ARMING
        self.arming_until = now + delay
        self._clear_vibration()
        events: list[dict[str, Any]] = [
            {"type": "arming", "seconds": delay, "validation": "at_commit"}
        ]
        if delay == 0:
            events.extend(self.tick(states, locked=locked, now=now))
        return events

    def tick(
        self, states: Mapping[str, ZoneState], *, locked: bool, now: float,
        vibration_window: float = 60,
    ) -> list[dict[str, Any]]:
        """Commit a frozen snapshot and expire vibration history on its own timer."""
        events: list[dict[str, Any]] = []
        if self.phase == Phase.ARMING and self.arming_until is not None:
            if now >= self.arming_until:
                eligibility = evaluate_eligibility(self.paths, states, lock_locked=locked)
                self.arming_until = None
                if not eligibility.permitted:
                    self.phase = Phase.DISARMED
                    self.fault = "Arming rejected at deadline: " + ", ".join(eligibility.problems)
                    events.append(
                        {"type": "arm_rejected", "problems": list(eligibility.problems)}
                    )
                else:
                    self.session = new_session(
                        f"episode-{int(now * 1000000)}", self.paths,
                        {key: states.get(key, ZoneState.UNAVAILABLE) for key in self.zones},
                        lock_locked=locked,
                    )
                    self.phase = Phase.ARMED_AWAY
                    events.append({
                        "type": "armed",
                        "routes": list(self.session.initial_routes),
                        "protected": sorted(self.session.protected_zones),
                        "pending": sorted(self.session.pending_zones),
                        "excluded": sorted(self.session.excluded_zones),
                    })
        self._expire_vibrations(now, events, window=vibration_window)
        return events

    def observed(
        self, zone: str, previous: ZoneState, current: ZoneState,
        *, now: float, recovery_policy: RecoveryPolicy = RecoveryPolicy.NOTIFY,
    ) -> list[dict[str, Any]]:
        """Apply state changes to the immutable per-episode coverage policy.

        Protected -> unavailable -> open ALWAYS triggers; unavailable does
        not remove protection. A contact UNKNOWN at arming may enter the
        protected set only on its first known CLOSED value. OPEN excludes
        it permanently (exactly like contacts already OPEN at commit).
        """
        if zone not in self.zones or self.phase != Phase.ARMED_AWAY or self.session is None:
            return []
        if zone in self.session.pending_zones:
            if current == ZoneState.UNAVAILABLE:
                return []
            protected = self.session.protected_zones
            if current == ZoneState.CLOSED:
                protected = protected | {zone}
            self.session = Session(
                identifier=self.session.identifier,
                known_zones=self.session.known_zones,
                protected_zones=frozenset(protected),
                pending_zones=self.session.pending_zones - {zone},
                initial_routes=self.session.initial_routes,
            )
            if current == ZoneState.CLOSED:
                return [{"type": "zone_enrolled", "zone": zone}]
            return [{"type": "zone_excluded", "zone": zone, "reason": "first_known_open"}]
        action = classify_opening(
            self.session, zone, previous, current,
            recovery_policy=recovery_policy,
        )
        if action == EventAction.TRIGGER:
            return self.trigger(zone)
        if action == EventAction.CRITICAL_NOTICE:
            return [{"type": "zone_fault", "zone": zone, "state": current.value}]
        return []

    def reconcile(self, states: Mapping[str, ZoneState], *, now: float) -> list[dict[str, Any]]:
        """Catch states already available before listeners attach at startup.

        In particular, an already-OPEN protected contact must never be
        silently tolerated just because Z2M updated before the HA listener
        subscribed. Pending contacts can be resolved from their first
        available state even without a new state-change event.
        """
        if self.phase != Phase.ARMED_AWAY or self.session is None:
            return []
        events: list[dict[str, Any]] = []
        for zone in sorted(self.session.pending_zones):
            state = states.get(zone, ZoneState.UNAVAILABLE)
            if state != ZoneState.UNAVAILABLE:
                events.extend(self.observed(zone, ZoneState.UNAVAILABLE, state, now=now))
        for zone in sorted(self.session.protected_zones):
            if states.get(zone, ZoneState.UNAVAILABLE) == ZoneState.OPEN:
                events.extend(self.trigger(zone))
                break
        return events

    def trigger(self, cause: str) -> list[dict[str, Any]]:
        """Trigger once per episode and never activate a physical output."""
        if self.phase != Phase.ARMED_AWAY:
            return []
        self.phase = Phase.TRIGGERED
        self._clear_vibration()
        return [{"type": "triggered", "cause": cause}]

    def disarm(self) -> list[dict[str, Any]]:
        """Discard the session; recover explicitly from a fault."""
        if self.phase == Phase.DISARMED and self.session is None:
            return []
        self.phase = Phase.DISARMED
        self.session = None
        self.arming_until = None
        self.fault = ""
        self.deterrent_requested = False
        self._clear_vibration()
        return [{"type": "disarmed"}]

    def vibration(
        self, zone: str, *, now: float, protected_zone: str | None = None,
        threshold: int = 2, debounce: float = 3, window: float = 20,
    ) -> list[dict[str, Any]]:
        """Confirm ONLY repeated rising edges from the same physical sensor.

        The first valid hit emits a prealert. A different sensor never adds
        confidence to this source, even in the same time window.
        """
        if self.phase != Phase.ARMED_AWAY or self.session is None:
            return []
        if protected_zone not in self.session.protected_zones:
            return [{
                "type": "vibration_ignored",
                "zone": zone,
                "reason": "linked_contact_not_protected",
            }]
        if threshold not in (2, 3) or debounce < 0 or window <= 0:
            raise ValueError("Invalid vibration confirmation settings")
        if now - self.vibration_last.get(zone, float("-inf")) < debounce:
            self.vibration_filtered += 1
            return [{"type": "vibration_filtered", "zone": zone}]
        self.vibration_last[zone] = now
        events: list[dict[str, Any]] = []
        self._expire_vibrations(now, events, window=window)
        self.vibration_hits.append((now, zone))
        n = sum(1 for _, source in self.vibration_hits if source == zone)
        if n == 1:
            self.vibration_prealarms += 1
            events.append({
                "type": "vibration_prealert",
                "zone": zone,
                "protected_contact": protected_zone,
                "threshold": threshold,
            })
        elif n >= threshold:
            events.extend(self.trigger(f"vibration:{zone}"))
        else:
            events.append({
                "type": "vibration_progress",
                "zone": zone,
                "count": n,
                "threshold": threshold,
            })
        return events

    def _expire_vibrations(
        self, now: float, events: list[dict[str, Any]], *, window: float = 20,
    ) -> None:
        kept = [
            (seen, source) for seen, source in self.vibration_hits
            if 0 <= now - seen < window
        ]
        if len(kept) < len(self.vibration_hits):
            self.vibration_hits = kept
            events.append({"type": "vibration_expired"})

    def _clear_vibration(self) -> None:
        self.vibration_hits.clear()
        self.vibration_last.clear()

    def snapshot(self) -> dict[str, Any]:
        """Persist critical state in one structured value."""
        return {
            "schema": 1,
            "phase": self.phase.value,
            "session": None if self.session is None else {
                "identifier": self.session.identifier,
                "known_zones": sorted(self.session.known_zones),
                "protected_zones": sorted(self.session.protected_zones),
                "pending_zones": sorted(self.session.pending_zones),
                "initial_routes": list(self.session.initial_routes),
            },
            "arming_until": self.arming_until,
            "fault": self.fault,
            "deterrent_requested": self.deterrent_requested,
        }

    def restore(self, data: Mapping[str, Any] | None) -> list[dict[str, Any]]:
        """Fail visibly on corruption; do not silently disarm an active system.

        A session's saved minimum route must remain represented by protected
        contacts. No zone set is rebuilt from current physical states.
        """
        if data is None:
            return []
        try:
            if data["schema"] != 1:
                raise ValueError("Unsupported storage schema")
            phase = Phase(data["phase"])
            serialized = data["session"]
            session: Session | None = None
            if serialized is not None:
                session = Session(
                    identifier=serialized["identifier"],
                    known_zones=frozenset(serialized["known_zones"]),
                    protected_zones=frozenset(serialized["protected_zones"]),
                    initial_routes=tuple(serialized["initial_routes"]),
                    pending_zones=frozenset(serialized.get("pending_zones", [])),
                )
                if not session.known_zones.issubset(self.zones):
                    raise ValueError("Configured zone set changed while active")
                # A required mandatory contact or minimum group can NEVER
                # rely on a pending (unknown) sensor for eligibility.
                if isinstance(self.paths, ProtectionRules) and (
                    session.pending_zones & set(self.paths.mandatory)
                ):
                    raise ValueError("Mandatory contact unexpectedly pending")
                protected_snapshot = {
                    zone: (
                        ZoneState.CLOSED if zone in session.protected_zones
                        else ZoneState.OPEN
                    ) for zone in session.known_zones
                }
                validity = evaluate_eligibility(
                    self.paths, protected_snapshot, lock_locked=True
                )
                if not validity.permitted:
                    raise ValueError("Session minimum protection missing")
                if not set(session.initial_routes).issubset(set(validity.routes)):
                    # One-time compatibility: v0.3 frozen sessions stored
                    # names of four route combinations. The new rule model
                    # stores one satisfied condition for each room.
                    legacy_names = {
                        "shutters", "windows", "living_window_bath_shutter",
                        "living_shutter_bath_window",
                    }
                    names = {group.name for group in self.paths.groups} if isinstance(
                        self.paths, ProtectionRules
                    ) else set()
                    is_home_migration = (
                        isinstance(self.paths, ProtectionRules)
                        and names == {"Sala", "Bagno"}
                        and set(session.initial_routes).issubset(legacy_names)
                    )
                    if not is_home_migration:
                        raise ValueError("Session minimum protection changed")
                    session = Session(
                        identifier=session.identifier,
                        known_zones=session.known_zones,
                        protected_zones=session.protected_zones,
                        initial_routes=validity.routes,
                        pending_zones=session.pending_zones,
                    )
            if phase in (Phase.ARMED_AWAY, Phase.TRIGGERED) and session is None:
                raise ValueError("Active state without a session")
            if phase in (Phase.DISARMED, Phase.ARMING) and session is not None:
                raise ValueError("Unexpected stored session")
            self.session = session
            self.deterrent_requested = (
                bool(data.get("deterrent_requested", False))
                if phase in (Phase.ARMED_AWAY, Phase.TRIGGERED) else False
            )
            self.fault = str(data.get("fault") or "")
            if phase == Phase.ARMING:
                self.phase = Phase.DISARMED
                self.arming_until = None
                self.fault = "Arming interrupted by Home Assistant restart"
                return [{"type": "startup_fault", "reason": self.fault}]
            self.phase = phase
            self.arming_until = None
            if phase == Phase.TRIGGERED:
                return [{"type": "triggered_restored"}]
            if phase == Phase.FAULT:
                return [{"type": "startup_fault", "reason": self.fault}]
            if phase == Phase.ARMED_AWAY:
                return [{"type": "armed_restored", "protected": sorted(session.protected_zones)}]
            return []
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            self.phase = Phase.FAULT
            self.deterrent_requested = False
            self.session = None
            self.arming_until = None
            self.fault = f"Invalid stored session: {exc}"
            return [{"type": "startup_fault", "reason": self.fault}]
