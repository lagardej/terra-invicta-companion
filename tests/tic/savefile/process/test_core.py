"""Boundary tests for the savefile process core."""

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

_CURRENT_DATE_TIME = datetime(2022, 6, 15, tzinfo=UTC)
_CAMPAIGN_START = datetime(2019, 12, 31, 23, 59, 30, 500_000, tzinfo=UTC)
_IDENTITY = Identity(
    real_world_campaign_start=_CAMPAIGN_START,
    player_faction=7,
)


def _context(
    current_date_time: datetime | None = None,
) -> CommandContext[SavefileState]:
    return CommandContext(state=SavefileState(current_date_time=current_date_time))


def _command(data: dict | None = None) -> ProcessSavefile:
    return ProcessSavefile(
        data=data if data is not None else valid_savefile_data(),
        identity=_IDENTITY,
        current_date_time=_CURRENT_DATE_TIME,
    )


async def _handle(
    command: ProcessSavefile,
    context: CommandContext[SavefileState],
) -> ProcessResult:
    return await ProcessSavefileHandler().handle(command, context)


class TestSuccessPath:
    @pytest.mark.asyncio
    async def test_returns_success_domain_event_with_extracted_data(self) -> None:
        result = await _handle(_command(), _context())

        assert isinstance(result, ProcessResult)
        assert isinstance(result.domain_event, SavefileProcessingSucceeded)
        assert len(result.extracted) > 0


class TestFailures:
    @pytest.mark.asyncio
    async def test_returns_failed_event_when_savefile_was_already_processed(
        self,
    ) -> None:
        result = await _handle(
            _command(),
            _context(current_date_time=datetime(2099, 1, 1, tzinfo=UTC)),
        )

        assert isinstance(result.domain_event, SavefileProcessingFailed)
        assert "already processed" in result.domain_event.reason.lower()
