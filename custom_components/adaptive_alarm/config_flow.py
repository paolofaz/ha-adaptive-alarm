"""Native configuration and options flows for the simulated alarm."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ARMING_DELAY,
    CONF_ENTRY_CONTACT,
    CONF_ENTRY_LOCK,
    CONF_EXTRA_CONTACTS,
    CONF_RECOVERY_POLICY,
    CONF_SHUTTER_BATH,
    CONF_SHUTTER_LIVING,
    CONF_STORM_SENSOR,
    CONF_VIBRATION_DEBOUNCE,
    CONF_VIBRATION_PROFILE,
    VIBRATION_PAIRS,
    CONF_VIBRATION_WINDOW,
    CONF_WINDOW_BATH,
    CONF_WINDOW_LIVING,
    DEFAULT_ARMING_DELAY,
    DEFAULT_NAME,
    DEFAULT_RECOVERY_POLICY,
    DEFAULT_VIBRATION_DEBOUNCE,
    DEFAULT_VIBRATION_PROFILE,
    DEFAULT_VIBRATION_WINDOW,
    DOMAIN,
)


class AdaptiveAlarmConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Choose the fixed minimum-route contacts in the setup flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Expose native configuration for additional zones and vibration."""
        return AdaptiveAlarmOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Create a single alarm instance, with no actuators configured."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        errors: dict[str, str] = {}
        if user_input is not None:
            contacts = [
                user_input[CONF_ENTRY_CONTACT],
                user_input[CONF_SHUTTER_LIVING],
                user_input[CONF_SHUTTER_BATH],
                user_input[CONF_WINDOW_LIVING],
                user_input[CONF_WINDOW_BATH],
            ]
            if len(set(contacts)) != len(contacts):
                errors["base"] = "duplicate_entities"
            else:
                return self.async_create_entry(title=DEFAULT_NAME, data=user_input)

        binary = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="binary_sensor")
        )
        lock = selector.EntitySelector(selector.EntitySelectorConfig(domain="lock"))
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ENTRY_CONTACT): binary,
                    vol.Required(CONF_ENTRY_LOCK): lock,
                    vol.Required(CONF_SHUTTER_LIVING): binary,
                    vol.Required(CONF_SHUTTER_BATH): binary,
                    vol.Required(CONF_WINDOW_LIVING): binary,
                    vol.Required(CONF_WINDOW_BATH): binary,
                }
            ),
            errors=errors,
        )


class AdaptiveAlarmOptionsFlow(config_entries.OptionsFlow):
    """Optional extra contacts, vibration filters, delays and fault reaction."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Present a single page of meaningful operational settings."""
        if user_input is not None:
            required = set(self.config_entry.data.values())
            extras = set(user_input.get(CONF_EXTRA_CONTACTS, []))
            contacts = required | extras
            vibration_sensors = [
                user_input[sensor_key]
                for sensor_key, _ in VIBRATION_PAIRS
                if user_input.get(sensor_key)
            ]
            errors: dict[str, str] = {}
            if required & extras or len(vibration_sensors) != len(set(vibration_sensors)):
                errors["base"] = "duplicate_entities"
            elif contacts & set(vibration_sensors):
                errors["base"] = "duplicate_entities"
            else:
                for sensor_key, target_key in VIBRATION_PAIRS:
                    sensor = user_input.get(sensor_key)
                    target = user_input.get(target_key)
                    if bool(sensor) != bool(target):
                        errors["base"] = "unpaired_vibration"
                        break
                    if target and target not in contacts:
                        errors["base"] = "invalid_vibration_zone"
                        break
            if errors:
                return self.async_show_form(
                    step_id="init", data_schema=self._schema(), errors=errors
                )
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(step_id="init", data_schema=self._schema())

    def _schema(self):
        options = self.config_entry.options
        multiple = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
        )
        entity = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="binary_sensor")
        )
        fields: dict[Any, Any] = {
            vol.Optional(
                CONF_EXTRA_CONTACTS,
                default=list(options.get(CONF_EXTRA_CONTACTS, [])),
            ): multiple,
            vol.Optional(
                CONF_STORM_SENSOR,
                description={"suggested_value": options.get(CONF_STORM_SENSOR)},
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor")
            ),
            vol.Required(
                CONF_ARMING_DELAY, default=options.get(
                    CONF_ARMING_DELAY, DEFAULT_ARMING_DELAY
                )
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=600)),
            vol.Required(
                CONF_VIBRATION_PROFILE, default=options.get(
                    CONF_VIBRATION_PROFILE, DEFAULT_VIBRATION_PROFILE
                )
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["balanced", "cross", "cautious"]
                )
            ),
            vol.Required(
                CONF_VIBRATION_DEBOUNCE, default=options.get(
                    CONF_VIBRATION_DEBOUNCE, DEFAULT_VIBRATION_DEBOUNCE
                )
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=20)),
            vol.Required(
                CONF_VIBRATION_WINDOW, default=options.get(
                    CONF_VIBRATION_WINDOW, DEFAULT_VIBRATION_WINDOW
                )
            ): vol.All(vol.Coerce(int), vol.Range(min=10, max=180)),
            vol.Required(
                CONF_RECOVERY_POLICY, default=options.get(
                    CONF_RECOVERY_POLICY, DEFAULT_RECOVERY_POLICY
                )
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(options=["notify", "trigger"])
            ),
        }
        for sensor_key, target_key in VIBRATION_PAIRS:
            fields[vol.Optional(
                sensor_key,
                description={"suggested_value": options.get(sensor_key)},
            )] = entity
            fields[vol.Optional(
                target_key,
                description={"suggested_value": options.get(target_key)},
            )] = entity
        return vol.Schema(fields)
