"""Tests for outbound savefile status integration event publishing."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tic._infra.bus_in_memory import MessageBusInMemory
from tic.savefile._events import (
    SavefileCampaignDataExtracted,
    SavefileFactionDataExtracted,
)
from tic.savefile.process.core.extracted_data import (
    ExtractedCampaignData,
    ExtractedFactionData,
)
from tic.savefile.process.core.extracted_data import (
    ScenarioCustomizations as ExtractedScenarioCustomizations,
)
from tic.savefile.process.shell.bus_out import (
    SavefileProcessBusOut as SavefileProcessBusOut,
)
from tic.shared.events.base import Message
from tic.shared.events.campaign import CampaignDataExtracted, ScenarioCustomizations
from tic.shared.events.faction import FactionDataExtracted
from tic.shared.models import Resources

pytestmark = pytest.mark.integration

_CAMPAIGN_START = datetime(2022, 6, 15, tzinfo=UTC)
_GAME_DATE = datetime(2035, 3, 10, tzinfo=UTC)


def _campaign_data() -> ExtractedCampaignData:
    return ExtractedCampaignData(
        campaign_start_version="1.0",
        current_date_time=_GAME_DATE,
        current_quarter_since_start=7,
        days_in_campaign=42,
        difficulty=3,
        latest_save_version="1.1",
        real_world_campaign_start=_CAMPAIGN_START,
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
        scenario_key="tpl",
    )


def _faction_data() -> ExtractedFactionData:
    return ExtractedFactionData(
        id=7,
        abductions=1,
        armies=(2,),
        atrocities=3,
        councilors=(4, 5),
        current_date_time=_GAME_DATE,
        fleets=(6,),
        is_ai=False,
        mission_control_usage=9,
        template_name="faction_template",
        resources=Resources(
            antimatter=1.0,
            boost=2.0,
            exotics=3.0,
            fissiles=4.0,
            influence=5.0,
            metals=6.0,
            mission_control=7.0,
            money=8.0,
            noble_metals=9.0,
            operations=10.0,
            volatiles=11.0,
            water=12.0,
        ),
    )


class TestExtractedData:
    @pytest.mark.asyncio
    async def test_publishes_campaign_data_integration_event(self) -> None:
        bus = MessageBusInMemory()
        _, dispatch = SavefileProcessBusOut(bus).subscriptions()[0]
        captured: list[CampaignDataExtracted] = []

        async def capture(event: Message) -> None:
            assert isinstance(event, CampaignDataExtracted)
            captured.append(event)

        bus.subscribe(CampaignDataExtracted, capture)

        extracted = _campaign_data()
        await dispatch(SavefileCampaignDataExtracted(campaign_id=1, data=extracted))

        assert len(captured) == 1
        event = captured[0]
        assert isinstance(event.scenario_customizations, ScenarioCustomizations)
        assert event.scenario_customizations is not extracted.scenario_customizations
        assert event.campaign_start_version == extracted.campaign_start_version

    @pytest.mark.asyncio
    async def test_publishes_faction_data_integration_event(self) -> None:
        bus = MessageBusInMemory()
        _, dispatch = SavefileProcessBusOut(bus).subscriptions()[1]
        captured: list[FactionDataExtracted] = []

        async def capture(event: Message) -> None:
            assert isinstance(event, FactionDataExtracted)
            captured.append(event)

        bus.subscribe(FactionDataExtracted, capture)

        extracted = _faction_data()
        await dispatch(SavefileFactionDataExtracted(campaign_id=1, data=extracted))

        assert len(captured) == 1
        event = captured[0]
        assert event.id == extracted.id
        assert event.current_date_time == extracted.current_date_time
        assert event.resources == extracted.resources
