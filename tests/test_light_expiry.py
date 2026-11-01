"""Safety invariants for automatic deterrent light cleanup."""

import unittest

from custom_components.adaptive_alarm.engine.light_expiry import LightLease, may_turn_off


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

    def test_serialization_and_reject_siren(self):
        self.assertEqual(LightLease.from_dict(self.lease.to_dict()), self.lease)
        with self.assertRaises(ValueError):
            LightLease.from_dict({**self.lease.to_dict(), "entity_id": "siren.real"})


if __name__ == "__main__":
    unittest.main()
