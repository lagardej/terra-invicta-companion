"""Savefile process status publisher — outbound shell."""

from __future__ import annotations

from tic.savefile._events import (
    SavefileCampaignDataExtracted,
    SavefileFactionDataExtracted,
)
from tic.savefile.process.core.extracted_data import (
    ExtractedCampaignData,
    ExtractedFactionData,
)
from tic.shared.events.base import Message
from tic.shared.events.campaign import CampaignDataExtracted, ScenarioCustomizations
from tic.shared.events.faction import FactionDataExtracted
from tic.shared.log_call import log_call
from tic.shared.message_bus import MessageBus, Subscription


class BusOut:
    """Publish integration events from extracted savefile process data."""

    def __init__(self, bus: MessageBus) -> None:
        """Store dependencies used by the savefile process outbound shell."""
        self._bus = bus

    def subscriptions(self) -> tuple[Subscription, ...]:
        """Return subscriptions for publishing integration events."""
        return (
            (SavefileCampaignDataExtracted, self._dispatch),
            (SavefileFactionDataExtracted, self._dispatch),
        )

    async def _dispatch(self, event: Message) -> None:
        match event:
            case SavefileCampaignDataExtracted() as e:
                await self._on_campaign_data_extracted(e)
            case SavefileFactionDataExtracted() as e:
                await self._on_faction_data_extracted(e)

    @log_call()
    async def _on_campaign_data_extracted(
        self,
        event: SavefileCampaignDataExtracted,
    ) -> None:
        await self._bus.publish(_to_campaign_data_extracted(event.data))

    @log_call()
    async def _on_faction_data_extracted(
        self,
        event: SavefileFactionDataExtracted,
    ) -> None:
        await self._bus.publish(_to_faction_data_extracted(event.data))


def _to_campaign_data_extracted(item: ExtractedCampaignData) -> CampaignDataExtracted:
    scenario_customizations = ScenarioCustomizations(
        **vars(item.scenario_customizations)
    )

    return CampaignDataExtracted(
        campaign_start_version=item.campaign_start_version,
        current_date_time=item.current_date_time,
        current_quarter_since_start=item.current_quarter_since_start,
        days_in_campaign=item.days_in_campaign,
        difficulty=item.difficulty,
        latest_save_version=item.latest_save_version,
        real_world_campaign_start=item.real_world_campaign_start,
        scenario_customizations=scenario_customizations,
        start_difficulty=item.start_difficulty,
        template_name=item.template_name,
    )


def _to_faction_data_extracted(item: ExtractedFactionData) -> FactionDataExtracted:
    return FactionDataExtracted(
        id=item.id,
        abductions=item.abductions,
        armies=item.armies,
        atrocities=item.atrocities,
        councilors=item.councilors,
        current_date_time=item.current_date_time,
        fleets=item.fleets,
        is_ai=item.is_ai,
        mission_control_usage=item.mission_control_usage,
        template_name=item.template_name,
        resources=item.resources,
    )
