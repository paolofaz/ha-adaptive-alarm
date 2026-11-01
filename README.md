# Adaptive Alarm — v0.6.0-alpha

Configurable Home Assistant intruder-alarm engine, with HACS support. **The alarm and siren remain simulated**, and supports explicitly opted-in **real deterrent lighting** and **Home Assistant push notifications**. Sirens and locking hardware are still inert.

## Install and upgrade

1. HACS → custom repository `https://github.com/paolofaz/ha-adaptive-alarm` → Integration → Update/Redownload.
2. Restart Home Assistant. **Do not delete or recreate your existing integration.**
3. Settings → Devices & services → Adaptive Alarm → Configure. Options are saved section by section.
4. If this is a new installation, choose a name, then configure at least one mandatory contact or alternative group before arming.

The integration respects existing rules and frozen sessions from v0.3.x and v0.4.x.

## Minimum protection

- **Mandatory contacts**: ALL must be closed.
- **Mandatory alternative groups**: ALL groups must be satisfied; within each group, at least ONE contact must be closed. The existing setup migrates to mandatory entry contact + optional required lock + OR group Sala + OR group Bagno.
- **Optional contacts**: they never block arming. Contacts closed at the end of the exit countdown become protected; contacts open/unavailable at the deadline stay excluded for the entire session, even if they later close.
- **Lock**: optional entity; if configured, it must be locked.

Exit delay defaults to 60 s. If positive, requirements are checked only at the deadline. With delay 0 they are checked immediately. The alarm is not armed during the countdown. Protected opening triggers a **simulated** alarm.

## Vibration sensor behavior (redesigned)

Go to **Configure → Vibration sensors** to **add, edit or remove any number** of sensor-to-contact pairs. Each vibration sensor must be linked to the *real contact* of the window/door where it is mounted; linking a vibration sensor to a closed shutter does not protect an open window. Existing sensor mappings are kept on upgrade.

The engine listens to binary sensor **`off → on` rising edges**. An individual sensor has an independent hit sequence:

- First valid hit on a **protected** contact → `vibration_prealert` immediately.
- **2 or 3 hits from the SAME sensor** within the configured confirmation window → simulated `triggered`.
- Hits from other sensors never add together, and never confirm the first sensor's hits. A second hit with threshold 3 emits `vibration_progress`.
- Contacts **excluded** at arming time cannot contribute vibration hits, even if the associated shutter is closed.
- Debounce prevents multiple edges too close together from counting. The configured confirmation window is checked by timer and on each new hit.

Default settings for new installations: **2 hits, 3-second debounce, 20-second window**. Configure threshold (2/3), debounce (1–20 seconds) and confirmation window (5–180 seconds) under **Configure → Timing**. Existing options for a 60-second confirmation window are retained until you edit them. Former `cross` profile and storm grace are **no longer applied**. A prior `cautious` or `cross` configuration maps to three hits from the **same sensor** unless you select a new threshold. This avoids silently making previous Cross settings more permissive.

**Hardware warning:** the Aqara DJT11LM is known to suppress repeat reports for about a minute, so two hits within 20 seconds cannot be expected. These rules target replacement sensors with demonstrated independent hit events roughly 5 seconds apart. Always test their actual Home Assistant binary sensor behavior before relying on detection.

## Opt-in deterrent lights (the ONLY real output)

Go to **Configure → Deterrent lights**:

1. Select one or more **`light.`** entities (do not select a siren or a switch).
2. Enable the explicit **Turn on deterrent lights at prealert** boolean. It is **OFF by default**.
3. After the alarm has fully armed and a vibration sensor linked to a *protected contact* raises its FIRST valid hit, the controller requests **`light.turn_on` at most once for that armed session (including across Home Assistant restarts)**. No later repeated prealerts keep sending commands.

These are **real Home Assistant light service calls**, unlike the simulated alarm. The new **safe auto-off** option is **separately disabled by default**, with an adjustable **120-second** default delay (15–3600 s). Only a light that was **off before the prealert**, was confirmed **on** after the integration's request and has **not subsequently changed state or attributes** may be turned off. A triggered alarm **holds the lights on** until disarmed. A Home Assistant restart invalidates ownership and skips auto-off with a warning instead of guessing. This is conservative: some lights may stay on if state acknowledgement is delayed or unavailable. Choose only lights you are comfortable switching on when the home is empty, not a siren proxy or unsafe relay. If light controls are disabled, **no light calls are made**.

