from fastapi import FastAPI
from lagom import ExplicitContainer

from tic.home.shell_http_in import HttpIn as HomeHttpIn
from tic.savefile.list.shell_http_in import HttpIn as SavefileListHttpIn


def register_routes(c: ExplicitContainer) -> None:
    c[FastAPI].include_router(c[HomeHttpIn].router())
    c[FastAPI].include_router(c[SavefileListHttpIn].router())
