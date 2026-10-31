"""Adaptive Alarm integration: no physical outputs in the preview."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Start controller and register platforms; clean up if setup fails."""
    from homeassistant.const import Platform

    from .controller import AdaptiveAlarmController


    platforms = (Platform.ALARM_CONTROL_PANEL, Platform.BINARY_SENSOR, Platform.SENSOR)
    controller = AdaptiveAlarmController(hass, entry)
    await controller.async_start()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = controller
    try:
        await hass.config_entries.async_forward_entry_setups(entry, platforms)
    except Exception:
        await controller.async_stop()
        hass.data[DOMAIN].pop(entry.entry_id, None)
        raise
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload settings after changes in the native options flow."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Stop subscriptions only when all entities have been unloaded."""
    from homeassistant.const import Platform

    platforms = (Platform.ALARM_CONTROL_PANEL, Platform.BINARY_SENSOR, Platform.SENSOR)
    if not await hass.config_entries.async_unload_platforms(entry, platforms):
        return False
    await hass.data[DOMAIN][entry.entry_id].async_stop()
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
