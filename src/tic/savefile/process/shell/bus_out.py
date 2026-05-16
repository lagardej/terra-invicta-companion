"""Savefile process status publisher — outbound shell."""

from __future__ import annotations

from framework.events import Message
from framework.log_call import log_call
from framework.message_bus import MessageBus, Subscription
from tic.savefile._events import (
    SavefileCampaignDataExtracted,
    SavefileFactionDataExtracted,
)
from tic.shared.events.campaign import CampaignDataExtracted, ScenarioCustomizations
from tic.shared.events.faction import FactionDataExtracted


class SavefileProcessBusOut:
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

    @log_call()
    async def _dispatch(self, event: Message) -> None:
        match event:
            case SavefileCampaignDataExtracted():
                await self._bus.publish(_to_campaign_data_extracted(event))
            case SavefileFactionDataExtracted():
                await self._bus.publish(_to_faction_data_extracted(event))


def _to_campaign_data_extracted(
    event: SavefileCampaignDataExtracted,
) -> CampaignDataExtracted:
    scenario_customizations = ScenarioCustomizations(
        **vars(event.data.scenario_customizations)
    )

    return CampaignDataExtracted(
        campaign_id=event.campaign_id,
        campaign_start_version=event.data.campaign_start_version,
        current_date_time=event.data.current_date_time,
        current_quarter_since_start=event.data.current_quarter_since_start,
        days_in_campaign=event.data.days_in_campaign,
        difficulty=event.data.difficulty,
        latest_save_version=event.data.latest_save_version,
        real_world_campaign_start=event.data.real_world_campaign_start,
        scenario_customizations=scenario_customizations,
        scenario_key=event.data.scenario_key,
        start_difficulty=event.data.start_difficulty,
    )


def _to_faction_data_extracted(
    event: SavefileFactionDataExtracted,
) -> FactionDataExtracted:
    return FactionDataExtracted(
        abductions=event.data.abductions,
        armies=event.data.armies,
        atrocities=event.data.atrocities,
        campaign_id=event.campaign_id,
        councilors=event.data.councilors,
        current_date_time=event.data.current_date_time,
        fleets=event.data.fleets,
        id=event.data.id,
        is_ai=event.data.is_ai,
        mission_control_usage=event.data.mission_control_usage,
        resources=event.data.resources,
        template_name=event.data.template_name,
    )
