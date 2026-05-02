"""Savefile identity extraction from raw data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import AliasChoices, BaseModel, Field
from returns.result import Failure, Result

from tic.savefile.process._internal.epoch import to_datetime
from tic.savefile.process._internal.validated_input import validate_input
from tic.savefile.process._internal.validation_failure import ValidationFailure


@dataclass(frozen=True)
class Identity:
    """Fields that uniquely identify a processed savefile."""

    real_world_campaign_start: datetime
    player_faction: int


def extract_identity_and_current_date_time(
    data: dict,
) -> Result[tuple[Identity, datetime], ValidationFailure]:
    """Extract identity fields and current_date_time from raw savefile data."""
    return (
        validate_input(_IdentityInput, data)
        .bind(_extract_identity_inputs)
        .map(
            lambda values: (
                Identity(
                    real_world_campaign_start=to_datetime(
                        values[1].real_world_campaign_start
                    ),
                    player_faction=values[0].faction.value,
                ),
                to_datetime(values[2].current_date_time),
            )
        )
    )


def _extract_identity_inputs(
    validated: _IdentityInput,
) -> Result[tuple[_PlayerValue, _GlobalValuesValue, _TimeValue], ValidationFailure]:
    player_value = next(
        (
            item.value
            for item in validated.gamestates.player_state
            if isinstance(item.value, _PlayerValue) and not item.value.is_ai
        ),
        None,
    )
    if player_value is None:
        return Failure(
            ValidationFailure(reason="no human player faction found in player_state")
        )

    global_values = validated.gamestates.global_values_state[0].value
    time_state = validated.gamestates.time_state[0].value
    if isinstance(global_values, _GlobalValuesValue) and isinstance(
        time_state, _TimeValue
    ):
        return Result.from_value((player_value, global_values, time_state))

    return Failure(ValidationFailure(reason="invalid identity input"))


class _CurrentId(BaseModel):
    value: int


class _Epoch(BaseModel):
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    millisecond: int


class _GlobalValuesValue(BaseModel):
    real_world_campaign_start: _Epoch = Field(..., alias="realWorldCampaignStart")


class _TimeValue(BaseModel):
    current_date_time: _Epoch = Field(..., alias="currentDateTime")


class _PlayerValue(BaseModel):
    is_ai: bool = Field(..., alias="isAI")
    faction: _CurrentId


class _ValueItem(BaseModel):
    value: _GlobalValuesValue | _TimeValue | _PlayerValue = Field(..., alias="Value")


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
    player_state: list[_ValueItem] = Field(
        ...,
        validation_alias=AliasChoices(
            "PlayerState",
            "PavonisInteractive.TerraInvicta.TIPlayerState",
        ),
    )


class _IdentityInput(BaseModel):
    gamestates: _Gamestates


__all__ = ["Identity", "extract_identity_and_current_date_time"]
