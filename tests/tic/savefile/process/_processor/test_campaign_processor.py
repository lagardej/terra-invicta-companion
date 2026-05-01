"""Unit tests for the campaign processor."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from returns.pipeline import is_successful
from returns.result import Result

from tic.savefile.process._internal.validation_failure import ValidationFailure
from tic.savefile.process._processor.campaign import process_campaign
from tic.shared.events.base import IntegrationEvent
from tic.shared.events.campaign import CampaignDataExtracted, ScenarioCustomizations

pytestmark = pytest.mark.unit

_DT = datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)


def _valid_data() -> dict:
    """Minimal raw dict satisfying the campaign processor's narrow input model."""
    return {
        "gamestates": {
            "GlobalValuesState": [
                {
                    "ID": {"value": 0},
                    "Value": {
                        "campaignStartVersion": "1.0",
                        "difficulty": 3,
                        "latestSaveVersion": "1.1",
                        "realWorldCampaignStart": {
                            "year": 2019,
                            "month": 12,
                            "day": 31,
                            "hour": 23,
                            "minute": 59,
                            "second": 30,
                            "millisecond": 500,
                        },
                        "scenarioCustomizations": {
                            "usingCustomizations": True,
                            "customDifficulty": False,
                            "customFactionText": {},
                            "customFactionStartingNationGroup": {},
                            "startingCouncilorProfessions": [],
                            "skipStartingCouncilors": [True, False],
                            "usePlayerCountryForStartingCouncilor": True,
                            "variableProjectUnlocks": False,
                            "showTriggeredProjects": True,
                            "addAlienAssaultCarrierFleet": False,
                            "otherFactionStartingNations": False,
                            "selectedFactionsForScenario": ["f1", "f2"],
                            "researchSpeedMultiplier": 1.0,
                            "controlPointMaintenanceFreebieBonusAI": 0,
                            "controlPointMaintenanceFreebieBonusPlayer": 0,
                            "missionControlBonus": 0.0,
                            "missionControlBonusAI": 0.0,
                            "alienProgressionSpeed": 1.0,
                            "miningProductivityMultiplier": 1.0,
                            "nationalIPMultiplier": 1.0,
                            "averageMonthlyEvents": 0,
                            "cinematicCombatRealismDV": False,
                            "cinematicCombatRealismScale": False,
                            "miningRatePlayer": 1.0,
                            "miningRateHumanAI": 1.0,
                            "miningRateAlien": 1.0,
                            "habConstructionSpeedPlayer": 1.0,
                            "habConstructionSpeedHumanAI": 1.0,
                            "habConstructionSpeedAlien": 1.0,
                            "shipConstructionSpeedPlayer": 1.0,
                            "shipConstructionSpeedHumanAI": 1.0,
                            "shipConstructionSpeedAlien": 1.0,
                        },
                        "startDifficulty": 2,
                    },
                }
            ],
            "TimeState": [
                {
                    "ID": {"value": 0},
                    "Value": {
                        "daysInCampaign": 42,
                        "currentQuarterSinceStart": 7,
                        "templateName": "tpl",
                    },
                }
            ],
        }
    }


def _assert_validation_failure(
    result: Result[tuple[IntegrationEvent, ...], ValidationFailure],
) -> ValidationFailure:
    assert not is_successful(result)
    return result.failure()


class TestProcessCampaignHappyPath:
    def test_returns_campaign_data_extracted(self) -> None:
        result = process_campaign(_valid_data(), _DT)

        assert is_successful(result)
        events = list(result.unwrap())
        assert len(events) == 1
        assert isinstance(events[0], CampaignDataExtracted)

    def test_extracts_expected_data(self) -> None:
        result = process_campaign(_valid_data(), _DT)

        assert is_successful(result)
        events = list(result.unwrap())

        expected = CampaignDataExtracted(
            campaign_start_version="1.0",
            current_date_time=_DT,
            current_quarter_since_start=7,
            days_in_campaign=42,
            difficulty=3,
            latest_save_version="1.1",
            real_world_campaign_start=datetime(
                2019, 12, 31, 23, 59, 30, 500_000, tzinfo=UTC
            ),
            scenario_customizations=ScenarioCustomizations(
                add_alien_assault_carrier_fleet=False,
                alien_progression_speed=1.0,
                average_monthly_events=0,
                cinematic_combat_realism_dv=False,
                cinematic_combat_realism_scale=False,
                control_point_maintenance_freebie_bonus_ai=0,
                control_point_maintenance_freebie_bonus=0,
                custom_difficulty=False,
                hab_construction_speed_alien=1.0,
                hab_construction_speed_human_ai=1.0,
                hab_construction_speed_player=1.0,
                mining_productivity_multiplier=1.0,
                mining_rate_alien=1.0,
                mining_rate_human_ai=1.0,
                mining_rate_player=1.0,
                mission_control_bonus_ai=0.0,
                mission_control_bonus=0.0,
                national_ip_multiplier=1.0,
                other_faction_starting_nations=False,
                research_speed_multiplier=1.0,
                selected_factions_for_scenario=("f1", "f2"),
                ship_construction_speed_alien=1.0,
                ship_construction_speed_human_ai=1.0,
                ship_construction_speed_player=1.0,
                show_triggered_projects=True,
                skip_starting_councilors=(True, False),
                use_player_country_for_starting_councilor=True,
                using_customizations=True,
                variable_project_unlocks=False,
            ),
            start_difficulty=2,
            template_name="tpl",
        )

        assert events == [expected]


class TestProcessCampaignValidationFailure:
    def test_missing_global_values_state_returns_failure(self) -> None:
        data = _valid_data()
        del data["gamestates"]["GlobalValuesState"]

        result = process_campaign(data, _DT)

        _assert_validation_failure(result)

    def test_missing_time_state_returns_failure(self) -> None:
        data = _valid_data()
        del data["gamestates"]["TimeState"]

        result = process_campaign(data, _DT)

        _assert_validation_failure(result)

    def test_wrong_type_for_difficulty_returns_failure(self) -> None:
        data = _valid_data()
        data["gamestates"]["GlobalValuesState"][0]["Value"]["difficulty"] = "hard"

        result = process_campaign(data, _DT)

        _assert_validation_failure(result)

    def test_failure_has_non_empty_reason(self) -> None:
        data = _valid_data()
        del data["gamestates"]["TimeState"]

        result = _assert_validation_failure(process_campaign(data, _DT))
        assert result.reason
