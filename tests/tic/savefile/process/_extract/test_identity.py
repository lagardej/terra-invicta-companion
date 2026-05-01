"""Unit tests for the savefile identity extractor."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from returns.pipeline import is_successful
from returns.result import Result

from tic.savefile.process._extract.identity import (
    Identity,
    extract_identity_and_current_date_time,
)
from tic.savefile.process._internal.validation_failure import ValidationFailure

pytestmark = pytest.mark.unit


def _valid_data() -> dict:
    """Minimal raw dict that satisfies identity extraction."""
    return {
        "gamestates": {
            "GlobalValuesState": [
                {
                    "ID": {"value": 0},
                    "Value": {
                        "realWorldCampaignStart": {
                            "year": 2019,
                            "month": 12,
                            "day": 31,
                            "hour": 23,
                            "minute": 59,
                            "second": 30,
                            "millisecond": 500,
                        },
                    },
                }
            ],
            "TimeState": [
                {
                    "ID": {"value": 0},
                    "Value": {
                        "currentDateTime": {
                            "year": 2022,
                            "month": 6,
                            "day": 15,
                            "hour": 8,
                            "minute": 0,
                            "second": 0,
                            "millisecond": 0,
                        },
                    },
                }
            ],
            "PlayerState": [
                {
                    "ID": {"value": 1},
                    "Value": {
                        "isAI": False,
                        "faction": {"value": 7},
                    },
                }
            ],
        }
    }


def _assert_validation_failure(
    result: Result[tuple[Identity, datetime], ValidationFailure],
) -> ValidationFailure:
    assert not is_successful(result)
    return result.failure()


class TestExtractIdentityHappyPath:
    def test_returns_identity_dataclass(self) -> None:
        result = extract_identity_and_current_date_time(_valid_data())

        assert is_successful(result)
        identity, _ = result.unwrap()
        assert isinstance(identity, Identity)

    def test_real_world_campaign_start(self) -> None:
        result = extract_identity_and_current_date_time(_valid_data())

        assert is_successful(result)
        identity, _ = result.unwrap()
        assert identity.real_world_campaign_start == datetime(
            2019, 12, 31, 23, 59, 30, 500_000, tzinfo=UTC
        )

    def test_current_date_time_is_available_from_combined_extractor(self) -> None:
        result = extract_identity_and_current_date_time(_valid_data())

        assert is_successful(result)
        _, current_date_time = result.unwrap()
        assert current_date_time == datetime(2022, 6, 15, 8, 0, 0, tzinfo=UTC)

    def test_player_faction(self) -> None:
        result = extract_identity_and_current_date_time(_valid_data())

        assert is_successful(result)
        identity, _ = result.unwrap()
        assert identity.player_faction == 7


class TestExtractIdentityValidationFailure:
    def test_missing_global_values_state_returns_failure(self) -> None:
        data = _valid_data()
        del data["gamestates"]["GlobalValuesState"]

        result = extract_identity_and_current_date_time(data)

        _assert_validation_failure(result)

    def test_missing_time_state_returns_failure(self) -> None:
        data = _valid_data()
        del data["gamestates"]["TimeState"]

        result = extract_identity_and_current_date_time(data)

        _assert_validation_failure(result)

    def test_missing_player_state_returns_failure(self) -> None:
        data = _valid_data()
        del data["gamestates"]["PlayerState"]

        result = extract_identity_and_current_date_time(data)

        _assert_validation_failure(result)

    def test_wrong_type_in_real_world_campaign_start_returns_failure(self) -> None:
        data = _valid_data()
        data["gamestates"]["GlobalValuesState"][0]["Value"][
            "realWorldCampaignStart"
        ] = "not-a-date"

        result = extract_identity_and_current_date_time(data)

        _assert_validation_failure(result)

    def test_failure_has_non_empty_reason(self) -> None:
        data = _valid_data()
        del data["gamestates"]["TimeState"]

        result = _assert_validation_failure(
            extract_identity_and_current_date_time(data)
        )
        assert result.reason
