# Controlled trial — no physical outputs

1. Leave your existing alarm installed as the only system with siren access.
2. Install this preview through HACS and add its six minimum entities.
3. Confirm readiness is OFF if any mandatory entry/lock/path requirement is missing and ON only when at least one route is valid.
4. Arm Away while both minimum paths are valid. Verify the panel displays Arming (default 60s), then Armed Away.
5. Open a secondary contact during arming and confirm it is excluded when commit happens. Open a protected contact: only the simulated panel transitions to Triggered, not any physical device.
6. Disarm, leave an extra window open, arm again, close it after arming; after five stable seconds it appears in the protected list. Reopen it and verify simulated trigger. Repeat with a 4.9s closure to check that it stays excluded.
7. Make a protected sensor unavailable and recover it open. Confirm a critical diagnostic event; test the alternative recovery policy only in simulation.
8. Add an optional vibration sensor, choose Balanced and produce two separated pulses; check the simulated prealarm and trigger. Repeat with the Cross and Cautious profiles and thunderstorm input.
9. Restart HA while armed and confirm the session ID, protected zone set and exclusions remain unchanged. Restart in Arming and confirm it does not silently continue the countdown.
10. Manually test the Trigger command, restart, then verify the triggered state resumes **without a physical siren**.
11. Inspect HA logs and the `adaptive_alarm_event` event stream. If an error occurs, remove/disable the preview rather than altering the production alarm.

This checklist is a proposed trial, **not a report that hardware tests have been performed**.
