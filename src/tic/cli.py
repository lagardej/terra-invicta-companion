"""CLI entrypoint — starts uvicorn and the file watcher concurrently."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from watchfiles import Change, awatch

from tic._config import build_server, configure_logging
from tic.config import ConfigurationError, Settings
from tic.shared.events.savefile import SavefileChangeDetected
from tic.shared.message_bus import MessageBus

_log = logging.getLogger(__name__)

_AUTOSAVE_NAMES = {"Autosave.json", "Autosave.gz"}


def main() -> None:
    """Load settings and run the application."""
    try:
        load_dotenv()
        settings = Settings.load()
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    configure_logging(settings.log_level)

    try:
        asyncio.run(_run(settings))
    except KeyboardInterrupt:
        pass


async def _run(settings: Settings) -> None:
    server, bus = build_server(port=settings.port)
    await asyncio.gather(
        server.serve(),
        _watch(settings.watch_dir, bus),
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
