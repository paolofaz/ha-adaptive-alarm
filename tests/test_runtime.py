"""State-transition tests for the HACS-installable simulation engine."""

import itertools
import unittest

from custom_components.adaptive_alarm.engine import MinimumPaths, ZoneState
from custom_components.adaptive_alarm.engine.runtime import AlarmMachine, Phase
from custom_components.adaptive_alarm.engine.model import RecoveryPolicy

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

    def test_delayed_arm_can_start_before_door_is_locked(self):
        e = AlarmMachine(PATHS, ZONES)
        events = e.arm(snapshot(entry=O), locked=False, now=100, delay=60)
        self.assertEqual(e.phase, Phase.ARMING)
        self.assertEqual(events[0]["type"], "arming")
        self.assertIsNone(e.session)
        e.tick(snapshot(), locked=True, now=160)
        self.assertEqual(e.phase, Phase.ARMED_AWAY)
        self.assertIn("entry", e.session.protected_zones)

    def test_delayed_arm_rejected_if_door_open_at_deadline(self):
        e = AlarmMachine(PATHS, ZONES)
        e.arm(snapshot(entry=O), locked=False, now=100, delay=60)
        result = e.tick(snapshot(entry=O), locked=True, now=160)
        self.assertEqual(e.phase, Phase.DISARMED)
        self.assertIsNone(e.session)
        self.assertEqual(result[0]["type"], "arm_rejected")
        self.assertIn("entry_not_closed_or_unavailable", result[0]["problems"])
        self.assertIn("entry_not_closed_or_unavailable", e.fault)

    def test_immediate_arm_rejects_invalid_before_setting_arming(self):
        e = AlarmMachine(PATHS, ZONES)
        result = e.arm(snapshot(entry=O), locked=False, now=100, delay=0)
        self.assertEqual(e.phase, Phase.DISARMED)
        self.assertIsNone(e.session)
        self.assertEqual([x["type"] for x in result], ["arm_rejected"])

    def test_delayed_arm_can_be_cancelled_before_final_check(self):
        e = AlarmMachine(PATHS, ZONES)
        e.arm(snapshot(entry=O), locked=False, now=100, delay=60)
        self.assertEqual(e.disarm(), [{"type": "disarmed"}])
        self.assertEqual(e.tick(snapshot(), locked=True, now=200), [])
        self.assertEqual(e.phase, Phase.DISARMED)

    def test_delayed_arm_uses_only_final_snapshot(self):
        e = AlarmMachine(PATHS, ZONES)
        e.arm(snapshot(w_sala=O, sh_bagno=O), locked=False, now=100, delay=60)
        final = snapshot(sh_sala=O, w_bagno=O)
        events = e.tick(final, locked=True, now=160)
        self.assertEqual(e.phase, Phase.ARMED_AWAY)
        self.assertEqual(e.session.initial_routes, ("living_window_bath_shutter",))
        self.assertIn("armed", [x["type"] for x in events])

    def test_window_vibration_ignores_shutter_only_coverage(self):
        e = armed(w_sala=O)
        for i in range(5):
            events = e.vibration(
                "v_window_sala", now=200 + i * 4, protected_zone="w_sala"
            )
            self.assertEqual(events[0]["type"], "vibration_ignored")
        self.assertEqual(e.phase, Phase.ARMED_AWAY)
        self.assertNotIn("w_sala", e.session.protected_zones)
        self.assertIn("sh_sala", e.session.protected_zones)

    def test_window_vibration_counts_when_window_closed_without_shutter(self):
        e = armed(sh_sala=O)
        self.assertIn("w_sala", e.session.protected_zones)
        self.assertNotIn("sh_sala", e.session.protected_zones)
        e.vibration("v_window_sala", now=200, protected_zone="w_sala")
        result = e.vibration("v_window_sala", now=204, protected_zone="w_sala")
        self.assertIn("triggered", [x["type"] for x in result])

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

    def test_protected_offline_then_closed_is_still_protected(self):
        e = armed()
        before = e.session.protected_zones
        self.assertEqual(e.observed("entry", C, U, now=200), [])
        self.assertIn("entry", e.session.protected_zones)
        self.assertEqual(e.observed("entry", U, C, now=201), [])
        self.assertEqual(e.session.protected_zones, before)
        self.assertEqual(e.observed("entry", C, O, now=202)[0]["type"], "triggered")

    def test_protected_offline_then_open_triggers_even_with_legacy_notify(self):
        for policy in (RecoveryPolicy.NOTIFY, RecoveryPolicy.TRIGGER):
            with self.subTest(policy=policy):
                e = armed()
                self.assertEqual(
                    e.observed("entry", C, U, now=200, recovery_policy=policy), []
                )
                self.assertIn("entry", e.session.protected_zones)
                events = e.observed(
                    "entry", U, O, now=201, recovery_policy=policy,
                )
                self.assertEqual(events, [
                    {"type": "triggered", "cause": "entry"}
                ])
                self.assertEqual(e.phase, Phase.TRIGGERED)

    def test_reboot_all_unavailable_does_not_demote_protected_contacts(self):
        e = armed(studio=C)
        previous = e.snapshot()
        rebooted = AlarmMachine(PATHS, ZONES)
        rebooted.restore(previous)
        all_unknown = {zone: U for zone in ZONES}
        self.assertEqual(rebooted.reconcile(all_unknown, now=1000), [])
        self.assertEqual(rebooted.session.protected_zones, e.session.protected_zones)
        self.assertEqual(rebooted.snapshot()["session"], previous["session"])
        self.assertEqual(rebooted.observed("w_sala", U, C, now=1001), [])
        events = rebooted.observed("w_sala", C, O, now=1002)
        self.assertEqual(events[0]["type"], "triggered")

    def test_restart_recovers_already_open_contact_before_listener(self):
        e = armed()
        recovered = AlarmMachine(PATHS, ZONES)
        recovered.restore(e.snapshot())
        states = {zone: U for zone in ZONES}
        states["w_sala"] = O
        self.assertEqual(recovered.reconcile(states, now=1000), [
            {"type": "triggered", "cause": "w_sala"}
        ])
        self.assertEqual(recovered.phase, Phase.TRIGGERED)
        self.assertEqual(recovered.reconcile(states, now=1001), [])

    def test_vibration_uses_enrolled_contact_not_other_group_barrier(self):
        e = armed(w_sala=U, sh_sala=C)
        self.assertIn("w_sala", e.session.pending_zones)
        self.assertEqual(
            e.vibration("v_window_sala", protected_zone="w_sala", now=200)[0]["type"],
            "vibration_ignored",
        )
        self.assertEqual(e.observed("w_sala", U, C, now=201)[0]["type"], "zone_enrolled")
        self.assertEqual(
            e.vibration("v_window_sala", protected_zone="w_sala", now=202)[0]["type"],
            "vibration_prealert",
        )
        self.assertEqual(
            e.vibration("v_window_sala", protected_zone="w_sala", now=207)[0]["type"],
            "triggered",
        )

    def test_unknown_at_arming_waits_then_enrolls_closed(self):
        e = armed(studio=U)
        self.assertNotIn("studio", e.session.protected_zones)
        self.assertIn("studio", e.session.pending_zones)
        self.assertNotIn("studio", e.session.excluded_zones)
        self.assertEqual(e.observed("studio", U, C, now=200), [
            {"type": "zone_enrolled", "zone": "studio"}
        ])
        self.assertIn("studio", e.session.protected_zones)
        self.assertNotIn("studio", e.session.pending_zones)
        self.assertEqual(e.observed("studio", C, O, now=201), [
            {"type": "triggered", "cause": "studio"}
        ])

    def test_unknown_at_arming_first_open_becomes_permanently_excluded(self):
        e = armed(studio=U)
        self.assertEqual(e.observed("studio", U, O, now=200), [
            {"type": "zone_excluded", "zone": "studio", "reason": "first_known_open"}
        ])
        self.assertIn("studio", e.session.excluded_zones)
        self.assertNotIn("studio", e.session.pending_zones)
        self.assertEqual(e.observed("studio", O, C, now=201), [])
        self.assertEqual(e.observed("studio", C, O, now=202), [])
        self.assertEqual(e.phase, Phase.ARMED_AWAY)

    def test_pending_state_survives_restart_and_reconciles(self):
        e = armed(studio=U)
        snapshot = e.snapshot()
        recovered = AlarmMachine(PATHS, ZONES)
        recovered.restore(snapshot)
        self.assertIn("studio", recovered.session.pending_zones)
        states = {zone: U for zone in ZONES}
        states["studio"] = C
        self.assertEqual(recovered.reconcile(states, now=1000), [
            {"type": "zone_enrolled", "zone": "studio"}
        ])
        self.assertIn("studio", recovered.session.protected_zones)
        reloaded = AlarmMachine(PATHS, ZONES)
        reloaded.restore(recovered.snapshot())
        self.assertIn("studio", reloaded.session.protected_zones)
        self.assertEqual(
            reloaded.observed("studio", U, O, now=1001)[0]["type"],
            "triggered",
        )

    def test_old_snapshot_without_pending_zones_stays_compatible(self):
        e = armed(studio=O)
        saved = e.snapshot()
        del saved["session"]["pending_zones"]
        recovered = AlarmMachine(PATHS, ZONES)
        self.assertEqual(recovered.restore(saved)[0]["type"], "armed_restored")
        self.assertFalse(recovered.session.pending_zones)
        self.assertIn("studio", recovered.session.excluded_zones)

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

    def test_different_sensors_never_confirm_each_other(self):
        e = armed()
        for zone, contact in (
            ("v_sala", "w_sala"),
            ("v_bagno", "w_bagno"),
            ("v_porta", "entry"),
        ):
            events = e.vibration(zone, protected_zone=contact, now=200, threshold=2)
            self.assertEqual([item["type"] for item in events], ["vibration_prealert"])
        self.assertEqual(e.phase, Phase.ARMED_AWAY)
        self.assertEqual(len(e.vibration_hits), 3)

    def test_interleaving_does_not_merge_or_reset_sensor_sequences(self):
        e = armed()
        e.vibration("v_sala", protected_zone="w_sala", now=200, threshold=2)
        e.vibration("v_bagno", protected_zone="w_bagno", now=201, threshold=2)
        events = e.vibration("v_sala", protected_zone="w_sala", now=206, threshold=2)
        self.assertIn("triggered", [x["type"] for x in events])
        self.assertEqual(e.phase, Phase.TRIGGERED)

    def test_three_impulse_threshold_on_one_source(self):
        e = armed()
        first = e.vibration("v_sala", protected_zone="w_sala", now=200, threshold=3)
        self.assertEqual(first[0]["type"], "vibration_prealert")
        second = e.vibration("v_sala", protected_zone="w_sala", now=206, threshold=3)
        self.assertEqual(second[0]["type"], "vibration_progress")
        self.assertEqual(second[0]["count"], 2)
        self.assertEqual(e.phase, Phase.ARMED_AWAY)
        third = e.vibration("v_sala", protected_zone="w_sala", now=212, threshold=3)
        self.assertEqual(third[0]["type"], "triggered")
        self.assertEqual(e.phase, Phase.TRIGGERED)

    def test_short_window_expires_independently_for_each_source(self):
        e = armed()
        e.vibration("v_sala", protected_zone="w_sala", now=200, threshold=2, window=10)
        e.vibration("v_bagno", protected_zone="w_bagno", now=208, threshold=2, window=10)
        events = e.vibration("v_sala", protected_zone="w_sala", now=211, threshold=2, window=10)
        self.assertIn("vibration_prealert", [x["type"] for x in events])
        self.assertEqual(e.phase, Phase.ARMED_AWAY)
        self.assertTrue(any(z == "v_bagno" for _, z in e.vibration_hits))

    def test_debounce_does_not_count_same_pulse_twice(self):
        e = armed()
        e.vibration("v_sala", protected_zone="w_sala", now=200, threshold=2, debounce=3)
        for t in (201, 202):
            self.assertEqual(e.vibration(
                "v_sala", protected_zone="w_sala", now=t, threshold=2, debounce=3
            )[0]["type"], "vibration_filtered")
        self.assertEqual(e.phase, Phase.ARMED_AWAY)

    def test_deterrent_once_only_marker_survives_restart(self):
        e = armed()
        e.deterrent_requested = True
        saved = e.snapshot()
        rebooted = AlarmMachine(PATHS, ZONES)
        rebooted.restore(saved)
        self.assertEqual(rebooted.phase, Phase.ARMED_AWAY)
        self.assertTrue(rebooted.deterrent_requested)
        rebooted.disarm()
        self.assertFalse(rebooted.deterrent_requested)

    def test_legacy_snapshot_without_deterrent_marker_restores(self):
        e = armed()
        saved = e.snapshot()
        del saved["deterrent_requested"]
        rebooted = AlarmMachine(PATHS, ZONES)
        rebooted.restore(saved)
        self.assertEqual(rebooted.phase, Phase.ARMED_AWAY)
        self.assertFalse(rebooted.deterrent_requested)

    def test_invalid_threshold_rejected(self):
        e = armed()
        with self.assertRaises(ValueError):
            e.vibration("v_sala", protected_zone="w_sala", now=200, threshold=1)

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
