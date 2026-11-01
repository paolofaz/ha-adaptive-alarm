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


# Home Assistant light state can arrive after a successful turn_on service
# request. Keep a SHORT, in-memory acknowledgement window; never use an
# unverified pending request as authority to turn the light off.
LIGHT_ACK_TIMEOUT = 15


@dataclass(frozen=True)
class PendingLight:
    """Light was OFF before we requested ON; waiting for state confirmation."""

    entity_id: str
    baseline_updated: str
    ack_deadline: float
    off_deadline: float
    episode: str


def confirm_transition(
    pending: PendingLight, *, now: float,
    old_state: str | None, old_updated: str | None,
    new_state: str | None, new_updated: str | None,
    current_episode: str | None,
) -> LightLease | None:
    """Accept exactly an OFF→ON transition starting at the sampled OFF state.

    We cannot prove a device's physical origin from state events, so if another
    actor changes state before the expected transition we fail closed. Late
    state updates are ignored instead of giving the integration permanent
    authority to shut a light off.
    """
    if (
        now > pending.ack_deadline
        or current_episode != pending.episode
        or old_state != "off"
        or old_updated != pending.baseline_updated
        or new_state != "on"
        or not new_updated
        or new_updated == old_updated
    ):
        return None
    return LightLease(
        entity_id=pending.entity_id,
        last_updated=new_updated,
        deadline=pending.off_deadline,
        episode=pending.episode,
    )
