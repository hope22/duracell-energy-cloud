"""Read-only sensors mapped from the observed getGroupHybridFlowgraph_v1 JSON."""

from __future__ import annotations

from datetime import timedelta
from time import monotonic
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import battery_value, numeric_value
from .const import CONF_INVERTER_ID, DOMAIN
from .coordinator import DuracellCoordinator
from .energy import EnergyAccumulator
from .telemetry import (
    DETAIL_DEFINITIONS,
    DETAIL_FIELDS,
    ENERGY_SOURCES,
    detail_value,
    power_value,
)

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    *(
        SensorEntityDescription(
            key=key,
            name=name,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        )
        for key, name in [
            ("grid_import_power", "Grid import power"),
            ("grid_export_power", "Grid export power"),
        ]
    ),
    SensorEntityDescription(
        key="battery_charging_power",
        name="Battery charging power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="battery_discharging_power",
        name="Battery discharging power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="battery_activity",
        name="Battery activity",
        icon="mdi:battery-sync",
    ),
    SensorEntityDescription(
        key="SOC",
        name="Battery state of charge",
        icon="mdi:battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Pbat",
        name="Battery power (signed)",
        icon="mdi:battery-arrow-down-outline",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="volt",
        name="Battery voltage",
        icon="mdi:flash",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="TotalDCpower",
        name="PV DC power (reported)",
        icon="mdi:solar-power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="loadCurrpac",
        name="Home load power",
        icon="mdi:home-lightning-bolt",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="gridCurrpac",
        name="Grid power (signed)",
        icon="mdi:transmission-tower",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="epsCurrpac",
        name="Backup EPS power",
        icon="mdi:power-plug",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="genCurrpac",
        name="Generator power",
        icon="mdi:engine",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Mode",
        name="Inverter mode code",
        icon="mdi:information-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


ENERGY_TYPES = (
    *(
        SensorEntityDescription(
            key=key,
            name=name,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            suggested_display_precision=3,
        )
        for key, name in [
            ("grid_energy_imported", "Grid energy imported"),
            ("grid_energy_exported", "Grid energy exported"),
            ("solar_dc_energy", "Solar DC energy (estimated)"),
        ]
    ),
    SensorEntityDescription(
        key="battery_energy_charged",
        name="Battery energy charged",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=3,
    ),
    SensorEntityDescription(
        key="battery_energy_discharged",
        name="Battery energy discharged",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=3,
    ),
)

# Keep the existing battery entities first, including their stable unique IDs.
ENERGY_TYPES = tuple(
    sorted(
        ENERGY_TYPES, key=lambda description: not description.key.startswith("battery_")
    )
)
HEALTH_TYPES = (
    SensorEntityDescription(
        key="connection_status",
        name="Connection status",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="last_successful_update",
        name="Last successful update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="consecutive_failures",
        name="Consecutive failed updates",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


DETAIL_TYPES = tuple(
    SensorEntityDescription(
        key=key,
        name=name,
        native_unit_of_measurement=unit,
        device_class=kind,
        state_class=SensorStateClass.TOTAL_INCREASING
        if kind == "energy"
        else SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=kind != "energy",
    )
    for key, name, unit, kind, _, _ in DETAIL_DEFINITIONS
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: DuracellCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            *(
                DuracellSensor(coordinator, entry.data[CONF_INVERTER_ID], description)
                for description in (*SENSOR_TYPES, *DETAIL_TYPES)
            ),
            *(
                DuracellHealthSensor(
                    coordinator, entry.data[CONF_INVERTER_ID], description
                )
                for description in HEALTH_TYPES
            ),
            *(
                DuracellEnergySensor(
                    coordinator, entry.data[CONF_INVERTER_ID], description
                )
                for description in ENERGY_TYPES
            ),
        ]
    )


class DuracellSensor(CoordinatorEntity[DuracellCoordinator], SensorEntity):
    """One entity sourced from the shared response, not a separate request."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DuracellCoordinator,
        inverter_id: str,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._inverter_id = inverter_id
        self._attr_unique_id = f"{inverter_id}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        raw: dict[str, Any] = self.coordinator.data or {}
        return DeviceInfo(
            identifiers={(DOMAIN, self._inverter_id)},
            manufacturer="Duracell Energy",
            model=str(raw.get("ModelName") or "Dura-i G3"),
            sw_version=str(raw.get("MDSPVersion") or "unknown"),
            name=f"Dura-i G3 {self._inverter_id[-4:]}",
        )

    @property
    def native_value(self) -> float | str | None:
        if self.entity_description.key in DETAIL_FIELDS:
            return detail_value(
                self.coordinator.data or {}, self.entity_description.key
            )
        if self.entity_description.key in ("grid_import_power", "grid_export_power"):
            return power_value(self.coordinator.data or {}, self.entity_description.key)
        if self.entity_description.key.startswith("battery_"):
            return battery_value(
                (self.coordinator.data or {}).get("Pbat"), self.entity_description.key
            )
        value = (self.coordinator.data or {}).get(self.entity_description.key)
        if self.entity_description.key == "Mode":
            return str(value) if value not in (None, "") else None
        return numeric_value(value)


class DuracellEnergySensor(DuracellSensor, RestoreSensor):
    """Persistent, estimated battery energy without manually configured helpers."""

    _attr_extra_state_attributes = {"estimated": True, "integration_method": "left"}

    def __init__(self, coordinator, inverter_id, description) -> None:
        super().__init__(coordinator, inverter_id, description)
        # Permit ordinary request latency, but never bridge a prolonged polling gap.
        interval = coordinator.update_interval.total_seconds()
        self._energy = EnergyAccumulator(max_gap_seconds=2 * interval + 20)
        self._power_key = ENERGY_SOURCES[description.key]

    async def async_added_to_hass(self) -> None:
        # Restore the native kWh total before starting a new sampling interval.
        await super().async_added_to_hass()
        restored = await self.async_get_last_sensor_data()
        if (
            restored is not None
            and restored.native_unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR
        ):
            self._energy.restore(restored.native_value)
        self._sample_energy()

    @property
    def available(self) -> bool:
        return (
            super().available
            and power_value(self.coordinator.data or {}, self._power_key) is not None
        )

    @property
    def native_value(self) -> float:
        # Keep full precision for persistence and recorder; display precision is separate.
        return self._energy.total

    @callback
    def _sample_energy(self) -> None:
        power = (
            power_value(self.coordinator.data or {}, self._power_key)
            if self.coordinator.last_update_success
            else None
        )
        self._energy.sample(power, monotonic())

    @callback
    def _handle_coordinator_update(self) -> None:
        self._sample_energy()
        self.async_write_ha_state()


class DuracellHealthSensor(DuracellSensor):
    """Keep diagnostic state available through a cloud outage."""

    @property
    def available(self):
        return True

    @property
    def native_value(self):
        return getattr(self.coordinator, self.entity_description.key)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(self.hass, self._tick, timedelta(seconds=30))
        )

    @callback
    def _tick(self, now):
        self.async_write_ha_state()
