# Adaptive Alarm

**Home Assistant security integration — v1.0.1**

Adaptive Alarm manages a protected home using configurable required contacts,
alternative groups, optional contacts and per-window vibration sensors.
It exposes one standard Home Assistant `alarm_control_panel`, compatible
with the HomeKit Bridge, and supports a separate optional Zigbee siren output.

The project is designed for homes where the opening and closing of windows
and shutters should not be treated identically: for example, a room can
be secured by its **closed window OR closed shutter**, while the entry door
must always be closed.

## At a glance

- **Arming:** one `armed_away` mode. During the exit delay (default 60 seconds)
  the system remains in `arming`; requirements are validated at the end.
  If validation fails, arming is refused with specific reasons.
- **Required contacts:** all configured mandatory contacts must be closed.
- **Alternative groups:** each group must have at least one closed contact.
  A configuration with no minimum requirements cannot arm.
- **Optional contacts:** closed at arming become Protected; already open become
  Excluded for that session. Initially unreadable optional contacts are Pending:
  their first confirmed closed state enrolls them, otherwise they are excluded.
- **Protected contacts remain protected** through Home Assistant or Zigbee2MQTT
  outages. Reconnection in an open state triggers an alarm; temporary
  unavailable status alone does not.
- **Vibration sensors:** each source is linked to the real physical contact.
  First valid hit emits a prealert; 2 or 3 hits **from the same sensor** within
  the chosen window trigger the alarm. Different sensors are not added together.
- **Triggered state:** lasts 30–3600 seconds (default 300), then returns to
  `armed_away` while preserving the protected session. Contacts still open
  must close before a subsequent opening can trigger again.
- **Deterrent lights:** optional `light` entities may turn on at prealert.
  Separate, conservative automatic-off requires explicit enablement.
  The integration will not blindly turn off a light that was already on,
  manually changed or no longer owned.
- **Notifications:** one shared list of Home Assistant notification recipients,
  plus six independent event switches: armed, disarmed, triggered, rejected,
  vibration prealert and sensor anomalies.
- **Siren:** native Zigbee2MQTT `siren.*` entities can be configured with
  a dedicated physical output switch, **OFF by default**. Independently
  configured hardware cutoff is strongly recommended.
- **Lovelace card:** a compact `custom:adaptive-alarm-card` displays alarm
  state, protected/pending/excluded sensors and diagnostics inside your
  **existing dashboard**. No new dashboard is created.

## Installation / upgrading

1. In **HACS**, add this repository as a Custom repository of type
   **Integration**: `https://github.com/paolofaz/ha-adaptive-alarm`.
2. Install or update **Adaptive Alarm**, then restart Home Assistant.
3. Navigate to **Settings → Devices & services → Adaptive Alarm → Configure**.
4. Configure required contacts and groups, optional contacts, vibration
   associations, timing and notifications.
5. Add the reusable Adaptive Alarm card to your existing YAML dashboard (see the Lovelace section).

**Existing users:** never delete and recreate the integration to upgrade.
The same config entry, entity unique IDs, options and protected session are
retained. The optional Lovelace resource is independent from alarm operation.

## Configuration details

### Required contacts and groups

Use **Configure → Required contacts and groups** to manage mandatory AND
contacts and alternative OR groups. A room with two alternatives needs one
closed alternative at the end of the exit delay. The menu and mandatory form
display the current groups, with Home Assistant friendly names.

If a lock is configured, it must report `locked` at the arming deadline.
Adaptive Alarm observes it; it never locks or unlocks the door.

### Vibration, deterrence and notifications

Use **Vibration sensors** to create a source → actual mounted contact mapping.
The menu lists every configured association. A source on an excluded contact
cannot trigger the alarm. With newer sensors, use 2 or 3 confirmed hits from
the same sensor and test their actual Zigbee report cadence: some older Aqara
devices suppress repeated impulses for around a minute.

The deterrent-light output is distinct from the siren. Choose only safe
`light` entities, enable ON at first valid prealert, and separately enable
automatic OFF if desired. Safe OFF is suspended after triggering until manual
disarm and may be skipped if HA cannot verify ownership.

In **Phone notifications**, choose the HA Companion app `notify.mobile_app_*`
service, Telegram Bot `notify` entities or other trusted notify targets.
In **Notification events**, independently choose which events to send to
those same destinations. Native Apple Casa / HomeKit notifications remain
independent: you can leave armed/disarmed/triggered OFF in HA to avoid duplicates
while keeping rejected/prealert/sensor anomalies ON.

### Physical siren — read before enabling

**Keep physical output disabled until you have verified the device and
retired every old YAML automation that can command the same siren.**

1. Configure an existing Zigbee2MQTT `siren.*` entity under
   **Configure → Zigbee2MQTT siren**.
2. Verify in the Zigbee2MQTT device controls that the siren has an
   **independent** cutoff; for a 300-second alarm phase, a 5-minute device
   cutoff is a reasonable backup. These are separate timers; neither can
   substitute for an actual hardware test.
3. Only then enable **Physical siren output**. It is disabled on every
   upgraded installation until you explicitly change the setting.
