"""Filesystem inbound shell for publishing savefile change events."""

from __future__ import annotations

import logging
from pathlib import Path

from watchfiles import Change, awatch

from tic.shared.events.savefile import SavefileChangeDetected
from tic.shared.log_call import log_call
from tic.shared.message_bus import MessageBus

_log = logging.getLogger(__name__)

_AUTOSAVE_NAMES = {"Autosave.json", "Autosave.gz"}


class FilesystemIn:
    """Watch the filesystem and publish savefile change events."""

    def __init__(self, bus: MessageBus) -> None:
        """Initialize the watcher with a message bus."""
        self._bus = bus

    @log_call()
    async def watch(self, watch_dir: Path) -> None:
        """Publish events for existing and updated autosave files in a directory."""
        _log.info("Watching %s", watch_dir)

        for name in _AUTOSAVE_NAMES:
            path = watch_dir / name
            if path.exists():
                _log.info("Found existing savefile %s", path)
                await self._bus.publish(SavefileChangeDetected(path=path))

        def _autosave_filter(change: object, path: str) -> bool:
            p = Path(path)
            return p.parent == watch_dir and p.name in _AUTOSAVE_NAMES

        async for changes in awatch(watch_dir, watch_filter=_autosave_filter):
            for change, path in changes:
                if change is Change.deleted:
                    continue
                _log.info("Detected change in %s", path)
                await self._bus.publish(SavefileChangeDetected(path=Path(path)))
