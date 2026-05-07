"""Savefile command handler — functional core, no I/O."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import reduce

from returns.result import Failure, Result, Success

from tic.savefile._events import SavefileProcessingSucceeded
from tic.savefile.process.core._processor import process_campaign, process_factions
from tic.savefile.process.core.extracted_data import (
    ExtractedCampaignData,
    ExtractedFactionData,
)
from tic.savefile.process.core.identity import Identity
from tic.savefile.process.core.validation import ValidationFailure
from tic.shared.command import CommandContext
from tic.shared.log_call import log_call

# — Type aliases

ExtractedData = ExtractedCampaignData | ExtractedFactionData


# — Success result (outcome of successful processing)


@dataclass(frozen=True)
class ProcessResult:
    """Successful result of savefile processing."""

    status_event: SavefileProcessingSucceeded
    extracted_data: tuple[ExtractedData, ...]


# — Failures (domain semantics)


@dataclass(frozen=True)
class AlreadyProcessedFailure:
    """Domain invariant violation: savefile has not advanced since last processing."""


@dataclass(frozen=True)
class DataProcessingFailure:
    """One or more processors failed to extract data from the savefile."""

    violations: tuple[str, ...]


ProcessingFailure = AlreadyProcessedFailure | DataProcessingFailure


# — Command (input to the handler)


@dataclass(frozen=True)
class ProcessSavefile:
    """Command to process a raw savefile payload."""

    data: dict
    identity: Identity
    current_date_time: datetime


# — Aggregate state (context for duplicate checking)


@dataclass(frozen=True)
class SavefileState:
    """Reconstructed aggregate state for duplicate checking."""

    current_date_time: datetime | None


# — Processor interface (contract for data extraction)


type _Processor = Callable[
    [dict, datetime], Result[tuple[ExtractedData, ...], ValidationFailure]
]


# — Handler implementation (functional core orchestrator)


_processors: list[_Processor] = [
    process_campaign,
    process_factions,
]


@log_call()
async def handle_process_savefile(
    command: ProcessSavefile,
    context: CommandContext[SavefileState],
) -> Result[ProcessResult, ProcessingFailure]:
    """Run scoped processors against raw savefile data.

    Returns Success[ProcessResult] when all processors succeed.
    Returns Failure[ProcessingFailure] for domain invariant violations or
    processor failures.
    """
    identity = command.identity
    current_date_time = command.current_date_time

    if _is_already_processed(current_date_time, context.state):
        return Failure(AlreadyProcessedFailure())

    t0 = time.perf_counter()
    process_result = _process(_processors, command.data, current_date_time)
    elapsed_ms = int(round((time.perf_counter() - t0) * 1000))

    match process_result:
        case Success(extracted):
            return _to_success(identity, current_date_time, extracted, elapsed_ms)
        case Failure(data_failure):
            return Failure(data_failure)
        case _ as unreachable:
            raise AssertionError(f"Unexpected result: {unreachable}")


def _process(
    processors: list[_Processor],
    data: dict,
    current_date_time: datetime,
) -> Result[tuple[ExtractedData, ...], DataProcessingFailure]:
    """Run all processors and aggregate extracted data or processing violations."""

    def fold(
        acc_tuple: tuple[tuple[ExtractedData, ...], tuple[str, ...]],
        processor: _Processor,
    ) -> tuple[tuple[ExtractedData, ...], tuple[str, ...]]:
        extracted_acc, failures_acc = acc_tuple
        match processor(data, current_date_time):
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
            status_event=SavefileProcessingSucceeded(
                real_world_campaign_start=identity.real_world_campaign_start,
                player_faction=identity.player_faction,
                current_date_time=current_date_time,
                duration_ms=elapsed_ms,
            ),
            extracted_data=extracted_data,
        )
    )


# — Domain predicates


def _is_already_processed(
    current_date_time: datetime,
    state: SavefileState | None,
) -> bool:
    return (
        state is not None
        and state.current_date_time is not None
        and current_date_time <= state.current_date_time
    )
