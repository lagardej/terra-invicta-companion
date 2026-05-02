"""CLI entrypoint — starts uvicorn and the file watcher concurrently."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from watchfiles import awatch

from tic._config import Container
from tic.config import ConfigurationError, Settings
from tic.shared.events.savefile import SavefileChangeDetected
from tic.shared.message_bus import MessageBus

_log = logging.getLogger("uvicorn.error")

_AUTOSAVE_NAMES = {"Autosave.json", "Autosave.gz"}


def main() -> None:
    """Load settings and run the application."""
    try:
        load_dotenv()
        settings = Settings.load()
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)
    try:
        asyncio.run(_run(settings))
    except KeyboardInterrupt:
        pass


async def _run(settings: Settings) -> None:
    container = Container()
    await asyncio.gather(
        container.uvicorn_server(port=settings.port).serve(),
        _watch(settings.watch_dir, container.bus),
    )


async def _watch(watch_dir: Path, bus: MessageBus) -> None:
    _log.info("Watching %s", watch_dir)
    async for changes in awatch(watch_dir, watch_filter=_autosave_filter):
        for _, path in changes:
            await bus.publish(SavefileChangeDetected(path=Path(path)))


def _autosave_filter(change: object, path: str) -> bool:
    return Path(path).name in _AUTOSAVE_NAMES
