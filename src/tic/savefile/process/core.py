"""Savefile command handler — functional core, no I/O."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from tic.shared.events.base import Message

_EPOCH = datetime.min.replace(tzinfo=UTC)


@dataclass(frozen=True)
class ProcessSavefile:
    """Command: process a savefile and emit domain events."""

    path: Path
    data: dict


def handle(command: ProcessSavefile) -> Iterator[Message]:
    """Handle a ProcessSavefile command."""
    # Minimal generator stub so the function satisfies the declared
    # return type. The full implementation yields domain events.
    yield from ()
