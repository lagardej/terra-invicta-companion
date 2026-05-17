"""End-to-end test for the savefile process pipeline with real fixture data."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from framework.event_store import EventFilter
from tests.tic.conftest import E2ERuntime
from tic.savefile._events import (
    SavefileProcessed,
)
from tic.savefile.process.shell.filewatch_in import SavefileProcessFilewatchIn
from tic.shared.events.campaign import CampaignDataExtracted, ScenarioCustomizations
from tic.shared.events.faction import FactionDataExtracted

from .conftest import global_values_state_dict, time_state_dict

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

        # Verify domain event is persisted with correct identity
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

        # Verify campaign integration event field mapping
        campaign = campaign_events[0]
        assert isinstance(campaign.scenario_customizations, ScenarioCustomizations)
        assert campaign.campaign_start_version is not None
        assert campaign.current_date_time == success.current_date_time
        assert campaign.real_world_campaign_start == success.real_world_campaign_start

        # Verify faction integration event field mapping
        faction = faction_events[0]
        assert faction.id is not None
        assert faction.current_date_time == success.current_date_time
        assert faction.resources is not None
        assert faction.template_name is not None


class TestFailures:
    @pytest.mark.asyncio
    async def test_identity_extraction_failure_persists_no_events(
        self,
        savefile_process_runtime: E2ERuntime,
        tmp_path: Path,
    ) -> None:
        savefile_path = tmp_path / "save.json"
        savefile_path.write_text(json.dumps({"gamestates": {}}), encoding="utf-8")

        runtime = savefile_process_runtime
        await SavefileProcessFilewatchIn(
            runtime.bus, runtime.event_store
        )._process_savefile(savefile_path)

        assert runtime.captured(SavefileProcessed) == []
        assert runtime.captured(CampaignDataExtracted) == []
        assert runtime.captured(FactionDataExtracted) == []

        persisted = await runtime.event_store.query(
            EventFilter(event_types=(SavefileProcessed.type(),), payload_predicates={})
        )
        assert len(persisted.events) == 0

    @pytest.mark.asyncio
    async def test_current_date_time_extraction_failure_persists_no_events(
        self,
        savefile_process_runtime: E2ERuntime,
        tmp_path: Path,
    ) -> None:
        time_state = time_state_dict()
        del time_state["Value"]["currentDateTime"]
        savefile_path = tmp_path / "save.json"
        savefile_path.write_text(
            json.dumps(
                {
                    "gamestates": {
                        "GlobalValuesState": [global_values_state_dict()],
                        "TimeState": [time_state],
                    }
                }
            ),
            encoding="utf-8",
        )

        runtime = savefile_process_runtime
        await SavefileProcessFilewatchIn(
            runtime.bus, runtime.event_store
        )._process_savefile(savefile_path)

        assert runtime.captured(SavefileProcessed) == []
        assert runtime.captured(CampaignDataExtracted) == []
        assert runtime.captured(FactionDataExtracted) == []

        persisted = await runtime.event_store.query(
            EventFilter(event_types=(SavefileProcessed.type(),), payload_predicates={})
        )
        assert len(persisted.events) == 0

    @pytest.mark.asyncio
    async def test_already_processed_failure_produces_no_new_events(
        self,
        savefile_process_runtime: E2ERuntime,
    ) -> None:
        assert _FIXTURE.exists()

        runtime = savefile_process_runtime
        filewatch_in = SavefileProcessFilewatchIn(runtime.bus, runtime.event_store)

        await filewatch_in._process_savefile(_FIXTURE)
        assert len(runtime.captured(SavefileProcessed)) == 1

        # Reset captured events, process the same file again
        for event_list in runtime.captured_events.values():
            event_list.clear()

        await filewatch_in._process_savefile(_FIXTURE)

        assert runtime.captured(SavefileProcessed) == []
        assert runtime.captured(CampaignDataExtracted) == []
        assert runtime.captured(FactionDataExtracted) == []

        persisted = await runtime.event_store.query(
            EventFilter(
                event_types=(SavefileProcessed.type(),),
                payload_predicates={},
            )
        )
        assert len(persisted.events) == 1  # still only the original
