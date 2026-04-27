#!/usr/bin/env python3
"""Extract each key under the top-level `gamestates` key from a JSON file.

Usage:
  python3 scripts/extract_gamestates.py \
    --input .tic/human/Autosave.json \
    --outdir out_gamestates

By default the script writes each gamestate key's content to a separate
JSON file named with a sanitized version of the key inside `outdir`.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def sanitize_filename(name: str, max_len: int = 200) -> str:
    """Return a filesystem-safe filename derived from ``name``.

    Non-alphanumeric characters are replaced with underscores, repeated
    underscores are collapsed, and the result is truncated to ``max_len``
    characters. If the result would be empty, returns "key".
    """
    # Replace non-alphanumeric characters with underscore
    s = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    # Collapse repeated underscores
    s = re.sub(r"_+", "_", s)
    return s[:max_len].strip("_") or "key"


def _get_id(elem: object) -> str | None:
    """Try to discover an identifier for an element.

    Looks for common patterns such as ``Key.value`` or
    ``Value.ID.value`` and returns the string form if found.
    """
    if not isinstance(elem, dict):
        return None
    k = elem.get("Key")
    if isinstance(k, dict) and "value" in k:
        return str(k["value"])
    v = elem.get("Value")
    if isinstance(v, dict):
        idobj = v.get("ID") or v.get("Id")
        if isinstance(idobj, dict) and "value" in idobj:
            return str(idobj["value"])
        if "id" in v and isinstance(v["id"], (str, int)):
            return str(v["id"])
    idobj = elem.get("ID") or elem.get("Id")
    if isinstance(idobj, dict) and "value" in idobj:
        return str(idobj["value"])
    return None


def _write_json(
    obj: object,
    path: Path,
    to_stdout: bool,
    heading: str | None = None,
) -> None:
    """Write ``obj`` either to ``path`` or to stdout with an optional heading."""
    if to_stdout:
        if heading:
            print(heading)
        print(json.dumps(obj, indent=2, ensure_ascii=False))
    else:
        with path.open("w", encoding="utf-8") as outfh:
            json.dump(obj, outfh, indent=2, ensure_ascii=False)


def _handle_list_exploded(
    short: str, content: list[object], dirpath: Path, to_stdout: bool
) -> None:
    dirpath.mkdir(parents=True, exist_ok=True)
    for idx, elem in enumerate(content):
        to_write = (
            elem.get("Value") if isinstance(elem, dict) and "Value" in elem else elem
        )
        ident = _get_id(elem)
        if ident:
            filename = f"{int(ident):04d}.json"
        else:
            filename = f"{idx + 1:04d}.json"
        path = dirpath / sanitize_filename(filename)
        heading = f"=== {short} {filename} ===" if to_stdout else None
        _write_json(to_write, path, to_stdout=to_stdout, heading=heading)


def _handle_list_simple(
    short: str,
    content: list[object],
    path: Path,
    to_stdout: bool,
) -> None:
    heading = f"=== {short} (list) ===" if to_stdout else None
    _write_json(content, path, to_stdout=to_stdout, heading=heading)


def _handle_object(short: str, content: object, path: Path, to_stdout: bool) -> None:
    heading = f"=== {short} ===" if to_stdout else None
    _write_json(content, path, to_stdout=to_stdout, heading=heading)


def extract_gamestates(
    input_path: Path, outdir: Path, to_stdout: bool = False, mode: str = "simple"
) -> None:
    """Read the JSON file at ``input_path`` and extract the top-level ``gamestates``.

    Each key/value pair in ``gamestates`` is written as a separate
    JSON file into ``outdir`` using a sanitized filename. If
    ``to_stdout`` is True the contents are printed instead of
    written to disk.
    """
    with input_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    if "gamestates" not in data:
        raise KeyError("Top-level key 'gamestates' not found in JSON")

    gamestates = data["gamestates"]
    if not isinstance(gamestates, dict):
        raise TypeError("'gamestates' must be an object/dictionary")

    outdir.mkdir(parents=True, exist_ok=True)

    prefix = "PavonisInteractive.TerraInvicta."

    for key, content in gamestates.items():
        short = key[len(prefix) :] if key.startswith(prefix) else key
        safe_dir_name = sanitize_filename(short)

        if isinstance(content, list):
            if mode == "exploded":
                dirpath = outdir / safe_dir_name
                _handle_list_exploded(short, content, dirpath, to_stdout)
            else:
                filename = sanitize_filename(short) + ".json"
                path = outdir / filename
                _handle_list_simple(short, content, path, to_stdout)
        else:
            filename = sanitize_filename(short) + ".json"
            path = outdir / filename
            _handle_object(short, content, path, to_stdout)


def main(argv: list[str] | None = None) -> int:
    """Parse command-line arguments and run the extraction.

    Returns an exit code suitable for ``sys.exit``.
    """
    p = argparse.ArgumentParser(
        description="Extract gamestates from a large Autosave JSON"
    )
    p.add_argument(
        "--input",
        "-i",
        type=Path,
        default=Path(".tic/human/Autosave.json"),
        help="Path to the JSON file",
    )
    p.add_argument(
        "--outdir",
        "-o",
        type=Path,
        default=Path("out_gamestates"),
        help="Directory to write extracted files",
    )
    p.add_argument(
        "--stdout",
        action="store_true",
        help="Print each key and content to stdout instead of writing files",
    )
    p.add_argument(
        "--mode",
        choices=("exploded", "simple"),
        default="simple",
        help=(
            "Output mode: 'exploded' = one file per element in a directory;"
            " 'simple' = one JSON file per key (default)"
        ),
    )
    args = p.parse_args(argv)

    try:
        extract_gamestates(
            args.input, args.outdir, to_stdout=args.stdout, mode=args.mode
        )
    except Exception as e:
        print("Error:", e)
        return 2
    print(f"Wrote gamestates to '{args.outdir}' (mode={args.mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
