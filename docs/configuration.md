# Configuration

Use your own account at the Duracell monitoring portal. Connection values belong in the local Home Assistant setup form, never in GitHub issues.

In the browser developer tools, use the Network tab while logging in and viewing your inverter's power-flow screen. Inspect the requests without exporting or sharing a full HAR file.

| Field | Source |
| --- | --- |
| Inverter ID | Exact inverter key in the `getGroupHybridFlowgraph_v1` JSON response |
| GroupAutoID | `GroupAutoID` in that request's JSON body |
| Flowgraph request sign | `sign` in that request's body |
| Login request sign | `sign` in the `UserLogin_v1` request body; different from the flowgraph signature |
| Username / password | Your monitoring account credentials |
| Monitoring token | Raw Authorization header value used by the monitoring request, without a Bearer prefix |

Password mode attempts login and retries once after a rejected session. Token mode cannot automatically renew an expired token; Home Assistant will request reauthentication. Signatures may stop working if the provider changes its authentication scheme.

Polling defaults to 120 seconds and is constrained to 60–3600 seconds. Use the integration entry's **Reconfigure** action to change connection details or polling. Reconfiguration keeps the same inverter identity; add another entry for a different inverter.

Credentials are stored by Home Assistant in its local configuration storage. Protect configuration backups accordingly. Never commit configuration exports, HAR captures or account tokens.
