"""Message bus abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from tic.shared.events.base import Message

Handler = Callable[[Message], Awaitable[None]]


class MessageBus(ABC):
    """Abstract base for message buses."""

    @abstractmethod
    def subscribe(self, event_class: type[Message], handler: Handler) -> None:
        """Register a handler for a message type."""

    @abstractmethod
    async def publish(self, event: Message) -> None:
        """Publish an event to subscribers."""
