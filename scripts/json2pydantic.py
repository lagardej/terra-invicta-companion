"""Generate Pydantic models from the JSON Schema.

Usage:
    uv run scripts/json2pydantic.py

Reads:
    build/schema/schema.json

Writes:
    src/tic/savefile/process/schema/models.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from datamodel_code_generator import InputFileType, generate
from datamodel_code_generator.enums import DataModelType
from datamodel_code_generator.format import Formatter

_PROJECT_ROOT = Path(__file__).parent.parent
_SCHEMA_PATH = _PROJECT_ROOT / "build" / "schema" / "schema.json"
_MODELS_PATH = (
    _PROJECT_ROOT / "src" / "tic" / "savefile" / "process" / "schema" / "models.py"
)
_VERSION_PATH = _PROJECT_ROOT / "build" / "schema" / "version.txt"
_GENERATED_HEADER = (
    '"""Generated Pydantic models \u2014 do not edit."""\n'
    "# generated \u2014 do not edit\n"
    "# ruff: noqa: D101, E501\n"
)


def _generate() -> None:
    if not _SCHEMA_PATH.exists():
        print(f"Error: schema not found at {_SCHEMA_PATH}", file=sys.stderr)
        sys.exit(1)

    _MODELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _ensure_init(_MODELS_PATH.parent)

    generate(
        _SCHEMA_PATH,
        input_file_type=InputFileType.JsonSchema,
        output=_MODELS_PATH,
        output_model_type=DataModelType.PydanticV2BaseModel,
        formatters=[Formatter.RUFF_FORMAT],
        use_schema_description=True,
        field_constraints=True,
        snake_case_field=True,
        settings_path=_PROJECT_ROOT,
    )
    _prepend_header(_MODELS_PATH)
    _reformat_no_wrap(_MODELS_PATH)
    print(f"Models written to {_MODELS_PATH}")


def _ensure_init(directory: Path) -> None:
    init = directory / "__init__.py"
    if not init.exists():
        init.write_text('"""Savefile schema models."""\n', encoding="utf-8")


def _prepend_header(path: Path) -> None:
    version = (
        _VERSION_PATH.read_text(encoding="utf-8").strip()
        if _VERSION_PATH.exists()
        else "unknown"
    )
    header = _GENERATED_HEADER + f"# game version: {version}\n"
    content = path.read_text(encoding="utf-8")
    path.write_text(header + content, encoding="utf-8")


def _reformat_no_wrap(path: Path) -> None:
    result = subprocess.run(
        [
            "uv",
            "run",
            "ruff",
            "format",
            "--isolated",
            "--line-length",
            "320",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)


def main() -> None:
    """Entry point."""
    if len(sys.argv) != 1:
        print(f"Usage: {sys.argv[0]}", file=sys.stderr)
        sys.exit(1)
    _generate()


if __name__ == "__main__":
    main()
