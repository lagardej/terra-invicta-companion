"""Extracted data models for savefile processing."""

from dataclasses import dataclass
from datetime import datetime

from tic.shared.models import Resources


@dataclass(frozen=True)
class Identity:
    """Fields that uniquely identify a processed savefile."""

    real_world_campaign_start: datetime
    scenario_id: str


@dataclass(frozen=True)
class ExtractedCampaignData:
    """Raw campaign data extracted from a savefile."""

    campaign_start_version: str
    current_date_time: datetime
    current_quarter_since_start: int
    days_in_campaign: int
    difficulty: int
    latest_save_version: str
    real_world_campaign_start: datetime
    scenario_customizations: ScenarioCustomizations
    start_difficulty: int
    scenario_key: str


@dataclass(frozen=True)
class ScenarioCustomizations:
    """ScenarioCustomizations."""

    add_alien_assault_carrier_fleet: bool
    alien_progression_speed: float
    average_monthly_events: int
    cinematic_combat_realism_dv: bool
    cinematic_combat_realism_scale: bool
    control_point_maintenance_freebie_bonus_ai: int
    control_point_maintenance_freebie_bonus: int
    custom_difficulty: bool
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
    show_triggered_projects: bool
    skip_starting_councilors: tuple[bool, ...]
    use_player_country_for_starting_councilor: bool
    using_customizations: bool
    variable_project_unlocks: bool


@dataclass(frozen=True)
class ExtractedFactionData:
    """Raw faction data extracted from a savefile."""

    id: int
    abductions: int
    armies: tuple[int, ...]
    atrocities: int
    councilors: tuple[int, ...]
    current_date_time: datetime
    fleets: tuple[int, ...]
    is_ai: bool
    mission_control_usage: int
    template_name: str
    resources: Resources
