"""Async message bus — functional core, no I/O."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable

type Payload = object

Handler = Callable[[Payload], Awaitable[None]]


class Bus:
    """Simple async publish/subscribe bus."""

    def __init__(self) -> None:
        """Initialise with an empty handler registry."""
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event: str, handler: Handler) -> None:
        """Register a handler for an event type."""
        self._handlers[event].append(handler)

    async def publish(self, event: str, payload: Payload) -> None:
        """Dispatch payload to all handlers subscribed to event."""
        for handler in self._handlers[event]:
            await handler(payload)
