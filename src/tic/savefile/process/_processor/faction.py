"""Faction processor."""

from __future__ import annotations

from datetime import datetime

import cattr
from pydantic import AliasChoices, BaseModel, Field
from returns.result import Failure, Result

from tic.savefile.process._internal.validated_input import validate_input
from tic.savefile.process._internal.validation_failure import ValidationFailure
from tic.shared.events.base import IntegrationEvent
from tic.shared.events.faction import FactionDataExtracted, Resources
from tic.shared.log_call import log_call

_CONVERTER = cattr.Converter()
_CONVERTER.register_structure_hook(tuple, lambda v, t: tuple(v))


@log_call()
def process_factions(
    data: dict, current_date_time: datetime
) -> Result[tuple[IntegrationEvent, ...], ValidationFailure]:
    """Map raw savefile data to faction integration events."""
    return (
        validate_input(_FactionInput, data)
        .bind(_to_faction_player_pairs)
        .map(
            lambda pairs: tuple(
                _to_event(current_date_time, faction, player)
                for faction, player in pairs
            )
        )
    )


def _to_faction_player_pairs(
    validated: _FactionInput,
) -> Result[tuple[tuple[_FactionValue, _PlayerValue], ...], ValidationFailure]:
    player_by_id = {
        item.value.id.value: item.value for item in validated.gamestates.player_state
    }
    pairs: list[tuple[_FactionValue, _PlayerValue]] = []
    for item in validated.gamestates.faction_state:
        faction = item.value
        player = player_by_id.get(faction.player.value)
        if player is None:
            return Failure(
                ValidationFailure(
                    reason=f"player with id {faction.player.value} not found"
                )
            )

        pairs.append((faction, player))

    return Result.from_value(tuple(pairs))


def _to_event(
    current_date_time: datetime,
    faction: _FactionValue,
    player: _PlayerValue,
) -> FactionDataExtracted:
    resources = _CONVERTER.structure(faction.resources.model_dump(), Resources)

    return FactionDataExtracted(
        id=faction.id.value,
        abductions=faction.abductions,
        armies=tuple(current_id.value for current_id in faction.armies),
        atrocities=faction.atrocities,
        councilors=tuple(current_id.value for current_id in faction.councilors),
        current_date_time=current_date_time,
        fleets=tuple(current_id.value for current_id in faction.fleets),
        is_ai=player.is_ai,
        mission_control_usage=faction.mission_control_usage,
        template_name=faction.template_name,
        resources=resources,
    )


class _CurrentId(BaseModel):
    value: int


class _Resources(BaseModel):
    antimatter: float = Field(
        ..., validation_alias=AliasChoices("antimatter", "Antimatter")
    )
    boost: float = Field(..., validation_alias=AliasChoices("boost", "Boost"))
    exotics: float = Field(..., validation_alias=AliasChoices("exotics", "Exotics"))
    fissiles: float = Field(..., validation_alias=AliasChoices("fissiles", "Fissiles"))
    influence: float = Field(
        ..., validation_alias=AliasChoices("influence", "Influence")
    )
    metals: float = Field(..., validation_alias=AliasChoices("metals", "Metals"))
    mission_control: float = Field(
        ..., validation_alias=AliasChoices("missionControl", "MissionControl")
    )
    money: float = Field(..., validation_alias=AliasChoices("money", "Money"))
    noble_metals: float = Field(
        ..., validation_alias=AliasChoices("nobleMetals", "NobleMetals")
    )
    operations: float = Field(
        ..., validation_alias=AliasChoices("operations", "Operations")
    )
    volatiles: float = Field(
        ..., validation_alias=AliasChoices("volatiles", "Volatiles")
    )
    water: float = Field(..., validation_alias=AliasChoices("water", "Water"))


class _FactionValue(BaseModel):
    id: _CurrentId = Field(..., validation_alias=AliasChoices("id", "ID"))
    player: _CurrentId
    abductions: int
    armies: list[_CurrentId]
    atrocities: int
    councilors: list[_CurrentId]
    fleets: list[_CurrentId]
    mission_control_usage: int = Field(..., alias="missionControlUsage")
    template_name: str = Field(..., alias="templateName")
    resources: _Resources


class _PlayerValue(BaseModel):
    id: _CurrentId = Field(..., validation_alias=AliasChoices("id", "ID"))
    is_ai: bool = Field(..., alias="isAI")


class _FactionItem(BaseModel):
    value: _FactionValue = Field(..., alias="Value")


class _PlayerItem(BaseModel):
    value: _PlayerValue = Field(..., alias="Value")


class _Gamestates(BaseModel):
    faction_state: list[_FactionItem] = Field(
        ...,
        validation_alias=AliasChoices(
            "FactionState",
            "PavonisInteractive.TerraInvicta.TIFactionState",
        ),
    )
    player_state: list[_PlayerItem] = Field(
        ...,
        validation_alias=AliasChoices(
            "PlayerState",
            "PavonisInteractive.TerraInvicta.TIPlayerState",
        ),
    )


class _FactionInput(BaseModel):
    gamestates: _Gamestates
