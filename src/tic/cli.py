"""CLI entrypoint — starts uvicorn and the file watcher concurrently."""

from __future__ import annotations

import asyncio

import uvicorn

from framework.application import Application
from framework.event_store import EventStore
from framework.message_bus import MessageBus
from tic._config import boot
from tic.savefile.process.shell.filewatch_in import SavefileProcessFilewatchIn


def main() -> None:
    """Boot the container, and run the application."""
    app = boot()

    try:
        asyncio.run(_run(app))
    except KeyboardInterrupt:
        pass


async def _run(app: Application) -> None:
    message_bus = app.resolve(MessageBus)
    event_store = app.resolve(EventStore)
    web_server = app.resolve(uvicorn.Server)
    watch_dir = app.settings.watch_dir

    await asyncio.gather(
        web_server.serve(),
        SavefileProcessFilewatchIn(message_bus, event_store).watch(watch_dir),
    )
