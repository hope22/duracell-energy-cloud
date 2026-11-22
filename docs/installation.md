# Installation and migration

## Move a manual v0.3.0/v0.4.0/v0.5.0 installation to HACS

1. Make a full Home Assistant backup and separately keep a copy of `config/custom_components/duracell_energy_cloud` outside `custom_components`.
2. Keep the existing **Duracell Energy Cloud** entry under Devices & services. Deleting it can remove entity settings and break dashboard references.
3. Add the published repository to HACS as an Integration custom repository, then download the latest release. HACS should replace the files in the same domain folder.
4. If HACS refuses because the folder already exists, stop Home Assistant, move only that integration's code folder outside `custom_components`, start Home Assistant, install using HACS and restart again. Temporary unavailable sensors during this operation are expected.
5. Confirm the loaded version is 0.6.0 in the integration's diagnostics/system information and the original entities still update. Two built-in battery energy entities should appear (14 entities in total). When upgrading from v0.3.0, the charging/discharging power and activity entities are also new.
6. Check charge/discharge direction against the Duracell portal and keep the backup until verified.

For Synology Container Manager, `config` above means the host directory mounted at `/config` inside the Home Assistant container. Restart the Home Assistant container; do not remove the container's persistent configuration volume.

## Roll back

Select the preceding release in HACS and restart. If v0.3.0 has not been published, stop Home Assistant and restore the saved code directory, then start it. This version retains config-entry version 2 and does not change existing sensor unique IDs.

## Manual installation

Copy `custom_components/duracell_energy_cloud` from this repository into Home Assistant's `config/custom_components/`, then restart. Manual installation does not register HACS update management.

## Removal

Remove the integration entry in Devices & services, then remove its download through HACS and restart. Back up first if you want to preserve configuration or restore the integration later.
