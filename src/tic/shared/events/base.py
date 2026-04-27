"""Base message types for the event bus."""

from __future__ import annotations


class Message:
    """Common base for all bus messages. Subclasses declare their type string."""

    @classmethod
    def type(cls) -> str:
        """Return the unique string identifier for this message type."""
        raise NotImplementedError


class DomainEvent(Message):
    """Base for domain events emitted by the functional core."""


class IntegrationEvent(Message):
    """Base for integration events that cross module boundaries."""
