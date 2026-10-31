# Adaptive Alarm

Adaptive Alarm is a Home Assistant custom integration project designed around **adaptive protection zones**.

> **DEVELOPMENT PREVIEW — NOT AN OPERATIONAL ALARM.** This first version can be installed as a custom HACS integration and configured through Home Assistant. It **does not yet create an alarm panel, activate a siren, arm/disarm a security system or read physical sensors**.

## Why adaptive?

Instead of separate Full/Night modes, a single arm request should be permitted only when:

- the entry door is closed **and** the entry lock is locked; and
- **either** both living-room and bathroom shutters are closed;
- **or** both living-room and bathroom windows are closed.

Every available, closed contact can be protected in the session. Contacts excluded at arm time can join after five seconds of stable closure. A protected contact is never silently excluded during the session.

This behavior is based on the previous **Allarme Casa v3.3 YAML design**, which is a reference specification, not an already validated implementation.

## Install via HACS (development preview)

Once this pull request is merged to `main`:

1. In HACS open the menu **Custom repositories**.
2. Add `https://github.com/paolofaz/ha-adaptive-alarm` with category **Integration**.
3. Download **Adaptive Alarm** and restart Home Assistant if prompted.
4. Go to **Settings → Devices & services → Add integration → Adaptive Alarm**.
5. Select the five minimum-route contacts and the entry lock.

**The integration is currently only a configuration preview.** Do not expect it to expose an alarm entity or control anything.

> HACS may not be able to access a **private** GitHub repository with the credentials used by your Home Assistant instance. If you want to keep development private, test using an authorized GitHub setup or copy `custom_components/adaptive_alarm` to an isolated development Home Assistant instance. Consider making the repository public only when you are ready; remove any private data before doing so.

## Run core tests

This project deliberately keeps its policy engine free of Home Assistant imports:

```sh
python -m unittest discover -s tests -v
```

## Structure

```text
custom_components/
  adaptive_alarm/
    __init__.py
    manifest.json
    config_flow.py
    const.py
    engine/
      model.py
      policy.py
    translations/
      en.json
      it.json
.github/workflows/
  tests.yml
  validate.yml
docs/
  architecture.md
  safety.md
tests/
```

## Development policy

All actuation (sirens, lock commands, notifications, alarm panel) stays **out of scope** until the state machine, recovery after restart, persistence, concurrent event handling and integration tests are complete. Never run two controllers against the same physical siren. RF code-based disarming is not planned for the first safe operational release.

License: MIT.
