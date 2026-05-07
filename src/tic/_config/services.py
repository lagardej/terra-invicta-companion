from lagom import ExplicitContainer

from tic._config.profiles import Profile
from tic.faction.update.shell import faction_update_subscriptions
from tic.home.shell import HomeHttp
from tic.savefile.list.document import SavefileLogEntry
from tic.savefile.list.shell import SavefileListHttp, savefile_list_subscriptions
from tic.savefile.process.shell.inbound import savefile_process_subscriptions
from tic.savefile.process.shell.outbound import (
    savefile_processing_publisher_subscriptions,
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

    subs = savefile_process_subscriptions(bus, event_store)
    c[MessageBus].subscribe(*subs)
    c[MessageBus].subscribe(*savefile_processing_publisher_subscriptions(bus))
    c[MessageBus].subscribe(*faction_update_subscriptions(bus, event_store))
    c[MessageBus].subscribe(
        *savefile_list_subscriptions(c[DocumentStore[SavefileLogEntry]])
    )
