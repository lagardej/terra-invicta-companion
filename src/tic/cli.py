"""CLI entrypoint — starts uvicorn and the file watcher concurrently."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

from tic.config import ConfigurationError, Settings

_log = logging.getLogger("uvicorn.error")


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
    server = uvicorn.Server(
        uvicorn.Config("tic.app:app", host="127.0.0.1", port=settings.port)
    )
    await asyncio.gather(
        server.serve(),
        _watch(settings),
    )


async def _watch(settings: Settings) -> None:
    from watchfiles import awatch

    _log.info("Watching %s", settings.watch_dir)
    async for _ in awatch(settings.watch_dir, watch_filter=_autosave_filter):
        pass  # watcher events will be wired to the bus in a later step


def _autosave_filter(change: object, path: str) -> bool:
    return Path(path).name in {"Autosave.json", "Autosave.gz"}
