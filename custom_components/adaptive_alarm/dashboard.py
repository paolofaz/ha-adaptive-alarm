"""Native Home Assistant Lovelace dashboard, installed once, non-destructively.

Only built-in cards are used; there is no external JS resource to maintain.
The dashboard is created once and then belongs to the user (no overwrites).
Dashboard installation is best-effort and cannot affect the alarm controller.
"""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)
DASHBOARD_PATH = "adaptive-alarm"


def build_dashboard(
    panel: str, ready: str, health: str,
    protected: str, excluded: str,
) -> dict[str, Any]:
    """Build an editable Lovelace storage dashboard from registered entities."""
    def list_card(title: str, attribute: str, empty_text: str) -> dict:
        # Templates read the current entity attributes, not installation-time
        # entity IDs of the physical contacts (which users may rename).
        content = (
            f"### {title}\n"
            f"{{% set zones = state_attr('{panel}', '{attribute}') or [] %}}\n"
            f"{{% if zones %}}\n"
            "{% for zone in zones %}\n"
            "- {{ state_attr(zone, 'friendly_name') or zone }}"
            " ({{ states(zone) }})\n"
            "{% endfor %}\n"
            f"{{% else %}}{empty_text}{{% endif %}}"
        )
        return {"type": "markdown", "content": content}
    return {
        "title": "Adaptive Alarm",
        "views": [{
            "title": "Allarme",
            "path": "allarme",
            "icon": "mdi:shield-home",
            "cards": [
                {"type": "alarm-panel", "entity": panel, "name": "Adaptive Alarm"},
                {"type": "glance", "title": "Protezione",
                 "show_state": True,
                 "entities": [
                     {"entity": ready, "name": "Pronto"},
                     {"entity": health, "name": "Salute"},
                     {"entity": protected, "name": "Protetti"},
                     {"entity": excluded, "name": "Esclusi"},
                 ]},
                {"type": "entities", "title": "Stato e diagnostica", "entities": [
                    {"entity": panel, "name": "Allarme"},
                    {"entity": health, "name": "Diagnostica"},
                    {"entity": ready, "name": "Inserimento consentito"},
                    {"entity": protected, "name": "Contatti protetti"},
                    {"entity": excluded, "name": "Contatti esclusi"},
                ]},
                list_card("Contatti protetti", "protected_zones", "Nessun contatto protetto."),
                list_card("Contatti in attesa", "pending_zones", "Nessun contatto in attesa."),
                list_card("Contatti esclusi", "excluded_zones", "Nessun contatto escluso."),
                {"type": "markdown", "content": (
                    "### Dettagli sessione\n"
                    f"**Requisiti soddisfatti:** {{{{ (state_attr('{panel}', 'minimum_routes') or []) | join(', ') or '—' }}}}\n\n"
                    f"**Causa ultimo scatto:** {{{{ state_attr('{panel}', 'trigger_cause') or '—' }}}}\n\n"
                    f"**Termine allarme (timestamp):** {{{{ state_attr('{panel}', 'triggered_until') or '—' }}}}\n\n"
                    f"**Problemi:** {{{{ state_attr('{panel}', 'fault') or 'Nessuno' }}}}\n\n"
                    f"**Errore sirena:** {{{{ state_attr('{panel}', 'siren_last_error') or 'Nessuno' }}}}"
                )},
                {"type": "markdown", "content": (
                    "### Sensori con anomalie\n"
                    f"{{% set problems = state_attr('{health}', 'protected_zone_problem_states') or {{}} %}}\n"
                    "{% if problems %}"
                    "{% for zone, reason in problems.items() %}\n"
                    "- {{ state_attr(zone, 'friendly_name') or zone }}: {{ reason }}"
                    "{% endfor %}"
                    "{% else %}Nessuna anomalia rilevata.{% endif %}"
                )},
            ],
        }],
    }


async def async_ensure_dashboard(hass: Any, entry_id: str) -> None:
    """Create once through Lovelace storage; do not alter user edits.

    Home Assistant's Lovelace dashboard collection is an internal API; failures
    are nonfatal and logged. A manual dashboard can always use build_dashboard.
    """
    from homeassistant.components import frontend
    from homeassistant.components.lovelace import LOVELACE_DATA, _register_panel
    from homeassistant.components.lovelace import dashboard as lovelace_dashboard
    from homeassistant.helpers import entity_registry as er

    data = hass.data.get(LOVELACE_DATA)
    if data is None:
        _LOGGER.warning("Lovelace is not loaded; dashboard creation skipped")
        return

    registry = er.async_get(hass)
    def entity(domain: str, kind: str) -> str | None:
        return registry.async_get_entity_id(domain, "adaptive_alarm", f"{entry_id}_{kind}")

    panel = entity("alarm_control_panel", "panel")
    ready = entity("binary_sensor", "ready")
    health = entity("sensor", "health")
    protected = entity("sensor", "protected")
    excluded = entity("sensor", "excluded")
    if not all((panel, ready, health, protected, excluded)):
        _LOGGER.warning("Adaptive Alarm entities not registered yet; dashboard skipped")
        return

    # Do not take over an existing dashboard at the same URL.
    if DASHBOARD_PATH in data.dashboards or frontend.async_panel_exists(hass, DASHBOARD_PATH):
        return

    collection = lovelace_dashboard.DashboardsCollection(hass)
    await collection.async_load()
    existing = next(
        (item for item in collection.async_items()
         if item.get("url_path") == DASHBOARD_PATH), None
    )
    if existing:
        # Dashboard has been intentionally modified or hidden by the user.
        return

    item = await collection.async_create_item({
        "url_path": DASHBOARD_PATH,
        "title": "Adaptive Alarm",
        "icon": "mdi:shield-home",
        "show_in_sidebar": True,
        "require_admin": False,
    })
    dashboard_obj = lovelace_dashboard.LovelaceStorage(hass, item)
    data.dashboards[DASHBOARD_PATH] = dashboard_obj
    await dashboard_obj.async_save(
        build_dashboard(panel, ready, health, protected, excluded)
    )
    _register_panel(hass, DASHBOARD_PATH, "storage", item, False)
    _LOGGER.info("Adaptive Alarm dashboard created at /%s", DASHBOARD_PATH)
