"""."""

from dataclasses import dataclass
from datetime import datetime

from tic.shared.events.base import IntegrationEvent


@dataclass(frozen=True)
class GlobalValuesExtracted(IntegrationEvent):
    """GlobalValuesExtracted."""

    earth_atmospheric_co2_ppm: float
    earth_atmospheric_ch4_ppm: float
    earth_atmospheric_n2_o_ppm: float
    stratospheric_aerosols_ppm: float
    global_sea_level_anomaly_cm: float
    initial_sustainability_min: float
    nuclear_strikes: int
    loose_nukes: int
    difficulty: int
    best_global_human_miltech: float
    control_point_maintenance_freebies: int
    campaign_start_version: str
    latest_save_version: str
    real_world_campaign_start: datetime
    game_state_subject_created: bool
    past_earth_atmospheric_co2_ppm: list[float]
    past_earth_atmospheric_ch4_ppm: list[float]
    past_earth_atmospheric_n2_o_ppm: list[float]
    global_sea_level_rise1_triggered: bool
    global_sea_level_rise2_triggered: bool
    end_of_oil: bool
    scenario_customizations: ScenarioCustomizations
    inactive_narrative_events: list[str]
    interstate_wars: list[int]
    modding_active: bool
    modding_used_anytime: bool
    current_tech_sort: int
    tech_sort_ascend: bool
    current_project_sort: int
    project_sort_ascend: bool
    project_sort_show_obsolete: bool
    fleet_screen_class_show_obsolete: bool
    hab_quick_build_toggle: bool
    hab_quick_build_with_boost_toggle: bool
    show_finder_councilors: bool
    show_finder_armies: bool
    show_finder_habs: bool
    show_finder_fleets: bool
    alien_invader_armies: int
    baseline_unnormalized_space_combat_value: float
    saved_init: bool
    tutorial_mode: bool
    start_difficulty: int


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
    selected_factions_for_scenario: list[str]
    ship_construction_speed_alien: float
    ship_construction_speed_human_ai: float
    ship_construction_speed_player: float
    show_triggered_projects: bool
    skip_starting_councilors: list[bool]
    use_player_country_for_starting_councilor: bool
    using_customizations: bool
    variable_project_unlocks: bool
