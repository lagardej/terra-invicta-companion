"""Savefile integration and processing events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from tic.shared.events.base import DomainEvent, IntegrationEvent


@dataclass(frozen=True)
class SavefileChangeDetected(IntegrationEvent):
    """Emitted when a savefile change is detected on disk."""

    path: Path

    @classmethod
    def type(cls) -> str:
        """Return the unique string identifier for this message type."""
        return "savefile.change_detected"


@dataclass(frozen=True)
class SavefileProcessingSucceeded(DomainEvent):
    """Emitted when a savefile was parsed successfully."""

    real_world_campaign_start: datetime
    player_faction: int
    current_date_time: datetime
    duration_ms: int

    @classmethod
    def type(cls) -> str:
        """Return the unique string identifier for this message type."""
        return "savefile.processing_succeeded"


@dataclass(frozen=True)
class SavefileProcessingFailed(DomainEvent):
    """Emitted when a savefile could not be parsed."""

    reason: str
    real_world_campaign_start: datetime | None = field(default=None)
    player_faction: int | None = field(default=None)
    current_date_time: datetime | None = field(default=None)

    @classmethod
    def type(cls) -> str:
        """Return the unique string identifier for this message type."""
        return "savefile.processing_failed"
