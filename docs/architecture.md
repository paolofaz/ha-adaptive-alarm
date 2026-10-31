# Architecture and development plan

The integration will have **one** session state machine, not multiple
independent Home Assistant automations modifying a session registry.

## Contract

- Entry door contact = closed and entry lock = locked.
- At least one pair is closed: living+bath shutters OR living+bath windows.
- Unknown/unavailable readings never count as closed.
- Every available closed contact is included at arm time.
- An excluded contact can join after five stable seconds of closure.
- Protection is monotone during a session. Openings of protected contacts
  produce alarm events; offline recovery may notify or trigger by policy.
- Restart must not replace the previously protected set with a new snapshot.
- Disarm, arming, triggering, persistence and notifications must have explicit
  failure and concurrency semantics.

## Layers

1. **Domain policies** (`engine/`): immutable state and pure decisions.
2. **State machine** (future): one event queue with monotonic session updates,
   generation IDs, persistence, migration and fault reconciliation.
3. **Home Assistant adapter** (future): sensor subscriptions, alarm panel,
   configuration/options flow, storage, entities and diagnostics.
4. **Optional reactions** (future): user automations for lights and notifications.

## Next milestones

1. Full state machine and replayable event-sequence tests.
2. Storage format, recovery and interruption tests.
3. UI options: extra sensors, vibrations, thresholds, diagnostic policies.
4. Read-only diagnostic sensors.
5. Alarm panel in simulation mode (no physical outputs).
6. Physical actuators only after end-to-end tests and a written safe migration.

This preview includes only the pure policies and a config flow for minimum paths.
