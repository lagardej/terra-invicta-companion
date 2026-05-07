"""Savefile log shell — subscriber and HTTP handler."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from tic.savefile._events import (
    SavefileProcessingFailed,
    SavefileProcessingSucceeded,
)
from tic.savefile.list.document import SavefileLogEntry, SavefileProcessingStatus
from tic.shared.document_store import DocumentStore
from tic.shared.events.base import Message
from tic.shared.http_module import HttpModule
from tic.shared.log_call import log_call
from tic.shared.message_bus import Subscription

_TEMPLATES_DIR = Path(__file__).parents[4] / "templates"


def savefile_list_subscriptions(
    store: DocumentStore[SavefileLogEntry],
    now: Callable[[], datetime] | None = None,
) -> tuple[Subscription, ...]:
    """Return subscriptions for projecting savefile processing events into the log."""
    _now = _utcnow if now is None else now

    async def _dispatch(event: Message) -> None:
        match event:
            case SavefileProcessingSucceeded() as e:
                await _on_succeeded(e)
            case SavefileProcessingFailed() as e:
                await _on_failed(e)

    @log_call()
    async def _on_succeeded(event: SavefileProcessingSucceeded) -> None:
        entry = SavefileLogEntry(
            id=_new_id(),
            status=SavefileProcessingStatus.SUCCEEDED,
            reason=None,
            real_world_campaign_start=event.real_world_campaign_start,
            player_faction=event.player_faction,
            current_date_time=event.current_date_time,
            duration_ms=event.duration_ms,
            recorded_at=_now(),
        )
        await store.put(entry.id, entry)

    @log_call()
    async def _on_failed(event: SavefileProcessingFailed) -> None:
        entry = SavefileLogEntry(
            id=_new_id(),
            status=SavefileProcessingStatus.FAILED,
            reason=event.reason,
            real_world_campaign_start=event.real_world_campaign_start,
            player_faction=event.player_faction,
            current_date_time=event.current_date_time,
            duration_ms=None,
            recorded_at=_now(),
        )
        await store.put(entry.id, entry)

    return (
        (SavefileProcessingSucceeded, _dispatch),
        (SavefileProcessingFailed, _dispatch),
    )


def _new_id() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


class SavefileListHttp(HttpModule):
    """Exposes the savefile log over HTTP."""

    def __init__(self, store: DocumentStore[SavefileLogEntry]) -> None:
        """Initialise with the log document store."""
        self._store = store

    def router(self) -> APIRouter:
        """Return the FastAPI router for the savefile log."""
        router = APIRouter()
        templates = Jinja2Templates(directory=_TEMPLATES_DIR)

        @router.get("/savefiles/", response_class=HTMLResponse)
        async def list_savefiles(request: Request) -> HTMLResponse:
            entries = await self._store.all()
            entries.sort(key=lambda e: e.recorded_at, reverse=True)
            return templates.TemplateResponse(
                request, "savefiles/list/index.html", {"entries": entries}
            )

        @router.get("/savefiles/table", response_class=HTMLResponse)
        async def list_savefiles_table(request: Request) -> HTMLResponse:
            entries = await self._store.all()
            entries.sort(key=lambda e: e.recorded_at, reverse=True)
            return templates.TemplateResponse(
                request, "savefiles/list/_table.html", {"entries": entries}
            )

        return router
