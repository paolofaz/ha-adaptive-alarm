# Adaptive Alarm — v0.11.0 release candidate 1

Configurable Home Assistant intruder-alarm engine, with HACS support. **The physical siren remains disabled while the alarm state machine is operational**, and supports explicitly opted-in **real deterrent lighting** and **Home Assistant push notifications**. Sirens and locking hardware are still inert.

## Install and upgrade

1. HACS → custom repository `https://github.com/paolofaz/ha-adaptive-alarm` → Integration → Update/Redownload.
2. Restart Home Assistant. **Do not delete or recreate your existing integration.**
3. Settings → Devices & services → Adaptive Alarm → Configure. Options are saved section by section.
4. If this is a new installation, choose a name, then configure at least one mandatory contact or alternative group before arming.

The integration respects existing rules and frozen sessions from v0.3.x and v0.4.x.

## Minimum protection

- **Mandatory contacts**: ALL must be closed.
- **Mandatory alternative groups**: ALL groups must be satisfied; within each group, at least ONE contact must be closed. The existing setup migrates to mandatory entry contact + optional required lock + OR group Sala + OR group Bagno.
- **Optional contacts**: they never block arming. Contacts CLOSED when the countdown ends become protected. Contacts already OPEN stay excluded for that session. Contacts UNKNOWN/UNAVAILABLE become Pending and are enrolled if their first known state is CLOSED; otherwise they are excluded.
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
- **Historical v0.6.1 behavior (retired):** the old offline recovery choice `notify` vs `trigger` no longer exists. Since v0.7.0 a protected sensor returning OPEN always triggers a simulated alarm, even after restart.
- Timing fields have numeric inputs for debounce, confirmation window and the 2-or-3 threshold. Offline recovery is automatic, not a user-selectable option.
- No physical siren, switch, lock, RF or MQTT actions are added; lighting and push remain opt-in as in v0.6.0.

## v0.6.2 — delayed light-state acknowledgement bug fix

The v0.6.0–0.6.1 timer could leave lights on even when auto-off was enabled:
`light.turn_on` had completed, but the light entity could still be `off` at
the instant the integration checked its state. Because no ownership record
was created, no automatic light-off was subsequently scheduled.

Starting in v0.6.2, if the light was OFF before the integration's own
opt-in `light.turn_on` request, the adapter monitors its Home Assistant
state for up to **15 seconds**, including delayed `off → on` events.
Only a confirmed transition with the unchanged original OFF-state timestamp
creates a temporary auto-off lease. State change, different episode, no
confirmation within the window, or HA restart => **fail safe: do not send
light.turn_off**. On an unconfirmed timer, the integration emits
`deterrent_light_tracking_unconfirmed` and an optional phone notification.
The Health sensor exposes `deterrent_auto_off_enabled`,
`deterrent_lights_waiting_for_on` and
`deterrent_lights_awaiting_auto_off` for troubleshooting.

IMPORTANT: **light turn-on** and **automatic light turn-off** are two separate
settings. Auto-off is OFF by default, including after upgrading from v0.5.x.
If auto-off remains disabled, the light will correctly stay on by design.
With auto-off enabled, default timer is 120 seconds. Never delete your
integration entry to update; HACS update + Home Assistant restart suffices.

During a simulated alarm `triggered` the light-off timer remains suspended;
disarm to permit conservative cleanup. It is not possible to prove physical
actuation or perfect command ownership from HA state alone; users should
still supervise real light behavior.

## v0.7.0 — stable protection across Home Assistant / Zigbee2MQTT outages

An active alarm uses a **persisted session** with three distinct sets:

- **Protected:** closed when arming (or later explicitly enrolled from Pending).
  A protected contact NEVER loses protection when it goes unavailable, including
  during HA/Z2M restart. If it comes back **closed**, monitoring simply
  resumes. If it comes back **open**, **simulated alarm triggers immediately**
  and the phone notification names that contact. Previous `notify` versus
  `trigger` recovery policy is no longer selectable or applied.
- **Pending:** a contact was **unknown/unavailable at the instant arming
  completed**. Provided mandatory contacts and every required alternative group
  were already satisfied by other closed contacts, this one may join on its
  **FIRST reported closed state**. First reported open permanently excludes
  it for the episode. Pending survives HA restart; after joining, protection
  also survives HA restart.
