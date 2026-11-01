"""Only explicitly selected Home Assistant notify endpoints are supported.

The caller supplies pre-configured notify entities (including modern Telegram
Bot chats) and/or legacy notify action names (including Companion mobile_app).
No chat IDs, credentials, external HTTP or generic service calls are allowed.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable

_LOGGER = logging.getLogger(__name__)
_VALID_SERVICE = re.compile(r"^[a-z][a-z0-9_]*$")
_RESERVED = frozenset({"notify", "send_message", "persistent_notification"})


def validate_targets(entities: Iterable[str], services: Iterable[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Validate user-supplied routing without granting arbitrary service calls."""
    if not isinstance(entities, (list, tuple)) or not isinstance(services, (list, tuple)):
        raise ValueError("invalid_notification_target")
    if any(not isinstance(entity, str) or not entity.startswith("notify.")
           or len(entity.split(".")) != 2 or not _VALID_SERVICE.fullmatch(entity.split(".")[1])
           for entity in entities):
        raise ValueError("invalid_notification_target")
    if any(not isinstance(name, str) or not _VALID_SERVICE.fullmatch(name)
           or name in _RESERVED for name in services):
        raise ValueError("invalid_notification_target")
    return tuple(dict.fromkeys(entities)), tuple(dict.fromkeys(services))


async def async_send_notification(
    hass, *, entities: Iterable[str], services: Iterable[str], message: str,
    title: str = "Adaptive Alarm",
) -> dict[str, list[str]]:
    """Request notification independently for each destination.

    A successful HA action means requested, NOT guaranteed delivered to phone.
    An unavailable endpoint cannot prevent other requests.
    """
    entity_ids, service_names = validate_targets(entities, services)
    result: dict[str, list[str]] = {"requested": [], "failed": []}
    for entity in entity_ids:
        if not hass.services.has_service("notify", "send_message"):
            result["failed"].append(entity)
            continue
        try:
            await hass.services.async_call(
                "notify", "send_message", {"message": message},
                target={"entity_id": entity}, blocking=True,
            )
        except Exception:
            _LOGGER.exception("Notification request failed for entity %s", entity)
            result["failed"].append(entity)
        else:
            result["requested"].append(entity)
    for service in service_names:
        if not hass.services.has_service("notify", service):
            result["failed"].append(f"notify.{service}")
            continue
        try:
            await hass.services.async_call(
                "notify", service, {"message": message, "title": title},
                blocking=True,
            )
        except Exception:
            _LOGGER.exception("Notification request failed for notify.%s", service)
            result["failed"].append(f"notify.{service}")
        else:
            result["requested"].append(f"notify.{service}")
    return result
