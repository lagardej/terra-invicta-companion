from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path


def _load_map_event_flow() -> object:
    script_path = Path("scripts/map_event_flow.py")
    spec = importlib.util.spec_from_file_location("map_event_flow_script", script_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _publishes_block(report: str, event_name: str, event_kind: str) -> str:
    group_header = re.escape(f"## {event_kind} Events")
    event_header = re.escape(f"### {event_name}")
    pattern = (
        rf"{group_header}\n"
        rf"\n"
        rf"(?:.*\n)*?"
        rf"{event_header}\n"
        rf"Publishes:\n"
        rf"(?P<block>(?:  - .*\n)+)\n"
        rf"Listens:\n"
    )
    match = re.search(pattern, report)
    assert match is not None
    return match.group("block")


def _event_in_group(report: str, event_name: str, event_kind: str) -> bool:
    group_header = re.escape(f"## {event_kind} Events")
    event_header = re.escape(f"### {event_name}")
    pattern = rf"{group_header}\n\n(?:.*\n)*?{event_header}\n"
    return re.search(pattern, report) is not None


def test_displays_event_types_in_headers(tmp_path: Path) -> None:
    module = _load_map_event_flow()
    out_path = tmp_path / "event_flow_map.md"

    module.map_event_flow(src_root=Path("src"), out_path=out_path)
    report = out_path.read_text(encoding="utf-8")

    assert "Domain Events" in report
    assert "Integration Events" in report
    assert "Mixed Events" not in report
    assert "CampaignDataExtracted" in report
    assert _event_in_group(report, "SavefileProcessingSucceeded", "Domain")
    assert _event_in_group(report, "SavefileProcessingSucceeded", "Integration")


def test_captures_savefile_process_publishers_for_extracted_events(
    tmp_path: Path,
) -> None:
    module = _load_map_event_flow()
    out_path = tmp_path / "event_flow_map.md"

    module.map_event_flow(src_root=Path("src"), out_path=out_path)
    report = out_path.read_text(encoding="utf-8")

    campaign_publishes = _publishes_block(
        report,
        "CampaignDataExtracted",
        "Integration",
    )
    faction_publishes = _publishes_block(
        report,
        "FactionDataExtracted",
        "Integration",
    )

    expected_publish = (
        "[src/tic/savefile/process/shell.py:86]"
        "(../src/tic/savefile/process/shell.py#L86)"
    )
    assert expected_publish in campaign_publishes
    assert expected_publish in faction_publishes
