"""Cloud connectivity remains visible even when telemetry is unavailable."""

from datetime import timedelta

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_INVERTER_ID, DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [
            DuracellConnectionSensor(
                hass.data[DOMAIN][entry.entry_id], entry.data[CONF_INVERTER_ID]
            )
        ]
    )


class DuracellConnectionSensor(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Cloud connection"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, inverter_id):
        super().__init__(coordinator)
        self._attr_unique_id = f"{inverter_id}_cloud_connection"
        self._attr_device_info = {"identifiers": {(DOMAIN, inverter_id)}}

    @property
    def available(self):
        return True

    @property
    def is_on(self):
        return self.coordinator.connection_status in ("connected", "partial")

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(self.hass, self._tick, timedelta(seconds=30))
        )

    @callback
    def _tick(self, now):
        self.async_write_ha_state()
