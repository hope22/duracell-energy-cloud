"""Automatic setup protocol and flow regression tests, using synthetic data."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.duracell_energy_cloud.api import (
    DuracellAPIError,
    DuracellAuthError,
    DuracellCloudClient,
    request_signature,
)
from custom_components.duracell_energy_cloud.config_flow import DuracellCloudConfigFlow
from custom_components.duracell_energy_cloud.const import AUTH_AUTO


@pytest.mark.parametrize(
    "payload,expected",
    [
        (
            {"MemberID": "test-user", "Password": "p@ss & café", "type": "1"},
            "t99r0dBXHiGGVE1i3eUA3g0jj8Ga0i/jWxUbFTSFj49mcnXb+E54WX7FuPtUCzmi8Dva6XdFMwgYM5e3/lVQLEmjS2IXXqxfB/OKjfrat998fKmVW8bsaqRuUw9k+XkU",
        ),
        (
            {"GroupAutoID": "123"},
            "Fv4RpVwVUu25mN9CGKIjXPsoNCaeQQ1znvZLo5IsEhgPMizRNPMsEzYmVSG0llpdSUkCHKMUe/RHIFcGNJRgIg==",
        ),
        (
            {"MemberAutoID": "12", "inputValue": ""},
            "Z9vjEXzAabp8zJ7/ObwoVfs6GvawNu24bqSk+f6PUxFZEJ/rJCTK7XpavCim7JabMlHe+L/1Kwfa5CUhGtb6HA==",
        ),
    ],
)
def test_independent_node_signature_vectors(payload, expected):
    assert request_signature(payload) == expected


def client():
    return DuracellCloudClient(
        MagicMock(), auth_mode=AUTH_AUTO, username="test-user", password="test-password"
    )


@pytest.mark.asyncio
async def test_discover_multiple_groups_filters_non_hybrid_and_reads_selected():
    api = client()
    api._post = AsyncMock(
        side_effect=[
            {"status": "ok", "token": "synthetic", "MemberAutoID": 12},
            {
                "AllGroupList": [
                    {"AutoID": 1, "GoodsTypeName": "Home"},
                    {"AutoID": 2, "GoodsTypeName": "Garage"},
                ]
            },
            {
                "AllInverterList": [
                    {"GoodsID": "test-a", "isHybrid": True},
                    {"GoodsID": "pv-only", "isHybrid": False},
                ]
            },
            {"AllInverterList": [{"GoodsID": "test-b", "isHybrid": True}]},
            {"test-b": {"SOC": 42}},
        ]
    )
    devices = await api.async_discover()
    assert [d["inverter_id"] for d in devices] == ["test-a", "test-b"]
    assert devices[1]["group_id"] == "2"
    api.select_inverter("test-b", "2")
    assert await api.async_get_flow() == {"SOC": 42}
    for call in api._post.call_args_list:
        body = dict(call.args[1])
        signature = body.pop("sign")
        assert signature == request_signature(body)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response,error",
    [
        ({"status": "error", "errocode": "1"}, DuracellAuthError),
        ({"status": "ok", "token": "synthetic"}, DuracellAPIError),
    ],
)
async def test_login_failure_and_missing_member_id(response, error):
    api = client()
    api._post = AsyncMock(return_value=response)
    with pytest.raises(error):
        await api.async_discover()
    assert api._post.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("groups", [{}, {"AllGroupList": None}, {"AllGroupList": [{}]}])
async def test_malformed_discovery_fails_without_creating_entry(groups):
    api = client()
    api._post = AsyncMock(
        side_effect=[{"status": "ok", "token": "synthetic", "MemberAutoID": 12}, groups]
    )
    with pytest.raises(DuracellAPIError):
        await api.async_discover()


@pytest.mark.asyncio
async def test_automatic_login_renews_expired_session():
    api = client()
    api.select_inverter("test-a", "1")
    api._post = AsyncMock(
        side_effect=[
            {"status": "ok", "token": "old", "MemberAutoID": 12},
            DuracellAuthError(),
            {"status": "ok", "token": "new", "MemberAutoID": 12},
            {"test-a": {"SOC": 40}},
        ]
    )
    assert await api.async_get_flow() == {"SOC": 40}
    assert api._post.await_count == 4
    assert api._post.call_args_list[-1].args[2] == "new"


def flow_fixture(monkeypatch, devices, source="user"):
    flow = DuracellCloudConfigFlow()
    flow.hass = MagicMock()
    flow.context = {"source": source}
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    api = MagicMock()
    api.async_discover = AsyncMock(return_value=devices)
    api.async_get_flow = AsyncMock(return_value={"SOC": 42})
    monkeypatch.setattr(
        "custom_components.duracell_energy_cloud.config_flow.DuracellCloudClient",
        MagicMock(return_value=api),
    )
    monkeypatch.setattr(
        "custom_components.duracell_energy_cloud.config_flow.async_get_clientsession",
        MagicMock(),
    )
    return flow, api


DEVICES = [
    {"inverter_id": "test-a", "group_id": "1", "label": "Home — test-a"},
    {"inverter_id": "test-b", "group_id": "2", "label": "Garage — test-b"},
]
LOGIN = {"username": " test-user ", "password": " exact password "}


@pytest.mark.asyncio
async def test_single_inverter_creates_entry_from_only_credentials(monkeypatch):
    flow, api = flow_fixture(monkeypatch, DEVICES[:1])
    form = await flow.async_step_user()
    assert set(str(k) for k in form["data_schema"].schema) == {"username", "password"}
    result = await flow.async_step_user(LOGIN)
    assert result["data"] == {
        "username": "test-user",
        "password": " exact password ",
        "auth_mode": AUTH_AUTO,
        "inverter_id": "test-a",
        "group_id": "1",
        "poll_seconds": 120,
    }
    api.async_get_flow.assert_awaited_once()
    flow._abort_if_unique_id_configured.assert_called_once()


@pytest.mark.asyncio
async def test_multiple_inverters_requires_selection(monkeypatch):
    flow, api = flow_fixture(monkeypatch, DEVICES)
    result = await flow.async_step_user(LOGIN)
    assert result["step_id"] == "select_inverter"
    api.async_get_flow.assert_not_awaited()
    result = await flow.async_step_select_inverter({"inverter_id": "test-b"})
    assert result["data"]["inverter_id"] == "test-b"
    assert result["data"]["group_id"] == "2"


@pytest.mark.asyncio
async def test_empty_account(monkeypatch):
    flow, api = flow_fixture(monkeypatch, [])
    result = await flow.async_step_user(LOGIN)
    assert result["errors"]["base"] == "no_inverters"
    api.async_get_flow.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["reauth", "reconfigure"])
async def test_existing_entry_migrates_without_changing_identity(monkeypatch, source):
    flow, api = flow_fixture(monkeypatch, DEVICES, source)
    entry = SimpleNamespace(
        data={"inverter_id": "test-b", "flow_sign": "old", "poll_seconds": 300}
    )
    flow._get_reauth_entry = MagicMock(return_value=entry)
    flow._get_reconfigure_entry = MagicMock(return_value=entry)
    flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})
    await flow.async_step_user(LOGIN)
    data = flow.async_update_reload_and_abort.call_args.kwargs["data"]
    assert data["inverter_id"] == "test-b"
    assert data["poll_seconds"] == 300
    assert "flow_sign" not in data
    assert data["auth_mode"] == AUTH_AUTO


@pytest.mark.asyncio
async def test_wrong_account_does_not_replace_existing_inverter(monkeypatch):
    flow, api = flow_fixture(monkeypatch, DEVICES[:1], "reauth")
    flow._get_reauth_entry = MagicMock(
        return_value=SimpleNamespace(data={"inverter_id": "different"})
    )
    result = await flow.async_step_user(LOGIN)
    assert result["reason"] == "wrong_inverter"
    api.async_get_flow.assert_not_awaited()


@pytest.mark.asyncio
async def test_selected_inverter_must_return_telemetry(monkeypatch):
    flow, api = flow_fixture(monkeypatch, DEVICES[:1])
    api.async_get_flow.side_effect = DuracellAPIError()
    result = await flow.async_step_user(LOGIN)
    assert result["type"] == "form"
    assert result["errors"]["base"] == "cannot_connect"
