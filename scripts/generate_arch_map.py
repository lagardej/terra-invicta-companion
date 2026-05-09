"""Generate a Markdown document describing modules and use cases.

Scans src/tic/ for __init__.py files containing __marker__ = "module" or
__marker__ = "use_case". For each use case, inspects shell files to extract
events listened to (from subscription return tuples) and published (from
bus.publish() calls). Each event is annotated with its kind (DomainEvent,
IntegrationEvent, or Event) from a registry built by scanning event files.

Also generates an event lookup table: for each event, which use cases publish
or listen to it.

Output: build/modules.md  (or <output-path> if provided)

Usage:
    python scripts/generate_arch_map.py [output-path]
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path

_SRC_ROOT = "src/tic"
_DEFAULT_OUTPUT = "build/modules.md"

_MARKER_MODULE = "module"
_MARKER_USE_CASE = "use_case"

_ARG_COUNT_WITH_OUTPUT = 2

_SHELL_GLOBS = ("shell.py", "shell/*.py")

_KIND_LABELS = {
    "DomainEvent": "domain",
    "IntegrationEvent": "integration",
    "Event": "coordination",
}


@dataclass
class UseCaseEvents:
    """Events listened to and published by a use case."""

    listened: list[str] = field(default_factory=list)
    published: list[str] = field(default_factory=list)


@dataclass
class EventIndex:
    """Use cases that publish or listen to an event."""

    published_by: list[str] = field(default_factory=list)
    listened_by: list[str] = field(default_factory=list)


def main(argv: list[str]) -> int:
    """Write the architecture map Markdown file."""
    output_path = _parse_output_path(argv)
    if output_path is None:
        return 1

    project_root = Path(__file__).resolve().parents[1]
    src_root = project_root / _SRC_ROOT

    event_registry = _build_event_registry(src_root)
    modules = _collect_marked(src_root, _MARKER_MODULE)
    use_cases = _collect_marked(src_root, _MARKER_USE_CASE)

    uc_events = _collect_all_use_case_events(use_cases, src_root, event_registry)
    event_index = _build_event_index(uc_events)

    md = _render(modules, use_cases, src_root, event_registry, uc_events, event_index)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md, encoding="utf-8")
    sys.stdout.write(f"Wrote {output_path}\n")
    return 0


def _parse_output_path(argv: list[str]) -> Path | None:
    if len(argv) not in (1, _ARG_COUNT_WITH_OUTPUT):
        sys.stderr.write("Usage: generate_arch_map.py [output-path]\n")
        return None
    if len(argv) == _ARG_COUNT_WITH_OUTPUT:
        return Path(argv[1]).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / _DEFAULT_OUTPUT


# -- event registry -----------------------------------------------------------


def _build_event_registry(src_root: Path) -> dict[str, str]:
    """Return a mapping of event class name → kind label."""
    registry: dict[str, str] = {}
    event_files = [
        *src_root.glob("shared/events/*.py"),
        *src_root.rglob("_events.py"),
    ]
    for path in event_files:
        registry.update(_extract_event_kinds(path))
    return registry


def _extract_event_kinds(path: Path) -> dict[str, str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return {}
    result: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            base_name = _name_from_node(base)
            if base_name in _KIND_LABELS:
                result[node.name] = _KIND_LABELS[base_name]
                break
    return result


# -- marker collection --------------------------------------------------------


def _collect_marked(src_root: Path, marker: str) -> list[Path]:
    result: list[Path] = []
    for init_file in sorted(src_root.rglob("__init__.py")):
        if _read_marker(init_file) == marker:
            result.append(init_file.parent)
    return result


def _read_marker(init_file: Path) -> str | None:
    try:
        tree = ast.parse(init_file.read_text(encoding="utf-8"), filename=str(init_file))
    except SyntaxError:
        return None
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "__marker__"
            and isinstance(node.value, ast.Constant)
        ):
            return str(node.value.value)
    return None


def _read_docstring(init_file: Path) -> str | None:
    try:
        tree = ast.parse(init_file.read_text(encoding="utf-8"), filename=str(init_file))
    except SyntaxError:
        return None
    return ast.get_docstring(tree)


# -- event extraction ---------------------------------------------------------


def _shell_files(use_case_path: Path) -> list[Path]:
    files: list[Path] = []
    for glob in _SHELL_GLOBS:
        files.extend(use_case_path.glob(glob))
    return sorted(set(files))


def _collect_all_use_case_events(
    use_cases: list[Path], src_root: Path, event_registry: dict[str, str]
) -> dict[str, UseCaseEvents]:
    """Return a mapping of use case package name → UseCaseEvents."""
    return {
        _package_name(uc, src_root): _extract_events(uc, event_registry)
        for uc in use_cases
    }


def _build_event_index(
    uc_events: dict[str, UseCaseEvents],
) -> dict[str, EventIndex]:
    """Return a mapping of event name → EventIndex across all use cases."""
    index: dict[str, EventIndex] = {}
    for uc_pkg, events in uc_events.items():
        for name in events.published:
            index.setdefault(name, EventIndex()).published_by.append(uc_pkg)
        for name in events.listened:
            index.setdefault(name, EventIndex()).listened_by.append(uc_pkg)
    return dict(sorted(index.items()))


def _extract_events(
    use_case_path: Path, event_registry: dict[str, str]
) -> UseCaseEvents:
    """Return listened and published event name lists for a use case.

    Published names are filtered against the event registry to drop unresolved
    function or variable names that leaked through static analysis.
    """
    listened: set[str] = set()
    published: set[str] = set()
    for shell_file in _shell_files(use_case_path):
        try:
            tree = ast.parse(
                shell_file.read_text(encoding="utf-8"), filename=str(shell_file)
            )
        except SyntaxError:
            continue
        listened.update(_extract_listened(tree))
        published.update(_extract_published(tree))
    return UseCaseEvents(
        listened=sorted(listened),
        published=sorted(n for n in published if n in event_registry),
    )


def _extract_listened(tree: ast.Module) -> list[str]:
    """Extract event names from subscription return tuples.

    Looks for tuple elements of the form (EventClass, handler) where the
    first element is a Name or Attribute node — the event type being subscribed to.
    """
    names: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Return):
            continue
        for elt in _iter_tuple_elements(node.value):
            if not isinstance(elt, ast.Tuple) or len(elt.elts) < 2:
                continue
            name = _name_from_node(elt.elts[0])
            if name:
                names.append(name)
    return names


def _extract_published(tree: ast.Module) -> list[str]:
    """Extract event names from bus.publish(...) and event_store.append(...) calls.

    Sources:
    - await bus.publish(arg) — direct, helper, variable, or starred
    - await event_store.append(filter, seq, event) — third arg is always the event;
      covers coroutine-assigned variables not resolvable via local_returns.
    """
    local_returns = _build_local_return_index(tree)
    local_variables = _build_local_variable_index(tree)
    names: list[str] = []
    for node in ast.walk(tree):
        call = _unwrap_await(node)
        if call is None:
            continue
        if _is_bus_publish(call):
            for arg in call.args:
                names.extend(_resolve_publish_arg(arg, local_returns, local_variables))
        elif _is_event_store_append(call):
            names.extend(
                _resolve_event_store_append(call, local_returns, local_variables)
            )
    return names


def _is_event_store_append(call: ast.Call) -> bool:
    func = call.func
    if not (
        isinstance(func, ast.Attribute)
        and func.attr == "append"
        and len(call.args) >= 3
    ):
        return False
    # Check for event_store.append(...) at module level
    if isinstance(func.value, ast.Name) and func.value.id == "event_store":
        return True
    # Check for self._event_store.append(...) at method level
    if isinstance(func.value, ast.Attribute) and func.value.attr == "_event_store":
        if isinstance(func.value.value, ast.Name) and func.value.value.id == "self":
            return True
    return False


def _resolve_event_store_append(
    call: ast.Call,
    local_returns: dict[str, list[str]],
    local_variables: dict[str, list[str]],
) -> list[str]:
    """Extract the event from event_store.append(filter, seq, event)."""
    return _resolve_publish_arg(call.args[2], local_returns, local_variables)


def _build_local_return_index(tree: ast.Module) -> dict[str, list[str]]:
    """Return a mapping of function name → list of returned class names.

    Collects all return statements in the function body, covering both
    single-return helpers and multi-branch match/if helpers.
    When a return is `tuple(f(...) for ...)`, recurses into f's returns.

    Uses two passes to handle forward references: first pass collects direct
    class names, second pass resolves helper function calls.
    """
    # First pass: collect direct class names and helper calls (unresolved)
    unresolved: dict[str, list[str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        names = []
        for ret in ast.walk(node):
            if isinstance(ret, ast.Return) and ret.value is not None:
                name = _class_name_from_call(ret.value)
                if name:
                    names.append(name)
        if names:
            unresolved[node.name] = names

    # Second pass: resolve helper calls using the complete unresolved index
    index: dict[str, list[str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        names = [
            resolved
            for ret in ast.walk(node)
            if isinstance(ret, ast.Return)
            for resolved in _resolve_return_value(ret.value, unresolved)
        ]
        if names:
            index[node.name] = names
    return index


def _resolve_return_value(
    node: ast.expr | None, index: dict[str, list[str]]
) -> list[str]:
    """Resolve a return value node to a list of event class names.

    Handles:
    - SomeEvent(...) — direct construction
    - tuple(f(...) for ...) — unwraps the generator's inner call via index
    """
    if node is None:
        return []
    name = _class_name_from_call(node)
    if name is None:
        return []
    if name != "tuple":
        return [name]
    # tuple(inner_call(...) for ...) — unwrap the generator
    assert isinstance(node, ast.Call)
    if not node.args or not isinstance(node.args[0], ast.GeneratorExp):
        return []
    elt: ast.expr = node.args[0].elt
    inner_name = _class_name_from_call(elt)
    if inner_name is None:
        return []
    return index.get(inner_name, [])


def _build_local_variable_index(tree: ast.Module) -> dict[str, list[str]]:
    """Return a mapping of variable name → event class names for file-local assignments.

    Covers:
      var = _helper(...)         (ast.Assign)
      var: Type = _helper(...)   (ast.AnnAssign)
      var = await _coro(...)     (ast.Assign with Await)
    Resolves through local_returns, collecting all possible returned types.
    """
    local_returns = _build_local_return_index(tree)
    index: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            resolved = _resolve_call_or_await(node.value, local_returns)
            if resolved:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        index[target.id] = resolved
        elif isinstance(node, ast.AnnAssign):
            resolved = _resolve_call_or_await(node.value, local_returns)
            if resolved:
                if isinstance(node.target, ast.Name):
                    index[node.target.id] = resolved
    return index


def _resolve_call_or_await(
    node: ast.expr | None, local_returns: dict[str, list[str]]
) -> list[str]:
    """Resolve a call or awaited call to a list of event class names."""
    if node is None:
        return []
    inner = node.value if isinstance(node, ast.Await) else node
    name = _class_name_from_call(inner)
    if name is None:
        return []
    return local_returns.get(name, [name])


def _resolve_publish_arg(
    node: ast.expr,
    local_returns: dict[str, list[str]],
    local_variables: dict[str, list[str]],
) -> list[str]:
    """Resolve a bus.publish() argument to event class names.

    Handles:
    - Direct construction: SomeEvent(...)
    - Helper call: _to_something(...)
    - Variable: domain_event assigned from a helper or coroutine
    - Starred variable: *coordination unpacked from a helper
    """
    if isinstance(node, ast.Starred):
        inner = node.value
        if isinstance(inner, ast.Name):
            return local_variables.get(inner.id, [])
        name = _class_name_from_call(inner)
        if name:
            return local_returns.get(name, [name])
        return []
    if isinstance(node, ast.Name):
        return local_variables.get(node.id, [])
    name = _class_name_from_call(node)
    if name is None:
        return []
    return local_returns.get(name, [name])


def _iter_tuple_elements(node: ast.expr | None) -> list[ast.expr]:
    if isinstance(node, ast.Tuple):
        return list(node.elts)
    return []


def _unwrap_await(node: ast.AST) -> ast.Call | None:
    if isinstance(node, ast.Await) and isinstance(node.value, ast.Call):
        return node.value
    if isinstance(node, ast.Call):
        return node
    return None


def _is_bus_publish(call: ast.Call) -> bool:
    func = call.func
    if not (isinstance(func, ast.Attribute) and func.attr == "publish"):
        return False
    # Check for bus.publish(...) at module level
    if isinstance(func.value, ast.Name) and func.value.id == "bus":
        return True
    # Check for self._bus.publish(...) at method level
    if isinstance(func.value, ast.Attribute) and func.value.attr == "_bus":
        if isinstance(func.value.value, ast.Name) and func.value.value.id == "self":
            return True
    return False


def _class_name_from_call(node: ast.expr) -> str | None:
    if isinstance(node, ast.Call):
        return _name_from_node(node.func)
    return None


def _name_from_node(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


# -- rendering ----------------------------------------------------------------


def _package_name(path: Path, src_root: Path) -> str:
    return path.relative_to(src_root).as_posix().replace("/", ".")


def _format_event_line(name: str, registry: dict[str, str]) -> str:
    kind = registry.get(name)
    return f"    - `{name}` ({kind})" if kind else f"    - `{name}`"


def _render_use_case(
    uc_path: Path,
    src_root: Path,
    event_registry: dict[str, str],
    uc_events: dict[str, UseCaseEvents],
) -> list[str]:
    uc_pkg = _package_name(uc_path, src_root)
    uc_doc = _read_docstring(uc_path / "__init__.py")
    events = uc_events[uc_pkg]
    lines = [f"- `{uc_pkg}`" + (f" — {uc_doc}" if uc_doc else "")]
    if events.listened:
        lines.append("  - **listens:**")
        lines.extend(_format_event_line(e, event_registry) for e in events.listened)
    if events.published:
        lines.append("  - **publishes:**")
        lines.extend(_format_event_line(e, event_registry) for e in events.published)
    return lines


def _render_event_index(
    event_index: dict[str, EventIndex],
    event_registry: dict[str, str],
) -> list[str]:
    kind_order = ["integration", "domain", "coordination"]
    kind_titles = {
        "integration": "Integration Events",
        "domain": "Domain Events",
        "coordination": "Coordination Events",
    }
    by_kind: dict[str, list[tuple[str, EventIndex]]] = {k: [] for k in kind_order}
    unknown: list[tuple[str, EventIndex]] = []
    for name, idx in event_index.items():
        kind = event_registry.get(name)
        if kind in by_kind:
            by_kind[kind].append((name, idx))
        else:
            unknown.append((name, idx))

    lines = ["## Event Index", ""]
    groups = [(kind_titles[k], by_kind[k]) for k in kind_order if by_kind[k]]
    if unknown:
        groups.append(("Unknown", unknown))
    for title, entries in groups:
        lines += [f"### {title}", ""]
        for name, idx in entries:
            lines.append(f"#### `{name}`")
            lines.append("")
            if idx.published_by:
                lines.append("- **published by:**")
                lines.extend(f"  - `{uc}`" for uc in sorted(idx.published_by))
            if idx.listened_by:
                lines.append("- **listened by:**")
                lines.extend(f"  - `{uc}`" for uc in sorted(idx.listened_by))
            lines.append("")
    return lines


def _render(
    modules: list[Path],
    use_cases: list[Path],
    src_root: Path,
    event_registry: dict[str, str],
    uc_events: dict[str, UseCaseEvents],
    event_index: dict[str, EventIndex],
) -> str:
    lines: list[str] = [
        "# Architecture Map",
        "",
        "Generated from `__marker__` annotations in `src/tic/`.",
        "",
        "## Modules",
        "",
    ]

    for mod_path in modules:
        pkg = _package_name(mod_path, src_root)
        doc = _read_docstring(mod_path / "__init__.py")
        lines.append(f"### `{pkg}`")
        lines.append("")
        if doc:
            lines.append(doc)
            lines.append("")
        mod_use_cases = [uc for uc in use_cases if _is_child(uc, mod_path)]
        if mod_use_cases:
            lines.append("**Use cases:**")
            lines.append("")
            for uc_path in mod_use_cases:
                lines.extend(
                    _render_use_case(uc_path, src_root, event_registry, uc_events)
                )
            lines.append("")

    orphan_use_cases = [
        uc for uc in use_cases if not any(_is_child(uc, m) for m in modules)
    ]
    if orphan_use_cases:
        lines += ["## Unattached Use Cases", ""]
        for uc_path in orphan_use_cases:
            lines.extend(_render_use_case(uc_path, src_root, event_registry, uc_events))
        lines.append("")

    lines += _render_event_index(event_index, event_registry)

    return "\n".join(lines)


def _is_child(candidate: Path, parent: Path) -> bool:
    return candidate != parent and candidate.is_relative_to(parent)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
