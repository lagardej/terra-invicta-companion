#!/usr/bin/env python3
# ruff: noqa: C901
"""Map event publishing and listening usage across src/.

Usage:
    uv run python scripts/map_event_flow.py
    uv run python scripts/map_event_flow.py --src src --out build/event_flow_map.md
"""

from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Occurrence:
    """Single publish/listen occurrence found during AST scan."""

    file: str
    line: int
    detail: str
    caller: str | None = None


def _unwrap_cast(node: ast.AST) -> ast.AST:
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "cast"
        and len(node.args) >= 2
    ):
        return node.args[1]
    return node


def _extract_ref(node: ast.AST) -> str | None:
    node = _unwrap_cast(node)
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _iter_subscription_pairs(node: ast.AST) -> Iterator[tuple[ast.AST, ast.AST]]:
    node = _unwrap_cast(node)
    if isinstance(node, (ast.Tuple, ast.List)):
        values = [_unwrap_cast(elt) for elt in node.elts]
        if len(values) == 2:
            yield values[0], values[1]
        for elt in values:
            yield from _iter_subscription_pairs(elt)


def _extract_event_names_from_annotation(
    node: ast.AST,
    known_events: set[str],
) -> set[str]:  # noqa: C901
    refs: set[str] = set()

    def _walk(n: ast.AST) -> None:
        n = _unwrap_cast(n)
        if isinstance(n, ast.Name):
            if n.id in known_events:
                refs.add(n.id)
            return
        if isinstance(n, ast.Attribute):
            if n.attr in known_events:
                refs.add(n.attr)
            return
        if isinstance(n, ast.Subscript):
            _walk(n.value)
            _walk(n.slice)
            return
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr):
            _walk(n.left)
            _walk(n.right)
            return
        if isinstance(n, ast.Tuple):
            for elt in n.elts:
                _walk(elt)
            return
        if isinstance(n, ast.List):
            for elt in n.elts:
                _walk(elt)

    _walk(node)
    return refs


def _extract_type_names_from_annotation(node: ast.AST) -> set[str]:
    refs: set[str] = set()

    def _walk(n: ast.AST) -> None:
        n = _unwrap_cast(n)
        if isinstance(n, ast.Name):
            refs.add(n.id)
            return
        if isinstance(n, ast.Attribute):
            refs.add(n.attr)
            return
        if isinstance(n, ast.Subscript):
            _walk(n.value)
            _walk(n.slice)
            return
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr):
            _walk(n.left)
            _walk(n.right)
            return
        if isinstance(n, ast.Tuple):
            for elt in n.elts:
                _walk(elt)
            return
        if isinstance(n, ast.List):
            for elt in n.elts:
                _walk(elt)

    _walk(node)
    return refs


def _event_classes_from_file(file_path: Path) -> set[str]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    result: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            base_ref = _extract_ref(base)
            if base_ref in {"DomainEvent", "IntegrationEvent"}:
                result.add(node.name)
                break
    return result


def _events_constructed_in_file(file_path: Path, known_events: set[str]) -> set[str]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    constructed: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        ref = _extract_ref(node)
        if ref is not None and ref in known_events:
            constructed.add(ref)
    return constructed


