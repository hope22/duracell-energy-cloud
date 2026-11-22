"""Synthetic fixtures only; never contact the monitoring provider."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.duracell_energy_cloud.api import (
    DuracellAPIError,
    DuracellAuthError,
    DuracellCloudClient,
    battery_value,
    extract_inverter_data,
    extract_login_token,
    numeric_value,
)
from custom_components.duracell_energy_cloud.config_flow import DuracellCloudConfigFlow
from custom_components.duracell_energy_cloud.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.duracell_energy_cloud.sensor import SENSOR_TYPES, DuracellSensor


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("12.5", 12.5),
        (0, 0),
        (None, None),
        ("", None),
        (True, None),
        ("NaN", None),
        ("inf", None),
        ({}, None),
    ],
)
def test_numeric_values(raw, expected):
    assert numeric_value(raw) == expected


@pytest.mark.parametrize(
    "raw,charge,discharge,activity",
    [
        (120, 0, 120, "discharging"),
        (-80, 80, 0, "charging"),
        (0, 0, 0, "idle"),
        (None, None, None, None),
    ],
)
def test_battery_direction(raw, charge, discharge, activity):
    assert battery_value(raw, "battery_charging_power") == charge
    assert battery_value(raw, "battery_discharging_power") == discharge
    assert battery_value(raw, "battery_activity") == activity


def test_select_only_requested_inverter():
    assert extract_inverter_data(
        {"test-a": {"SOC": 50}, "test-b": {"SOC": 80}}, "test-a"
    ) == {"SOC": 50}
    with pytest.raises(DuracellAPIError):
        extract_inverter_data({"test-b": {"SOC": 80}}, "test-a")


def test_auth_and_token_parsing():
    assert (
        extract_login_token({"data": {"token": "Bearer synthetic-token"}})
        == "synthetic-token"
    )
    with pytest.raises(DuracellAuthError):
        extract_inverter_data({"code": 401}, "test-a")
    with pytest.raises(DuracellAuthError):
        extract_login_token({"data": {}})


def client(mode="password"):
    return DuracellCloudClient(
        MagicMock(),
        inverter_id="test-a",
        group_id="test-group",
        flow_sign="test-sign",
        auth_mode=mode,
        username="test-user",
        password="test-password",
        login_sign="test-login-sign",
        token="test-token",
    )


@pytest.mark.asyncio
async def test_password_retries_only_once():
    api = client()
    api._async_login = AsyncMock(side_effect=["first-token", "second-token"])
    api._post = AsyncMock(side_effect=[DuracellAuthError(), {"test-a": {"SOC": 50}}])
    assert await api.async_get_flow() == {"SOC": 50}
    assert api._async_login.await_count == 2
    assert api._post.await_count == 2


@pytest.mark.asyncio
async def test_second_auth_failure_propagates():
    api = client()
    api._async_login = AsyncMock(return_value="test-token")
    api._post = AsyncMock(side_effect=DuracellAuthError())
    with pytest.raises(DuracellAuthError):
        await api.async_get_flow()
    assert api._post.await_count == 2


@pytest.mark.asyncio
async def test_token_never_attempts_password_login():
    api = client("token")
    api._async_login = AsyncMock()
    api._post = AsyncMock(side_effect=DuracellAuthError())
    with pytest.raises(DuracellAuthError):
        await api.async_get_flow()
    api._async_login.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,error",
    [(302, DuracellAPIError), (401, DuracellAuthError), (500, DuracellAPIError)],
)
async def test_http_errors_and_redirects(status, error):
    api = client()
    response = MagicMock(status=status)
    api._session.post.return_value.__aenter__ = AsyncMock(return_value=response)
    with pytest.raises(error):
        await api._post("https://example.invalid", {}, "synthetic-token")
    assert api._session.post.call_args.kwargs["allow_redirects"] is False


def test_original_unique_ids_and_sensor_values():
    coordinator = SimpleNamespace(
        data={"SOC": 55, "Pbat": -100}, last_update_success=True
    )
    for description in SENSOR_TYPES:
        sensor = DuracellSensor(coordinator, "test-a", description)
        assert sensor.unique_id == f"test-a_{description.key}"
        if description.key == "SOC":
            assert sensor.native_value == 55
        if description.key == "battery_charging_power":
            assert sensor.native_value == 100
    assert len(SENSOR_TYPES) == 14


@pytest.mark.asyncio
async def test_diagnostics_omit_secrets_and_telemetry():
    entry = SimpleNamespace(
        entry_id="test",
        data={"auth_mode": "token", "token": "secret", "inverter_id": "private-serial"},
    )
    hass = SimpleNamespace(
        data={
            "duracell_energy_cloud": {
                "test": SimpleNamespace(
                    last_update_success=True, data={"private": "secret"}
                )
            }
        }
    )
    assert await async_get_config_entry_diagnostics(hass, entry) == {
        "auth_mode": "token",
        "poll_seconds": 120,
        "last_update_success": True,
        "details_available": False,
        "last_successful_update": None,
        "consecutive_failures": 0,
    }


@pytest.mark.asyncio
async def test_setup_stores_trimmed_values(monkeypatch):
    flow = DuracellCloudConfigFlow()
    flow.hass = MagicMock()
    flow.context = {"source": "user"}
    flow._mode = "token"
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    api = MagicMock()
    api.async_get_flow = AsyncMock(return_value={"SOC": 50})
    monkeypatch.setattr(
        "custom_components.duracell_energy_cloud.config_flow.DuracellCloudClient",
        MagicMock(return_value=api),
    )
    monkeypatch.setattr(
        "custom_components.duracell_energy_cloud.config_flow.async_get_clientsession",
        MagicMock(),
    )
    result = await flow.async_step_details(
        {
            "inverter_id": " test-a ",
            "group_id": " group ",
            "flow_sign": " sign ",
            "token": " token ",
            "poll_seconds": 120,
        }
    )
    assert result["data"]["flow_sign"] == "sign"
    assert result["data"]["token"] == "token"


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["reauth", "reconfigure"])
async def test_updates_existing_entry(source, monkeypatch):
    flow = DuracellCloudConfigFlow()
    flow.hass = MagicMock()
    flow.context = {"source": source}
    flow._mode = "token"
    flow.async_set_unique_id = AsyncMock()
    entry = SimpleNamespace(data={"inverter_id": "test-a"})
    flow._get_reauth_entry = MagicMock(return_value=entry)
    flow._get_reconfigure_entry = MagicMock(return_value=entry)
    flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})
    api = MagicMock()
    api.async_get_flow = AsyncMock(return_value={"SOC": 50})
    monkeypatch.setattr(
        "custom_components.duracell_energy_cloud.config_flow.DuracellCloudClient",
        MagicMock(return_value=api),
    )
    monkeypatch.setattr(
        "custom_components.duracell_energy_cloud.config_flow.async_get_clientsession",
        MagicMock(),
    )
    await flow.async_step_details(
        {
            "inverter_id": "test-a",
            "group_id": "group",
            "flow_sign": "sign",
            "token": "token",
            "poll_seconds": 120,
        }
    )
    flow.async_update_reload_and_abort.assert_called_once()


@pytest.mark.asyncio
async def test_changed_inverter_rejected(monkeypatch):
    flow = DuracellCloudConfigFlow()
    flow.hass = MagicMock()
    flow.context = {"source": "reauth"}
    flow._mode = "token"
    flow.async_set_unique_id = AsyncMock()
    flow._get_reauth_entry = MagicMock(
        return_value=SimpleNamespace(data={"inverter_id": "original"})
    )
    api = MagicMock()
    api.async_get_flow = AsyncMock(return_value={"SOC": 50})
    monkeypatch.setattr(
        "custom_components.duracell_energy_cloud.config_flow.DuracellCloudClient",
        MagicMock(return_value=api),
    )
    monkeypatch.setattr(
        "custom_components.duracell_energy_cloud.config_flow.async_get_clientsession",
        MagicMock(),
    )
    result = await flow.async_step_details(
        {
            "inverter_id": "different",
            "group_id": "group",
            "flow_sign": "sign",
            "token": "token",
            "poll_seconds": 120,
        }
    )
    assert result["reason"] == "wrong_inverter"