4. A new trigger requests `turn_on`. Disarming, expiry of the trigger period
   and graceful integration unload request `turn_off`. Failed OFF requests
   are reported and retried while the integration is operational.
5. **On Home Assistant restart**, a restored `triggered` state does not
   automatically resend `turn_on` to the siren; this avoids unexpected
   extended sound after recovery. The device's independent cutoff is essential
   when Home Assistant, MQTT or the Zigbee coordinator are down.

A successful Home Assistant service call is **not proof** that the Zigbee
device physically switched on/off. Monitor the actual Z2M entity and test the
device's auto-off in a controlled manner. Never share physical siren ownership
with the retired YAML system.


## HomeKit / Apple Casa

Expose the standard `alarm_control_panel` in Home Assistant's **HomeKit
Bridge**. The integration keeps its existing unique entity identity; no new
bridge, custom HomeKit plugin, PIN or night mode is introduced.

HomeKit can show armed/disarmed/triggered state and deliver Apple Home
notifications. A rejected arming attempt leaves the panel disarmed, so use
the dedicated **Arming rejected** Home Assistant notification to understand
the precise problem.

Disarming from an iPhone shortcut, GPS-based automation, or an RF remote
depends on the security of those *external commands*. Avoid fixed-code
RF remotes for disarming a real security system, and validate GPS presence
before relying on it to unlock or disarm a house.

## Lovelace card for an existing dashboard

Adaptive Alarm does **not** create a second dashboard. Its custom card shows
the alarm status, counts and friendly names of Protected/Pending/Excluded
contacts, current sensor states, arming routes, fault diagnostics and the siren
status. It uses the existing `alarm_control_panel` and does not issue
arming/disarming commands of its own.

The JS module is served automatically at:

```
/adaptive_alarm/adaptive-alarm-card.js
```

If Lovelace **resources use storage mode**, the integration registers the
module resource automatically. A YAML-managed dashboard may still use storage
resources; these settings are independent.

If your `lovelace` resources use **YAML mode**, add the following *once*
under the existing `lovelace:` key in `configuration.yaml` (do not duplicate
`lovelace:`):

```yaml
lovelace:
  resource_mode: yaml
  resources:
    - url: /adaptive_alarm/adaptive-alarm-card.js?v=1.0.1
      type: module
```

Then add **one card** in the `cards:` list of your *existing* YAML dashboard:

```yaml
- type: custom:adaptive-alarm-card
```

The card normally detects the Adaptive Alarm panel automatically. If you
prefer to specify the entity explicitly, use:

```yaml
- type: custom:adaptive-alarm-card
  entity: alarm_control_panel.YOUR_REAL_ENTITY_ID
  title: Antifurto
```

Replace `YOUR_REAL_ENTITY_ID` with the actual entity from Home Assistant.
With YAML resources, reload Lovelace resources or restart HA, then refresh
your browser. With storage resources, simply refresh after the upgrade.

An existing separate `Adaptive Alarm` dashboard that was created by v1.0.0
is **not deleted automatically**: Home Assistant may contain user edits.
If you no longer want it, remove it manually in Settings → Dashboards.

### Diagnostics

The panel exposes Protected, Pending, Excluded, `minimum_routes`,
`triggered_until`, `trigger_cause` and `fault`; sensor Health also reports
relevant offline and abnormal contact states.

Listen to `adaptive_alarm_event` in **Developer Tools → Events** for
detailed machine-readable state transitions and output failure events.

## What stays outside Adaptive Alarm

Keep household presence reminders, balcony Shelly indicator, camera photo
capture / Telegram attachments, iPhone gate-opening scripts and RF receiver
automation in normal Home Assistant automations. Adaptive Alarm does not
directly command gates, locks, cameras, RF or generic user scripts.

For an exact migration inventory, see
**[Migrating from the old YAML alarm](docs/migration-from-yaml.md)**.

## Safe transition from YAML

1. **Back up** Home Assistant and the existing YAML package.
2. Test the new panel side-by-side while leaving **physical siren output OFF**.
3. Migrate all HomeKit, iPhone shortcut and household automation references
   from `alarm_control_panel.allarme_casa` to the actual new panel entity ID.
4. Ensure the old manual alarm and its trigger, siren and reset automations
   are disabled, and restart HA. Confirm the old panel is no longer active.
5. Check all protected/optional zones, rules and notification recipients.
6. Enable physical siren output only after physical auto-off verification and
   with **one** alarm system commanding the Zigbee siren.
7. Keep the old package archived and ready for rollback. If there is a
   problem, disable the new physical siren output before restoring the old
   YAML automation set.

The integration is community-developed, not a certified security appliance.
Correct behavior depends on HA, Z2M, radios, devices and local networking.
Automated tests and HACS/hassfest checks do not substitute for field tests.

## Development

Run `python -m unittest discover -s tests -v`. The repository includes
deterministic engine tests, notification and policy tests, dashboard
construction tests and HACS / hassfest validation workflows.

Report bugs with the Adaptive Alarm version, relevant Health attributes,
alarm state and anonymized `adaptive_alarm_event` payloads. Do not include
API tokens, RF codes, chat identifiers or personal address data.
