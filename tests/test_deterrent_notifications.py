"""Behavioural regression for automatic deterrent-light notifications.

Compile the real controller method without importing Home Assistant, matching
the pattern used for real siren service tests in this repository.
"""
import ast
import asyncio
import logging
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from custom_components.adaptive_alarm.engine.light_expiry import (
    LightLease, PendingLight, may_turn_off,
)
from custom_components.adaptive_alarm.engine.runtime import Phase

UPDATED = datetime(2026, 11, 1, tzinfo=timezone.utc)


class FakeServices:
    def __init__(self, fail=()):
        self.calls = []
        self.fail = set(fail)

    async def async_call(self, domain, service, data, *, blocking):
        entity = data["entity_id"]
        self.calls.append((domain, service, entity))
        if entity in self.fail:
            raise RuntimeError("Simulated device error")


class FakeStore:
    def __init__(self):
        self.saved = []

    async def async_save(self, value):
        self.saved.append(value)


class FakeController:
    def __init__(self, lights, *, fail=()):
        self._guard = asyncio.Lock()
        self._light_pending = {}
        self._light_leases = {
            light: LightLease(light, UPDATED.isoformat(), 0, "episode-1")
            for light in lights
        }
        self.machine = SimpleNamespace(
            phase=Phase.ARMED_AWAY,
            deterrent_hold_after_trigger=False,
            session=SimpleNamespace(identifier="episode-1"),
        )
        self.deterrent_off_delay = 60
        self._light_store = FakeStore()
        self.states = {
            light: SimpleNamespace(state="on", last_updated=UPDATED)
            for light in lights
        }
        self.hass = SimpleNamespace(
            states=SimpleNamespace(get=lambda light: self.states.get(light)),
            services=FakeServices(fail),
        )
        self.events = []
        self.messages = []

    def _events(self, events):
        self.events.extend(events)

    async def _notify_text(self, message):
        self.messages.append(message)


def load_expiry_method():
    source = (Path(__file__).resolve().parents[1] /
              "custom_components/adaptive_alarm/controller.py").read_text()
    controller = next(
        node for node in ast.parse(source).body
        if isinstance(node, ast.ClassDef) and node.name == "AdaptiveAlarmController"
    )
    method = next(
        node for node in controller.body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == "_expire_deterrent_lights"
    )
    module = ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[]))
    namespace = {
        "Phase": Phase,
        "time": time,
        "may_turn_off": may_turn_off,
        "_LOGGER": logging.getLogger(__name__),
    }
    exec(compile(module, "<real-light-expiry-method>", "exec"), namespace)
    return namespace["_expire_deterrent_lights"]


class DeterrentNotificationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.expire = load_expiry_method()

    async def test_successfully_switching_off_multiple_lights_is_silent(self):
        lights = ["light.portico", "light.ingresso", "light.giardino"]
        controller = FakeController(lights)
        await self.expire(controller)
        self.assertCountEqual(
            controller.hass.services.calls,
            [("light", "turn_off", light) for light in lights],
        )
        self.assertEqual(controller.messages, [])
        self.assertCountEqual(
            controller.events,
            [{"type": "deterrent_light_off_requested", "light": light}
             for light in lights],
        )
        self.assertEqual(controller._light_leases, {})
        self.assertEqual(controller._light_store.saved[-1], {"leases": []})

    async def test_failed_off_warns_but_successful_off_does_not(self):
        controller = FakeController(
            ["light.portico", "light.ingresso"], fail=["light.ingresso"],
        )
        await self.expire(controller)
        self.assertEqual(len(controller.messages), 1)
        self.assertIn("FALLITA", controller.messages[0])
        self.assertIn("light.ingresso", controller.messages[0])
        self.assertIn(
            {"type": "deterrent_light_off_requested", "light": "light.portico"},
            controller.events,
        )
        self.assertIn(
            {"type": "deterrent_light_off_failed", "light": "light.ingresso"},
            controller.events,
        )

    async def test_modified_light_skips_off_and_warns(self):
        controller = FakeController(["light.portico"])
        controller.states["light.portico"].last_updated = UPDATED + timedelta(seconds=5)
        await self.expire(controller)
        self.assertEqual(controller.hass.services.calls, [])
        self.assertEqual(len(controller.messages), 1)
        self.assertIn("NON eseguito", controller.messages[0])
        self.assertEqual(controller.events[0]["type"], "deterrent_light_off_skipped")

    async def test_unconfirmed_activation_keeps_critical_warning(self):
        controller = FakeController([])
        controller._light_pending["light.portico"] = PendingLight(
            entity_id="light.portico",
            baseline_updated=UPDATED.isoformat(),
            ack_deadline=0,
            off_deadline=0,
            episode="episode-1",
        )
        await self.expire(controller)
        self.assertEqual(len(controller.messages), 1)
        self.assertIn("nessuna conferma", controller.messages[0])
        self.assertEqual(
            controller.events[0]["type"], "deterrent_light_tracking_unconfirmed",
        )

    async def test_does_not_switch_off_while_alarm_holds_lights(self):
        controller = FakeController(["light.portico"])
        controller.machine.deterrent_hold_after_trigger = True
        await self.expire(controller)
        self.assertEqual(controller.hass.services.calls, [])
        self.assertEqual(controller.messages, [])


if __name__ == "__main__":
    unittest.main()
