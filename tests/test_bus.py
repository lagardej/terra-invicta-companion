"""Tests for the async message bus."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from tic.bus import Bus
from tic.shared.events.base import DomainEvent, IntegrationEvent


@dataclass(frozen=True)
class _SaveDetected(IntegrationEvent):
    path: str

    @classmethod
    def type(cls) -> str:
        return "savefile.detected"


@dataclass(frozen=True)
class _ImportSucceeded(DomainEvent):
    @classmethod
    def type(cls) -> str:
        return "savefile.import_succeeded"


class TestBus:
    """Async message bus behaviour."""

    @pytest.mark.unit
    async def test_subscribed_handler_is_called(self) -> None:
        bus = Bus()
        received: list[object] = []

        async def handler(payload: object) -> None:
            received.append(payload)

        event = _SaveDetected(path="/saves/Autosave.json")
        bus.subscribe(_SaveDetected, handler)
        await bus.publish(event)

        assert received == [event]

    @pytest.mark.unit
    async def test_multiple_handlers_all_called(self) -> None:
        bus = Bus()
        received: list[object] = []

        async def handler_a(payload: object) -> None:
            received.append(("a", payload))

        async def handler_b(payload: object) -> None:
            received.append(("b", payload))

        event = _SaveDetected(path="/saves/Autosave.json")
        bus.subscribe(_SaveDetected, handler_a)
        bus.subscribe(_SaveDetected, handler_b)
        await bus.publish(event)

        assert ("a", event) in received
        assert ("b", event) in received

    @pytest.mark.unit
    async def test_unrelated_event_not_dispatched(self) -> None:
        bus = Bus()
        received: list[object] = []

        async def handler(payload: object) -> None:
            received.append(payload)

        bus.subscribe(_SaveDetected, handler)
        await bus.publish(_ImportSucceeded())

        assert received == []

    @pytest.mark.unit
    async def test_no_subscribers_publish_is_silent(self) -> None:
        bus = Bus()
        await bus.publish(_SaveDetected(path="/saves/Autosave.json"))
