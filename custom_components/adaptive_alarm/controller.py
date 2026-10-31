"""Home Assistant adapter for a serialized, dry-run alarm machine.

This module deliberately NEVER invokes light, switch, siren, lock, notify or
MQTT services. It observes physical entities and emits diagnostic events only.
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
    CONF_VIBRATION_DEBOUNCE, CONF_VIBRATION_PROFILE, CONF_VIBRATION_SENSORS,
    CONF_VIBRATION_WINDOW, CONF_WINDOW_BATH, CONF_WINDOW_LIVING,
    DEFAULT_ARMING_DELAY, DEFAULT_RECOVERY_POLICY, DEFAULT_VIBRATION_DEBOUNCE,
    DEFAULT_VIBRATION_PROFILE, DEFAULT_VIBRATION_WINDOW, DOMAIN, EVENT_ADAPTIVE_ALARM,
)
from .engine import MinimumPaths, RecoveryPolicy, ZoneState, evaluate_eligibility
from .engine.runtime import AlarmMachine, Phase

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
        self.paths = MinimumPaths(
            entry=d[CONF_ENTRY_CONTACT],
            shutters=(d[CONF_SHUTTER_LIVING], d[CONF_SHUTTER_BATH]),
            windows=(d[CONF_WINDOW_LIVING], d[CONF_WINDOW_BATH]),
        )
        self.lock_entity = d[CONF_ENTRY_LOCK]
        extra = set(entry.options.get(CONF_EXTRA_CONTACTS, []))
        self.zones = frozenset({
            self.paths.entry, *self.paths.shutters, *self.paths.windows, *extra
        })
        self.vibrations = frozenset(entry.options.get(CONF_VIBRATION_SENSORS, []))
        self.storm_entity = entry.options.get(CONF_STORM_SENSOR)
        self.machine = AlarmMachine(self.paths, self.zones)
        self._store: Store[dict[str, Any]] = Store(
            hass, 1, f"{DOMAIN}.{entry.entry_id}"
        )
        self._guard = asyncio.Lock()
        self._remove_callbacks: list[Any] = []
        self._active_faults: set[str] = set()

    @property
    def signal(self) -> str:
        """Dispatcher update signal scoped to this config entry."""
        return f"{DOMAIN}_{self.entry.entry_id}_update"

    def _states(self) -> dict[str, ZoneState]:
        return {zone: _contact_state(self.hass.states.get(zone)) for zone in self.zones}

    def _locked(self) -> bool:
        return self.hass.states.is_state(self.lock_entity, "locked")

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
        if recovery:
            _LOGGER.warning("Adaptive Alarm restart: %s", recovery)
        # Observe contacts and optional vibrations from one shared listener.
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
            await self._apply(
                lambda: self.machine.observed(
                    zone, previous, current, now=now, recovery_policy=policy
                )
            )
            await self._refresh_faults()
        elif zone in self.vibrations and getattr(new_state, "state", None) == "on" and getattr(old_state, "state", None) == "off":
            await self._apply(
                lambda: self.machine.vibration(
                    zone, now=now,
                    profile=self.entry.options.get(
                        CONF_VIBRATION_PROFILE, DEFAULT_VIBRATION_PROFILE
                    ),
                    debounce=float(self.entry.options.get(
                        CONF_VIBRATION_DEBOUNCE, DEFAULT_VIBRATION_DEBOUNCE
                    )),
                    window=float(self.entry.options.get(
                        CONF_VIBRATION_WINDOW, DEFAULT_VIBRATION_WINDOW
                    )),
                    storm=bool(
                        self.storm_entity and self.hass.states.is_state(
                            self.storm_entity, "on"
                        )
                    ),
                )
            )
        elif zone == self.lock_entity and self.machine.active:
            if getattr(new_state, "state", None) != "locked":
                await self._apply(
                    lambda: [{"type": "lock_fault", "state": getattr(new_state, "state", None)}]
                )

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
        """Handle countdown, inclusion deadlines, and prealarm expiry."""
        await self._apply(
            lambda: self.machine.tick(
                self._states(), locked=self._locked(), now=time.time()
            )
        )
        # Detect missed transitions, but never manufacture an intrusion after startup.
        await self._refresh_faults()

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
        return await self._apply(lambda: self.machine.trigger("manual_test"))
