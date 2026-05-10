"""Savefile list HTTP inbound shell — serves the savefile log over HTTP."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from tic.savefile.list.document import SavefileLogEntry
from tic.shared.document_store import DocumentStore
from tic.shared.http_module import HttpModule

_TEMPLATES_DIR = Path(__file__).parents[4] / "templates"


class HttpIn(HttpModule):
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
