"""Domain events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class SavefileChangeDetected:
    """Emitted when a savefile change is detected on disk."""

    path: Path


@dataclass(frozen=True)
class SaveFileProcessingSucceeded:
    """Emitted when a savefile was parsed successfully."""

    path: Path
    campaign_start: datetime
    player_faction_key: str
    duration_ms: float
    player_count: int


@dataclass(frozen=True)
class SavefileProcessingFailed:
    """Emitted when a savefile could not be parsed."""

    path: Path
    reason: str
