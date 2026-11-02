"""Only a deliberately selected input_boolean can act as a virtual siren."""

import unittest

from custom_components.adaptive_alarm.engine.fake_siren import (
    fake_siren_target, validate_fake_siren_helper,
)


class FakeSirenSafetyTests(unittest.TestCase):
    def test_accepts_only_input_boolean(self):
        self.assertEqual(
            validate_fake_siren_helper("input_boolean.sirena_fittizia"),
            "input_boolean.sirena_fittizia",
        )
        for unsafe in (
            "switch.sirena", "siren.real", "light.sirena", "script.alarm",
            "input_boolean.", "input_boolean.a.b", "input_boolean.a/b",
            "input_boolean.aa;switch.turn_on", "", None, 42, [],
        ):
            with self.subTest(unsafe=unsafe), self.assertRaises(ValueError):
                validate_fake_siren_helper(unsafe)

    def test_only_triggered_means_on(self):
        self.assertEqual(fake_siren_target("triggered"), "on")
        for phase in ("disarmed", "arming", "armed_away", "fault", "unknown"):
            with self.subTest(phase=phase):
                self.assertEqual(fake_siren_target(phase), "off")


if __name__ == "__main__":
    unittest.main()
