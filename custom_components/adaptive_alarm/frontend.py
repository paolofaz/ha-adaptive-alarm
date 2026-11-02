"""Serve the Adaptive Alarm Lovelace card and register its resource.

The user owns YAML dashboards: we never create or modify a dashboard or YAML.
If Lovelace resources use storage, register/update the resource automatically.
For YAML-managed resources, load the module through Home Assistant's frontend
API without editing the user's configuration.yaml or dashboard files.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
CARD_PATH = "/adaptive_alarm/adaptive-alarm-card.js"
CARD_RESOURCE = f"{CARD_PATH}?v=1.0.4"
CARD_FILE = Path(__file__).parent / "www" / "adaptive-alarm-card.js"
_STATIC_READY = "_card_static_ready"
_EXTRA_MODULE_REGISTERED = "_card_extra_module_registered"


async def async_register_card(hass: Any) -> None:
    """Expose the JS module and register it without touching user dashboards."""
    from homeassistant.components.http import StaticPathConfig
    from homeassistant.components.lovelace import LOVELACE_DATA
    from homeassistant.components import frontend

    data = hass.data.setdefault(DOMAIN, {})
    if not data.get(_STATIC_READY):
        await hass.http.async_register_static_paths([
            StaticPathConfig(CARD_PATH, str(CARD_FILE), cache_headers=False),
        ])
        data[_STATIC_READY] = True

    lovelace = hass.data.get(LOVELACE_DATA)
    if lovelace is None:
        _LOGGER.warning("Lovelace is unavailable; JS card endpoint is registered")
        return
    if lovelace.resource_mode == "yaml":
        # Lovelace YAML resource collections are read-only. Instead, HA's
        # documented frontend API injects this module on page load,
        # regardless of whether the dashboard itself is in YAML mode.
        # The user's existing configuration and dashboard stay untouched.
        if not data.get(_EXTRA_MODULE_REGISTERED):
            frontend.add_extra_js_url(hass, CARD_RESOURCE)
            data[_EXTRA_MODULE_REGISTERED] = True
            _LOGGER.info(
                "Adaptive Alarm Lovelace card module automatically loaded "
                "in YAML resource mode: %s", CARD_RESOURCE
            )
        return

    resources = lovelace.resources
    await resources.async_get_info()  # Ensure collection loaded before reading.
    old = next(
        (item for item in resources.async_items()
         if str(item.get("url", "")).split("?", 1)[0] == CARD_PATH),
        None,
    )
    if old is None:
        await resources.async_create_item({
            "url": CARD_RESOURCE, "res_type": "module",
        })
    elif old.get("url") != CARD_RESOURCE or old.get("type") != "module":
        await resources.async_update_item(old["id"], {
            "url": CARD_RESOURCE, "res_type": "module",
        })


def async_unregister_card(hass: Any) -> None:
    """Remove our YAML-mode module registration on integration unload.

    The file endpoint remains registered until Home Assistant restarts;
    only the extra frontend module is removed. Never modify user resources.
    """
    from homeassistant.components import frontend

    data = hass.data.get(DOMAIN, {})
    if data.pop(_EXTRA_MODULE_REGISTERED, False):
        frontend.remove_extra_js_url(hass, CARD_RESOURCE)
