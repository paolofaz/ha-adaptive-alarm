"""Check built-in, source-independent dashboard composition."""

import unittest

from custom_components.adaptive_alarm.dashboard import build_dashboard, DASHBOARD_PATH


class DashboardTests(unittest.TestCase):
    def test_native_dashboard_covers_alarm_and_all_sets(self):
        dashboard = build_dashboard(
            "alarm_control_panel.adaptive_alarm",
            "binary_sensor.adaptive_ready",
            "sensor.adaptive_health",
            "sensor.adaptive_protected",
            "sensor.adaptive_excluded",
        )
        self.assertEqual(DASHBOARD_PATH, "adaptive-alarm")
        view = dashboard["views"][0]
        self.assertEqual(view["cards"][0]["type"], "alarm-panel")
        self.assertEqual(view["cards"][0]["entity"], "alarm_control_panel.adaptive_alarm")
        text = " ".join(str(card) for card in view["cards"])
        for expected in ("protected_zones", "pending_zones", "excluded_zones",
                         "triggered_until", "protected_zone_problem_states",
                         "minimum_routes", "sensor.adaptive_health"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertNotIn("custom:", text)
        self.assertNotIn("button-card", text)


if __name__ == "__main__":
    unittest.main()
