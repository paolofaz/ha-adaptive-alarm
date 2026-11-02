"""Tests for the explanatory Health attributes (no Home Assistant imports)."""

import unittest

from custom_components.adaptive_alarm.engine.health import protected_state_issues


class HealthDiagnosticTests(unittest.TestCase):
    def test_explains_unknown_unavailable_missing_and_open(self):
        self.assertEqual(
            protected_state_issues(
                {"a", "b", "c", "d", "e", "f"},
                {"a": "off", "b": "unknown", "c": "unavailable",
                 "d": None, "e": "on", "f": "invalid"},
            ),
            {
                "b": "unknown", "c": "unavailable", "d": "missing",
                "e": "open", "f": "unexpected",
            },
        )

    def test_pending_or_excluded_are_not_considered_unhealthy(self):
        self.assertEqual(
            protected_state_issues({"protected"}, {
                "protected": "off", "pending": "unknown", "excluded": "on",
            }),
            {},
        )


if __name__ == "__main__":
    unittest.main()
