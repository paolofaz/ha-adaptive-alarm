"""Pure-Python vibration configuration validation tests."""

import unittest

from custom_components.adaptive_alarm.engine.vibration_links import (
    VibrationConfigurationError,
    validated_vibration_links,
)


class VibrationLinksTests(unittest.TestCase):
    def setUp(self):
        self.contacts = frozenset({"door", "sala", "bagno"})

    def test_empty(self):
        self.assertEqual(
            validated_vibration_links([(None, None)] * 3, self.contacts), {}
        )

    def test_complete_mapping(self):
        mapping = validated_vibration_links(
            [("v1", "door"), ("v2", "sala"), ("v3", "bagno")],
            self.contacts,
        )
        self.assertEqual(mapping, {"v1": "door", "v2": "sala", "v3": "bagno"})

    def test_missing_sensor_or_target(self):
        for link in (("v1", None), (None, "door")):
            with self.subTest(link=link), self.assertRaisesRegex(
                VibrationConfigurationError, "unpaired_vibration"
            ):
                validated_vibration_links([link], self.contacts)

    def test_target_must_be_monitored(self):
        with self.assertRaisesRegex(
            VibrationConfigurationError, "invalid_vibration_zone"
        ):
            validated_vibration_links([("v1", "not_monitored")], self.contacts)

    def test_duplicate_sensor_cannot_alias_zones(self):
        with self.assertRaisesRegex(
            VibrationConfigurationError, "duplicate_entities"
        ):
            validated_vibration_links(
                [("v1", "door"), ("v1", "sala")], self.contacts
            )

    def test_contact_cannot_be_a_vibration_source(self):
        with self.assertRaisesRegex(
            VibrationConfigurationError, "duplicate_entities"
        ):
            validated_vibration_links([("door", "sala")], self.contacts)


if __name__ == "__main__":
    unittest.main()
