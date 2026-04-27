"""Tests for CampaignParsed event and its value objects."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tic.shared.events.campaign import CampaignParsed, GlobalValuesState, PlayerState


class TestGlobalValuesState:
    """GlobalValuesState is a frozen value object."""

    @pytest.mark.unit
    def test_is_frozen(self) -> None:
        gv = GlobalValuesState(
            difficulty=2,
            campaign_start_version="1.0.32",
            latest_save_version="1.0.33",
            real_world_campaign_start=datetime(2026, 4, 7, tzinfo=UTC),
            scenario_customizations={},
        )

        with pytest.raises(Exception):
            gv.difficulty = 99  # type: ignore[misc]


class TestPlayerState:
    """PlayerState is a frozen value object."""

    @pytest.mark.unit
    def test_is_frozen(self) -> None:
        p = PlayerState(id=1, name="Resist", faction_id=10, is_ai=False)

        with pytest.raises(Exception):
            p.name = "other"  # type: ignore[misc]


class TestCampaignParsed:
    """CampaignParsed carries GlobalValuesState and PlayerState value objects."""

    _GV = GlobalValuesState(
        difficulty=2,
        campaign_start_version="1.0.32",
        latest_save_version="1.0.33",
        real_world_campaign_start=datetime(2026, 4, 7, tzinfo=UTC),
        scenario_customizations={"usingCustomizations": True},
    )
    _HUMAN = PlayerState(id=10, name="ResistPlayer", faction_id=100, is_ai=False)
    _AI = PlayerState(id=11, name="DestroyPlayer", faction_id=101, is_ai=True)

    @pytest.mark.unit
    def test_is_frozen(self) -> None:
        event = CampaignParsed(
            global_values=self._GV,
            players=(self._HUMAN, self._AI),
        )

        with pytest.raises(Exception):
            event.global_values = None  # type: ignore[misc]

    @pytest.mark.unit
    def test_players_is_tuple(self) -> None:
        event = CampaignParsed(global_values=self._GV, players=(self._HUMAN,))

        assert isinstance(event.players, tuple)

    @pytest.mark.unit
    def test_global_values_can_be_none(self) -> None:
        event = CampaignParsed(global_values=None, players=())

        assert event.global_values is None
