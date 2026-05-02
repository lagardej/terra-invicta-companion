"""Home HTTP module — serves the landing page."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from tic.shared.http_module import HttpModule

_TEMPLATES_DIR = Path(__file__).parents[3] / "templates"


class HomeHttp(HttpModule):
    """Serves the application homepage."""

    def router(self) -> APIRouter:
        """Return the FastAPI router for the homepage."""
        router = APIRouter()
        templates = Jinja2Templates(directory=_TEMPLATES_DIR)

        @router.get("/", response_class=HTMLResponse)
        async def home(request: Request) -> HTMLResponse:
            return templates.TemplateResponse(request, "index.html", {})

        return router
