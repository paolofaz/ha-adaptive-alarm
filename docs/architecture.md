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

The physical siren adapter is disabled by default and accepts only
configured `siren` or `switch` entity domains. A fresh trigger requests
ON before other side effects. Disarm, trigger expiry and graceful unload
request OFF. No physical ON is replayed after a restored TRIGGERED state.
The device independent auto-off must be configured outside the integration.
A separate `input_boolean` indicator can follow alarm phase.

Deterrent lights may be turned on once per armed session and turned off
only after conservatively confirmed ownership; they are not physical sirens.

## Lovelace

`dashboard.build_dashboard` generates a standard built-in-card dashboard
without any custom frontend JS. On initial setup, `async_ensure_dashboard`
creates a dedicated Lovelace storage dashboard `adaptive-alarm` once,
using registered entity IDs, and does not overwrite an existing one.
Dashboard creation failures are nonfatal. Home Assistant's internal
Lovelace collection API may vary between releases; installation is
best-effort and should be checked after upgrades.

## Integration boundary

Adaptive Alarm never administers HomeKit, presence, locks, gate scripts,
Sonoff RF MQTT commands, LED effects or Telegram camera snapshots.
All these are user-owned HA automations. The migration guide documents
what old YAML alarm logic should be disabled when the new owner is active.
