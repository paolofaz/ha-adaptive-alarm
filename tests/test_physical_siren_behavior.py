"""Behavioral siren service tests without running Home Assistant.

Compile the actual siren request method in a minimal fake HA environment.
This verifies command decisions rather than matching source-code strings.
"""
import ast
import asyncio
import logging
from pathlib import Path
from types import SimpleNamespace
import unittest

from custom_components.adaptive_alarm.engine.runtime import Phase


class FakeStates:
    def __init__(self, state="off"):
        self.value = state

    def get(self, entity):
        return None if self.value is None else SimpleNamespace(state=self.value)

    def is_state(self, entity, state):
        return self.value == state


class FakeServices:
    def __init__(self, states):
        self.states = states
        self.calls = []
        self.available = True
        self.fail = False

    def has_service(self, domain, service):
        return self.available

    async def async_call(self, domain, service, data, *, target, blocking):
        self.calls.append((domain, service, target["entity_id"]))
        if self.fail:
            raise RuntimeError("Z2M service failed")
        if service == "turn_off":
            self.states.value = "off"
        else:
            self.states.value = "on"


class FakeController:
    def __init__(self, phase=Phase.ARMED_AWAY, device="off"):
        states = FakeStates(device)
        self.hass = SimpleNamespace(
            states=states,
            services=FakeServices(states),
        )
        self.siren_entity = "siren.sirena_allarme"
        self.siren_output_enabled = True
        self.machine = SimpleNamespace(phase=phase)
        self._guard = asyncio.Lock()
        self._siren_off_retry_after = 0.0
        self._siren_off_pending = False
        self._siren_reported_failures = set()
        self.siren_last_error = None
        self.notify_events = {"zone_fault": False}
        self.events = []

    def _events(self, events):
        self.events.extend(events)


def load_siren_method():
    source = (Path(__file__).resolve().parents[1] /
              "custom_components/adaptive_alarm/controller.py").read_text()
    cls = next(n for n in ast.parse(source).body
               if isinstance(n, ast.ClassDef) and n.name == "AdaptiveAlarmController")
    fn = next(n for n in cls.body
              if isinstance(n, ast.AsyncFunctionDef)
              and n.name == "_request_physical_siren")
    module = ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[]))
    namespace = {"Phase": Phase, "time": SimpleNamespace(time=lambda: 5000),
                 "_LOGGER": logging.getLogger(__name__)}
    exec(compile(module, "<real-physical-siren-method>", "exec"), namespace)
    return namespace["_request_physical_siren"]


class SirenServiceBehaviorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.request = load_siren_method()

    async def test_no_automatic_off_on_startup_or_timer_ticks(self):
        controller = FakeController(device="on")
        await self.request(controller)
        await self.request(controller)
        self.assertEqual(controller.hass.services.calls, [])
        self.assertFalse(controller._siren_off_pending)

    async def test_disarm_explicit_off_then_clear_pending_on_confirmation(self):
        controller = FakeController(device="on")
        await self.request(controller, force=True)
        self.assertEqual(controller.hass.services.calls, [
            ("siren", "turn_off", "siren.sirena_allarme")])
        self.assertTrue(controller._siren_off_pending)
        await self.request(controller)
        self.assertFalse(controller._siren_off_pending)
        self.assertEqual(len(controller.hass.services.calls), 1)

    async def test_new_alarm_cancels_previous_off_retry(self):
        controller = FakeController(phase=Phase.TRIGGERED, device="off")
        controller._siren_off_pending = True
        await self.request(controller, activate=True, force=True)
        self.assertFalse(controller._siren_off_pending)
        self.assertEqual(controller.hass.services.calls[0][1], "turn_on")
        await self.request(controller)
        self.assertEqual(len(controller.hass.services.calls), 1)

    async def test_active_alarm_is_not_silenced_by_off_request(self):
        controller = FakeController(phase=Phase.TRIGGERED, device="on")
        await self.request(controller, force=True)
        self.assertEqual(controller.hass.services.calls, [])

    async def test_real_off_failure_remains_pending_and_reports(self):
        controller = FakeController(device="unavailable")
        await self.request(controller, force=True)
        self.assertTrue(controller._siren_off_pending)
        self.assertTrue(controller.siren_last_error)
        self.assertTrue(any(e["type"] == "siren_request_failed"
                            for e in controller.events))

    async def test_physical_siren_requires_explicit_opt_in(self):
        controller = FakeController(device="on")
        controller.siren_output_enabled = False
        await self.request(controller, force=True)
        self.assertEqual(controller.hass.services.calls, [])


if __name__ == "__main__":
    unittest.main()
