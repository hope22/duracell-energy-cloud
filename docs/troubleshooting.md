# Troubleshooting

- **Integration not found:** confirm the directory is `custom_components/duracell_energy_cloud`, then restart Home Assistant and refresh the browser.
- **Cannot connect:** confirm the monitoring portal is working and retry. HTTP failures and malformed responses make sensors unavailable.
- **Authentication failed:** verify your monitoring username/password in the portal. Complete any CAPTCHA there first. Reauthenticate or use Reconfigure to switch an old manual entry to automatic login.
- **No supported inverters:** the account has no hybrid devices returned by the monitoring API.
- **Readings do not change:** the cloud may report more slowly than the polling interval. Compare the portal and wait several cycles.
- **Energy Dashboard cannot select a power sensor:** use a cumulative kWh helper as described in the energy guide.

Download integration diagnostics from Devices & services when reporting a problem. Diagnostics expose only authentication mode, polling interval and last-update success. Include Home Assistant and integration versions and a concise reproduction. Review any logs before sharing; do not include tokens, passwords, signatures, serial numbers or full API responses.
