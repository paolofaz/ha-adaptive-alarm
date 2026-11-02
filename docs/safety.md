# Safety — v0.11.0 RC1

## Real outputs

Only explicit opt-in real lighting is implemented: `light.turn_on` on the first valid protected vibration prealert, and a separately enabled conservative `light.turn_off` timer. Selected Home Assistant notify providers may also send push alerts.

- OFF by default; a user must explicitly select `light.` entities **and** enable the feature.
- Only while the machine is fully `armed_away` and a configured vibration sensor is linked to a contact included in the frozen protected session.
- Once per armed session, not on every edge; one concurrent disarm cannot make this trigger after disarming, because conditions are rechecked under the controller state guard.
- No brightness, color or flashing effects are sent. `light.turn_off` is restricted to safely owned, unchanged lights; it is suspended during a triggered alarm and skipped after HA restart.
- The event `deterrent_lights_requested` does **not** prove the light actually turned on.
- Do not select a light entity that operates a physical siren, dangerous relay or unsafe load.

**The siren remains completely inert.** No siren, switch, lock, RF or MQTT actuation is performed. Notifications are allowed only through explicitly configured HA notify entities/services and their success does not prove delivery. Do not connect the simulated event bus to physical sirens.

## Trigger conditions

- Each vibration sensor is linked to one actual physical protected contact. An open/excluded window can never be enabled via a closed shutter.
- A single hit produces a prealert. Only 2 or 3 hits from **the same sensor** in a short window produce a simulated intrusion alarm.
- Hits across different sensors never add together.
- The first hit can be caused by thunder, wind, impacts or ordinary movement. A light can therefore turn on spuriously when opted in.
- The new logic assumes replacement sensors that can report two independent `off → on` edges in time; Aqara DJT11LM typically cannot do this within 20 s.
- The old storm-grace and cross-sensor confirmation logic has been retired.
- Protected contact opening still causes the existing simulated trigger, independently of vibrations.

An empty protection rule set cannot arm. The exit countdown (60 s default) is not protection until the required routes are validated. Already-open Excluded contacts never dynamically re-enroll, but initially unreadable Pending contacts can join on their first CLOSED observation. Options changes are blocked during arming/armed/triggered; saved Protected zones persist over restart.

This is an early preview, **not a certified or operational security alarm**. Keep the existing physical security system in charge of any siren.

- The once-only deterrent lighting request is persisted in the restored alarm session to avoid repeating it after a Home Assistant restart.

## v0.6.0 — Push and automatic light-off safeguards

- Both push notifications and light auto-off are **separate disabled-by-default options**.
- Outbound messages use only explicitly configured Home Assistant `notify` entities/actions. Telegram Bot is configured and authorized in Home Assistant, not in Adaptive Alarm. Successful dispatch does not prove delivery.
- A prealert sends a notification regardless of lights being enabled. A confirmed trigger sends a separate notification; siren output remains permanently disabled.
- Real `light.turn_off` requests are authorized ONLY for lights that were OFF before Adaptive Alarm switched them on, subsequently confirmed ON, and have not had any `last_updated` change. Never turn off an already-ON light, a changed state, an unavailable light, or a light from another active armed episode.
- Automatic off remains suspended while the alarm is in the TRIGGERED state. Once disarmed, expiry may proceed if ownership evidence remains unchanged.
- HA restart / integration reload cancels pending ownership rather than guessing. Notification warns that lights may need manual shutdown. Some real lights report delayed changes and may therefore remain on: this is intentional and safer than turning off an unrelated light.
- Auto-off duration defaults to 120 s if separately enabled, adjustable between 15 and 3600 s; it cannot be enabled through the siren field. Light.turn_off is the only additional physical action in this version.
- Threshold 1 is explicitly forbidden by the engine. All tests must reject it.

## v0.6.2 — asynchronous light acknowledgement

