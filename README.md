# Sol-Ark Cloud (MySolArk) – Home Assistant Integration

![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Component-blue)
![Version](https://img.shields.io/badge/version-0.2.6-success)
![License](https://img.shields.io/badge/license-MIT-green)

A small, read-only Home Assistant custom integration for the **Sol-Ark Cloud / MySolArk** portal.

> Maintenance status: limited. For a larger actively developed Sol-Ark integration, also see [HammondAutomationHub/HomeAssistant_SolArk](https://github.com/HammondAutomationHub/HomeAssistant_SolArk).

## Design

The integration intentionally stays narrow:

`MySolArk API → Home Assistant shared HTTP session → one coordinator → sensors`

There is no database, MQTT bridge, proxy service, write/control API, or custom background scheduler.

## Sensors

- PV Power (W)
- Load Power (W)
- Grid Import Power (W)
- Grid Export Power (W)
- Battery Power (W)
- Battery SoC (%)
- PV Energy Today (kWh)
- Grid Import Energy Today (kWh), when supplied by MySolArk
- Grid Export Energy Today (kWh), when supplied by MySolArk
- Load Energy Today (kWh), when supplied by MySolArk

The integration does **not** estimate daily kWh by multiplying an instantaneous power reading by the polling interval. If the cloud does not provide a daily energy total, use Home Assistant's built-in **Integral** helper and, if needed, **Utility Meter** helper from the corresponding power sensor.

## Installation

### HACS custom repository

1. Add this repository to HACS as a custom **Integration** repository.
2. Install **Sol-Ark Cloud**.
3. Restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration** and search for **Sol-Ark**.

### Manual

Copy these files into:

```text
<config>/custom_components/solark_cloud/
```

Required integration files are `__init__.py`, `api.py`, `config_flow.py`, `const.py`, `manifest.json`, `sensor.py`, and `strings.json`.

Restart Home Assistant after installation or upgrade.

## Configuration

Enter:

- MySolArk username/email
- MySolArk password
- Plant ID
- Scan interval: 60–900 seconds (default 120)
- Authentication mode: Auto, Strict, or Legacy
- Optional grid-sign inversion

For credential safety, the API host is no longer user-configurable. Strict authentication uses the current `https://www.solarkcloud.com` portal origin, and credentials are sent only to the current `https://p2.api.solarkcloud.com` API host or the previous `https://api.solarkcloud.com` API host.

The setup flow validates the exact Plant ID before saving it and prevents the same Plant ID from being added twice.

## 0.2.6 hardening

- Removed the inaccurate custom W→kWh accumulator.
- Fixed grid-sign inversion so the setting is actually applied.
- Fixed missing grid power causing uninitialized values.
- Uses Home Assistant's shared HTTP session.
- Uses coordinator failure semantics instead of returning an empty successful update.
- Restricts authentication to known Sol-Ark API hosts and uses the current Sol-Ark portal origin.
- Validates the Plant ID during setup.
- Adds proper reauthentication for existing entries.
- Adds bounded scan intervals and bounded authentication fallback.
- Avoids logging API response bodies or credentials.
- Adds small deterministic parser tests and CI checks.

## License and credits

MIT licensed. See `LICENSE`.

Developed independently with reference to public Sol-Ark community work, including Rick-EV/SolarkCloud, judasgutenberg/SolArkMonitor, and the `solark-cloud` Python package.
