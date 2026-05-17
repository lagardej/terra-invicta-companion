"""Savefile command handler — functional core, no I/O.

Structure:
  Outcomes
    ProcessResult
    AlreadyProcessedFailure
    DataProcessingFailure
  Command
    ProcessSavefile
  Command handler
    EVENT_TYPES
    SavefileState
    _Processor
    _PROCESSORS
    handle_process_savefile
    _build_state
    _is_already_processed
    _process
    _to_success
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from functools import reduce

from returns.result import Failure, Result, Success

from framework.events import DomainEvent
from framework.log_call import log_call
from tic.savefile._events import SavefileProcessed
from tic.savefile.process.core.extracted_data import (
    ExtractedCampaignData,
    ExtractedFactionData,
    Identity,
)
from tic.savefile.process.core.extractor import extract_campaign, extract_factions
from tic.savefile.process.core.extractor._data_validator import ValidationFailure

#
# — Outcomes
#
ExtractedData = ExtractedCampaignData | ExtractedFactionData


@dataclass(frozen=True)
class ProcessResult:
    """Successful result of savefile processing."""

    event: SavefileProcessed
    extracted_data: tuple[ExtractedData, ...]


@dataclass(frozen=True)
class AlreadyProcessedFailure:
    """Domain invariant violation: savefile has not advanced since last processing."""


@dataclass(frozen=True)
class DataProcessingFailure:
    """One or more processors failed to extract data from the savefile."""

    violations: tuple[str, ...]


ProcessingFailure = AlreadyProcessedFailure | DataProcessingFailure


#
# — Command
#
@dataclass(frozen=True)
class ProcessSavefile:
    """Command to process a raw savefile payload."""

    data: dict
    identity: Identity
    current_date_time: datetime


#
# — Command handler
#
EVENT_TYPES = (SavefileProcessed.type(),)


@dataclass(frozen=True)
class SavefileState:
    """Reconstructed aggregate state for duplicate checking."""

    current_date_time: datetime | None


type _Processor = Callable[
    [dict, datetime], Result[tuple[ExtractedData, ...], ValidationFailure]
]


_PROCESSORS: Sequence[_Processor] = (
    extract_campaign,
    extract_factions,
)


@log_call()
async def handle_process_savefile(
    command: ProcessSavefile,
    events: Sequence[DomainEvent],
) -> Result[ProcessResult, ProcessingFailure]:
    """Run scoped processors against raw savefile data.

    Returns Success[ProcessResult] when all processors succeed.
    Returns Failure[ProcessingFailure] for domain invariant violations or
    processor failures.
    """
    identity = command.identity
    current_date_time = command.current_date_time
    state = _build_state(events)

    if _is_already_processed(current_date_time, state):
        return Failure(AlreadyProcessedFailure())

    t0 = time.perf_counter()
    process_result = _process(_PROCESSORS, command)
    elapsed_ms = int(round((time.perf_counter() - t0) * 1000))

    match process_result:
        case Success(extracted):
            return _to_success(identity, current_date_time, extracted, elapsed_ms)
        case Failure(data_failure):
            return Failure(data_failure)
        case _ as unreachable:
            raise AssertionError(f"Unexpected result: {unreachable}")


def _build_state(events: Sequence[DomainEvent]) -> SavefileState:
    """Reconstruct SavefileState from event history."""
    state = SavefileState(current_date_time=None)
    for event in events:
        if isinstance(event, SavefileProcessed):
            state = SavefileState(current_date_time=event.current_date_time)
    return state


def _is_already_processed(
    current_date_time: datetime,
    state: SavefileState,
) -> bool:
    return (
        state.current_date_time is not None
        and current_date_time <= state.current_date_time
    )


def _process(
    processors: Sequence[_Processor],
    command: ProcessSavefile,
) -> Result[tuple[ExtractedData, ...], DataProcessingFailure]:
    """Run all processors and aggregate extracted data or processing violations."""

    def fold(
        acc_tuple: tuple[tuple[ExtractedData, ...], tuple[str, ...]],
        processor: _Processor,
    ) -> tuple[tuple[ExtractedData, ...], tuple[str, ...]]:
        extracted_acc, failures_acc = acc_tuple
        match processor(command.data, command.current_date_time):
            case Success(extracted):
                return (extracted_acc + tuple(extracted), failures_acc)
            case Failure(vf):
                return (extracted_acc, failures_acc + vf.violations)
            case _ as unreachable:
                raise AssertionError(f"Unexpected result: {unreachable}")

    extracted, failures = reduce(fold, processors, ((), ()))
    if failures:
        return Failure(DataProcessingFailure(violations=failures))
    return Success(extracted)


def _to_success(
    identity: Identity,
    current_date_time: datetime,
    extracted_data: tuple[ExtractedData, ...],
    elapsed_ms: int,
) -> Result[ProcessResult, ProcessingFailure]:
    return Success(
        ProcessResult(
            event=SavefileProcessed(
                real_world_campaign_start=identity.real_world_campaign_start,
                scenario_id=identity.scenario_id,
                current_date_time=current_date_time,
                duration_ms=elapsed_ms,
            ),
            extracted_data=extracted_data,
        )
    )
