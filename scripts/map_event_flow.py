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
class ChainPath:
    """Linearized event chain path from a root trigger event."""

    root_event: str
    steps: tuple[str, ...]


@dataclass(frozen=True)
class LocalFlowGraph:
    """Intra-file call graph with optional event-type guards."""

    unconditional_calls: dict[str, set[str]]
    guarded_calls: dict[tuple[str, str], set[str]]


@dataclass(frozen=True)
class Occurrence:
    """Single publish/listen occurrence found during AST scan."""

    event_name: str
    event_kind: str
    file: str
    line: int
    detail: str
    caller: str | None = None


@dataclass(frozen=True)
class EventClass:
    """Discovered event class metadata from source modules."""

    name: str
    kind: str
    module: str


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


def _module_path_for_file(file_path: Path, src_root: Path) -> str:
    return file_path.relative_to(src_root).with_suffix("").as_posix().replace("/", ".")


def _event_classes_from_file(file_path: Path, src_root: Path) -> list[EventClass]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    result: list[EventClass] = []
    module = _module_path_for_file(file_path, src_root)
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            base_ref = _extract_ref(base)
            if base_ref == "DomainEvent":
                result.append(EventClass(name=node.name, kind="Domain", module=module))
                break
            if base_ref == "IntegrationEvent":
                result.append(
                    EventClass(
                        name=node.name,
                        kind="Integration",
                        module=module,
                    )
                )
                break
            if base_ref == "Event":
                result.append(
                    EventClass(
                        name=node.name,
                        kind="Unknown",
                        module=module,
                    )
                )
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


def _infer_function_event_refs(
    tree: ast.Module,
    known_events: set[str],
) -> dict[str, set[str]]:
    function_nodes = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    inferred: dict[str, set[str]] = defaultdict(set)

    for node in function_nodes:
        if node.returns is None:
            continue
        refs = _extract_event_names_from_annotation(node.returns, known_events)
        if refs:
            inferred[node.name].update(refs)

    changed = True
    while changed:
        changed = False
        for node in function_nodes:
            refs = set(inferred.get(node.name, set()))
            for child in ast.walk(node):
                if not isinstance(child, ast.Call):
                    continue
                ref = _extract_ref(child)
                if ref is None:
                    continue
                if ref in known_events:
                    refs.add(ref)
                refs.update(inferred.get(ref, set()))

            if refs != inferred.get(node.name, set()):
                inferred[node.name] = refs
                changed = True

    return {name: refs for name, refs in inferred.items() if refs}


