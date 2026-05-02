"""End-to-end test for the faction update pipeline."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tic._infra.bus_in_memory import MessageBusInMemory
from tic._infra.event_store_in_memory import EventStoreInMemory
from tic.faction.update.core import UpdateFactionHandler
from tic.faction.update.shell import FactionUpdateListener
from tic.shared.events.faction import FactionDataExtracted, FactionUpdated, Resources

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


def _runtime() -> tuple[MessageBusInMemory, FactionUpdateListener]:
    bus = MessageBusInMemory()
    event_store = EventStoreInMemory()
    listener = FactionUpdateListener(
        bus=bus,
        event_store=event_store,
        handler=UpdateFactionHandler(),
    )
    bus.subscribe(*listener.subscriptions())
    return bus, listener


class TestFactionUpdateE2E:
    @pytest.mark.asyncio
    async def test_faction_updated_published_on_bus(self) -> None:
        bus, _ = _runtime()
        published: list[object] = []

        async def capture(event: object) -> None:
            published.append(event)

        bus.subscribe(FactionUpdated, capture)

        await bus.publish(_EXTRACTED)

        assert len(published) == 1
        assert isinstance(published[0], FactionUpdated)
