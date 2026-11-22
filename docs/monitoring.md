# Connection health and battery details

## Connection health

- **Cloud connection** is on while the last primary monitoring request was successful and recent. It stays available during outages so automations can detect an off state.
- **Connection status** is `connected`, `partial`, `disconnected` or `stale`. `partial` means primary readings work but the optional details request failed or is unavailable (including legacy token-only authentication). `stale` means no successful flow read within twice the polling interval plus 20 seconds.
- **Last successful update** is the time Home Assistant last successfully received the primary flow response, not the inverter's own measurement time.
- **Consecutive failed updates** counts primary read failures and resets after recovery.

Health displays refresh every 30 seconds without additional cloud calls. They do not prove that an inverter is physically online: the provider can return stale measurements successfully, and there is no verified measurement timestamp in the flow response.

Optional details are requested at most once every five minutes (or the polling interval if longer). Details failures don't make working primary readings unavailable. Old details are cleared when a details request fails. Use Reconfigure to move a legacy token entry to username/password authentication for detail access.

## Battery detail sensors

Where the provider supplies them, the integration exposes battery temperature (°C), health (%), reported capacity (Ah), current (A), and BMS charge/discharge current and voltage limits. These are read-only measurements, not controls. Capacity in Ah is not converted to usable kWh. First battery-bank fields are used; a separate second battery-bank view is not implemented.

Missing fields, `-` sentinels and invalid numbers remain unknown. Temperature below the portal's -28°C sentinel cutoff, health outside 0–100%, and nonpositive capacity are treated as unavailable readings. Models and firmware differ, so not every sensor will have a value.

Manufacturer-reported generation, grid and battery cumulative counters are also exposed as **disabled-by-default** sensors. Enable them only after comparing against the portal for your installation. The reported import counter can include generator energy in some connection modes; the generation counter is not assumed to equal solar DC production. Existing battery estimates retain their identity and history and are never silently replaced by these counters.
