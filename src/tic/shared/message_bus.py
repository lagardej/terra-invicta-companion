"""Message bus abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Sequence
from typing import cast, overload

from tic.shared.events.base import Message

Handler = Callable[[Message], Awaitable[None]]
Subscription = tuple[type[Message], Handler]


class MessageBus(ABC):
    """Abstract base for message buses."""

    def subscribe(
        self,
        *args: type[Message] | Handler | Subscription,
    ) -> None:
        """Register one or more (event_type, handler) subscriptions.

        Accepts either:
        - ``bus.subscribe(EventType, handler)`` — flat two-arg form
        - ``bus.subscribe((EventType, handler), ...)`` — tuple form
        """
        if len(args) == 2 and isinstance(args[0], type) and callable(args[1]):
            self._subscribe(args[0], cast(Handler, args[1]))
        else:
            for subscription in args:
                self._subscribe(*cast(Subscription, subscription))

    @abstractmethod
    def _subscribe(self, event_class: type[Message], handler: Handler) -> None:
        """Register a single handler for a message type."""

    @overload
    async def publish(self, event: Message) -> None: ...

    @overload
    async def publish(self, *events: Message) -> None: ...

    @overload
    async def publish(self, events: Sequence[Message]) -> None: ...

    async def publish(self, *events) -> None:  # type: ignore[override]
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

    @abstractmethod
    async def _publish(self, event: Message) -> None:
        """Publish an event to subscribers."""
