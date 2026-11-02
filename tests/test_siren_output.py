"""Physical siren domain validation regression tests."""

import unittest

from custom_components.adaptive_alarm.engine.siren_output import validate_real_siren


class SirenValidationTests(unittest.TestCase):
    def test_only_registered_siren_and_switch_ids(self):
        for entity in ("siren.ingresso", "switch.sirena_alarm_switch"):
            self.assertEqual(validate_real_siren(entity), entity)

    def test_untrusted_domains_or_strings_rejected(self):
        for bad in (
            None, "", 42, "input_boolean.test", "light.led_allarme",
            "script.sirena", "lock.porta", "siren.", "switch.",
            "switch.unsafe;service", "switch.siren.real", "switch.Sirena",
            "switch.sirena/turn_on", "mqtt.alarm",
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_real_siren(bad)


if __name__ == "__main__":
    unittest.main()
