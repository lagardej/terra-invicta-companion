"""Generate a combined index file: project file list + symbol maps.

Output: .tic/index.json  (or <output-dir>/index.json)

Schema:
  {
    "files": ["path/to/file", ...],
    "by_symbol": {"SymbolName": "path", ...},
    "by_file": {"path": ["Sym", ...], ...}
  }

"files" lists all tracked project files.
"by_symbol" maps each symbol to the file that defines it (forward index).
"by_file" maps each file to its symbols; files with no symbols are omitted.
"""

from __future__ import annotations

import ast
import contextlib
import json
import sys
from pathlib import Path

_INDEX_NAME = "index.json"

_MANIFEST_DIRECTORIES = (".tic", "docs", "projects", "scripts")
_SYMBOL_DIRECTORIES = ("projects", "scripts")

_EXCLUDED_DIRS = frozenset({"__pycache__", ".pytest_cache", ".venv"})
_PYTHON_SUFFIX = ".py"

_ARG_COUNT_WITH_OUTPUT_DIR = 2


def main(argv: list[str]) -> int:
    """Write a combined index file to the requested output directory."""
    output_directory = _parse_output_directory(argv)
    if output_directory is None:
        return 1

    project_root = Path(__file__).resolve().parents[1]
    index_path = output_directory / _INDEX_NAME

    files = _collect_files(project_root, index_path)
    by_symbol, by_file = _collect_symbols(project_root)

    output_directory.mkdir(parents=True, exist_ok=True)
    payload = {"files": files, "by_symbol": by_symbol, "by_file": by_file}
    index_path.write_text(
        json.dumps(payload, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    sys.stdout.write(f"Wrote {index_path}\n")
    return 0


def _parse_output_directory(argv: list[str]) -> Path | None:
    if len(argv) not in (1, _ARG_COUNT_WITH_OUTPUT_DIR):
        sys.stderr.write("Usage: generate_index.py [output-directory]\n")
        return None
    if len(argv) == _ARG_COUNT_WITH_OUTPUT_DIR:
        return Path(argv[1]).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / ".tic"


# -- file list ----------------------------------------------------------------


def _collect_files(project_root: Path, index_path: Path) -> list[str]:
    files: set[str] = {
        p.relative_to(project_root).as_posix()
        for p in project_root.iterdir()
        if p.is_file()
    }
    for name in _MANIFEST_DIRECTORIES:
        files.update(_walk_files(project_root, name))

    with contextlib.suppress(ValueError):
        files.discard(index_path.relative_to(project_root).as_posix())

    return sorted(files)


def _walk_files(project_root: Path, directory_name: str) -> list[str]:
    directory = project_root / directory_name
    result: list[str] = []
    for root, dirs, file_names in directory.walk():
        dirs[:] = [d for d in dirs if d not in _EXCLUDED_DIRS]
        result.extend(
            (root / f).relative_to(project_root).as_posix() for f in file_names
        )
    return result


# -- symbol index -------------------------------------------------------------


def _collect_symbols(
    project_root: Path,
) -> tuple[dict[str, str], dict[str, list[str]]]:
    by_symbol: dict[str, str] = {}
    by_file: dict[str, list[str]] = {}

    for directory_name in _SYMBOL_DIRECTORIES:
        for python_file in _iter_python_files(project_root / directory_name):
            rel = python_file.relative_to(project_root).as_posix()
            symbols = _extract_symbols(python_file)
            if symbols:
                by_file[rel] = symbols
                for sym in symbols:
                    by_symbol[sym] = rel

    return dict(sorted(by_symbol.items())), dict(sorted(by_file.items()))


def _iter_python_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    files: list[Path] = []
    for root, dirs, file_names in directory.walk():
        dirs[:] = [d for d in dirs if d not in _EXCLUDED_DIRS]
        files.extend(root / f for f in file_names if f.endswith(_PYTHON_SUFFIX))
    return files


def _extract_symbols(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        sys.stderr.write(f"Warning: could not parse {path}\n")
        return []
    return [
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
    ]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
