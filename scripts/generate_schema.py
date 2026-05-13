"""Generate or update a JSON Schema from a Terra Invicta savefile.

Usage:
    uv run scripts/generate_schema.py <savefile>

The schema is written to:
    build/schema/schema.json

Requires quicktype on PATH or accessible via npx.
"""

from __future__ import annotations

import gzip
import json
import logging
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import cast

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
    """Replace inf/nan floats with 0.0 so numeric types are inferred correctly."""
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


def _quicktype_cmd() -> str:
    """Return the quicktype executable, preferring the installed binary over npx."""
    if shutil.which("quicktype"):
        return "quicktype"
    return "npx quicktype"


def _build_schema(data: dict) -> dict:
    """Invoke quicktype to infer a JSON Schema with $ref/$definitions from data."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tmp:
        json.dump(data, tmp)
        tmp_path = Path(tmp.name)

    try:
        cmd = _quicktype_cmd().split() + [
            "--src", str(tmp_path),
            "--src-lang", "json",
            "--lang", "schema",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            _log.error("quicktype failed:\n%s", result.stderr)
            sys.exit(1)
        return json.loads(result.stdout)
    finally:
        tmp_path.unlink(missing_ok=True)


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
