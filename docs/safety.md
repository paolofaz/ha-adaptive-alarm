# Safety — 0.4.0 alpha

The code is **simulation-only**, not an operational security system. Keep your existing physical alarm as the only controller of sirens or relays.

- The siren selection is optional **inert metadata only**; it never calls services.
- Leave the siren unselected during your trial. Do not bridge `adaptive_alarm_event` to real outputs.
- No RF code, credential, MQTT or lock services are implemented.
- Unknown/offline/missing required contacts are unsafe at the arming deadline.
- No configured mandatory contact and no alternative groups: arm always rejected.
- If your configured lock is unavailable or unlocked: arm rejected at the deadline.
- The exit countdown is **not** protection. An invalid deadline cancels the attempt.
- Adding/editing/removing rules during active or arming state is forbidden. Disarm first.
- An excluded contact stays excluded for the whole session, even if wind closes and reopens it.
- Configured vibration sensors must monitor the physical contact to which they are actually attached. Do not infer a window is protected when only a shutter is closed.
- Siren power, feedback, backup and event duplication have not been certified or tested on physical equipment.
