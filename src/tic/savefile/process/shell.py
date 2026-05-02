"""Savefile import subscriber — imperative shell."""

from __future__ import annotations

import gzip
import json
from collections.abc import Sequence

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
from tic.shared.event_subscriber import EventSubscriber, Subscription
from tic.shared.events.base import DomainEvent, Message
from tic.shared.events.savefile import (
    SavefileChangeDetected,
    SavefileProcessingFailed,
    SavefileProcessingSucceeded,
)
from tic.shared.message_bus import MessageBus


class SavefileProcess(EventSubscriber):
    """Subscribes to savefile change events and drives processing."""

    def __init__(self, bus: MessageBus, event_store: EventStore) -> None:
        """Initialise with required infrastructure."""
        self._bus = bus
        self._event_store = event_store

    def subscriptions(self) -> tuple[Subscription, ...]:
        """Return subscription entries for this module."""
        return ((SavefileChangeDetected, self._on_savefile_detected),)

    async def _on_savefile_detected(self, event: Message) -> None:
        assert isinstance(event, SavefileChangeDetected)
        data = _load(event)

        identity_and_time_result = extract_identity_and_current_date_time(data)
        if not is_successful(identity_and_time_result):
            await self._persist_validation_failure(identity_and_time_result.failure())
            return

        identity, current_date_time = identity_and_time_result.unwrap()
        command = ProcessSavefile(
            data=data,
            identity=identity,
            current_date_time=current_date_time,
        )

        event_filter = _event_filter(identity)
        context, expected_max_sequence = await self._load_context(event_filter)

        handler = ProcessSavefileHandler()
        result = await handler.handle(command, context)

        await self._event_store.append(
            event_filter,
            result.domain_event,
            expected_max_sequence=expected_max_sequence,
        )
        if isinstance(result.domain_event, SavefileProcessingSucceeded):
            await self._bus.publish(result.integration_events)

    async def _persist_validation_failure(self, failure: ValidationFailure) -> None:
        failure_filter = EventFilter(event_types=(SavefileProcessingFailed.type(),))
        query_result = await self._event_store.query(failure_filter)
        await self._event_store.append(
            failure_filter,
            SavefileProcessingFailed(reason=failure.reason),
            expected_max_sequence=query_result.max_sequence,
        )

    async def _load_context(
        self, scoped_filter: EventFilter
    ) -> tuple[CommandContext[SavefileState], int]:
        query_result = await self._event_store.query(scoped_filter)
        state = _fold_state(query_result.events)
        return CommandContext(state=state), query_result.max_sequence


def _event_filter(identity: Identity) -> EventFilter:
    return EventFilter(
        event_types=(SavefileProcessingSucceeded.type(),),
        payload_predicates={
            "real_world_campaign_start": identity.real_world_campaign_start,
            "player_faction": identity.player_faction,
        },
    )


def _load(event: SavefileChangeDetected) -> dict:
    path = event.path
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as fh:
        return json.load(fh, parse_constant=_parse_constant)


def _parse_constant(c: str) -> float:
    return float(c)


def _fold_state(history: Sequence[DomainEvent]) -> SavefileState:
    state = SavefileState(current_date_time=None)
    for event in history:
        if isinstance(event, SavefileProcessingSucceeded):
            state = SavefileState(current_date_time=event.current_date_time)
    return state
