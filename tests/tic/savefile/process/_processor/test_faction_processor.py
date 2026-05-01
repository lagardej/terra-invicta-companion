"""Unit tests for the faction processor."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from returns.pipeline import is_successful
from returns.result import Result

from tic.savefile.process._internal.validation_failure import ValidationFailure
from tic.savefile.process._processor.faction import process_factions
from tic.shared.events.base import IntegrationEvent
from tic.shared.events.faction import FactionDataExtracted, Resources

pytestmark = pytest.mark.unit

_DT = datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)


def _resources_dict() -> dict:
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


def _valid_data() -> dict:
    """Minimal raw dict satisfying the faction processor's narrow input model."""
    return {
        "gamestates": {
            "FactionState": [
                {
                    "ID": {"value": 2},
                    "Value": {
                        "id": {"value": 2},
                        "player": {"value": 1},
                        "abductions": 0,
                        "armies": [],
                        "councilors": [],
                        "fleets": [],
                        "atrocities": 123,
                        "templateName": "faction_template_name",
                        "missionControlUsage": 0,
                        "resources": _resources_dict(),
                    },
                }
            ],
            "PlayerState": [
                {
                    "ID": {"value": 1},
                    "Value": {
                        "id": {"value": 1},
                        "isAI": False,
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


class TestProcessFactionsHappyPath:
    def test_returns_faction_data_extracted(self) -> None:
        result = process_factions(_valid_data(), _DT)

        assert is_successful(result)
        events = list(result.unwrap())
        assert len(events) == 1
        assert isinstance(events[0], FactionDataExtracted)

    def test_extracts_expected_data(self) -> None:
        result = process_factions(_valid_data(), _DT)

        assert is_successful(result)
        events = list(result.unwrap())

        expected = FactionDataExtracted(
            id=2,
            abductions=0,
            armies=(),
            atrocities=123,
            councilors=(),
            current_date_time=_DT,
            fleets=(),
            is_ai=False,
            mission_control_usage=0,
            template_name="faction_template_name",
            resources=Resources(
                antimatter=1.0,
                boost=2.0,
                exotics=3.0,
                fissiles=4.0,
                influence=5.0,
                metals=6.0,
                mission_control=7.0,
                money=8.0,
                noble_metals=9.0,
                operations=10.0,
                volatiles=11.0,
                water=12.0,
            ),
        )

        assert events == [expected]

    def test_multiple_factions_produce_multiple_events(self) -> None:
        data = _valid_data()
        second_faction = {
            "ID": {"value": 3},
            "Value": {
                "id": {"value": 3},
                "player": {"value": 1},
                "abductions": 0,
                "armies": [],
                "councilors": [],
                "fleets": [],
                "atrocities": 0,
                "templateName": "other_faction",
                "missionControlUsage": 0,
                "resources": _resources_dict(),
            },
        }
        data["gamestates"]["FactionState"].append(second_faction)

        result = process_factions(data, _DT)

        assert is_successful(result)
        events = list(result.unwrap())
        assert len(events) == 2


class TestProcessFactionsValidationFailure:
    def test_missing_faction_state_returns_failure(self) -> None:
        data = _valid_data()
        del data["gamestates"]["FactionState"]

        result = process_factions(data, _DT)

        _assert_validation_failure(result)

    def test_missing_player_state_returns_failure(self) -> None:
        data = _valid_data()
        del data["gamestates"]["PlayerState"]

        result = process_factions(data, _DT)

        _assert_validation_failure(result)

    def test_wrong_type_for_abductions_returns_failure(self) -> None:
        data = _valid_data()
        data["gamestates"]["FactionState"][0]["Value"]["abductions"] = "many"

        result = process_factions(data, _DT)

        _assert_validation_failure(result)

    def test_failure_has_non_empty_reason(self) -> None:
        data = _valid_data()
        del data["gamestates"]["FactionState"]

        result = _assert_validation_failure(process_factions(data, _DT))
        assert result.reason
