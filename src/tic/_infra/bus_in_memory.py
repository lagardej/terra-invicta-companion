"""Async message bus."""

from __future__ import annotations

from collections import defaultdict

from tic.shared.events.base import Message
from tic.shared.log_call import log_call
from tic.shared.message_bus import Handler, MessageBus


class MessageBusInMemory(MessageBus):
    """Simple async publish/subscribe bus."""

    def __init__(self) -> None:
        """Initialise with an empty handler registry."""
        self._handlers: dict[type[Message], list[Handler]] = defaultdict(list)

    @log_call(with_args=True)
    def _subscribe(self, event_class: type[Message], handler: Handler) -> None:
        """Register a single handler for a message type."""
        self._handlers[event_class].append(handler)

    @log_call(with_args=True)
    async def _publish(self, event: Message) -> None:
        """Dispatch event to all handlers subscribed to its type."""
        event_type = type(event)
        handlers = self._handlers[event_type]
        for handler in handlers:
            await self._dispatch(event, handler)

    @log_call(with_args=True)
    async def _dispatch(self, event: Message, handler: Handler) -> None:
        await handler(event)
