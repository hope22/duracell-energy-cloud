# Changelog

## 0.6.0 — 2026-11-22

- Automatically add Battery energy charged and Battery energy discharged in kWh.
- Make battery energy totals eligible for Energy Dashboard statistics without manual helpers.
- Restore native totals across normal restarts/reloads, preserving full calculation precision.
- Integrate unchanged power readings on successful polls; skip missing readings, failed polls and prolonged gaps.
- Preserve existing entity identities and add the new sensors to the same device.
- Add energy calculation, restoration, metadata and lifecycle regression tests.

Totals are estimates starting at installation, not historical meter readings. They do not backfill outages, downtime or existing helper history.


## 0.5.0 — 2026-11-22

- Add username/password-only setup with automatic request signatures.
- Discover supported hybrid inverters across account sites. Select a single inverter automatically or show a selection list.
- Verify telemetry before creating an entry.
- Preserve existing entry identity and polling interval when switching from manual authentication.
- Retain compatibility with v0.4.0 configurations.
- Verify real login, discovery and telemetry against the public demo account; add protocol and flow regression tests.

Validation on the owner’s Home Assistant instance remains pending.


## 0.4.0 — 2026-11-22

- Prepare a HACS-compatible repository and GitHub validation workflows.
- Add separate battery charging power, discharging power and activity sensors.
- Add reauthentication and reconfiguration without replacing existing entities.
- Normalize stored connection identifiers and signatures after validation.
- Add allowlisted diagnostics; reject HTTP redirects for authenticated requests.
- Document installation, migration, estimated energy helpers and release procedures.

Based on recovered v0.3.0 source. This is not the unavailable v0.4.0 archive from the earlier chat. Live upgrade testing remains outstanding.

## 0.3.0

Initial privately installed monitoring integration with nine sensors and password/token authentication. Reported working on a Synology Home Assistant container with a Dura-i G3 and Dura16 installation.
