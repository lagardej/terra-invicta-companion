"""Savefile identity extraction from raw data."""

from __future__ import annotations

from pydantic import AliasChoices, BaseModel, Field
from returns.result import Failure, Result

from tic.savefile.process.core.data_validator import ValidationFailure, validate_data
from tic.savefile.process.core.epoch import EpochModel, to_datetime
from tic.savefile.process.core.extracted_data import Identity


def extract_identity(data: dict) -> Result[Identity, ValidationFailure]:
    """Extract identity fields from raw savefile data."""
    return (
        validate_data(_IdentityModel, data)
        .bind(_extract_identity_inputs)
        .map(_to_identity)
    )


def _to_identity(values: tuple[_GlobalValuesValue, _TimeValue]) -> Identity:
    return Identity(
        real_world_campaign_start=to_datetime(values[0].real_world_campaign_start),
        scenario_id=values[1].scenario_meta_template_name,
    )


def _extract_identity_inputs(
    validated: _IdentityModel,
) -> Result[tuple[_GlobalValuesValue, _TimeValue], ValidationFailure]:
    violations: list[str] = []

    global_values = validated.gamestates.global_values_state[0].value
    if not isinstance(global_values, _GlobalValuesValue):
        actual_type = type(global_values).__name__
        violations.append(f"global_values_state[0] has unexpected type: {actual_type}")

    time_state = validated.gamestates.time_state[0].value
    if not isinstance(time_state, _TimeValue):
        actual_type = type(time_state).__name__
        violations.append(f"time_state[0] has unexpected type: {actual_type}")

    if violations:
        return Failure(ValidationFailure(violations=tuple(violations)))

    assert isinstance(global_values, _GlobalValuesValue)
    assert isinstance(time_state, _TimeValue)
    return Result.from_value((global_values, time_state))


class _IdentityModel(BaseModel):
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
    real_world_campaign_start: EpochModel = Field(..., alias="realWorldCampaignStart")


class _TimeValue(BaseModel):
    scenario_meta_template_name: str = Field(..., alias="scenarioMetaTemplateName")