def _is_subscription_factory(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    """Heuristic for functions that define message-bus subscriptions."""
    if "subscription" in node.name:
        return True
    if node.returns is None:
        return False
    return "Subscription" in _extract_type_names_from_annotation(node.returns)


class _EventFlowVisitor(ast.NodeVisitor):
    def __init__(
        self,
        rel_path: str,
        known_events: set[str],
        event_kinds_by_name: dict[str, set[str]],
        event_kinds_by_module_name: dict[tuple[str, str], set[str]],
        global_class_field_events: dict[str, dict[str, set[str]]],
        inferred_integration_events: set[str],
        function_event_refs: dict[str, set[str]],
        function_event_refs_by_module_name: dict[tuple[str, str], set[str]],
    ) -> None:
        self.rel_path = rel_path
        self.known_events = known_events
        self._event_kinds_by_name = event_kinds_by_name
        self._event_kinds_by_module_name = event_kinds_by_module_name
        self.publishes: list[Occurrence] = []
        self.listens: list[Occurrence] = []
        self._current_class: str | None = None
        self._class_stack: list[str] = []
        self._function_stack: list[str] = []
        self._var_types: dict[str, set[str]] = {}
        self._class_field_events: dict[str, dict[str, set[str]]] = defaultdict(dict)
        self._global_class_field_events = global_class_field_events
        self._inferred_integration_events = inferred_integration_events
        self._function_event_refs = function_event_refs
        self._function_event_refs_by_module_name = function_event_refs_by_module_name
        self._imported_event_kinds: dict[str, set[str]] = {}
        self._imported_function_event_refs: dict[str, set[str]] = {}
        self._module_aliases: dict[str, str] = {}
        self._class_handler_result_type: dict[str, dict[str, set[str]]] = defaultdict(
            dict
        )

    def _function_refs_for_call(self, call_ref: str) -> set[str]:
        refs = set(self._function_event_refs.get(call_ref, set()))
        refs.update(self._imported_function_event_refs.get(call_ref, set()))
        return refs

    def _event_kinds_for_ref(self, event_ref: str, node: ast.AST | None) -> set[str]:
        if event_ref in self._imported_event_kinds:
            return set(self._imported_event_kinds[event_ref])

        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id in self._module_aliases
        ):
            module_name = self._module_aliases[node.value.id]
            by_module = self._event_kinds_by_module_name.get(
                (module_name, event_ref),
                set(),
            )
            if by_module:
                return set(by_module)

        return set(self._event_kinds_by_name.get(event_ref, set()))

    def _current_caller(self) -> str | None:
        if not self._function_stack:
            return None
        function_name = self._function_stack[-1]
        if self._class_stack:
            return f"{self._class_stack[-1]}.{function_name}"
        return function_name

    def _record_publish(
        self,
        node: ast.AST,
        event_ref: str,
        event_node: ast.AST | None,
    ) -> None:
        if event_ref not in self.known_events:
            return
        for event_kind in sorted(self._event_kinds_for_ref(event_ref, event_node)):
            self.publishes.append(
                Occurrence(
                    event_name=event_ref,
                    event_kind=event_kind,
                    file=self.rel_path,
                    line=getattr(node, "lineno", 1),
                    detail=event_ref,
                    caller=self._current_caller(),
                )
            )

    def _record_listen(
        self,
        node: ast.AST,
        event_ref: str,
        handler_ref: str,
        event_node: ast.AST | None,
    ) -> None:
        if event_ref not in self.known_events:
            return
        for event_kind in sorted(self._event_kinds_for_ref(event_ref, event_node)):
            self.listens.append(
                Occurrence(
                    event_name=event_ref,
                    event_kind=event_kind,
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
            if ref is None:
                return set()
            return self._function_refs_for_call(ref)
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
                if node.attr in {"event", "status_event"}:
                    return set(container_types)
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
            function_refs = set()
            if ref is not None:
                function_refs = self._function_refs_for_call(ref)
            if function_refs:
                self._var_types[target.id] = function_refs
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
        if isinstance(value, (ast.Tuple, ast.List)):
            refs: set[str] = set()
            for elt in value.elts:
                refs.update(self._event_refs_from_expr(elt))
            if refs:
                self._var_types[target.id] = refs
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
                    self._record_publish(node, ref, arg)

        if isinstance(node.func, ast.Attribute) and node.func.attr == "subscribe":
            if len(node.args) == 2:
                event_ref = _extract_ref(node.args[0])
                handler_ref = _extract_ref(node.args[1])
                if event_ref is not None and handler_ref is not None:
                    self._record_listen(node, event_ref, handler_ref, node.args[0])
            else:
                for arg in node.args:
                    if isinstance(arg, (ast.Tuple, ast.List)) and len(arg.elts) == 2:
                        event_ref = _extract_ref(arg.elts[0])
                        handler_ref = _extract_ref(arg.elts[1])
                        if event_ref is not None and handler_ref is not None:
                            self._record_listen(
                                node,
                                event_ref,
                                handler_ref,
                                arg.elts[0],
                            )

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        if node.module is not None:
            for alias in node.names:
                local_name = alias.asname or alias.name
                kinds = self._event_kinds_by_module_name.get((node.module, alias.name))
                if kinds:
                    self._imported_event_kinds[local_name] = set(kinds)
                function_refs = self._function_event_refs_by_module_name.get(
                    (node.module, alias.name)
                )
                if function_refs:
                    self._imported_function_event_refs[local_name] = set(function_refs)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        for alias in node.names:
            if alias.asname is not None:
                self._module_aliases[alias.asname] = alias.name
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

    def _bind_match_pattern(self, pattern: ast.pattern, refs: set[str]) -> None:
        if isinstance(pattern, ast.MatchAs) and pattern.name is not None:
            self._var_types[pattern.name] = set(refs)
            return
        if isinstance(pattern, ast.MatchStar) and pattern.name is not None:
            self._var_types[pattern.name] = set(refs)
            return
        if isinstance(pattern, ast.MatchSequence):
            for child in pattern.patterns:
                self._bind_match_pattern(child, refs)
            return
        if isinstance(pattern, ast.MatchClass):
            for child in pattern.patterns:
                self._bind_match_pattern(child, refs)
            for child in pattern.kwd_patterns:
                self._bind_match_pattern(child, refs)

    def visit_Match(self, node: ast.Match) -> None:  # noqa: N802
        subject_refs = self._event_refs_from_expr(node.subject)
        for case in node.cases:
            self._bind_match_pattern(case.pattern, subject_refs)
        self.generic_visit(node)

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
        if not _is_subscription_factory(node):
            return
        for subnode in ast.walk(node):
            if isinstance(subnode, ast.Return) and subnode.value is not None:
                for event_node, handler_node in _iter_subscription_pairs(subnode.value):
                    event_ref = _extract_ref(event_node)
                    handler_ref = _extract_ref(handler_node)
                    if event_ref is not None and handler_ref is not None:
                        self._record_listen(subnode, event_ref, handler_ref, event_node)


def _collect_python_files(src_root: Path) -> list[Path]:
    return sorted(p for p in src_root.rglob("*.py") if p.is_file())


def _group_by_event(
    publishes: list[Occurrence],
    listens: list[Occurrence],
) -> dict[tuple[str, str], dict[str, list[Occurrence]]]:
    grouped: dict[tuple[str, str], dict[str, list[Occurrence]]] = defaultdict(
        lambda: {"publishes": [], "listens": []}
    )

    for item in publishes:
        grouped[(item.event_name, item.event_kind)]["publishes"].append(item)

    for item in listens:
        grouped[(item.event_name, item.event_kind)]["listens"].append(item)

    return dict(sorted(grouped.items(), key=lambda kv: (kv[0][1], kv[0][0].lower())))


def _extract_handler_ref(detail: str) -> str | None:
    marker = "->"
    if marker not in detail:
        return None
    return detail.split(marker, 1)[1].strip()


class _LocalCallGraphVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.calls: dict[str, set[str]] = defaultdict(set)
        self.calls_by_event: dict[tuple[str, str], set[str]] = defaultdict(set)
        self._class_stack: list[str] = []
        self._function_stack: list[str] = []
        self._function_args_stack: list[set[str]] = []
        self._event_guard_stack: list[set[str] | None] = []

    def _current_function(self) -> str | None:
        if not self._function_stack:
            return None
        function_name = self._function_stack[-1]
        if self._class_stack:
            return f"{self._class_stack[-1]}.{function_name}"
        return function_name

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._function_stack.append(node.name)
        args = {arg.arg for arg in node.args.args}
        self._function_args_stack.append(args)
        self._event_guard_stack.append(None)
        self.generic_visit(node)
        self._event_guard_stack.pop()
        self._function_args_stack.pop()
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._function_stack.append(node.name)
        args = {arg.arg for arg in node.args.args}
        self._function_args_stack.append(args)
        self._event_guard_stack.append(None)
        self.generic_visit(node)
        self._event_guard_stack.pop()
        self._function_args_stack.pop()
        self._function_stack.pop()

    def _pattern_event_refs(self, pattern: ast.pattern) -> set[str]:
        refs: set[str] = set()
        if isinstance(pattern, ast.MatchClass):
            ref = _extract_ref(pattern.cls)
            if ref is not None:
                refs.add(ref)
            for child in pattern.patterns:
                refs.update(self._pattern_event_refs(child))
            for child in pattern.kwd_patterns:
                refs.update(self._pattern_event_refs(child))
            return refs
        if isinstance(pattern, ast.MatchOr):
            for child in pattern.patterns:
                refs.update(self._pattern_event_refs(child))
            return refs
        if isinstance(pattern, ast.MatchAs) and pattern.pattern is not None:
            refs.update(self._pattern_event_refs(pattern.pattern))
            return refs
        if isinstance(pattern, ast.MatchSequence):
            for child in pattern.patterns:
                refs.update(self._pattern_event_refs(child))
            return refs
        return refs

    def _merge_guard(self, refs: set[str]) -> set[str] | None:
        current = self._event_guard_stack[-1] if self._event_guard_stack else None
        if current is None:
            return refs or None
        if not refs:
            return set(current)
        intersected = current & refs
        return intersected or None

    def visit_Match(self, node: ast.Match) -> None:  # noqa: N802
        subject = node.subject
        is_event_subject = (
            isinstance(subject, ast.Name)
            and self._function_args_stack
            and subject.id in self._function_args_stack[-1]
        )
        if not is_event_subject:
            self.generic_visit(node)
            return

        self.visit(node.subject)
        for case in node.cases:
            refs = self._pattern_event_refs(case.pattern)
            merged_guard = self._merge_guard(refs)
            self._event_guard_stack.append(merged_guard)
            if case.guard is not None:
                self.visit(case.guard)
            for stmt in case.body:
                self.visit(stmt)
            self._event_guard_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        caller = self._current_function()
        if caller is not None:
            callee: str | None = None
            if isinstance(node.func, ast.Name):
                callee = node.func.id
            elif (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "self"
                and self._class_stack
            ):
                callee = f"{self._class_stack[-1]}.{node.func.attr}"
            if callee is not None:
                guard = self._event_guard_stack[-1] if self._event_guard_stack else None
                if guard:
                    for event_name in guard:
                        self.calls_by_event[(caller, event_name)].add(callee)
                else:
                    self.calls[caller].add(callee)
        self.generic_visit(node)


def _build_local_call_graphs(
    all_files: list[Path],
    src_root: Path,
) -> dict[str, LocalFlowGraph]:
    graphs: dict[str, LocalFlowGraph] = {}
    for file_path in all_files:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        rel_path = file_path.relative_to(src_root.parent).as_posix()
        visitor = _LocalCallGraphVisitor()
        visitor.visit(tree)
        graphs[rel_path] = LocalFlowGraph(
            unconditional_calls={k: set(v) for k, v in visitor.calls.items()},
            guarded_calls={k: set(v) for k, v in visitor.calls_by_event.items()},
        )
    return graphs


def _reachable_callers(
    graph: LocalFlowGraph,
    start: str,
    event_name: str,
) -> set[str]:
    seen: set[str] = set()
    stack = [start]
    while stack:
        caller = stack.pop()
        if caller in seen:
            continue
        seen.add(caller)
        for callee in graph.unconditional_calls.get(caller, set()):
            if callee not in seen:
                stack.append(callee)
        for callee in graph.guarded_calls.get((caller, event_name), set()):
            if callee not in seen:
                stack.append(callee)
    return seen


def _build_event_chains(
    publishes: list[Occurrence],
    listens: list[Occurrence],
    local_call_graphs: dict[str, LocalFlowGraph],
    roots: tuple[str, ...] = ("SavefileChangeDetected",),
) -> list[ChainPath]:
    publishes_by_file_caller: dict[tuple[str, str], list[Occurrence]] = defaultdict(
        list
    )
    for item in publishes:
        if item.caller is None:
            continue
        publishes_by_file_caller[(item.file, item.caller)].append(item)

    listens_by_event: dict[str, list[Occurrence]] = defaultdict(list)
    for item in listens:
        listens_by_event[item.event_name].append(item)

    result: list[ChainPath] = []

    def source_link(item: Occurrence) -> str:
        return f"[{item.file}:{item.line}](../{item.file})"

    def walk(event_name: str, steps: tuple[str, ...], visited: set[str]) -> None:
        listeners = sorted(
            listens_by_event.get(event_name, []),
            key=lambda x: (x.file, x.line),
        )
        if not listeners:
            result.append(ChainPath(root_event=steps[0], steps=steps))
            return

        expanded_any = False
        for listen in listeners:
            handler = _extract_handler_ref(listen.detail)
            if handler is None:
                continue

            graph = local_call_graphs.get(
                listen.file,
                LocalFlowGraph(unconditional_calls={}, guarded_calls={}),
            )
            reachable = _reachable_callers(graph, handler, event_name)

            produced: list[Occurrence] = []
            for caller in sorted(reachable):
                produced.extend(publishes_by_file_caller.get((listen.file, caller), []))
            produced = sorted(produced, key=lambda x: (x.file, x.line, x.event_name))

            handler_step = f"{handler} @ {source_link(listen)}"
            if not produced:
                result.append(
                    ChainPath(
                        root_event=steps[0],
                        steps=steps + (handler_step,),
                    )
                )
                expanded_any = True
                continue

            for publish in produced:
                publish_step = f"{publish.event_name} @ {source_link(publish)}"
                next_steps = steps + (handler_step, publish_step)
                if publish.event_name in visited:
                    result.append(
                        ChainPath(
                            root_event=steps[0],
                            steps=next_steps + ("(cycle detected)",),
                        )
                    )
                    expanded_any = True
                    continue
                walk(
                    publish.event_name,
                    next_steps,
                    visited | {publish.event_name},
                )
                expanded_any = True

        if not expanded_any:
            result.append(ChainPath(root_event=steps[0], steps=steps))

    for root in roots:
        has_publish = root in {p.event_name for p in publishes}
        if root not in listens_by_event and not has_publish:
            continue
        walk(root, (root,), {root})

    return result


def _format_report(
    grouped: dict[tuple[str, str], dict[str, list[Occurrence]]],
    chains: list[ChainPath],
) -> str:
    def _source_link(item: Occurrence) -> str:
        target = f"../{item.file}"
        label = f"{item.file}:{item.line}"
        return f"[{label}]({target})"

    def _publish_cell(item: Occurrence) -> str:
        link = _source_link(item)
        return f"{link} (from {item.caller})" if item.caller else link

    def _listen_cell(item: Occurrence) -> str:
        return f"{_source_link(item)} (`{item.detail}`)"

    lines: list[str] = []
    lines.append("# Event Flow Map")
    lines.append("")

    if not grouped:
        lines.append("No event publish/listen activity found.")
        lines.append("")
        return "\n".join(lines)

    grouped_by_type: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for event_key in grouped:
        grouped_by_type[event_key[1]].append(event_key)

    group_order = ["Domain", "Integration", "Unknown"]

    for group_name in group_order:
        event_keys = sorted(
            grouped_by_type.get(group_name, []),
            key=lambda x: x[0].lower(),
        )
        if not event_keys:
            continue

        lines.append(f"## {group_name} Events")
        lines.append("")
        lines.append("| Event | Publishes | Listens |")
        lines.append("| --- | --- | --- |")

        for event_name, event_kind in event_keys:
            buckets = grouped[(event_name, event_kind)]
            publishes = sorted(buckets["publishes"], key=lambda x: (x.file, x.line))
            listens = sorted(buckets["listens"], key=lambda x: (x.file, x.line))

            pub_cell = (
                "<br>".join(_publish_cell(p) for p in publishes) if publishes else ""
            )
            lst_cell = (
                "<br>".join(_listen_cell(listen) for listen in listens)
                if listens
                else ""
            )
            lines.append(f"| **{event_name}** | {pub_cell} | {lst_cell} |")

        lines.append("")

    if chains:
        lines.append("## Event Chains")
        lines.append("")
        by_root: dict[str, list[ChainPath]] = defaultdict(list)
        for chain in chains:
            by_root[chain.root_event].append(chain)

        for root_event in sorted(by_root):
            lines.append(f"### From {root_event}")
            lines.append("")
            for chain in sorted(by_root[root_event], key=lambda c: c.steps):
                lines.append(f"- {chain.steps[0]}")
                for depth, step in enumerate(chain.steps[1:], start=1):
                    indent = "  " * depth
                    lines.append(f"{indent}- {step}")
                lines.append("")
            lines.append("")

    return "\n".join(lines)


def map_event_flow(src_root: Path, out_path: Path) -> Path:  # noqa: C901
    """Inspect source files and write a markdown map of event flow."""
    all_files = _collect_python_files(src_root)
    event_kinds_by_name: dict[str, set[str]] = defaultdict(set)
    event_kinds_by_module_name: dict[tuple[str, str], set[str]] = defaultdict(set)
    for file_path in all_files:
        for event_class in _event_classes_from_file(file_path, src_root):
            event_kinds_by_name[event_class.name].add(event_class.kind)
            event_kinds_by_module_name[(event_class.module, event_class.name)].add(
                event_class.kind
            )
    known_events = set(event_kinds_by_name.keys())

    inferred_integration_events: set[str] = set()
    processor_glob = "tic/savefile/process/_processor/*.py"
    for file_path in src_root.glob(processor_glob):
        inferred_integration_events.update(
            _events_constructed_in_file(file_path, known_events)
        )

    global_class_field_events: dict[str, dict[str, set[str]]] = defaultdict(dict)
    function_event_refs_by_module_name: dict[tuple[str, str], set[str]] = {}
    for file_path in all_files:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        module = _module_path_for_file(file_path, src_root)
        inferred_function_refs = _infer_function_event_refs(tree, known_events)
        for function_name, refs in inferred_function_refs.items():
            function_event_refs_by_module_name[(module, function_name)] = set(refs)
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
    local_call_graphs = _build_local_call_graphs(all_files, src_root)

    for file_path in all_files:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        rel_path = file_path.relative_to(src_root.parent).as_posix()
        function_event_refs = _infer_function_event_refs(tree, known_events)
        visitor = _EventFlowVisitor(
            rel_path=rel_path,
            known_events=known_events,
            event_kinds_by_name=dict(event_kinds_by_name),
            event_kinds_by_module_name=dict(event_kinds_by_module_name),
            global_class_field_events=global_class_field_events,
            inferred_integration_events=inferred_integration_events,
            function_event_refs=function_event_refs,
            function_event_refs_by_module_name=function_event_refs_by_module_name,
        )
        visitor.visit(tree)
        publishes.extend(visitor.publishes)
        listens.extend(visitor.listens)

    grouped = _group_by_event(publishes, listens)
    chains = _build_event_chains(publishes, listens, local_call_graphs)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_format_report(grouped, chains), encoding="utf-8")
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
