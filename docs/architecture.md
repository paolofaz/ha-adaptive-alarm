# Architecture — v0.2.0 alpha

## Boundaries

1. **Pure domain model** (`engine/model.py`, `policy.py` and `runtime.py`): deterministic state transitions, immutable session snapshot and an explicit recovery policy. Zero Home Assistant imports.
2. **Serialized Home Assistant adapter** (`controller.py`): one `asyncio.Lock` owns all state changes, reads real entity states, persists the session in Home Assistant's Store, publishes events and updates entity listeners.
3. **UI and entities**: config flow with five mandatory contacts and a lock, options flow for additional zones/vibrations, `alarm_control_panel` and read-only diagnostics. No physical outputs.
4. **Output adapters**: intentionally absent. An event is an observation, not a siren action.

### Minimum eligibility

`entry_contact_closed AND lock_locked AND ((shutter_living_closed AND shutter_bath_closed) OR (window_living_closed AND window_bath_closed))`.

### State phases

`disarmed → arming → armed_away → triggered → disarmed`. Aborted arming returns to disarmed with fault detail. Invalid restored state enters `fault` (panel state unknown), never silently `disarmed`. An explicitly requested disarm clears the fault.

An exit-delay deadline is stored as a UTC epoch timestamp, and reconciliation is driven by a periodic timer. If Home Assistant restarts during the exit delay, it cancels the incomplete attempt; if it restarts while armed or triggered, it restores the same protected-zone set and reports problematic protected contacts without silently rebuilding the set.

### Storage

The Store document contains a versioned schema, phase, active session identifier, zone catalogue, protected set, initial route(s), arming deadline and fault text. The adapter serializes mutation and schedules storage before emitting state-change events. The state-machine internals do not invoke physical services. Current storage is **best effort**, not a tamper-proof transaction log.

### Event model

Physical contact updates and vibration impulses enter one controller under an async lock. Every tick serializes with sensor events. A five-second pending closure can be admitted during a physical opening without waiting for the scheduled timer; a zone opened before five seconds stays excluded.

`adaptive_alarm_event` is diagnostic and must not be used as a real siren command until the actuation design and safety reviews are complete.

## Incomplete by design (future milestones)

- A user-configurable secure disarm policy for real deployment.
- Explicit associations between vibrations and physical zones.
- Siren output confirmation, tamper/power/battery supervision.
- Real-runtime Home Assistant fixtures, interrupted-store tests and startup races.
- A fully supervised migration away from the YAML package.
- RF guest access needs stronger security than the legacy static radio codes and is **not implemented**.

The current integration is useful for **safe behavioral trials** in parallel with the existing working alarm, not as its replacement.