- **Excluded:** a contact was **already open at arming**, or Pending first
  reported open. It stays excluded even if closed and later reopened. This
  protects the deliberate open-window / wind exception.

**Hard boundary:** a missing mandatory contact or an uncovered mandatory OR
group still REJECTS arming at the deadline; we never treat an unknown contact
as a closed minimum barrier. The lock requirement still applies. Existing
sessions saved by v0.6.2 are restored without inventing Pending entries
(previously excluded contacts remain excluded until next disarm/re-arm).

The panel and Health sensor now expose `pending_zones` in addition to
`protected_zones` and `excluded_zones`. Recoveries can emit
`zone_enrolled` and `zone_excluded` diagnostic events. Temporary offline
does not itself trigger or send a push. The Health sensor may show a degraded
state until connectivity is restored.

A restored protected contact that is already OPEN before the HA listener is
registered is detected by a post-start reconciliation and notified. Periodic
reconciliation also prevents lost state-change events from silently leaving
a protected zone open. Physical siren remains **inert**.

## v0.8.0 — unified group editor and Health diagnostics

Open **Configure → Required contacts and groups** to see existing groups in a single
native Home Assistant menu and manage required contacts, add groups, edit selected
groups (pre-filled current members) or delete them. Group controls have been
removed from the top-level menu. Changes are blocked while arming or armed.

Adaptive Alarm Health values:
- `ready`: disarmed; minimum requirements met.
- `not_ready`: disarmed; minimum requirements not met.
- `ok`: armed and all protected contact states are closed.
- `degraded`: armed, but at least one protected contact is not currently
  readable/closed. It does not drop monitoring or impose a fixed restart delay.
- `triggered`: simulated alarm triggered.
- `critical`: internal saved-session/configuration fault.

After restarting Home Assistant or Zigbee2MQTT, `degraded` can be normal for
a short time while protected sensors report `unknown` or `unavailable`.
Check the `protected_zone_problem_states` Health attribute for each affected
contact (`unknown`, `unavailable`, `missing`, `open`, `unexpected`). The attributes
`protected_zones_unreadable`, `protected_zones_open` and `pending_zones` provide
additional context. Pending contacts do not themselves cause `degraded`.

Both `unknown` and `unavailable` still count as unreadable in the alarm logic.
No siren, light, notification, threshold or session-policy behavior was changed
in this release.

## v0.9.1 — remove household presence automation from integration

The optional presence-mismatch checks introduced in v0.9.0 have been removed
from the integration. They belong in ordinary Home Assistant automations:
alerts when the alarm is armed while someone is home, or when the home is
certainly empty but the alarm is disarmed. No presence check, listener or
notification is configured or run by Adaptive Alarm after this update.

Existing HA `person` entities, presence helpers, locks and automations
are **never changed or deleted**. Earlier `presence_*` options are safely
ignored if they remain in stored config; unrelated protection, notifications,
and deterrent options are preserved. The one `armed_away` mode, protected /
pending / excluded zones and physical siren inertness are unchanged.

## v0.10.0 beta 1 — HomeKit-first notifications and timed alarm cycle

### HomeKit / iPhone

Keep exposing **only the existing `alarm_control_panel`** from Adaptive Alarm
through Home Assistant's HomeKit Bridge. No second panel, fake sensor, invented
HomeKit modes or new HomeKit dependency is required. The panel still supports
only `armed_away`; there is no night mode. Apple Home can continue handling
the family's normal armed/disarmed/triggered notifications. No PIN has been
introduced or changed in this beta.

**Configure → Phone notifications** is still the single source for Home
Assistant app/Telegram recipient destinations. The new **Configure →
Notification events** submenu allows separate switches for:
successful arming, disarming, triggering, rejected arming, vibration prealerts
and sensor fault events. On existing installations, triggered alerts, prealerts
and sensor faults keep their previous enabled default. Successful arming and
disarming default OFF to avoid duplicate Apple Home alerts; rejected arming
defaults ON (it cannot be reliably represented by HomeKit because the panel
remains disarmed). The global notifications switch still controls all
Home Assistant push delivery. HomeKit notifications are independent.

A rejected arming attempt reports the failing mandatory contacts, required OR
groups (with friendly member names) and configured lock when applicable.
Immediate zero-delay rejection and delayed rejection are both reported.

