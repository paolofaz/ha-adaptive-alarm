# Adaptive Alarm 1.0 — architecture

## Pure engine

`engine.runtime.AlarmMachine` owns deterministic state transitions:
DISARMED → ARMING → ARMED_AWAY → TRIGGERED → ARMED_AWAY or DISARMED.
Session Protected/Pending/Excluded membership is persisted independently
of current transient Zigbee2MQTT availability. Required AND contacts,
alternative OR groups and optional lock are validated at arming deadline.
Per-source vibration reports cannot be aggregated across devices.

The triggered duration, cause and open-contact hold state survive HA
restarts. Contacts open at timeout remain Protected but are held until a
confirmed CLOSED report, preventing an alarm loop after rearming.

## Home Assistant adapter

`controller.AdaptiveAlarmController` serializes the machine state,
storage, events, notifications, lighting and siren commands using an
`asyncio.Lock`. It saves critical state before publishing events.
Outbound actions can fail without changing protected session membership.

Notifications are driven by six independent switches sharing one
recipient list. HomeKit consumes the standard `alarm_control_panel`;
its entity identity is unchanged on upgrades.

The physical siren adapter is disabled by default. The configuration UI
selects native `siren.*` entities; existing `switch.*` configurations are
still accepted internally for backwards compatibility. A fresh trigger requests
ON before other side effects. Disarm, trigger expiry and graceful unload
request OFF. No physical ON is replayed after a restored TRIGGERED state.
The device independent auto-off must be configured outside the integration.

Deterrent lights may be turned on once per armed session and turned off
only after conservatively confirmed ownership; they are not physical sirens.

## Lovelace

`frontend.async_register_card` serves a versioned JavaScript custom card.
For storage-managed resources it registers/updates the module URL through
Lovelace resource collection. YAML-managed resources require a one-time
`lovelace.resources` entry in the user's configuration. It never edits YAML,
does not install dashboards, and is independent from the alarm engine.

`www/adaptive-alarm-card.js` renders a read-only, entity-driven card using
the current panel attributes; dynamic entity labels use DOM `textContent`
instead of HTML to avoid injection. The card requires only one `type:`
declaration in the existing dashboard.

## Integration boundary

Adaptive Alarm never administers HomeKit, presence, locks, gate scripts,
Sonoff RF MQTT commands, LED effects or Telegram camera snapshots.
All these are user-owned HA automations. The migration guide documents
what old YAML alarm logic should be disabled when the new owner is active.
