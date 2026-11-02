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
            "mqtt.publish",
            "lock.unlock",
        )
        controller = (DOMAIN / "controller.py").read_text()
        self.assertEqual(controller.count("services.async_call("), 3)
        self.assertIn('"light", "turn_on"', controller)
        self.assertIn('blocking=True', controller)
        self.assertIn('self.siren_output_enabled', controller)
        self.assertIn('if activate and phase != Phase.TRIGGERED', controller)
        self.assertIn('not activate and not force', controller)
        self.assertNotIn('input_boolean', controller)
        self.assertNotIn('fake_siren', controller)
        self.assertIn('event.get("type") == "trigger_timeout_rearmed"', controller)
        self.assertIn('if not self.siren_output_enabled', controller)
        for component in DOMAIN.rglob("*.py"):
            source = component.read_text()
            for phrase in forbidden:
                with self.subTest(file=str(component), phrase=phrase):
                    self.assertNotIn(phrase, source)

    def test_deterrent_only_turns_on_lights_after_explicit_opt_in(self):
        source = (DOMAIN / "controller.py").read_text()
        flow = (DOMAIN / "config_flow.py").read_text()
        const = (DOMAIN / "const.py").read_text()
        self.assertIn('"light", "turn_on"', source)
        self.assertIn('"light", "turn_off"', source)
        self.assertIn("may_turn_off(", source)
        self.assertIn("await asyncio.gather(", source)
        self.assertIn("self.deterrent_auto_off", source)
        self.assertIn("_process_light_state_event", source)
        self.assertIn("confirm_transition(", source)
        self.assertIn("self._light_pending[light] = pending", source)
        self.assertIn("deterrent_light_tracking_unconfirmed", source)
        self.assertIn("self.deterrent_enabled", source)
        self.assertIn("session.protected_zones", source)
        self.assertIn("CONF_DETERRENT_ENABLED", flow)
        self.assertIn("CONF_DETERRENT_LIGHTS", flow)
        self.assertIn("DEFAULT_DETERRENT_ENABLED = False", const)
        self.assertIn('self.siren_output_enabled', source)

    def test_physical_siren_output_opt_in(self):
        manifest = json.loads((DOMAIN / "manifest.json").read_text())
        self.assertEqual(manifest["version"], "1.0.1")
        panel = (DOMAIN / "alarm_control_panel.py").read_text()
        controller = (DOMAIN / "controller.py").read_text()
        self.assertIn('"siren_enabled": self.controller.siren_output_enabled', panel)
        self.assertIn("self.siren_entity = self.paths.siren", controller)
        sensor = (DOMAIN / "sensor.py").read_text()
        self.assertIn('"pending_zones"', sensor)
        self.assertIn('"minimum_protection_frozen"', sensor)
        self.assertIn('"protected_zone_problem_states"', sensor)
        self.assertIn('"protected_zones_unreadable"', sensor)


if __name__ == "__main__":
    unittest.main()

