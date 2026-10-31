"""Configuration: quick initial setup and editable native protection wizard.

No physical outputs. Changes are blocked during an active/arming session so
an edit cannot silently replace a live security snapshot.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ARMING_DELAY, CONF_RECOVERY_POLICY, CONF_STORM_SENSOR,
    CONF_VIBRATION_DEBOUNCE, CONF_VIBRATION_PROFILE, CONF_VIBRATION_WINDOW,
    DEFAULT_ARMING_DELAY, DEFAULT_RECOVERY_POLICY, DEFAULT_VIBRATION_DEBOUNCE,
    DEFAULT_VIBRATION_PROFILE, DEFAULT_VIBRATION_WINDOW, DEFAULT_NAME, DOMAIN,
    VIBRATION_ASSIGNMENTS,
)
from .engine.configurable import AlternativeGroup, ProtectionRules, rules_for_config
from .engine.vibration_links import VibrationConfigurationError, validated_vibration_links


def _contacts(*, multiple: bool = True):
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain="binary_sensor", multiple=multiple)
    )


def _lock():
    return selector.EntitySelector(selector.EntitySelectorConfig(domain="lock"))


class AdaptiveAlarmConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """The integration can be added without a premature house-specific schema."""

    VERSION = 2

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        return AdaptiveAlarmOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(
                title=user_input.get("name") or DEFAULT_NAME,
                data={"setup_version": 2},
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional("name", default=DEFAULT_NAME): str,
            }),
        )


class AdaptiveAlarmOptionsFlow(config_entries.OptionsFlow):
    """Native multi-page editor for arbitrary mandatory AND alternative OR rules."""

    def _rules(self) -> ProtectionRules:
        return rules_for_config(self.config_entry.data, self.config_entry.options)

    def _active(self) -> bool:
        ctrl = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        return bool(ctrl and (
            ctrl.machine.active or ctrl.machine.phase.value == "arming"
        ))

    def _save(self, *, protection: ProtectionRules | None = None,
              other: dict[str, Any] | None = None):
        if self._active():
            return self.async_abort(reason="active_session")
        opts = dict(self.config_entry.options)
        if protection is not None:
            opts["protection"] = protection.to_dict()
        elif "protection" not in opts:
            opts["protection"] = self._rules().to_dict()
        if other:
            opts.update(other)
        return self.async_create_entry(title="", data=opts)

    def _with(self, **changes) -> ProtectionRules:
        data = self._rules().to_dict()
        data.update(changes)
        return ProtectionRules.from_dict(data)

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "mandatory", "group", "remove_group",
                "optional", "vibrations", "siren", "timing",
            ],
        )

    async def async_step_mandatory(self, user_input: dict[str, Any] | None = None):
        rule = self._rules()
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                update = self._with(
                    mandatory=user_input.get("mandatory", []),
                    lock=user_input.get("lock") or None,
                )
            except (ValueError, KeyError, TypeError):
                errors["base"] = "invalid_rules"
            else:
                return self._save(protection=update)
        return self.async_show_form(
            step_id="mandatory", errors=errors,
            data_schema=vol.Schema({
                vol.Optional("mandatory", default=list(rule.mandatory)): _contacts(),
                vol.Optional("lock", description={
                    "suggested_value": rule.lock
                }): _lock(),
            }),
        )

    async def async_step_group(self, user_input: dict[str, Any] | None = None):
        rule = self._rules()
        errors: dict[str, str] = {}
        if user_input is not None:
            name = str(user_input.get("name", "")).strip()
            contacts = tuple(user_input.get("contacts", []))
            try:
                group = AlternativeGroup(name=name, contacts=contacts)
                # Same name edits a group. Other group names stay untouched.
                updated_groups = [
                    g for g in rule.groups if g.name.casefold() != name.casefold()
                ] + [group]
                update = self._with(groups=[
                    {"name": g.name, "contacts": list(g.contacts)}
                    for g in updated_groups
                ])
            except (ValueError, KeyError, TypeError):
                errors["base"] = "invalid_rules"
            else:
                return self._save(protection=update)
        return self.async_show_form(
            step_id="group", errors=errors,
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Required("contacts"): _contacts(),
            }),
        )

    async def async_step_remove_group(self, user_input: dict[str, Any] | None = None):
        rule = self._rules()
        if not rule.groups:
            return self.async_abort(reason="no_groups")
        if user_input is not None:
            selected = user_input["name"]
            updated = self._with(groups=[
                {"name": g.name, "contacts": list(g.contacts)}
                for g in rule.groups if g.name != selected
            ])
            return self._save(protection=updated)
        return self.async_show_form(
            step_id="remove_group",
            data_schema=vol.Schema({
                vol.Required("name"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[g.name for g in rule.groups]
                    )
                )
            }),
        )

    async def async_step_optional(self, user_input: dict[str, Any] | None = None):
        rule = self._rules()
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                update = self._with(optional=user_input.get("optional", []))
            except (ValueError, KeyError, TypeError):
                errors["base"] = "invalid_rules"
            else:
                return self._save(protection=update)
        return self.async_show_form(
            step_id="optional", errors=errors,
            data_schema=vol.Schema({
                vol.Optional("optional", default=list(rule.optional)): _contacts()
            }),
        )

    def _links(self) -> list[dict[str, str]]:
        opts = self.config_entry.options
        if "vibration_links" in opts:
            return list(opts["vibration_links"])
        old = self.config_entry.data
        return [
            {"sensor": opts[sensor_key], "contact": old[contact_key]}
            for sensor_key, contact_key in VIBRATION_ASSIGNMENTS
            if opts.get(sensor_key) and old.get(contact_key)
        ]

    async def async_step_vibrations(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        old_links = self._links()
        if user_input is not None:
            pairs = [
                (user_input.get(f"sensor_{n}"), user_input.get(f"contact_{n}"))
                for n in (1, 2, 3)
            ]
            try:
                validated_vibration_links(pairs, self._rules().known_contacts)
            except VibrationConfigurationError as exc:
                errors["base"] = str(exc)
            else:
                return self._save(other={
                    "vibration_links": [
                        {"sensor": sensor, "contact": contact}
                        for sensor, contact in pairs if sensor and contact
                    ],
                })
        schema: dict[Any, Any] = {}
        for n in (1, 2, 3):
            saved = old_links[n - 1] if len(old_links) >= n else {}
            for key, domain in (
                (f"sensor_{n}", "binary_sensor"),
                (f"contact_{n}", "binary_sensor"),
            ):
                value = saved.get("sensor" if key.startswith("sensor") else "contact")
                schema[vol.Optional(key, description={"suggested_value": value})] = (
                    selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=domain)
                    )
                )
        return self.async_show_form(
            step_id="vibrations", data_schema=vol.Schema(schema), errors=errors,
        )

    async def async_step_siren(self, user_input: dict[str, Any] | None = None):
        rule = self._rules()
        if user_input is not None:
            try:
                update = self._with(siren=user_input.get("siren") or None)
            except (ValueError, KeyError, TypeError):
                return self.async_show_form(
                    step_id="siren", data_schema=self._siren_schema(),
                    errors={"base": "invalid_rules"},
                )
            return self._save(protection=update)
        return self.async_show_form(
            step_id="siren", data_schema=self._siren_schema(),
        )

    def _siren_schema(self):
        return vol.Schema({
            vol.Optional("siren", description={
                "suggested_value": self._rules().siren
            }): selector.EntitySelector(selector.EntitySelectorConfig(
                domain=["siren", "switch"]
            ))
        })

    async def async_step_timing(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self._save(other=user_input)
        opts = self.config_entry.options
        return self.async_show_form(
            step_id="timing", data_schema=vol.Schema({
                vol.Required("arming_delay", default=opts.get(
                    CONF_ARMING_DELAY, DEFAULT_ARMING_DELAY
                )): vol.All(vol.Coerce(int), vol.Range(min=0, max=600)),
                vol.Required("vibration_profile", default=opts.get(
                    CONF_VIBRATION_PROFILE, DEFAULT_VIBRATION_PROFILE
                )): selector.SelectSelector(selector.SelectSelectorConfig(
                    options=["balanced", "cross", "cautious"]
                )),
                vol.Required("vibration_debounce", default=opts.get(
                    CONF_VIBRATION_DEBOUNCE, DEFAULT_VIBRATION_DEBOUNCE
                )): vol.All(vol.Coerce(int), vol.Range(min=1, max=20)),
                vol.Required("vibration_window", default=opts.get(
                    CONF_VIBRATION_WINDOW, DEFAULT_VIBRATION_WINDOW
                )): vol.All(vol.Coerce(int), vol.Range(min=10, max=180)),
                vol.Required("recovery_policy", default=opts.get(
                    CONF_RECOVERY_POLICY, DEFAULT_RECOVERY_POLICY
                )): selector.SelectSelector(selector.SelectSelectorConfig(
                    options=["notify", "trigger"]
                )),
                vol.Optional("storm_sensor", description={
                    "suggested_value": opts.get(CONF_STORM_SENSOR)
                }): _contacts(multiple=False),
            }),
        )
