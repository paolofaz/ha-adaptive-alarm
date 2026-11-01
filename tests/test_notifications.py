"""Notification dispatch must never be able to address arbitrary HA services."""

import asyncio
import unittest

from custom_components.adaptive_alarm.notifications import (
    async_send_notification, validate_targets,
)


class FakeServices:
    def __init__(self):
        self.available = {"send_message", "mobile_app_phone", "telegram_legacy"}
        self.calls = []

    def has_service(self, domain, service):
        return domain == "notify" and service in self.available

    async def async_call(self, domain, service, data, **kwargs):
        self.calls.append((domain, service, data, kwargs))
        if service == "mobile_app_phone":
            raise RuntimeError("Simulated phone outage")


class FakeHass:
    def __init__(self):
        self.services = FakeServices()


class NotificationTests(unittest.TestCase):
    def test_validation_only_notify_domain(self):
        for name in ("siren.turn_on", "light.turn_off", "script.test", "notify", "send_message", "../mqtt"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_targets([], [name])
        for entity in ("light.lamp", "siren.siren", "notify.a.b", "notify.", "notify/my_phone"):
            with self.subTest(entity=entity), self.assertRaises(ValueError):
                validate_targets([entity], [])

    def test_multiple_targets_deduplicated(self):
        entities, services = validate_targets(
            ["notify.telegram_chat", "notify.telegram_chat"],
            ["mobile_app_phone", "mobile_app_phone"],
        )
        self.assertEqual(entities, ("notify.telegram_chat",))
        self.assertEqual(services, ("mobile_app_phone",))

    def test_failures_are_isolated(self):
        hass = FakeHass()
        r = asyncio.run(async_send_notification(
            hass, entities=["notify.telegram_chat", "notify.missing"],
            services=["mobile_app_phone", "telegram_legacy", "missing"],
            message="Test", title="Adaptive Alarm",
        ))
        self.assertEqual(r["requested"], ["notify.telegram_chat", "notify.telegram_legacy"])
        self.assertEqual(set(r["failed"]), {"notify.missing", "notify.mobile_app_phone", "notify.missing"})
        self.assertTrue(all(call[0] == "notify" for call in hass.services.calls))
        self.assertEqual(hass.services.calls[0][3]["target"]["entity_id"], "notify.telegram_chat")


if __name__ == "__main__":
    unittest.main()
