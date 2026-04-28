"""Async message bus."""

from __future__ import annotations

from collections import defaultdict

from tic.shared.events.base import Message
from tic.shared.message_bus import Handler, MessageBus


class MessageBusInMemory(MessageBus):
    """Simple async publish/subscribe bus."""

    def __init__(self) -> None:
        """Initialise with an empty handler registry."""
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event_class: type[Message], handler: Handler) -> None:
        """Register a handler for a message type."""
        self._handlers[event_class.type()].append(handler)

    async def publish(self, event: Message) -> None:
        """Dispatch event to all handlers subscribed to its type."""
        for handler in self._handlers[type(event).type()]:
            await handler(event)
