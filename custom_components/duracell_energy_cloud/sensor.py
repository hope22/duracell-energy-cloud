"""Read-only sensors mapped from the observed getGroupHybridFlowgraph_v1 JSON."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
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
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import battery_value, numeric_value
from .const import CONF_INVERTER_ID, DOMAIN
from .coordinator import DuracellCoordinator

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
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


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: DuracellCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        DuracellSensor(coordinator, entry.data[CONF_INVERTER_ID], description)
        for description in SENSOR_TYPES
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
        if self.entity_description.key.startswith("battery_"):
            return battery_value(
                (self.coordinator.data or {}).get("Pbat"), self.entity_description.key
            )
        value = (self.coordinator.data or {}).get(self.entity_description.key)
        if self.entity_description.key == "Mode":
            return str(value) if value not in (None, "") else None
        return numeric_value(value)
