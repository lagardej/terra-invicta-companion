#!/usr/bin/env python3
# noqa: D101
"""Generate Pydantic models from a JSON file.

Usage: python scripts/json2pydantic.py input.json [--outdir build/json2pydantic]
"""

from __future__ import annotations

import argparse
import json
import keyword
import re
from pathlib import Path

PRIMITIVE_MAP = {str: "str", int: "int", float: "float", bool: "bool"}


def _camel_case(s: str) -> str:
    parts = [p for p in s.replace("-", "_").split("_") if p]
    return "".join(p.capitalize() for p in parts) or "Model"


def _infer_type(
    value: object, name_hint: str, classes: dict[str, dict[str, tuple[str, str]]]
) -> str:
    if value is None:
        return "Any"
    if isinstance(value, dict):
        cls_name = _camel_case(name_hint)
        _collect_class(value, cls_name, classes)
        return cls_name
    if isinstance(value, list):
        item_type = "Any"
        for it in value:
            if it is None:
                continue
            if isinstance(it, dict):
                cls_name = _camel_case(name_hint + "Item")
                _collect_class(it, cls_name, classes)
                item_type = cls_name
                break
            else:
                item_type = PRIMITIVE_MAP.get(type(it), "Any")
                break
        return f"list[{item_type}]"
    return PRIMITIVE_MAP.get(type(value), "Any")


def _safe_field_name(name: str) -> str:
    # replace non-alphanumeric with underscore
    s = re.sub(r"[^0-9a-zA-Z_]", "_", name)
    # insert underscores between camelCase transitions
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    s = re.sub(r"__+", "_", s)
    s = s.lower()
    if s and s[0].isdigit():
        s = "f_" + s
    if keyword.iskeyword(s):
        s = s + "_"
    if not s.isidentifier():
        s = "field_" + s
    return s


def _collect_class(
    obj: dict[str, object],
    cls_name: str,
    classes: dict[str, dict[str, tuple[str, str]]],
) -> None:
    if cls_name in classes:
        return
    fields: dict[str, tuple[str, str]] = {}
    for k, v in obj.items():
        t = _infer_type(v, k, classes)
        safe = _safe_field_name(k)
        fields[safe] = (k, t)
    classes[cls_name] = fields


def _render_classes(
    classes: dict[str, dict[str, tuple[str, str]]], root_name: str
) -> str:
    lines: list[str] = []
    # emit a ruff file-level noqa directive first so ruff/pydocstyle ignore D101
    lines.append("# ruff: noqa: D101")
    # place module docstring (ending with a period to satisfy D415)
    lines.append(f'"""{root_name} models generated from JSON."""')
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append("from typing import Any")
    lines.append("from pydantic import BaseModel, Field")
    lines.append("")

    for cls_name, fields in classes.items():
        lines.append(f"class {cls_name}(BaseModel):")
        if not fields:
            lines.append("    pass")
            lines.append("")
            continue
        for fname, (orig, ftype) in fields.items():
            # always use alias to preserve original key
            alias = orig.replace('"', '\\"')
            lines.append(f'    {fname}: {ftype} = Field(..., alias="{alias}")')
        lines.append("")
    return "\n".join(lines)


def _generate_models(data: object, root_basename: str) -> tuple[str, str]:
    classes: dict[str, dict[str, tuple[str, str]]] = {}
    root_name = _camel_case(Path(root_basename).stem)
    if isinstance(data, dict):
        _collect_class(data, root_name, classes)
    else:
        if isinstance(data, list) and data and isinstance(data[0], dict):
            item_name = root_name + "Item"
            _collect_class(data[0], item_name, classes)
            classes[root_name] = {"items": ("items", f"list[{item_name}]")}
        else:
            classes[root_name] = {"value": ("value", "Any")}

    code = _render_classes(classes, root_name)

    def _to_snake(name: str) -> str:
        s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
        s = re.sub(r"[^0-9a-zA-Z_]", "_", s)
        s = re.sub(r"__+", "_", s)
        s = s.lower()
        if s and s[0].isdigit():
            s = "f_" + s
        return s

    filename = f"{_to_snake(Path(root_basename).stem)}.py"
    return filename, code


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint.

    Args:
        argv: Optional list of argv strings to parse instead of sys.argv.
    """
    parser = argparse.ArgumentParser(description="Generate pydantic models from JSON")
    parser.add_argument("json_file", help="Input JSON file")
    parser.add_argument(
        "--outdir", default="build/json2pydantic/", help="Output directory"
    )
    args = parser.parse_args(argv)

    src = Path(args.json_file)
    if not src.exists():
        raise SystemExit(f"input file not found: {src}")
    data = json.loads(src.read_text(encoding="utf-8"))
    out_name, code = _generate_models(data, src.name)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / out_name
    outpath.write_text(code, encoding="utf-8")
    print(f"Wrote models to {outpath}")


if __name__ == "__main__":
    main()
