# Configuration

## New installations (v0.5.0+)

1. Open Settings → Devices & services → Add integration → Duracell Energy Cloud.
2. Enter the username and password you use for the Duracell monitoring portal.
3. If your account has one supported hybrid inverter, it is selected automatically. If it has several, select the site/inverter from the list.

No serial number, group ID, signature or token needs to be copied. The integration signs requests, discovers your account's sites and validates inverter telemetry before saving the entry. To connect another inverter, add the integration again and choose it.

The default polling interval is 120 seconds. Existing polling intervals are preserved during reconfiguration. This release's setup form only asks for credentials and, when necessary, an inverter selection.

## Existing v0.4.0 entries

Existing manual password/signature and token entries continue to work after the update. To switch an existing entry to automatic login, use its **Reconfigure** action and enter your username and password. The same inverter must be present on the account; its entity identities and polling interval are retained. Old signatures and tokens are removed from that entry when switching.

If authentication expires, Home Assistant requests reauthentication using username and password. Automatic mode renews a rejected monitoring session once before requesting user intervention.

## Login problems

Confirm you can log in at the provider's monitoring portal. If it requires a CAPTCHA, complete that in the portal before trying the integration again. No supported inverters means the account returned no hybrid devices; grid-only PV inverters are outside this integration's current scope.

Credentials stay in Home Assistant's local configuration storage and are sent only to the monitoring API over HTTPS. Protect configuration backups. Never include passwords, tokens, signatures, account exports or HAR files in GitHub issues.
