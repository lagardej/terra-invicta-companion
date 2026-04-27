"""Tests for the CLI helpers."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tic.bus import Bus
from tic.cli import _autosave_filter, _watch
from tic.savefile.process.shell import on_savefile_detected
from tic.shared.events.base import Message
from tic.shared.events.campaign import CampaignParsed
from tic.shared.events.savefile import (
    SavefileChangeDetected,
    SavefileProcessingFailed,
    SaveFileProcessingSucceeded,
)

_PLAYER_STATE_KEY = "PavonisInteractive.TerraInvicta.TIPlayerState"
_GLOBAL_VALUES_KEY = "PavonisInteractive.TerraInvicta.TIGlobalValuesState"


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
    """Watcher publishes SavefileChangeDetected on the bus."""

    @pytest.mark.unit
    async def test_publishes_savefile_detected(self, tmp_path: Path) -> None:
        save = tmp_path / "Autosave.json"
        save.write_text("{}", encoding="utf-8")

        bus = Bus()
        received: list[object] = []

        async def handler(payload: Message) -> None:
            received.append(payload)

        bus.subscribe(SavefileChangeDetected, handler)

        from unittest.mock import patch

        mock_changes = {(None, str(save))}
        with patch("tic.cli.awatch", return_value=_async_iter([mock_changes])):
            await _watch(tmp_path, bus)

        assert received == [SavefileChangeDetected(path=save)]


class TestOnSavefileDetected:
    """Subscriber reads file, parses it, publishes result on the bus."""

    @pytest.mark.unit
    async def test_publishes_campaign_parsed_and_processing_succeeded(
        self, tmp_path: Path
    ) -> None:
        save = tmp_path / "Autosave.json"
        save.write_text(
            json.dumps(
                {
                    "gamestates": {
                        _GLOBAL_VALUES_KEY: [
                            {
                                "Key": {"value": 1},
                                "Value": {
                                    "difficulty": 2,
                                    "campaignStartVersion": "1.0.32",
                                    "latestSaveVersion": "1.0.33",
                                    "realWorldCampaignStart": {
                                        "year": 2026,
                                        "month": 4,
                                        "day": 7,
                                        "hour": 11,
                                        "minute": 4,
                                        "second": 18,
                                    },
                                    "scenarioCustomizations": {},
                                },
                            }
                        ],
                        _PLAYER_STATE_KEY: [
                            {
                                "Key": {"value": 10},
                                "Value": {
                                    "isAI": False,
                                    "faction": {"value": 100},
                                    "name": "ResistPlayer",
                                },
                            },
                            {
                                "Key": {"value": 11},
                                "Value": {
                                    "isAI": True,
                                    "faction": {"value": 101},
                                    "name": "DestroyPlayer",
                                },
                            },
                        ],
                    }
                }
            ),
            encoding="utf-8",
        )
        bus = Bus()
        received: list[object] = []

        async def handler(payload: Message) -> None:
            received.append(payload)

        bus.subscribe(CampaignParsed, handler)
        bus.subscribe(SaveFileProcessingSucceeded, handler)
        await on_savefile_detected(SavefileChangeDetected(path=save), bus=bus)

        assert any(isinstance(e, CampaignParsed) for e in received)
        succeeded = next(
            e for e in received if isinstance(e, SaveFileProcessingSucceeded)
        )
        assert succeeded.path == save
        assert succeeded.campaign_start == datetime(2026, 4, 7, 11, 4, 18, tzinfo=UTC)
        assert succeeded.player_faction_key == "ResistPlayer"
        assert succeeded.player_count == 2
        assert isinstance(succeeded.duration_ms, float)
        assert succeeded.duration_ms >= 0.0

    @pytest.mark.unit
    async def test_publishes_import_failed_on_missing_file(
        self, tmp_path: Path
    ) -> None:
        save = tmp_path / "Autosave.json"
        bus = Bus()
        received: list[object] = []

        async def handler(payload: Message) -> None:
            received.append(payload)

        bus.subscribe(SavefileProcessingFailed, handler)
        await on_savefile_detected(SavefileChangeDetected(path=save), bus=bus)

        assert len(received) == 1
        assert isinstance(received[0], SavefileProcessingFailed)
        assert received[0].path == save  # type: ignore[union-attr]

    @pytest.mark.unit
    async def test_publishes_import_failed_on_invalid_json(
        self, tmp_path: Path
    ) -> None:
        save = tmp_path / "Autosave.json"
        save.write_text("not json", encoding="utf-8")
        bus = Bus()
        received: list[object] = []

        async def handler(payload: Message) -> None:
            received.append(payload)

        bus.subscribe(SavefileProcessingFailed, handler)
        await on_savefile_detected(SavefileChangeDetected(path=save), bus=bus)

        assert len(received) == 1
        assert isinstance(received[0], SavefileProcessingFailed)


async def _async_iter(items: list[object]) -> AsyncGenerator[object]:
    for item in items:
        yield item
