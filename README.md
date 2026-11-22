# Duracell Energy Cloud

<img src="custom_components/duracell_energy_cloud/brand/icon.png" width="96" alt="Community energy integration icon">

Unofficial, read-only Home Assistant integration for Duracell Energy cloud monitoring.

Monitor your battery, solar generation and home power from Home Assistant. One shared cloud request refreshes all sensors every two minutes by default.

**v0.4.0 release candidate:** prepared for HACS custom repositories. Live upgrade verification and GitHub validation are required before a stable release. The original v0.3.0 was reported working with a Dura-i G3 inverter and Dura16 batteries; other models are unverified.

## Features

- Battery percentage, voltage and signed power.
- Separate battery charging and discharging power, plus charging/discharging/idle status.
- Solar DC power, home load, signed grid power, backup EPS and generator power.
- Shared polling, bounded login renewal and Home Assistant reauthentication.
- Configuration editing and diagnostics containing no raw cloud responses or credentials.
- Existing v0.3.0 device and sensor identifiers retained.

## Install with HACS

Requires Home Assistant 2024.12 or newer and HACS. This repository is not yet in the default HACS catalog.

1. In HACS, open **Custom repositories** from the menu.
2. Add `https://github.com/hope22/duracell-energy-cloud` with type **Integration**.
3. Find **Duracell Energy Cloud**, download it and restart Home Assistant.
4. Open **Settings → Devices & services → Add integration** and search for **Duracell Energy Cloud**.
5. Enter the connection details described in [Configuration](docs/configuration.md).

These steps become available once the repository is published. For an existing manual installation, follow [the migration guide](docs/installation.md) first; do not delete the configured integration.

## Setup limitations

This version requires the inverter ID, group ID and flowgraph request signature. Password mode also needs a login signature; token mode needs a monitoring token. Username/password-only setup, signature generation and automatic inverter discovery are **not implemented**. Password login depends on the provider accepting the supplied signature.

No battery controls or charging schedule changes are sent. The API is unofficial and may change without notice. Data refreshes depend on the provider's own reporting cadence.

## Sensors

| Reading | Unit / meaning |
| --- | --- |
| Battery state of charge | % |
| Battery power (signed) | W; positive discharge, negative charge |
| Battery charging / discharging power | W; separate non-negative readings |
| Battery activity | charging, discharging, idle |
| Battery voltage | V |
| PV DC power (reported) | W; provider's DC reading |
| Home load / backup EPS / generator power | W |
| Grid power (signed) | W; direction convention not yet verified |
| Inverter mode code | Raw provider code |

Missing or invalid numerical readings remain unknown rather than becoming zero. A failed cloud update makes the coordinator's entities unavailable.

## Energy Dashboard

The API used here exposes power in watts, not cumulative energy in kWh. See [Energy Dashboard setup](docs/energy-dashboard.md) to derive estimated battery energy using Home Assistant's integral helpers. Grid import/export splitting is intentionally pending verification of the provider's sign convention.

## Updates and support

After publication, new tagged GitHub releases can be installed from HACS, followed by a Home Assistant restart. Pushing a commit alone is not the documented stable release process.

- [Installation and upgrades](docs/installation.md)
- [Configuration](docs/configuration.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Release checklist](docs/releasing.md)

An independent community project, not affiliated with or endorsed by Duracell, Duracell Energy or the monitoring provider. Product names belong to their respective owners. MIT licensed.
