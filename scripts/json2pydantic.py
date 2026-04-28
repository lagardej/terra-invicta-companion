"""Generate Pydantic models from a versioned JSON Schema.

Usage:
    uv run scripts/json2pydantic.py <version_slug>

Example:
    uv run scripts/json2pydantic.py v1_0_32

Reads:
    src/tic/savefile/process/schema/<version_slug>/schema.json

Writes:
    src/tic/savefile/process/schema/<version_slug>/models.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from datamodel_code_generator import InputFileType, generate
from datamodel_code_generator.enums import DataModelType
from datamodel_code_generator.format import Formatter

_PROJECT_ROOT = Path(__file__).parent.parent
_SCHEMA_ROOT = _PROJECT_ROOT / "build" / "schema"
_MODELS_ROOT = _PROJECT_ROOT / "src" / "tic" / "savefile" / "process" / "schema"
_GENERATED_HEADER = (
    '"""Generated Pydantic models \u2014 do not edit."""\n'
    "# generated \u2014 do not edit\n"
    "# ruff: noqa: D101, E501\n"
)


def _schema_path(slug: str) -> Path:
    return _SCHEMA_ROOT / slug / "schema.json"


def _output_path(slug: str) -> Path:
    return _MODELS_ROOT / slug / "models.py"


def _generate(slug: str) -> None:
    schema = _schema_path(slug)
    if not schema.exists():
        print(f"Error: schema not found at {schema}", file=sys.stderr)
        sys.exit(1)

    output = _output_path(slug)
    output.parent.mkdir(parents=True, exist_ok=True)
    init = output.parent / "__init__.py"
    if not init.exists():
        init.write_text(
            f'"""Schema package for savefile process {output.parent.name}."""\n',
            encoding="utf-8",
        )
    generate(
        schema,
        input_file_type=InputFileType.JsonSchema,
        output=output,
        output_model_type=DataModelType.PydanticV2BaseModel,
        formatters=[Formatter.RUFF_FORMAT],
        use_schema_description=True,
        field_constraints=True,
        snake_case_field=True,
        settings_path=_PROJECT_ROOT,
    )
    _prepend_header(output)
    _reformat_no_wrap(output)
    print(f"Models written to {output}")


def _prepend_header(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    path.write_text(_GENERATED_HEADER + content, encoding="utf-8")


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
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <version_slug>", file=sys.stderr)
        sys.exit(1)
    _generate(sys.argv[1])


if __name__ == "__main__":
    main()
