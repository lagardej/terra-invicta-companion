"""Logging configuration."""

from __future__ import annotations

import logging
from pathlib import Path

from uvicorn.logging import ColourizedFormatter, DefaultFormatter


def configure(level: str, app_dir: Path) -> None:
    """Configure logging for the application.

    - tic.*: colourized console (INFO+), file (level)
    - uvicorn/uvicorn.error: restored uvicorn formatters, file (level)
    - uvicorn.access: silenced entirely
    """
    log_file = app_dir / "tic.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    plain_formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")

    def _file_handler() -> logging.FileHandler:
        h = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        h.setFormatter(plain_formatter)
        h.setLevel(level)
        return h

    # tic.*
    tic_stream = logging.StreamHandler()
    tic_stream.setFormatter(ColourizedFormatter("%(levelprefix)s %(message)s"))
    tic_stream.setLevel(logging.INFO)

    tic_logger = logging.getLogger("tic")
    tic_logger.setLevel(level)
    tic_logger.propagate = False
    tic_logger.handlers.clear()
    tic_logger.addHandler(tic_stream)
    tic_logger.addHandler(_file_handler())

    # uvicorn.*
    uvicorn_configs: list[tuple[str, logging.Formatter]] = [
        ("uvicorn", DefaultFormatter("%(levelprefix)s %(message)s", use_colors=True)),
        (
            "uvicorn.error",
            DefaultFormatter("%(levelprefix)s %(message)s", use_colors=True),
        ),
    ]
    for name, formatter in uvicorn_configs:
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        stream.setLevel(logging.INFO)

        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = False
        logger.handlers.clear()
        logger.addHandler(stream)
        logger.addHandler(_file_handler())

    # silence access log
    access = logging.getLogger("uvicorn.access")
    access.propagate = False
    access.handlers.clear()
