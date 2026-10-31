"""Read-only zone counts and current health status."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN
from .engine.runtime import Phase


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    controller = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        AdaptiveDiagnostic(controller, "protected", "Protected zones", "mdi:shield-lock"),
        AdaptiveDiagnostic(controller, "excluded", "Excluded zones", "mdi:shield-off"),
        AdaptiveDiagnostic(controller, "health", "Health", "mdi:heart-pulse"),
    ])


class AdaptiveDiagnostic(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, controller, kind: str, name: str, icon: str) -> None:
        self.controller = controller
        self.kind = kind
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{controller.entry.entry_id}_{kind}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, controller.entry.entry_id)},
            "name": "Adaptive Alarm",
            "manufacturer": "Adaptive Alarm (community)",
            "model": "Dry-run preview",
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self.controller.signal, self.async_write_ha_state)
        )

    @property
    def native_value(self):
        machine = self.controller.machine
        session = machine.session
        if self.kind == "protected":
            return len(session.protected_zones) if session else 0
        if self.kind == "excluded":
            return len(session.excluded_zones) if session else 0
        if machine.phase == Phase.FAULT:
            return "critical"
        if machine.phase == Phase.TRIGGERED:
            return "triggered"
        if machine.phase == Phase.ARMED_AWAY:
            return "degraded" if self.controller._active_faults else "ok"
        return "not_ready" if not self.controller.readiness.permitted else "ready"

    @property
    def extra_state_attributes(self) -> dict:
        session = self.controller.machine.session
        if self.kind == "protected":
            zones = session.protected_zones if session else frozenset()
            return {"zones": sorted(zones), "session_frozen": True}
        if self.kind == "excluded":
            zones = session.excluded_zones if session else frozenset()
            return {"zones": sorted(zones), "session_frozen": True}
        if self.kind == "health":
            return {
                "fault": self.controller.machine.fault or None,
                "simulation_only": True,
                "protected_zone_problems": sorted(self.controller._active_faults),
            }
        return {}
