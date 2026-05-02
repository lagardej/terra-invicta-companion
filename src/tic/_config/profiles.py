"""Profiles for different environments (dev/test/prod)."""

from tic._infra.bus_in_memory import MessageBusInMemory
from tic._infra.document_store_in_memory import DocumentStoreInMemory
from tic._infra.event_store_in_memory import EventStoreInMemory
from tic.shared.profile import Profile

DevProfile = Profile(
    event_store=EventStoreInMemory,
    message_bus=MessageBusInMemory,
    document_store_savefile_log_entry=DocumentStoreInMemory,
)
