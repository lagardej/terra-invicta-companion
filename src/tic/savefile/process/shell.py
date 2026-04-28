"""Savefile import subscriber — imperative shell."""

from __future__ import annotations

import json
from collections.abc import Callable, Coroutine
from typing import Any

from tic.savefile.process.core import ProcessSavefile, handle
from tic.shared.events.base import Message
from tic.shared.events.savefile import (
    SavefileChangeDetected,
    SavefileProcessingFailed,
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
    try:
        data = json.loads(event.path.read_text(encoding="utf-8"))
        command = ProcessSavefile(path=event.path, data=data)
        for e in handle(command):
            await bus.publish(e)
    except Exception as exc:
        await bus.publish(
            SavefileProcessingFailed(path=event.path, reason=str(exc)),
        )
