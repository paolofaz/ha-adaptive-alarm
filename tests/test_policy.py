"""Pure Python policy tests. No Home Assistant installation required."""

import itertools
import unittest

from custom_components.adaptive_alarm.engine import (
    EventAction,
    MinimumPaths,
    RecoveryPolicy,
    ZoneState,
    classify_opening,
    evaluate_eligibility,
    new_session,
    startup_faults,
)

P = MinimumPaths(
    entry="door",
    shutters=("shutter_living", "shutter_bath"),
    windows=("window_living", "window_bath"),
)
C = ZoneState.CLOSED
O = ZoneState.OPEN
U = ZoneState.UNAVAILABLE


def states(**changes):
    data = {
        "door": C,
        "shutter_living": C,
        "shutter_bath": C,
        "window_living": C,
        "window_bath": C,
        "studio": O,
    }
    data.update(changes)
    return data


class EligibilityTests(unittest.TestCase):
    def test_shutters_only(self):
        data = states(window_living=O, window_bath=O)
        self.assertEqual(evaluate_eligibility(P, data, lock_locked=True).routes, ("shutters",))

    def test_windows_only(self):
        data = states(shutter_living=O, shutter_bath=O)
        self.assertEqual(evaluate_eligibility(P, data, lock_locked=True).routes, ("windows",))

    def test_both_routes(self):
        self.assertEqual(
            evaluate_eligibility(P, states(), lock_locked=True).routes,
            ("shutters", "windows"),
        )

    def test_never_accept_unlocked_or_unknown_door(self):
        for door in (O, U):
            self.assertFalse(evaluate_eligibility(P, states(door=door), lock_locked=True).permitted)
        self.assertFalse(evaluate_eligibility(P, states(), lock_locked=False).permitted)

    def test_exhaustive_minimum_paths(self):
        keys = ["door", "shutter_living", "shutter_bath", "window_living", "window_bath"]
        for values in itertools.product((C, O, U), repeat=5):
            data = dict(zip(keys, values))
            for lock_locked in (True, False):
                expected = (
                    lock_locked
                    and data["door"] == C
                    and (
                        data["shutter_living"] == C and data["shutter_bath"] == C
                        or data["window_living"] == C and data["window_bath"] == C
                    )
                )
                with self.subTest(states=data, locked=lock_locked):
                    self.assertEqual(
                        evaluate_eligibility(P, data, lock_locked=lock_locked).permitted,
                        expected,
                    )

    def test_missing_sensor_fails_closed(self):
        data = {"door": C, "shutter_living": C, "shutter_bath": C}
        self.assertTrue(evaluate_eligibility(P, data, lock_locked=True).permitted)
        self.assertFalse(
            evaluate_eligibility(P, {"door": C, "shutter_living": C}, lock_locked=True).permitted
        )

    def test_duplicate_path_contacts_rejected(self):
        with self.assertRaises(ValueError):
            MinimumPaths(entry="door", shutters=("door", "s2"), windows=("w1", "w2"))


class SessionTests(unittest.TestCase):
    def test_snapshot_includes_only_closed(self):
        session = new_session("episode-1", P, states(studio=O), lock_locked=True)
        self.assertNotIn("studio", session.protected_zones)
        self.assertEqual(session.excluded_zones, frozenset({"studio"}))

    def test_no_session_when_minimum_not_met(self):
        with self.assertRaises(ValueError):
            new_session("bad", P, states(door=O), lock_locked=True)

    def test_frozen_snapshot_does_not_reclassify_excluded_zones(self):
        session = new_session("episode-2", P, states(), lock_locked=True)
        self.assertIn("studio", session.excluded_zones)
        for previous in (C, O, U):
            with self.subTest(previous=previous):
                self.assertEqual(
                    classify_opening(session, "studio", previous, O),
                    EventAction.IGNORE,
                )

    def test_opening_protected_triggers(self):
        session = new_session("x", P, states(), lock_locked=True)
        self.assertEqual(
            classify_opening(session, "door", C, O),
            EventAction.TRIGGER,
        )

    def test_excluded_opening_does_not_trigger(self):
        session = new_session("x", P, states(), lock_locked=True)
        self.assertEqual(classify_opening(session, "studio", O, O), EventAction.IGNORE)

    def test_offline_recovery_policy(self):
        session = new_session("x", P, states(), lock_locked=True)
        self.assertEqual(
            classify_opening(session, "door", U, O),
            EventAction.CRITICAL_NOTICE,
        )
        self.assertEqual(
            classify_opening(session, "door", U, O, recovery_policy=RecoveryPolicy.TRIGGER),
            EventAction.TRIGGER,
        )

    def test_startup_never_guesses_intrusion(self):
        session = new_session("x", P, states(), lock_locked=True)
        self.assertEqual(
            classify_opening(
                session, "door", C, O,
                recovery_policy=RecoveryPolicy.TRIGGER, startup=True
            ),
            EventAction.CRITICAL_NOTICE,
        )
        self.assertEqual(
            startup_faults(session, {"door": O}),
            session.protected_zones,
        )


if __name__ == "__main__":
    unittest.main()
