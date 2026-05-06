"""Savefile import subscriber — imperative shell."""

from __future__ import annotations

import gzip
import json
from collections.abc import Sequence
from datetime import datetime

from returns.result import Failure, Result, Success

from tic.savefile._events import (
    SavefileCampaignDataExtracted,
    SavefileFactionDataExtracted,
    SavefileIdentityExtractionFailed,
    SavefileProcessingFailed,
    SavefileProcessingSucceeded,
)
from tic.savefile.process.core._processor.campaign import ExtractedCampaignData
from tic.savefile.process.core._processor.faction import ExtractedFactionData
from tic.savefile.process.core.command import (
    AlreadyProcessedFailure,
    DataProcessingFailure,
    ExtractedData,
    ProcessingFailure,
    ProcessResult,
    ProcessSavefile,
    SavefileState,
)
from tic.savefile.process.core.identity import (
    Identity,
    extract_identity_and_current_date_time,
)
from tic.shared.command import CommandContext, CommandHandler
from tic.shared.event_store import EventFilter, EventStore
from tic.shared.event_subscriber import EventSubscriber, Subscription
from tic.shared.events.base import DomainEvent, Message
from tic.shared.events.savefile import SavefileChangeDetected
from tic.shared.log_call import log_call
from tic.shared.message_bus import MessageBus


class SavefileProcess(EventSubscriber):
    """Subscribes to savefile change events and drives processing."""

    def __init__(
        self,
        bus: MessageBus,
        event_store: EventStore,
        handler: CommandHandler[
            ProcessSavefile, Result[ProcessResult, ProcessingFailure], SavefileState
        ],
    ) -> None:
        """Initialise with required infrastructure."""
        self._bus = bus
        self._event_store = event_store
        self._handler = handler

    def subscriptions(self) -> tuple[Subscription, ...]:
        """Return subscription entries for this module."""
        return ((SavefileChangeDetected, self._on_savefile_detected),)

    @log_call()
    async def _on_savefile_detected(self, event: Message) -> None:
        assert isinstance(event, SavefileChangeDetected)
        data = _load(event)

        identity_and_time_result = extract_identity_and_current_date_time(data)
        if isinstance(identity_and_time_result, Failure):
            # Identity extraction failed: observable coordination event only.
            # Not persisted because it is not attachable to a savefile identity.
            vf = identity_and_time_result.failure()
            reason = "; ".join(vf.violations)
            await self._bus.publish(SavefileIdentityExtractionFailed(reason=reason))
            return

        identity, current_date_time = identity_and_time_result.unwrap()
        command = ProcessSavefile(data, identity, current_date_time)

        event_filter = _event_filter(identity)
        context, expected_max_sequence = await self._load_context(event_filter)

        result = await self._handler.handle(command, context)

        match result:
            case Failure(failure_value):
                # Domain invariant violation or processor failure
                await self._persist_and_publish(
                    event_filter,
                    expected_max_sequence,
                    _to_failure_event(failure_value, identity, current_date_time),
                )
            case Success(process_result):
                # All processors succeeded
                await self._persist_and_publish(
                    event_filter, expected_max_sequence, process_result.status_event
                )
                await self._publish_coordination_events(process_result)
            case _ as unreachable:
                raise AssertionError(f"Unexpected result: {unreachable}")

    async def _persist_and_publish(
        self, event_filter: EventFilter, expected_max_sequence: int, event: DomainEvent
    ) -> None:
        await self._event_store.append(event_filter, expected_max_sequence, event)
        await self._bus.publish(event)

    async def _publish_coordination_events(self, result: ProcessResult) -> None:
        coordination_events = _to_coordination_events(result.extracted_data)
        await self._bus.publish(*coordination_events)

    async def _load_context(
        self, scoped_filter: EventFilter
    ) -> tuple[CommandContext[SavefileState], int]:
        query_result = await self._event_store.query(scoped_filter)
        state = _fold_state(query_result.events)
        return CommandContext(state=state), query_result.max_sequence


def _load(event: SavefileChangeDetected) -> dict:
    path = event.path
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as fh:
        return json.load(fh, parse_constant=_parse_constant)


def _parse_constant(c: str) -> float:
    return float(c)


def _event_filter(identity: Identity) -> EventFilter:
    return EventFilter(
        event_types=(SavefileProcessingSucceeded.type(),),
        payload_predicates={
            "real_world_campaign_start": identity.real_world_campaign_start,
            "player_faction": identity.player_faction,
        },
    )


def _fold_state(history: Sequence[DomainEvent]) -> SavefileState:
    state = SavefileState(current_date_time=None)
    for event in history:
        if isinstance(event, SavefileProcessingSucceeded):
            state = SavefileState(current_date_time=event.current_date_time)
    return state


def _to_coordination_events(
    extracted: tuple[ExtractedData, ...],
) -> tuple[Message, ...]:
    """Convert raw extracted data to coordination events."""
    return tuple(_to_coordination_event(item) for item in extracted)


def _to_coordination_event(
    item: ExtractedData,
) -> Message:
    match item:
        case ExtractedCampaignData():
            return SavefileCampaignDataExtracted(data=item)
        case ExtractedFactionData():
            return SavefileFactionDataExtracted(data=item)
        case _ as unreachable:
            raise AssertionError(f"Unexpected extracted data type: {unreachable}")


def _to_failure_event(
    failure: ProcessingFailure,
    identity: Identity,
    current_date_time: datetime,
) -> SavefileProcessingFailed:
    """Map a ProcessingFailure to a domain event for persistence and publishing."""
    match failure:
        case AlreadyProcessedFailure():
            reason = "Already processed: savefile current_date_time has not advanced"
        case DataProcessingFailure(violations=v):
            reason = "; ".join(v)
    return SavefileProcessingFailed(
        reason=reason,
        real_world_campaign_start=identity.real_world_campaign_start,
        player_faction=identity.player_faction,
        current_date_time=current_date_time,
    )
