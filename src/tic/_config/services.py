from lagom import ExplicitContainer

from tic._config.profiles import Profile
from tic.faction.update.shell import FactionUpdateSubscriber
from tic.home.shell import HomeHttp
from tic.savefile.list.document import SavefileLogEntry
from tic.savefile.list.shell import SavefileListHttp, SavefileListSubscriber
from tic.savefile.process.shell.inbound import SavefileProcessSubscriber
from tic.savefile.process.shell.outbound import (
    SavefileProcessingPublisher,
)
from tic.shared.document_store import DocumentStore
from tic.shared.event_store import EventStore
from tic.shared.message_bus import MessageBus


def register_services(container: ExplicitContainer, profile: Profile) -> None:
    c = container

    c[MessageBus] = profile.message_bus()
    c[EventStore] = profile.event_store()
    c[DocumentStore[SavefileLogEntry]] = profile.document_store_savefile_log_entry()

    c[HomeHttp] = lambda: HomeHttp()
    c[SavefileListHttp] = lambda: SavefileListHttp(
        store=c[DocumentStore[SavefileLogEntry]]
    )

    bus = c[MessageBus]
    event_store = c[EventStore]

    subs = SavefileProcessSubscriber(bus, event_store).subscriptions()
    c[MessageBus].subscribe(*subs)
    c[MessageBus].subscribe(*SavefileProcessingPublisher(bus).subscriptions())
    c[MessageBus].subscribe(*FactionUpdateSubscriber(bus, event_store).subscriptions())
    c[MessageBus].subscribe(
        *SavefileListSubscriber(c[DocumentStore[SavefileLogEntry]]).subscriptions()
    )
