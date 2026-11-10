# Changelog

## v1.0.8 — silence routine deterrent auto-off notifications

- Suppress phone/Telegram notifications for each successful scheduled
  deterrent-light switch-off after a vibration prealert
- Preserve `deterrent_light_off_requested` HA events for diagnostics and
  the actual automatic turn-off behaviour
- Keep vibration prealert, alarm and safety/failure notifications unchanged
- Add behavioural regressions covering multiple lights and failure cases

## v1.0.7 — Home Assistant frontend custom-element registry race

- Fixed a potential race where an extra-module registers a card before
  Home Assistant installs its scoped custom-element registry polyfill
- Uses one native Lovelace resource import in storage mode, not a duplicate
  early frontend import of the same URL
- In YAML mode or storage error, retains frontend fallback and registers
  the card again after the HA root is initialized when needed
- Adds a JavaScript regression test simulating the registry replacement
- Does not alter the alarm engine, siren, HomeKit or sensor rules

## v1.0.6 — single-card editor syntax and correct siren lifecycle

- Documented YAML for Home Assistant single-card editor without a leading dash
- Clearer Lovelace card configuration validation
- Removed unconditional siren OFF on Home Assistant startup and unload
- Preserved ON for fresh alarms and OFF on disarm or actual timer expiry
- Retries only explicit OFF commands; a fresh alarm cancels old retries
- No changes to HomeKit IDs or adaptive zone protection

## v1.0.5 — robust frontend resource auto-loading in storage mode

- Fixed the missing fallback when Lovelace storage resource registration fails
- Loads the bundled JS module via Home Assistant frontend in both resource modes
- Still attempts to create/update the visible resource record in storage mode
- Emits actionable error logs instead of making card loading depend on storage
- Includes regression tests for collection errors and unavailable Lovelace data
- No changes to the alarm, Zigbee siren, HomeKit or configuration state

## v1.0.4 — automatic Lovelace card loading in YAML resource mode

- Fixed the card JavaScript not being loaded automatically when `lovelace.resource_mode: yaml`
- Uses Home Assistant's frontend extra module registration without writing user YAML
- Keeps the existing storage-mode resource registration
- Unregisters the extra module when the integration is unloaded
- UI placement remains user-defined via `type: custom:adaptive-alarm-card`
- No changes to alarm engine, siren, HomeKit, or notifications

## v1.0.3 — HACS submission preparation

- Lovelace card: stable icon when disarmed, arming or armed; flashes only in `triggered`
- Honors reduced-motion accessibility preferences
- Removes ignored HACS Action checks and keeps hassfest validation mandatory
- Defers GitHub Releases until the validation workflow and regression tests pass
- Adds maintainer documentation, issue template and HACS submission checklist
- Alarm engine, HomeKit state machine and real siren output unchanged

## v1.0.2 — final stable

- Correzione sirena allo scatto rilevato durante il ripristino di `armed_away`
- Nessuna riattivazione della sirena per un episodio già `triggered` al riavvio
- Scheda Lovelace YAML: diagnostica Health con nomi dei sensori anomali
- Pulizia metadati e test automatici aggiuntivi
- Pubblicazione ufficiale GitHub Release

## v1.0.1

- Supporto diretto a sirena Zigbee2MQTT `siren.*`
- `custom:adaptive-alarm-card` per plance YAML esistenti
- Eliminazione della sirena fittizia e della creazione della dashboard separata

## v1.0.0

- Primo motore stabile di protezione adattiva con sirena reale opt-in
- Durata allarme, notifiche configurabili e integrazione HomeKit
- README e guida di migrazione dal vecchio YAML
