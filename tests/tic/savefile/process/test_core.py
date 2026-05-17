"""Boundary tests for the savefile process core."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest
from returns.result import Failure, Result, Success

from framework.events import DomainEvent
from tic.savefile._events import (
    SavefileProcessed,
)
from tic.savefile.process.core.command import (
    AlreadyProcessedFailure,
    DataProcessingFailure,
    ProcessingFailure,
    ProcessResult,
    ProcessSavefile,
    handle_process_savefile,
)
from tic.savefile.process.core.extracted_data import ExtractedCampaignData, Identity

from .conftest import valid_savefile_data

pytestmark = pytest.mark.unit

_CURRENT_DATE_TIME = datetime(2022, 6, 15, tzinfo=UTC)
_CAMPAIGN_START = datetime(2019, 12, 31, 23, 59, 30, 500_000, tzinfo=UTC)
_IDENTITY = Identity(
    real_world_campaign_start=_CAMPAIGN_START,
    scenario_id="scenario-template",
)


def _events(
    current_date_time: datetime | None = None,
) -> Sequence[DomainEvent]:
    if current_date_time is None:
        return ()
    return (
        SavefileProcessed(
            real_world_campaign_start=_CAMPAIGN_START,
            scenario_id="scenario-template",
            current_date_time=current_date_time,
            duration_ms=10,
        ),
    )


def _command(data: dict | None = None) -> ProcessSavefile:
    return ProcessSavefile(
        data=data if data is not None else valid_savefile_data(),
        identity=_IDENTITY,
        current_date_time=_CURRENT_DATE_TIME,
    )


async def _handle(
    command: ProcessSavefile,
    events: Sequence[DomainEvent],
) -> Result[ProcessResult, ProcessingFailure]:
    return await handle_process_savefile(command, events)


class TestSuccessPath:
    @pytest.mark.asyncio
    async def test_returns_success_domain_event_with_extracted_data(self) -> None:
        result = await _handle(_command(), _events())

        assert isinstance(result, Success)
        process_result = result.unwrap()
        assert isinstance(process_result.event, SavefileProcessed)
        assert len(process_result.extracted_data) > 0
        assert isinstance(process_result.extracted_data[0], ExtractedCampaignData)


class TestFailures:
    @pytest.mark.asyncio
    async def test_returns_failed_event_when_savefile_was_already_processed(
        self,
    ) -> None:
        result = await _handle(
            _command(),
            _events(current_date_time=datetime(2099, 1, 1, tzinfo=UTC)),
        )

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), AlreadyProcessedFailure)

    @pytest.mark.asyncio
    async def test_returns_data_processing_failure_when_savefile_data_is_malformed(
        self,
    ) -> None:
        result = await _handle(_command(data={"gamestates": {}}), _events())

        assert isinstance(result, Failure)
        failure = result.failure()
        assert isinstance(failure, DataProcessingFailure)
        assert len(failure.violations) > 0