The siren field remains optional and **inert metadata**; `siren.turn_on`, `switch.turn_on`, lock commands, RF and MQTT actuations are absent. Simulated `triggered` never activates the siren. Do not create user automations that drive a siren based on preview `adaptive_alarm_event` events.

## Diagnostics and safe trial

Listen to `adaptive_alarm_event` in Home Assistant Developer Tools → Events. New events include `vibration_prealert`, `vibration_progress`, `vibration_filtered`, `vibration_ignored`, `vibration_expired`, `deterrent_lights_requested`, `deterrent_light_request_failed` and `triggered`.

The old alarm YAML/hardware remains your **only operational physical alarm** during trials. Test one replacement vibration sensor before replacing all three. See [Safety](docs/safety.md), [Test plan](docs/test-plan.md) and [Architecture](docs/architecture.md).

## Tests

```sh
python -m unittest discover -s tests -v
```

GitHub CI also runs HACS and hassfest. Tests cannot establish physical sensor behavior or guarantee Home Assistant runtime compatibility.

## Phone notifications (new in v0.6.0)

**Configure → Phone notifications** is OFF by default, completely independent of enabling deterrent lights.

- To send to **Home Assistant Companion App**, select its existing **`notify.mobile_app_*` action** in the Notify actions field.
- To send to **Telegram Bot**, create/allowlist a chat in the **Telegram bot integration** first. It exposes a **`notify.*` entity** for each chat; select that entity in the Notify entities field. Older configured Telegram `notify.` actions are also supported.
- Other Home Assistant notify entities or notify services can be added. No direct Telegram API, chat IDs, API tokens or external HTTP integrations are stored in Adaptive Alarm.
- Enable notifications and save. Select **Send test notification** in Configure to request a harmless live message.
- A valid first vibration on a protected window sends a **prealarm** notification even if deterrent lights are disabled. A later **simulated trigger**, from repeated same-sensor vibration or protected contact opening, sends an **alarm** notification. Safe timer expiry, automatic-off skipped, failure and restart cancellation also generate messages where recipients are configured.
- Each target is requested independently. Successful `notify` service calls do **not** guarantee push delivery (phone could be offline). Missing or failing targets are reported in `adaptive_alarm_event` as `notification_failed`; other recipients continue.

**Only thresholds 2 or 3 are supported. A single vibration can NEVER trigger the alarm.**

All notification targets and lighting outputs default to disabled on existing installations. Reconfigure them explicitly after updating, and test one harmless light with the siren disconnected/inert.

## v0.6.1-alpha — clear diagnostics and notifications

- The **mandatory contacts** configuration form now also shows **every configured required alternative group** and its member contacts, using Home Assistant friendly names where available. This summary is read-only: use the separate group editor to change memberships. Do **not** list group contacts twice.
- Home Assistant push messages for **vibration prealerts** now name the protected physical contact (e.g. **Finestra Sala**) and the reporting vibration source (e.g. **Vibrazione Sala**), rather than showing raw `binary_sensor.*` IDs when a friendly name exists.
- **Simulated trigger notifications identify the cause**: opening of a protected contact, confirmed repeated vibration from a particular sensor and linked window, or manual test. Source IDs are preserved internally for diagnostics; only display text changes.
- **Offline contact faults** now also send phone notifications when external notifications are enabled. The offline recovery option **notify** means *report a recovered-but-open protected contact without triggering*, not "configure phone push". **trigger** means *raise simulated alarm if a protected contact returns online already open*. Ordinary `closed → open` on a protected contact still triggers regardless of this option.
- Timing fields have visible numeric inputs, with explanations for debounce, the hit confirmation window, the 2-or-3 threshold, and the offline-return policy. Recovery choices are localized in IT/EN while their stored identifiers remain unchanged.
- No physical siren, switch, lock, RF or MQTT actions are added; lighting and push remain opt-in as in v0.6.0.
