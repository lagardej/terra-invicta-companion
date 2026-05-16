"""Shared test runtime helpers for e2e tests under tests/tic."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from inspect import signature
from typing import TypeVar, cast

import pytest

from framework.events import Message
from framework.message_bus import Subscription
from tic._infra.bus_in_memory import MessageBusInMemory
from tic._infra.event_store_in_memory import EventStoreInMemory

type SubscriptionFactory = Callable[..., tuple[Subscription, ...]]
type E2ERuntimeBuilder = Callable[..., E2ERuntime]
_EventT = TypeVar("_EventT", bound=Message)


@dataclass
class E2ERuntime:
    """In-memory runtime with bus/store and captured integration events."""

    bus: MessageBusInMemory
    event_store: EventStoreInMemory
    captured_events: dict[type[Message], list[Message]] = field(default_factory=dict)

    def captured(self, event_type: type[_EventT]) -> list[_EventT]:
        """Return captured events for a subscribed event type."""
        return cast(list[_EventT], self.captured_events[event_type])


def build_e2e_runtime(
    subscription_factories: tuple[SubscriptionFactory, ...] = (),
    capture_event_types: tuple[type[Message], ...] = (),
) -> E2ERuntime:
    """Create in-memory runtime, wire subscriptions, and attach event capture."""
    bus = MessageBusInMemory()
    event_store = EventStoreInMemory()
    runtime = E2ERuntime(bus=bus, event_store=event_store)

    for factory in subscription_factories:
        params_len = len(signature(factory).parameters)
        subscriptions = factory(bus) if params_len == 1 else factory(bus, event_store)
        bus.subscribe(*subscriptions)

    for event_type in capture_event_types:
        runtime.captured_events[event_type] = []

        async def _capture(
            event: Message,
            _event_type: type[Message] = event_type,
        ) -> None:
            assert isinstance(event, _event_type)
            runtime.captured_events[_event_type].append(event)

        bus.subscribe(event_type, _capture)

    return runtime


@pytest.fixture
def e2e_runtime_builder() -> E2ERuntimeBuilder:
    """Return a generic builder for in-memory e2e runtimes."""
    return build_e2e_runtime
