"""Tests for the CLI helpers."""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

from tic.bus import Bus
from tic.cli import _autosave_filter, _watch
from tic.events import SavefileChangeDetected


class TestAutosaveFilter:
    """File filter for the watcher."""

    @pytest.mark.unit
    def test_autosave_json_accepted(self) -> None:
        assert _autosave_filter(None, "/saves/Autosave.json") is True

    @pytest.mark.unit
    def test_autosave_gz_accepted(self) -> None:
        assert _autosave_filter(None, "/saves/Autosave.gz") is True

    @pytest.mark.unit
    def test_other_file_rejected(self) -> None:
        assert _autosave_filter(None, "/saves/Save01.json") is False


class TestWatch:
    """Watcher publishes SavefileDetected on the bus."""

    @pytest.mark.unit
    async def test_publishes_savefile_detected(self, tmp_path: Path) -> None:
        save = tmp_path / "Autosave.json"
        save.write_text("{}", encoding="utf-8")

        bus = Bus()
        received: list[object] = []

        async def handler(payload: object) -> None:
            received.append(payload)

        bus.subscribe("savefile.detected", handler)

        from unittest.mock import patch

        mock_changes = {(None, str(save))}
        with patch("tic.cli.awatch", return_value=_async_iter([mock_changes])):
            await _watch(tmp_path, bus)

        assert received == [SavefileChangeDetected(path=save)]


async def _async_iter(items: list[object]) -> AsyncGenerator[object]:
    for item in items:
        yield item
