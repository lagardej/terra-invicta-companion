"""CLI entrypoint — starts uvicorn and the file watcher concurrently."""

from __future__ import annotations

import asyncio
import logging
import sys
from functools import partial
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from watchfiles import awatch

from tic.bus import Bus
from tic.config import ConfigurationError, Settings
from tic.savefile.process.shell import on_savefile_detected
from tic.shared.events.savefile import SavefileChangeDetected

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
    bus = Bus()
    bus.subscribe("savefile.detected", partial(on_savefile_detected, bus=bus))
    server = uvicorn.Server(
        uvicorn.Config("tic.app:app", host="127.0.0.1", port=settings.port)
    )
    await asyncio.gather(
        server.serve(),
        _watch(settings.watch_dir, bus),
    )


async def _watch(watch_dir: Path, bus: Bus) -> None:
    _log.info("Watching %s", watch_dir)
    async for changes in awatch(watch_dir, watch_filter=_autosave_filter):
        for _, path in changes:
            await bus.publish(
                "savefile.detected", SavefileChangeDetected(path=Path(path))
            )


def _autosave_filter(change: object, path: str) -> bool:
    return Path(path).name in _AUTOSAVE_NAMES
