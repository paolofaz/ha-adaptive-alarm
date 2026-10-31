# Safety and testing boundaries

**Do not rely on the development preview for burglary protection.**

The current integration has no alarm entity, siren integration, sensor
subscriptions, lock commands, RF access or automatic arming.

The YAML prototype is a design reference, not evidence of production safety.

Before enabling any actuator in a future release:

- Test delayed arming, interruption, disarming and rearming.
- Test a sensor that becomes `unavailable`, recovers open and recovers closed.
- Test restart during arming, triggered state and state-store writes.
- Verify loss of power and loss of Home Assistant / Zigbee / Wi-Fi connectivity.
- Verify separate event handling so urgent actions do not wait for snapshots.
- Ensure only **one** controller can drive the siren.
- Isolate sirens during test and verify actual sounding in a controlled window.
- Never store static RF codes or other secrets in source control.
- Review guest access separately; fixed-code RF is replayable.

Future CI must exercise the runtime with Home Assistant test fixtures, not
merely pure-Python policy tests.
