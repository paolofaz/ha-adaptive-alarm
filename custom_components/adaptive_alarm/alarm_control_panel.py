"""Home Assistant alarm panel for Adaptive Alarm."""

from __future__ import annotations

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN
from .controller import AdaptiveAlarmController
from .engine.runtime import Phase

MAP = {
    Phase.DISARMED: AlarmControlPanelState.DISARMED,
    Phase.ARMING: AlarmControlPanelState.ARMING,
    Phase.ARMED_AWAY: AlarmControlPanelState.ARMED_AWAY,
    Phase.TRIGGERED: AlarmControlPanelState.TRIGGERED,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Expose the alarm control panel."""
    async_add_entities([AdaptiveAlarmPanel(hass.data[DOMAIN][entry.entry_id])])


class AdaptiveAlarmPanel(AlarmControlPanelEntity):
    """Away arming and HomeKit-compatible alarm states."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.TRIGGER
    )
    _attr_code_arm_required = False

    def __init__(self, controller: AdaptiveAlarmController) -> None:
        self.controller = controller
        self._attr_unique_id = f"{controller.entry.entry_id}_panel"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, controller.entry.entry_id)},
            "name": "Adaptive Alarm",
            "manufacturer": "Adaptive Alarm (community)",
            "model": "Adaptive Alarm 1.0",
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self.controller.signal, self.async_write_ha_state)
        )

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        return MAP.get(self.controller.machine.phase)

    @property
    def extra_state_attributes(self) -> dict:
        session = self.controller.machine.session
        return {
            "siren_configured": bool(self.controller.siren_entity),
            "siren_enabled": self.controller.siren_output_enabled,
            "siren_entity": self.controller.siren_entity,
            "siren_last_error": self.controller.siren_last_error,
            "fake_siren_enabled": self.controller.fake_siren_enabled,
            "fake_siren_helper": self.controller.fake_siren_helper,
            "fault": self.controller.machine.fault or None,
            "triggered_until": self.controller.machine.triggered_until,
            "trigger_cause": self.controller.machine.trigger_cause,
            "minimum_routes": list(session.initial_routes) if session else [],
            "protected_zones": sorted(session.protected_zones) if session else [],
            "pending_zones": sorted(session.pending_zones) if session else [],
            "excluded_zones": sorted(session.excluded_zones) if session else [],
            "session_id": session.identifier if session else None,
            "arming_until": self.controller.machine.arming_until,
        }

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        await self.controller.async_arm()

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        await self.controller.async_disarm()

    async def async_alarm_trigger(self, code: str | None = None) -> None:
        await self.controller.async_trigger()
