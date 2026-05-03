from lagom import ExplicitContainer

from tic._config.profiles import Profile
from tic.faction.update.core import UpdateFactionHandler
from tic.faction.update.shell import FactionUpdateListener
from tic.home.shell import HomeHttp
from tic.savefile.list.document import SavefileLogEntry
from tic.savefile.list.shell import SavefileListHttp, SavefileListListener
from tic.savefile.process.core import ProcessSavefileHandler
from tic.savefile.process.shell import SavefileProcess
from tic.shared.document_store import DocumentStore
from tic.shared.event_store import EventStore
from tic.shared.message_bus import MessageBus


def register_services(container: ExplicitContainer, profile: Profile) -> None:
    c = container

    c[MessageBus] = profile.message_bus()
    c[EventStore] = profile.event_store()
    c[DocumentStore[SavefileLogEntry]] = profile.document_store_savefile_log_entry()

    c[ProcessSavefileHandler] = lambda: ProcessSavefileHandler()
    c[UpdateFactionHandler] = lambda: UpdateFactionHandler()

    c[HomeHttp] = lambda: HomeHttp()
    c[SavefileListHttp] = lambda: SavefileListHttp(
        store=c[DocumentStore[SavefileLogEntry]]
    )

    c[SavefileProcess] = lambda: SavefileProcess(
        bus=c[MessageBus],
        event_store=c[EventStore],
        handler=c[ProcessSavefileHandler],
    )
    c[FactionUpdateListener] = lambda: FactionUpdateListener(
        bus=c[MessageBus],
        event_store=c[EventStore],
        handler=c[UpdateFactionHandler],
    )
    c[SavefileListListener] = lambda: SavefileListListener(
        store=c[DocumentStore[SavefileLogEntry]]
    )

    c[MessageBus].subscribe(*c[SavefileProcess].subscriptions())
    c[MessageBus].subscribe(*c[FactionUpdateListener].subscriptions())
    c[MessageBus].subscribe(*c[SavefileListListener].subscriptions())
