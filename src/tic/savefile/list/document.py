"""Savefile log read model — document definition."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SavefileProcessingStatus(StrEnum):
    """Status values for a savefile processing attempt."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class SavefileLogEntry:
    """A single savefile processing attempt recorded in the log."""

    id: str
    status: SavefileProcessingStatus
    reason: str | None
    real_world_campaign_start: datetime | None
    player_faction: int | None
    current_date_time: datetime | None
    duration_ms: int | None
    recorded_at: datetime
