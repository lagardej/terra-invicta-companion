"""In-memory event store — for use in tests."""

from __future__ import annotations

from dataclasses import fields

from tic.shared.event_store import (
    ConcurrencyError,
    EventFilter,
    EventStore,
    QueryResult,
)
from tic.shared.events.base import DomainEvent


class EventStoreInMemory(EventStore):
    """Pure in-memory event store. Single-process; no locking required."""

    def __init__(self) -> None:
        """Initialise with an empty event log."""
        self._log: list[DomainEvent] = []

    async def query(self, filter: EventFilter) -> QueryResult:
        """Return all events matching filter and the current max sequence."""
        matched = tuple(e for e in self._log if _matches(e, filter))
        return QueryResult(events=matched, max_sequence=len(matched))

    async def append(
        self,
        filter: EventFilter,
        *events: DomainEvent,
        expected_max_sequence: int,
    ) -> None:
        """Append events if context has not changed since query.

        Raises ConcurrencyError if the number of matching events has grown
        since expected_max_sequence.
        """
        current_sequence = sum(1 for e in self._log if _matches(e, filter))
        if current_sequence != expected_max_sequence:
            raise ConcurrencyError(
                f"Expected max sequence {expected_max_sequence}, got {current_sequence}"
            )
        self._log.extend(events)


def _matches(event: DomainEvent, filter: EventFilter) -> bool:
    if type(event).type() not in filter.event_types:
        return False
    event_fields = {f.name: getattr(event, f.name) for f in fields(event)}  # type: ignore[arg-type]
    return all(event_fields.get(k) == v for k, v in filter.payload_predicates.items())
