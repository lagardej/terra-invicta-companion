"""Savefile import subscriber — imperative shell."""

from __future__ import annotations

import json

from tic.bus import Bus
from tic.savefile.process.core import ProcessSavefile, handle
from tic.shared.events.base import Message
from tic.shared.events.savefile import (
    SavefileChangeDetected,
    SavefileProcessingFailed,
)

_TOPIC = "savefile.imported"


async def on_savefile_detected(event: Message, *, bus: Bus) -> None:
    """Read, parse and publish the result of a savefile import."""
    assert isinstance(event, SavefileChangeDetected)
    try:
        data = json.loads(event.path.read_text(encoding="utf-8"))
        command = ProcessSavefile(path=event.path, data=data)
        for e in handle(command):
            await bus.publish(e)
    except Exception as exc:
        await bus.publish(
            SavefileProcessingFailed(path=event.path, reason=str(exc)),
        )
