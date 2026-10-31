"""State-transition tests for the HACS-installable simulation engine."""

import itertools
import unittest

from custom_components.adaptive_alarm.engine import MinimumPaths, ZoneState
from custom_components.adaptive_alarm.engine.runtime import AlarmMachine, Phase

C = ZoneState.CLOSED
O = ZoneState.OPEN
U = ZoneState.UNAVAILABLE
PATHS = MinimumPaths("entry", ("sh_sala", "sh_bagno"), ("w_sala", "w_bagno"))
ZONES = frozenset({"entry", "sh_sala", "sh_bagno", "w_sala", "w_bagno", "studio"})


def snapshot(**kwargs):
    return {
        "entry": C, "sh_sala": C, "sh_bagno": C, "w_sala": C,
        "w_bagno": C, "studio": O, **kwargs,
    }


def armed(**kwargs):
    engine = AlarmMachine(PATHS, ZONES)
    engine.arm(snapshot(**kwargs), locked=True, now=100, delay=0)
    assert engine.phase == Phase.ARMED_AWAY
    return engine


class RuntimeTests(unittest.TestCase):
    def test_all_minimum_combinations(self):
        names = ["entry", "sh_sala", "sh_bagno", "w_sala", "w_bagno"]
        for values in itertools.product((C, O, U), repeat=5):
            for locked in (True, False):
                expected = locked and values[0] == C and (
                    values[1] == C and values[2] == C
                    or values[3] == C and values[4] == C
                )
                e = AlarmMachine(PATHS, ZONES)
                e.arm(dict(zip(names, values)), locked=locked, now=0, delay=0)
                self.assertEqual(e.phase == Phase.ARMED_AWAY, expected)

    def test_delay_final_validation(self):
        e = AlarmMachine(PATHS, ZONES)
        e.arm(snapshot(), locked=True, now=10, delay=60)
        self.assertEqual(e.phase, Phase.ARMING)
        e.tick(snapshot(), locked=True, now=69)
        self.assertEqual(e.phase, Phase.ARMING)
        e.tick(snapshot(entry=O), locked=True, now=70)
        self.assertEqual(e.phase, Phase.DISARMED)
        self.assertIsNone(e.session)

    def test_lock_stays_required_at_commit(self):
        e = AlarmMachine(PATHS, ZONES)
        e.arm(snapshot(), locked=True, now=10, delay=60)
        e.tick(snapshot(), locked=False, now=70)
        self.assertEqual(e.phase, Phase.DISARMED)

    def test_dynamic_closure(self):
        e = armed()
        e.observed("studio", O, C, now=200)
        self.assertNotIn("studio", e.session.protected_zones)
        e.tick(snapshot(studio=C), locked=True, now=204.9)
        self.assertNotIn("studio", e.session.protected_zones)
        events = e.tick(snapshot(studio=C), locked=True, now=205)
        self.assertIn("studio", e.session.protected_zones)
        self.assertEqual(events[0]["type"], "zone_added")

    def test_race_exact_five_second_boundary(self):
        e = armed()
        e.observed("studio", O, C, now=200)
        result = e.observed("studio", C, O, now=205)
        self.assertEqual([v["type"] for v in result], ["zone_added", "triggered"])
        self.assertEqual(e.phase, Phase.TRIGGERED)

    def test_four_point_nine_does_not_trigger(self):
        e = armed()
        e.observed("studio", O, C, now=200)
        self.assertEqual(e.observed("studio", C, O, now=204.9), [])
        self.assertEqual(e.phase, Phase.ARMED_AWAY)

    def test_protected_offline_and_return(self):
        e = armed()
        self.assertEqual(e.observed("entry", C, U, now=200)[0]["type"], "zone_fault")
        self.assertEqual(e.observed("entry", U, O, now=201)[0]["type"], "zone_fault")
        self.assertEqual(e.phase, Phase.ARMED_AWAY)

    def test_trigger_one_per_episode(self):
        e = armed()
        self.assertEqual(e.observed("entry", C, O, now=200)[0]["type"], "triggered")
        self.assertEqual(e.observed("w_sala", C, O, now=201), [])
        self.assertEqual(e.phase, Phase.TRIGGERED)

    def test_restore_preserves_exclusions(self):
        e = armed()
        saved = e.snapshot()
        recovered = AlarmMachine(PATHS, ZONES)
        recovered.restore(saved)
        self.assertEqual(recovered.phase, Phase.ARMED_AWAY)
        self.assertEqual(recovered.session.excluded_zones, frozenset({"studio"}))

    def test_corrupt_storage_is_critical_not_disarmed(self):
        e = AlarmMachine(PATHS, ZONES)
        e.restore({"schema": 1, "phase": "armed_away", "session": None})
        self.assertEqual(e.phase, Phase.FAULT)
        self.assertNotEqual(e.phase, Phase.DISARMED)

    def test_restored_triggered_not_retriggered(self):
        e = armed()
        e.trigger("entry")
        restored = AlarmMachine(PATHS, ZONES)
        events = restored.restore(e.snapshot())
        self.assertEqual(restored.phase, Phase.TRIGGERED)
        self.assertEqual(events, [{"type": "triggered_restored"}])

    def test_arming_restart_aborts(self):
        e = AlarmMachine(PATHS, ZONES)
        e.arm(snapshot(), locked=True, now=100, delay=60)
        restarted = AlarmMachine(PATHS, ZONES)
        restarted.restore(e.snapshot())
        self.assertEqual(restarted.phase, Phase.DISARMED)
        self.assertIn("restart", restarted.fault)

    def test_invalid_session_missing_route(self):
        e = armed()
        saved = e.snapshot()
        saved["session"]["protected_zones"] = ["entry"]
        another = AlarmMachine(PATHS, ZONES)
        another.restore(saved)
        self.assertEqual(another.phase, Phase.FAULT)

    def test_both_vibration_hits_trigger(self):
        e = armed()
        self.assertEqual(e.vibration("vib_entry", now=200)[0]["type"], "vibration_prealert")
        self.assertEqual(e.vibration("vib_entry", now=201)[0]["type"], "vibration_filtered")
        events = e.vibration("vib_entry", now=204)
        self.assertTrue(any(x["type"] == "triggered" for x in events))

    def test_cross_profile(self):
        e = armed()
        e.vibration("v1", now=200, profile="cross")
        self.assertEqual(e.vibration("v1", now=204, profile="cross"), [])
        events = e.vibration("v2", now=205, profile="cross")
        self.assertTrue(any(x["type"] == "triggered" for x in events))

    def test_temporale_grazia(self):
        e = armed()
        e.vibration("v1", now=200, storm=True)
        result = e.vibration("v1", now=204, storm=True)
        self.assertIn("vibration_storm_grace", [x["type"] for x in result])
        later = e.vibration("v1", now=208, storm=True)
        self.assertEqual(e.phase, Phase.TRIGGERED)
        self.assertIn("triggered", [x["type"] for x in later])

    def test_cautious_profile(self):
        e = armed()
        e.vibration("v1", now=200, profile="cautious")
        e.vibration("v1", now=204, profile="cautious")
        self.assertEqual(e.phase, Phase.ARMED_AWAY)
        e.vibration("v1", now=208, profile="cautious")
        self.assertEqual(e.phase, Phase.TRIGGERED)

    def test_disarm_does_not_keep_pending(self):
        e = armed()
        e.vibration("v1", now=200)
        e.disarm()
        self.assertEqual(e.phase, Phase.DISARMED)
        self.assertFalse(e.vibration_hits)
        self.assertEqual(e.observed("entry", C, O, now=204), [])

    def test_restart_and_rearm_new_episode(self):
        e = armed()
        first = e.session.identifier
        e.disarm()
        e.arm(snapshot(), locked=True, now=300, delay=0)
        self.assertNotEqual(first, e.session.identifier)


if __name__ == "__main__":
    unittest.main()
