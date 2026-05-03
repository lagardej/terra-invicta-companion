"""Configuration loading from environment / .env file."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from tic.shared.application import Settings as BaseSettings


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings(BaseSettings):
    """Application settings."""

    app_dir: Path
    log_level: int
    port: int
    watch_dir: Path

    @classmethod
    def load(cls) -> Settings:
        """Load settings from environment."""
        return cls(
            app_dir=_load_app_dir(),
            log_level=_load_log_level(),
            port=_load_port(),
            watch_dir=_load_watch_dir(),
        )


def _load_app_dir() -> Path:
    raw = os.getenv("TIC_APP_DIR")
    if not raw:
        raise ConfigurationError("TIC_APP_DIR is required but not set.")
    path = Path(raw).expanduser()
    if not path.is_dir():
        raise ConfigurationError(f"TIC_APP_DIR={raw!r} is not a valid directory.")
    return path


def _load_log_level() -> int:
    raw = os.getenv("TIC_LOG_LEVEL", "INFO").upper()
    level = logging.getLevelName(raw)
    if not isinstance(level, int):
        raise ConfigurationError(
            f"TIC_LOG_LEVEL={raw!r} is not a valid log level. "
            "Use DEBUG, INFO, WARNING, ERROR, or CRITICAL."
        )
    return level


def _load_port() -> int:
    return int(os.getenv("TIC_PORT", "8000"))


def _load_watch_dir() -> Path:
    raw = os.getenv("TIC_WATCH_DIR")
    if not raw:
        raise ConfigurationError("TIC_WATCH_DIR is required but not set.")
    path = Path(raw).expanduser()
    if not path.is_dir():
        raise ConfigurationError(f"TIC_WATCH_DIR={raw!r} is not a valid directory.")
    return path
