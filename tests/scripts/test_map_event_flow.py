"""Regression tests for scripts/map_event_flow.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _load_map_event_flow() -> object:
    module_path = Path(__file__).parents[2] / "scripts" / "map_event_flow.py"
    spec = importlib.util.spec_from_file_location("map_event_flow", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.map_event_flow


def test_maps_events_from_underscore_events_and_subscription_factories(
    tmp_path: Path,
) -> None:
    map_event_flow = _load_map_event_flow()

    src_root = tmp_path / "src"
    pkg = src_root / "pkg"
    pkg.mkdir(parents=True)

    (pkg / "_events.py").write_text(
        """
from dataclasses import dataclass

from tic.shared.events.base import DomainEvent


@dataclass(frozen=True)
class FooEvt(DomainEvent):
    @classmethod
    def type(cls) -> str:
        return "foo.evt"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    (pkg / "publisher.py").write_text(
        """
from pkg._events import FooEvt


async def emit(bus) -> None:
    await bus.publish(FooEvt())
""".strip()
        + "\n",
        encoding="utf-8",
    )

    (pkg / "wiring.py").write_text(
        """
from pkg._events import FooEvt
from tic.shared.events.base import Message
from tic.shared.message_bus import Subscription


def make_subscriptions() -> tuple[Subscription, ...]:
    async def handle(event: Message) -> None:
        return None

    return ((FooEvt, handle),)
""".strip()
        + "\n",
        encoding="utf-8",
    )

    out_path = tmp_path / "build" / "event_flow_map.md"
    map_event_flow(src_root=src_root, out_path=out_path)

    report = out_path.read_text(encoding="utf-8")

    assert "**FooEvt**" in report
    assert "src/pkg/publisher.py" in report
    assert "src/pkg/wiring.py" in report


def test_maps_publish_calls_using_imported_event_factories(tmp_path: Path) -> None:
    map_event_flow = _load_map_event_flow()

    src_root = tmp_path / "src"
    pkg = src_root / "pkg"
    pkg.mkdir(parents=True)

    (pkg / "events.py").write_text(
        """
from dataclasses import dataclass

from tic.shared.events.base import IntegrationEvent


@dataclass(frozen=True)
class BarEvt(IntegrationEvent):
    value: int
""".strip()
        + "\n",
        encoding="utf-8",
    )

    (pkg / "factory.py").write_text(
        """
from pkg.events import BarEvt


def to_bar() -> BarEvt:
    return BarEvt(value=1)
""".strip()
        + "\n",
        encoding="utf-8",
    )

    (pkg / "publisher.py").write_text(
        """
from pkg.factory import to_bar


async def emit(bus) -> None:
    await bus.publish(to_bar())
""".strip()
        + "\n",
        encoding="utf-8",
    )

    out_path = tmp_path / "build" / "event_flow_map.md"
    map_event_flow(src_root=src_root, out_path=out_path)

    report = out_path.read_text(encoding="utf-8")

    assert "**BarEvt**" in report
    assert "src/pkg/publisher.py" in report


def test_reports_chain_from_savefile_change_detected(tmp_path: Path) -> None:
    map_event_flow = _load_map_event_flow()

    src_root = tmp_path / "src"
    pkg = src_root / "pkg"
    pkg.mkdir(parents=True)

    (pkg / "events.py").write_text(
        """
from dataclasses import dataclass

from tic.shared.events.base import IntegrationEvent


@dataclass(frozen=True)
class SavefileChangeDetected(IntegrationEvent):
    path: str


@dataclass(frozen=True)
class NextEvt(IntegrationEvent):
    value: int
""".strip()
        + "\n",
        encoding="utf-8",
    )

    (pkg / "shell.py").write_text(
        """
from pkg.events import NextEvt, SavefileChangeDetected
from tic.shared.events.base import Message
from tic.shared.message_bus import Subscription


def savefile_process_subscriptions(bus) -> tuple[Subscription, ...]:
    async def _dispatch(event: Message) -> None:
        await _on_detected(event)

    async def _on_detected(event: Message) -> None:
        if isinstance(event, SavefileChangeDetected):
            await bus.publish(NextEvt(value=1))

    return ((SavefileChangeDetected, _dispatch),)
""".strip()
        + "\n",
        encoding="utf-8",
    )

    out_path = tmp_path / "build" / "event_flow_map.md"
    map_event_flow(src_root=src_root, out_path=out_path)

    report = out_path.read_text(encoding="utf-8")

    assert "## Event Chains" in report
    assert "### From SavefileChangeDetected" in report
    assert "SavefileChangeDetected -> _dispatch" in report
    assert "-> NextEvt @" in report


def test_chain_is_match_case_path_sensitive(tmp_path: Path) -> None:
    map_event_flow = _load_map_event_flow()

    src_root = tmp_path / "src"
    pkg = src_root / "pkg"
    pkg.mkdir(parents=True)

    (pkg / "events.py").write_text(
        """
from dataclasses import dataclass

from tic.shared.events.base import IntegrationEvent


@dataclass(frozen=True)
class SavefileChangeDetected(IntegrationEvent):
    path: str


@dataclass(frozen=True)
class StageA(IntegrationEvent):
    value: int


@dataclass(frozen=True)
class StageB(IntegrationEvent):
    value: int


@dataclass(frozen=True)
class FinalA(IntegrationEvent):
    value: int


@dataclass(frozen=True)
class FinalB(IntegrationEvent):
    value: int
""".strip()
        + "\n",
        encoding="utf-8",
    )

    (pkg / "pipeline.py").write_text(
        """
from pkg.events import FinalA, FinalB, SavefileChangeDetected, StageA, StageB
from tic.shared.events.base import Message
from tic.shared.message_bus import Subscription


def subscriptions(bus) -> tuple[Subscription, ...]:
    async def _on_start(event: Message) -> None:
        if isinstance(event, SavefileChangeDetected):
            await bus.publish(StageA(value=1), StageB(value=2))

    async def _dispatch(event: Message) -> None:
        match event:
            case StageA() as e:
                await _on_stage_a(e)
            case StageB() as e:
                await _on_stage_b(e)

    async def _on_stage_a(event: Message) -> None:
        if isinstance(event, StageA):
            await bus.publish(FinalA(value=event.value))

    async def _on_stage_b(event: Message) -> None:
        if isinstance(event, StageB):
            await bus.publish(FinalB(value=event.value))

    return (
        (SavefileChangeDetected, _on_start),
        (StageA, _dispatch),
        (StageB, _dispatch),
    )
""".strip()
        + "\n",
        encoding="utf-8",
    )

    out_path = tmp_path / "build" / "event_flow_map.md"
    map_event_flow(src_root=src_root, out_path=out_path)

    report = out_path.read_text(encoding="utf-8")

    assert "-> StageA @" in report
    assert "-> FinalA @" in report
    assert "-> StageB @" in report
    assert "-> FinalB @" in report

    for line in report.splitlines():
        if "-> StageA @" in line:
            assert "-> FinalB @" not in line
        if "-> StageB @" in line:
            assert "-> FinalA @" not in line
