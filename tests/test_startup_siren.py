"""Final regression coverage: a fresh restart-detected intrusion can sound.

The Home Assistant adapter is not importable into the pure-engine CI runner.
Test the actual engine event distinction and statically enforce the bridge
between startup reconciliation and siren output on the HA adapter.
"""

from __future__ import annotations

import ast
import pathlib
import unittest

from custom_components.adaptive_alarm.engine.runtime import AlarmMachine, Phase
from tests.test_runtime import PATHS, ZONES, C, O, armed, snapshot


CONTROLLER = pathlib.Path(__file__).resolve().parents[1] / (
    "custom_components/adaptive_alarm/controller.py"
)


class SirenStartupRegressionTests(unittest.TestCase):
    def test_restart_armed_open_raises_fresh_trigger_only_once(self):
        original = armed()
        restored = AlarmMachine(PATHS, ZONES)
        self.assertEqual(restored.restore(original.snapshot())[0]["type"], "armed_restored")
        self.assertEqual(restored.phase, Phase.ARMED_AWAY)
        trigger = restored.reconcile(snapshot(entry=O), now=3000)
        self.assertEqual(trigger, [{"type": "triggered", "cause": "entry"}])
        self.assertEqual(restored.reconcile(snapshot(entry=O), now=3001), [])

    def test_restart_already_triggered_does_not_emit_a_new_trigger(self):
        original = armed()
        original.trigger("entry", now=2000)
        restored = AlarmMachine(PATHS, ZONES)
        self.assertEqual(
            restored.restore(original.snapshot()),
            [{"type": "triggered_restored"}],
        )
        self.assertEqual(restored.reconcile(snapshot(entry=O), now=2001), [])
        self.assertEqual(restored.phase, Phase.TRIGGERED)

    def test_controller_startup_sounds_only_fresh_trigger_before_push(self):
        tree = ast.parse(CONTROLLER.read_text())
        cls = next(node for node in tree.body
                   if isinstance(node, ast.ClassDef)
                   and node.name == "AdaptiveAlarmController")
        start = next(node for node in cls.body
                     if isinstance(node, ast.AsyncFunctionDef)
                     and node.name == "async_start")
        armed_branch = next(node for node in start.body
                            if isinstance(node, ast.If)
                            and "self.machine.phase == Phase.ARMED_AWAY"
                            in ast.unparse(node.test))
        src = "\n".join(ast.unparse(item) for item in armed_branch.body)
        self.assertIn('event.get("type") == "triggered"', src)
        self.assertIn("self._sync_outputs(triggered=True, force=True)", src)
        self.assertIn("self._notify_events(restored_events)", src)
        self.assertLess(
            src.index("self._sync_outputs(triggered=True, force=True)"),
            src.index("self._notify_events(restored_events)"),
        )
        triggered_branch = next(node for node in start.body
                                if isinstance(node, ast.If)
                                and "self.machine.phase == Phase.TRIGGERED"
                                in ast.unparse(node.test))
        # The restored TRIGGERED path may process expiry, but never sends
        # a fresh physical ON merely because that phase was restored.
        self.assertNotIn("triggered=True", ast.unparse(triggered_branch))


if __name__ == "__main__":
    unittest.main()
