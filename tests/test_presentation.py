"""Friendly display names never modify alarm identity or severity."""

import unittest
from types import SimpleNamespace

from custom_components.adaptive_alarm.engine.presentation import (
    group_summary, prealert_text, trigger_text, fault_text,
)


NAMES = {
    "binary_sensor.window_living": "Finestra Sala",
    "binary_sensor.shutter_living": "Persiana Sala",
    "binary_sensor.window_bath": "Finestra Bagno",
    "binary_sensor.vib_living": "Vibrazione Sala",
}
name_of = lambda entity: NAMES.get(entity, entity)


class PresentationTests(unittest.TestCase):
    def test_all_mandatory_groups_visible_with_friendly_names(self):
        groups = [
            SimpleNamespace(name="Sala", contacts=(
                "binary_sensor.window_living", "binary_sensor.shutter_living")),
            SimpleNamespace(name="Bagno", contacts=(
                "binary_sensor.window_bath",)),
        ]
        self.assertEqual(
            group_summary(groups, name_of),
            "Sala: Finestra Sala oppure Persiana Sala; Bagno: Finestra Bagno",
        )
        self.assertEqual(
            group_summary(groups, name_of, alternative_word="or"),
            "Sala: Finestra Sala or Persiana Sala; Bagno: Finestra Bagno",
        )
        self.assertEqual(group_summary([], name_of), "—")

    def test_prealert_identifies_window_and_sensor(self):
        message = prealert_text(
            "binary_sensor.vib_living", "binary_sensor.window_living", name_of,
        )
        self.assertIn("Finestra Sala", message)
        self.assertIn("Vibrazione Sala", message)
        self.assertNotIn("binary_sensor.", message)
        self.assertIn("PREALLARME", message)

    def test_vibration_trigger_identifies_linked_physical_contact(self):
        message = trigger_text(
            "vibration:binary_sensor.vib_living",
            {"binary_sensor.vib_living": "binary_sensor.window_living"},
            name_of,
        )
        self.assertIn("Finestra Sala", message)
        self.assertIn("Vibrazione Sala", message)
        self.assertIn("ALLARME SIMULATO", message)
        self.assertNotIn("binary_sensor.", message)

    def test_contact_trigger_identifies_open_contact(self):
        message = trigger_text(
            "binary_sensor.window_bath", {}, name_of,
        )
        self.assertIn("apertura del contatto Finestra Bagno", message)
        self.assertNotIn("binary_sensor.", message)

    def test_manual_trigger_is_distinguished(self):
        self.assertIn(
            "attivazione manuale",
            trigger_text("manual_test", {}, name_of),
        )

    def test_sensor_offline_or_open_diagnostic_is_distinguished(self):
        for state, expected in (
            ("unavailable", "sensore non disponibile"),
            ("open", "sensore tornato online già aperto"),
        ):
            msg = fault_text("binary_sensor.window_living", state, name_of)
            self.assertIn(expected, msg)
            self.assertIn("Finestra Sala", msg)
            self.assertIn("Nessun allarme", msg)
            self.assertNotIn("binary_sensor.", msg)

    def test_unknown_entities_fall_back_to_original_id(self):
        self.assertIn(
            "binary_sensor.unregistered",
            trigger_text("binary_sensor.unregistered", {}, name_of),
        )


if __name__ == "__main__":
    unittest.main()
