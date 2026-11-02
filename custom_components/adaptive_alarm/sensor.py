"""Read-only zone counts and current health status."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN
from .engine.runtime import Phase
from .engine.health import protected_state_issues


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
            "model": "Adaptive Alarm 1.0",
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
            return {
                "zones": sorted(zones),
                "minimum_protection_frozen": True,
                "late_pending_enrollment_allowed": True,
            }
        if self.kind == "excluded":
            zones = session.excluded_zones if session else frozenset()
            return {
                "zones": sorted(zones),
                "pending_zones": sorted(session.pending_zones) if session else [],
                "minimum_protection_frozen": True,
                "late_pending_enrollment_allowed": True,
            }
        if self.kind == "health":
            rules = self.controller.paths
            protected = session.protected_zones if session else frozenset()
            issues = protected_state_issues(
                protected,
                {
                    zone: getattr(self.controller.hass.states.get(zone), "state", None)
                    for zone in protected
                },
            )
            return {
                "fault": self.controller.machine.fault or None,
                "triggered_until": self.controller.machine.triggered_until,
                "trigger_cause": self.controller.machine.trigger_cause,
                "held_open_zones": sorted(self.controller.machine.held_open_zones),
                "siren_configured": bool(self.controller.siren_entity),
                "siren_enabled": self.controller.siren_output_enabled,
                "siren_entity": self.controller.siren_entity,
                "siren_last_error": self.controller.siren_last_error,
                "fake_siren_enabled": self.controller.fake_siren_enabled,
                "fake_siren_helper": self.controller.fake_siren_helper,
                "deterrent_enabled": self.controller.deterrent_enabled,
                "deterrent_hold_after_trigger": self.controller.machine.deterrent_hold_after_trigger,
                "deterrent_auto_off_enabled": self.controller.deterrent_auto_off,
                "deterrent_off_delay_seconds": self.controller.deterrent_off_delay,
                "deterrent_lights_waiting_for_on": sorted(
                    self.controller._light_pending
                ),
                "deterrent_lights_awaiting_auto_off": sorted(
                    self.controller._light_leases
                ),
                "requirements_configured": rules.configured,
                "mandatory_contacts": list(rules.mandatory),
                "alternative_groups": {
                    group.name: list(group.contacts) for group in rules.groups
                },
                "optional_contacts": list(rules.optional),
                "lock_configured": bool(rules.lock),
                "protected_zone_problems": sorted(self.controller._active_faults),
                "protected_zone_problem_states": issues,
                "protected_zones_unreadable": sorted(
                    zone for zone, reason in issues.items() if reason != "open"
                ),
                "protected_zones_open": sorted(
                    zone for zone, reason in issues.items() if reason == "open"
                ),
                "pending_zones": sorted(session.pending_zones) if session else [],
                "active_zone_monitoring": sorted(
                    session.protected_zones
                ) if session else [],
            }
        return {}
