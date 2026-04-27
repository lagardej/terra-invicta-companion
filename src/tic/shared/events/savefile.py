"""Savefile integration and processing events."""

from __future__ import annotations

from dataclasses import dataclass
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
        return "savefile.detected"


@dataclass(frozen=True)
class SaveFileProcessingSucceeded(DomainEvent):
    """Emitted when a savefile was parsed successfully."""

    path: Path
    campaign_start: datetime
    player_faction_key: str
    duration_ms: float
    player_count: int

    @classmethod
    def type(cls) -> str:
        """Return the unique string identifier for this message type."""
        return "savefile.processing_succeeded"


@dataclass(frozen=True)
class SavefileProcessingFailed(DomainEvent):
    """Emitted when a savefile could not be parsed."""

    path: Path
    reason: str

    @classmethod
    def type(cls) -> str:
        """Return the unique string identifier for this message type."""
        return "savefile.processing_failed"
