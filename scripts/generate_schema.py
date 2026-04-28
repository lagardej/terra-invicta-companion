"""Generate or update a JSON Schema from a Terra Invicta savefile.

Usage:
    uv run scripts/generate_schema.py <savefile>

The schema is written to:
    build/schema/schema.json

If a schema already exists, it is merged with the new one.
New fields overwrite old ones. Type conflicts are logged.
"""

from __future__ import annotations

import gzip
import json
import logging
import sys
from pathlib import Path

from genson import SchemaBuilder

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
_log = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).parent.parent / "build" / "schema" / "schema.json"
_PAVONIS_PREFIX = "PavonisInteractive.TerraInvicta."
_VERSION_KEY = (
    "gamestates",
    "TIGlobalValuesState",
    0,
    "Value",
    "latestSaveVersion",
)


def _load(path: Path) -> dict:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as fh:
        return _strip_prefix(json.load(fh))


def _strip_prefix(data: dict) -> dict:
    if "gamestates" not in data:
        return data
    stripped = {
        k.removeprefix(_PAVONIS_PREFIX): v for k, v in data["gamestates"].items()
    }
    return {**data, "gamestates": stripped}


def _extract_version(data: dict) -> str:
    node = data
    for key in _VERSION_KEY:
        node = node[key]
    return str(node)


def _build_schema(data: dict) -> dict:
    builder = SchemaBuilder()
    builder.add_object(data)
    return builder.to_schema()


def _log_conflicts(existing: dict, incoming: dict, path: str = "") -> None:
    existing_props = existing.get("properties", {})
    incoming_props = incoming.get("properties", {})
    for key in existing_props:
        if key not in incoming_props:
            continue
        e_type = existing_props[key].get("type")
        i_type = incoming_props[key].get("type")
        if e_type != i_type:
            _log.warning(
                "Type conflict at %s.%s: existing=%r new=%r — new wins",
                path,
                key,
                e_type,
                i_type,
            )
        _log_conflicts(
            existing_props[key],
            incoming_props[key],
            path=f"{path}.{key}" if path else key,
        )


def _merge(existing: dict, incoming: dict) -> dict:
    _log_conflicts(existing, incoming)
    merged = {**existing, **incoming}
    if "properties" in existing and "properties" in incoming:
        merged_props = {**existing["properties"]}
        for key, value in incoming["properties"].items():
            if key in merged_props and isinstance(merged_props[key], dict):
                merged_props[key] = _merge(merged_props[key], value)
            else:
                merged_props[key] = value
        merged["properties"] = merged_props
    required = sorted(
        set(existing.get("required", [])) | set(incoming.get("required", []))
    )
    if required:
        merged["required"] = required
    return merged


_VERSION_PATH = _SCHEMA_PATH.parent / "version.txt"


def _write(schema: dict, version: str) -> None:
    _SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SCHEMA_PATH.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    _log.info("Schema written to %s", _SCHEMA_PATH)
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

    incoming = _build_schema(data)

    if _SCHEMA_PATH.exists():
        _log.info("Existing schema found — merging")
        existing = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        schema = _merge(existing, incoming)
    else:
        schema = incoming

    _write(schema, version)


if __name__ == "__main__":
    main()
