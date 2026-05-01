"""Tests for EventStoreInMemory."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from tic._infra.event_store_in_memory import EventStoreInMemory
from tic.shared.event_store import ConcurrencyError, EventFilter, QueryResult
from tic.shared.events.base import DomainEvent

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class _StubEvent(DomainEvent):
    real_world_campaign_start: str
    player_faction_id: int
    current_date_time: datetime

    @classmethod
    def type(cls) -> str:
        return "stub.event"


_FILTER = EventFilter(
    event_types=("stub.event",),
    payload_predicates={
        "real_world_campaign_start": "2024-01-01",
        "player_faction_id": 42,
    },
)
_DATE_1 = datetime(2050, 3, 1, tzinfo=UTC)
_DATE_2 = datetime(2050, 6, 1, tzinfo=UTC)
_EVENT_1 = _StubEvent(
    real_world_campaign_start="2024-01-01",
    player_faction_id=42,
    current_date_time=_DATE_1,
)
_EVENT_2 = _StubEvent(
    real_world_campaign_start="2024-01-01",
    player_faction_id=42,
    current_date_time=_DATE_2,
)
_EVENT_OTHER = _StubEvent(
    real_world_campaign_start="2024-01-01",
    player_faction_id=99,
    current_date_time=_DATE_1,
)
_OTHER_FILTER = EventFilter(
    event_types=("stub.event",),
    payload_predicates={
        "real_world_campaign_start": "2024-01-01",
        "player_faction_id": 99,
    },
)


class TestEventStoreInMemoryQuery:
    """query() behaviour."""

    async def test_empty_store_returns_empty_result(self) -> None:
        store = EventStoreInMemory()

        result = await store.query(_FILTER)

        assert result == QueryResult(events=(), max_sequence=0)

    async def test_returns_matching_event_after_append(self) -> None:
        store = EventStoreInMemory()
        await store.append(_FILTER, _EVENT_1, expected_max_sequence=0)

        result = await store.query(_FILTER)

        assert result.events == (_EVENT_1,)
        assert result.max_sequence == 1

    async def test_returns_all_matching_events_in_order(self) -> None:
        store = EventStoreInMemory()
        await store.append(_FILTER, _EVENT_1, expected_max_sequence=0)
        await store.append(_FILTER, _EVENT_2, expected_max_sequence=1)

        result = await store.query(_FILTER)

        assert result.events == (_EVENT_1, _EVENT_2)
        assert result.max_sequence == 2

    async def test_payload_predicate_excludes_non_matching_events(self) -> None:
        store = EventStoreInMemory()
        await store.append(_FILTER, _EVENT_1, expected_max_sequence=0)
        await store.append(_OTHER_FILTER, _EVENT_OTHER, expected_max_sequence=0)

        result = await store.query(_FILTER)
        assert result.events == (_EVENT_1,)

        result_other = await store.query(_OTHER_FILTER)
        assert result_other.events == (_EVENT_OTHER,)

    async def test_event_type_filter_excludes_other_types(self) -> None:
        store = EventStoreInMemory()
        await store.append(_FILTER, _EVENT_1, expected_max_sequence=0)

        result = await store.query(EventFilter(event_types=("other.event",)))

        assert result.events == ()
        assert result.max_sequence == 0


class TestEventStoreInMemoryAppend:
    """append() OCC behaviour."""

    async def test_raises_concurrency_error_when_sequence_stale(self) -> None:
        store = EventStoreInMemory()
        await store.append(_FILTER, _EVENT_1, expected_max_sequence=0)

        with pytest.raises(ConcurrencyError):
            await store.append(_FILTER, _EVENT_2, expected_max_sequence=0)

    async def test_raises_concurrency_error_on_concurrent_append(self) -> None:
        store = EventStoreInMemory()
        await store.append(_FILTER, _EVENT_1, expected_max_sequence=0)
        await store.append(_FILTER, _EVENT_2, expected_max_sequence=1)

        with pytest.raises(ConcurrencyError):
            await store.append(_FILTER, _EVENT_2, expected_max_sequence=1)

    async def test_append_multiple_events_at_once(self) -> None:
        store = EventStoreInMemory()
        await store.append(_FILTER, _EVENT_1, _EVENT_2, expected_max_sequence=0)

        result = await store.query(_FILTER)
        assert result.events == (_EVENT_1, _EVENT_2)
        assert result.max_sequence == 2

    async def test_independent_sequences_per_filter(self) -> None:
        store = EventStoreInMemory()
        await store.append(_FILTER, _EVENT_1, expected_max_sequence=0)
        await store.append(_OTHER_FILTER, _EVENT_OTHER, expected_max_sequence=0)

        result = await store.query(_FILTER)
        assert result.max_sequence == 1

        result_other = await store.query(_OTHER_FILTER)
        assert result_other.max_sequence == 1
