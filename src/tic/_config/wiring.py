"""Dependency injection container — owns construction and wiring of all services."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from tic._infra.bus_in_memory import MessageBusInMemory
from tic._infra.document_store_in_memory import DocumentStoreInMemory
from tic._infra.event_store_in_memory import EventStoreInMemory
from tic.savefile.list.document import SavefileLogEntry
from tic.savefile.list.shell import SavefileListHttp, SavefileListListener
from tic.savefile.process.shell import SavefileProcess
from tic.shared.event_subscriber import EventSubscriber
from tic.shared.http_module import HttpModule
from tic.shared.message_bus import MessageBus


class Container:
    """Constructs and wires all application services."""

    def __init__(self) -> None:
        """Construct all services and apply static wiring."""
        log_store: DocumentStoreInMemory[SavefileLogEntry] = DocumentStoreInMemory()
        event_store = EventStoreInMemory()
        self._bus = MessageBusInMemory()
        self._app = FastAPI(title="Terra Invicta Companion")

        modules: list[EventSubscriber | HttpModule] = [
            SavefileProcess(self._bus, event_store),
            SavefileListListener(log_store),
            SavefileListHttp(log_store),
        ]

        for module in modules:
            if isinstance(module, EventSubscriber):
                self._bus.subscribe(*module.subscriptions())
            if isinstance(module, HttpModule):
                self._app.include_router(module.router())

    @property
    def bus(self) -> MessageBus:
        """The wired message bus."""
        return self._bus

    def uvicorn_server(
        self, host: str = "127.0.0.1", port: int = 8000
    ) -> uvicorn.Server:
        """Build a uvicorn server wrapping the application."""
        return uvicorn.Server(uvicorn.Config(self._app, host=host, port=port))
