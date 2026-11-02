# Security Policy

Adaptive Alarm is community-developed Home Assistant software. It is **not**
a certified intruder alarm or a substitute for professional security measures.

Please do not publicly disclose exploitable vulnerabilities, credentials,
RF replay codes, household access methods or sensitive deployment information.

## Reporting

Use GitHub's private vulnerability reporting if available for this repository.
Otherwise contact the repository maintainer through a private channel before
opening any public issue with exploit details. Avoid sensitive information
in ordinary public bug reports.

The integration's physical siren output is opt-in; reliable operation depends
on Zigbee2MQTT availability and an independent siren auto-off timer. Presence
disarm, HomeKit and RF automations are controlled outside the integration.
A validated Home Assistant service call does not confirm physical actuation.

Supported security fixes target the latest stable release. Older versions
are not guaranteed to receive backports.
