"""Savefile command handler — functional core, no I/O."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime

from returns.pipeline import is_successful
from returns.result import Result

from tic.savefile.process._extract.identity import Identity
from tic.savefile.process._internal.validation_failure import ValidationFailure
from tic.savefile.process._processor.campaign import process_campaign
from tic.savefile.process._processor.faction import process_factions
from tic.shared.command import CommandContext, CommandHandler
from tic.shared.events.base import IntegrationEvent
from tic.shared.events.savefile import (
    SavefileProcessingFailed,
    SavefileProcessingSucceeded,
)


@dataclass(frozen=True)
class ProcessSavefile:
    """Command to process a raw savefile payload."""

    data: dict
    identity: Identity
    current_date_time: datetime


@dataclass(frozen=True)
class ProcessResult:
    """Result of savefile processing for the imperative shell."""

    domain_event: SavefileProcessingSucceeded | SavefileProcessingFailed
    integration_events: tuple[IntegrationEvent, ...]


@dataclass(frozen=True)
class SavefileState:
    """Reconstructed aggregate state for duplicate checking."""

    current_date_time: datetime | None


type _Processor = Callable[
    [dict, datetime], Result[tuple[IntegrationEvent, ...], ValidationFailure]
]


class ProcessSavefileHandler(
    CommandHandler[ProcessSavefile, ProcessResult, SavefileState]
):
    """Command handler contract implementation for savefile processing."""

    processors: list[_Processor] = [
        process_campaign,
        process_factions,
    ]

    async def handle(
        self,
        command: ProcessSavefile,
        context: CommandContext[SavefileState],
    ) -> ProcessResult:
        """Run scoped processors against raw savefile data."""
        identity = command.identity
        current_date_time = command.current_date_time

        if _is_already_processed(current_date_time, context.state):
            return _already_processed(identity, current_date_time)

        integration_events, failures, elapsed_ms = self._run_processors(
            command.data, current_date_time
        )
        if failures:
            return _processor_failures_result(identity, current_date_time, failures)

        return _success_result(
            identity, current_date_time, integration_events, elapsed_ms
        )

    def _run_processors(
        self,
        data: dict,
        current_date_time: datetime,
    ) -> tuple[tuple[IntegrationEvent, ...], list[str], int]:
        t0 = time.perf_counter()

        integration_events: list[IntegrationEvent] = []
        failures: list[str] = []
        for processor in self.processors:
            result = processor(data, current_date_time)
            if not is_successful(result):
                failures.append(result.failure().reason)
                continue
            integration_events.extend(result.unwrap())

        elapsed_ms = int(round((time.perf_counter() - t0) * 1000))
        return tuple(integration_events), failures, elapsed_ms


def _is_already_processed(
    current_date_time: datetime,
    state: SavefileState | None,
) -> bool:
    return (
        state is not None
        and state.current_date_time is not None
        and current_date_time <= state.current_date_time
    )


def _already_processed(
    identity: Identity, current_date_time: datetime
) -> ProcessResult:
    return ProcessResult(
        domain_event=SavefileProcessingFailed(
            reason="Already processed: savefile current_date_time has not advanced",
            real_world_campaign_start=identity.real_world_campaign_start,
            player_faction=identity.player_faction,
            current_date_time=current_date_time,
        ),
        integration_events=(),
    )


def _processor_failures_result(
    identity: Identity,
    current_date_time: datetime,
    failures: Sequence[str],
) -> ProcessResult:
    return ProcessResult(
        domain_event=SavefileProcessingFailed(
            reason="; ".join(failures),
            real_world_campaign_start=identity.real_world_campaign_start,
            player_faction=identity.player_faction,
            current_date_time=current_date_time,
        ),
        integration_events=(),
    )


def _success_result(
    identity: Identity,
    current_date_time: datetime,
    integration_events: tuple[IntegrationEvent, ...],
    elapsed_ms: int,
) -> ProcessResult:
    return ProcessResult(
        domain_event=SavefileProcessingSucceeded(
            real_world_campaign_start=identity.real_world_campaign_start,
            player_faction=identity.player_faction,
            current_date_time=current_date_time,
            duration_ms=elapsed_ms,
        ),
        integration_events=integration_events,
    )
