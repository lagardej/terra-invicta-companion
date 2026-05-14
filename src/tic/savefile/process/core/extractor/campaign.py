"""Campaign processor."""

from __future__ import annotations

from datetime import datetime
from typing import cast

import cattr
from pydantic import AliasChoices, BaseModel, Field
from returns.result import Failure, Result

from tic.savefile.process.core.data_validator import ValidationFailure, validate_data
from tic.savefile.process.core.epoch import EpochModel, to_datetime
from tic.savefile.process.core.extracted_data import (
    ExtractedCampaignData,
    ScenarioCustomizations,
)

_CONVERTER = cattr.Converter()
_CONVERTER.register_structure_hook(tuple, lambda v, t: tuple(v))


def extract_campaign(
    data: dict, current_date_time: datetime
) -> Result[tuple[ExtractedCampaignData, ...], ValidationFailure]:
    """Map raw savefile data to extracted campaign data."""
    return (
        validate_data(_CampaignModel, data)
        .bind(_extract_campaign_values)
        .map(lambda values: (_to_result(current_date_time, values[0], values[1]),))
    )


def _extract_campaign_values(
    validated: _CampaignModel,
) -> Result[tuple[_GlobalValuesValue, _TimeValue], ValidationFailure]:
    global_values = validated.gamestates.global_values_state[0].value
    time_state = validated.gamestates.time_state[0].value
    violations: list[str] = []

    if not isinstance(global_values, _GlobalValuesValue):
        actual_type = type(global_values).__name__
        violations.append(f"global_values_state[0] has unexpected type: {actual_type}")

    if not isinstance(time_state, _TimeValue):
        actual_type = type(time_state).__name__
        violations.append(f"time_state[0] has unexpected type: {actual_type}")

    if violations:
        return Failure(ValidationFailure(violations=tuple(violations)))

    return Result.from_value(
        (
            cast(_GlobalValuesValue, global_values),
            cast(_TimeValue, time_state),
        )
    )


def _to_result(
    current_date_time: datetime,
    global_values: _GlobalValuesValue,
    time_state: _TimeValue,
) -> ExtractedCampaignData:
    scenario_customizations = _CONVERTER.structure(
        global_values.scenario_customizations.model_dump(), ScenarioCustomizations
    )

    return ExtractedCampaignData(
        campaign_start_version=global_values.campaign_start_version,
        current_date_time=current_date_time,
        current_quarter_since_start=time_state.current_quarter_since_start,
        days_in_campaign=time_state.days_in_campaign,
        difficulty=global_values.difficulty,
        latest_save_version=global_values.latest_save_version,
        real_world_campaign_start=to_datetime(global_values.real_world_campaign_start),
        scenario_customizations=scenario_customizations,
        scenario_key=time_state.template_name,
        start_difficulty=global_values.start_difficulty,
    )


class _CampaignModel(BaseModel):
    gamestates: _Gamestates


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


class _ValueItem(BaseModel):
    value: _GlobalValuesValue | _TimeValue = Field(..., alias="Value")


class _GlobalValuesValue(BaseModel):
    campaign_start_version: str = Field(..., alias="campaignStartVersion")
    difficulty: int
    latest_save_version: str = Field(..., alias="latestSaveVersion")
    real_world_campaign_start: EpochModel = Field(..., alias="realWorldCampaignStart")
    scenario_customizations: _ScenarioCustomizations = Field(
        ..., alias="scenarioCustomizations"
    )
    start_difficulty: int = Field(..., alias="startDifficulty")


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


class _TimeValue(BaseModel):
    days_in_campaign: int = Field(..., alias="daysInCampaign")
    current_quarter_since_start: int = Field(..., alias="currentQuarterSinceStart")
    template_name: str = Field(..., alias="templateName")
