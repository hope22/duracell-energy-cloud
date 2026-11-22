# Your ready-made Duracell dashboard

Version 0.7.0 includes a dashboard generator. It resolves your current entity IDs (including renamed entities), creates one view per loaded inverter, and uses only built-in Home Assistant cards. No third-party frontend cards are needed.

## Create the dashboard

1. Update through HACS, restart Home Assistant and allow the integration to load.
2. As an administrator, open **Developer tools → Actions** and select **Duracell Energy Cloud: Generate dashboard** (`duracell_energy_cloud.generate_dashboard`). No inputs are needed.
3. Run the action. Copy the complete response object, beginning with `title: Duracell Energy` (or the JSON object with `title` and `views`). JSON is also valid YAML.
4. Under **Settings → Dashboards**, create a new empty dashboard called **Duracell Energy** and open it. If needed, take control of that new dashboard.
5. Choose **Edit dashboard → ⋮ → Raw configuration editor**, replace the new dashboard's configuration with the generated response and save.

Do this in a **new dashboard**, not your existing Overview. The action only generates configuration; it does not change any dashboards automatically. Keep the `title` and `views` object, without an enclosing response wrapper if your Home Assistant UI displays one.

## Included

- Battery percentage gauge.
- Solar DC, household, grid import/export and battery charge/discharge power tiles.
- 24-hour power history and seven-day daily energy bars.
- Accumulated energy readings.
- Battery temperature, health, reported capacity and current/voltage limits.
- Cloud connection, connection status, last successful update and consecutive failed polls.
- A visible warning when the cloud connection is disconnected or stale.

Charts fill as Recorder collects readings; historical data is not imported. Unsupported battery information remains unknown. The main Energy Dashboard must still be configured separately using the sensors described in the energy guide.

For multiple inverters, each view represents that inverter. Site-level grid/home readings may overlap for shared-meter installations; don't sum those readings blindly across inverters.

After renaming entities, adding inverters or enabling optional sensors, regenerate and replace the dashboard configuration if needed. This will replace edits you made in that particular dashboard; save those edits first.