### Trigger expiry

**Configure → Timing** has a 30–3600 second triggered duration, default 300
seconds. When the timer expires, the panel returns from `triggered` to
`armed_away` without disarming or resetting the Protected/Pending/Excluded
session. Manual disarming always cancels the timer. The wall-clock deadline is
saved and restored through HA restarts; sessions stored by previous versions
without a deadline receive one full fresh period after startup.

Contacts still OPEN at timeout are held until they are next explicitly seen
CLOSED; only a subsequent new OPEN can trigger again, preventing repeated
alarms every second. Other sensors and optional Pending enrollment continue
normally. These held-open contacts **remain protected**, never become
Excluded. Once triggering occurred, the existing conservative deterrent-light
automatic OFF stays suspended until manual disarm, even after the timed
return to armed_away.

### Physical outputs and home automations

**Physical siren remains disabled**: the configured siren/switch is not
actuated. The timed triggered state is intended to support a future
separately reviewed siren safety adapter, not itself a real alarm sound.
Deterrent light opt-in behavior is unchanged.

Keep Shelly LED, household presence alerts, Telegram camera snapshots and
RF remote support in separate Home Assistant automations. Review RF
fixed-code replay risk and GPS-dependent automatic disarming before putting
a physical siren into service. Test this beta alongside the existing
operational alarm, not as a replacement.


## v0.11.0 RC1 — configuration overview and virtual siren acceptance

- **Required contacts and groups**: the main submenu and the mandatory
  contacts form list all the configured groups and their actual friendly
  sensor names, one group per line. Home Assistant translations contain actual
  newline characters instead of a literal `\\n` sequence; other option-page
  descriptions are corrected as well.
- **Vibration sensors**: the submenu now includes a read-only list of ALL
  configured sensor → actual monitored contact links, using Home Assistant
  friendly names. Adding/editing/removing links is unchanged.
- **Virtual siren test mode**: in **Configure → Physical siren and helper
  simulation**, you may separately enable the option **Virtual helper output**
  and select **only** an `input_boolean` helper. The physical siren/switch
  field remains **metadata only and never receives a service call**.
  The integration requests `input_boolean.turn_on` when an alarm enters
  `triggered`, and `input_boolean.turn_off` upon timed return to
  `armed_away` or an explicit disarm. After an HA restart it reconciles the
  current alarm phase with the helper; if the old trigger deadline already
  expired, it processes expiry before requesting any helper state. Failed
  requests emit `fake_siren_request_failed` with a 30-second retry interval.

### Create a safe siren simulator in Home Assistant

1. Go to **Settings → Devices & services → Helpers → Create helper → Toggle**.
   Name it **Sirena fittizia**, obtaining an entity such as
   `input_boolean.sirena_fittizia`. The default helper restore-state
   behavior is sufficient; Adaptive Alarm reconciles its state after startup.
2. In Adaptive Alarm **Configure → Sirena fisica e simulazione con helper**,
   do **not** use the original real siren switch for the simulated helper.
   Instead choose the newly created **input_boolean** and enable the separate
   virtual helper output switch. It is OFF by default on all installs.
3. Listen to state changes of the helper or build an ordinary HA automation
   with `input_boolean.sirena_fittizia` as trigger and your preferred
   `notify` action as its output. The ON and OFF state transitions mark
   when a physical siren *would* start and stop.
4. Test a simulated trigger and timed return after the configured duration.
   Test manual disarm and an HA restart while triggered. The phone may have a
   delivery delay, so use the helper state history as the timing reference.

**Safety rule:** Do not add an automation that copies the fake helper's ON
state to a real siren, switch, Shelly relay, MQTT device, or physical actuator.
Doing so defeats the safety boundary of this RC. The existing physical siren
must remain under the original alarm's sole control while both systems are
running in parallel. The old physical siren selection is still stored but
NEVER driven by the RC. Do not use the test output as a substitute for a
reviewed, independently fail-safe physical siren adapter.

HomeKit continues to receive the original `alarm_control_panel` states;
the virtual helper is a separate Home Assistant test indicator and need not
be exposed to Apple Home. Household presence, RF remotes, Shelly LED,
Telegram photographs, and generic scripts remain external automations.
