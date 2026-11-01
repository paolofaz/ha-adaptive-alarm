# v0.4.0 — Generic protection configuration

The deterministic engine accepts `ProtectionRules`: a list of mandatory binary contacts, named groups of alternatives, optional contacts, optional lock and inert siren metadata.

Eligibility is **AND(mandatory) AND AND(OR(each alternative group)) AND lock-if-configured**; a configuration with zero mandatory contacts and zero groups cannot arm.

The session is snapshotted at the arming deadline; protected contacts never change until disarm. Protected opening triggers a simulated alarm; excluded opening does not. The state-machine/storage format is preserved. One controller serializes event processing and storage with an `asyncio.Lock`.

An existing v0.3.x configuration is mapped to a door requirement and Sala/Bagno OR groups; previous active-session route labels are reconciled, maintaining the protected set. Configuration changes are blocked while a session is active or during arming.

Native Options Flow pages configure mandatory contacts, lock, add/edit/remove OR group, optional contacts, vibration pairings, inert siren selector and timing/recovery settings.

**The siren entity is never passed to a service call.** Any later physical output adapter must require a separate explicit enablement, security checks and acceptance testing. The repository contains no RF codes.

## v0.5.0 vibration and light-only deterrence

Each accepted `off → on` edge is associated with exactly one linked physical contact. The frozen session's protected zone set gates acceptance. The engine maintains independent per-sensor histories and emits a single `vibration_prealert` on the first valid hit per sequence, `vibration_progress` when below a 3-hit threshold, and `triggered` only when 2 or 3 valid hits from the **same sensor** fall within the configurable rolling confirmation window. A different sensor cannot contribute to the count. Debounce remains per source, not global. Old cross-sensor profiles and storm grace have been removed.

Home Assistant adapter only subscribes to binary_sensor rising edges. Configured vibration links are an expandable list, with native Options Flow add/edit/remove and strict validation; existing legacy mappings are imported without re-pairing sources. For older accounts, the previous cautious profile maps to 3-hit threshold and other profiles to 2 until the new threshold is configured.

Lights can be an **explicit opt-in real output**; they are OFF by default and only `light.` entities can be selected. After `vibration_prealert` is durably processed by the engine, an independent guarded adapter re-checks the armed phase, the protected contact, sensor pairing and whether this session already requested lights, then makes a nonblocking `light.turn_on` request. It never sends `light.turn_off`. The siren is still unconditionally inert. Core engine remains pure Python and never controls devices.
