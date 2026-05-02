"""Base message types for the event bus."""

from __future__ import annotations

from abc import ABC, abstractmethod


class DomainEvent(ABC):
    """Base for domain events emitted by the functional core."""

    @classmethod
    @abstractmethod
    def type(cls) -> str:
        """Return the unique string identifier for this message type."""


class IntegrationEvent(ABC):
    """Base for integration events that cross module boundaries."""

    @classmethod
    @abstractmethod
    def type(cls) -> str:
        """Return the unique string identifier for this message type."""


Message = DomainEvent | IntegrationEvent
