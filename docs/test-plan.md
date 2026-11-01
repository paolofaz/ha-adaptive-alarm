# Generic protection alpha — safe test plan

Leave the old hardware-controlling YAML alarm disarmed while physically opening its contacts. **Do not connect the simulated event bus to a siren.**

1. After HACS update to v0.4.0 and restart, confirm the existing user's rules were preserved: mandatory porta, lock and Sala/Bagno alternative groups.
2. Open Configure → Mandatory. Check the mandatory contacts and optional lock; the old values should be prefilled. Reopen Configure to review groups or add a new one.
3. Verify your four Sala/Bagno combinations and verify readiness turns off if the door or optional lock is unsecured.
4. With a positive exit delay, press Arm while the door is still open; close and lock it before the deadline. If requirements then hold, Armed Away is shown. Otherwise, arm is rejected with details in `fault`.
5. Verify every closed contact is protected at commit and excluded contacts stay excluded, even after closing and reopening (wind case).
6. In a separate test profile/installation, configure one mandatory front door and optional windows, **without groups or lock**, and verify it can arm. Empty rules must never arm.
7. Add a new alternative group and edit it using the same group name; after disarming, removing it must change readiness as expected.
8. With a vibration sensor associated with its actual window contact, ensure a window excluded at arm time ignores impulses, even if its shutter happens to be closed.
9. In Options → Siren, leave empty. If you deliberately select a test siren entity for UI verification, **confirm that no physical action is sent** on trigger. Do not try this against your physical siren.
10. Restart while armed (simulation only), confirm the protected zone set is restored exactly and never recreated from current sensor states.
11. Try editing configuration while Arming/Armed Away/Triggered: the change must be refused until Disarm.

These steps have not been executed on your actual HA runtime. GitHub CI only covers Python unit tests, manifest checks, HACS and hassfest.

## v0.5.0: new per-source vibration and light deterrence

1. Leave **Deterrent lights OFF** and any siren unconfigured for initial tests. Choose a replacement vibration sensor known to publish separate rising edges every ~5 s; do not expect DJT11LM to do this.
2. Open Configure → Vibrations → Add, and pair one sensor to its real door/window contact. Repeat with 4+ dummy/test sensors if needed to verify the menu scales. Test Edit and Remove only when disarmed.
3. Under Timing, choose threshold 2, debounce 3 s, window 20 s. Arm while the linked window is closed; verify its contact is included in the frozen protected zone set.
4. Generate one real impulse: exactly one `vibration_prealert`, panel remains `armed_away`. A second `off → on` edge after at least 3 s and before 20 s from the first should produce simulated `triggered`.
5. Disarm, re-arm; choose threshold 3. One impulse = prealert, second = `vibration_progress`, third = simulated trigger. Different sensors must **never** help reach the threshold.
6. With the linked window OPEN at insertion, confirm impulses are ignored regardless of its shutter. Close and re-open the window later: it remains excluded.
7. Confirm a debounce-rejected edge and an expired sequence do not trigger; wait 20 s after a prealert and confirm the next edge creates a fresh prealert.
8. **Only if you explicitly want a real light test:** choose a harmless test `light.` entity, enable the Deterrent lights toggle, and arm. The first valid prealert should request one `light.turn_on`; subsequent hits should not repeat it. Disarming or triggering should **not** turn the light off. Turn it off manually afterward.
9. Verify the chosen siren never activates. **Do not configure or select a physical siren for these tests.** No switch, lock or RF actuation is permitted.
10. Restart HA and verify the frozen zone set is restored, with no automatic light activation at boot.

This checklist is a plan for your on-site testing, not a report of physical tests performed.
