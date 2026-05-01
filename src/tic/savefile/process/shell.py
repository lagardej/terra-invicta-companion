"""Savefile import subscriber — imperative shell."""

from __future__ import annotations

import gzip
import json
from collections.abc import Callable, Coroutine, Sequence
from typing import Any

from returns.pipeline import is_successful

from tic.savefile.process._extract.identity import (
    Identity,
    extract_identity_and_current_date_time,
)
from tic.savefile.process._internal.validation_failure import ValidationFailure
from tic.savefile.process.core import (
    ProcessSavefile,
    ProcessSavefileHandler,
    SavefileState,
)
from tic.shared.command import CommandContext
from tic.shared.event_store import EventFilter, EventStore
from tic.shared.events.base import DomainEvent, Message
from tic.shared.events.savefile import (
    SavefileChangeDetected,
    SavefileProcessingFailed,
    SavefileProcessingSucceeded,
)
from tic.shared.message_bus import MessageBus


def subscriptions() -> tuple[
    tuple[type[Message], Callable[..., Coroutine[Any, Any, None]]], ...
]:
    """Return subscription entries for this module."""
    return ((SavefileChangeDetected, on_savefile_detected),)


async def on_savefile_detected(
    event: SavefileChangeDetected, *, bus: MessageBus, event_store: EventStore
) -> None:
    """Handle a savefile change detected event."""
    data = _load(event)

    identity_and_time_result = extract_identity_and_current_date_time(data)
    if not is_successful(identity_and_time_result):
        await _persist_validation_failure(
            event_store, identity_and_time_result.failure()
        )
        return

    identity, current_date_time = identity_and_time_result.unwrap()
    command = ProcessSavefile(
        data=data,
        identity=identity,
        current_date_time=current_date_time,
    )

    event_filter = _event_filter(identity)
    context, expected_max_sequence = await _load_context(event_store, event_filter)

    handler = ProcessSavefileHandler()
    result = await handler.handle(command, context)

    await event_store.append(
        event_filter,
        result.domain_event,
        expected_max_sequence=expected_max_sequence,
    )
    if isinstance(result.domain_event, SavefileProcessingSucceeded):
        await bus.publish(result.integration_events)


async def _persist_validation_failure(
    event_store: EventStore,
    failure: ValidationFailure,
) -> None:
    """Persist a validation failure when identity cannot be extracted."""
    failure_filter = EventFilter(event_types=(SavefileProcessingFailed.type(),))
    query_result = await event_store.query(failure_filter)
    await event_store.append(
        failure_filter,
        SavefileProcessingFailed(reason=failure.reason),
        expected_max_sequence=query_result.max_sequence,
    )


def _event_filter(identity: Identity) -> EventFilter:
    """Build an event filter scoped to one campaign/faction aggregate."""
    return EventFilter(
        event_types=(SavefileProcessingSucceeded.type(),),
        payload_predicates={
            "real_world_campaign_start": identity.real_world_campaign_start,
            "player_faction": identity.player_faction,
        },
    )


async def _load_context(
    event_store: EventStore,
    scoped_filter: EventFilter,
) -> tuple[CommandContext[SavefileState], int]:
    """Query history and reconstruct context state for the handler."""
    query_result = await event_store.query(scoped_filter)
    state = _fold_state(query_result.events)
    return CommandContext(state=state), query_result.max_sequence


def _load(event: SavefileChangeDetected) -> dict:
    path = event.path
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as fh:
        return json.load(fh, parse_constant=_parse_constant)


def _parse_constant(c: str) -> float:
    return float(c)


def _fold_state(
    history: Sequence[DomainEvent],
) -> SavefileState:
    """Reconstruct state from event history."""
    state = SavefileState(current_date_time=None)
    for event in history:
        if isinstance(event, SavefileProcessingSucceeded):
            state = SavefileState(current_date_time=event.current_date_time)
    return state
