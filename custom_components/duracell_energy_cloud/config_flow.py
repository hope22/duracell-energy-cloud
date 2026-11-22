"""Duracell Energy Cloud setup; all secrets entered into local Home Assistant."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DuracellAPIError, DuracellAuthError, DuracellCloudClient
from .const import (
    AUTH_AUTO,
    AUTH_PASSWORD,
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
    MIN_POLL_SECONDS,
)

_SECRET = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
)


def _details_schema(mode: str, data: dict | None = None) -> vol.Schema:
    data = data or {}
    fields: dict = {
        vol.Required(CONF_INVERTER_ID, default=data.get(CONF_INVERTER_ID, "")): str,
        vol.Required(CONF_GROUP_ID, default=data.get(CONF_GROUP_ID, "")): str,
        vol.Required(CONF_FLOW_SIGN, default=data.get(CONF_FLOW_SIGN, "")): _SECRET,
        vol.Required(
            CONF_POLL_SECONDS,
            default=data.get(CONF_POLL_SECONDS, DEFAULT_POLL_SECONDS),
        ): vol.All(vol.Coerce(int), vol.Range(min=MIN_POLL_SECONDS, max=3600)),
    }
    if mode == AUTH_PASSWORD:
        fields.update(
            {
                vol.Required(CONF_USERNAME, default=data.get(CONF_USERNAME, "")): str,
                vol.Required(CONF_PASSWORD): _SECRET,
                vol.Required(
                    CONF_LOGIN_SIGN, default=data.get(CONF_LOGIN_SIGN, "")
                ): _SECRET,
            }
        )
    else:
        fields[vol.Required(CONF_TOKEN)] = _SECRET
    return vol.Schema(fields)


class DuracellCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure a private monitoring account without sending secrets to chat."""

    VERSION = 2

    def __init__(self) -> None:
        self._mode = AUTH_PASSWORD
        self._credentials = {}
        self._devices = {}
        self._client = None

    async def async_step_reauth(self, entry_data: dict):
        return await self.async_step_user()

    async def async_step_reconfigure(self, user_input: dict | None = None):
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input: dict | None = None):
        errors = {}
        if user_input is not None:
            self._credentials = {
                CONF_AUTH_MODE: AUTH_AUTO,
                CONF_USERNAME: user_input[CONF_USERNAME].strip(),
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            self._client = DuracellCloudClient(
                async_get_clientsession(self.hass),
                auth_mode=AUTH_AUTO,
                username=self._credentials[CONF_USERNAME],
                password=self._credentials[CONF_PASSWORD],
            )
            try:
                devices = await self._client.async_discover()
            except DuracellAuthError:
                errors["base"] = "invalid_auth"
            except DuracellAPIError:
                errors["base"] = "cannot_connect"
            else:
                self._devices = {d[CONF_INVERTER_ID]: d for d in devices}
                if self.source in ("reauth", "reconfigure"):
                    entry = (
                        self._get_reauth_entry()
                        if self.source == "reauth"
                        else self._get_reconfigure_entry()
                    )
                    serial = entry.data[CONF_INVERTER_ID]
                    if serial not in self._devices:
                        return self.async_abort(reason="wrong_inverter")
                    return await self.async_step_select_inverter(
                        {CONF_INVERTER_ID: serial}
                    )
                if not devices:
                    errors["base"] = "no_inverters"
                elif len(devices) == 1:
                    return await self.async_step_select_inverter(
                        {CONF_INVERTER_ID: devices[0][CONF_INVERTER_ID]}
                    )
                else:
                    return await self.async_step_select_inverter()
        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema(
                {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): _SECRET}
            ),
        )

    async def async_step_select_inverter(self, user_input: dict | None = None):
        errors = {}
        if user_input is not None:
            serial = user_input[CONF_INVERTER_ID]
            if serial not in self._devices:
                errors["base"] = "no_inverters"
            else:
                device = self._devices[serial]
                self._client.select_inverter(serial, device[CONF_GROUP_ID])
                try:
                    await self._client.async_get_flow()
                except DuracellAuthError:
                    return await self.async_step_user()
                except DuracellAPIError:
                    errors["base"] = "cannot_connect"
                else:
                    data = {
                        **self._credentials,
                        CONF_INVERTER_ID: serial,
                        CONF_GROUP_ID: device[CONF_GROUP_ID],
                        CONF_POLL_SECONDS: DEFAULT_POLL_SECONDS,
                    }
                    await self.async_set_unique_id(serial)
                    if self.source in ("reauth", "reconfigure"):
                        entry = (
                            self._get_reauth_entry()
                            if self.source == "reauth"
                            else self._get_reconfigure_entry()
                        )
                        data[CONF_POLL_SECONDS] = entry.data.get(
                            CONF_POLL_SECONDS, DEFAULT_POLL_SECONDS
                        )
                        return self.async_update_reload_and_abort(entry, data=data)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Duracell {serial[-4:]}", data=data
                    )
        return self.async_show_form(
            step_id="select_inverter",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_INVERTER_ID): vol.In(
                        {
                            serial: device["label"]
                            for serial, device in self._devices.items()
                        }
                    )
                }
            ),
        )

    async def async_step_details(self, user_input: dict | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {CONF_AUTH_MODE: self._mode, **user_input}
            for key in (
                CONF_INVERTER_ID,
                CONF_GROUP_ID,
                CONF_FLOW_SIGN,
                CONF_LOGIN_SIGN,
                CONF_USERNAME,
                CONF_TOKEN,
            ):
                if isinstance(data.get(key), str):
                    data[key] = data[key].strip()
            if not all(
                str(data.get(name, "")).strip()
                for name in (CONF_INVERTER_ID, CONF_GROUP_ID, CONF_FLOW_SIGN)
            ):
                errors["base"] = "missing_fields"
            else:
                client = DuracellCloudClient(
                    async_get_clientsession(self.hass),
                    inverter_id=data[CONF_INVERTER_ID].strip(),
                    group_id=data[CONF_GROUP_ID].strip(),
                    flow_sign=data[CONF_FLOW_SIGN].strip(),
                    auth_mode=self._mode,
                    username=data.get(CONF_USERNAME),
                    password=data.get(CONF_PASSWORD),
                    login_sign=data.get(CONF_LOGIN_SIGN),
                    token=data.get(CONF_TOKEN),
                )
                try:
                    await client.async_get_flow()
                except DuracellAuthError:
                    errors["base"] = "invalid_auth"
                except DuracellAPIError:
                    errors["base"] = "cannot_connect"
                else:
                    inverter_id = data[CONF_INVERTER_ID].strip()
                    await self.async_set_unique_id(inverter_id)
                    if self.source in ("reauth", "reconfigure"):
                        entry = (
                            self._get_reauth_entry()
                            if self.source == "reauth"
                            else self._get_reconfigure_entry()
                        )
                        if inverter_id != entry.data[CONF_INVERTER_ID]:
                            return self.async_abort(reason="wrong_inverter")
                        return self.async_update_reload_and_abort(
                            entry, data_updates=data
                        )
                    self._abort_if_unique_id_configured()
                    data[CONF_INVERTER_ID] = inverter_id
                    data[CONF_GROUP_ID] = data[CONF_GROUP_ID].strip()
                    return self.async_create_entry(
                        title=f"Duracell G3 {inverter_id[-4:]}", data=data
                    )
        return self.async_show_form(
            step_id="details",
            data_schema=_details_schema(
                self._mode,
                user_input
                or (
                    dict(self._get_reauth_entry().data)
                    if self.source == "reauth"
                    else dict(self._get_reconfigure_entry().data)
                    if self.source == "reconfigure"
                    else None
                ),
            ),
            errors=errors,
        )
