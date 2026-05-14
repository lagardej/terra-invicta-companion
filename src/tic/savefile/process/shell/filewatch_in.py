"""Filesystem inbound shell for publishing savefile change events."""

from __future__ import annotations

import gzip
import json
import logging
from collections.abc import Sequence
from pathlib import Path

from returns.result import Failure, Success
from watchfiles import Change, awatch

from tic.savefile._events import (
    SavefileCampaignDataExtracted,
    SavefileFactionDataExtracted,
    SavefileProcessed,
)
from tic.savefile.process.core.command import (
    ExtractedData,
    ProcessSavefile,
    SavefileState,
    handle_process_savefile,
)
from tic.savefile.process.core.extracted_data import (
    ExtractedCampaignData,
    ExtractedFactionData,
    Identity,
)
from tic.savefile.process.core.extractor.current_date_time import (
    extract_current_date_time,
)
from tic.savefile.process.core.extractor.identity import extract_identity
from tic.shared.command import CommandContext
from tic.shared.event_store import EventFilter, EventStore
from tic.shared.events.base import DomainEvent, Message
from tic.shared.log_call import log_call
from tic.shared.message_bus import MessageBus

_log = logging.getLogger(__name__)

_AUTOSAVE_NAMES = {"Autosave.json", "Autosave.gz"}


class SavefileProcessFilewatchIn:
    """Watch the filesystem and publish savefile change events."""

    def __init__(self, bus: MessageBus, event_store: EventStore) -> None:
        """Initialize the watcher with a message bus."""
        self._bus = bus
        self._event_store = event_store

    @log_call()
    async def watch(self, watch_dir: Path) -> None:
        """Publish events for existing and updated autosave files in a directory."""
        _log.info("Watching %s", watch_dir)

        for name in _AUTOSAVE_NAMES:
            path = watch_dir / name
            if path.exists():
                _log.info("Found existing savefile %s", path)
                await self._process_savefile(path)

        def _autosave_filter(change: object, path: str) -> bool:
            p = Path(path)
            return p.parent == watch_dir and p.name in _AUTOSAVE_NAMES

        async for changes in awatch(watch_dir, watch_filter=_autosave_filter):
            for change, path in changes:
                if change is Change.deleted:
                    continue
                _log.info("Detected change in %s", path)
                await self._process_savefile(Path(path))

    @log_call()
    async def _process_savefile(self, path: Path) -> None:
        """Process one savefile path and publish resulting domain events."""
        data = _load_file(path)

        identity_result = extract_identity(data)
        if isinstance(identity_result, Failure):
            reason = "; ".join(identity_result.failure().violations)
            _log.error("Identity extraction failed for %s: %s", path, reason)
            return

        current_date_time_result = extract_current_date_time(data)
        if isinstance(current_date_time_result, Failure):
            reason = "; ".join(current_date_time_result.failure().violations)
            _log.error("Current datetime extraction failed for %s: %s", path, reason)
            return

        identity = identity_result.unwrap()
        campaign_id = identity.__hash__()
        current_date_time = current_date_time_result.unwrap()
        filter = _event_filter(identity)
        query_result = await self._event_store.query(filter)

        command = ProcessSavefile(data, identity, current_date_time)
        context = _create_context(query_result.events)

        result = await handle_process_savefile(command, context)

        match result:
            case Failure(failure_value):
                _log.error("Processing failed for %s: %s", path, failure_value)
            case Success(process_result):
                expected_max_sequence = query_result.max_sequence
                event = process_result.event
                data = process_result.extracted_data

                await self._event_store.append(filter, expected_max_sequence, event)

                coordination_events = _to_coordination_events(campaign_id, data)
                await self._bus.publish(event, *coordination_events)

                _log.info(
                    "Processing succeeded for %s, %s", campaign_id, current_date_time
                )


def _load_file(path: Path) -> dict:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as fh:
        return json.load(fh, parse_constant=_parse_constant)


def _parse_constant(c: str) -> float:
    return float(c)


def _event_filter(identity: Identity) -> EventFilter:
    return EventFilter(
        event_types=(SavefileProcessed.type(),),
        payload_predicates={
            "real_world_campaign_start": identity.real_world_campaign_start,
            "scenario_id": identity.scenario_id,
        },
    )


def _create_context(events: Sequence[DomainEvent]) -> CommandContext:
    state = SavefileState(current_date_time=None)
    for event in events:
        if isinstance(event, SavefileProcessed):
            state = SavefileState(current_date_time=event.current_date_time)

    return CommandContext(state)


def _to_coordination_events(
    campaign_id: int,
    extracted: tuple[ExtractedData, ...],
) -> tuple[Message, ...]:
    """Convert raw extracted data to coordination events."""
    return tuple(_to_coordination_event(campaign_id, item) for item in extracted)


def _to_coordination_event(
    campaign_id: int,
    item: ExtractedData,
) -> Message:
    match item:
        case ExtractedCampaignData():
            return SavefileCampaignDataExtracted(campaign_id, item)
        case ExtractedFactionData():
            return SavefileFactionDataExtracted(campaign_id, item)
