"""Pure, read-only diagnosis of currently problematic protected contacts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping


def protected_state_issues(
    protected: Iterable[str], raw_states: Mapping[str, str | None],
) -> dict[str, str]:
    """Explain unknown/unavailable/missing without changing session coverage."""
    issues: dict[str, str] = {}
    for zone in sorted(protected):
        raw = raw_states.get(zone)
        if raw == "off":
            continue
        if raw == "on":
            issues[zone] = "open"
        elif raw in ("unknown", "unavailable"):
            issues[zone] = raw
        elif raw is None:
            issues[zone] = "missing"
        else:
            issues[zone] = "unexpected"
    return issues
