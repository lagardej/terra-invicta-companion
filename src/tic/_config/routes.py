from fastapi import FastAPI
from lagom import ExplicitContainer

from tic.home.shell import HomeHttp
from tic.savefile.list.shell import SavefileListHttp


def register_routes(c: ExplicitContainer) -> None:
    c[FastAPI].include_router(c[HomeHttp].router())
    c[FastAPI].include_router(c[SavefileListHttp].router())
