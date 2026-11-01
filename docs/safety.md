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
