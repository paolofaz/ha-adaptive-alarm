"""Home Assistant adapter for a serialized, dry-run alarm machine.

This module invokes only opted-in light.turn_on / safe light.turn_off and
explicitly selected Home Assistant notify actions. Sirens, locks, switches, RF
and MQTT have no actuator path.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store

from .const import (
    CONF_ARMING_DELAY, CONF_ENTRY_CONTACT, CONF_ENTRY_LOCK,
    CONF_EXTRA_CONTACTS, CONF_RECOVERY_POLICY,
    CONF_SHUTTER_BATH, CONF_SHUTTER_LIVING, CONF_STORM_SENSOR,
    CONF_VIBRATION_DEBOUNCE, CONF_VIBRATION_PROFILE,
    CONF_VIBRATION_WINDOW, CONF_VIBRATION_THRESHOLD, DEFAULT_VIBRATION_THRESHOLD,
    CONF_DETERRENT_ENABLED, CONF_DETERRENT_LIGHTS,
    CONF_DETERRENT_AUTO_OFF, CONF_DETERRENT_OFF_DELAY, DEFAULT_DETERRENT_OFF_DELAY,
    CONF_NOTIFY_ENABLED, CONF_NOTIFY_ENTITIES, CONF_NOTIFY_SERVICES,
    CONF_WINDOW_BATH, CONF_WINDOW_LIVING,
    VIBRATION_ASSIGNMENTS,
    DEFAULT_ARMING_DELAY, DEFAULT_RECOVERY_POLICY, DEFAULT_VIBRATION_DEBOUNCE,
    DEFAULT_VIBRATION_PROFILE, DEFAULT_VIBRATION_WINDOW, DOMAIN, EVENT_ADAPTIVE_ALARM,
)
from .engine import RecoveryPolicy, ZoneState, evaluate_eligibility
from .engine.configurable import rules_for_config
from .engine.runtime import AlarmMachine, Phase
from .engine.presentation import prealert_text, trigger_text, fault_text
from .engine.light_expiry import (
    LIGHT_ACK_TIMEOUT, LightLease, PendingLight, confirm_transition, may_turn_off,
)
from .notifications import async_send_notification, validate_targets
from .engine.vibration_links import validated_vibration_links

_LOGGER = logging.getLogger(__name__)


def _contact_state(state: Any) -> ZoneState:
    """Binary contact: off=closed, on=open; missing/unknown always unsafe."""
    if state is None:
        return ZoneState.UNAVAILABLE
    value = getattr(state, "state", None)
    if value == "off":
        return ZoneState.CLOSED
    if value == "on":
        return ZoneState.OPEN
    return ZoneState.UNAVAILABLE


class AdaptiveAlarmController:
    """Single writer with a persistent session and one event subscriber."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        d = entry.data
        self.paths = rules_for_config(d, entry.options)
        self.lock_entity = self.paths.lock
        self.siren_entity = self.paths.siren  # inert metadata; no siren services
        self.deterrent_enabled = entry.options.get(CONF_DETERRENT_ENABLED) is True
        self.deterrent_lights = tuple(entry.options.get(CONF_DETERRENT_LIGHTS, []))
        if any(
            not isinstance(light, str) or not light.startswith("light.")
            for light in self.deterrent_lights
        ):
            raise ValueError("Deterrent output must be light entities only")

        self.deterrent_auto_off = entry.options.get(CONF_DETERRENT_AUTO_OFF) is True
        self.deterrent_off_delay = int(entry.options.get(
            CONF_DETERRENT_OFF_DELAY, DEFAULT_DETERRENT_OFF_DELAY
        ))
        if not 15 <= self.deterrent_off_delay <= 3600:
            raise ValueError("Invalid light-off delay")
        self.notify_enabled = entry.options.get(CONF_NOTIFY_ENABLED) is True
        self.notify_entities, self.notify_services = validate_targets(
            entry.options.get(CONF_NOTIFY_ENTITIES, []),
            entry.options.get(CONF_NOTIFY_SERVICES, []),
        )

        self.zones = self.paths.known_contacts
        if "vibration_links" in entry.options:
            links = (
                (v.get("sensor"), v.get("contact"))
                for v in entry.options["vibration_links"]
            )
        else:
            # Keep only old v0.3.1 explicit door/window link locations.
            links = (
                (entry.options[sensor_key], d[contact_key])
                for sensor_key, contact_key in VIBRATION_ASSIGNMENTS
                if entry.options.get(sensor_key) and d.get(contact_key)
            )
        self.vibration_zone_map = validated_vibration_links(links, self.zones)
        self.vibrations = frozenset(self.vibration_zone_map)
        self.storm_entity = entry.options.get(CONF_STORM_SENSOR)
        self.machine = AlarmMachine(self.paths, self.zones)
        self._store: Store[dict[str, Any]] = Store(
            hass, 1, f"{DOMAIN}.{entry.entry_id}"
        )
        self._light_store: Store[dict[str, Any]] = Store(
            hass, 1, f"{DOMAIN}.{entry.entry_id}.deterrent_lights"
        )
        self._light_leases: dict[str, LightLease] = {}
        self._light_pending: dict[str, PendingLight] = {}
        self._guard = asyncio.Lock()
        self._remove_callbacks: list[Any] = []
        self._active_faults: set[str] = set()

    @property
    def signal(self) -> str:
        """Dispatcher update signal scoped to this config entry."""
        return f"{DOMAIN}_{self.entry.entry_id}_update"

    def _states(self) -> dict[str, ZoneState]:
        return {zone: _contact_state(self.hass.states.get(zone)) for zone in self.zones}

    def _friendly_name(self, entity_id: str) -> str:
        """Use HA's actual friendly name; keep the ID only as safe fallback."""
        if not entity_id:
            return "sconosciuto"
        state = self.hass.states.get(entity_id)
        if state is None:
            return entity_id
        friendly = state.attributes.get("friendly_name")
        return friendly if isinstance(friendly, str) and friendly.strip() else entity_id

    def _locked(self) -> bool:
        return not self.lock_entity or self.hass.states.is_state(self.lock_entity, "locked")

    @property
    def readiness(self):
        """Compute actual eligibility on every read; never trust a cached sensor."""
        return evaluate_eligibility(self.paths, self._states(), lock_locked=self._locked())

    def _events(self, events: list[dict[str, Any]]) -> None:
        for event in events:
            self.hass.bus.async_fire(
                EVENT_ADAPTIVE_ALARM, {"entry_id": self.entry.entry_id, **event}
            )
        async_dispatcher_send(self.hass, self.signal)

    async def _apply(self, change) -> list[dict[str, Any]]:
        """Commit critical state before publishing events."""
        async with self._guard:
            before = self.machine.snapshot()
            events = change()
            after = self.machine.snapshot()
            if before != after:
                await self._store.async_save(after)
            if events or before != after:
                self._events(events)
            return events

    async def async_start(self) -> None:
        """Load persisted state, attach listeners, then reconcile faults."""
        stored = await self._store.async_load()
        recovery = self.machine.restore(stored)
        old_leases = await self._light_store.async_load()
        if old_leases and old_leases.get("leases"):
            # After any restart/reload we cannot establish who controls a
            # physical light. Never issue automatic OFF from stale metadata.
            await self._light_store.async_save({"leases": []})
            await self._notify_text(
                "Riavvio: spegnimento automatico luci sospeso per sicurezza. "
                "Controlla e spegni manualmente le luci deterrenti rimaste accese."
            )
            self._events([{"type": "deterrent_lights_restart_unclaimed"}])
        # Interrupted arming must not reappear as arming after another restart.
        if stored is not None and self.machine.snapshot() != stored:
            await self._store.async_save(self.machine.snapshot())
        if recovery:
            _LOGGER.warning("Adaptive Alarm restart: %s", recovery)
        # Observe contacts and optional vibrations from one shared listener.
        if self.zones or self.vibrations:
            self._remove_callbacks.append(
                async_track_state_change_event(
                    self.hass, list(self.zones | self.vibrations), self._on_state_event
                )
            )
        if self.lock_entity:
            self._remove_callbacks.append(
                async_track_state_change_event(
                    self.hass, [self.lock_entity], self._on_state_event
                )
            )
        if self.deterrent_enabled and self.deterrent_auto_off and self.deterrent_lights:
            # Register before accepting new requests; async light state updates
            # may arrive after turn_on returned successfully.
            self._remove_callbacks.append(
                async_track_state_change_event(
                    self.hass, list(self.deterrent_lights), self._on_light_state_event,
                )
            )
        self._remove_callbacks.append(
            async_track_time_interval(
                self.hass, self._on_timer, timedelta(seconds=1)
            )
        )
        if self.machine.phase == Phase.ARMED_AWAY:
            await self._refresh_faults()
        self._events(recovery)

    async def async_stop(self) -> None:
        """Release callbacks; leave persisted session untouched."""
        for unsubscribe in self._remove_callbacks:
            unsubscribe()
        self._remove_callbacks.clear()

    @callback
    def _on_timer(self, _now: Any) -> None:
        self.hass.async_create_task(self.async_tick())

    @callback
    def _on_state_event(self, event: Event) -> None:
        self.hass.async_create_task(self._process_state_event(event))

    @callback
    def _on_light_state_event(self, event: Event) -> None:
        self.hass.async_create_task(self._process_light_state_event(event))

    async def _process_light_state_event(self, event: Event) -> None:
        """Claim delayed OFF→ON acknowledgement, never arbitrary lights."""
        entity = event.data.get("entity_id")
        old = event.data.get("old_state")
        new = event.data.get("new_state")
        async with self._guard:
            pending = self._light_pending.get(entity)
            if pending is None:
                return
            session = self.machine.session
            episode = (
                session.identifier
                if session and self.machine.phase in (Phase.ARMED_AWAY, Phase.TRIGGERED)
                else None
            )
            lease = confirm_transition(
                pending, now=time.time(),
                old_state=getattr(old, "state", None),
                old_updated=old.last_updated.isoformat() if old else None,
                new_state=getattr(new, "state", None),
                new_updated=new.last_updated.isoformat() if new else None,
                current_episode=episode,
            )
            # Any change from the originally sampled OFF state invalidates
            # our tracking. Otherwise wait only until the short timeout.
            if lease is None:
                if (
                    old is None or new is None
                    or old.last_updated.isoformat() != pending.baseline_updated
                    or getattr(new, "state", None) != "off"
                ):
                    del self._light_pending[entity]
                    self._events([{
                        "type": "deterrent_light_tracking_cancelled", "light": entity,
                    }])
                return
            self._light_pending.pop(entity, None)
            self._light_leases[entity] = lease
            await self._light_store.async_save({
                "leases": [v.to_dict() for v in self._light_leases.values()]
            })
            self._events([{
                "type": "deterrent_light_tracking_confirmed",
                "light": entity, "timeout_seconds": self.deterrent_off_delay,
            }])

    async def _process_state_event(self, event: Event) -> None:
        data = event.data
        zone = data.get("entity_id")
        old_state = data.get("old_state")
        new_state = data.get("new_state")
        now = time.time()
        if zone in self.zones:
            previous = _contact_state(old_state)
            current = _contact_state(new_state)
            policy = RecoveryPolicy(
                self.entry.options.get(CONF_RECOVERY_POLICY, DEFAULT_RECOVERY_POLICY)
            )
            emitted = await self._apply(
                lambda: self.machine.observed(
                    zone, previous, current, now=now, recovery_policy=policy
                )
            )
            await self._notify_events(emitted)
            await self._refresh_faults()
            # Readiness is derived from actual states, even while disarmed.
            self._events([])
        elif (
            zone in self.vibrations
            and getattr(new_state, "state", None) == "on"
            and getattr(old_state, "state", None) == "off"
        ):
            threshold = self.entry.options.get(CONF_VIBRATION_THRESHOLD)
            if threshold is None:
                # Existing cautious users keep their 3-hit threshold.
                threshold = 3 if self.entry.options.get(CONF_VIBRATION_PROFILE) in ("cautious", "cross") else 2
            events = await self._apply(
                lambda: self.machine.vibration(
                    zone, now=now,
                    protected_zone=self.vibration_zone_map[zone],
                    threshold=int(threshold),
                    debounce=float(self.entry.options.get(
                        CONF_VIBRATION_DEBOUNCE, DEFAULT_VIBRATION_DEBOUNCE
                    )),
                    window=float(self.entry.options.get(
                        CONF_VIBRATION_WINDOW, DEFAULT_VIBRATION_WINDOW
                    )),
                )
            )
            # Do not make an urgent prealert wait for slow Zigbee/Wi-Fi
            # lights (or delay real lighting on a slow notify provider).
            # The prealert never claims the physical lights actually switched.
            await asyncio.gather(
                self._notify_events(events),
                self._request_deterrent_lights(events),
            )
        elif zone == self.lock_entity:
            if self.machine.active and getattr(new_state, "state", None) != "locked":
                await self._apply(
                    lambda: [{"type": "lock_fault", "state": getattr(new_state, "state", None)}]
                )
            self._events([])

    async def _notify_text(self, message: str) -> None:
        """Never block or influence the alarm on notifier errors."""
        if not self.notify_enabled:
            return
        if not self.notify_entities and not self.notify_services:
            return
        try:
            result = await async_send_notification(
                self.hass, entities=self.notify_entities,
                services=self.notify_services, message=message,
            )
            if result["failed"]:
                self._events([{
                    "type": "notification_failed", "targets": result["failed"],
                }])
        except Exception:
            _LOGGER.exception("Could not request Adaptive Alarm notification")

    async def _notify_events(self, events: list[dict[str, Any]]) -> None:
        """Send understandable, reason-specific alerts to selected phones."""
        for event in events:
            kind = event.get("type")
            if kind == "vibration_prealert":
                await self._notify_text(prealert_text(
                    event["zone"], event["protected_contact"],
                    self._friendly_name,
                ))
            elif kind == "triggered":
                await self._notify_text(trigger_text(
                    event.get("cause", "sconosciuta"),
                    self.vibration_zone_map, self._friendly_name,
                ))
            elif kind == "zone_fault":
                # The policy named "notify" means no auto-trigger on a
                # recovered-but-open contact; now also notify the phone
                # when a notification destination is configured.
                await self._notify_text(fault_text(
                    event["zone"], event["state"], self._friendly_name,
                ))

    async def _request_deterrent_lights(
        self, events: list[dict[str, Any]],
    ) -> str:
        """Explicit opt-in: activate only currently OFF light entities.

        Claims require a confirmed transition to ON. Lights already ON are
        never touched. Auto-off is separately opted in and fail-closed.
        """
        candidates = [e for e in events if e.get("type") == "vibration_prealert"]
        if not candidates:
            return ""
        if not self.deterrent_enabled or not self.deterrent_lights:
            return "non abilitate"
        async with self._guard:
            session = self.machine.session
            if (
                self.machine.phase != Phase.ARMED_AWAY
                or session is None
                or self.machine.deterrent_requested
            ):
                return "non richieste"
            if not any(
                e.get("protected_contact") in session.protected_zones
                and self.vibration_zone_map.get(e.get("zone")) == e.get("protected_contact")
                for e in candidates
            ):
                return "contatto non protetto"
            # Persist before physical actuation, never redo a request on restart.
            self.machine.deterrent_requested = True
            await self._store.async_save(self.machine.snapshot())
            lights_off = [
                light for light in self.deterrent_lights
                if self.hass.states.is_state(light, "off")
            ]
            if not lights_off:
                self._events([{"type": "deterrent_lights_already_on_or_unavailable"}])
                return "già accese o non disponibili"
            requested: list[str] = []
            failed: list[str] = []
            now = time.time()
            session_id = session.identifier
            for light in lights_off:
                baseline = self.hass.states.get(light)
                if baseline is None or baseline.state != "off":
                    continue
                try:
                    await self.hass.services.async_call(
                        "light", "turn_on", {"entity_id": light}, blocking=True,
                    )
                except Exception:
                    _LOGGER.exception("Deterrent light-on request failed: %s", light)
                    failed.append(light)
                    continue
                requested.append(light)
                if not self.deterrent_auto_off:
                    continue
                # The on request may return before the physical device
                # publishes its new state. Never assume success equals ON.
                pending = PendingLight(
                    entity_id=light,
                    baseline_updated=baseline.last_updated.isoformat(),
                    ack_deadline=now + LIGHT_ACK_TIMEOUT,
                    off_deadline=now + self.deterrent_off_delay,
                    episode=session_id,
                )
                current = self.hass.states.get(light)
                if current is None:
                    continue
                if current.state == "on":
                    # Synchronous state change; same strict confirmation as
                    # delayed OFF→ON events.
                    lease = confirm_transition(
                        pending, now=time.time(),
                        old_state=baseline.state,
                        old_updated=baseline.last_updated.isoformat(),
                        new_state=current.state,
                        new_updated=current.last_updated.isoformat(),
                        current_episode=session_id,
                    )
                    if lease is not None:
                        self._light_leases[light] = lease
                elif (
                    current.state == "off"
                    and current.last_updated == baseline.last_updated
                ):
                    # Wait for the independent light state event (max 15 s).
                    self._light_pending[light] = pending
                else:
                    self._events([{
                        "type": "deterrent_light_tracking_cancelled",
                        "light": light,
                    }])
            if self._light_leases:
                await self._light_store.async_save({
                    "leases": [v.to_dict() for v in self._light_leases.values()]
                })
            if failed:
                self._events([{"type": "deterrent_light_request_failed", "lights": failed}])
            if requested:
                self._events([{
                    "type": "deterrent_lights_requested", "lights": requested,
                    "auto_off": self.deterrent_auto_off,
                    "timeout_seconds": self.deterrent_off_delay if self.deterrent_auto_off else None,
                }])
            return ("accensione richiesta (" + ", ".join(requested) + ")"
                    if requested else "accensione fallita")

    async def _expire_deterrent_lights(self) -> None:
        """Conservatively turn off only owned, unmodified lights at deadline.

        Do not turn off during a triggered alarm, or within another armed
        episode. After reboot no claims are restored (manual inspection).
        """
        # A successful service request is not evidence of a state change.
        # Report pending lights that never confirmed ON within 15 seconds.
        expired_pending: list[str] = []
        async with self._guard:
            now = time.time()
            for entity, pending in list(self._light_pending.items()):
                if now >= pending.ack_deadline:
                    del self._light_pending[entity]
                    expired_pending.append(entity)
            if expired_pending:
                self._events([{
                    "type": "deterrent_light_tracking_unconfirmed",
                    "lights": expired_pending,
                }])
        if expired_pending:
            await self._notify_text(
                "Luci deterrenti: nessuna conferma di accensione in tempo "
                "per " + ", ".join(expired_pending) +
                ". Spegnimento automatico non eseguito: controlla le luci."
            )
        if not self._light_leases:
            return
        notices: list[str] = []
        events: list[dict[str, Any]] = []
        async with self._guard:
            if self.machine.phase == Phase.TRIGGERED:
                return
            now = time.time()
            session = self.machine.session
            episode = session.identifier if session and self.machine.phase == Phase.ARMED_AWAY else None
            for entity, lease in list(self._light_leases.items()):
                if now < lease.deadline:
                    continue
                state = self.hass.states.get(entity)
                allowed = may_turn_off(
                    lease, state=state.state if state else None,
                    last_updated=state.last_updated.isoformat() if state else None,
                    alarm_triggered=False, current_episode=episode,
                )
                del self._light_leases[entity]
                if not allowed:
                    events.append({
                        "type": "deterrent_light_off_skipped", "light": entity,
                        "reason": "state_changed_or_new_session",
                    })
                    notices.append(
                        f"Luci deterrenti: spegnimento automatico NON eseguito "
                        f"per {entity} (stato cambiato o nuova sessione). Controlla la luce."
                    )
                    continue
                try:
                    await self.hass.services.async_call(
                        "light", "turn_off", {"entity_id": entity}, blocking=True,
                    )
                except Exception:
                    _LOGGER.exception("Deterrent light-off request failed: %s", entity)
                    events.append({"type": "deterrent_light_off_failed", "light": entity})
                    notices.append(
                        f"Luci deterrenti: richiesta spegnimento FALLITA per {entity}."
                    )
                else:
                    events.append({"type": "deterrent_light_off_requested", "light": entity})
                    notices.append(
                        f"Luci deterrenti: richiesta spegnimento per {entity} "
                        f"dopo {self.deterrent_off_delay} secondi."
                    )
            if events:
                await self._light_store.async_save({
                    "leases": [v.to_dict() for v in self._light_leases.values()]
                })
                self._events(events)
        for message in notices:
            await self._notify_text(message)

    async def _refresh_faults(self) -> None:
        """Publish new non-closed protected contacts once per fault episode."""
        async with self._guard:
            if self.machine.phase not in (Phase.ARMED_AWAY, Phase.TRIGGERED) or self.machine.session is None:
                self._active_faults.clear()
                return
            snapshot = self._states()
            current = {
                zone for zone in self.machine.session.protected_zones
                if snapshot.get(zone) != ZoneState.CLOSED
            }
            newly_faulty = current - self._active_faults
            recovered = self._active_faults - current
            self._active_faults = current
            events = (
                [{"type": "protected_zone_abnormal", "zone": z, "state": snapshot[z].value}
                 for z in sorted(newly_faulty)]
                + [{"type": "protected_zone_recovered", "zone": z} for z in sorted(recovered)]
            )
            if events:
                self._events(events)

    async def async_tick(self) -> None:
        """Handle countdown and prealarm expiry; session zones remain frozen."""
        await self._apply(
            lambda: self.machine.tick(
                self._states(), locked=self._locked(), now=time.time(),
                vibration_window=float(
                    self.entry.options.get(
                        CONF_VIBRATION_WINDOW, DEFAULT_VIBRATION_WINDOW
                    )
                ),
            )
        )
        # Detect missed transitions, but never manufacture an intrusion after startup.
        await self._refresh_faults()
        await self._expire_deterrent_lights()

    async def async_arm(self) -> list[dict[str, Any]]:
        return await self._apply(
            lambda: self.machine.arm(
                self._states(), locked=self._locked(), now=time.time(),
                delay=int(self.entry.options.get(CONF_ARMING_DELAY, DEFAULT_ARMING_DELAY)),
            )
        )

    async def async_disarm(self) -> list[dict[str, Any]]:
        return await self._apply(self.machine.disarm)

    async def async_trigger(self) -> list[dict[str, Any]]:
        events = await self._apply(lambda: self.machine.trigger("manual_test"))
        await self._notify_events(events)
        return events
