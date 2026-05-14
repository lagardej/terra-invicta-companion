"""Savefile current date/time extraction from raw data."""

from __future__ import annotations

from datetime import datetime

from pydantic import AliasChoices, BaseModel, Field
from returns.result import Failure, Result

from tic.savefile.process.core.data_validator import ValidationFailure, validate_data
from tic.savefile.process.core.epoch import EpochModel, to_datetime


def extract_current_date_time(data: dict) -> Result[datetime, ValidationFailure]:
    """Extract current_date_time from raw savefile data."""
    return (
        validate_data(_CurrentDateTimeModel, data)
        .bind(_extract_time_value)
        .map(_to_datetime)
    )


def _extract_time_value(
    validated: _CurrentDateTimeModel,
) -> Result[_TimeValue, ValidationFailure]:
    violations: list[str] = []

    time_state = validated.gamestates.time_state[0].value
    if not isinstance(time_state, _TimeValue):
        actual_type = type(time_state).__name__
        violations.append(f"time_state[0] has unexpected type: {actual_type}")

    if violations:
        return Failure(ValidationFailure(violations=tuple(violations)))

    assert isinstance(time_state, _TimeValue)
    return Result.from_value(time_state)


def _to_datetime(time_value: _TimeValue) -> datetime:
    return to_datetime(time_value.current_date_time)


class _CurrentDateTimeModel(BaseModel):
    gamestates: _Gamestates


class _Gamestates(BaseModel):
    time_state: list[_ValueItem] = Field(
        ...,
        validation_alias=AliasChoices(
            "TimeState",
            "PavonisInteractive.TerraInvicta.TITimeState",
        ),
    )


class _ValueItem(BaseModel):
    value: _TimeValue = Field(..., alias="Value")


class _TimeValue(BaseModel):
    current_date_time: EpochModel = Field(..., alias="currentDateTime")
