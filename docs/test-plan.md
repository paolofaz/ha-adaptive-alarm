# Controlled trial — no physical outputs

1. Leave your existing alarm installed as the only system with siren access.
2. Install this preview through HACS and add its six minimum entities.
3. Confirm readiness is OFF if entry is open, lock is unlocked, or either sala OR bagno has no closed shutter/window. Verify separately all four allowed combinations: two shutters, two windows, sala window + bagno shutter, sala shutter + bagno window. Test `unknown`/`unavailable` as not closed.
4. Arm Away while any one of the four minimum paths is valid. Verify the panel displays Arming (default 60s), then Armed Away.
5. Open a secondary contact during arming and confirm it is excluded when commit happens. **The protection snapshot is taken at the end of the countdown, not when you press Arm.** Open a protected contact: only the simulated panel transitions to Triggered, not any physical device.
6. Disarm, leave an extra window open and arm. Check that it remains excluded after closure for 5 seconds, a minute or longer. Reopen it: **no simulated trigger**. Disarm, close that window, and arm again: it is now protected, and opening it causes a simulated trigger.
7. Make a protected sensor unavailable and recover it open. Confirm a critical diagnostic event; test the alternative recovery policy only in simulation.
8. In Configure → Options, pair a vibration sensor with a **specific** monitored contact. Arm with that contact excluded and generate repeated impulses: the simulation must **not** trigger. Then disarm, close that contact and rearm: two properly spaced pulses in Balanced must prealert then trigger. Try Cross, Cautious and the storm sensor. An unpaired sensor must not count.
9. Restart HA while armed and confirm the session ID, protected zone set and exclusions remain unchanged. Restart in Arming and confirm it does not silently continue the countdown.
10. Manually test the Trigger command, restart, then verify the triggered state resumes **without a physical siren**.
11. Inspect HA logs and the `adaptive_alarm_event` event stream. If an error occurs, remove/disable the preview rather than altering the production alarm.

This checklist is a proposed trial, **not a report that hardware tests have been performed**.
