"""Savefile parser — functional core, no I/O."""

from __future__ import annotations

from datetime import UTC, datetime

from tic.models import CampaignSnapshot, GlobalValues, PlayerInfo

_GLOBAL_VALUES_KEY = "PavonisInteractive.TerraInvicta.TIGlobalValuesState"
_PLAYER_STATE_KEY = "PavonisInteractive.TerraInvicta.TIPlayerState"


def parse(data: dict) -> CampaignSnapshot:
    """Parse a raw savefile dict into a CampaignSnapshot."""
    gamestates = data.get("gamestates", {})
    return CampaignSnapshot(
        global_values=_parse_global_values(gamestates),
        players=_parse_players(gamestates),
    )


def _parse_global_values(gamestates: dict) -> GlobalValues | None:
    entries = gamestates.get(_GLOBAL_VALUES_KEY, [])
    if not entries:
        return None
    v = entries[0].get("Value", {})
    start = v.get("realWorldCampaignStart")
    return GlobalValues(
        difficulty=v.get("difficulty", 0),
        campaign_start_version=v.get("campaignStartVersion", ""),
        latest_save_version=v.get("latestSaveVersion", ""),
        real_world_campaign_start=_parse_datetime(start)
        if start
        else datetime.min.replace(tzinfo=UTC),
        scenario_customizations=v.get("scenarioCustomizations", {}),
    )


def _parse_players(gamestates: dict) -> list[PlayerInfo]:
    entries = gamestates.get(_PLAYER_STATE_KEY, [])
    players = (_parse_player(e) for e in entries)
    return [p for p in players if p is not None]


def _parse_player(entry: dict) -> PlayerInfo | None:
    key = entry.get("Key", {}).get("value")
    v = entry.get("Value", {})
    faction_id = v.get("faction", {}).get("value")
    if key is None or faction_id is None:
        return None
    return PlayerInfo(
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
