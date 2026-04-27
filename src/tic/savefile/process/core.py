"""Savefile command handler — functional core, no I/O."""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from tic.shared.events.campaign import CampaignParsed, GlobalValuesState, PlayerState
from tic.shared.events.savefile import SaveFileProcessingSucceeded

_GLOBAL_VALUES_KEY = "PavonisInteractive.TerraInvicta.TIGlobalValuesState"
_PLAYER_STATE_KEY = "PavonisInteractive.TerraInvicta.TIPlayerState"
_EPOCH = datetime.min.replace(tzinfo=UTC)


@dataclass(frozen=True)
class ProcessSavefile:
    """Command: process a savefile and emit domain events."""

    path: Path
    data: dict


def handle(command: ProcessSavefile) -> Iterator[object]:
    """Handle a ProcessSavefile command."""
    t0 = time.perf_counter()
    gamestates = command.data.get("gamestates", {})

    campaign = _process_campaign(gamestates)
    yield campaign

    yield _build_processing_succeeded(
        command.path, campaign, (time.perf_counter() - t0) * 1000
    )


def _process_campaign(gamestates: dict) -> CampaignParsed:
    return CampaignParsed(
        global_values=_parse_global_values(gamestates),
        players=_parse_players(gamestates),
    )


def _build_processing_succeeded(
    path: Path,
    campaign: CampaignParsed,
    duration_ms: float,
) -> SaveFileProcessingSucceeded:
    human = next((p for p in campaign.players if not p.is_ai), None)
    return SaveFileProcessingSucceeded(
        path=path,
        campaign_start=campaign.global_values.real_world_campaign_start
        if campaign.global_values is not None
        else _EPOCH,
        player_faction_key=human.name if human is not None else "",
        duration_ms=duration_ms,
        player_count=len(campaign.players),
    )


def _parse_global_values(gamestates: dict) -> GlobalValuesState | None:
    entries = gamestates.get(_GLOBAL_VALUES_KEY, [])
    if not entries:
        return None
    v = entries[0].get("Value", {})
    start = v.get("realWorldCampaignStart")
    return GlobalValuesState(
        difficulty=v.get("difficulty", 0),
        campaign_start_version=v.get("campaignStartVersion", ""),
        latest_save_version=v.get("latestSaveVersion", ""),
        real_world_campaign_start=_parse_datetime(start) if start else _EPOCH,
        scenario_customizations=v.get("scenarioCustomizations", {}),
    )


def _parse_players(gamestates: dict) -> tuple[PlayerState, ...]:
    entries = gamestates.get(_PLAYER_STATE_KEY, [])
    return tuple(p for e in entries if (p := _parse_player(e)) is not None)


def _parse_player(entry: dict) -> PlayerState | None:
    key = entry.get("Key", {}).get("value")
    v = entry.get("Value", {})
    faction_id = v.get("faction", {}).get("value")
    if key is None or faction_id is None:
        return None
    return PlayerState(
        id=key,
        name=v.get("name", ""),
        faction_id=faction_id,
        is_ai=v.get("isAI", True),
    )


def _parse_datetime(raw: dict) -> datetime:
    return datetime(
        year=raw.get("year", 1),
        month=raw.get("month", 1),
        day=raw.get("day", 1),
        hour=raw.get("hour", 0),
        minute=raw.get("minute", 0),
        second=raw.get("second", 0),
        tzinfo=UTC,
    )
