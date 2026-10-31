"""Read-only readiness diagnostic."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    async_add_entities([AdaptiveReady(hass.data[DOMAIN][entry.entry_id])])


class AdaptiveReady(BinarySensorEntity):
    """Minimum route eligibility, never an arming bypass."""

    _attr_has_entity_name = True
    _attr_name = "Ready to arm"
    _attr_icon = "mdi:shield-check"

    def __init__(self, controller) -> None:
        self.controller = controller
        self._attr_unique_id = f"{controller.entry.entry_id}_ready"
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
    def is_on(self) -> bool:
        return self.controller.readiness.permitted

    @property
    def extra_state_attributes(self) -> dict:
        value = self.controller.readiness
        return {"routes": list(value.routes), "problems": list(value.problems)}
