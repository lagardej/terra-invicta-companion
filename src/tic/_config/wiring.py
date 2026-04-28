"""FastAPI application instance."""

from __future__ import annotations

from functools import partial

import uvicorn
from fastapi import FastAPI

from tic._infra.bus_in_memory import MessageBusInMemory
from tic.savefile.process.shell import subscriptions as savefile_subscriptions
from tic.shared.message_bus import MessageBus


def message_bus() -> MessageBus:
    bus = MessageBusInMemory()

    for event_type, handler in savefile_subscriptions():
        bus.subscribe(event_type, partial(handler, bus=bus))

    return bus


def uvicorn_server(host: str = "127.0.0.1", port: int = 8000) -> uvicorn.Server:
    return uvicorn.Server(uvicorn.Config(_web_app(), host=host, port=port))


def _web_app() -> FastAPI:
    return FastAPI(title="Terra Invicta Companion")
