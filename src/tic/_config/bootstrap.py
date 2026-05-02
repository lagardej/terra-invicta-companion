"""Bootstrap — wires settings into logging and the application container."""

from __future__ import annotations

import sys

from dotenv import load_dotenv
from fastapi import FastAPI

from tic._config.application import Application, build_application
from tic._config.logging import configure as configure_logging
from tic._config.profiles import DevProfile
from tic._config.settings import ConfigurationError, Settings
from tic.faction.update.shell import FactionUpdateListener
from tic.home.shell import HomeHttp
from tic.savefile.list.shell import SavefileListHttp, SavefileListListener
from tic.savefile.process.shell import SavefileProcess
from tic.shared.message_bus import MessageBus
from tic.shared.profile import Profile


def boot(profile: Profile = DevProfile) -> Application:
    """Configure logging and build the wired application."""
    try:
        load_dotenv()
        settings = Settings.load()
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    configure_logging(settings.log_level, settings.app_dir)
    app = build_application(settings=settings, profile=profile)
    _register_routes(app, app.resolve(FastAPI))
    _register_subscriptions(app, app.resolve(MessageBus))
    return app


def _register_routes(a: Application, w: FastAPI) -> None:
    for http_module in [
        a.resolve(HomeHttp),
        a.resolve(SavefileListHttp),
    ]:
        w.include_router(http_module.router())


def _register_subscriptions(a: Application, b: MessageBus) -> None:
    for subscriber in [
        a.resolve(SavefileProcess),
        a.resolve(SavefileListListener),
        a.resolve(FactionUpdateListener),
    ]:
        b.subscribe(*subscriber.subscriptions())
