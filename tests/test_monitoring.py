"""Verified telemetry mappings, failure isolation and dashboard regression tests."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util

from custom_components.duracell_energy_cloud.api import (
    DuracellAPIError,
    DuracellAuthError,
    DuracellCloudClient,
)
from custom_components.duracell_energy_cloud.binary_sensor import (
    DuracellConnectionSensor,
)
from custom_components.duracell_energy_cloud.coordinator import DuracellCoordinator
from custom_components.duracell_energy_cloud.dashboard import (
    async_register_dashboard_service,
    dashboard_view,
)
from custom_components.duracell_energy_cloud.sensor import (
    ENERGY_TYPES,
    DuracellEnergySensor,
)
from custom_components.duracell_energy_cloud.telemetry import detail_value, power_value


@pytest.mark.parametrize(
    "signed,imported,exported",
    [
        (1000, 1000, 0),
        (-500, 0, 500),
        (0, 0, 0),
        (None, None, None),
        ("bad", None, None),
    ],
)
def test_verified_grid_sign(signed, imported, exported):
    assert power_value({"gridCurrpac": signed}, "grid_import_power") == imported
    assert power_value({"gridCurrpac": signed}, "grid_export_power") == exported


@pytest.mark.parametrize(
    "key,raw,expected",
    [
        ("BMS_temp", -100, None),
        ("BMS_temp", 0, 0),
        ("SOH", 105, None),
        ("SOH", 95, 95),
        ("capacity", 0, None),
        ("capacity", 314, 314),
        ("bmsChargeCurLimit", "-", None),
        ("bmsChargeCurLimit", 0, 0),
        ("ETTotal", 123.45, 123.45),
    ],
)
def test_optional_fields_do_not_invent_zero(key, raw, expected):
    assert detail_value({"details": {key: raw}}, key) == expected
    assert detail_value({}, key) is None


@pytest.mark.asyncio
async def test_detail_identity_and_allowlist():
    client = DuracellCloudClient(
        MagicMock(),
        auth_mode="automatic",
        username="test",
        password="test",
        inverter_id="test-a",
    )
    client._token = "synthetic"
    client._member_id = "12"
    client._post = AsyncMock(
        return_value={
            "GoodsID": "test-a",
            "BMS_temp": 25,
            "SOH": 99,
            "password": "secret",
            "MemberID": "private",
        }
    )
    assert await client.async_get_details() == {"BMS_temp": 25, "SOH": 99}
    client._post.return_value = {"GoodsID": "other", "BMS_temp": 30}
    with pytest.raises(DuracellAPIError):
        await client.async_get_details()


@pytest.mark.asyncio
async def test_optional_details_failure_does_not_break_monitoring(
    tmp_path, monkeypatch
):
    now = [0]
    monkeypatch.setattr(
        "custom_components.duracell_energy_cloud.coordinator.monotonic", lambda: now[0]
    )
    client = SimpleNamespace(
        async_get_flow=AsyncMock(return_value={"SOC": 50, "Pbat": 100}),
        async_get_details=AsyncMock(side_effect=DuracellAPIError()),
    )
    hass = HomeAssistant(str(tmp_path))
    coord = DuracellCoordinator(hass, client)
    data = await coord._async_update_data()
    assert data["SOC"] == 50 and data["details"] == {}
    assert coord.connection_status == "partial"
    assert coord.last_successful_update is not None
    now[0] = 120
    await coord._async_update_data()
    assert client.async_get_details.await_count == 1
    now[0] = 360
    client.async_get_details.side_effect = None
    client.async_get_details.return_value = {"SOH": 99}
    data = await coord._async_update_data()
    assert data["details"] == {"SOH": 99}
    assert coord.connection_status == "connected"
    coord.last_successful_update = dt_util.utcnow() - timedelta(seconds=300)
    assert coord.connection_status == "stale"
    await coord.async_shutdown()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error,expected",
    [(DuracellAPIError(), UpdateFailed), (DuracellAuthError(), ConfigEntryAuthFailed)],
)
async def test_failure_counter_and_recovery(tmp_path, error, expected):
    client = SimpleNamespace(
        async_get_flow=AsyncMock(side_effect=error),
        async_get_details=AsyncMock(return_value={}),
    )
    coord = DuracellCoordinator(HomeAssistant(str(tmp_path)), client)
    for count in [1, 2]:
        with pytest.raises(expected):
            await coord._async_update_data()
        assert coord.consecutive_failures == count
    assert coord.last_successful_update is None
    client.async_get_flow.side_effect = None
    client.async_get_flow.return_value = {"Pbat": 0}
    await coord._async_update_data()
    assert coord.consecutive_failures == 0
    await coord.async_shutdown()


@pytest.mark.parametrize(
    "status,on",
    [("connected", True), ("partial", True), ("stale", False), ("disconnected", False)],
)
def test_connectivity_stays_available_during_failure(status, on):
    entity = DuracellConnectionSensor(
        SimpleNamespace(connection_status=status), "test-a"
    )
    assert entity.available is True
    assert entity.is_on is on


@pytest.mark.parametrize(
    "key,source,value",
    [
        ("grid_energy_imported", "gridCurrpac", 3000),
        ("grid_energy_exported", "gridCurrpac", -3000),
        ("solar_dc_energy", "TotalDCpower", 3000),
    ],
)
def test_new_energy_sources_and_missing_readings(monkeypatch, key, source, value):
    clock = [0]
    monkeypatch.setattr(
        "custom_components.duracell_energy_cloud.sensor.monotonic", lambda: clock[0]
    )
    coordinator = SimpleNamespace(
        data={source: value},
        last_update_success=True,
        update_interval=timedelta(seconds=120),
    )
    entity = DuracellEnergySensor(
        coordinator, "test-a", next(d for d in ENERGY_TYPES if d.key == key)
    )
    entity.async_write_ha_state = MagicMock()
    entity._handle_coordinator_update()
    clock[0] = 120
    entity._handle_coordinator_update()
    assert entity.native_value == pytest.approx(0.1)
    assert entity.available
    coordinator.data = {}
    clock[0] = 240
    entity._handle_coordinator_update()
    assert not entity.available
    coordinator.data = {source: value}
    clock[0] = 360
    entity._handle_coordinator_update()
    assert entity.native_value == pytest.approx(0.1)


def test_dashboard_uses_actual_renamed_entities_and_native_cards():
    entities = {
        k: "sensor.custom_" + str(i)
        for i, k in enumerate(
            [
                "SOC",
                "TotalDCpower",
                "loadCurrpac",
                "battery_energy_charged",
                "solar_dc_energy",
                "BMS_temp",
                "connection_status",
            ]
        )
    }
    entities["cloud_connection"] = "binary_sensor.custom_connection"
    view = dashboard_view("Home", "inverter-1", entities)
    assert view["title"] == "Home"
    assert any(c["type"] == "conditional" for c in view["cards"])
    assert any(c["type"] == "statistics-graph" for c in view["cards"])
    import json

    content = json.dumps(view)
    assert "custom:" not in content
    for entity_id in entities.values():
        assert entity_id in content
    assert "sensor.duracell" not in content


@pytest.mark.asyncio
async def test_dashboard_service_denies_non_admin(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    hass.auth = SimpleNamespace(
        async_get_user=AsyncMock(return_value=SimpleNamespace(is_admin=False))
    )
    async_register_dashboard_service(hass)
    from homeassistant.core import Context
    from homeassistant.exceptions import HomeAssistantError

    with pytest.raises(HomeAssistantError, match="Administrator"):
        await hass.services.async_call(
            "duracell_energy_cloud",
            "generate_dashboard",
            {},
            blocking=True,
            return_response=True,
            context=Context(user_id="test"),
        )


@pytest.mark.asyncio
async def test_dashboard_generation_for_multiple_inverters(tmp_path, monkeypatch):
    hass = HomeAssistant(str(tmp_path))
    entries = [
        SimpleNamespace(entry_id="one", title="Home", data={"inverter_id": "test-a"}),
        SimpleNamespace(entry_id="two", title="Garage", data={"inverter_id": "test-b"}),
    ]
    hass.config_entries = SimpleNamespace(async_entries=lambda domain: entries)
    hass.data["duracell_energy_cloud"] = {"one": object(), "two": object()}
    registry = object()
    monkeypatch.setattr(
        "custom_components.duracell_energy_cloud.dashboard.er.async_get",
        lambda _: registry,
    )

    def entities(_, entry_id):
        serial = "test-a" if entry_id == "one" else "test-b"
        return [
            SimpleNamespace(
                unique_id=serial + "_SOC",
                entity_id="sensor.renamed_" + entry_id,
                platform="duracell_energy_cloud",
                disabled_by=None,
            ),
            SimpleNamespace(
                unique_id=serial + "_capacity",
                entity_id="sensor.disabled",
                platform="duracell_energy_cloud",
                disabled_by="user",
            ),
        ]

    monkeypatch.setattr(
        "custom_components.duracell_energy_cloud.dashboard.er.async_entries_for_config_entry",
        entities,
    )
    async_register_dashboard_service(hass)
    result = await hass.services.async_call(
        "duracell_energy_cloud",
        "generate_dashboard",
        {},
        blocking=True,
        return_response=True,
    )
    assert [v["title"] for v in result["views"]] == ["Home", "Garage"]
    assert result["views"][0]["path"] != result["views"][1]["path"]
    assert "sensor.disabled" not in str(result)
    assert "sensor.renamed_one" in str(result["views"][0])
    assert "sensor.renamed_two" not in str(result["views"][0])
