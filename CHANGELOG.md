# Changelog

## v1.0.6 — card-editor syntax and Zigbee2MQTT startup sequencing

- Documented the correct single-card editor YAML without a leading dash
- More helpful validation for malformed or missing Lovelace card configuration
- Defers startup siren OFF until Zigbee2MQTT is available, without error spam
- Retries the pending startup OFF, including after a temporarily unavailable siren
- Warns once if the device remains unreachable for more than two minutes
- Preserves urgent ON failures, manual disarm OFF and independent siren cutoff
- No changes to HomeKit entity IDs or the adaptive zone engine

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
