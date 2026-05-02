"""In-memory document store — for use in tests and local dev."""

from __future__ import annotations

from tic.shared.document_store import DocumentStore
from tic.shared.log_call import log_call


class DocumentStoreInMemory[T](DocumentStore[T]):
    """Pure in-memory document store. Not thread-safe."""

    def __init__(self) -> None:
        """Initialise with an empty store."""
        self._data: dict[str, T] = {}

    async def all(self) -> list[T]:
        """Return all documents in insertion order."""
        return list(self._data.values())

    async def get(self, key: str) -> T | None:
        """Return the document for key, or None if absent."""
        return self._data.get(key)

    @log_call(with_args=True)
    async def put(self, key: str, document: T) -> None:
        """Insert or replace the document at key."""
        self._data[key] = document

    async def delete(self, key: str) -> None:
        """Delete the document at key. No-op if absent."""
        self._data.pop(key, None)
