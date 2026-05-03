"""Profiles for different environments (dev/prod)."""

from collections.abc import Callable
from dataclasses import dataclass

from tic._infra.bus_in_memory import MessageBusInMemory
from tic._infra.document_store_in_memory import DocumentStoreInMemory
from tic._infra.event_store_in_memory import EventStoreInMemory
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


DevProfile = Profile(
    event_store=EventStoreInMemory,
    message_bus=MessageBusInMemory,
    document_store_savefile_log_entry=DocumentStoreInMemory,
)

PROFILES: dict[str, Profile] = {
    "dev": DevProfile,
}
