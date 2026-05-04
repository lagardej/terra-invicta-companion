"""Boundary tests for the savefile process shell."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tic._infra.bus_in_memory import MessageBusInMemory
from tic._infra.event_store_in_memory import EventStoreInMemory
from tic.savefile.process._extract.identity import Identity
from tic.savefile.process._processor.campaign import (
    ExtractedCampaignData,
)
from tic.savefile.process._processor.campaign import (
    ScenarioCustomizations as ExtractedScenarioCustomizations,
)
from tic.savefile.process.core import ProcessResult, ProcessSavefile, SavefileState
from tic.savefile.process.events import (
    SavefileProcessingFailed,
    SavefileProcessingSucceeded,
)
from tic.savefile.process.shell import SavefileProcess
from tic.shared.command import CommandContext
from tic.shared.event_store import EventFilter
from tic.shared.events.base import Message
from tic.shared.events.campaign import CampaignDataExtracted, ScenarioCustomizations
from tic.shared.events.savefile import SavefileChangeDetected

from .conftest import valid_savefile_data

pytestmark = pytest.mark.integration

_CURRENT_DATE_TIME = datetime(2022, 6, 15, 8, 0, 0, tzinfo=UTC)
_REAL_WORLD_CAMPAIGN_START = datetime(2019, 12, 31, 23, 59, 30, 500_000, tzinfo=UTC)


class _FakeHandler:
    def __init__(self, result: ProcessResult) -> None:
        self._result = result
        self.calls = 0
        self.command: ProcessSavefile | None = None
        self.context: CommandContext[SavefileState] | None = None

    async def handle(
        self,
        command: ProcessSavefile,
        context: CommandContext[SavefileState],
    ) -> ProcessResult:
        self.calls += 1
        self.command = command
        self.context = context
        return self._result


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
    async def test_persists_and_publishes_handler_output(
        self,
        tmp_path: Path,
    ) -> None:
        savefile_path = tmp_path / "save.json"
        savefile_path.write_text(json.dumps(valid_savefile_data()), encoding="utf-8")

        extracted = _campaign_data()
        handler = _FakeHandler(
            ProcessResult(
                domain_event=SavefileProcessingSucceeded(
                    real_world_campaign_start=_REAL_WORLD_CAMPAIGN_START,
                    player_faction=7,
                    current_date_time=_CURRENT_DATE_TIME,
                    duration_ms=12,
                ),
                extracted=(extracted,),
            )
        )
        bus = MessageBusInMemory()
        event_store = EventStoreInMemory()
        process = SavefileProcess(bus, event_store, handler)
        published_campaign_events: list[CampaignDataExtracted] = []

        async def capture_campaign_event(event: Message) -> None:
            assert isinstance(event, CampaignDataExtracted)
            published_campaign_events.append(event)

        bus.subscribe(CampaignDataExtracted, capture_campaign_event)

        await process._on_savefile_detected(SavefileChangeDetected(path=savefile_path))

        assert handler.calls == 1
        assert handler.command is not None
        assert handler.context is not None
        assert handler.command.identity == Identity(
            real_world_campaign_start=_REAL_WORLD_CAMPAIGN_START,
            player_faction=7,
        )
        assert handler.command.current_date_time == _CURRENT_DATE_TIME
        assert handler.context.state == SavefileState(current_date_time=None)

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

        assert len(published_campaign_events) == 1
        published = published_campaign_events[0]
        assert isinstance(published.scenario_customizations, ScenarioCustomizations)
        assert (
            published.scenario_customizations is not extracted.scenario_customizations
        )
        assert published.campaign_start_version == extracted.campaign_start_version


class TestFailures:
    @pytest.mark.asyncio
    async def test_persists_validation_failure_without_calling_handler(
        self,
        tmp_path: Path,
    ) -> None:
        savefile_path = tmp_path / "invalid-save.json"
        savefile_path.write_text("{}", encoding="utf-8")

        handler = _FakeHandler(
            ProcessResult(
                domain_event=SavefileProcessingSucceeded(
                    real_world_campaign_start=_REAL_WORLD_CAMPAIGN_START,
                    player_faction=7,
                    current_date_time=_CURRENT_DATE_TIME,
                    duration_ms=12,
                ),
                extracted=(),
            )
        )
        bus = MessageBusInMemory()
        event_store = EventStoreInMemory()
        process = SavefileProcess(bus, event_store, handler)
        published_campaign_events: list[CampaignDataExtracted] = []

        async def capture_campaign_event(event: Message) -> None:
            assert isinstance(event, CampaignDataExtracted)
            published_campaign_events.append(event)

        bus.subscribe(CampaignDataExtracted, capture_campaign_event)

        await process._on_savefile_detected(SavefileChangeDetected(path=savefile_path))

        assert handler.calls == 0
        failed = await event_store.query(
            EventFilter(
                event_types=(SavefileProcessingFailed.type(),),
                payload_predicates={},
            )
        )
        assert len(failed.events) == 1
        assert published_campaign_events == []