Previous light turn-on service completion is not proof the light entity
is already reporting ON. Starting in v0.6.2, the controller watches
for up to 15 seconds for a verified state transition from the sampled OFF
state after its own activation request. Pending evidence by itself gives
NO authority to turn off a light. Only a confirmed ON lease that remains
unchanged until expiry may turn it OFF. A missing, reordered, delayed beyond
15 s, or conflicting transition causes a warning and never a blind OFF.
A successful request does not establish secure physical command provenance;
external manual changes can occur even during the acknowledgement window.
Sirens and switches still have zero actuation paths.

## v0.7.0 — persist protected vs pending vs excluded zones

A protected zone must survive `unavailable` and all HA/Z2M restarts; it
always triggers when its first returning valid value is OPEN, ignoring any old
`recovery_policy: notify` option. OFFLINE alone does not trigger or send
a phone push. Contact status may be diagnosed as degraded.

An UNKNOWN sensor when arming is not deemed safe: it enters Pending only when
all configured minimum requirements are already satisfied without it. Pending
contact CLOSED for the first time => protected; first OPEN => permanently
excluded. A sensor already OPEN at commit is permanently excluded as before.

Persist Pending and Protected atomically before events are published and
restore them without using transient Zigbee2MQTT availability as a new
insertion baseline. Existing v0.6.x stored sessions lacking the `pending_zones`
field retain their original exclusion set. A mandatory contact or minimum
group that cannot be covered without an unavailable sensor STILL blocks arm.
The old UI return-online policy is removed because the safer fixed behavior
cannot be downgraded. Siren remains entirely simulated.

## v0.8.0 — Diagnostics and protection editor

Health distinguishes `unknown`, `unavailable`, `missing`, `open` and
`unexpected` protected contact states. This never demotes a Protected sensor.
Both `unknown` and `unavailable` are unreadable for security. The unified
group editor remains blocked while a session is arming or active.

## v0.10.0 beta — trigger timeout and notification privacy

A timer controls the duration of the `triggered` **state** (default 300 s).
It does not activate a physical siren. On expiry the same protected session
is restored as `armed_away`; protected contacts that were still OPEN are
temporarily held until they return CLOSED and only then may trigger again.
This held-open set is persisted and is not the same as exclusion. A protected
contact that was closed and later opens continues to trigger even after HA/Z2M
outages. Timer deadlines persist across HA restarts. Upgrading an old
triggered snapshot starts a new full timeout instead of disarming silently.

Conservative deterrent-light OFF stays suspended after triggering until a
user disarms, including after an automatic return to armed_away. Any stale
light claims are invalidated on restart, as before.

All Home Assistant notification categories are independently controlled but
share the same optional recipient list and global switch. Apple Home native
notifications are not controlled by these switches. Reject notifications are
sent only for a real rejection (after the exit deadline or zero-delay check).
No RF, GPS presence, PIN, camera, LED, or physical siren actuation is added.

## v0.11.0 RC1 — input_boolean-only virtual siren

The RC allows an **explicitly opted-in virtual output**, validated strictly
as an existing `input_boolean.<id>` entity. ONLY the Home Assistant
`input_boolean.turn_on` and `input_boolean.turn_off` services may be used;
no `siren`, `switch`, RF, MQTT, script, lock or arbitrary service routing
is introduced. Default disabled. The previously configured physical siren
is inert metadata and cannot receive commands.

Requests are serialized with state changes and set `on` only while the
phase is `triggered`. Return to armed, manual disarm and startup recovery
request `off`. On restart, expired trigger deadlines are processed before
the virtual siren can be turned on. The helper state is checked before
issuing another command, and failures are logged and throttled with a
30-second retry delay. This is an **observability mechanism**, not a
physical siren driver.

Any user automation that connects this virtual helper to a physical
siren or other actuator would defeat this separation and MUST NOT be created.
Live siren control remains excluded until full field acceptance and a
fail-safe hardware adapter are separately reviewed.
