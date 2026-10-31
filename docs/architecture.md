# Architecture — v0.3.1 alpha

## Boundaries

1. **Pure domain model** (`engine/model.py`, `policy.py` and `runtime.py`): deterministic state transitions, immutable session snapshot and an explicit recovery policy. Zero Home Assistant imports.
2. **Serialized Home Assistant adapter** (`controller.py`): one `asyncio.Lock` owns all state changes, reads real entity states, persists the session in Home Assistant's Store, publishes events and updates entity listeners.
3. **UI and entities**: config flow with five mandatory contacts and a lock, options flow for additional zones/vibrations, `alarm_control_panel` and read-only diagnostics. No physical outputs.
4. **Output adapters**: intentionally absent. An event is an observation, not a siren action.

### Minimum eligibility

`entry_contact_closed AND lock_locked AND (shutter_living_closed OR window_living_closed) AND (shutter_bath_closed OR window_bath_closed)`.

### State phases

`disarmed → arming → armed_away → triggered → disarmed`. Aborted arming returns to disarmed with fault detail. Invalid restored state enters `fault` (panel state unknown), never silently `disarmed`. An explicitly requested disarm clears the fault.

An exit-delay deadline is stored as a UTC epoch timestamp, and reconciliation is driven by a periodic timer. If Home Assistant restarts during the exit delay, it cancels the incomplete attempt; if it restarts while armed or triggered, it restores the same protected-zone set and reports problematic protected contacts without silently rebuilding the set.

### Storage

The Store document contains a versioned schema, phase, active session identifier, zone catalogue, protected set, initial route(s), arming deadline and fault text. The adapter serializes mutation and schedules storage before emitting state-change events. The state-machine internals do not invoke physical services. Current storage is **best effort**, not a tamper-proof transaction log.

### Event model

Physical contact updates and vibration impulses enter one controller under an async lock. Vibration is accepted only if its physical door/window contact is in the active session's protected set. Legacy freely paired and unpaired sensors are ignored until reconfigured using the location-specific fields. Every tick serializes with sensor events. **Zone membership is frozen at the end of the arming countdown:** contacts open or offline at commit stay excluded, even if later closed for hours. Previously excluded contacts only become protected after disarming and starting a new session. Restart restores the same saved zone set.

`adaptive_alarm_event` is diagnostic and must not be used as a real siren command until the actuation design and safety reviews are complete.

## Incomplete by design (future milestones)

- A user-configurable secure disarm policy for real deployment.
- More than three vibration/contact pairs and optionally one-to-many associations. Current three vibration slots require a specific protected contact per sensor.
- Siren output confirmation, tamper/power/battery supervision.
- Real-runtime Home Assistant fixtures, interrupted-store tests and startup races.
- A fully supervised migration away from the YAML package.
- RF guest access needs stronger security than the legacy static radio codes and is **not implemented**.

The current integration is useful for **safe behavioral trials** in parallel with the existing working alarm, not as its replacement.

### Exit-delay gate (v0.3.1)

- With a delay greater than zero, Arm Away enters `arming` regardless of the present readiness indication. The system is **not armed** during this countdown.
- At the deadline the entry contact must be closed, the lock must be locked, and one valid sala/bagno route must exist. If the requirements fail, abort and publish `arm_rejected` with diagnostic reasons. The panel remains disarmed and the failed requirement is exposed as `fault`.
- With delay zero, reject immediately when requirements fail. A valid request commits immediately.
- Arming cancelled by Disarm or interrupted by a Home Assistant restart must never silently activate later.

### Vibration placement (v0.3.1)

Sensor source options are exclusively `vibration_entry`, `vibration_window_living`, `vibration_window_bath`; their paired contacts are those configured in the original setup. No shutter mappings are allowed. Ignore old `vibration_1/2/3` options rather than silently rewire them. The engine accepts valid impulses only when the mapped contact is protected in the frozen session.
