"""Serve the Adaptive Alarm Lovelace card and register its resource.

The user owns YAML dashboards: we never create or modify a dashboard or YAML.
Prefer native Lovelace resource loading in storage mode; use the frontend
module fallback only for YAML resources or actual storage registration error.
Never edit user dashboards, cards or YAML files.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
CARD_PATH = "/adaptive_alarm/adaptive-alarm-card.js"
CARD_RESOURCE = f"{CARD_PATH}?v=1.0.7"
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

    # Native Lovelace resource imports occur after the frontend's scoped
    # customElements registry has been initialized. Do not also inject an
    # early extra_module_url in storage mode; both paths with the same URL
    # share module evaluation, which can lose an early card definition.
    def add_fallback() -> None:
        if not data.get(_EXTRA_MODULE_REGISTERED):
            frontend.add_extra_js_url(hass, CARD_RESOURCE)
            data[_EXTRA_MODULE_REGISTERED] = True
            _LOGGER.info("Adaptive Alarm frontend fallback: %s", CARD_RESOURCE)

    lovelace = hass.data.get(LOVELACE_DATA)
    if lovelace is None:
        _LOGGER.warning("Lovelace data unavailable; using frontend fallback")
        add_fallback()
        return

    if lovelace.resource_mode == "yaml":
        add_fallback()
        return

    try:
        resources = lovelace.resources
        await resources.async_get_info()
        old = next(
            (item for item in resources.async_items()
             if str(item.get("url", "")).split("?", 1)[0] == CARD_PATH),
            None,
        )
        if old is None:
            await resources.async_create_item({
                "url": CARD_RESOURCE, "res_type": "module",
            })
            _LOGGER.info("Adaptive Alarm Lovelace resource created: %s", CARD_RESOURCE)
        elif old.get("url") != CARD_RESOURCE or old.get("type") != "module":
            await resources.async_update_item(old["id"], {
                "url": CARD_RESOURCE, "res_type": "module",
            })
            _LOGGER.info("Adaptive Alarm Lovelace resource updated: %s", CARD_RESOURCE)
        else:
            _LOGGER.info("Adaptive Alarm Lovelace resource confirmed: %s", CARD_RESOURCE)
    except Exception:
        _LOGGER.exception(
            "Adaptive Alarm Lovelace storage resource failed; "
            "falling back to frontend extra-module URL"
        )
        add_fallback()



def async_unregister_card(hass: Any) -> None:
    """Remove the injected frontend module on integration unload.

    The file endpoint remains registered until Home Assistant restarts;
    storage resources and user dashboards stay unchanged.
    """
    from homeassistant.components import frontend

    data = hass.data.get(DOMAIN, {})
    if data.pop(_EXTRA_MODULE_REGISTERED, False):
        frontend.remove_extra_js_url(hass, CARD_RESOURCE)
