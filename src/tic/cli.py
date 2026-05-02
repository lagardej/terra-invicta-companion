"""CLI entrypoint — starts uvicorn and the file watcher concurrently."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import uvicorn
from watchfiles import Change, awatch

from tic._config import Application, boot
from tic.shared.events.savefile import SavefileChangeDetected
from tic.shared.message_bus import MessageBus

_log = logging.getLogger(__name__)

_AUTOSAVE_NAMES = {"Autosave.json", "Autosave.gz"}


def main() -> None:
    """Boot the container, and run the application."""
    app = boot()

    try:
        asyncio.run(_run(app))
    except KeyboardInterrupt:
        pass


async def _run(app: Application) -> None:
    message_bus = app.resolve(MessageBus)
    web_server = app.resolve(uvicorn.Server)
    watch_dir = app.settings.watch_dir

    await asyncio.gather(
        web_server.serve(),
        _watch(watch_dir, message_bus),
    )


async def _watch(watch_dir: Path, bus: MessageBus) -> None:
    _log.info("Watching %s", watch_dir)

    for name in _AUTOSAVE_NAMES:
        path = watch_dir / name
        if path.exists():
            _log.info("Found existing savefile %s", path)
            await bus.publish(SavefileChangeDetected(path=path))

    def autosave_filter(change: object, path: str) -> bool:
        p = Path(path)
        return p.parent == watch_dir and p.name in _AUTOSAVE_NAMES

    async for changes in awatch(watch_dir, watch_filter=autosave_filter):
        for change, path in changes:
            if change is Change.deleted:
                continue
            _log.info("Detected change in %s", path)
            await bus.publish(SavefileChangeDetected(path=Path(path)))
