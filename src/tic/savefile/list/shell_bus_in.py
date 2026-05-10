"""Savefile list bus inbound shell — projects processing events into the log store."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from tic.savefile._events import (
    SavefileProcessingFailed,
    SavefileProcessingSucceeded,
)
from tic.savefile.list.document import SavefileLogEntry, SavefileProcessingStatus
from tic.shared.document_store import DocumentStore
from tic.shared.events.base import Message
from tic.shared.log_call import log_call
from tic.shared.message_bus import Subscription


class BusIn:
    """Project savefile processing events into the savefile log store."""

    def __init__(
        self,
        store: DocumentStore[SavefileLogEntry],
        now: Callable[[], datetime] | None = None,
    ) -> None:
        """Store dependencies used by the savefile list bus inbound shell."""
        self._store = store
        self._now = _utcnow if now is None else now

    def subscriptions(self) -> tuple[Subscription, ...]:
        """Return subscriptions for projecting processing events into the log."""
        return (
            (SavefileProcessingSucceeded, self._dispatch),
            (SavefileProcessingFailed, self._dispatch),
        )

    async def _dispatch(self, event: Message) -> None:
        match event:
            case SavefileProcessingSucceeded() as e:
                await self._on_succeeded(e)
            case SavefileProcessingFailed() as e:
                await self._on_failed(e)

    @log_call()
    async def _on_succeeded(self, event: SavefileProcessingSucceeded) -> None:
        entry = SavefileLogEntry(
            id=_new_id(),
            status=SavefileProcessingStatus.SUCCEEDED,
            reason=None,
            real_world_campaign_start=event.real_world_campaign_start,
            player_faction=event.player_faction,
            current_date_time=event.current_date_time,
            duration_ms=event.duration_ms,
            recorded_at=self._now(),
        )
        await self._store.put(entry.id, entry)

    @log_call()
    async def _on_failed(self, event: SavefileProcessingFailed) -> None:
        entry = SavefileLogEntry(
            id=_new_id(),
            status=SavefileProcessingStatus.FAILED,
            reason=event.reason,
            real_world_campaign_start=event.real_world_campaign_start,
            player_faction=event.player_faction,
            current_date_time=event.current_date_time,
            duration_ms=None,
            recorded_at=self._now(),
        )
        await self._store.put(entry.id, entry)


def _new_id() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)
