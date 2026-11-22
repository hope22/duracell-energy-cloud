"""Field definitions verified against the provider's monitoring UI."""

from .api import battery_value, numeric_value

# Field, display name, unit, device class, valid minimum, valid maximum.
DETAIL_DEFINITIONS = (
    ("BMS_temp", "Battery temperature", "°C", "temperature", -28, 100),
    ("SOH", "Battery health", "%", None, 0, 100),
    ("capacity", "Battery capacity (reported)", "Ah", None, 0.001, None),
    ("cur", "Battery current", "A", "current", None, None),
    ("bmsChargeCurLimit", "Battery charge current limit", "A", "current", 0, None),
    ("bmsDishargeCurLimit", "Battery discharge current limit", "A", "current", 0, None),
    ("bmsChargeVolLimit", "Battery charge voltage limit", "V", "voltage", 0, None),
    (
        "bmsDischargeVolLimit",
        "Battery discharge voltage limit",
        "V",
        "voltage",
        0,
        None,
    ),
    ("ETotal", "Inverter generation total (reported)", "kWh", "energy", 0, None),
    ("ETTotal", "Grid export total (reported)", "kWh", "energy", 0, None),
    ("EFTotal", "Grid or generator import total (reported)", "kWh", "energy", 0, None),
    ("Etotal_batChrg", "Battery charge total (reported)", "kWh", "energy", 0, None),
    (
        "Etotal_batDischrg",
        "Battery discharge total (reported)",
        "kWh",
        "energy",
        0,
        None,
    ),
)
DETAIL_FIELDS = {row[0] for row in DETAIL_DEFINITIONS}
DETAIL_LIMITS = {row[0]: row[4:] for row in DETAIL_DEFINITIONS}
ENERGY_SOURCES = {
    "battery_energy_charged": "battery_charging_power",
    "battery_energy_discharged": "battery_discharging_power",
    "grid_energy_imported": "grid_import_power",
    "grid_energy_exported": "grid_export_power",
    "solar_dc_energy": "solar_dc_power",
}


def power_value(data, key):
    if key.startswith("battery_"):
        return battery_value(data.get("Pbat"), key)
    if key == "solar_dc_power":
        value = numeric_value(data.get("TotalDCpower"))
        return max(value, 0) if value is not None else None
    value = numeric_value(data.get("gridCurrpac"))
    if value is None:
        return None
    if key == "grid_import_power":
        return max(value, 0)
    if key == "grid_export_power":
        return max(-value, 0)
    return None


def detail_value(data, key):
    value = numeric_value(data.get("details", {}).get(key))
    low, high = DETAIL_LIMITS[key]
    if (
        value is None
        or (low is not None and value < low)
        or (high is not None and value > high)
    ):
        return None
    return value
