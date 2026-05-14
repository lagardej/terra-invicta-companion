"""End-to-end test for the savefile process pipeline with real fixture data."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.tic.conftest import E2ERuntime
from tic.savefile._events import (
    SavefileProcessed,
)
from tic.savefile.process.shell.filewatch_in import SavefileProcessFilewatchIn
from tic.shared.event_store import EventFilter
from tic.shared.events.campaign import CampaignDataExtracted
from tic.shared.events.faction import FactionDataExtracted

pytestmark = pytest.mark.e2e

_FIXTURE = Path(__file__).parent / "fixtures" / "Autosave.gz"


class TestSavefileProcessE2E:
    @pytest.mark.asyncio
    async def test_processes_real_autosave_fixture(
        self,
        savefile_process_runtime: E2ERuntime,
    ) -> None:
        assert _FIXTURE.exists()

        runtime = savefile_process_runtime
        await SavefileProcessFilewatchIn(
            runtime.bus, runtime.event_store
        )._process_savefile(_FIXTURE)

        processing_succeeded = runtime.captured(SavefileProcessed)
        campaign_events = runtime.captured(CampaignDataExtracted)
        faction_events = runtime.captured(FactionDataExtracted)

        assert len(processing_succeeded) == 1
        assert len(campaign_events) == 1
        assert len(faction_events) == 8

        success = processing_succeeded[0]
        persisted = await runtime.event_store.query(
            EventFilter(
                event_types=(SavefileProcessed.type(),),
                payload_predicates={
                    "real_world_campaign_start": success.real_world_campaign_start,
                    "scenario_id": success.scenario_id,
                },
            )
        )
        assert persisted.max_sequence == 1
        assert persisted.events == (success,)
