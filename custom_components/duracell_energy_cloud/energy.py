"""Conservative left-sum energy estimates from successful cloud samples."""

from __future__ import annotations

from .api import numeric_value


class EnergyAccumulator:
    """Accumulate kWh, without extrapolating across invalid or missing samples."""

    def __init__(self, max_gap_seconds: float) -> None:
        self.total = 0.0
        self.max_gap_seconds = max_gap_seconds
        self._previous_power: float | None = None
        self._previous_time: float | None = None

    def restore(self, total: object) -> None:
        """Restore only the total; never integrate time while Home Assistant was off."""
        value = numeric_value(total)
        if value is not None and value >= 0:
            self.total = value
        self._previous_power = None
        self._previous_time = None

    def sample(self, power: object, now: float) -> None:
        value = numeric_value(power)
        if value is None or value < 0:
            self._previous_power = None
            self._previous_time = None
            return
        if self._previous_time is not None and self._previous_power is not None:
            elapsed = now - self._previous_time
            if 0 < elapsed <= self.max_gap_seconds:
                self.total += self._previous_power * elapsed / 3_600_000
        self._previous_power = value
        self._previous_time = now
