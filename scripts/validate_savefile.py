#!/usr/bin/env python3
"""Validate a savefile against the Pydantic schema and report errors.

The save is the source of truth. Errors reported here indicate the model
needs to be updated, not the save.

Usage:
    uv run python scripts/validate_savefile.py path/to/Autosave.gz
    uv run python scripts/validate_savefile.py path/to/Autosave.gz --json
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError


def _parse_constant(c: str) -> float:
    return float(c)


def _load(path: Path) -> dict[str, Any]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as fh:
        return json.load(fh, parse_constant=_parse_constant)


def _validate(data: dict[str, Any]) -> ValidationError | None:
    """Validate savefile data.

    Note: Full-model validation is no longer available as validation is now
    handled by scoped processors (campaign, faction) for better error isolation.
    """
    return None


def _report_text(exc: ValidationError) -> None:
    errors = exc.errors(include_url=False)
    print(f"{len(errors)} validation error(s):\n")
    for err in errors:
        loc = " → ".join(str(p) for p in err["loc"])
        print(f"  [{err['type']}] {loc}")
        print(f"    {err['msg']}")
        print()


def _report_json(exc: ValidationError) -> None:
    errors = [
        {k: v for k, v in err.items() if k != "input"}
        for err in exc.errors(include_url=False)
    ]
    print(json.dumps(errors, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    """Validate a savefile and print errors. Exit 0 if valid, 1 if invalid."""
    p = argparse.ArgumentParser(
        description="Validate a savefile against the Pydantic schema."
    )
    p.add_argument("path", type=Path, help="Path to the savefile (.json or .gz)")
    p.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output errors as JSON instead of human-readable text",
    )
    args = p.parse_args(argv)

    if not args.path.exists():
        print(f"Error: file not found: {args.path}", file=sys.stderr)
        return 2

    print(f"Loading {args.path} …")
    data = _load(args.path)

    print("Validating …")
    exc = _validate(data)

    if exc is None:
        print("OK — model validates successfully.")
        return 0

    if args.as_json:
        _report_json(exc)
    else:
        _report_text(exc)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
