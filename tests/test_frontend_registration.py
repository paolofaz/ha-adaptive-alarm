"""Behavioral registration tests for both Lovelace resource modes.

No full Home Assistant installation needed: mock only the documented
frontend and HTTP APIs and assert no user YAML is edited.
"""

from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch
import sys

from custom_components.adaptive_alarm.frontend import (
    CARD_PATH,
    CARD_RESOURCE,
    async_register_card,
    async_unregister_card,
)


@contextmanager
def mock_homeassistant_frontend():
    root = ModuleType("homeassistant")
    components = ModuleType("homeassistant.components")
    frontend = ModuleType("homeassistant.components.frontend")
    frontend.add_extra_js_url = Mock()
    frontend.remove_extra_js_url = Mock()
    http = ModuleType("homeassistant.components.http")
    http.StaticPathConfig = lambda *a, **kw: (a, kw)
    lovelace = ModuleType("homeassistant.components.lovelace")
    lovelace.LOVELACE_DATA = "lovelace"
    root.components = components
    components.frontend = frontend
    components.http = http
    components.lovelace = lovelace
    with patch.dict(sys.modules, {
        "homeassistant": root,
        "homeassistant.components": components,
        "homeassistant.components.frontend": frontend,
        "homeassistant.components.http": http,
        "homeassistant.components.lovelace": lovelace,
    }):
        yield frontend


class RegistrationTests(IsolatedAsyncioTestCase):
    def make_hass(self, resources=None, mode="yaml"):
        return SimpleNamespace(
            data={"lovelace": SimpleNamespace(
                resource_mode=mode, resources=resources,
            )},
            http=SimpleNamespace(async_register_static_paths=AsyncMock()),
        )

    async def test_yaml_resources_register_extra_module_once_without_writes(self):
        hass = self.make_hass(mode="yaml")
        with mock_homeassistant_frontend() as frontend:
            await async_register_card(hass)
            await async_register_card(hass)
            frontend.add_extra_js_url.assert_called_once_with(hass, CARD_RESOURCE)
            hass.http.async_register_static_paths.assert_awaited_once()
            paths = hass.http.async_register_static_paths.await_args.args[0]
            self.assertEqual(paths[0][0][0], CARD_PATH)
            async_unregister_card(hass)
            frontend.remove_extra_js_url.assert_called_once_with(hass, CARD_RESOURCE)
            async_unregister_card(hass)
            frontend.remove_extra_js_url.assert_called_once()

    async def test_storage_resources_keep_existing_automatic_registration(self):
        resources = SimpleNamespace(
            async_get_info=AsyncMock(return_value={"resources": 0}),
            async_items=Mock(return_value=[]),
            async_create_item=AsyncMock(),
            async_update_item=AsyncMock(),
        )
        hass = self.make_hass(mode="storage", resources=resources)
        with mock_homeassistant_frontend() as frontend:
            await async_register_card(hass)
            resources.async_get_info.assert_awaited_once()
            resources.async_create_item.assert_awaited_once_with(
                {"url": CARD_RESOURCE, "res_type": "module"}
            )
            frontend.add_extra_js_url.assert_not_called()
            async_unregister_card(hass)
            frontend.remove_extra_js_url.assert_not_called()

    async def test_storage_resources_upgrade_existing_entry_in_place(self):
        resources = SimpleNamespace(
            async_get_info=AsyncMock(return_value={"resources": 1}),
            async_items=Mock(return_value=[{
                "id": "owned-record",
                "url": CARD_PATH + "?v=1.0.3",
                "type": "module",
            }]),
            async_create_item=AsyncMock(),
            async_update_item=AsyncMock(),
        )
        hass = self.make_hass(mode="storage", resources=resources)
        with mock_homeassistant_frontend():
            await async_register_card(hass)
            resources.async_create_item.assert_not_awaited()
            resources.async_update_item.assert_awaited_once_with(
                "owned-record",
                {"url": CARD_RESOURCE, "res_type": "module"},
            )


if __name__ == "__main__":
    import unittest
    unittest.main()
