"""Application wiring — builds the lagom container and exposes the server."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from lagom import Container

from tic._infra.bus_in_memory import MessageBusInMemory
from tic._infra.document_store_in_memory import DocumentStoreInMemory
from tic._infra.event_store_in_memory import EventStoreInMemory
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
from tic.shared.event_subscriber import EventSubscriber
from tic.shared.events.faction import FactionUpdated
from tic.shared.http_module import HttpModule
from tic.shared.message_bus import MessageBus


def build_server(
    host: str = "127.0.0.1", port: int = 8000
) -> tuple[uvicorn.Server, MessageBus]:
    """Build the wired application and return the uvicorn server and message bus."""
    c = Container()

    # Infrastructure bindings
    bus = MessageBusInMemory()
    event_store = EventStoreInMemory()
    log_store: DocumentStoreInMemory[SavefileLogEntry] = DocumentStoreInMemory()

    c.define(MessageBus, lambda: bus)
    c.define(EventStore, lambda: event_store)
    c.define(DocumentStore[SavefileLogEntry], lambda: log_store)  # type: ignore[type-abstract]
    c.define(
        CommandHandler[ProcessSavefile, ProcessResult, SavefileState],  # type: ignore[type-abstract]
        lambda: ProcessSavefileHandler(),
    )
    c.define(
        CommandHandler[UpdateFaction, FactionUpdated, FactionState],  # type: ignore[type-abstract]
        lambda: UpdateFactionHandler(),
    )

    # Module resolution
    modules: list[EventSubscriber | HttpModule] = [
        c[HomeHttp],
        c[SavefileProcess],
        c[SavefileListListener],
        c[SavefileListHttp],
        c[FactionUpdateListener],
    ]

    # Wiring
    app = FastAPI(title="Terra Invicta Companion")
    for module in modules:
        if isinstance(module, EventSubscriber):
            bus.subscribe(*module.subscriptions())
        if isinstance(module, HttpModule):
            app.include_router(module.router())

    server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_config=None))
    return server, bus
