"""Regression checks for physical siren commands on genuine events.

The adapter imports Home Assistant; CI therefore checks its lifecycle AST.
No arbitrary OFF on HA start/unload, and actual disarm/timeout OFF preserved.
"""
import ast
from pathlib import Path
import unittest

SRC = (Path(__file__).resolve().parents[1]
       / "custom_components/adaptive_alarm/controller.py")


class SirenLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ast_tree=ast.parse(SRC.read_text())
        cls.controller=next(n for n in ast_tree.body
                            if isinstance(n,ast.ClassDef)
                            and n.name=="AdaptiveAlarmController")

    def method(self,name):
        return ast.unparse(next(n for n in self.controller.body
                                if isinstance(n,ast.AsyncFunctionDef)
                                and n.name==name))

    def test_no_siren_command_for_startup_alone(self):
        src=self.method("async_start")
        self.assertNotIn("await self._sync_outputs(force=True)",src)
        self.assertIn("self.machine.reconcile",src)
        # Tick can still process a genuinely expired trigger deadline.
        self.assertIn("await self.async_tick()",src)

    def test_unload_never_silences_active_alarm(self):
        src=self.method("async_stop")
        self.assertNotIn("_request_physical_siren",src)
        self.assertNotIn("_sync_outputs",src)

    def test_off_only_when_request_pending_or_forced(self):
        src=self.method("_request_physical_siren")
        self.assertIn("self._siren_off_pending = True",src)
        self.assertIn("if not self._siren_off_pending:",src)
        self.assertIn("self._siren_off_pending = False",src)
        self.assertIn("self._siren_off_retry_after",src)
        self.assertNotIn("shutdown",src)

    def test_disarm_and_actual_timeout_request_off(self):
        self.assertIn("await self._sync_outputs(force=True)",self.method("async_disarm"))
        tick=self.method("async_tick")
        self.assertIn("trigger_timeout_rearmed",tick)
        self.assertIn("force=any(",tick)


if __name__ == "__main__":
    unittest.main()
