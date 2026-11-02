# Adaptive Alarm 1.0 — acceptance tests

## Automated tests (CI)

- In the reusable Lovelace card, verify the icon is static for `disarmed`,
  `arming` and `armed_away`, flashes only in `triggered`, and respects
  the browser's reduced-motion preference.
- Distinguish this component from HA's built-in `alarm-panel` and the
  HomeKit UI: they have their own animations.
- The HACS Action must run without ignored checks; the official GitHub
  Release must be created after HACS/hassfest success.



Run `python -m unittest discover -s tests -v`; CI also runs HACS and
hassfest. These checks do not establish real Zigbee relay reliability.

## Installation and migration

- Upgrade without deleting the existing config entry. Verify panel entity
  unique ID and HomeKit remain unchanged.
- Confirm previous groups, mandatory contacts, optional contacts, vibration
  links, notifications, deterrent lights and stored session are retained.
- The new real siren option must default to **OFF** on upgrade.
- Add the `custom:adaptive-alarm-card` card to an existing YAML dashboard.
  Verify it lists Protected/Pending/Excluded sensors, state, siren and anomalies,
  including the Health sensor's contact problem details.
  Verify no additional dashboard is installed and user YAML is never modified.
  With storage resources, confirm automatic JS registration; with YAML
  resources, confirm the documented one-time `lovelace.resources` entry.

## Alarm functionality

1. Arm and reject with invalid mandatory contact / group / lock. Confirm
   only valid requirements become `armed_away`.
2. Verify optional contacts initially open are excluded and initially
   unknown become Pending, joining only on first CLOSED state.
3. Verify normal protected opening triggers; after the timeout the original
   session remains armed with a held-open zone, and only close→open
   generates a fresh alert.
4. Verify vibration prealert (first hit), confirmed second/third hit, and
   non-aggregation of different sources.
5. Restart HA and Zigbee2MQTT during armed, triggered and disconnected
   contact conditions; ensure no silent loss of protection.
   When an ARMED_AWAY session finds an OPEN protected contact at restart,
   ensure a fresh TRIGGERED event requests real siren ON before notifications.
   A previously TRIGGERED session must NOT replay siren ON just because
   Home Assistant restarted.
6. Verify HomeKit and iPhone shortcuts reference the new panel and
   notifications are not duplicated unnecessarily.
7. Test deterrent light ON/OFF with a manually adjusted light, a slow
   acknowledgement and after HA restart.

## Physical siren (only after the old alarm is no longer in control)

1. With physical output **OFF**, test all alarm states: no real siren calls
   must occur, even if an old siren entity is already configured.
2. Configure the intended Zigbee2MQTT `siren.*` entity and independently test
   its actual automatic 5-minute device cutoff.
3. Enable physical output; trigger once; verify it audibly turns ON,
   the engine timer runs, and an OFF request is delivered on timeout.
4. Trigger again and disarm before timeout: OFF must be requested promptly.
5. Disconnect Zigbee2MQTT / power-cycle HA during trigger and ensure
   hardware cutoff stops sounding even if software cannot deliver OFF.
6. Restart with TRIGGERED stored: the controller must **not re-send ON**.
   After expiry it must return to ARMED_AWAY with protected zones.
7. Confirm service errors are logged and `siren_request_failed` is emitted.
   Confirm at most one system has write ownership of the physical siren.
8. If any item fails, turn physical output OFF and keep the archived YAML
   system available for rollback, never operating both simultaneously.

## External automation audit

- Presence auto-disarm, scripts that open locks/gates, HomeKit commands,
  Telegram photos, LED Shelly, Sonoff RF remotes are **not** migrated.
- Check every old `alarm_control_panel.allarme_casa` entity reference.
- Read [Migration checklist](migration-from-yaml.md) before disabling YAML.
