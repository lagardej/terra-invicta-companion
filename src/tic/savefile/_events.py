"""Domain events for save file processing."""

from dataclasses import dataclass
from datetime import datetime

from framework.events import DomainEvent, Event
from tic.savefile.process.core.extracted_data import (
    ExtractedCampaignData,
    ExtractedFactionData,
)


@dataclass(frozen=True)
class SavefileProcessed(DomainEvent):
    """Emitted when a savefile was parsed successfully."""

    real_world_campaign_start: datetime
    scenario_id: str
    current_date_time: datetime
    duration_ms: int

    @classmethod
    def type(cls) -> str:
        """Return the unique string identifier for this message type."""
        return "savefile.processed"


@dataclass(frozen=True)
class SavefileCampaignDataExtracted(Event):
    """Use-case coordination: campaign data extracted from a savefile."""

    campaign_id: int
    data: ExtractedCampaignData


@dataclass(frozen=True)
class SavefileFactionDataExtracted(Event):
    """Use-case coordination: faction data extracted from a savefile."""

    campaign_id: int
    data: ExtractedFactionData
