"""Unit tests for the faction update use case — core and shell."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from tic.faction.update.core import FactionState, UpdateFaction, UpdateFactionHandler
from tic.faction.update.shell import FactionUpdateListener
from tic.shared.command import CommandContext
from tic.shared.event_store import EventStore
from tic.shared.events.faction import FactionDataExtracted, FactionUpdated, Resources
from tic.shared.message_bus import MessageBus

pytestmark = pytest.mark.unit

_DT = datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)

_RESOURCES = Resources(
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
)

_COMMAND = UpdateFaction(
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
    resources=_RESOURCES,
)

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
    resources=_RESOURCES,
)


class TestUpdateFactionHandler:
    @pytest.mark.asyncio
    async def test_returns_faction_updated(self) -> None:
        handler = UpdateFactionHandler()
        context: CommandContext[FactionState] = CommandContext(state=None)

        result = await handler.handle(_COMMAND, context)

        assert isinstance(result, FactionUpdated)

    @pytest.mark.asyncio
    async def test_faction_updated_mirrors_command_data(self) -> None:
        handler = UpdateFactionHandler()
        context: CommandContext[FactionState] = CommandContext(state=None)

        result = await handler.handle(_COMMAND, context)

        expected = FactionUpdated(
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
            resources=_RESOURCES,
        )
        assert result == expected


class TestFactionUpdateListener:
    def test_subscriptions_include_faction_data_extracted(self) -> None:
        listener = FactionUpdateListener(
            bus=AsyncMock(spec=MessageBus),
            event_store=AsyncMock(spec=EventStore),
            handler=UpdateFactionHandler(),
        )

        event_types = [event_type for event_type, _ in listener.subscriptions()]

        assert FactionDataExtracted in event_types

    @pytest.mark.asyncio
    async def test_publishes_faction_updated_on_bus(self) -> None:
        from tic._infra.event_store_in_memory import EventStoreInMemory

        bus = AsyncMock(spec=MessageBus)
        listener = FactionUpdateListener(
            bus=bus,
            event_store=EventStoreInMemory(),
            handler=UpdateFactionHandler(),
        )

        await listener._on_faction_data_extracted(_EXTRACTED)

        bus.publish.assert_awaited_once()
        published = bus.publish.call_args.args[0]
        assert isinstance(published, FactionUpdated)
        assert published.id == _EXTRACTED.id

    @pytest.mark.asyncio
    async def test_persists_faction_updated_to_event_store(self) -> None:
        from tic._infra.event_store_in_memory import EventStoreInMemory

        bus = AsyncMock(spec=MessageBus)
        event_store = EventStoreInMemory()
        listener = FactionUpdateListener(
            bus=bus,
            event_store=event_store,
            handler=UpdateFactionHandler(),
        )

        await listener._on_faction_data_extracted(_EXTRACTED)

        assert len(event_store._streams) == 1
        assert isinstance(event_store._streams[0], FactionUpdated)
