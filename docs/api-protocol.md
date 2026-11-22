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
