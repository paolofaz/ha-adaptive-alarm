# v0.4.0 — Generic protection configuration

The deterministic engine accepts `ProtectionRules`: a list of mandatory binary contacts, named groups of alternatives, optional contacts, optional lock and inert siren metadata.

Eligibility is **AND(mandatory) AND AND(OR(each alternative group)) AND lock-if-configured**; a configuration with zero mandatory contacts and zero groups cannot arm.

The session is snapshotted at the arming deadline; protected contacts never change until disarm. Protected opening triggers a simulated alarm; excluded opening does not. The state-machine/storage format is preserved. One controller serializes event processing and storage with an `asyncio.Lock`.

An existing v0.3.x configuration is mapped to a door requirement and Sala/Bagno OR groups; previous active-session route labels are reconciled, maintaining the protected set. Configuration changes are blocked while a session is active or during arming.

Native Options Flow pages configure mandatory contacts, lock, add/edit/remove OR group, optional contacts, vibration pairings, inert siren selector and timing/recovery settings.

**The siren entity is never passed to a service call.** Any later physical output adapter must require a separate explicit enablement, security checks and acceptance testing. The repository contains no RF codes.
