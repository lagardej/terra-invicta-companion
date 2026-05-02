"""Document store abstract base class — generic NoSQL-style interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DocumentStore[T](ABC):
    """Generic key/value document store."""

    @abstractmethod
    async def all(self) -> list[T]:
        """Return all documents."""
        ...

    @abstractmethod
    async def get(self, key: str) -> T | None:
        """Return the document for key, or None if absent."""
        ...

    @abstractmethod
    async def put(self, key: str, document: T) -> None:
        """Insert or replace the document at key."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete the document at key. No-op if absent."""
        ...


# Satisfy type checkers when a concrete store is referenced as DocumentStore[Any].
type AnyDocumentStore = DocumentStore[Any]
