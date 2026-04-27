"""Tests for the savefile parser."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tic.models import GlobalValues, PlayerInfo
from tic.parser import parse

_FIXTURES = Path(__file__).parent / "fixtures"
_MINIMAL = _FIXTURES / "autosave_minimal.json"

_GLOBAL_VALUES_KEY = "PavonisInteractive.TerraInvicta.TIGlobalValuesState"
_PLAYER_STATE_KEY = "PavonisInteractive.TerraInvicta.TIPlayerState"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def minimal() -> dict:
    return _load(_MINIMAL)


class TestParseGlobalValues:
    """GlobalValues extraction from TIGlobalValuesState."""

    @pytest.mark.unit
    def test_difficulty(self, minimal: dict) -> None:
        gv = parse(minimal).global_values
        assert gv is not None
        assert gv.difficulty == 2

    @pytest.mark.unit
    def test_versions(self, minimal: dict) -> None:
        gv = parse(minimal).global_values
        assert gv is not None
        assert gv.campaign_start_version == "1.0.32"
        assert gv.latest_save_version == "1.0.33"

    @pytest.mark.unit
    def test_campaign_start_is_datetime(self, minimal: dict) -> None:
        gv = parse(minimal).global_values
        assert gv is not None
        assert isinstance(gv.real_world_campaign_start, datetime)

    @pytest.mark.unit
    def test_campaign_start_value(self, minimal: dict) -> None:
        gv = parse(minimal).global_values
        assert gv is not None
        assert gv.real_world_campaign_start == datetime(
            2026, 4, 7, 11, 4, 18, tzinfo=UTC
        )

    @pytest.mark.unit
    def test_scenario_customizations_preserved(self, minimal: dict) -> None:
        gv = parse(minimal).global_values
        assert gv is not None
        assert gv.scenario_customizations == {"usingCustomizations": True}

    @pytest.mark.unit
    def test_full_global_values(self, minimal: dict) -> None:
        assert parse(minimal).global_values == GlobalValues(
            difficulty=2,
            campaign_start_version="1.0.32",
            latest_save_version="1.0.33",
            real_world_campaign_start=datetime(2026, 4, 7, 11, 4, 18, tzinfo=UTC),
            scenario_customizations={"usingCustomizations": True},
        )


class TestParsePlayers:
    """PlayerInfo extraction from TIPlayerState."""

    @pytest.mark.unit
    def test_player_count(self, minimal: dict) -> None:
        assert len(parse(minimal).players) == 2

    @pytest.mark.unit
    def test_human_player(self, minimal: dict) -> None:
        human = next(p for p in parse(minimal).players if not p.is_ai)

        assert human == PlayerInfo(
            id=10, name="ResistPlayer", faction_id=100, is_ai=False
        )

    @pytest.mark.unit
    def test_ai_player(self, minimal: dict) -> None:
        ai = next(p for p in parse(minimal).players if p.is_ai)

        assert ai == PlayerInfo(id=11, name="DestroyPlayer", faction_id=101, is_ai=True)

    @pytest.mark.unit
    def test_exactly_one_human_player(self, minimal: dict) -> None:
        assert sum(1 for p in parse(minimal).players if not p.is_ai) == 1


class TestParseDefensive:
    """Parser is resilient to missing or unexpected keys."""

    @pytest.mark.unit
    def test_missing_global_values_returns_none(self, minimal: dict) -> None:
        data = {
            "gamestates": {_PLAYER_STATE_KEY: minimal["gamestates"][_PLAYER_STATE_KEY]}
        }

        assert parse(data).global_values is None

    @pytest.mark.unit
    def test_missing_players_returns_empty(self, minimal: dict) -> None:
        data = {
            "gamestates": {
                _GLOBAL_VALUES_KEY: minimal["gamestates"][_GLOBAL_VALUES_KEY]
            }
        }

        assert parse(data).players == []

    @pytest.mark.unit
    def test_missing_gamestates_key(self) -> None:
        snapshot = parse({})

        assert snapshot.global_values is None
        assert snapshot.players == []
