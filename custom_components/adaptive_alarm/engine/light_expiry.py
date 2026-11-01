"""Fail-closed model for optional automatic light cleanup.

A light may be switched OFF only if it was OFF before deterrence, was
subsequently confirmed ON and has had no visible state/attribute update since
that confirmation. Restart invalidates ownership rather than guessing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LightLease:
    entity_id: str
    last_updated: str
    deadline: float
    episode: str

    def to_dict(self) -> dict[str, str | float]:
        return {
            "entity_id": self.entity_id,
            "last_updated": self.last_updated,
            "deadline": self.deadline,
            "episode": self.episode,
        }

    @classmethod
    def from_dict(cls, value: dict) -> "LightLease":
        obj = cls(
            entity_id=value["entity_id"],
            last_updated=value["last_updated"],
            deadline=float(value["deadline"]),
            episode=value["episode"],
        )
        if not obj.entity_id.startswith("light.") or not obj.last_updated or not obj.episode:
            raise ValueError("Invalid stored light claim")
        return obj


def may_turn_off(
    lease: LightLease, *, state: str | None, last_updated: str | None,
    alarm_triggered: bool, current_episode: str | None,
) -> bool:
    """Never switch off a light with uncertain ownership or during alarm."""
    if alarm_triggered:
        return False
    if current_episode is not None and current_episode != lease.episode:
        return False
    return state == "on" and last_updated == lease.last_updated
