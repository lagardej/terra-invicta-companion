"""Bootstrap — wires settings into logging and the application container."""

from __future__ import annotations

import sys

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from lagom import ExplicitContainer

from tic._config.logging import configure as configure_logging
from tic._config.profiles import PROFILES, DevProfile
from tic._config.services import register_services
from tic._config.settings import ConfigurationError, TicSettings
from tic.shared.application import Application


def boot() -> Application[TicSettings]:
    """Configure logging and build the wired application."""
    try:
        load_dotenv()
        settings = TicSettings.load()
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    configure_logging(settings.log_level, settings.app_dir)

    profile = PROFILES.get(settings.env, DevProfile)

    c = ExplicitContainer()
    c[FastAPI] = FastAPI(title="Terra Invicta Companion")
    c[uvicorn.Server] = uvicorn.Server(
        uvicorn.Config(c[FastAPI], port=settings.port, log_config=None)
    )

    register_services(container=c, profile=profile)

    return Application(container=c, settings=settings)
