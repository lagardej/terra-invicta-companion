"""CLI entrypoint — starts uvicorn and the file watcher concurrently."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from uvicorn.logging import ColourizedFormatter, DefaultFormatter
from watchfiles import Change, awatch

from tic._config import Container
from tic.config import ConfigurationError, Settings
from tic.shared.events.savefile import SavefileChangeDetected
from tic.shared.message_bus import MessageBus

_log = logging.getLogger(__name__)

_AUTOSAVE_NAMES = {"Autosave.json", "Autosave.gz"}


def _configure_logging(level: int) -> None:
    log_file = Path.cwd() / "logs" / "tic.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    plain_formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    tic_stream = logging.StreamHandler()
    tic_stream.setFormatter(ColourizedFormatter("%(levelprefix)s %(name)s: %(message)s"))
    tic_stream.setLevel(logging.INFO)

    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setFormatter(plain_formatter)
    file_handler.setLevel(level)

    tic_logger = logging.getLogger("tic")
    tic_logger.setLevel(level)
    tic_logger.propagate = False
    tic_logger.handlers.clear()
    tic_logger.addHandler(tic_stream)
    tic_logger.addHandler(file_handler)

    uvicorn_configs: list[tuple[str, logging.Formatter]] = [
        ("uvicorn", DefaultFormatter("%(levelprefix)s %(message)s", use_colors=True)),
        ("uvicorn.error", DefaultFormatter("%(levelprefix)s %(message)s", use_colors=True)),
    ]

    for name, formatter in uvicorn_configs:
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        stream.setLevel(logging.INFO)

        file_h = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_h.setFormatter(plain_formatter)
        file_h.setLevel(level)

        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = False
        logger.handlers.clear()
        logger.addHandler(stream)
        logger.addHandler(file_h)

    # Silence uvicorn.access entirely
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("uvicorn.access").handlers.clear()


def main() -> None:
    """Load settings and run the application."""
    try:
        load_dotenv()
        settings = Settings.load()
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    _configure_logging(settings.log_level)

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
