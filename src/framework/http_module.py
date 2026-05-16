"""HttpModule protocol — contract for routable modules."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fastapi import APIRouter


@runtime_checkable
class HttpModule(Protocol):
    """A module that exposes routes to mount on the FastAPI app."""

    def router(self) -> APIRouter:
        """Return the APIRouter to mount on the application."""
        ...
