"""Savefile import subscriber — imperative shell."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from tic.shared.events.base import Message
from tic.shared.events.savefile import (
    SavefileChangeDetected,
)
from tic.shared.message_bus import MessageBus


def subscriptions() -> tuple[
    tuple[type[Message], Callable[..., Coroutine[Any, Any, None]]], ...
]:
    """Return subscription entries for this module."""
    return ((SavefileChangeDetected, on_savefile_detected),)


async def on_savefile_detected(
    event: SavefileChangeDetected, *, bus: MessageBus
) -> None:
    """Read, parse and publish the result of a savefile import."""
    raise NotImplementedError("on_savefile_detected() is not implemented yet")
