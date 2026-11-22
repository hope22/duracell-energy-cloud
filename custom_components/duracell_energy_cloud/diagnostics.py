"""Allowlisted diagnostics: no credentials, serial numbers or raw API payloads."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_AUTH_MODE, CONF_POLL_SECONDS, DEFAULT_POLL_SECONDS, DOMAIN


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "auth_mode": entry.data[CONF_AUTH_MODE],
        "poll_seconds": entry.data.get(CONF_POLL_SECONDS, DEFAULT_POLL_SECONDS),
        "last_update_success": coordinator.last_update_success,
    }
