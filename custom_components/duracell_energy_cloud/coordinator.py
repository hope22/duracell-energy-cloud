"""Single coordinator for the Duracell monitoring cloud telemetry."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

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

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.async_get_flow()
        except DuracellAuthError as exc:
            raise ConfigEntryAuthFailed(str(exc)) from exc
        except DuracellAPIError as exc:
            raise UpdateFailed(str(exc)) from exc
