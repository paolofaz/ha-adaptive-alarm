"""Adaptive Alarm adapter (development preview only).

No entities, listeners, services or actuators are registered in this version.
The policy engine is intentionally independent of Home Assistant.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Load the preview config entry without interacting with the alarm."""
    _LOGGER.warning(
        "Adaptive Alarm preview loaded: no alarm entities or actuators are enabled"
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the preview."""
    return True
