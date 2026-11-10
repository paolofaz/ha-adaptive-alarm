"""Behavioural anti-spam regression, including the real HA adapter method."""
import ast
import asyncio
import logging
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from custom_components.adaptive_alarm.engine.diagnostic_notices import (
    DiagnosticNoticeGate, STARTUP_GRACE_SECONDS,
)
from custom_components.adaptive_alarm.engine.runtime import Phase
from custom_components.adaptive_alarm.engine.model import ZoneState, contact_state_from_raw

CONTROLLER = (Path(__file__).resolve().parents[1] /
              "custom_components/adaptive_alarm/controller.py")


def adapter_method(name):
    tree = ast.parse(CONTROLLER.read_text())
    controller = next(
        cls for cls in tree.body if isinstance(cls, ast.ClassDef)
        and cls.name == "AdaptiveAlarmController"
    )
    method = next(
        node for node in controller.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name
    )
    namespace = {
        "time": time, "Phase": Phase, "ZoneState": ZoneState,
        "_contact_state": lambda value: contact_state_from_raw(
            getattr(value, "state", None)
        ),
    }
    exec(compile(ast.fix_missing_locations(
        ast.Module(body=[method], type_ignores=[])
    ), "<real-controller-method>", "exec"), namespace)
    return namespace[name]


class GateTests(unittest.TestCase):
    def test_ha_restart_with_all_zigbee_devices_rejoining_is_quiet(self):
        gate = DiagnosticNoticeGate(started_at=0)
        offline = {"binary_sensor.a": "offline", "binary_sensor.b": "offline"}
        self.assertEqual(gate.poll(now=0, problems=offline), {})
        self.assertEqual(gate.poll(now=70, problems=offline), {})
        self.assertEqual(gate.poll(now=90, problems={}), {})
        self.assertEqual(gate.poll(now=150, problems={}), {})
        self.assertEqual(gate.reported, set())

    def test_multiple_long_offline_sensors_get_one_message_after_grace(self):
        gate = DiagnosticNoticeGate(started_at=0)
        gate.poll(now=0, problems={"a": "offline", "b": "offline"})
        self.assertEqual(gate.poll(now=119, problems={"a": "offline", "b": "offline"}), {})
        self.assertEqual(gate.poll(now=120, problems={"a": "offline", "b": "offline"}), {})
        self.assertEqual(
            gate.poll(now=130, problems={"a": "offline", "b": "offline"}),
            {"a": "offline", "b": "offline"},
        )
        self.assertEqual(gate.poll(now=500, problems={"a": "offline", "b": "offline"}), {})

    def test_short_disconnect_during_normal_operation_is_silent(self):
        gate = DiagnosticNoticeGate(started_at=0)
        gate.poll(now=200, problems={"a": "offline"})
        self.assertEqual(gate.poll(now=259, problems={"a": "offline"}), {})
        self.assertEqual(gate.poll(now=260, problems={}), {})
        self.assertEqual(gate.poll(now=400, problems={}), {})

    def test_normal_persistent_disconnect_is_delayed_and_batched(self):
        gate = DiagnosticNoticeGate(started_at=0)
        gate.poll(now=200, problems={"a": "offline"})
        gate.poll(now=205, problems={"a": "offline", "b": "offline"})
        self.assertEqual(gate.poll(now=260, problems={"a": "offline", "b": "offline"}), {})
        self.assertEqual(gate.poll(now=265, problems={"a": "offline", "b": "offline"}), {})
        self.assertEqual(
            gate.poll(now=270, problems={"a": "offline", "b": "offline"}),
            {"a": "offline", "b": "offline"},
        )

    def test_cooldown_and_recovery_no_duplicated_notifications(self):
        gate = DiagnosticNoticeGate(started_at=0)
        gate.poll(now=200, problems={"a": "offline"})
        gate.poll(now=260, problems={"a": "offline"})
        self.assertEqual(gate.poll(now=270, problems={"a": "offline"}), {"a": "offline"})
        gate.poll(now=275, problems={"a": "offline", "b": "offline"})
        gate.poll(now=335, problems={"a": "offline", "b": "offline"})
        self.assertEqual(gate.poll(now=345, problems={"a": "offline", "b": "offline"}), {})
        self.assertEqual(
            gate.poll(now=570, problems={"a": "offline", "b": "offline"}),
            {"b": "offline"},
        )
        self.assertEqual(gate.poll(now=580, problems={"a": "offline", "b": "offline"}), {})
        gate.poll(now=600, problems={})
        gate.poll(now=700, problems={"a": "offline"})
        gate.poll(now=760, problems={"a": "offline"})
        self.assertEqual(gate.poll(now=770, problems={"a": "offline"}), {})

    def test_short_recovery_restarts_continuous_offline_timer(self):
        gate = DiagnosticNoticeGate(started_at=0)
        gate.poll(now=200, problems={"a": "offline"})
        gate.poll(now=250, problems={})
        self.assertEqual(gate.poll(now=255, problems={"a": "offline"}), {})
        self.assertEqual(gate.poll(now=310, problems={"a": "offline"}), {})
        self.assertEqual(gate.poll(now=315, problems={"a": "offline"}), {})
        self.assertEqual(gate.poll(now=325, problems={"a": "offline"}), {"a": "offline"})

    def test_disarm_clears_previous_diagnostic_episode(self):
        gate = DiagnosticNoticeGate(started_at=0)
        gate.poll(now=200, problems={"a": "offline"})
        gate.poll(now=260, problems={"a": "offline"})
        self.assertEqual(gate.poll(now=270, problems={"a": "offline"}), {"a": "offline"})
        gate.clear()
        self.assertEqual(gate.poll(now=300, problems={"a": "offline"}), {})
        self.assertEqual(gate.poll(now=360, problems={"a": "offline"}), {})
        self.assertEqual(gate.poll(now=370, problems={"a": "offline"}), {"a": "offline"})


