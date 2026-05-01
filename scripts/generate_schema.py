"""Generate or update a JSON Schema from a Terra Invicta savefile.

Usage:
    uv run scripts/generate_schema.py <savefile>

The schema is written to:
    build/schema/schema.json
"""

from __future__ import annotations

import gzip
import json
import logging
import sys
from pathlib import Path
from typing import cast

from genson import SchemaBuilder

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
_log = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).parent.parent / "build" / "schema" / "schema.json"
_VERSION_PATH = _SCHEMA_PATH.parent / "version.txt"
_VERSION_KEY = (
    "gamestates",
    "PavonisInteractive.TerraInvicta.TIGlobalValuesState",
    0,
    "Value",
    "latestSaveVersion",
)


def _parse_constant(c: str) -> float:
    return float(c)


def _normalize(obj: object) -> object:
    """Replace inf/nan floats with 0.0 so genson infers numeric types only."""
    if (
        isinstance(obj, float)
        and not obj == obj
        or isinstance(obj, float)
        and abs(obj) == float("inf")
    ):
        return 0.0
    if isinstance(obj, dict):
        return {k: _normalize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize(v) for v in obj]
    return obj


def _load(path: Path) -> dict:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as fh:
        return cast(dict, _normalize(json.load(fh, parse_constant=_parse_constant)))


def _extract_version(data: dict) -> str:
    node = data
    for key in _VERSION_KEY:
        node = node[key]
    return str(node)


def _build_schema(data: dict) -> dict:
    builder = SchemaBuilder()
    builder.add_object(data)
    return builder.to_schema()


def _write(schema: dict, version: str) -> None:
    _SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    _path = _SCHEMA_PATH.with_name("schema.json")
    _path.write_text(json.dumps(schema, separators=(",", ":")), encoding="utf-8")
    _log.info("Schema written to %s", _path)
    _VERSION_PATH.write_text(version, encoding="utf-8")
    _log.info("Version written to %s", _VERSION_PATH)


def main() -> None:
    """Entry point."""
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <savefile>", file=sys.stderr)
        sys.exit(1)

    savefile = Path(sys.argv[1])
    data = _load(savefile)
    version = _extract_version(data)
    _log.info("Savefile version: %s", version)
    _write(_build_schema(data), version)


if __name__ == "__main__":
    main()
