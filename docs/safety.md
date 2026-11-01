# Safety — v0.5.0 alpha

## Real outputs

**Only one type of physical output is implemented:** an opt-in `light.turn_on` request on the first valid protected vibration prealert.

- OFF by default; a user must explicitly select `light.` entities **and** enable the feature.
- Only while the machine is fully `armed_away` and a configured vibration sensor is linked to a contact included in the frozen protected session.
- Once per armed session, not on every edge; one concurrent disarm cannot make this trigger after disarming, because conditions are rechecked under the controller state guard.
- No brightness, color or flashing effects are sent. No `light.turn_off`; lights remain on after disarm, expiry, HA restart or simulated trigger.
- `light.turn_on` is sent as a nonblocking request; the event `deterrent_lights_requested` does **not** prove the physical device responded.
- Do not select a light entity that operates a physical siren, dangerous relay or unsafe load.

**No other output is implemented.** The optional siren is **still inert**. No siren, switch, lock, RF, MQTT or notify services are invoked by this preview. Do not use the preview event bus for physical alarm actuation.

## Trigger conditions

- Each vibration sensor is linked to one actual physical protected contact. An open/excluded window can never be enabled via a closed shutter.
- A single hit produces a prealert. Only 2 or 3 hits from **the same sensor** in a short window produce a simulated intrusion alarm.
- Hits across different sensors never add together.
- The first hit can be caused by thunder, wind, impacts or ordinary movement. A light can therefore turn on spuriously when opted in.
- The new logic assumes replacement sensors that can report two independent `off → on` edges in time; Aqara DJT11LM typically cannot do this within 20 s.
- The old storm-grace and cross-sensor confirmation logic has been retired.
- Protected contact opening still causes the existing simulated trigger, independently of vibrations.

An empty protection rule set must never arm. A 60-second exit countdown is not protection until commit; if minimum requirements fail then the alarm remains disarmed. Excluded sensors never dynamically re-enroll. Changes to options are rejected while arming/armed/triggered. Saved protected zones persist across restarts.

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
