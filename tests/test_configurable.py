"""Rules remain portable and fail closed without a HA runtime."""

import itertools
import unittest

from custom_components.adaptive_alarm.engine.configurable import (
    AlternativeGroup, ProtectionRules, legacy_to_rules,
)
from custom_components.adaptive_alarm.engine.model import ZoneState
from custom_components.adaptive_alarm.engine.policy import evaluate_eligibility, new_session
from custom_components.adaptive_alarm.engine.runtime import AlarmMachine, Phase

C = ZoneState.CLOSED
O = ZoneState.OPEN
U = ZoneState.UNAVAILABLE


def rules():
    return ProtectionRules(
        mandatory=("binary_sensor.entry",),
        groups=(
            AlternativeGroup("Sala", ("binary_sensor.sala_window", "binary_sensor.sala_shutter")),
            AlternativeGroup("Bagno", ("binary_sensor.bath_window", "binary_sensor.bath_shutter")),
        ),
        optional=("binary_sensor.garage",),
        lock="lock.entry",
    )


class GenericRulesTests(unittest.TestCase):
    def test_legacy_migration_preserves_house_rules(self):
        data = {
            "entry_contact": "binary_sensor.entry", "entry_lock": "lock.entry",
            "window_living": "binary_sensor.sala_window",
            "shutter_living": "binary_sensor.sala_shutter",
            "window_bath": "binary_sensor.bath_window",
            "shutter_bath": "binary_sensor.bath_shutter",
        }
        p = legacy_to_rules(data, {"extra_contacts": ["binary_sensor.garage"]})
        self.assertEqual(p, rules())
        self.assertEqual(ProtectionRules.from_dict(p.to_dict()), p)

    def test_all_3_state_combinations(self):
        p = rules()
        ids = ["binary_sensor.entry", "binary_sensor.sala_window",
               "binary_sensor.sala_shutter", "binary_sensor.bath_window",
               "binary_sensor.bath_shutter"]
        for readings in itertools.product((C, O, U), repeat=5):
            st = dict(zip(ids, readings))
            for locked in (True, False):
                expected = bool(
                    locked and readings[0] == C
                    and (readings[1] == C or readings[2] == C)
                    and (readings[3] == C or readings[4] == C)
                )
                actual = evaluate_eligibility(p, st, lock_locked=locked)
                self.assertEqual(actual.permitted, expected)
                if expected:
                    self.assertEqual(set(actual.routes), {"Sala", "Bagno"})

    def test_no_requirements_never_arm(self):
        p = ProtectionRules()
        self.assertFalse(evaluate_eligibility(p, {}, lock_locked=True).permitted)
        e = AlarmMachine(p, frozenset())
        self.assertEqual(e.arm({}, locked=True, now=1, delay=0)[0]["type"], "arm_rejected")
        self.assertEqual(e.phase, Phase.DISARMED)

    def test_no_lock_optional(self):
        p = ProtectionRules(mandatory=("binary_sensor.entry",))
        self.assertTrue(
            evaluate_eligibility(p, {"binary_sensor.entry": C}, lock_locked=True).permitted
        )
        self.assertFalse(
            evaluate_eligibility(p, {"binary_sensor.entry": C}, lock_locked=False).permitted
        )  # locked is always injected as True when no lock is configured

    def test_general_apartment_without_shutters(self):
        p = ProtectionRules(
            mandatory=("binary_sensor.frontdoor", "binary_sensor.kitchen"),
            optional=("binary_sensor.balcony",),
        )
        st = {"binary_sensor.frontdoor": C, "binary_sensor.kitchen": C,
              "binary_sensor.balcony": O}
        self.assertTrue(evaluate_eligibility(p, st, lock_locked=True).permitted)
        e = AlarmMachine(p, p.known_contacts)
        e.arm(st, locked=True, now=1, delay=0)
        self.assertEqual(e.phase, Phase.ARMED_AWAY)
        self.assertEqual(e.session.excluded_zones, frozenset({"binary_sensor.balcony"}))
        restarted = AlarmMachine(p, p.known_contacts)
        restarted.restore(e.snapshot())
        self.assertEqual(restarted.phase, Phase.ARMED_AWAY)

    def test_group_only_config(self):
        p = ProtectionRules(groups=(AlternativeGroup("Ingresso",
            ("binary_sensor.a", "binary_sensor.b")),))
        self.assertTrue(evaluate_eligibility(p, {"binary_sensor.b": C}, lock_locked=True).permitted)
        self.assertFalse(evaluate_eligibility(p, {"binary_sensor.b": U}, lock_locked=True).permitted)

    def test_config_validation(self):
        with self.assertRaises(ValueError):
            ProtectionRules(mandatory=("binary_sensor.a",),
                            optional=("binary_sensor.a",))
        with self.assertRaises(ValueError):
            ProtectionRules(groups=(AlternativeGroup("Sala", ("binary_sensor.a",)),
                                    AlternativeGroup("sala", ("binary_sensor.b",))))
        with self.assertRaises(ValueError):
            ProtectionRules(siren="light.wrong")

    def test_siren_is_inert_metadata(self):
        p = ProtectionRules(mandatory=("binary_sensor.door",), siren="switch.test_siren")
        self.assertEqual(p.to_dict()["siren"], "switch.test_siren")
        e = AlarmMachine(p, p.known_contacts)
        e.arm({"binary_sensor.door": C}, locked=True, now=1, delay=0)
        self.assertEqual(e.phase, Phase.ARMED_AWAY)
        self.assertEqual(e.trigger("door"), [{"type": "triggered", "cause": "door"}])
