"""Savefile list bus inbound shell — projects processing events into the log store."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from framework.document_store import DocumentStore
from framework.events import Message
from framework.log_call import log_call
from framework.message_bus import Subscription
from tic.savefile._events import SavefileProcessed
from tic.savefile.list.document import SavefileLogEntry


class SavefileListBusIn:
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
        return ((SavefileProcessed, self._dispatch),)

    async def _dispatch(self, event: Message) -> None:
        match event:
            case SavefileProcessed() as e:
                await self._on_succeeded(e)

    @log_call()
    async def _on_succeeded(self, event: SavefileProcessed) -> None:
        entry = SavefileLogEntry(
            id=str(uuid.uuid4()),
            reason=None,
            real_world_campaign_start=event.real_world_campaign_start,
            scenario_id=event.scenario_id,
            current_date_time=event.current_date_time,
            duration_ms=event.duration_ms,
            recorded_at=self._now(),
        )
        await self._store.put(entry.id, entry)


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)
