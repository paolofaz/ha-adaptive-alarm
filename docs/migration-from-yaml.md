# Migration checklist — old Allarme Casa YAML → Adaptive Alarm 1.0

This checklist is based on the previous `allarme_casa` YAML package. It
**does not edit, disable or delete any Home Assistant user configuration**.

## Replace old alarm logic

| Old YAML component | Adaptive Alarm 1.0 replacement |
| --- | --- |
| `alarm_control_panel.allarme_casa` (`platform: manual`) | New Adaptive Alarm `alarm_control_panel`; preserve its actual HA entity ID |
| `notificafinestraperteeallarme` | Built-in arming rejection + reason-specific notification |
| `allarmeinserito` | Core arming requirements + committed Protected session |
| `allarmedisinserito` | Built-in disarm; keep independent household effects outside |
| `allarmescattato` | Core trigger state and optionally enabled Zigbee siren + configured light deterrence; **move Telegram photo and extra lighting to external automations** |
| `datriggerainserito` | Core timed return from `triggered` to `armed_away` |
| `triggerfinestre`, `triggerpersianeinfinestre`, `triggerpersiane` | Core monitoring of contacts and alternative groups |
| `alarmevibrazione`, `alarmevibrazionepersiane`, `vibrazionefalsoallarme` | Core per-sensor vibration logic, prealert and conservative light timing |
| `timer.allarme_vibrazione`, `input_boolean.vibrazione_perdonata` | Old global vibration-state helpers; **remove only after confirming nothing else uses them** |
| `input_boolean.allarme_in_scala`, `input_boolean.persiane_monitorate`, `input_boolean.night_finestre_basse` | Obsolete for new one-mode `armed_away` engine; check other dashboard/automation references first |
| `input_text.sensoreallarme` | Replace uses with `trigger_cause` / `adaptive_alarm_event` where appropriate. Check photo/script dependencies before removing. |

The old YAML `armed_night` transitions are **not reproduced**: only
`armed_away` exists in Adaptive Alarm 1.0. Do not leave shortcuts or
automations invoking `alarm_arm_night` without redesign.

## Keep or migrate separately

- **Zigbee2MQTT devices/entities:** keep the *original* door, window,
  shutter and vibration `binary_sensor` entities, the configured door
  `lock` and the Zigbee siren entity. The integration references them.
- **Presence:** `allarme_avviso_armato_con_persona_home` and
  `allarme_avviso_casa_vuota_disarmato` belong to Home Assistant
  automations. Keep the underlying person/presence helpers and
  `binary_sensor.casa_certamente_vuota` if used; retarget alarm references.
- **LED Shelly:** keep `light.led_allarme` (if it is still the entity).
  Replace the old `script.lampeggioled` and LED state automations with
  the agreed sunset-to-sunrise steady light and two identical brief flashes
  on genuine arming/disarming events. Do not reveal the alarm state.
- **Telegram photos:** keep the photo-taking `script.invia_telegram` and
  camera definitions outside Adaptive Alarm. Trigger it from
  `adaptive_alarm_event` when `type: triggered` (respect `entry_id`)
  or the alarm panel's `triggered` state. The core notifications do not
  attach camera photos.
- **RF remote:** `disarmadaRF` listens to `Sonoff/RfBridge/RESULT`
  and disarms on fixed RF payloads. Keep it outside the integration **only
  after a replay-attack risk review**; ideally do not use fixed codes for
  disarming physical security.
- **iPhone/HomeKit and gate/door script:** update shortcuts and automations
  to the new alarm panel ID. Keep the gate and lock actions external.
  Consider confirmation/secure presence evidence for unattended disarm.
- **Home Assistant groups and counters** (`group.finestre_allarme`,
  `group.persiane_allarme`, `group.finestre_basse_allarme`;
  `sensor.finestreaperteallarme`, `sensor.persianeaperteallarme`,
  `sensor.finestrebasseallarme`): not needed by the core if the equivalent
  contacts are configured under Adaptive Alarm. **Retain temporarily**
  if referenced by other dashboard, presence, reporting or legacy scripts.
- Keep unrelated household lights, `notify` services, camera, MQTT and
  network definitions, person trackers, locks and other system helpers.

## Before archiving or disabling the YAML

1. Back up `configuration.yaml`, the original package, automations,
   secrets and your Home Assistant storage.
2. Take note of the exact new panel entity ID in Developer Tools → States.
   The old ID is not automatically reassigned.
3. Audit all other automations/scripts referencing
   `alarm_control_panel.allarme_casa`, `alarm_arm_night`,
   `switch.sirena_alarm_switch` and `input_text.sensoreallarme`.
4. While both systems exist, leave **physical siren output disabled** in
   Adaptive Alarm. Do not create dual ownership of the Zigbee siren.
5. Disable the old manual alarm package and its own alarm-trigger
   automations, restart HA, and verify the old panel is absent.
6. Test new armed-away, rejected, trigger, timed rearm, disarm, offline
   recovery and HomeKit state **before** enabling the new real output.
7. Independently verify the Zigbee2MQTT siren's hardware auto-off. Confirm
   the new HA siren entity domain and actual ON/OFF behavior. Enable the new
   output explicitly, once the old system is no longer controlling it.
8. Retain the archived YAML and a rollback plan for days/weeks. Do not erase
   entities or helpers that remain referenced by any live automations.

## Rollback

Disable physical siren output in Adaptive Alarm first. Confirm the siren is
off. Only then restore the old YAML and restart HA. Never operate both
physical siren command paths at once.

The external presence and RF automations can disarm the new system as soon
as they target its real entity ID. The plugin does not manage or authorize
those automations. A fixed RF code is not cryptographic authentication.
