"""Campaign domain events and their value objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from tic.shared.events.base import DomainEvent


@dataclass(frozen=True)
class GlobalValuesState:
    """Campaign-level settings extracted from TIGlobalValuesState."""

    difficulty: int
    campaign_start_version: str
    latest_save_version: str
    real_world_campaign_start: datetime
    scenario_customizations: dict


@dataclass(frozen=True)
class PlayerState:
    """One player (human or AI) extracted from TIPlayerState."""

    id: int
    name: str
    faction_id: int
    is_ai: bool


@dataclass(frozen=True)
class CampaignParsed(DomainEvent):
    """Emitted when campaign data has been extracted from a savefile."""

    global_values: GlobalValuesState | None
    players: tuple[PlayerState, ...]

    @classmethod
    def type(cls) -> str:
        """Return the unique string identifier for this message type."""
        return "campaign.parsed"
