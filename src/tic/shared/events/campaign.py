"""Campaign domain events and their value objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from tic.shared.events.base import DomainEvent


@dataclass(frozen=True)
class CampaignParsed(DomainEvent):
    """Emitted when campaign data has been extracted from a savefile."""

    global_values: GlobalValuesState
    players: tuple[PlayerState, ...]

    @classmethod
    def type(cls) -> str:
        """Return the unique string identifier for this message type."""
        return "campaign.parsed"


@dataclass(frozen=True)
class GlobalValuesState:
    """Campaign-level settings extracted from TIGlobalValuesState."""

    difficulty: int
    campaign_start_version: str
    latest_save_version: str
    real_world_campaign_start: datetime
    scenario_customizations: ScenarioCustomizations


@dataclass(frozen=True)
class ScenarioCustomizations:
    """Parsed `scenarioCustomizations` from TIGlobalValuesState."""

    using_customizations: bool
    custom_difficulty: bool
    add_alien_assault_carrier_fleet: bool
    alien_progression_speed: float
    average_monthly_events: int
    cinematic_combat_realism_dv: bool
    cinematic_combat_realism_scale: bool
    control_point_maintenance_freebie_bonus_ai: int
    control_point_maintenance_freebie_bonus: int
    hab_construction_speed_alien: float
    hab_construction_speed_human_ai: float
    hab_construction_speed_player: float
    mining_productivity_multiplier: float
    mining_rate_alien: float
    mining_rate_human_ai: float
    mining_rate_player: float
    mission_control_bonus_ai: float
    mission_control_bonus: float
    national_ip_multiplier: float
    other_faction_starting_nations: bool
    research_speed_multiplier: float
    selected_factions_for_scenario: tuple[str, ...]
    ship_construction_speed_alien: float
    ship_construction_speed_human_ai: float
    ship_construction_speed_player: float


@dataclass(frozen=True)
class PlayerState:
    """One player (human or AI) extracted from TIPlayerState."""

    id: int
    name: str
    faction_id: int
    is_ai: bool
