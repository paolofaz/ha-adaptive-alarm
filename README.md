# Adaptive Alarm v0.4.0-alpha

**HACS-installable, simulation-only, programmable AND/OR intrusion policy.**

> **NO PHYSICAL OUTPUTS.** The optional siren selector saves an entity reference only. No siren, switch, light, lock, RF or MQTT command is ever issued. Do not depend on this alpha for real security.

## Setup

1. Install via HACS custom repository `https://github.com/paolofaz/ha-adaptive-alarm` (Integration).
2. Restart Home Assistant and add **Adaptive Alarm** under Settings → Devices & services.
3. The quick first step only asks for a name. The alarm **cannot be armed** until minimum rules are configured.
4. Open **Adaptive Alarm → Configure**, and select a configuration section. One section is saved at a time; reopen Configure for other sections.

## Protection policy

- **Mandatory contacts**: all must be closed.
- **Alternative groups**: each named group requires *at least one* closed sensor. All groups must pass.
- **Optional contacts**: do not gate insertion. Those closed at activation are protected; those open/offline remain excluded until disarm and re-arm.
- **Lock**: optional `lock.` entity, if present must be `locked`. No lock is required if unset.
- **Vibrations**: up to three sensor → actual physical door/window contact associations. An impulse counts only when that exact contact was protected at insertion, not because a shutter was closed.
- **Siren**: optional `siren.` or `switch.` entity selection, **inert in v0.4.0-alpha**. Leave unconfigured until output controls are developed and separately field-tested.

Every binary contact is interpreted as `off = closed`, `on = open`. `unknown`, `unavailable` and missing entities are NOT safe. This first generic release targets binary door/window contacts, not arbitrary sensor types with custom normal states.

### Example: Sala and Bagno

For your existing setup, the rules map to:

- Mandatory: **porta ingresso** (closed)
- Optional lock prerequisite: **serratura ingresso** (locked)
- OR group **Sala**: finestra sala **or** persiana sala closed
- OR group **Bagno**: finestra bagno **or** persiana bagno closed
- Any other configured contacts: Optional list

If both window and shutter in a room are closed at the arming deadline, **both are protected**. A closure after activation never adds an excluded contact.

For another home, a single mandatory door and several optional windows may be enough, with no shutters or lock.

### Exit delay

For delay > 0, Arm Away starts the countdown even if conditions are not yet met. All minimum requirements are checked **only at the deadline**. If they fail, arming is rejected, the panel remains disarmed and its `fault` attribute explains which conditions failed. Delay 0 checks immediately. Use `Ready to arm` as a live diagnostic, not as a premature gate.

## Migration from v0.3.1

**No reinstall or re-selection is needed for your existing home.** Your previous six configured entities are automatically interpreted through the generic policy, with mandatory door, Sala and Bagno groups, optional lock and any extra contacts. Your previously configured door/window vibration sensors keep their original safe physical associations until you edit the vibration page. A previously armed frozen session keeps the exact protected entity set on restart; obsolete route names are converted to new group labels.

Migration is **in memory** until an Options page is saved. If you edit mandatory/groups, do so while disarmed, verify the groups, and then proceed with tests. A configuration change is refused while Arming, Armed Away or Triggered.

## Siren safety

The optional siren is deliberately *metadata only* (no output adapter or actuation services). The panel publishes `siren_configured` and `siren_enabled: false`. The application never calls any Home Assistant service on the selected siren.

For trial runs **leave the siren field blank**, and never create automations that route the `adaptive_alarm_event` simulation event to a real siren.

## Testing and limitations

```sh
python -m unittest discover -s tests -v
```

The project also runs hassfest and HACS checks. Neither CI nor the dry-run simulation is a certified alarm; Home Assistant runtime and on-site testing remain essential.

Configuration currently uses native multi-step Options Flow pages rather than a custom Lovelace configuration panel. Additional rule operators and siren control are future work, not silently enabled in this release.

[Architecture](docs/architecture.md) · [Safety](docs/safety.md) · [Trial plan](docs/test-plan.md)
