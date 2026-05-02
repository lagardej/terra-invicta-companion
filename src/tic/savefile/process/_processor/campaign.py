"""Campaign processor."""

from __future__ import annotations

from datetime import datetime

import cattr
from pydantic import AliasChoices, BaseModel, Field
from returns.result import Failure, Result

from tic.savefile.process._internal.epoch import to_datetime
from tic.savefile.process._internal.validated_input import validate_input
from tic.savefile.process._internal.validation_failure import ValidationFailure
from tic.shared.events.base import IntegrationEvent
from tic.shared.events.campaign import CampaignDataExtracted, ScenarioCustomizations

_CONVERTER = cattr.Converter()
_CONVERTER.register_structure_hook(tuple, lambda v, t: tuple(v))


def process_campaign(
    data: dict, current_date_time: datetime
) -> Result[tuple[IntegrationEvent, ...], ValidationFailure]:
    """Map raw savefile data to a campaign integration event."""
    return (
        validate_input(_CampaignInput, data)
        .bind(_extract_campaign_values)
        .map(lambda values: (_to_result(current_date_time, values[0], values[1]),))
    )


def _extract_campaign_values(
    validated: _CampaignInput,
) -> Result[tuple[_GlobalValuesValue, _TimeValue], ValidationFailure]:
    global_values = validated.gamestates.global_values_state[0].value
    time_state = validated.gamestates.time_state[0].value
    if isinstance(global_values, _GlobalValuesValue) and isinstance(
        time_state, _TimeValue
    ):
        return Result.from_value((global_values, time_state))

    return Failure(ValidationFailure(reason="invalid campaign input"))


def _to_result(
    current_date_time: datetime,
    global_values: _GlobalValuesValue,
    time_state: _TimeValue,
) -> CampaignDataExtracted:
    scenario_customizations = _CONVERTER.structure(
        global_values.scenario_customizations.model_dump(), ScenarioCustomizations
    )

    return CampaignDataExtracted(
        campaign_start_version=global_values.campaign_start_version,
        current_date_time=current_date_time,
        current_quarter_since_start=time_state.current_quarter_since_start,
        days_in_campaign=time_state.days_in_campaign,
        difficulty=global_values.difficulty,
        latest_save_version=global_values.latest_save_version,
        real_world_campaign_start=to_datetime(global_values.real_world_campaign_start),
        scenario_customizations=scenario_customizations,
        start_difficulty=global_values.start_difficulty,
        template_name=time_state.template_name,
    )


class _Epoch(BaseModel):
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    millisecond: int


class _ScenarioCustomizations(BaseModel):
    using_customizations: bool = Field(..., alias="usingCustomizations")
    custom_difficulty: bool = Field(..., alias="customDifficulty")
    skip_starting_councilors: list[bool] = Field(..., alias="skipStartingCouncilors")
    use_player_country_for_starting_councilor: bool = Field(
        ..., alias="usePlayerCountryForStartingCouncilor"
    )
    variable_project_unlocks: bool = Field(..., alias="variableProjectUnlocks")
    show_triggered_projects: bool = Field(..., alias="showTriggeredProjects")
    add_alien_assault_carrier_fleet: bool = Field(
        ..., alias="addAlienAssaultCarrierFleet"
    )
    other_faction_starting_nations: bool = Field(
        ..., alias="otherFactionStartingNations"
    )
    selected_factions_for_scenario: list[str] = Field(
        ..., alias="selectedFactionsForScenario"
    )
    research_speed_multiplier: float = Field(..., alias="researchSpeedMultiplier")
    control_point_maintenance_freebie_bonus_ai: int = Field(
        ..., alias="controlPointMaintenanceFreebieBonusAI"
    )
    control_point_maintenance_freebie_bonus: int = Field(
        ...,
        validation_alias=AliasChoices(
            "controlPointMaintenanceFreebieBonusPlayer",
            "controlPointMaintenanceFreebieBonus",
        ),
    )
    mission_control_bonus: float = Field(..., alias="missionControlBonus")
    mission_control_bonus_ai: float = Field(..., alias="missionControlBonusAI")
    alien_progression_speed: float = Field(..., alias="alienProgressionSpeed")
    mining_productivity_multiplier: float = Field(
        ..., alias="miningProductivityMultiplier"
    )
    national_ip_multiplier: float = Field(..., alias="nationalIPMultiplier")
    average_monthly_events: int = Field(..., alias="averageMonthlyEvents")
    cinematic_combat_realism_dv: bool = Field(..., alias="cinematicCombatRealismDV")
    cinematic_combat_realism_scale: bool = Field(
        ..., alias="cinematicCombatRealismScale"
    )
    mining_rate_player: float = Field(..., alias="miningRatePlayer")
    mining_rate_human_ai: float = Field(..., alias="miningRateHumanAI")
    mining_rate_alien: float = Field(..., alias="miningRateAlien")
    hab_construction_speed_player: float = Field(
        ..., alias="habConstructionSpeedPlayer"
    )
    hab_construction_speed_human_ai: float = Field(
        ..., alias="habConstructionSpeedHumanAI"
    )
    hab_construction_speed_alien: float = Field(..., alias="habConstructionSpeedAlien")
    ship_construction_speed_player: float = Field(
        ..., alias="shipConstructionSpeedPlayer"
    )
    ship_construction_speed_human_ai: float = Field(
        ..., alias="shipConstructionSpeedHumanAI"
    )
    ship_construction_speed_alien: float = Field(
        ..., alias="shipConstructionSpeedAlien"
    )


class _GlobalValuesValue(BaseModel):
    campaign_start_version: str = Field(..., alias="campaignStartVersion")
    difficulty: int
    latest_save_version: str = Field(..., alias="latestSaveVersion")
    real_world_campaign_start: _Epoch = Field(..., alias="realWorldCampaignStart")
    scenario_customizations: _ScenarioCustomizations = Field(
        ..., alias="scenarioCustomizations"
    )
    start_difficulty: int = Field(..., alias="startDifficulty")


class _TimeValue(BaseModel):
    days_in_campaign: int = Field(..., alias="daysInCampaign")
    current_quarter_since_start: int = Field(..., alias="currentQuarterSinceStart")
    template_name: str = Field(..., alias="templateName")


class _ValueItem(BaseModel):
    value: _GlobalValuesValue | _TimeValue = Field(..., alias="Value")


class _Gamestates(BaseModel):
    global_values_state: list[_ValueItem] = Field(
        ...,
        validation_alias=AliasChoices(
            "GlobalValuesState",
            "PavonisInteractive.TerraInvicta.TIGlobalValuesState",
        ),
    )
    time_state: list[_ValueItem] = Field(
        ...,
        validation_alias=AliasChoices(
            "TimeState",
            "PavonisInteractive.TerraInvicta.TITimeState",
        ),
    )


class _CampaignInput(BaseModel):
    gamestates: _Gamestates
