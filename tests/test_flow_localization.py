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
    "vibrations", "deterrent", "notifications", "notification_test", "siren", "timing",
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
                    self.assertTrue(
                        "data" in options[step] or "menu_options" in options[step]
                        or step == "notification_test"
                    )
                self.assertEqual(
                    set(options["vibrations"]["menu_options"]),
                    {"vibration_add", "vibration_edit", "vibration_remove"},
                )
                for step in (
                    "vibration_add", "vibration_edit",
                    "vibration_edit_contact", "vibration_remove",
                ):
                    self.assertIn("data", options[step])
                    self.assertTrue(options[step]["title"])
                self.assertIn("data", options["deterrent"])

    def test_human_readable_recovery_policy_translated(self):
        flow = FLOW.read_text()
        self.assertIn('translation_key="recovery_policy"', flow)
        self.assertIn("description_placeholders={", flow)
        self.assertIn('"groups_summary": group_summary(', flow)
        self.assertIn("NumberSelectorMode.BOX", flow)
        for language in ("it", "en"):
            tr = json.loads(
                (INTEGRATION / "translations" / f"{language}.json").read_text()
            )
            self.assertEqual(
                set(tr["selector"]["recovery_policy"]["options"]),
                {"notify", "trigger"},
            )
            timing = tr["options"]["step"]["timing"]
            self.assertEqual(set(timing["data_description"]), {
                "arming_delay", "vibration_threshold", "vibration_debounce",
                "vibration_window", "recovery_policy",
            })
            mandatory = tr["options"]["step"]["mandatory"]
            self.assertIn("{groups_summary}", mandatory["description"])

    def test_no_outdated_five_sensor_setup_description(self):
        for language in ("it", "en"):
            translation = json.loads(
                (INTEGRATION / "translations" / f"{language}.json").read_text()
            )
            # A legitimate vibration form can refer to monitored zones;
            # prohibit outdated setup text only in the initial setup step.
            intro = translation["config"]["step"]["user"]["description"].lower()
            self.assertNotIn("cinque contatti", intro)
            self.assertNotIn("five contacts", intro)
            self.assertNotIn("zone monitorate", intro)
            self.assertNotIn("monitored zones", intro)

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
