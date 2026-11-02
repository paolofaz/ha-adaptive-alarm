"""Serve the Adaptive Alarm Lovelace card and register its resource.

The user owns YAML dashboards: we never create or modify a dashboard or YAML.
If Lovelace resources use storage, register/update the resource automatically.
For YAML-managed resources, users must include the resource entry manually.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
CARD_PATH = "/adaptive_alarm/adaptive-alarm-card.js"
CARD_RESOURCE = f"{CARD_PATH}?v=1.0.1"
CARD_FILE = Path(__file__).parent / "www" / "adaptive-alarm-card.js"
_STATIC_READY = "_card_static_ready"


async def async_register_card(hass: Any) -> None:
    """Expose the JS module and register it without touching user dashboards."""
    from homeassistant.components.http import StaticPathConfig
    from homeassistant.components.lovelace import LOVELACE_DATA

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
        # This is a normal HA limitation, not a failure. Never edit user YAML.
        _LOGGER.info(
            "Adaptive Alarm card is available at %s; add it to "
            "lovelace.resources in configuration.yaml", CARD_PATH
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
