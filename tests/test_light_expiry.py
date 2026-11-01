"""Safety invariants for automatic deterrent light cleanup."""

import unittest

from custom_components.adaptive_alarm.engine.light_expiry import (
    LIGHT_ACK_TIMEOUT, LightLease, PendingLight, confirm_transition, may_turn_off,
)


class LightLeaseTests(unittest.TestCase):
    def setUp(self):
        self.lease = LightLease(
            "light.sala", "2026-11-01T06:00:00+00:00", 121.0, "episode-1",
        )

    def test_may_switch_off_only_unchanged_activated_light(self):
        self.assertTrue(may_turn_off(
            self.lease, state="on", last_updated=self.lease.last_updated,
            alarm_triggered=False, current_episode="episode-1",
        ))
        for state, updated, triggered, episode in [
            ("off", self.lease.last_updated, False, "episode-1"),
            ("unknown", self.lease.last_updated, False, "episode-1"),
            ("on", None, False, "episode-1"),
            ("on", "2026-11-01T06:00:02+00:00", False, "episode-1"),
            ("on", self.lease.last_updated, True, "episode-1"),
            ("on", self.lease.last_updated, False, "episode-2"),
        ]:
            with self.subTest(state=state, updated=updated, triggered=triggered):
                self.assertFalse(may_turn_off(
                    self.lease, state=state, last_updated=updated,
                    alarm_triggered=triggered, current_episode=episode,
                ))

    def test_late_state_change_can_be_acknowledged(self):
        pending = PendingLight(
            entity_id="light.sala",
            baseline_updated="2026-11-01T10:00:00+00:00",
            ack_deadline=115,
            off_deadline=220,
            episode="episode-1",
        )
        lease = confirm_transition(
            pending, now=106,
            old_state="off",
            old_updated="2026-11-01T10:00:00+00:00",
            new_state="on",
            new_updated="2026-11-01T10:00:06+00:00",
            current_episode="episode-1",
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.deadline, 220)
        self.assertTrue(may_turn_off(
            lease, state="on", last_updated=lease.last_updated,
            current_episode="episode-1", alarm_triggered=False,
        ))

    def test_pending_lease_is_rejected_if_incorrect_or_late(self):
        pending = PendingLight(
            entity_id="light.sala",
            baseline_updated="start",
            ack_deadline=115,
            off_deadline=220,
            episode="episode-1",
        )
        valid = {
            "now": 105,
            "old_state": "off",
            "old_updated": "start",
            "new_state": "on",
            "new_updated": "finish",
            "current_episode": "episode-1",
        }
        changes = [
            {"now": 116},
            {"old_state": "on"},
            {"old_updated": "someone_changed_the_light"},
            {"new_state": "off"},
            {"new_state": "unavailable"},
            {"new_updated": "start"},
            {"new_updated": None},
            {"current_episode": "episode-2"},
            {"current_episode": None},
        ]
        for change in changes:
            with self.subTest(change=change):
                self.assertIsNone(confirm_transition(
                    pending, **(valid | change)
                ))

    def test_ack_window_is_bounded(self):
        self.assertEqual(LIGHT_ACK_TIMEOUT, 15)

    def test_serialization_and_reject_siren(self):
        self.assertEqual(LightLease.from_dict(self.lease.to_dict()), self.lease)
        with self.assertRaises(ValueError):
            LightLease.from_dict({**self.lease.to_dict(), "entity_id": "siren.real"})


if __name__ == "__main__":
    unittest.main()
