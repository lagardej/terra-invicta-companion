"""Infrastructure profile — factories for pluggable infrastructure."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from tic.savefile.list.document import SavefileLogEntry
from tic.shared.document_store import DocumentStore
from tic.shared.event_store import EventStore
from tic.shared.message_bus import MessageBus


@dataclass(frozen=True)
class Profile:
    """Factories that supply infrastructure implementations to the container."""

    event_store: Callable[[], EventStore]
    message_bus: Callable[[], MessageBus]
    document_store_savefile_log_entry: Callable[[], DocumentStore[SavefileLogEntry]]
