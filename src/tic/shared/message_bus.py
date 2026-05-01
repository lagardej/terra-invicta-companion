"""Message bus abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Sequence
from typing import overload

from tic.shared.events.base import Message

Handler = Callable[[Message], Awaitable[None]]


class MessageBus(ABC):
    """Abstract base for message buses."""

    @abstractmethod
    def subscribe(self, event_class: type[Message], handler: Handler) -> None:
        """Register a handler for a message type."""

    @abstractmethod
    async def _publish(self, event: Message) -> None:
        """Publish an event to subscribers."""

    @overload
    async def publish(
        self, event: Message
    ) -> None:  # pragma: no cover - typing overload
        ...

    @overload
    async def publish(
        self, *events: Message
    ) -> None:  # pragma: no cover - typing overload
        ...

    @overload
    async def publish(
        self, events: Sequence[Message]
    ) -> None:  # pragma: no cover - typing overload
        ...

    async def publish(self, *events):  # type: ignore[override]
        """Publish one or more events.

        Usage:
        - `await bus.publish(msg)`
        - `await bus.publish(m1, m2, m3)`
        - `await bus.publish((m1, m2))` (pass a tuple/list without unpacking)
        """
        # allow callers to pass a single tuple/list of messages without unpacking
        if len(events) == 1:
            first = events[0]
            if isinstance(first, (tuple, list)):
                events = tuple(first)

        for event in events:
            await self._publish(event)
