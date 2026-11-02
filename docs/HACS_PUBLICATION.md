# HACS publication readiness — Adaptive Alarm

This checklist applies to the **HACS default Integration catalog**, not
installing a **custom repository**. The two are different workflows.

Official references:
- [HACS general repository requirements](https://www.hacs.dev/docs/publish/start/)
- [HACS integration publishing requirements](https://www.hacs.dev/docs/publish/integration/)
- [Adding default repositories](https://www.hacs.dev/docs/publish/include/)
- [Official HACS default repository list](https://github.com/hacs/default)
- [Home Assistant brands repository](https://github.com/home-assistant/brands)

## Repository audit for v1.0.3

| Requirement | Current status |
| --- | --- |
| Public repository on GitHub | Met |
| One integration under `custom_components/adaptive_alarm/` | Met |
| Manifest with name, version, issue tracker, docs, codeowners | Met |
| HACS `hacs.json` name and rendered README | Met |
| Recognized OSI license (MIT) | Met |
| README with setup, usage and safety guidance | Met |
| GitHub issues enabled and description provided | Met |
| GitHub topics set (alarm, home-assistant, hacs, etc.) | Met |
| HACS GitHub Action | Required to pass **without ignore options** |
| Home Assistant hassfest | Required to pass |
| Full GitHub Release after successful checks | Automated after validation |
| Branding in the central `home-assistant/brands` repository | **Not confirmed/remaining external step** |
| PR to `hacs/default` by repository owner/major contributor | **Not submitted** |

The integration currently bundles `custom_components/adaptive_alarm/brand/icon.png`.
The HACS default-list validator may accept that local icon in its **brand
check**, but the HACS integration publishing guide separately calls for
an entry in `home-assistant/brands`. Local packaging is not a substitute
for confirming that external central-branding requirement.

## Owner checklist before submitting to HACS

1. Confirm `v1.0.3` HACS Action and hassfest are **both green**, with
   no ignored validation rules. Confirm the official `v1.0.3` release was
   created afterward.
2. Verify the integration against a currently supported production version
   of Home Assistant, including HomeKit Bridge and Lovelace resource storage
   as well as YAML resource mode.
3. Add/verify the integration icon under the correct custom integration
   directory in `home-assistant/brands`, following the central repository
   image/dimension requirements. This requires a separate PR there; it is
   **not completed by this repository refactor**.
4. Ensure GitHub repository metadata (description, topics, license, issues)
   remains correct, and the README has sufficient English-language guidance.
5. As the owner/major contributor, fork `hacs/default`, add
   `paolofaz/ha-adaptive-alarm` in alphabetical order to its `integration`
   file, and follow the latest PR template. Do not submit this repository as
   a separate HACS `plugin`: the custom card is bundled with the integration.
6. Expect independent maintainer review; passing repository actions is
   necessary but **not sufficient for approval**.

## Repository layout

```text
custom_components/adaptive_alarm/
  __init__.py              Integration lifecycle and options migration
  manifest.json            Home Assistant manifest and semantic version
  alarm_control_panel.py   Standard alarm panel / HomeKit Bridge
  binary_sensor.py         Readiness diagnostic
  sensor.py                Counters and Health diagnostic
  config_flow.py           Configuration and options UI
  controller.py            HA adapter and siren/light service control
  frontend.py              Lovelace JS module resource registration
  www/adaptive-alarm-card.js  Optional UI for an existing YAML dashboard
  translations/{it,en}.json  Built-in translations
  engine/                  Pure, deterministic state engine
tests/                     Python and headless Node regressions
.github/workflows/         Unit, HACS/hassfest, validated release workflows
docs/                      Architecture, safety, migration and release notes
```

This project implements a community home alarm, **not a certified security
appliance**. No code change in this publication pass modifies real siren
actuation, sensor enrollment, authentication or alarm states.
