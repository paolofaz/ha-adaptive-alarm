"""Initial native UI flow for the two alternative minimum paths."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_ENTRY_CONTACT,
    CONF_ENTRY_LOCK,
    CONF_SHUTTER_BATH,
    CONF_SHUTTER_LIVING,
    CONF_WINDOW_BATH,
    CONF_WINDOW_LIVING,
    DEFAULT_NAME,
    DOMAIN,
)


class AdaptiveAlarmConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Collect the minimum safety path entities. No commands are sent."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select contacts and the lock."""
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
        lock = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="lock")
        )
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
