"""End-to-end test for the faction update pipeline."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tests.tic.conftest import E2ERuntime, E2ERuntimeBuilder
from tic.faction.shared_events import FactionUpdated
from tic.faction.update.shell_bus_in import BusIn as FactionUpdateBusIn
from tic.shared.event_store import EventStore
from tic.shared.events.faction import FactionDataExtracted
from tic.shared.message_bus import MessageBus, Subscription
from tic.shared.models import Resources

pytestmark = pytest.mark.e2e

_DT = datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)

_EXTRACTED = FactionDataExtracted(
    id=1,
    abductions=0,
    armies=(10, 20),
    atrocities=3,
    councilors=(5,),
    current_date_time=_DT,
    fleets=(7,),
    is_ai=False,
    mission_control_usage=2,
    template_name="my_faction",
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


class TestFactionUpdateE2E:
    @pytest.mark.asyncio
    async def test_faction_updated_published_on_bus(
        self,
        e2e_runtime_builder: E2ERuntimeBuilder,
    ) -> None:
        def subscriptions(
            bus: MessageBus,
            event_store: EventStore,
        ) -> tuple[Subscription, ...]:
            return FactionUpdateBusIn(bus, event_store).subscriptions()

        runtime: E2ERuntime = e2e_runtime_builder(
            subscription_factories=(subscriptions,),
            capture_event_types=(FactionUpdated,),
        )

        await runtime.bus.publish(_EXTRACTED)

        published = runtime.captured(FactionUpdated)
        assert len(published) == 1
        assert isinstance(published[0], FactionUpdated)
