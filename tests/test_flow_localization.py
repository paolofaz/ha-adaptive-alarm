"""Catch missing or stale translations for all seven native options pages."""

import ast
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "adaptive_alarm"
FLOW = INTEGRATION / "config_flow.py"

EXPECTED_STEPS = (
    "mandatory", "group", "remove_group", "optional",
    "vibrations", "siren", "timing",
)


class FlowLocalizationTests(unittest.TestCase):
    def test_step_constants_match_translated_labels_and_descriptions(self):
        source = ast.parse(FLOW.read_text())
        constants = [
            node for node in source.body
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "OPTIONS_MENU_STEPS"
                    for t in node.targets)
        ]
        self.assertEqual(len(constants), 1)
        menu = tuple(ast.literal_eval(constants[0].value))
        self.assertEqual(menu, EXPECTED_STEPS)

        for language in ("it", "en"):
            with self.subTest(language=language):
                strings = json.loads(
                    (INTEGRATION / "translations" / f"{language}.json").read_text()
                )
                self.assertTrue(strings["config"]["step"]["user"]["data"]["name"])
                self.assertIn("name", strings["config"]["step"]["user"]["data"])
                options = strings["options"]["step"]
                self.assertTrue(options["init"]["title"])
                self.assertTrue(options["init"]["description"])
                self.assertEqual(
                    set(options["init"]["menu_options"]), set(menu)
                )
                self.assertEqual(
                    set(options["init"]["menu_option_descriptions"]), set(menu)
                )
                for step in menu:
                    self.assertTrue(options["init"]["menu_options"][step].strip())
                    self.assertTrue(options[step]["title"].strip())
                    self.assertIn("data", options[step])

    def test_no_outdated_five_sensor_setup_description(self):
        for language in ("it", "en"):
            text = (INTEGRATION / "translations" / f"{language}.json").read_text()
            self.assertNotIn("cinque contatti", text.lower())
            self.assertNotIn("five contacts", text.lower())
            self.assertNotIn("zone monitorate", text.lower())
            self.assertNotIn("monitored zones", text.lower())

    def test_no_unreleased_home_assistant_translation_api_import(self):
        # This helper exists on Home Assistant dev, but not in the
        # 2026.9 / 2026.10 stable releases. Direct import caused
        # "Invalid handler specified" when loading config_flow.py.
        for source in (FLOW, INTEGRATION / "__init__.py"):
            with self.subTest(source=source.name):
                self.assertNotIn("async_invalidate_translations", source.read_text())
        self.assertIn("menu_options=list(OPTIONS_MENU_STEPS)", FLOW.read_text())


if __name__ == "__main__":
    unittest.main()
