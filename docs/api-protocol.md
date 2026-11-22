# Observed monitoring protocol

Verified on 22 November 2026 against the public [Duracell monitoring portal](https://monitoring.duracellenergy.com/dist/), bundle `umi.77dc955a.js`, login chunk `p__Login__Home__index.076b5edf.async.js`, group list chunk `p__GroupList__index.49119bfb.async.js`, and device list chunk `p__GroupDevice__index.9407669f.async.js`.

All calls use HTTPS POST JSON to `/dist/server/api/CodeIgniter/index.php/Senergytec/web/v2/Inverterapi/`. Authenticated calls use the raw login token in `Authorization`.

- `UserLogin_v1`: MemberID, Password, type `1`; successful response status `ok`, token and MemberAutoID.
- `GroupList`: MemberAutoID, inputValue (empty); response AllGroupList, whose AutoID identifies each site.
- `GroupDetailList`: MemberAutoID and GroupAutoID; response AllInverterList. GoodsID is the inverter serial, isHybrid identifies supported devices.
- `getGroupHybridFlowgraph_v1`: GroupAutoID; response is keyed by GoodsID. A selected inverter must return telemetry before setup completes.

Every payload receives a sign property. The public portal sorts parameter names, omits empty/null/boolean values, joins `name=value` pairs with ampersands, appends an ampersand and its public 32-byte signing key, then applies AES-256-CBC with its public IV and PKCS7 padding. The result is Base64. These constants are public interoperability parameters, not customer credentials. This implementation supports the string/integer parameters used by these four endpoints; it does not send control commands.

Live validation used the portal's advertised demo account, not the owner's credentials. The actual Python client discovered three supported inverters and successfully read SOC, Pbat and ModelName fields for each. The local test used the OS DNS resolver because the Mac test environment's aiodns/pycares versions were incompatible; TLS verification remained enabled.

Tests include independent Node crypto signature vectors, malformed responses, no devices, multiple sites, telemetry validation, authentication renewal and entry identity preservation. Live validation of the owner's Home Assistant setup remains pending. The unofficial protocol may change, and accounts requiring CAPTCHA must resolve that through the provider's portal.


## Expanded monitoring verification (v0.7.0)

Public chunk `409.50f95486.async.js` explicitly maps gridCurrpac > 0 to fromGrid and < 0 to toGrid. The same renderer uses positive battery power for discharge. This verifies the normal portal sign convention; special generator/CT configurations still need an installation-specific check.

`InverterDetailInfoNewone` takes GoodsID and MemberAutoID with the usual signature. The public device-info chunk labels BMS_temp as °C, SOH as %, capacity as Ah, cur and BMS current limits as A, voltage limits as V, and energy counters as kWh. The temperature sentinel below -28°C follows that UI. ETTotal is export; EFTotal is import but may include generator energy. ETotal is inverter generation, not assumed to be AC solar output.

Live requests using the actual client succeeded for three demo inverters and returned all 13 allowlisted fields. Many were empty/sentinels, and current grid flow was unavailable. Thus live numeric import/export and populated BMS values were not verified on that demo; field interpretation is verified against portal code and synthetic regression tests. No customer credentials, serial numbers or response payloads were added to the repository.
