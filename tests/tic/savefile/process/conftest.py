"""Shared fixtures for savefile processing tests."""

from __future__ import annotations


def scenario_customizations_dict() -> dict:
    """Minimal scenario customizations matching campaign processor expectations."""
    return {
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
    }


def global_values_state_dict() -> dict:
    """Minimal GlobalValuesState data for campaign processor."""
    return {
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
            "scenarioCustomizations": scenario_customizations_dict(),
            "startDifficulty": 2,
        },
    }


def time_state_dict() -> dict:
    """Minimal TimeState data for campaign processor."""
    return {
        "ID": {"value": 0},
        "Value": {
            "daysInCampaign": 42,
            "currentQuarterSinceStart": 7,
            "currentDateTime": {
                "year": 2022,
                "month": 6,
                "day": 15,
                "hour": 8,
                "minute": 0,
                "second": 0,
                "millisecond": 0,
            },
            "templateName": "tpl",
        },
    }


def resources_dict() -> dict:
    """Minimal resources data for faction processor."""
    return {
        "antimatter": 1.0,
        "boost": 2.0,
        "exotics": 3.0,
        "fissiles": 4.0,
        "influence": 5.0,
        "metals": 6.0,
        "missionControl": 7.0,
        "money": 8.0,
        "nobleMetals": 9.0,
        "operations": 10.0,
        "volatiles": 11.0,
        "water": 12.0,
    }


def player_state_dict(is_ai: bool = False) -> dict:
    """Minimal PlayerState data shared by identity and faction processor."""
    return {
        "ID": {"value": 1},
        "Value": {
            "id": {"value": 1},
            "isAI": is_ai,
            "faction": {"value": 7},
        },
    }


def faction_state_dict(faction_id: int = 2, player_id: int = 1) -> dict:
    """Minimal FactionState data for faction processor."""
    return {
        "ID": {"value": faction_id},
        "Value": {
            "id": {"value": faction_id},
            "player": {"value": player_id},
            "abductions": 0,
            "armies": [],
            "councilors": [],
            "fleets": [],
            "atrocities": 123,
            "templateName": "faction_template_name",
            "missionControlUsage": 0,
            "resources": resources_dict(),
        },
    }


def valid_savefile_data() -> dict:
    """Complete valid savefile data for core handler."""
    return {
        "gamestates": {
            "GlobalValuesState": [global_values_state_dict()],
            "TimeState": [time_state_dict()],
            "PlayerState": [player_state_dict()],
            "FactionState": [faction_state_dict()],
        }
    }
