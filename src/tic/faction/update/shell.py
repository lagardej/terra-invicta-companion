"""Faction update use case — imperative shell."""

from __future__ import annotations

from tic.faction._events import FactionUpdated
from tic.faction.update.core import FactionState, UpdateFaction, handle_update_faction
from tic.shared.command import CommandContext
from tic.shared.event_store import EventFilter, EventStore
from tic.shared.events.base import DomainEvent, Message
from tic.shared.events.faction import FactionDataExtracted
from tic.shared.log_call import log_call
from tic.shared.message_bus import MessageBus, Subscription


class FactionUpdateSubscriber:
    """Subscribe to faction integration events and persist domain updates."""

    def __init__(self, bus: MessageBus, event_store: EventStore) -> None:
        """Store dependencies used by the faction update shell."""
        self._bus = bus
        self._event_store = event_store

    def subscriptions(self) -> tuple[Subscription, ...]:
        """Return subscriptions for faction update processing."""
        return ((FactionDataExtracted, self._dispatch),)

    async def _dispatch(self, event: Message) -> None:
        match event:
            case FactionDataExtracted() as e:
                await self._on_faction_data_extracted(e)

    @log_call()
    async def _on_faction_data_extracted(self, event: FactionDataExtracted) -> None:
        command = _to_command(event)
        event_filter = _event_filter(event)
        query_result = await self._event_store.query(event_filter)
        context = CommandContext(state=_fold_state(query_result.events))
        expected_max_sequence = query_result.max_sequence

        domain_event = await handle_update_faction(command, context)

        await self._event_store.append(
            event_filter,
            expected_max_sequence,
            domain_event,
        )
        await self._bus.publish(domain_event)


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
