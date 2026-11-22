"""Single coordinator for the Duracell monitoring cloud telemetry."""

from __future__ import annotations

import logging
from datetime import timedelta
from time import monotonic
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import DuracellAPIError, DuracellAuthError, DuracellCloudClient
from .const import DEFAULT_POLL_SECONDS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class DuracellCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(
        self,
        hass: HomeAssistant,
        client: DuracellCloudClient,
        poll_seconds: int = DEFAULT_POLL_SECONDS,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN} telemetry",
            update_interval=timedelta(seconds=poll_seconds),
        )
        self.client = client
        self.last_successful_update = None
        self.consecutive_failures = 0
        self.details_available = False
        self.last_details_update = None
        self._details = {}
        self._next_details_refresh = 0.0

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.client.async_get_flow()

        except DuracellAuthError as exc:
            self.consecutive_failures += 1
            raise ConfigEntryAuthFailed(str(exc)) from exc
        except DuracellAPIError as exc:
            self.consecutive_failures += 1
            raise UpdateFailed(str(exc)) from exc

        self.last_successful_update = dt_util.utcnow()
        self.consecutive_failures = 0
        if monotonic() >= self._next_details_refresh:
            self._next_details_refresh = monotonic() + max(
                300, self.update_interval.total_seconds()
            )
            try:
                self._details = await self.client.async_get_details()
            except DuracellAPIError:
                self._details = {}
                self.details_available = False
            else:
                self.details_available = True
                self.last_details_update = dt_util.utcnow()
        return {**data, "details": self._details}

    @property
    def connection_status(self) -> str:
        if not self.last_update_success or self.last_successful_update is None:
            return "disconnected"
        age = (dt_util.utcnow() - self.last_successful_update).total_seconds()
        if age > 2 * self.update_interval.total_seconds() + 20:
            return "stale"
        return "connected" if self.details_available else "partial"
