"""Tests for DocumentStoreInMemory."""

from __future__ import annotations

import pytest

from tic._infra.document_store_in_memory import DocumentStoreInMemory


@pytest.fixture
def store() -> DocumentStoreInMemory[str]:
    return DocumentStoreInMemory[str]()


class TestDocumentStoreAll:
    async def test_empty_returns_empty_list(
        self, store: DocumentStoreInMemory[str]
    ) -> None:
        assert await store.all() == []

    async def test_returns_all_documents(
        self, store: DocumentStoreInMemory[str]
    ) -> None:
        await store.put("a", "alpha")
        await store.put("b", "beta")

        assert await store.all() == ["alpha", "beta"]


class TestDocumentStoreGet:
    async def test_missing_key_returns_none(
        self, store: DocumentStoreInMemory[str]
    ) -> None:
        assert await store.get("missing") is None

    async def test_existing_key_returns_document(
        self, store: DocumentStoreInMemory[str]
    ) -> None:
        await store.put("k", "value")

        assert await store.get("k") == "value"


class TestDocumentStorePut:
    async def test_put_overwrites_existing(
        self, store: DocumentStoreInMemory[str]
    ) -> None:
        await store.put("k", "first")
        await store.put("k", "second")

        assert await store.get("k") == "second"


class TestDocumentStoreDelete:
    async def test_delete_removes_document(
        self, store: DocumentStoreInMemory[str]
    ) -> None:
        await store.put("k", "value")
        await store.delete("k")

        assert await store.get("k") is None

    async def test_delete_missing_key_is_noop(
        self, store: DocumentStoreInMemory[str]
    ) -> None:
        await store.delete("missing")  # must not raise