class _EventFlowVisitor(ast.NodeVisitor):
    def __init__(
        self,
        rel_path: str,
        known_events: set[str],
        global_class_field_events: dict[str, dict[str, set[str]]],
        inferred_integration_events: set[str],
    ) -> None:
        self.rel_path = rel_path
        self.known_events = known_events
        self.publishes: list[Occurrence] = []
        self.listens: list[Occurrence] = []
        self._current_class: str | None = None
        self._class_stack: list[str] = []
        self._function_stack: list[str] = []
        self._var_types: dict[str, set[str]] = {}
        self._class_field_events: dict[str, dict[str, set[str]]] = defaultdict(dict)
        self._global_class_field_events = global_class_field_events
        self._inferred_integration_events = inferred_integration_events
        self._class_handler_result_type: dict[str, dict[str, set[str]]] = defaultdict(
            dict
        )

    def _current_caller(self) -> str | None:
        if not self._function_stack:
            return None
        function_name = self._function_stack[-1]
        if self._class_stack:
            return f"{self._class_stack[-1]}.{function_name}"
        return function_name

    def _record_publish(self, node: ast.AST, event_ref: str) -> None:
        if event_ref not in self.known_events:
            return
        self.publishes.append(
            Occurrence(
                file=self.rel_path,
                line=getattr(node, "lineno", 1),
                detail=event_ref,
                caller=self._current_caller(),
            )
        )

    def _record_listen(self, node: ast.AST, event_ref: str, handler_ref: str) -> None:
        if event_ref not in self.known_events:
            return
        self.listens.append(
            Occurrence(
                file=self.rel_path,
                line=getattr(node, "lineno", 1),
                detail=f"{event_ref} -> {handler_ref}",
            )
        )

    def _event_refs_from_expr(self, node: ast.AST) -> set[str]:  # noqa: C901
        node = _unwrap_cast(node)
        if isinstance(node, ast.Call):
            ref = _extract_ref(node)
            if ref in self.known_events:
                return {ref}
            return set()
        if isinstance(node, ast.Name):
            if node.id in self.known_events:
                return {node.id}
            return set(self._var_types.get(node.id, set()))
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                container_types = self._var_types.get(node.value.id, set())
                refs: set[str] = set()
                for typ in container_types:
                    refs.update(
                        self._class_field_events.get(typ, {}).get(node.attr, set())
                    )
                    refs.update(
                        self._global_class_field_events.get(typ, {}).get(
                            node.attr,
                            set(),
                        )
                    )
                if refs:
                    return refs
            if node.attr in self.known_events:
                return {node.attr}
            return set()
        if isinstance(node, ast.Starred):
            return self._event_refs_from_expr(node.value)
        return set()

    def _infer_var_assignment(self, target: ast.AST, value: ast.AST) -> None:
        if not isinstance(target, ast.Name):
            return
        value = _unwrap_cast(value)
        if isinstance(value, ast.Call):
            ref = _extract_ref(value)
            if ref in self.known_events:
                self._var_types[target.id] = {ref}
                return
            if (
                isinstance(value.func, ast.Attribute)
                and value.func.attr == "handle"
                and isinstance(value.func.value, ast.Attribute)
                and isinstance(value.func.value.value, ast.Name)
                and value.func.value.value.id == "self"
                and self._current_class is not None
            ):
                attr_name = value.func.value.attr
                refs = self._class_handler_result_type.get(self._current_class, {}).get(
                    attr_name,
                    set(),
                )
                if refs:
                    self._var_types[target.id] = set(refs)
                    return
        if isinstance(value, ast.Await):
            self._infer_var_assignment(target, value.value)
            return
        if isinstance(value, ast.Name) and value.id in self._var_types:
            self._var_types[target.id] = set(self._var_types[value.id])

    def _register_dataclass_field_events(self, node: ast.ClassDef) -> None:
        for child in node.body:
            if not isinstance(child, ast.AnnAssign):
                continue
            if not isinstance(child.target, ast.Name):
                continue
            refs = _extract_event_names_from_annotation(
                child.annotation,
                self.known_events,
            )
            if refs:
                self._class_field_events[node.name][child.target.id] = refs

    def _register_handler_result_types(self, node: ast.ClassDef) -> None:  # noqa: C901
        init_node: ast.FunctionDef | None = None
        for child in node.body:
            if isinstance(child, ast.FunctionDef) and child.name == "__init__":
                init_node = child
                break
        if init_node is None:
            return

        param_ann: dict[str, ast.AST] = {}
        for arg in init_node.args.args:
            if arg.annotation is not None:
                param_ann[arg.arg] = arg.annotation

        for stmt in init_node.body:
            if not isinstance(stmt, ast.Assign):
                continue
            if len(stmt.targets) != 1:
                continue
            target = stmt.targets[0]
            if not (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
                and isinstance(stmt.value, ast.Name)
            ):
                continue

            param_name = stmt.value.id
            ann = param_ann.get(param_name)
            if ann is None:
                continue

            if (
                isinstance(ann, ast.Subscript)
                and _extract_ref(ann.value) == "CommandHandler"
                and isinstance(ann.slice, ast.Tuple)
                and len(ann.slice.elts) >= 2
            ):
                result_type_ann = ann.slice.elts[1]
                refs = _extract_type_names_from_annotation(result_type_ann)
                if refs:
                    self._class_handler_result_type[node.name][target.attr] = refs

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802, C901
        if isinstance(node.func, ast.Attribute) and node.func.attr == "publish":
            for arg in node.args:
                refs = self._event_refs_from_expr(arg)
                if (
                    isinstance(arg, ast.Starred)
                    and not refs
                    and isinstance(arg.value, ast.Attribute)
                    and arg.value.attr == "integration_events"
                ):
                    refs = set(self._inferred_integration_events)
                for ref in refs:
                    self._record_publish(node, ref)

        if isinstance(node.func, ast.Attribute) and node.func.attr == "subscribe":
            if len(node.args) == 2:
                event_ref = _extract_ref(node.args[0])
                handler_ref = _extract_ref(node.args[1])
                if event_ref is not None and handler_ref is not None:
                    self._record_listen(node, event_ref, handler_ref)
            else:
                for arg in node.args:
                    if isinstance(arg, (ast.Tuple, ast.List)) and len(arg.elts) == 2:
                        event_ref = _extract_ref(arg.elts[0])
                        handler_ref = _extract_ref(arg.elts[1])
                        if event_ref is not None and handler_ref is not None:
                            self._record_listen(node, event_ref, handler_ref)

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        for target in node.targets:
            self._infer_var_assignment(target, node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # noqa: N802
        if node.value is not None:
            self._infer_var_assignment(node.target, node.value)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self._register_dataclass_field_events(node)
        self._register_handler_result_types(node)

        previous_class = self._current_class
        previous_vars = self._var_types

        self._current_class = node.name
        self._var_types = {}
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

        self._current_class = previous_class
        self._var_types = previous_vars

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._visit_subscriptions_return(node)
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._visit_subscriptions_return(node)
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def _visit_subscriptions_return(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        if node.name != "subscriptions":
            return
        for subnode in ast.walk(node):
            if isinstance(subnode, ast.Return) and subnode.value is not None:
                for event_node, handler_node in _iter_subscription_pairs(subnode.value):
                    event_ref = _extract_ref(event_node)
                    handler_ref = _extract_ref(handler_node)
                    if event_ref is not None and handler_ref is not None:
                        self._record_listen(subnode, event_ref, handler_ref)


def _collect_python_files(src_root: Path) -> list[Path]:
    return sorted(p for p in src_root.rglob("*.py") if p.is_file())


def _group_by_event(
    publishes: list[Occurrence],
    listens: list[Occurrence],
) -> dict[str, dict[str, list[Occurrence]]]:
    grouped: dict[str, dict[str, list[Occurrence]]] = defaultdict(
        lambda: {"publishes": [], "listens": []}
    )

    for item in publishes:
        grouped[item.detail]["publishes"].append(item)

    for item in listens:
        event_ref = item.detail.split(" -> ", maxsplit=1)[0]
        grouped[event_ref]["listens"].append(item)

    return dict(sorted(grouped.items(), key=lambda kv: kv[0].lower()))


def _format_report(grouped: dict[str, dict[str, list[Occurrence]]]) -> str:
    def _source_link(item: Occurrence) -> str:
        target = f"../{item.file}#L{item.line}"
        label = f"{item.file}:{item.line}"
        return f"[{label}]({target})"

    lines: list[str] = []
    lines.append("Event Flow Map")
    lines.append("==============")
    lines.append("")

    if not grouped:
        lines.append("No event publish/listen activity found.")
        lines.append("")
        return "\n".join(lines)

    for event_name, buckets in grouped.items():
        lines.append(f"{event_name}")
        lines.append("-" * len(event_name))

        publishes = sorted(buckets["publishes"], key=lambda x: (x.file, x.line))
        listens = sorted(buckets["listens"], key=lambda x: (x.file, x.line))

        lines.append("Publishes:")
        if publishes:
            for item in publishes:
                if item.caller:
                    lines.append(f"  - {_source_link(item)} (from {item.caller})")
                else:
                    lines.append(f"  - {_source_link(item)}")
        else:
            lines.append("  - none")

        lines.append("")

        lines.append("Listens:")
        if listens:
            for item in listens:
                lines.append(f"  - {_source_link(item)} ({item.detail})")
        else:
            lines.append("  - none")

        lines.append("")

    return "\n".join(lines)


def map_event_flow(src_root: Path, out_path: Path) -> Path:  # noqa: C901
    """Inspect source files and write a markdown map of event flow."""
    all_files = _collect_python_files(src_root)
    event_files = [p for p in all_files if "/events/" in p.as_posix()]
    known_events: set[str] = set()
    for file_path in event_files:
        known_events.update(_event_classes_from_file(file_path))

    inferred_integration_events: set[str] = set()
    processor_glob = "tic/savefile/process/_processor/*.py"
    for file_path in src_root.glob(processor_glob):
        inferred_integration_events.update(
            _events_constructed_in_file(file_path, known_events)
        )

    global_class_field_events: dict[str, dict[str, set[str]]] = defaultdict(dict)
    for file_path in all_files:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for child in node.body:
                if not isinstance(child, ast.AnnAssign):
                    continue
                if not isinstance(child.target, ast.Name):
                    continue
                refs = _extract_event_names_from_annotation(
                    child.annotation,
                    known_events,
                )
                if refs:
                    global_class_field_events[node.name][child.target.id] = refs

    publishes: list[Occurrence] = []
    listens: list[Occurrence] = []

    for file_path in all_files:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        rel_path = file_path.relative_to(src_root.parent).as_posix()
        visitor = _EventFlowVisitor(
            rel_path=rel_path,
            known_events=known_events,
            global_class_field_events=global_class_field_events,
            inferred_integration_events=inferred_integration_events,
        )
        visitor.visit(tree)
        publishes.extend(visitor.publishes)
        listens.extend(visitor.listens)

    grouped = _group_by_event(publishes, listens)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_format_report(grouped), encoding="utf-8")
    return out_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect src and map event publishing/listening usage."
    )
    parser.add_argument("--src", type=Path, default=Path("src"), help="Source root")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("build/event_flow_map.md"),
        help="Output report path",
    )
    return parser.parse_args()


def _resolve_output_path(path: Path) -> Path:
    if path.suffix.lower() != ".md":
        return path.with_suffix(".md")
    return path


def main() -> int:
    """CLI entrypoint for event flow report generation."""
    args = _parse_args()
    output = map_event_flow(src_root=args.src, out_path=_resolve_output_path(args.out))
    print(f"Event flow map written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
