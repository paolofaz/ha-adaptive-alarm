# Contributing to Adaptive Alarm

Contributions are welcome, especially reproducible bug fixes and compatibility
reports for supported Home Assistant versions.

## Before submitting changes

1. Read the [architecture](docs/architecture.md) and
   [safety assumptions](docs/safety.md). Do not add unsolicited physical
   actuator control, HomeKit modes, PIN requirements, lock/gate actions,
   RF disarm or fail-open alarm behavior.
2. Open an issue describing the expected and actual behavior. Include the
   Home Assistant release, Adaptive Alarm version, and anonymized logs.
3. Run `python -m unittest discover -s tests -v`,
   `node --check custom_components/adaptive_alarm/www/adaptive-alarm-card.js`,
   and `node tests/test_card_runtime.js`.
4. Ensure HACS Action (with **no ignored validations**) and hassfest pass.
   Changes to state or siren logic require new regression tests.
5. Submit a PR with a clear explanation, rollback considerations, and
   screenshots only when the UI change cannot be explained through tests.

Never post tokens, RF payloads, device serial numbers, credentials, precise
locations or private home-layout details.

## Release policy

Only maintainers publish releases after checks pass. Each release uses the
same `vX.Y.Z` tag as the integration manifest, with detailed release notes.
Do not alter YAML dashboards or user-controlled Home Assistant automations
automatically.
