"""Energy integration, restoration and coordinator lifecycle tests."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorExtraStoredData,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoredExtraData

from custom_components.duracell_energy_cloud.energy import EnergyAccumulator
from custom_components.duracell_energy_cloud.sensor import (
    ENERGY_TYPES,
    DuracellEnergySensor,
    async_setup_entry,
)


def test_one_kilowatt_for_one_hour():
    energy = EnergyAccumulator(260)
    for seconds in range(0, 3601, 120):
        energy.sample(1000, seconds)
    assert energy.total == pytest.approx(1.0)


def test_left_sum_and_zero_power():
    energy = EnergyAccumulator(260)
    energy.sample(3000, 0)
    energy.sample(0, 120)
    energy.sample(0, 240)
    assert energy.total == pytest.approx(0.1)


@pytest.mark.parametrize(
    "invalid", [None, "unknown", "unavailable", "NaN", "inf", True, -1]
)
def test_invalid_sample_breaks_integration(invalid):
    energy = EnergyAccumulator(260)
    energy.sample(3000, 0)
    energy.sample(invalid, 120)
    energy.sample(3000, 240)
    assert energy.total == 0
    energy.sample(3000, 360)
    assert energy.total == pytest.approx(0.1)


def test_long_gap_and_duplicate_timestamps():
    energy = EnergyAccumulator(260)
    energy.sample(3000, 0)
    energy.sample(3000, 3600)
    energy.sample(3000, 3600)
    assert energy.total == 0
    energy.sample(3000, 3720)
    assert energy.total == pytest.approx(0.1)


def test_restore_never_integrates_downtime():
    energy = EnergyAccumulator(260)
    energy.sample(3000, 0)
    energy.restore(12.3456789)
    energy.sample(3000, 100000)
    assert energy.total == 12.3456789
    energy.sample(3000, 100120)
    assert energy.total == pytest.approx(12.4456789)


@pytest.mark.parametrize("invalid", [-1, "NaN", "inf", None, True])
def test_invalid_restored_total(invalid):
    energy = EnergyAccumulator(260)
    energy.restore(invalid)
    assert energy.total == 0


def make_sensor(description=ENERGY_TYPES[0]):
    listeners = []

    def add_listener(listener, context):
        listeners.append(listener)
        return lambda: listeners.remove(listener)

    coordinator = SimpleNamespace(
        data={"Pbat": -3000},
        last_update_success=True,
        update_interval=timedelta(seconds=120),
        async_add_listener=add_listener,
    )
    sensor = DuracellEnergySensor(coordinator, "test-inverter", description)
    sensor.async_write_ha_state = MagicMock()
    return sensor, coordinator, listeners


@pytest.mark.asyncio
async def test_native_restore_data_and_polling_callbacks(monkeypatch, tmp_path):
    clock = [0.0]
    monkeypatch.setattr(
        "custom_components.duracell_energy_cloud.sensor.monotonic", lambda: clock[0]
    )
    sensor, coordinator, listeners = make_sensor()
    sensor.hass = HomeAssistant(str(tmp_path))
    # Exercise real RestoreSensor deserialization, including precision and unit.
    saved = SensorExtraStoredData(12.123456789, "kWh").as_dict()
    sensor.async_get_last_extra_data = AsyncMock(return_value=RestoredExtraData(saved))
    await sensor.async_added_to_hass()
    assert len(listeners) == 1
    assert sensor.native_value == 12.123456789
    clock[0] = 120
    listeners[0]()
    assert sensor.native_value == pytest.approx(12.223456789)
    assert (
        sensor.extra_restore_state_data.as_dict()["native_value"] == sensor.native_value
    )
    assert sensor.available
    coordinator.last_update_success = False
    clock[0] = 240
    listeners[0]()
    assert not sensor.available
    coordinator.last_update_success = True
    clock[0] = 360
    listeners[0]()
    assert sensor.native_value == pytest.approx(12.223456789)
    clock[0] = 480
    listeners[0]()
    assert sensor.native_value == pytest.approx(12.323456789)
    # Simulate a reload: restore the total, with no previous interval carried over.
    restored, _, _ = make_sensor()
    restored.hass = sensor.hass
    restored.async_get_last_extra_data = AsyncMock(
        return_value=RestoredExtraData(sensor.extra_restore_state_data.as_dict())
    )
    clock[0] = 100000
    await restored.async_added_to_hass()
    assert restored.native_value == sensor.native_value
    await restored.async_will_remove_from_hass()
    await sensor.async_will_remove_from_hass()


@pytest.mark.parametrize("description", ENERGY_TYPES)
def test_energy_dashboard_metadata_and_existing_device(description):
    sensor, _, _ = make_sensor(description)
    assert sensor.device_class == SensorDeviceClass.ENERGY
    assert sensor.state_class == SensorStateClass.TOTAL_INCREASING
    assert sensor.native_unit_of_measurement == "kWh"
    assert sensor.unique_id == f"test-inverter_{description.key}"
    assert sensor.device_info["identifiers"] == {
        ("duracell_energy_cloud", "test-inverter")
    }
    assert sensor.extra_state_attributes["estimated"] is True
    assert sensor.should_poll is False


def test_charge_and_discharge_are_separate(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(
        "custom_components.duracell_energy_cloud.sensor.monotonic", lambda: clock[0]
    )
    charge, coordinator, _ = make_sensor(ENERGY_TYPES[0])
    discharge = DuracellEnergySensor(coordinator, "test-inverter", ENERGY_TYPES[1])
    discharge.async_write_ha_state = MagicMock()
    for seconds, power in [(0, -3000), (120, 6000), (240, 0), (360, 0)]:
        clock[0] = seconds
        coordinator.data = {"Pbat": power}
        charge._handle_coordinator_update()
        discharge._handle_coordinator_update()
    assert charge.native_value == pytest.approx(0.1)
    assert discharge.native_value == pytest.approx(0.2)
    coordinator.data = {}
    charge._handle_coordinator_update()
    assert not charge.available
    assert charge.native_value == pytest.approx(0.1)


@pytest.mark.asyncio
async def test_setup_adds_two_energy_entities_without_helpers():
    _, coordinator, _ = make_sensor()
    hass = SimpleNamespace(data={"duracell_energy_cloud": {"entry": coordinator}})
    entry = SimpleNamespace(entry_id="entry", data={"inverter_id": "test-inverter"})
    added = MagicMock()
    await async_setup_entry(hass, entry, added)
    entities = added.call_args.args[0]
    assert len(entities) == 35
    assert len({e.unique_id for e in entities}) == 35
    assert sum(isinstance(e, DuracellEnergySensor) for e in entities) == 5
