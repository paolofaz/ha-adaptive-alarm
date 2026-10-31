"""Basic HACS package integrity checks that need no HA installation."""

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOMAIN = ROOT / "custom_components" / "adaptive_alarm"


class PackagingTests(unittest.TestCase):
    def test_hacs_structure_and_manifest(self):
        self.assertTrue((ROOT / "hacs.json").is_file())
        manifest = json.loads((DOMAIN / "manifest.json").read_text())
        self.assertEqual(manifest["domain"], "adaptive_alarm")
        self.assertTrue(manifest["config_flow"])
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")
        self.assertTrue((DOMAIN / "alarm_control_panel.py").is_file())
        self.assertTrue((DOMAIN / "engine" / "runtime.py").is_file())

    def test_translations_load(self):
        for locale in ("en", "it"):
            translation = json.loads((DOMAIN / "translations" / f"{locale}.json").read_text())
            self.assertIn("options", translation)
            self.assertIn("config", translation)

    def test_no_physical_actuation_services(self):
        """Any future siren output requires an explicit, reviewed release."""
        forbidden = (
            "services.async_call(",
            "mqtt.publish",
            "lock.unlock",
            "switch.turn_on",
            "siren.turn_on",
            'async_call("siren"',
            'async_call("switch"',
        )
        for component in DOMAIN.rglob("*.py"):
            source = component.read_text()
            for phrase in forbidden:
                with self.subTest(file=str(component), phrase=phrase):
                    self.assertNotIn(phrase, source)

    def test_siren_metadata_cannot_activate_outputs(self):
        manifest = json.loads((DOMAIN / "manifest.json").read_text())
        self.assertEqual(manifest["version"], "0.4.1")
        panel = (DOMAIN / "alarm_control_panel.py").read_text()
        controller = (DOMAIN / "controller.py").read_text()
        self.assertIn('"siren_enabled": False', panel)
        self.assertIn("self.siren_entity = self.paths.siren", controller)


if __name__ == "__main__":
    unittest.main()

