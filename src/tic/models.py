"""Read model — immutable data carriers for parsed savefile data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class GlobalValues:
    """Campaign-level settings extracted from TIGlobalValuesState."""

    difficulty: int
    campaign_start_version: str
    latest_save_version: str
    real_world_campaign_start: datetime
    scenario_customizations: dict


@dataclass(frozen=True)
class PlayerInfo:
    """One player (human or AI) extracted from TIPlayerState."""

    id: int
    name: str
    faction_id: int
    is_ai: bool


@dataclass(frozen=True)
class CampaignSnapshot:
    """Top-level result of parsing a single savefile."""

    global_values: GlobalValues | None
    players: list[PlayerInfo]
