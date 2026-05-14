from lagom import ExplicitContainer

from tic._config.profiles import Profile
from tic.faction.update.shell_bus_in import BusIn as FactionUpdateBusIn
from tic.home.shell_http_in import HttpIn as HomeHttpIn
from tic.savefile.list.document import SavefileLogEntry
from tic.savefile.list.shell_bus_in import SavefileListBusIn as SavefileListBusIn
from tic.savefile.list.shell_http_in import SavefileListHttpIn as SavefileListHttpIn
from tic.savefile.process.shell.bus_out import (
    SavefileProcessBusOut as SavefileProcessBusOut,
)
from tic.shared.document_store import DocumentStore
from tic.shared.event_store import EventStore
from tic.shared.message_bus import MessageBus


def register_services(container: ExplicitContainer, profile: Profile) -> None:
    c = container

    c[MessageBus] = profile.message_bus()
    c[EventStore] = profile.event_store()
    c[DocumentStore[SavefileLogEntry]] = profile.document_store_savefile_log_entry()

    c[HomeHttpIn] = lambda: HomeHttpIn()
    c[SavefileListHttpIn] = lambda: SavefileListHttpIn(
        store=c[DocumentStore[SavefileLogEntry]]
    )

    bus = c[MessageBus]
    event_store = c[EventStore]

    c[MessageBus].subscribe(*SavefileProcessBusOut(bus).subscriptions())
    c[MessageBus].subscribe(*FactionUpdateBusIn(bus, event_store).subscriptions())
    c[MessageBus].subscribe(
        *SavefileListBusIn(c[DocumentStore[SavefileLogEntry]]).subscriptions()
    )
