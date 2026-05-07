"""Domain events for save file processing."""

from dataclasses import dataclass, field
from datetime import datetime

from tic.savefile.process.core.extracted_data import (
    ExtractedCampaignData,
    ExtractedFactionData,
)
from tic.shared.events.base import DomainEvent, Event


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


@dataclass(frozen=True)
class SavefileCampaignDataExtracted(Event):
    """Use-case coordination: campaign data extracted from a savefile."""

    data: ExtractedCampaignData


@dataclass(frozen=True)
class SavefileFactionDataExtracted(Event):
    """Use-case coordination: faction data extracted from a savefile."""

    data: ExtractedFactionData


@dataclass(frozen=True)
class SavefileIdentityExtractionFailed(Event):
    """Use-case coordination: identity could not be extracted from a savefile.

    Indicates data corruption or malformed savefile that prevents tracking.
    Not persisted to event store (observable only).
    """

    reason: str
