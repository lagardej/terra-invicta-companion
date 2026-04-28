"""Tests for the savefile command handler (core)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tic.savefile.process.core import ProcessSavefile, handle
from tic.shared.events.campaign import CampaignParsed, PlayerState
from tic.shared.events.savefile import (
    SaveFileProcessingSucceeded,
)

_FIXTURES = Path(__file__).parent / "fixtures"
_MINIMAL = _FIXTURES / "autosave_minimal.json"

_GLOBAL_VALUES_KEY = "PavonisInteractive.TerraInvicta.TIGlobalValuesState"
_PLAYER_STATE_KEY = "PavonisInteractive.TerraInvicta.TIPlayerState"

_FAKE_PATH = Path("/saves/Autosave.json")


@pytest.fixture(scope="module")
def minimal() -> dict:
    return json.loads(_MINIMAL.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def minimal_command(minimal: dict) -> ProcessSavefile:
    return ProcessSavefile(path=_FAKE_PATH, data=minimal)


@pytest.fixture(scope="module")
def minimal_events(minimal_command: ProcessSavefile) -> tuple:
    return tuple(handle(minimal_command))


class TestProcessSavefile:
    """ProcessSavefile is a frozen command."""

    @pytest.mark.unit
    def test_is_frozen(self) -> None:
        cmd = ProcessSavefile(path=_FAKE_PATH, data={})

        with pytest.raises(Exception):
            cmd.path = Path("/other")  # type: ignore[misc]


class TestHandleEmitsEvents:
    """handle() returns a sequence of events."""

    @pytest.mark.unit
    def test_returns_campaign_parsed(self, minimal_events: tuple) -> None:
        assert any(isinstance(e, CampaignParsed) for e in minimal_events)

    @pytest.mark.unit
    def test_returns_processing_succeeded(self, minimal_events: tuple) -> None:
        assert any(isinstance(e, SaveFileProcessingSucceeded) for e in minimal_events)

    @pytest.mark.unit
    def test_processing_succeeded_is_last(self, minimal_events: tuple) -> None:
        assert isinstance(minimal_events[-1], SaveFileProcessingSucceeded)


class TestHandleCampaignParsed:
    """CampaignParsed event carries correct data."""

    @pytest.fixture(scope="class")
    def campaign(self, minimal_events: tuple) -> CampaignParsed:
        return next(e for e in minimal_events if isinstance(e, CampaignParsed))

    @pytest.mark.unit
    def test_global_values_present(self, campaign: CampaignParsed) -> None:
        assert campaign.global_values is not None

    @pytest.mark.unit
    def test_difficulty(self, campaign: CampaignParsed) -> None:
        assert campaign.global_values is not None
        assert campaign.global_values.difficulty == 2

    @pytest.mark.unit
    def test_campaign_start(self, campaign: CampaignParsed) -> None:
        assert campaign.global_values is not None
        assert campaign.global_values.real_world_campaign_start == datetime(
            2026, 4, 7, 11, 4, 18, tzinfo=UTC
        )

    @pytest.mark.unit
    def test_player_count(self, campaign: CampaignParsed) -> None:
        assert len(campaign.players) == 2

    @pytest.mark.unit
    def test_human_player(self, campaign: CampaignParsed) -> None:
        human = next(p for p in campaign.players if not p.is_ai)
        assert human == PlayerState(
            id=10, name="ResistPlayer", faction_id=100, is_ai=False
        )

    @pytest.mark.unit
    def test_players_is_tuple(self, campaign: CampaignParsed) -> None:
        assert isinstance(campaign.players, tuple)


class TestHandleProcessingSucceeded:
    """SaveFileProcessingSucceeded is built from collected domain events."""

    @pytest.fixture(scope="class")
    def succeeded(self, minimal_events: tuple) -> SaveFileProcessingSucceeded:
        return next(
            e for e in minimal_events if isinstance(e, SaveFileProcessingSucceeded)
        )

    @pytest.mark.unit
    def test_path(self, succeeded: SaveFileProcessingSucceeded) -> None:
        assert succeeded.path == _FAKE_PATH

    @pytest.mark.unit
    def test_campaign_start(self, succeeded: SaveFileProcessingSucceeded) -> None:
        assert succeeded.campaign_start == datetime(2026, 4, 7, 11, 4, 18, tzinfo=UTC)

    @pytest.mark.unit
    def test_player_faction_key(self, succeeded: SaveFileProcessingSucceeded) -> None:
        assert succeeded.player_faction_key == "ResistPlayer"

    @pytest.mark.unit
    def test_player_count(self, succeeded: SaveFileProcessingSucceeded) -> None:
        assert succeeded.player_count == 2

    @pytest.mark.unit
    def test_duration_ms_non_negative(
        self, succeeded: SaveFileProcessingSucceeded
    ) -> None:
        assert succeeded.duration_ms >= 0.0


class TestHandleDefensive:
    """handle() is resilient to missing or partial data."""

    @pytest.mark.unit
    def test_missing_gamestates_key(self) -> None:
        events = tuple(handle(ProcessSavefile(path=_FAKE_PATH, data={})))

        campaign = next(e for e in events if isinstance(e, CampaignParsed))
        assert campaign.global_values is None
        assert campaign.players == ()

    @pytest.mark.unit
    def test_missing_global_values(self, minimal: dict) -> None:
        data = {
            "gamestates": {_PLAYER_STATE_KEY: minimal["gamestates"][_PLAYER_STATE_KEY]}
        }
        events = tuple(handle(ProcessSavefile(path=_FAKE_PATH, data=data)))

        campaign = next(e for e in events if isinstance(e, CampaignParsed))
        assert campaign.global_values is None

    @pytest.mark.unit
    def test_missing_players(self, minimal: dict) -> None:
        data = {
            "gamestates": {
                _GLOBAL_VALUES_KEY: minimal["gamestates"][_GLOBAL_VALUES_KEY]
            }
        }
        events = tuple(handle(ProcessSavefile(path=_FAKE_PATH, data=data)))

        campaign = next(e for e in events if isinstance(e, CampaignParsed))
        assert campaign.players == ()

    @pytest.mark.unit
    def test_no_human_player_yields_empty_faction_key(self, minimal: dict) -> None:
        ai_only = {
            "gamestates": {
                _PLAYER_STATE_KEY: [
                    e
                    for e in minimal["gamestates"][_PLAYER_STATE_KEY]
                    if e.get("Value", {}).get("isAI", True)
                ]
            }
        }
        events = tuple(handle(ProcessSavefile(path=_FAKE_PATH, data=ai_only)))

        succeeded = next(
            e for e in events if isinstance(e, SaveFileProcessingSucceeded)
        )
        assert succeeded.player_faction_key == ""

    @pytest.mark.unit
    def test_missing_global_values_yields_epoch_campaign_start(self) -> None:
        events = tuple(handle(ProcessSavefile(path=_FAKE_PATH, data={})))

        succeeded = next(
            e for e in events if isinstance(e, SaveFileProcessingSucceeded)
        )
        assert succeeded.campaign_start == datetime.min.replace(tzinfo=UTC)
