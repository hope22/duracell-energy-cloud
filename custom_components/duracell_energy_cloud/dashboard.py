"""Generate a native Lovelace dashboard using actual entity registry IDs."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.core import SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .const import CONF_INVERTER_ID, DOMAIN


def dashboard_view(title, path, entities):
    """No custom frontend cards or hard-coded entity names are required."""
    cards = [
        {
            "type": "markdown",
            "content": "## Your energy at a glance\nEnergy totals are estimates from cloud readings. Solar is DC energy, before inverter losses.",
        }
    ]
    if "cloud_connection" in entities:
        cards.append(
            {
                "type": "conditional",
                "conditions": [
                    {"entity": entities["cloud_connection"], "state": "off"}
                ],
                "card": {
                    "type": "markdown",
                    "content": "### Monitoring connection needs attention\nReadings are unavailable or updates have stopped. Check the connection status below.",
                },
            }
        )
    if "SOC" in entities:
        cards.append(
            {
                "type": "gauge",
                "entity": entities["SOC"],
                "name": "Battery charge",
                "min": 0,
                "max": 100,
                "severity": {"red": 0, "yellow": 20, "green": 40},
            }
        )
    power_keys = [
        "TotalDCpower",
        "loadCurrpac",
        "grid_import_power",
        "grid_export_power",
        "battery_charging_power",
        "battery_discharging_power",
    ]
    power = [entities[k] for k in power_keys if k in entities]
    if power:
        cards.append(
            {
                "type": "grid",
                "columns": 2,
                "square": False,
                "cards": [{"type": "tile", "entity": e} for e in power],
            }
        )
        cards.append(
            {
                "type": "history-graph",
                "title": "Power over the last 24 hours",
                "hours_to_show": 24,
                "entities": power,
            }
        )
    energy_keys = [
        "solar_dc_energy",
        "grid_energy_imported",
        "grid_energy_exported",
        "battery_energy_charged",
        "battery_energy_discharged",
    ]
    energy = [entities[k] for k in energy_keys if k in entities]
    if energy:
        cards.append(
            {
                "type": "statistics-graph",
                "title": "Daily energy · last 7 days",
                "chart_type": "bar",
                "period": "day",
                "days_to_show": 7,
                "stat_types": ["change"],
                "entities": energy,
            }
        )
        cards.append(
            {
                "type": "entities",
                "title": "Accumulated energy",
                "show_header_toggle": False,
                "entities": energy,
            }
        )
    for title_, keys in [
        (
            "Battery information",
            [
                "SOC",
                "volt",
                "BMS_temp",
                "SOH",
                "capacity",
                "cur",
                "bmsChargeCurLimit",
                "bmsDishargeCurLimit",
                "bmsChargeVolLimit",
                "bmsDischargeVolLimit",
            ],
        ),
        (
            "Connection health",
            [
                "cloud_connection",
                "connection_status",
                "last_successful_update",
                "consecutive_failures",
            ],
        ),
    ]:
        selected = [entities[k] for k in keys if k in entities]
        if selected:
            cards.append(
                {
                    "type": "entities",
                    "title": title_,
                    "show_header_toggle": False,
                    "entities": selected,
                }
            )
    return {
        "title": title,
        "path": path,
        "icon": "mdi:home-lightning-bolt",
        "cards": cards,
    }


@callback
def async_register_dashboard_service(hass):
    if hass.services.has_service(DOMAIN, "generate_dashboard"):
        return

    async def generate(call):
        if call.context.user_id:
            user = await hass.auth.async_get_user(call.context.user_id)
            if user is None or not user.is_admin:
                raise HomeAssistantError("Administrator access is required")
        registry = er.async_get(hass)
        views = []
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.entry_id not in hass.data.get(DOMAIN, {}):
                continue
            prefix = entry.data[CONF_INVERTER_ID] + "_"
            entities = {
                e.unique_id[len(prefix) :]: e.entity_id
                for e in er.async_entries_for_config_entry(registry, entry.entry_id)
                if e.platform == DOMAIN
                and e.unique_id.startswith(prefix)
                and e.disabled_by is None
            }
            if entities:
                views.append(
                    dashboard_view(entry.title, f"inverter-{len(views) + 1}", entities)
                )
        if not views:
            raise HomeAssistantError("No loaded Duracell inverter entities were found")
        return {"title": "Duracell Energy", "views": views}

    hass.services.async_register(
        DOMAIN,
        "generate_dashboard",
        generate,
        schema=vol.Schema({}),
        supports_response=SupportsResponse.ONLY,
    )
