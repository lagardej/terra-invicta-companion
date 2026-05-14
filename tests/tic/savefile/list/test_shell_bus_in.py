"""Tests for the savefile log shell — subscriber projections."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tic._infra.document_store_in_memory import DocumentStoreInMemory
from tic.savefile._events import SavefileProcessed
from tic.savefile.list.document import SavefileLogEntry
from tic.savefile.list.shell_bus_in import SavefileListBusIn as SavefileListBusIn

pytestmark = pytest.mark.integration

_NOW = datetime(2030, 1, 1, tzinfo=UTC)
_CAMPAIGN_START = datetime(2022, 6, 15, tzinfo=UTC)
_GAME_DATE = datetime(2035, 3, 10, tzinfo=UTC)


@pytest.fixture
def store() -> DocumentStoreInMemory[SavefileLogEntry]:
    return DocumentStoreInMemory[SavefileLogEntry]()


class TestSuccessPath:
    async def test_writes_entry_to_store(
        self, store: DocumentStoreInMemory[SavefileLogEntry]
    ) -> None:
        event = SavefileProcessed(
            real_world_campaign_start=_CAMPAIGN_START,
            scenario_id="scenario-alpha",
            current_date_time=_GAME_DATE,
            duration_ms=42,
        )
        _, dispatch = SavefileListBusIn(store, now=lambda: _NOW).subscriptions()[0]

        await dispatch(event)

        entries = await store.all()
        assert len(entries) == 1
        entry = entries[0]
        expected = SavefileLogEntry(
            id=entry.id,
            reason=None,
            real_world_campaign_start=_CAMPAIGN_START,
            scenario_id="scenario-alpha",
            current_date_time=_GAME_DATE,
            duration_ms=42,
            recorded_at=_NOW,
        )
        assert entry == expected

    async def test_entry_has_unique_id(
        self, store: DocumentStoreInMemory[SavefileLogEntry]
    ) -> None:
        event = SavefileProcessed(
            real_world_campaign_start=_CAMPAIGN_START,
            scenario_id="scenario-alpha",
            current_date_time=_GAME_DATE,
            duration_ms=10,
        )
        _, dispatch = SavefileListBusIn(store, now=lambda: _NOW).subscriptions()[0]

        await dispatch(event)
        await dispatch(event)

        entries = await store.all()
        assert entries[0].id != entries[1].id
