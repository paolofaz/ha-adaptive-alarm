# Adaptive Alarm 1.0 — operational safeguards

**Physical output remains OFF by default.** A real `siren` or `switch`
can be selected and enabled separately only after device-level testing.

The physical Zigbee2MQTT siren must have an independent automatic cutoff
verified on the device. The 300-second Home Assistant `triggered` timer and
the siren's independent cutoff are separate mechanisms; loss of HA/Z2M may
prevent any software OFF command from being delivered. A HA service call
returning successfully does not prove the Zigbee device acted.

On a new trigger the integration requests ON before push notifications.
On manual disarm, timeout or graceful unload it requests OFF, with
bounded retries if the device remains unavailable/ON. After HA restart an
already-triggered session is restored without an automatic re-send of ON,
preventing unexpected repeated siren sound. If your protection requirements
need sounding on restart, that needs a separate supervised design.

Mandatory contacts and one route per required alternative group must be
readable and closed to arm. Protected contacts never become excluded due to
temporary network interruptions. Pending optional contacts enroll only on
their first confirmed closed report. Contacts intentionally excluded at
commit remain excluded for the armed episode. Open protected contacts held
after trigger expiry remain protected and rearm only after they close.

A prealert requires a valid protected-contact vibration; two or three hits
from the same sensor are required for trigger. Deterrent lights have
independent explicit opt-in and safe ON/OFF ownership. After trigger,
light auto-off remains suspended until manual disarm.

The dashboard creation is noncritical and must not block the alarm.
No YAML automations, HomeKit configuration, RF remotes, Telegram photos,
locks or gates are edited by the integration. No PIN is added; external
presence automations and iPhone shortcuts must be secured independently.

The integration is community software and not a certified alarm panel.
Back up and test each physical action. Do not allow both the old YAML
system and Adaptive Alarm to command the same siren simultaneously.
