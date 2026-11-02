"""Regression checks for the single-card Lovelace integration."""

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / "custom_components" / "adaptive_alarm"


class FrontendTests(unittest.TestCase):
    def test_card_is_bundled_with_storage_or_yaml_resource_paths(self):
        frontend = (BASE / "frontend.py").read_text()
        card = (BASE / "www" / "adaptive-alarm-card.js").read_text()
        integration = (BASE / "__init__.py").read_text()
        self.assertIn('CARD_PATH = "/adaptive-alarm/adaptive-alarm-card.js"', frontend)
        self.assertIn('resource_mode == "yaml"', frontend)
        self.assertIn("async_register_static_paths", frontend)
        self.assertIn('"res_type": "module"', frontend)
        self.assertIn("async_register_card(hass)", integration)
        self.assertNotIn("async_ensure_dashboard", integration)
        self.assertIn('customElements.define("adaptive-alarm-card"', card)
        self.assertIn('protected_zones', card)
        self.assertIn('pending_zones', card)
        self.assertIn('excluded_zones', card)
        self.assertIn('siren_entity', card)
        self.assertIn('textContent', card)
        self.assertNotIn('callService(', card)

    def test_no_virtual_siren_remains(self):
        self.assertFalse((BASE / "engine" / "fake_siren.py").exists())
        for path in ("controller.py", "config_flow.py", "alarm_control_panel.py",
                     "sensor.py", "const.py"):
            source = (BASE / path).read_text()
            self.assertNotIn("CONF_FAKE_SIREN", source, path)
            self.assertNotIn("fake_siren_enabled", source, path)
            self.assertNotIn("fake_siren_helper", source, path)

    def test_readme_describes_single_yaml_card(self):
        readme = (ROOT / "README.md").read_text()
        self.assertIn("custom:adaptive-alarm-card", readme)
        self.assertIn("resource_mode: yaml", readme)
        self.assertNotIn("automatically creates the", readme)


if __name__ == "__main__":
    unittest.main()
