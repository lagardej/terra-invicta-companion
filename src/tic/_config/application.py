"""Application wiring — builds the lagom container."""

from __future__ import annotations

from typing import TypeVar

import uvicorn
from fastapi import FastAPI
from lagom import ExplicitContainer

from tic._config.profiles import DevProfile
from tic._config.settings import Settings
from tic.faction.update.core import FactionState, UpdateFaction, UpdateFactionHandler
from tic.faction.update.shell import FactionUpdateListener
from tic.home.shell import HomeHttp
from tic.savefile.list.document import SavefileLogEntry
from tic.savefile.list.shell import SavefileListHttp, SavefileListListener
from tic.savefile.process.core import (
    ProcessResult,
    ProcessSavefile,
    ProcessSavefileHandler,
    SavefileState,
)
from tic.savefile.process.shell import SavefileProcess
from tic.shared.command import CommandHandler
from tic.shared.document_store import DocumentStore
from tic.shared.event_store import EventStore
from tic.shared.events.faction import FactionUpdated
from tic.shared.message_bus import MessageBus
from tic.shared.profile import Profile

_T = TypeVar("_T")


class Application:
    """Wired application — wraps the lagom container and exposes typed helpers."""

    def __init__(
        self,
        container: ExplicitContainer,
        settings: Settings,
    ) -> None:
        self._container = container
        self.settings = settings

    def resolve(self, type_: type[_T]) -> _T:
        """Resolve a type from the container."""
        return self._container[type_]  # type: ignore[return-value]


def build_application(
    settings: Settings,
    profile: Profile = DevProfile,
) -> Application:
    """Build and wire the application container."""
    c = ExplicitContainer()

    c[MessageBus] = profile.message_bus()
    c[EventStore] = profile.event_store()
    c[DocumentStore[SavefileLogEntry]] = profile.document_store_savefile_log_entry()

    c[FastAPI] = FastAPI(title="Terra Invicta Companion")
    c[uvicorn.Server] = uvicorn.Server(
        uvicorn.Config(c[FastAPI], port=settings.port, log_config=None)
    )

    _register_command_handlers(c)
    _register_subscribers(c)
    _register_routers(c)

    return Application(container=c, settings=settings)


def _register_command_handlers(c: ExplicitContainer) -> None:
    c[CommandHandler[ProcessSavefile, ProcessResult, SavefileState]] = lambda: (
        ProcessSavefileHandler()
    )
    c[CommandHandler[UpdateFaction, FactionUpdated, FactionState]] = lambda: (
        UpdateFactionHandler()
    )


def _register_routers(c: ExplicitContainer) -> None:
    document_store = c[DocumentStore[SavefileLogEntry]]
    c[HomeHttp] = lambda: HomeHttp()
    c[SavefileListHttp] = lambda: SavefileListHttp(store=document_store)


def _register_subscribers(c: ExplicitContainer) -> None:
    message_bus = c[MessageBus]
    event_store = c[EventStore]
    document_store = c[DocumentStore[SavefileLogEntry]]

    c[SavefileProcess] = lambda: SavefileProcess(
        bus=message_bus,
        event_store=event_store,
        handler=c[CommandHandler[ProcessSavefile, ProcessResult, SavefileState]],
    )
    c[FactionUpdateListener] = lambda: FactionUpdateListener(
        bus=message_bus,
        event_store=event_store,
        handler=c[CommandHandler[UpdateFaction, FactionUpdated, FactionState]],
    )
    c[SavefileListListener] = lambda: SavefileListListener(store=document_store)
