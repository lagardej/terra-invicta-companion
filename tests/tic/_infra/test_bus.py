"""Tests for the async message bus."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from tic._infra.bus_in_memory import MessageBusInMemory
from tic.shared.events.base import DomainEvent, IntegrationEvent

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class _SaveDetected(IntegrationEvent):
    path: str


@dataclass(frozen=True)
class _ImportSucceeded(DomainEvent):
    @classmethod
    def type(cls) -> str:
        return "savefile.import_succeeded"


async def test_subscribed_handler_is_called() -> None:
    bus = MessageBusInMemory()
    received: list[object] = []

    async def handler(payload: object) -> None:
        received.append(payload)

    event = _SaveDetected(path="/saves/Autosave.json")
    bus.subscribe(_SaveDetected, handler)
    await bus.publish(event)

    assert received == [event]


async def test_multiple_handlers_all_called() -> None:
    bus = MessageBusInMemory()
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


async def test_unrelated_event_not_dispatched() -> None:
    bus = MessageBusInMemory()
    received: list[object] = []

    async def handler(payload: object) -> None:
        received.append(payload)

    bus.subscribe(_SaveDetected, handler)
    await bus.publish(_ImportSucceeded())

    assert received == []


async def test_no_subscribers_publish_is_silent() -> None:
    bus = MessageBusInMemory()
    await bus.publish(_SaveDetected(path="/saves/Autosave.json"))
