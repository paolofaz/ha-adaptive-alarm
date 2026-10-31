"""Adaptive Alarm: HACS-installable, simulation-only integration.

No physical actuators, codes, RF, MQTT, lock or siren services are invoked.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .controller import AdaptiveAlarmController

PLATFORMS = [Platform.ALARM_CONTROL_PANEL, Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one serialized alarm engine, then expose read-only diagnostics."""
    controller = AdaptiveAlarmController(hass, entry)
    await controller.async_start()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = controller
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload configured zone catalogue and thresholds."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Stop listeners only after all HA entities unload."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await hass.data[DOMAIN][entry.entry_id].async_stop()
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
