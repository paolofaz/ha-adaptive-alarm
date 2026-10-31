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
        source = (DOMAIN / "controller.py").read_text()
        self.assertNotIn("services.async_call(", source)
        self.assertNotIn("mqtt.publish", source)
        self.assertNotIn("lock.unlock", source)
        self.assertNotIn("switch.turn_on", source)
        self.assertNotIn("siren.turn_on", source)


if __name__ == "__main__":
    unittest.main()
