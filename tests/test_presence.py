"""Opt-in presence alerts: no automatic arm, and no repeat notification spam."""

import unittest

from custom_components.adaptive_alarm.engine.presence import PresenceAlerts


class PresenceAlertTests(unittest.TestCase):
    def observe(self, observer, now, *, phase="armed_away", people=("person.a",),
                empty=False, locked=False, home=True, empty_watch=False):
        return observer.observe(
            now=now, phase=phase, people_home=people,
            empty_sensor_on=empty, lock_locked=locked,
            watch_home=home, watch_empty=empty_watch,
        )

    def test_opt_in_disabled_is_silent(self):
        monitor = PresenceAlerts()
        self.assertEqual(self.observe(monitor, 0, home=False), [])
        self.assertEqual(self.observe(monitor, 100, home=False), [])

    def test_armed_with_person_home_delay_then_once(self):
        monitor = PresenceAlerts()
        self.assertEqual(self.observe(monitor, 0), [])
        self.assertEqual(self.observe(monitor, 19.9), [])
        self.assertEqual(self.observe(monitor, 20), [{
            "type": "presence_mismatch",
            "kind": "armed_with_person_home", "people": ["person.a"],
        }])
        self.assertEqual(self.observe(monitor, 100), [])
        # Returning to normal clears the latch; a new episode may alert again.
        self.assertEqual(self.observe(monitor, 101, people=()), [])
        self.assertEqual(self.observe(monitor, 102), [])
        self.assertEqual(self.observe(monitor, 122)[0]["kind"], "armed_with_person_home")

    def test_only_home_is_evidence(self):
        monitor = PresenceAlerts()
        self.assertEqual(self.observe(monitor, 0, people=()), [])
        self.assertEqual(self.observe(monitor, 25, people=()), [])
        self.assertEqual(self.observe(monitor, 26, phase="disarmed"), [])

    def test_empty_house_requires_locked_explicitly_empty_and_disarmed(self):
        monitor = PresenceAlerts()
        self.assertEqual(self.observe(
            monitor, 0, phase="disarmed", people=(), home=False,
            empty=True, locked=False, empty_watch=True,
        ), [])
        self.assertEqual(self.observe(
            monitor, 200, phase="disarmed", people=(), home=False,
            empty=True, locked=True, empty_watch=True,
        ), [])
        self.assertEqual(self.observe(
            monitor, 319.9, phase="disarmed", people=(), home=False,
            empty=True, locked=True, empty_watch=True,
        ), [])
        self.assertEqual(self.observe(
            monitor, 320, phase="disarmed", people=(), home=False,
            empty=True, locked=True, empty_watch=True,
        ), [{"type": "presence_mismatch", "kind": "empty_house_disarmed"}])
        self.assertEqual(self.observe(
            monitor, 400, phase="disarmed", people=(), home=False,
            empty=True, locked=True, empty_watch=True,
        ), [])

    def test_unavailable_empty_sensor_or_unlocked_door_resets(self):
        monitor = PresenceAlerts()
        args = dict(phase="disarmed", people=(), home=False, empty_watch=True)
        self.assertEqual(self.observe(monitor, 0, empty=True, locked=True, **args), [])
        self.assertEqual(self.observe(monitor, 70, empty=False, locked=True, **args), [])
        self.assertEqual(self.observe(monitor, 150, empty=True, locked=True, **args), [])
        self.assertEqual(self.observe(monitor, 269, empty=True, locked=True, **args), [])
        self.assertEqual(self.observe(monitor, 270, empty=True, locked=True, **args)[0]["kind"], "empty_house_disarmed")
        self.assertEqual(self.observe(monitor, 271, empty=True, locked=False, **args), [])
        self.assertEqual(self.observe(monitor, 272, empty=True, locked=True, **args), [])
        self.assertEqual(self.observe(monitor, 392, empty=True, locked=True, **args)[0]["kind"], "empty_house_disarmed")

    def test_siren_triggered_and_arming_never_count_as_home_mismatch(self):
        monitor = PresenceAlerts()
        for phase in ("arming", "triggered", "disarmed", "fault"):
            self.assertEqual(self.observe(monitor, 0, phase=phase), [])
            self.assertEqual(self.observe(monitor, 200, phase=phase), [])

    def test_restart_restarts_full_grace_period(self):
        first = PresenceAlerts()
        self.assertEqual(self.observe(first, 0), [])
        self.assertEqual(self.observe(first, 20)[0]["kind"], "armed_with_person_home")
        restored = PresenceAlerts()
        self.assertEqual(self.observe(restored, 21), [])
        self.assertEqual(self.observe(restored, 40), [])
        self.assertEqual(self.observe(restored, 41)[0]["kind"], "armed_with_person_home")


if __name__ == "__main__":
    unittest.main()
