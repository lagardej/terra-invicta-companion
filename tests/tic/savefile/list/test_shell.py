"""Tests for the savefile log shell — subscriber projections."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tic._infra.document_store_in_memory import DocumentStoreInMemory
from tic.savefile.list.document import SavefileLogEntry, SavefileProcessingStatus
from tic.savefile.list.shell import SavefileListListener
from tic.shared.events.savefile import (
    SavefileProcessingFailed,
    SavefileProcessingSucceeded,
)

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
        event = SavefileProcessingSucceeded(
            real_world_campaign_start=_CAMPAIGN_START,
            player_faction=3,
            current_date_time=_GAME_DATE,
            duration_ms=42,
        )
        listener = SavefileListListener(store, now=lambda: _NOW)

        await listener._on_succeeded(event)

        entries = await store.all()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.status == SavefileProcessingStatus.SUCCEEDED
        assert entry.reason is None
        assert entry.real_world_campaign_start == _CAMPAIGN_START
        assert entry.player_faction == 3
        assert entry.current_date_time == _GAME_DATE
        assert entry.duration_ms == 42
        assert entry.recorded_at == _NOW

    async def test_entry_has_unique_id(
        self, store: DocumentStoreInMemory[SavefileLogEntry]
    ) -> None:
        event = SavefileProcessingSucceeded(
            real_world_campaign_start=_CAMPAIGN_START,
            player_faction=3,
            current_date_time=_GAME_DATE,
            duration_ms=10,
        )
        listener = SavefileListListener(store, now=lambda: _NOW)

        await listener._on_succeeded(event)
        await listener._on_succeeded(event)

        entries = await store.all()
        assert entries[0].id != entries[1].id


class TestFailures:
    async def test_writes_entry_with_reason(
        self, store: DocumentStoreInMemory[SavefileLogEntry]
    ) -> None:
        event = SavefileProcessingFailed(
            reason="parse error",
            real_world_campaign_start=_CAMPAIGN_START,
            player_faction=3,
            current_date_time=_GAME_DATE,
        )
        listener = SavefileListListener(store, now=lambda: _NOW)

        await listener._on_failed(event)

        entries = await store.all()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.status == SavefileProcessingStatus.FAILED
        assert entry.reason == "parse error"
        assert entry.duration_ms is None
        assert entry.recorded_at == _NOW

    async def test_writes_entry_without_optional_fields(
        self, store: DocumentStoreInMemory[SavefileLogEntry]
    ) -> None:
        event = SavefileProcessingFailed(reason="identity extraction failed")
        listener = SavefileListListener(store, now=lambda: _NOW)

        await listener._on_failed(event)

        entries = await store.all()
        entry = entries[0]
        assert entry.real_world_campaign_start is None
        assert entry.player_faction is None
        assert entry.current_date_time is None
