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
                    (values[1] == C or values[3] == C)
                    and (values[2] == C or values[4] == C)
                )
                e = AlarmMachine(PATHS, ZONES)
                e.arm(dict(zip(names, values)), locked=locked, now=0, delay=0)
                self.assertEqual(e.phase == Phase.ARMED_AWAY, expected)

    def test_mixed_route_survives_restart(self):
        engine = armed(sh_sala=O, w_bagno=O)
        self.assertEqual(
            engine.session.initial_routes, ("living_window_bath_shutter",)
        )
        restored = AlarmMachine(PATHS, ZONES)
        self.assertEqual(restored.restore(engine.snapshot())[0]["type"], "armed_restored")
        self.assertEqual(restored.phase, Phase.ARMED_AWAY)
        self.assertEqual(restored.session.initial_routes, engine.session.initial_routes)

    def test_arming_revalidates_mixed_route_at_commit(self):
        engine = AlarmMachine(PATHS, ZONES)
        engine.arm(snapshot(sh_sala=O, w_bagno=O), locked=True, now=10, delay=60)
        engine.tick(snapshot(sh_sala=O, w_bagno=O), locked=True, now=70)
        self.assertEqual(engine.phase, Phase.ARMED_AWAY)

    def test_arming_rejects_when_one_room_loses_all_barriers(self):
        engine = AlarmMachine(PATHS, ZONES)
        engine.arm(snapshot(), locked=True, now=10, delay=60)
        events = engine.tick(snapshot(sh_sala=O, w_sala=O), locked=True, now=70)
        self.assertEqual(engine.phase, Phase.DISARMED)
        self.assertIn("arm_rejected", [event["type"] for event in events])

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

    def test_excluded_window_wind_close_then_reopen_never_triggers(self):
        """An initially open window stays excluded, even after a long closure."""
        for duration in (0.1, 4.9, 5, 60, 3600, 86400):
            with self.subTest(duration=duration):
                e = armed()
                original = e.snapshot()
                self.assertEqual(e.observed("studio", O, C, now=200), [])
                self.assertEqual(
                    e.tick(snapshot(studio=C), locked=True, now=200 + duration), []
                )
                self.assertEqual(
                    e.observed("studio", C, O, now=201 + duration), []
                )
                self.assertEqual(e.phase, Phase.ARMED_AWAY)
                self.assertEqual(e.snapshot(), original)

    def test_minimum_contact_excluded_under_other_valid_route_stays_excluded(self):
        e = armed(w_sala=O, w_bagno=O)
        self.assertNotIn("w_sala", e.session.protected_zones)
        self.assertEqual(e.observed("w_sala", O, C, now=200), [])
        self.assertEqual(
            e.tick(snapshot(w_sala=C, w_bagno=O), locked=True, now=500), []
        )
        self.assertEqual(e.observed("w_sala", C, O, now=501), [])
        self.assertEqual(e.phase, Phase.ARMED_AWAY)
        self.assertEqual(
            e.session.excluded_zones,
            frozenset({"studio", "w_sala", "w_bagno"}),
        )

    def test_exclusion_preserved_after_restart_and_closed_contact(self):
        e = armed()
        restarted = AlarmMachine(PATHS, ZONES)
        restarted.restore(e.snapshot())
        self.assertEqual(restarted.observed("studio", O, C, now=200), [])
        self.assertEqual(
            restarted.tick(snapshot(studio=C), locked=True, now=100000), []
        )
        self.assertEqual(restarted.observed("studio", C, O, now=100001), [])
        self.assertEqual(restarted.phase, Phase.ARMED_AWAY)

    def test_disarm_rearm_recalculates_frozen_zone_set(self):
        e = armed()
        self.assertIn("studio", e.session.excluded_zones)
        e.disarm()
        e.arm(snapshot(studio=C), locked=True, now=300, delay=0)
        self.assertIn("studio", e.session.protected_zones)
        self.assertEqual(
            e.observed("studio", C, O, now=350)[0]["type"], "triggered"
        )

    def test_protected_contact_remains_protected(self):
        e = armed(studio=C)
        self.assertIn("studio", e.session.protected_zones)
        self.assertEqual(
            e.observed("studio", C, O, now=250)[0]["type"], "triggered"
        )

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

    def test_unpaired_or_excluded_vibration_cannot_trigger(self):
        engine = armed()
        for i in range(10):
            self.assertEqual(
                engine.vibration("unpaired", now=200 + i * 4),
                [{"type": "vibration_ignored", "zone": "unpaired",
                  "reason": "linked_contact_not_protected"}],
            )
            self.assertEqual(
                engine.vibration("v_studio", protected_zone="studio", now=200 + i * 4),
                [{"type": "vibration_ignored", "zone": "v_studio",
                  "reason": "linked_contact_not_protected"}],
            )
        self.assertEqual(engine.vibration_hits, [])
        self.assertEqual(engine.phase, Phase.ARMED_AWAY)

    def test_vibration_only_counts_if_its_specific_contact_is_protected(self):
        engine = armed(w_sala=O)
        self.assertEqual(
            engine.vibration("v_living_window", protected_zone="w_sala", now=200)[0]["type"],
            "vibration_ignored",
        )
        self.assertEqual(
            engine.vibration("v_living_shutter", protected_zone="sh_sala", now=201)[0]["type"],
            "vibration_prealert",
        )
        self.assertEqual(
            engine.vibration("v_living_window", protected_zone="w_sala", now=202)[0]["type"],
            "vibration_ignored",
        )
        self.assertEqual(engine.phase, Phase.ARMED_AWAY)
        self.assertEqual(
            engine.vibration("v_living_shutter", protected_zone="sh_sala", now=205)[0]["type"],
            "triggered",
        )

    def test_vibration_timer_uses_selected_window(self):
        engine = armed()
        engine.vibration("v1", protected_zone="entry", now=200)
        engine.tick(snapshot(), locked=True, now=216, vibration_window=15)
        self.assertEqual(engine.vibration_hits, [])
        engine.vibration("v1", protected_zone="entry", now=217)
        self.assertEqual(engine.phase, Phase.ARMED_AWAY)

    def test_both_vibration_hits_trigger(self):
        e = armed()
        self.assertEqual(e.vibration("vib_entry", now=200, protected_zone="entry")[0]["type"], "vibration_prealert")
        self.assertEqual(e.vibration("vib_entry", now=201, protected_zone="entry")[0]["type"], "vibration_filtered")
        events = e.vibration("vib_entry", now=204, protected_zone="entry")
        self.assertTrue(any(x["type"] == "triggered" for x in events))

    def test_cross_profile(self):
        e = armed()
        e.vibration("v1", protected_zone="entry", now=200, profile="cross")
        self.assertEqual(e.vibration("v1", protected_zone="entry", now=204, profile="cross"), [])
        events = e.vibration("v2", protected_zone="sh_sala", now=205, profile="cross")
        self.assertTrue(any(x["type"] == "triggered" for x in events))

    def test_temporale_grazia(self):
        e = armed()
        e.vibration("v1", protected_zone="entry", now=200, storm=True)
        result = e.vibration("v1", protected_zone="entry", now=204, storm=True)
        self.assertIn("vibration_storm_grace", [x["type"] for x in result])
        later = e.vibration("v1", protected_zone="entry", now=208, storm=True)
        self.assertEqual(e.phase, Phase.TRIGGERED)
        self.assertIn("triggered", [x["type"] for x in later])

    def test_cautious_profile(self):
        e = armed()
        e.vibration("v1", protected_zone="entry", now=200, profile="cautious")
        e.vibration("v1", protected_zone="entry", now=204, profile="cautious")
        self.assertEqual(e.phase, Phase.ARMED_AWAY)
        e.vibration("v1", protected_zone="entry", now=208, profile="cautious")
        self.assertEqual(e.phase, Phase.TRIGGERED)

    def test_disarm_does_not_keep_pending(self):
        e = armed()
        e.vibration("v1", protected_zone="entry", now=200)
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
