# Safety / security boundaries

This is **v0.3.0 alpha, SIMULATION ONLY**.

- No service calls to sirens, lights, relays, locks, MQTT, Telegram or notifications.
- RF guest unlock/disarm is not implemented; never upload personal codes.
- The alarm control panel is for simulation. It does not protect the house, and can be disarmed through Home Assistant without a PIN. Do not confuse this with a certified or hardened alarm.
- Keep the existing YAML-based alarm as the sole physical controller; never have two active programs driving the same siren.
- Physical sensor states are only as reliable as the underlying radios, integrations and power supply.
- Restoring the session after a crash does not prove when a physical opening actually happened while Home Assistant was down. The controller emits diagnostics instead of falsely reporting an intrusion.
- An event bus consumer that you create yourself could still command a siren. Do **not** create one for this preview.
- Do not upload `.storage`, secrets, `configuration.yaml` with credentials, individual household configuration, RF payloads or private tokens to issues.

The integration is not evaluated or certified as a security system. Before a future operational release: integration tests on supported Home Assistant versions, hardware watchdog checks, secure disarm authorization, backup and rollback validation, and a complete end-to-end failure-mode review are necessary.

- A sensor open or unavailable at the arming commit remains **excluded** throughout the session, regardless of later closures. This prevents wind-induced false alarms, but the contact is **not monitored for openings** until the next disarm and re-arm. Review the excluded-zone list.

- A vibration sensor counts only when explicitly paired to a contact that is protected in the frozen session. Map sensors to the contact they physically monitor; never guess mappings.
- The minimum arming condition admits mixed sala/bagno pairs. Door contact closed and door lock locked are always required.
