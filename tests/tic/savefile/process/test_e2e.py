"""End-to-end tests for the savefile processing pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from tic._infra.bus_in_memory import MessageBusInMemory
from tic._infra.event_store_in_memory import EventStoreInMemory
from tic.savefile.process.core import ProcessSavefileHandler
from tic.savefile.process.events import (
    SavefileProcessingFailed,
    SavefileProcessingSucceeded,
)
from tic.savefile.process.shell import SavefileProcess
from tic.shared.events.campaign import CampaignDataExtracted
from tic.shared.events.faction import FactionDataExtracted
from tic.shared.events.savefile import (
    SavefileChangeDetected,
)

pytestmark = pytest.mark.e2e

_FIXTURES = Path(__file__).parent / "fixtures"
_AUTOSAVE_GZ = _FIXTURES / "Autosave.gz"


def _events_of_type[EventT](
    events: list[object], event_type: type[EventT]
) -> list[EventT]:
    return [event for event in events if isinstance(event, event_type)]


def _runtime() -> tuple[MessageBusInMemory, EventStoreInMemory, SavefileProcess]:
    bus = MessageBusInMemory()
    event_store = EventStoreInMemory()
    handler = ProcessSavefileHandler()
    return bus, event_store, SavefileProcess(bus, event_store, handler)


@pytest.fixture(scope="module")
def autosave_event() -> SavefileChangeDetected:
    return SavefileChangeDetected(path=_AUTOSAVE_GZ)


class TestE2EAutosaveHappyPath:
    @pytest.mark.asyncio
    async def test_domain_event_persisted(
        self,
        autosave_event: SavefileChangeDetected,
    ) -> None:
        bus, event_store, process = _runtime()

        await process._on_savefile_detected(autosave_event)

        assert len(event_store._streams) == 1
        event = event_store._streams[0]
        assert isinstance(event, SavefileProcessingSucceeded)

        assert event.real_world_campaign_start is not None
        assert event.player_faction is not None
        assert event.current_date_time is not None
        assert event.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_integration_events_published(
        self,
        autosave_event: SavefileChangeDetected,
    ) -> None:
        bus, event_store, process = _runtime()
        published_events: list[object] = []

        async def capture_event(event: object) -> None:
            published_events.append(event)

        bus.subscribe(CampaignDataExtracted, capture_event)
        bus.subscribe(FactionDataExtracted, capture_event)

        await process._on_savefile_detected(autosave_event)

        assert len(published_events) > 0

        campaign_events = _events_of_type(published_events, CampaignDataExtracted)
        faction_events = _events_of_type(published_events, FactionDataExtracted)

        assert len(campaign_events) == 1, "Should extract exactly 1 campaign"
        assert len(faction_events) == 8, "Should extract all 8 factions"


class TestE2EAutosaveFailures:
    @pytest.mark.asyncio
    async def test_already_processed_savefile_appends_failure(
        self,
        autosave_event: SavefileChangeDetected,
    ) -> None:
        bus, event_store, process = _runtime()

        await process._on_savefile_detected(autosave_event)
        await process._on_savefile_detected(autosave_event)

        failed = [
            e for e in event_store._streams if isinstance(e, SavefileProcessingFailed)
        ]
        assert len(failed) == 1
        assert "already processed" in failed[0].reason.lower()

    @pytest.mark.asyncio
    async def test_invalid_savefile_raises(self, tmp_path: Path) -> None:
        bus, event_store, process = _runtime()
        invalid_path = tmp_path / "invalid-save.json"
        invalid_path.write_text("{}", encoding="utf-8")

        await process._on_savefile_detected(SavefileChangeDetected(path=invalid_path))

        failed = [
            e for e in event_store._streams if isinstance(e, SavefileProcessingFailed)
        ]
        assert len(failed) == 1
        assert failed[0].real_world_campaign_start is None
        assert failed[0].player_faction is None
        assert failed[0].current_date_time is None

    @pytest.mark.asyncio
    async def test_missing_file_raises(self, tmp_path: Path) -> None:
        bus, event_store, process = _runtime()
        missing_path = tmp_path / "missing-save.json"

        with pytest.raises(FileNotFoundError):
            await process._on_savefile_detected(
                SavefileChangeDetected(path=missing_path)
            )
