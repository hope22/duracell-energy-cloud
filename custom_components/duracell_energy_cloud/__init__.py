"""Unofficial, read-only Duracell Energy Cloud integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DuracellCloudClient
from .const import (
    CONF_AUTH_MODE,
    CONF_FLOW_SIGN,
    CONF_GROUP_ID,
    CONF_INVERTER_ID,
    CONF_LOGIN_SIGN,
    CONF_PASSWORD,
    CONF_POLL_SECONDS,
    CONF_TOKEN,
    CONF_USERNAME,
    DEFAULT_POLL_SECONDS,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import DuracellCoordinator
from .dashboard import async_register_dashboard_service


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = entry.data
    client = DuracellCloudClient(
        async_get_clientsession(hass),
        inverter_id=data[CONF_INVERTER_ID],
        group_id=data[CONF_GROUP_ID],
        flow_sign=data.get(CONF_FLOW_SIGN),
        auth_mode=data[CONF_AUTH_MODE],
        username=data.get(CONF_USERNAME),
        password=data.get(CONF_PASSWORD),
        login_sign=data.get(CONF_LOGIN_SIGN),
        token=data.get(CONF_TOKEN),
    )
    coordinator = DuracellCoordinator(
        hass, client, poll_seconds=data.get(CONF_POLL_SECONDS, DEFAULT_POLL_SECONDS)
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_register_dashboard_service(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    result = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if result:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "generate_dashboard")
    return result