class FakeStates:
    def __init__(self, values):
        self.values = values

    def get(self, entity):
        value = self.values.get(entity)
        return SimpleNamespace(state=value) if value is not None else None

    def is_state(self, entity, expected):
        return self.values.get(entity) == expected


class FakeController:
    def __init__(self, clock):
        self.clock = clock
        self._guard = asyncio.Lock()
        self._diagnostic_gate = DiagnosticNoticeGate(started_at=0)
        self._startup_fault_reported = False
        self._unclaimed_lights = ()
        self.notify_events = {"zone_fault": True}
        self.lock_entity = "lock.front"
        self.machine = SimpleNamespace(
            phase=Phase.ARMED_AWAY, fault="",
            session=SimpleNamespace(protected_zones=frozenset({
                "binary_sensor.door", "binary_sensor.window"
            })),
        )
        self.states = FakeStates({
            "binary_sensor.door": "unavailable",
            "binary_sensor.window": "unknown",
            "lock.front": "locked",
        })
        self.hass = SimpleNamespace(states=self.states)
        self.messages = []

    def _locked(self):
        return self.hass.states.is_state(self.lock_entity, "locked")

    def _friendly_name(self, entity):
        return entity

    async def _notify_text(self, message):
        self.messages.append(message)


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_method_silences_reconnect_and_batches_persistent_offline(self):
        method = adapter_method("_notify_persistent_diagnostics")
        original = method.__globals__["time"]
        clock = SimpleNamespace(now=0)
        method.__globals__["time"] = SimpleNamespace(monotonic=lambda: clock.now)
        try:
            c = FakeController(clock)
            await method(c)
            clock.now = 100
            c.states.values["binary_sensor.door"] = "off"
            c.states.values["binary_sensor.window"] = "off"
            await method(c)
            self.assertEqual(c.messages, [])
            clock.now = 200
            c.states.values["binary_sensor.door"] = "unavailable"
            c.states.values["binary_sensor.window"] = "unknown"
            await method(c)
            clock.now = 260
            await method(c)
            self.assertEqual(c.messages, [])
            clock.now = 270
            await method(c)
            self.assertEqual(len(c.messages), 1)
            self.assertIn("binary_sensor.door", c.messages[0])
            self.assertIn("binary_sensor.window", c.messages[0])
            clock.now = 700
            await method(c)
            self.assertEqual(len(c.messages), 1)
        finally:
            method.__globals__["time"] = original

    async def test_fault_requires_startup_grace_and_sends_once(self):
        method = adapter_method("_notify_persistent_diagnostics")
        original = method.__globals__["time"]
        clock = SimpleNamespace(now=0)
        method.__globals__["time"] = SimpleNamespace(monotonic=lambda: clock.now)
        try:
            c = FakeController(clock)
            c.machine.phase = Phase.FAULT
            c.machine.session = None
            c.machine.fault = "Invalid stored session"
            await method(c)
            clock.now = STARTUP_GRACE_SECONDS - 1
            await method(c)
            self.assertEqual(c.messages, [])
            clock.now = STARTUP_GRACE_SECONDS
            await method(c)
            self.assertEqual(len(c.messages), 1)
            self.assertIn("NON OPERATIVO", c.messages[0])
            clock.now = 700
            await method(c)
            self.assertEqual(len(c.messages), 1)
        finally:
            method.__globals__["time"] = original

    async def test_missing_lock_is_delayed_but_only_once(self):
        method = adapter_method("_notify_persistent_diagnostics")
        original = method.__globals__["time"]
        clock = SimpleNamespace(now=0)
        method.__globals__["time"] = SimpleNamespace(monotonic=lambda: clock.now)
        try:
            c = FakeController(clock)
            c.states.values["binary_sensor.door"] = "off"
            c.states.values["binary_sensor.window"] = "off"
            c.states.values["lock.front"] = "unavailable"
            await method(c)
            clock.now = 120
            await method(c)
            clock.now = 130
            await method(c)
            self.assertEqual(len(c.messages), 1)
            self.assertIn("lock.front", c.messages[0])
            clock.now = 700
            await method(c)
            self.assertEqual(len(c.messages), 1)
        finally:
            method.__globals__["time"] = original

    async def test_restart_warning_only_for_confirmed_on_light(self):
        method = adapter_method("_notify_persistent_diagnostics")
        original = method.__globals__["time"]
        clock = SimpleNamespace(now=0)
        method.__globals__["time"] = SimpleNamespace(monotonic=lambda: clock.now)
        try:
            c = FakeController(clock)
            c.notify_events["zone_fault"] = False
            c._unclaimed_lights = ("light.a", "light.b")
            c.states.values.update({"light.a": "off", "light.b": "on"})
            await method(c)
            self.assertEqual(c.messages, [])
            clock.now = 120
            await method(c)
            self.assertEqual(len(c.messages), 1)
            self.assertIn("light.b", c.messages[0])
            self.assertNotIn("light.a", c.messages[0])
            clock.now = 200
            await method(c)
            self.assertEqual(len(c.messages), 1)
        finally:
            method.__globals__["time"] = original


class WiringTests(unittest.TestCase):
    def test_diagnostic_gate_is_timer_only_and_lifecycle_is_preserved(self):
        source = CONTROLLER.read_text()
        self.assertIn("await self._notify_persistent_diagnostics()", source)
        self.assertIn("self._diagnostic_gate.clear()", source)
        self.assertIn("self._startup_fault_reported = False", source)
        self.assertIn('"type": "protected_zone_abnormal"', source)
        self.assertIn('event.get("type") == "triggered"', source)

    def test_group_duplicate_name_is_rejected(self):
        source = (CONTROLLER.parent / "config_flow.py").read_text()
        self.assertIn("and (not editing or other.name != editing.name)", source)
        self.assertIn('raise ValueError("Duplicate group name")', source)
        self.assertIn("{editing.name.casefold()} if editing else set()", source)


if __name__ == "__main__":
    unittest.main()
