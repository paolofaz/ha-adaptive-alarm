# Architecture — v0.11.0 RC1 (adaptive protection)

The deterministic engine accepts `ProtectionRules`: a list of mandatory binary contacts, named groups of alternatives, optional contacts, optional lock and inert siren metadata.

Eligibility is **AND(mandatory) AND AND(OR(each alternative group)) AND lock-if-configured**; a configuration with zero mandatory contacts and zero groups cannot arm.

A session is persisted at the arming deadline in Protected, Pending and Excluded sets. Protected contacts stay protected across `unknown` / `unavailable` and HA/Z2M restarts; an OPEN return triggers simulated alarm. Pending contacts (initially unreadable) may join Protected only on their first CLOSED state. A first OPEN excludes them permanently for that session. Contacts already OPEN at arming stay excluded. The controller serializes transitions and storage with an `asyncio.Lock`.

An existing v0.3.x configuration is mapped to a door requirement and Sala/Bagno OR groups; previous active-session route labels are reconciled, maintaining the protected set. Configuration changes are blocked while a session is active or during arming.

The native Options Flow has a unified Required contacts and groups submenu: edit mandatory/lock, add a group, select and edit a group, or remove a group. Other pages configure optional contacts, vibration mappings, inert siren metadata, timing, notifications and opt-in lights. The obsolete `notify`/`trigger` recovery choice is not offered.

**The siren entity is never passed to a service call.** Any later physical output adapter must require a separate explicit enablement, security checks and acceptance testing. The repository contains no RF codes.

## v0.5.0 vibration and light-only deterrence

Each accepted `off → on` edge is associated with exactly one linked physical contact. The frozen session's protected zone set gates acceptance. The engine maintains independent per-sensor histories and emits a single `vibration_prealert` on the first valid hit per sequence, `vibration_progress` when below a 3-hit threshold, and `triggered` only when 2 or 3 valid hits from the **same sensor** fall within the configurable rolling confirmation window. A different sensor cannot contribute to the count. Debounce remains per source, not global. Old cross-sensor profiles and storm grace have been removed.

Home Assistant adapter only subscribes to binary_sensor rising edges. Configured vibration links are an expandable list, with native Options Flow add/edit/remove and strict validation; existing legacy mappings are imported without re-pairing sources. For older accounts, the previous cautious profile maps to 3-hit threshold and other profiles to 2 until the new threshold is configured.

Lights can be an **explicit opt-in real output**; they are OFF by default and only `light.` entities can be selected. After `vibration_prealert` is durably processed by the engine, an independent guarded adapter re-checks the armed phase, the protected contact, sensor pairing and whether this session already requested lights, then requests `light.turn_on`. Separately enabled safe light auto-off can request `light.turn_off` only after confirmed ownership, never for already-on/changed lights, and not while triggered. A restart invalidates ownership. The siren is still unconditionally inert; the core engine remains pure Python.

## Health diagnosis

Health reports `degraded` while protected contacts are unreadable, including
`unknown`, `unavailable`, or missing HA state after reboot. The report is
observational: it cannot change Protected/Pending/Excluded membership. A
separate pure helper preserves the raw diagnosis while the security policy
normalizes unknown and unavailable to the same unreadable domain state.

## v0.10.0 beta — timed trigger lifecycle and external automations

`triggered_until` (UTC epoch seconds), `trigger_cause`,
`held_open_zones` and `deterrent_hold_after_trigger` are persisted in
the state-machine snapshot. On triggering, the configured duration gives a
fixed wall-clock expiry; on timeout, the machine re-enters `armed_away`
without allocating a new session. Open protected contacts are held until a
valid CLOSED observation. On contact closure the hold is removed, so the
next OPEN can trigger. The held-open set is **not** the excluded set.
Other protected contacts continue being checked and remain protected across
startup and unknown/unavailable transitions.

A v0.9.1 triggered snapshot missing the deadline starts a new full configured
duration on the first tick after restart, preserving safety and compatibility.

Notification event gates live exclusively in the HA controller. They affect
outbound requests, not the state machine's event bus or Apple Home notifications.
One shared recipient list and global notify opt-in remain in place.
The HomeKit Bridge consumes the original `alarm_control_panel` unchanged;
there is still only the `armed_away` arming mode and no integration-level PIN.
Shelly LED, presence, Telegram photos and any RF handling stay external to
this engine. The physical siren is inert.

## v0.11.0 RC1 — rendering and simulated siren

`group_summary` accepts optional per-group line separation and prefix;
`vibration_summary` renders friendly sensor-to-contact links. The Options
Flow provides these through `description_placeholders` without altering
stored rules. Italian and English translations use real newlines rather
than literal backslash-n sequences.

An independently opted-in `input_boolean` output provides phase-cycle
observability. The config flow and adapter both validate its domain with
`engine.fake_siren.validate_fake_siren_helper`. A dedicated guarded
`_sync_fake_siren_state` maps TRIGGERED → on and other phases → off,
serialized against alarm commits. The adapter never routes the existing
physical siren metadata to an output. Only selected `input_boolean`
actions are called, with a throttled recovery path for unavailable helpers.
HomeKit consumes the existing alarm panel unchanged.
