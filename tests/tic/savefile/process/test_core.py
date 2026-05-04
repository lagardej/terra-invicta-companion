"""Unit tests for the savefile processing core handler."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tic.savefile.process._extract.identity import Identity
from tic.savefile.process.core import (
    ProcessResult,
    ProcessSavefile,
    ProcessSavefileHandler,
    SavefileState,
)
from tic.savefile.process.events import (
    SavefileProcessingFailed,
    SavefileProcessingSucceeded,
)
from tic.shared.command import CommandContext

from .conftest import valid_savefile_data

pytestmark = pytest.mark.unit

_DT = datetime(2022, 6, 15, tzinfo=UTC)
_CAMPAIGN_START = datetime(2019, 12, 31, 23, 59, 30, 500_000, tzinfo=UTC)
_PLAYER_FACTION = 7
_IDENTITY = Identity(
    real_world_campaign_start=_CAMPAIGN_START,
    player_faction=_PLAYER_FACTION,
)


def _context(
    previous_events: tuple[
        SavefileProcessingSucceeded | SavefileProcessingFailed, ...
    ] = (),
) -> CommandContext[SavefileState]:
    # Shell would reconstruct state by folding events
    state = SavefileState(current_date_time=None)
    for event in previous_events:
        if isinstance(event, SavefileProcessingSucceeded):
            state = SavefileState(current_date_time=event.current_date_time)
    return CommandContext(state=state)


def _command(data: dict | None = None) -> ProcessSavefile:
    return ProcessSavefile(
        data=data if data is not None else valid_savefile_data(),
        identity=_IDENTITY,
        current_date_time=_DT,
    )


async def _handle(
    command: ProcessSavefile, context: CommandContext[SavefileState]
) -> ProcessResult:
    return await ProcessSavefileHandler().handle(command, context)


class TestHandleHappyPath:
    @pytest.mark.asyncio
    async def test_returns_success_domain_event(self) -> None:
        result = await _handle(_command(), _context())

        assert isinstance(result, ProcessResult)
        assert isinstance(result.domain_event, SavefileProcessingSucceeded)

    @pytest.mark.asyncio
    async def test_extracted_data_collected(self) -> None:
        result = await _handle(_command(), _context())

        assert isinstance(result, ProcessResult)
        assert isinstance(result.domain_event, SavefileProcessingSucceeded)
        assert len(result.extracted) > 0


class TestHandleContext:
    @pytest.mark.asyncio
    async def test_non_success_events_in_history_do_not_block_processing(self) -> None:
        history = (
            SavefileProcessingSucceeded(
                real_world_campaign_start=_CAMPAIGN_START,
                player_faction=7,
                current_date_time=datetime(2020, 1, 1, tzinfo=UTC),
                duration_ms=10,
            ),
            SavefileProcessingFailed(reason="earlier failure"),
        )
        context = _context(history)

        result = await _handle(_command(), context)

        assert isinstance(result.domain_event, SavefileProcessingSucceeded)


class TestHandleFailures:
    @pytest.mark.asyncio
    async def test_duplicate_invariant_returns_failed_event(self) -> None:
        # Previous event for same campaign/faction (pre-filtered by shell)
        previous = (
            SavefileProcessingSucceeded(
                real_world_campaign_start=_CAMPAIGN_START,
                player_faction=_PLAYER_FACTION,
                current_date_time=datetime(2022, 6, 15, 8, 0, 0, tzinfo=UTC),
                duration_ms=10,
            ),
        )
        result = await _handle(
            _command(),
            _context(previous),
        )

        assert isinstance(result.domain_event, SavefileProcessingFailed)
        assert "already processed" in result.domain_event.reason.lower()

    @pytest.mark.asyncio
    async def test_older_timestamp_than_previous_same_campaign_fails(self) -> None:
        # Events for the same campaign/faction are pre-filtered by shell
        # Handler should detect if new timestamp is not advancing
        previous = (
            SavefileProcessingSucceeded(
                real_world_campaign_start=_CAMPAIGN_START,
                player_faction=_PLAYER_FACTION,
                current_date_time=datetime(2099, 1, 1, tzinfo=UTC),
                duration_ms=10,
            ),
        )
        result = await _handle(
            _command(),
            _context(previous),
        )

        assert isinstance(result.domain_event, SavefileProcessingFailed)
        assert "already processed" in result.domain_event.reason.lower()
