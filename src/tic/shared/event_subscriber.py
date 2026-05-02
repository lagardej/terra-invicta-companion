"""EventSubscriber protocol — contract for bus-subscribable modules."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from tic.shared.message_bus import Subscription


@runtime_checkable
class EventSubscriber(Protocol):
    """A module that registers handlers on the message bus."""

    def subscriptions(self) -> tuple[Subscription, ...]:
        """Return (event_type, handler) pairs to register on the bus."""
        ...
