"""Event store abstract base class — aggregateless pattern."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from tic.shared.events.base import DomainEvent


class ConcurrencyError(Exception):
    """Raised when an append conflicts with the expected max sequence."""


@dataclass(frozen=True)
class EventFilter:
    """Describes which events to query and scopes the OCC guard on append."""

    event_types: tuple[str, ...]
    payload_predicates: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class QueryResult:
    """Events matching a filter plus the max sequence number at query time."""

    events: tuple[DomainEvent, ...]
    max_sequence: int


class EventStore(ABC):
    """Abstract event store — query by filter, append with OCC guard."""

    @abstractmethod
    async def query(self, filter: EventFilter) -> QueryResult:
        """Return all events matching filter and the current max sequence."""
        ...

    @abstractmethod
    async def append(
        self,
        filter: EventFilter,
        *events: DomainEvent,
        expected_max_sequence: int,
    ) -> None:
        """Append one or more events if the context has not changed since query.

        Raises ConcurrencyError if max sequence no longer matches
        expected_max_sequence within the filter scope.
        """
        ...
