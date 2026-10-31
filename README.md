# Adaptive Alarm

**Adaptive protection for Home Assistant** · HACS-installable · Open source (MIT)

> **v0.3.0 alpha — SIMULATION ONLY.** This integration can be installed and its alarm panel can be armed/disarmed to test the behavior of real sensors, but **it cannot control a siren, light, lock, radio receiver, MQTT device or other physical actuator. It is NOT an operational security system.** Keep your existing alarm running while testing, and do not automate its outputs from these preview events.

## Install with HACS

1. Open HACS in Home Assistant → menu (three dots) → **Custom repositories**.
2. Enter `https://github.com/paolofaz/ha-adaptive-alarm`, select **Integration**, and add it.
3. Download **Adaptive Alarm**; restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration → Adaptive Alarm**.
5. Configure the entry-door contact, door lock, living-room and bathroom shutters, living-room and bathroom windows.
6. Under **Configure → Options**, select optional other contacts and vibration sensors, with timings and recovery policy.
7. Add `alarm_control_panel.adaptive_alarm` (actual entity ID may differ) to an Alarm panel card. You may select Away and Disarm only; triggering is for simulation tests.

The GitHub repository is public, and only the one custom component under `custom_components/adaptive_alarm/` is installed. If HACS does not offer the repository yet, ensure you have the latest version of HACS or install from its custom repository menu. A public GitHub release is not required for a custom repository on HACS; the default branch version is used until releases exist.

## The adaptive contract

You can arm when **the entry contact is closed**, **the door lock is locked**, **and** one of these minimum coverage routes holds:

- **Route A:** living-room shutter + bathroom shutter.
- **Route B:** living-room window + bathroom window.
- **Route C:** living-room window + bathroom shutter.
- **Route D:** living-room shutter + bathroom window.

In other words, **entry door closed AND lock locked AND (sala shutter OR sala window) AND (bagno shutter OR bagno window)**. Several routes may be valid at once. A missing, unknown or unavailable contact never counts as closed. You do **not** need to recreate the integration: previously configured entities remain in use.

The exit delay is 60 seconds by default. Eligibility is checked at both the initial arm request **and** the final commit. **Protection is frozen at the end of the exit delay:** every closed contact is protected and every open/offline contact is excluded for the *entire* session, even if it later closes and reopens (e.g. wind). To include a previously excluded contact, **disarm and re-arm** after closing it. Protected contacts remain protected until disarm.

A normal transition from closed to open on a protected sensor causes a simulated trigger. Offline recovery that reports open is configurable (default: critical notice; optional: simulated trigger). The session is persisted in Home Assistant storage so a restart does not rebuild the exclusion list.

## Native entities

| Type | Entity name | Behavior |
| --- | --- | --- |
| Alarm control panel | Adaptive Alarm | Away / Disarm, plus manual simulated trigger |
| Binary sensor | Ready to arm | Whether a minimum route is satisfied right now |
| Sensor | Protected zones | Count of protected contacts; `zones` attribute lists their entity IDs |
| Sensor | Excluded zones | Count of excluded contacts; `zones` attribute lists their entity IDs |
| Sensor | Health | Ready, not ready, OK, degraded, triggered or critical |

The alarm entity attributes include its session identifier, protected and excluded entity IDs, satisfied minimum routes and fault text. The two numeric zone-count sensors also expose their entity-ID lists in the `zones` attribute and `session_frozen: true`. This may reveal sensitive room names to anyone who already has access to those Home Assistant entities; set Home Assistant permissions accordingly.

## Vibration engine (optional)

In **Configure → Options**, you can now define up to **three vibration sensor/contact pairs** (`Vibration 1/2/3` and its linked contact). Choose **exactly one monitored contact** for each vibration sensor: e.g. entry vibration → entry contact, sala vibration → actual shutter/window to which it belongs, bagno vibration → actual shutter/window. An incomplete pair is rejected; pulses from sensors linked to excluded contacts **do not count**. Vibration sensors configured under the old unpaired option are intentionally not enabled until they receive explicit associations.

A transition from `off` to `on` counts as an impulse. Profiles:

- `balanced`: two valid impulses within the window.
- `cross`: two different sensors or three impulses on one sensor.
- `cautious`: three valid impulses.

Default debounce is three seconds per sensor and confirmation window 60 seconds. If the optional thunderstorm sensor is active, one grace allowance applies to repeated impulses from one sensor; confirmation from a different sensor bypasses this allowance.

**Important:** one vibration sensor currently has one associated contact. If it physically monitors multiple elements, select the one it is actually mounted on; do not infer that it protects both. Vibration detection is simulated and does not activate a physical siren.

## Debugging and safe notifications

Every meaningful state transition emits a Home Assistant event of type `adaptive_alarm_event`, carrying `entry_id`, `type`, and relevant zone/cause/route details. Examples of `type`: `arming`, `armed`, `arm_rejected`, `zone_fault`, `protected_zone_abnormal`, `vibration_prealert`, `vibration_storm_grace`, `triggered`, `triggered_restored`, `disarmed`. Use **Developer tools → Events** to listen for this event during trials. **Do not connect this preview event directly to a physical siren.**

See [Example dashboard](examples/dashboard.yaml), [Architecture](docs/architecture.md), [Safety](docs/safety.md), and [Test plan](docs/test-plan.md).

## Local tests

```bash
python -m unittest discover -s tests -v
```

GitHub CI also runs Home Assistant's `hassfest` and HACS repository validation. These cannot replace an actual Home Assistant runtime or a controlled physical test.

## Personal data / RF

**No RF codes, MQTT credential, personal address or household-specific entity IDs are stored in the project.** The optional guest RF workflow from the old YAML project is intentionally not implemented in this alpha.

License: MIT. Repository: [paolofaz/ha-adaptive-alarm](https://github.com/paolofaz/ha-adaptive-alarm).
