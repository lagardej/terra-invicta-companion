"""Bootstrap — wires settings into logging and the application container."""

from __future__ import annotations

import sys

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from lagom import ExplicitContainer

from tic._config.logging import configure as configure_logging
from tic._config.profiles import DevProfile
from tic.faction.update.core import UpdateFactionHandler
from tic.faction.update.shell import FactionUpdateListener
from tic.home.shell import HomeHttp
from tic.savefile.list.document import SavefileLogEntry
from tic.savefile.list.shell import SavefileListHttp, SavefileListListener
from tic.savefile.process.core import ProcessSavefileHandler
from tic.savefile.process.shell import SavefileProcess
from tic.shared.application import Application
from tic.shared.document_store import DocumentStore
from tic.shared.event_store import EventStore
from tic.shared.message_bus import MessageBus
from tic.shared.profile import Profile
from tic.shared.settings import ConfigurationError, Settings


def boot(profile: Profile = DevProfile) -> Application[Settings]:
    """Configure logging and build the wired application."""
    try:
        load_dotenv()
        settings = Settings.load()
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    configure_logging(settings.log_level, settings.app_dir)
    c = ExplicitContainer()

    _register_infra(c, profile, settings)
    _register_services(c)

    return Application(container=c, settings=settings)


def _register_infra(c: ExplicitContainer, profile: Profile, settings: Settings) -> None:
    c[MessageBus] = profile.message_bus()
    c[EventStore] = profile.event_store()
    c[DocumentStore[SavefileLogEntry]] = profile.document_store_savefile_log_entry()

    c[FastAPI] = FastAPI(title="Terra Invicta Companion")
    c[uvicorn.Server] = uvicorn.Server(
        uvicorn.Config(c[FastAPI], port=settings.port, log_config=None)
    )


def _register_services(c: ExplicitContainer) -> None:
    _register_command_handlers(c)
    _register_subscribers(c)
    _register_routers(c)


def _register_command_handlers(c: ExplicitContainer) -> None:
    c[ProcessSavefileHandler] = lambda: ProcessSavefileHandler()
    c[UpdateFactionHandler] = lambda: UpdateFactionHandler()


def _register_routers(c: ExplicitContainer) -> None:
    c[HomeHttp] = lambda: HomeHttp()
    c[SavefileListHttp] = lambda: SavefileListHttp(
        store=c[DocumentStore[SavefileLogEntry]]
    )

    c[FastAPI].include_router(c[HomeHttp].router())
    c[FastAPI].include_router(c[SavefileListHttp].router())


def _register_subscribers(c: ExplicitContainer) -> None:
    message_bus = c[MessageBus]
    event_store = c[EventStore]

    c[SavefileProcess] = lambda: SavefileProcess(
        bus=message_bus,
        event_store=event_store,
        handler=c[ProcessSavefileHandler],
    )
    c[FactionUpdateListener] = lambda: FactionUpdateListener(
        bus=message_bus,
        event_store=event_store,
        handler=c[UpdateFactionHandler],
    )
    c[SavefileListListener] = lambda: SavefileListListener(
        store=c[DocumentStore[SavefileLogEntry]]
    )

    message_bus.subscribe(*c[SavefileProcess].subscriptions())
    message_bus.subscribe(*c[FactionUpdateListener].subscriptions())
    message_bus.subscribe(*c[SavefileListListener].subscriptions())
