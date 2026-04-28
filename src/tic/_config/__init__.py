"""Configuration package for application-wide singletons."""

from .wiring import message_bus, uvicorn_server

__all__ = ["message_bus", "uvicorn_server"]
