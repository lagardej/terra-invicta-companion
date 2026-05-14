"""Savefile log read model — document definition."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SavefileLogEntry:
    """A single savefile processing attempt recorded in the log."""

    id: str
    reason: str | None
    real_world_campaign_start: datetime | None
    scenario_id: str | None
    current_date_time: datetime | None
    duration_ms: int | None
    recorded_at: datetime
