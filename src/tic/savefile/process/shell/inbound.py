"""Savefile import subscriber — imperative shell."""

from __future__ import annotations

import gzip
import json
from collections.abc import Sequence
from datetime import datetime

from returns.result import Failure, Success

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
    ProcessSavefile,
    SavefileState,
    handle_process_savefile,
)
from tic.savefile.process.core.identity import (
    Identity,
    extract_identity_and_current_date_time,
)
from tic.shared.command import CommandContext
from tic.shared.event_store import EventFilter, EventStore
from tic.shared.events.base import DomainEvent, Message
from tic.shared.events.savefile import SavefileChangeDetected
from tic.shared.log_call import log_call
from tic.shared.message_bus import MessageBus, Subscription


def savefile_process_subscriptions(
    bus: MessageBus,
    event_store: EventStore,
) -> tuple[Subscription, ...]:
    """Return subscriptions for savefile change processing."""

    @log_call()
    async def _on_savefile_detected(event: Message) -> None:
        assert isinstance(event, SavefileChangeDetected)
        data = _load(event)

        identity_and_time_result = extract_identity_and_current_date_time(data)
        if isinstance(identity_and_time_result, Failure):
            # Identity extraction failed: observable coordination event only.
            # Not persisted because it is not attachable to a savefile identity.
            vf = identity_and_time_result.failure()
            reason = "; ".join(vf.violations)
            await bus.publish(SavefileIdentityExtractionFailed(reason=reason))
            return

        identity, current_date_time = identity_and_time_result.unwrap()
        command = ProcessSavefile(data, identity, current_date_time)

        event_filter = _event_filter(identity)
        query_result = await event_store.query(event_filter)
        context = CommandContext(state=_fold_state(query_result.events))
        expected_max_sequence = query_result.max_sequence

        result = await handle_process_savefile(command, context)

        match result:
            case Failure(failure_value):
                # Domain invariant violation or processor failure
                domain_event: DomainEvent = _to_failure_event(
                    failure_value, identity, current_date_time
                )
                await event_store.append(
                    event_filter, expected_max_sequence, domain_event
                )
                await bus.publish(domain_event)
            case Success(process_result):
                # All processors succeeded
                await event_store.append(
                    event_filter, expected_max_sequence, process_result.status_event
                )
                await bus.publish(process_result.status_event)
                coordination = _to_coordination_events(process_result.extracted_data)
                await bus.publish(*coordination)
            case _ as unreachable:
                raise AssertionError(f"Unexpected result: {unreachable}")

    return ((SavefileChangeDetected, _on_savefile_detected),)


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
