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
