"""Faction update use case — imperative shell."""

from __future__ import annotations

from tic.faction.update.core import FactionState, UpdateFaction
from tic.faction.update.events import FactionUpdated
from tic.shared.command import CommandContext, CommandHandler
from tic.shared.event_store import EventFilter, EventStore
from tic.shared.event_subscriber import EventSubscriber, Subscription
from tic.shared.events.base import DomainEvent, Message
from tic.shared.events.faction import FactionDataExtracted
from tic.shared.log_call import log_call
from tic.shared.message_bus import MessageBus


class FactionUpdateListener(EventSubscriber):
    """Subscribes to FactionDataExtracted and drives the update use case."""

    def __init__(
        self,
        bus: MessageBus,
        event_store: EventStore,
        handler: CommandHandler[UpdateFaction, FactionUpdated, FactionState],
    ) -> None:
        """Initialise with required infrastructure."""
        self._bus = bus
        self._event_store = event_store
        self._handler = handler

    def subscriptions(self) -> tuple[Subscription, ...]:
        """Return subscription entries for this module."""
        return ((FactionDataExtracted, self._on_faction_data_extracted),)

    @log_call()
    async def _on_faction_data_extracted(self, event: Message) -> None:
        assert isinstance(event, FactionDataExtracted)
        command = _to_command(event)
        event_filter = _event_filter(event)
        context, expected_max_sequence = await self._load_context(event_filter)

        domain_event = await self._handler.handle(command, context)

        await self._event_store.append(
            event_filter,
            domain_event,
            expected_max_sequence=expected_max_sequence,
        )
        await self._bus.publish(domain_event)

    async def _load_context(
        self, scoped_filter: EventFilter
    ) -> tuple[CommandContext[FactionState], int]:
        query_result = await self._event_store.query(scoped_filter)
        state = _fold_state(query_result.events)
        return CommandContext(state=state), query_result.max_sequence


def _to_command(event: FactionDataExtracted) -> UpdateFaction:
    return UpdateFaction(
        id=event.id,
        abductions=event.abductions,
        armies=event.armies,
        atrocities=event.atrocities,
        councilors=event.councilors,
        current_date_time=event.current_date_time,
        fleets=event.fleets,
        is_ai=event.is_ai,
        mission_control_usage=event.mission_control_usage,
        template_name=event.template_name,
        resources=event.resources,
    )


def _event_filter(event: FactionDataExtracted) -> EventFilter:
    return EventFilter(
        event_types=(FactionUpdated.type(),),
        payload_predicates={
            "id": event.id,
            "current_date_time": event.current_date_time,
        },
    )


def _fold_state(history: tuple[DomainEvent, ...]) -> FactionState:
    state = FactionState(current_date_time=None)
    for event in history:
        if isinstance(event, FactionUpdated):
            state = FactionState(current_date_time=event.current_date_time)
    return state
