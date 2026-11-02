# Changelog

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
