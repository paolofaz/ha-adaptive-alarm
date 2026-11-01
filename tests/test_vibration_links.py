"""Pure-Python vibration configuration validation tests."""

import unittest

from custom_components.adaptive_alarm.const import (
    CONF_ENTRY_CONTACT,
    CONF_VIBRATION_ENTRY,
    CONF_VIBRATION_WINDOW_BATH,
    CONF_VIBRATION_WINDOW_LIVING,
    CONF_WINDOW_BATH,
    CONF_WINDOW_LIVING,
    CONF_SHUTTER_BATH,
    CONF_SHUTTER_LIVING,
    VIBRATION_ASSIGNMENTS,
)
from custom_components.adaptive_alarm.engine.vibration_links import (
    VibrationConfigurationError,
    validated_vibration_links,
)


class VibrationLinksTests(unittest.TestCase):
    def setUp(self):
        self.contacts = frozenset({"door", "sala", "bagno"})

    def test_fixed_assignments_never_reference_shutters(self):
        self.assertEqual(
            VIBRATION_ASSIGNMENTS,
            (
                (CONF_VIBRATION_ENTRY, CONF_ENTRY_CONTACT),
                (CONF_VIBRATION_WINDOW_LIVING, CONF_WINDOW_LIVING),
                (CONF_VIBRATION_WINDOW_BATH, CONF_WINDOW_BATH),
            ),
        )
        self.assertFalse(
            {target for _, target in VIBRATION_ASSIGNMENTS}
            & {CONF_SHUTTER_LIVING, CONF_SHUTTER_BATH}
        )

    def test_n_sources_unlimited(self):
        contacts = {f"binary_sensor.window_{n}" for n in range(12)}
        links = [(f"binary_sensor.vibration_{n}", f"binary_sensor.window_{n}")
                 for n in range(12)]
        self.assertEqual(len(validated_vibration_links(links, contacts)), 12)

    def test_empty(self):
        self.assertEqual(
            validated_vibration_links([(None, None)] * 3, self.contacts), {}
        )

    def test_different_sensors_can_share_no_shutters(self):
        self.assertEqual(
            validated_vibration_links([("v_door", "door"), ("v_sala", "sala")],
                                      self.contacts),
            {"v_door": "door", "v_sala": "sala"},
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
