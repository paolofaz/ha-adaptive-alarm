"""Configuration: quick initial setup and editable native protection wizard.

Physical outputs are strictly opted-in light controls; changes are blocked during an active/arming session so
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
    CONF_ARMING_DELAY, CONF_STORM_SENSOR,
    CONF_VIBRATION_DEBOUNCE, CONF_VIBRATION_PROFILE, CONF_VIBRATION_WINDOW,
    CONF_VIBRATION_THRESHOLD, DEFAULT_VIBRATION_THRESHOLD,
    CONF_DETERRENT_ENABLED, CONF_DETERRENT_LIGHTS,
    CONF_DETERRENT_AUTO_OFF, CONF_DETERRENT_OFF_DELAY, DEFAULT_DETERRENT_OFF_DELAY,
    CONF_NOTIFY_ENABLED, CONF_NOTIFY_ENTITIES, CONF_NOTIFY_SERVICES,
    DEFAULT_ARMING_DELAY, DEFAULT_VIBRATION_DEBOUNCE,
    DEFAULT_VIBRATION_PROFILE, DEFAULT_VIBRATION_WINDOW, DEFAULT_NAME, DOMAIN,
    VIBRATION_ASSIGNMENTS,
)
from .engine.configurable import AlternativeGroup, ProtectionRules, rules_for_config
from .engine.presentation import group_summary
from .engine.vibration_links import VibrationConfigurationError, validated_vibration_links
from .notifications import async_send_notification, validate_targets


OPTIONS_MENU_STEPS = (
    "mandatory",
    "group",
    "remove_group",
    "optional",
    "vibrations",
    "deterrent",
    "notifications",
    "notification_test",
    "siren",
    "timing",
)


def _contacts(*, multiple: bool = True):
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain="binary_sensor", multiple=multiple)
    )


def _lock():
    return selector.EntitySelector(selector.EntitySelectorConfig(domain="lock"))


class AdaptiveAlarmConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """The integration can be added without a premature house-specific schema."""

    VERSION = 1
    MINOR_VERSION = 1  # Preserve existing v0.3 config-entry major version

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

    def _friendly_name(self, entity_id: str) -> str:
        """Show current HA display names in the read-only group summary."""
        state = self.hass.states.get(entity_id)
        if state:
            friendly = state.attributes.get("friendly_name")
            if isinstance(friendly, str) and friendly.strip():
                return friendly
        return entity_id

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
            # Do not persist a rule edit that strands an existing vibration
            # sensor on an unknown/removed contact. Explicitly unlink it first.
            try:
                validated_vibration_links(
                    ((v["sensor"], v["contact"]) for v in self._links()),
                    protection.known_contacts,
                )
            except (VibrationConfigurationError, KeyError):
                return self.async_abort(reason="unlink_vibration_first")
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
            menu_options=list(OPTIONS_MENU_STEPS),
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
        language = self.hass.config.language
        return self.async_show_form(
            step_id="mandatory", errors=errors,
            description_placeholders={
                "groups_summary": group_summary(
                    rule.groups, self._friendly_name,
                    alternative_word="oppure" if language.startswith("it") else "or",
                ),
            },
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
        """Manage any number of vibration sensors, one item per action."""
        choices = ["vibration_add"]
        if self._links():
            choices += ["vibration_edit", "vibration_remove"]
        return self.async_show_menu(step_id="vibrations", menu_options=choices)

    def _validate_vibration_links(self, links: list[dict[str, str]]) -> str | None:
        try:
            validated_vibration_links(
                ((link["sensor"], link["contact"]) for link in links),
                self._rules().known_contacts,
            )
        except (VibrationConfigurationError, KeyError) as exc:
            return str(exc) if isinstance(exc, VibrationConfigurationError) else "invalid_vibration_zone"
        return None

    async def async_step_vibration_add(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            links = [*self._links(), {
                "sensor": user_input["sensor"], "contact": user_input["contact"],
            }]
            if issue := self._validate_vibration_links(links):
                errors["base"] = issue
            else:
                return self._save(other={"vibration_links": links})
        return self.async_show_form(
            step_id="vibration_add", errors=errors,
            data_schema=vol.Schema({
                vol.Required("sensor"): _contacts(multiple=False),
                vol.Required("contact"): _contacts(multiple=False),
            }),
        )

    async def async_step_vibration_edit(self, user_input: dict[str, Any] | None = None):
        links = self._links()
        if not links:
            return self.async_abort(reason="no_vibrations")
        if user_input is not None:
            self._editing_vibration_source = user_input["sensor"]
            return await self.async_step_vibration_edit_contact()
        return self.async_show_form(
            step_id="vibration_edit",
            data_schema=vol.Schema({
                vol.Required("sensor"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[link["sensor"] for link in links]
                    )
                )
            }),
        )

    async def async_step_vibration_edit_contact(
        self, user_input: dict[str, Any] | None = None,
    ):
        source = getattr(self, "_editing_vibration_source", None)
        links = self._links()
        original = next((v for v in links if v["sensor"] == source), None)
        if original is None:
            return self.async_abort(reason="no_vibrations")
        errors: dict[str, str] = {}
        if user_input is not None:
            updated = [
                {"sensor": link["sensor"],
                 "contact": user_input["contact"] if link["sensor"] == source else link["contact"]}
                for link in links
            ]
            if issue := self._validate_vibration_links(updated):
                errors["base"] = issue
            else:
                return self._save(other={"vibration_links": updated})
        return self.async_show_form(
            step_id="vibration_edit_contact", errors=errors,
            data_schema=vol.Schema({
                vol.Required("contact", description={
                    "suggested_value": original["contact"]
                }): _contacts(multiple=False),
            }),
        )

    async def async_step_vibration_remove(self, user_input: dict[str, Any] | None = None):
        links = self._links()
        if not links:
            return self.async_abort(reason="no_vibrations")
        if user_input is not None:
            updated = [v for v in links if v["sensor"] != user_input["sensor"]]
            return self._save(other={"vibration_links": updated})
        return self.async_show_form(
            step_id="vibration_remove",
            data_schema=vol.Schema({
                vol.Required("sensor"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[v["sensor"] for v in links]
                    )
                )
            }),
        )

    async def async_step_deterrent(self, user_input: dict[str, Any] | None = None):
        """Opt-in lights only. Never allow switches or sirens as outputs."""
        opts = self.config_entry.options
        errors: dict[str, str] = {}
        if user_input is not None:
            enabled = user_input.get(CONF_DETERRENT_ENABLED, False) is True
            lights = user_input.get(CONF_DETERRENT_LIGHTS, [])
            if enabled and not lights:
                errors["base"] = "deterrent_no_lights"
            elif any(not isinstance(v, str) or not v.startswith("light.") for v in lights):
                errors["base"] = "invalid_deterrent_lights"
            else:
                return self._save(other={
                    CONF_DETERRENT_ENABLED: enabled,
                    CONF_DETERRENT_LIGHTS: lights,
                    CONF_DETERRENT_AUTO_OFF: user_input.get(CONF_DETERRENT_AUTO_OFF, False) is True,
                    CONF_DETERRENT_OFF_DELAY: user_input.get(
                        CONF_DETERRENT_OFF_DELAY, DEFAULT_DETERRENT_OFF_DELAY
                    ),
                })
        return self.async_show_form(
            step_id="deterrent", errors=errors,
            data_schema=vol.Schema({
                vol.Required(
                    CONF_DETERRENT_ENABLED,
                    default=opts.get(CONF_DETERRENT_ENABLED, False),
                ): bool,
                vol.Optional(
                    CONF_DETERRENT_LIGHTS,
                    default=opts.get(CONF_DETERRENT_LIGHTS, []),
                ): selector.EntitySelector(selector.EntitySelectorConfig(
                    domain="light", multiple=True,
                )),
                vol.Required(
                    CONF_DETERRENT_AUTO_OFF,
                    default=opts.get(CONF_DETERRENT_AUTO_OFF, False),
                ): bool,
                vol.Required(
                    CONF_DETERRENT_OFF_DELAY,
                    default=opts.get(
                        CONF_DETERRENT_OFF_DELAY, DEFAULT_DETERRENT_OFF_DELAY,
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=15, max=3600)),
            }),
        )

    def _available_notify_services(self) -> list[str]:
        """Only real notify actions, never a generic arbitrary HA service."""
        names = self.hass.services.async_services().get("notify", {})
        return sorted(
            name for name in names
            if name not in ("notify", "send_message", "persistent_notification")
        )

    async def async_step_notifications(self, user_input: dict[str, Any] | None = None):
        """Configure explicit push providers, never credentials or chat IDs."""
        opts = self.config_entry.options
        errors: dict[str, str] = {}
        available = self._available_notify_services()
        if user_input is not None:
            enabled = user_input.get(CONF_NOTIFY_ENABLED, False) is True
            entities = user_input.get(CONF_NOTIFY_ENTITIES, [])
            services = user_input.get(CONF_NOTIFY_SERVICES, [])
            try:
                chosen_entities, chosen_services = validate_targets(entities, services)
            except ValueError:
                errors["base"] = "invalid_notification_target"
            else:
                if enabled and not (chosen_entities or chosen_services):
                    errors["base"] = "notification_no_targets"
                elif any(name not in available for name in chosen_services):
                    errors["base"] = "notification_service_missing"
                else:
                    return self._save(other={
                        CONF_NOTIFY_ENABLED: enabled,
                        CONF_NOTIFY_ENTITIES: list(chosen_entities),
                        CONF_NOTIFY_SERVICES: list(chosen_services),
                    })
        known = sorted(set(available) | set(opts.get(CONF_NOTIFY_SERVICES, [])))
        return self.async_show_form(
            step_id="notifications", errors=errors,
            data_schema=vol.Schema({
                vol.Required(CONF_NOTIFY_ENABLED, default=opts.get(
                    CONF_NOTIFY_ENABLED, False,
                )): bool,
                vol.Optional(CONF_NOTIFY_ENTITIES, default=opts.get(
                    CONF_NOTIFY_ENTITIES, [],
                )): selector.EntitySelector(selector.EntitySelectorConfig(
                    domain="notify", multiple=True,
                )),
                vol.Optional(CONF_NOTIFY_SERVICES, default=opts.get(
                    CONF_NOTIFY_SERVICES, [],
                )): selector.SelectSelector(selector.SelectSelectorConfig(
                    options=known, multiple=True,
                )),
            }),
        )

    async def async_step_notification_test(
        self, user_input: dict[str, Any] | None = None,
    ):
        """User-selected menu action; only sends a harmless test message."""
        opts = self.config_entry.options
        entities = opts.get(CONF_NOTIFY_ENTITIES, [])
        services = opts.get(CONF_NOTIFY_SERVICES, [])
        try:
            entity_ids, names = validate_targets(entities, services)
        except ValueError:
            return self.async_abort(reason="invalid_notification_target")
        if not (entity_ids or names):
            return self.async_abort(reason="notification_no_targets")
        result = await async_send_notification(
            self.hass, entities=entity_ids, services=names,
            message="Test Adaptive Alarm: canale notifiche configurato correttamente. Nessun allarme attivato.",
        )
        if result["failed"]:
            return self.async_abort(reason="notification_test_failed")
        return self.async_abort(reason="notification_test_sent")

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
        """Explicit numeric values and localized offline-return choices."""
        if user_input is not None:
            return self._save(other=user_input)
        opts = self.config_entry.options
        number = lambda minimum, maximum: selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=minimum, max=maximum, step=1,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="s",
            )
        )
        return self.async_show_form(
            step_id="timing", data_schema=vol.Schema({
                vol.Required(CONF_ARMING_DELAY, default=opts.get(
                    CONF_ARMING_DELAY, DEFAULT_ARMING_DELAY
                )): vol.All(number(0, 600), vol.Coerce(int)),
                vol.Required(CONF_VIBRATION_THRESHOLD, default=opts.get(
                    CONF_VIBRATION_THRESHOLD,
                    3 if opts.get(CONF_VIBRATION_PROFILE) in ("cautious", "cross")
                    else DEFAULT_VIBRATION_THRESHOLD,
                )): vol.All(
                    selector.NumberSelector(selector.NumberSelectorConfig(
                        min=2, max=3, step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )),
                    vol.Coerce(int), vol.In((2, 3)),
                ),
                vol.Required(CONF_VIBRATION_DEBOUNCE, default=opts.get(
                    CONF_VIBRATION_DEBOUNCE, DEFAULT_VIBRATION_DEBOUNCE
                )): vol.All(number(1, 20), vol.Coerce(int)),
                vol.Required(CONF_VIBRATION_WINDOW, default=opts.get(
                    CONF_VIBRATION_WINDOW, DEFAULT_VIBRATION_WINDOW
                )): vol.All(number(5, 180), vol.Coerce(int)),

            }),
        )
