"""Boundary tests for the savefile process shell."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from returns.result import Success

from tic._infra.bus_in_memory import MessageBusInMemory
from tic._infra.event_store_in_memory import EventStoreInMemory
from tic.savefile._events import (
    SavefileCampaignDataExtracted,
    SavefileIdentityExtractionFailed,
    SavefileProcessingFailed,
    SavefileProcessingSucceeded,
)
from tic.savefile.process.core._processor.campaign import (
    ExtractedCampaignData,
)
from tic.savefile.process.core._processor.campaign import (
    ScenarioCustomizations as ExtractedScenarioCustomizations,
)
from tic.savefile.process.core.command import (
    ProcessResult,
    SavefileState,
)
from tic.savefile.process.core.identity import Identity
from tic.savefile.process.shell.inbound import SavefileProcess
from tic.shared.event_store import EventFilter
from tic.shared.events.base import Message
from tic.shared.events.savefile import SavefileChangeDetected

from .conftest import valid_savefile_data

pytestmark = pytest.mark.integration

_CURRENT_DATE_TIME = datetime(2022, 6, 15, 8, 0, 0, tzinfo=UTC)
_REAL_WORLD_CAMPAIGN_START = datetime(2019, 12, 31, 23, 59, 30, 500_000, tzinfo=UTC)


def _campaign_data() -> ExtractedCampaignData:
    return ExtractedCampaignData(
        campaign_start_version="1.0",
        current_date_time=_CURRENT_DATE_TIME,
        current_quarter_since_start=7,
        days_in_campaign=42,
        difficulty=3,
        latest_save_version="1.1",
        real_world_campaign_start=_REAL_WORLD_CAMPAIGN_START,
        scenario_customizations=ExtractedScenarioCustomizations(
            add_alien_assault_carrier_fleet=False,
            alien_progression_speed=1.0,
            average_monthly_events=0,
            cinematic_combat_realism_dv=False,
            cinematic_combat_realism_scale=False,
            control_point_maintenance_freebie_bonus_ai=0,
            control_point_maintenance_freebie_bonus=0,
            custom_difficulty=False,
            hab_construction_speed_alien=1.0,
            hab_construction_speed_human_ai=1.0,
            hab_construction_speed_player=1.0,
            mining_productivity_multiplier=1.0,
            mining_rate_alien=1.0,
            mining_rate_human_ai=1.0,
            mining_rate_player=1.0,
            mission_control_bonus_ai=0.0,
            mission_control_bonus=0.0,
            national_ip_multiplier=1.0,
            other_faction_starting_nations=False,
            research_speed_multiplier=1.0,
            selected_factions_for_scenario=("f1", "f2"),
            ship_construction_speed_alien=1.0,
            ship_construction_speed_human_ai=1.0,
            ship_construction_speed_player=1.0,
            show_triggered_projects=True,
            skip_starting_councilors=(True, False),
            use_player_country_for_starting_councilor=True,
            using_customizations=True,
            variable_project_unlocks=False,
        ),
        start_difficulty=2,
        template_name="tpl",
    )


class TestSuccessPath:
    @pytest.mark.asyncio
    async def test_persists_and_publishes_domain_and_coordination_events(
        self,
        tmp_path: Path,
    ) -> None:
        savefile_path = tmp_path / "save.json"
        savefile_path.write_text(json.dumps(valid_savefile_data()), encoding="utf-8")

        extracted = _campaign_data()
        process_result = ProcessResult(
            status_event=SavefileProcessingSucceeded(
                real_world_campaign_start=_REAL_WORLD_CAMPAIGN_START,
                player_faction=7,
                current_date_time=_CURRENT_DATE_TIME,
                duration_ms=12,
            ),
            extracted_data=(extracted,),
        )
        mock_handle = AsyncMock(return_value=Success(process_result))
        bus = MessageBusInMemory()
        event_store = EventStoreInMemory()
        process = SavefileProcess(bus, event_store)
        published_domain_events: list[Message] = []

        async def capture_domain_event(event: Message) -> None:
            published_domain_events.append(event)

        bus.subscribe(SavefileProcessingSucceeded, capture_domain_event)
        bus.subscribe(SavefileCampaignDataExtracted, capture_domain_event)

        _patch = "tic.savefile.process.shell.inbound.handle_process_savefile"
        with patch(_patch, mock_handle):
            await process._on_savefile_detected(
                SavefileChangeDetected(path=savefile_path)
            )

        assert mock_handle.call_count == 1
        command, context = mock_handle.call_args.args
        assert command.identity == Identity(
            real_world_campaign_start=_REAL_WORLD_CAMPAIGN_START,
            player_faction=7,
        )
        assert command.current_date_time == _CURRENT_DATE_TIME
        assert context.state == SavefileState(current_date_time=None)

        persisted = await event_store.query(
            EventFilter(
                event_types=(SavefileProcessingSucceeded.type(),),
                payload_predicates={
                    "real_world_campaign_start": _REAL_WORLD_CAMPAIGN_START,
                    "player_faction": 7,
                },
            )
        )
        assert len(persisted.events) == 1

        assert len(published_domain_events) == 2
        assert isinstance(published_domain_events[0], SavefileProcessingSucceeded)
        assert isinstance(published_domain_events[1], SavefileCampaignDataExtracted)


class TestFailures:
    @pytest.mark.asyncio
    async def test_persists_validation_failure_without_calling_handler(
        self,
        tmp_path: Path,
    ) -> None:
        savefile_path = tmp_path / "invalid-save.json"
        savefile_path.write_text("{}", encoding="utf-8")

        mock_handle = AsyncMock()
        bus = MessageBusInMemory()
        event_store = EventStoreInMemory()
        process = SavefileProcess(bus, event_store)
        published_events: list[Message] = []

        async def capture_failure(event: Message) -> None:
            published_events.append(event)

        bus.subscribe(SavefileIdentityExtractionFailed, capture_failure)

        _patch = "tic.savefile.process.shell.inbound.handle_process_savefile"
        with patch(_patch, mock_handle):
            await process._on_savefile_detected(
                SavefileChangeDetected(path=savefile_path)
            )

        assert mock_handle.call_count == 0
        # Identity extraction failure is observable via integration event only.
        failed = await event_store.query(
            EventFilter(
                event_types=(SavefileProcessingFailed.type(),),
                payload_predicates={},
            )
        )
        assert len(failed.events) == 0
        assert len(published_events) == 1
        assert isinstance(published_events[0], SavefileIdentityExtractionFailed)
