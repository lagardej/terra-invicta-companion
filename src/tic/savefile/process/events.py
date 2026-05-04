"""Domain events for save file processing."""

from dataclasses import dataclass, field
from datetime import datetime

from tic.shared.events.base import DomainEvent


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
