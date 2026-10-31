"""Pure policies: no Home Assistant, storage, timers or I/O."""

from __future__ import annotations

from typing import Mapping

from .model import (
    Eligibility,
    EventAction,
    MinimumPaths,
    RecoveryPolicy,
    Session,
    ZoneState,
)

def _closed(states: Mapping[str, ZoneState], zone: str) -> bool:
    """Unavailable, unknown and missing are never considered closed."""
    return states.get(zone) == ZoneState.CLOSED


def evaluate_eligibility(
    paths: MinimumPaths,
    states: Mapping[str, ZoneState],
    *,
    lock_locked: bool,
) -> Eligibility:
    """Door and lock, plus one closed barrier in each room (four routes)."""
    routes: list[str] = []
    problems: list[str] = []
    if not _closed(states, paths.entry):
        problems.append("entry_not_closed_or_unavailable")
    if not lock_locked:
        problems.append("lock_not_locked_or_unavailable")
    for name, pair in paths.route_pairs():
        if all(_closed(states, zone) for zone in pair):
            routes.append(name)
    if not routes:
        problems.append("no_minimum_path")
    return Eligibility(not problems, tuple(routes), tuple(problems))


def new_session(
    identifier: str,
    paths: MinimumPaths,
    states: Mapping[str, ZoneState],
    *,
    lock_locked: bool,
) -> Session:
    """Snapshot all closed contacts if at least one minimum route is satisfied.

    The future HA adapter must serialize input events and recheck before commit.
    """
    eligibility = evaluate_eligibility(paths, states, lock_locked=lock_locked)
    if not eligibility.permitted:
        raise ValueError("Cannot arm: " + ", ".join(eligibility.problems))
    return Session(
        identifier=identifier,
        known_zones=frozenset(states),
        protected_zones=frozenset(
            zone for zone, state in states.items() if state == ZoneState.CLOSED
        ),
        initial_routes=eligibility.routes,
    )


def classify_opening(
    session: Session,
    zone: str,
    previous: ZoneState,
    current: ZoneState,
    *,
    recovery_policy: RecoveryPolicy = RecoveryPolicy.NOTIFY,
    startup: bool = False,
) -> EventAction:
    """Classify an observation using the frozen protected-zone set.

    Startup observations are not proof of an intrusion.
    """
    if zone not in session.known_zones:
        return EventAction.IGNORE
    if zone not in session.protected_zones:
        return EventAction.IGNORE
    if current == ZoneState.UNAVAILABLE:
        return EventAction.CRITICAL_NOTICE
    if current != ZoneState.OPEN:
        return EventAction.IGNORE
    if startup:
        return EventAction.CRITICAL_NOTICE
    if previous == ZoneState.CLOSED:
        return EventAction.TRIGGER
    if previous == ZoneState.UNAVAILABLE:
        return (
            EventAction.TRIGGER
            if recovery_policy == RecoveryPolicy.TRIGGER
            else EventAction.CRITICAL_NOTICE
        )
    return EventAction.IGNORE


def startup_faults(
    session: Session,
    current: Mapping[str, ZoneState],
) -> frozenset[str]:
    """Detect open, offline or missing protected contacts at restart."""
    return frozenset(
        zone
        for zone in session.protected_zones
        if current.get(zone) != ZoneState.CLOSED
    )
