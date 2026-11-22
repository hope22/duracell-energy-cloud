"""Read-only client for the observed Duracell / Senergytec monitoring API.

Only calls the user's demonstrated login and hybrid-flowgraph endpoints.
The provider's protocol is unofficial. Never log request bodies or auth headers.
"""

from __future__ import annotations

import asyncio
import math
from collections.abc import Mapping
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import AUTH_PASSWORD, AUTH_TOKEN, FLOW_URL, LOGIN_URL


class DuracellAPIError(Exception):
    """Non-secret, user-safe cloud API failure."""


class DuracellAuthError(DuracellAPIError):
    """Authentication rejected, missing or expired."""


def _denotes_auth_failure(raw: Any) -> bool:
    """Recognise explicit auth failures returned inside HTTP 200 JSON."""
    if not isinstance(raw, Mapping):
        return False
    # Do not inspect or log unstructured free-text provider error messages.
    code = raw.get("code", raw.get("errorCode", raw.get("error_code")))
    if str(code) in ("401", "403"):
        return True
    status = raw.get("status", raw.get("Status"))
    # Only classify explicit failures; a success response can have other fields.
    return isinstance(status, str) and status.lower() in (
        "invalid_token",
        "token_expired",
        "unauthorized",
        "unauthorised",
    )


def extract_inverter_data(raw: Any, inverter_id: str) -> dict[str, Any]:
    """Read just the explicitly configured serial number from the group JSON."""
    if _denotes_auth_failure(raw):
        raise DuracellAuthError("Monitoring API rejected authentication")
    if not isinstance(raw, Mapping):
        raise DuracellAPIError("Monitoring API did not return a JSON object")
    inverter = raw.get(inverter_id)
    if not isinstance(inverter, Mapping):
        raise DuracellAPIError("Monitoring API response omitted the selected inverter")
    if not any(k in inverter for k in ("SOC", "Pbat", "ModelName")):
        raise DuracellAPIError("Monitoring API response lacked telemetry fields")
    return dict(inverter)


def numeric_value(value: Any) -> float | None:
    """Convert telemetry numbers; missing/invalid values stay unavailable."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def extract_login_token(raw: Any) -> str:
    """Read the JWT from a recognised login response structure.

    The user has not yet captured the full monitoring login response schema.
    These are the conventional variants used by related Senergytec services.
    """
    if not isinstance(raw, Mapping):
        raise DuracellAuthError("Login returned an unexpected JSON format")
    if _denotes_auth_failure(raw):
        raise DuracellAuthError("Monitoring account login was rejected")
    for key in ("token", "Token", "access_token", "accessToken"):
        token = raw.get(key)
        if isinstance(token, str) and token.strip():
            # The monitoring API needs the *raw* JWT, not a Bearer prefix.
            return token.removeprefix("Bearer ").strip()
    for key in ("data", "Data", "result", "Result"):
        if isinstance(raw.get(key), Mapping):
            try:
                return extract_login_token(raw[key])
            except DuracellAuthError:
                pass
    raise DuracellAuthError("Login response did not contain a recognised token")


class DuracellCloudClient:
    """Fetch the specified owner's inverter, optionally renewing a session."""

    def __init__(
        self,
        session: ClientSession,
        *,
        inverter_id: str,
        group_id: str,
        flow_sign: str,
        auth_mode: str,
        username: str | None = None,
        password: str | None = None,
        login_sign: str | None = None,
        token: str | None = None,
    ) -> None:
        if auth_mode not in (AUTH_PASSWORD, AUTH_TOKEN):
            raise ValueError("Unsupported authentication mode")
        self._session = session
        self._inverter_id = inverter_id
        self._group_id = group_id
        self._flow_sign = flow_sign
        self._auth_mode = auth_mode
        self._username = username
        self._password = password
        self._login_sign = login_sign
        self._token = token.strip() if auth_mode == AUTH_TOKEN and token else None
        self._login_lock = asyncio.Lock()

    async def _post(
        self, url: str, body: dict[str, Any], token: str | None = None
    ) -> Any:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
        }
        if token:
            # Confirmed by the owner's DevTools trace: no "Bearer" prefix.
            headers["Authorization"] = token
        try:
            async with self._session.post(
                url,
                json=body,
                headers=headers,
                timeout=ClientTimeout(total=20),
                allow_redirects=False,
            ) as response:
                if response.status in (401, 403):
                    raise DuracellAuthError("Monitoring API rejected authentication")
                if response.status >= 300:
                    raise DuracellAPIError(
                        f"Monitoring API returned HTTP {response.status}"
                    )
                try:
                    return await response.json(content_type=None)
                except (ValueError, TypeError) as exc:
                    raise DuracellAPIError(
                        "Monitoring API returned invalid JSON"
                    ) from exc
        except DuracellAPIError:
            raise
        except (TimeoutError, ClientError) as exc:
            raise DuracellAPIError("Unable to contact the monitoring API") from exc

    async def _async_login(self) -> str:
        if not (self._username and self._password and self._login_sign):
            raise DuracellAuthError("Monitoring login credentials are incomplete")
        response = await self._post(
            LOGIN_URL,
            {
                "MemberID": self._username,
                "Password": self._password,
                "type": "1",
                "sign": self._login_sign,
            },
        )
        return extract_login_token(response)

    async def _ensure_token(self) -> str:
        if self._token:
            return self._token
        if self._auth_mode == AUTH_TOKEN:
            raise DuracellAuthError("Monitoring token is missing")
        async with self._login_lock:
            if not self._token:
                self._token = await self._async_login()
        return self._token

    async def async_get_flow(self) -> dict[str, Any]:
        """Fetch inverter data; on rejection, re-login at most once."""
        token = await self._ensure_token()
        payload = {"GroupAutoID": self._group_id, "sign": self._flow_sign}
        try:
            return extract_inverter_data(
                await self._post(FLOW_URL, payload, token), self._inverter_id
            )
        except DuracellAuthError:
            if self._auth_mode == AUTH_TOKEN:
                raise
            # Protect concurrent polling if it is triggered by the UI and timer.
            async with self._login_lock:
                if self._token == token:
                    self._token = await self._async_login()
                new_token = self._token
            return extract_inverter_data(
                await self._post(FLOW_URL, payload, new_token), self._inverter_id
            )


def battery_value(raw: Any, key: str) -> float | str | None:
    """Positive battery power is discharge; negative is charge."""
    value = numeric_value(raw)
    if value is None:
        return None
    if key == "battery_charging_power":
        return max(-value, 0.0)
    if key == "battery_discharging_power":
        return max(value, 0.0)
    if key == "battery_activity":
        return "discharging" if value > 0 else "charging" if value < 0 else "idle"
    return None
