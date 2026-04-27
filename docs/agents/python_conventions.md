# Python Conventions

Python-specific conventions for this project. Treat this as the authoritative reference for Python idioms and practices. For language-agnostic guidance, see `docs/coding_conventions.md`.

## Python Version

- The supported Python version must be documented in `pyproject.toml`. Always write code targeting that version.

## Typing & Structures

- Prefer explicit typing for public APIs and module boundaries; use `Protocol` or ABCs where appropriate.
- Use dataclasses or `NamedTuple` for simple immutable data carriers when they improve clarity.
- Use PEP 695 native type parameter syntax (`class Foo[T]:`) — do not use `Generic[T]` subclassing or `TypeVar` declarations.

## Dependency Rule

- Minimise direct third-party dependencies in core/domain modules. They should depend only on the standard library and small, stable, purpose-specific utilities where strictly necessary.
- When a domain module needs functionality provided by an external library (I/O, persistence, external APIs), define an explicit interface (`Protocol` or ABC) in the domain or application layer and provide the concrete implementation in an infrastructure or adapters module.
- Inject concrete implementations at runtime via dependency injection or explicit factory wiring. Do not import infrastructure implementations directly from domain modules.
- Document any exception in the PR and explain why the dependency is necessary at that layer.

## Linting & Formatting

- Use ruff for both linting and formatting. Configure it in `pyproject.toml` and run it as part of the developer workflow and CI.
- Default line length: 88 characters.

## Docstrings & Comments

- Document public modules, classes, and functions with docstrings. Adopt a consistent style (Google-style, NumPy-style, or reStructuredText) and document the chosen style in the contributor guide.
- Default line length: 88 characters.

## Encoding & I/O

- Always specify `encoding="utf-8"` when opening files.
- When invoking subprocesses with text output, handle encoding explicitly.

## Method Ordering Within a Class

Order methods so a reader encounters intent before implementation detail:

1. `__init__`
2. Public methods and properties
3. Abstract methods (subclass contract)
4. Protected / private methods (`_` prefix)
5. Other dunder methods (`__str__`, `__repr__`, `__eq__`, …)

`@classmethod`, `@staticmethod`, and `@abstractmethod` are orthogonal to this order — they modify a method within its visibility group, they do not determine its position.

Not linter-enforceable by ruff. Compliance is by discipline; flag violations in code review.

## Function Ordering

- Follows the general rule in `docs/coding_conventions.md`.
- Not linter-enforceable by ruff. Compliance is by discipline; flag violations in code review.

## Function Shape

- Prefer expression-style return chains when they remain easy to read.
- If a one-liner becomes unclear, use a single local assignment before `return`.
- Avoid nested `def` declarations inside functions in production code; extract a private helper instead.

Why this matters:

- Nested local functions increase indentation and hide behavior in local scope.
- One-assignment-or-one-liner returns keep functions predictable and easy to debug.
- Helper extraction improves reuse and makes tests target explicit units.

## Prefer Private by Default

- Follows the general rule in `docs/coding_conventions.md`.
- Use a `_` prefix for private functions, methods, and module-level names.
- Control the public surface of a module explicitly via `__all__`; names absent from `__all__` are considered internal even if not prefixed.

## Testing

- Follows the general rules in `docs/coding_conventions.md`.
- Test files live under the top-level `tests/` directory and mirror the module layout.

## Exceptions

- Any exception to these conventions must be documented in the PR and approved by reviewers.

## References

- Language-agnostic conventions: `docs/coding_conventions.md`
