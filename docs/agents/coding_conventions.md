# Coding Conventions

Language-agnostic conventions, style expectations, and development practices. Map this guidance to the project's chosen language(s) and tools.

> These conventions are guidelines. When the technology or context requires deviation, document the exception and the rationale in the change set or PR.

## Purpose

- Provide a consistent baseline for code quality, readability, and maintainability across modules and languages.
- Document expectations for tests, commits, formatting, and dependency usage.

## Function and Method Design

- **One instruction per body:** each line in a function or method body should express a single intent. Multi-line construction or mapping inline is a violation — extract it to a named private helper.
- **Mapping boilerplate at the call site:** object mapping helpers live close to the code that uses them, not on the source or target type. The call site stays a one-liner; the mapping detail lives in the helper.
- **No nested local functions by default:** avoid defining functions inside functions in production code. Prefer a private helper at module/class scope to keep code linear and discoverable.
- **Return-shape preference:** prefer chain-style one-liner returns when readability stays high. Otherwise use at most one local assignment before the return.

Why these rules:

- They reduce the "arrow" effect caused by deeply nested blocks and callbacks.
- They keep control flow easy to scan from top to bottom.
- They make code review and refactoring safer by limiting hidden scope and side effects.

## Function Ordering

- **Read-order:** define functions in the order a reader encounters them — high-level, public-facing functions first, the helpers they delegate to after. A reader should understand intent before seeing implementation details.
- **Cohesion over strict public/private split:** group functions by concept. Keep a public function and its private helpers adjacent rather than separating them into distant public and private blocks.

## Prefer Private by Default

- Default to private visibility for any new function unless there is an immediate, concrete reason for it to be public.
- It is easy to make a private function public later; making a public function private is a breaking change for any caller.
- A minimal public surface reduces cognitive load, eases refactoring, and keeps module contracts explicit.

## Key Principles

- Clarity over cleverness: prefer simple, explicit code that is easy to read and reason about.
- Small functions and modules: each function or module should have a single responsibility.
- Encapsulation: modules should expose a clear, minimal public API and hide internal details.
- Minimise cross-module coupling: prefer well-defined interfaces or abstractions for interactions between modules.

## Style & Formatting

- Adopt the project's chosen formatter and linter. Configure and run them as part of the development workflow and CI.
- Use a consistent maximum line length agreed by the team.
- Use a consistent comment and documentation style appropriate for the language. Document public APIs.

## Typing and Interfaces

- Where the language supports static or optional typing, prefer explicit types or interfaces for public APIs.
- Define language-appropriate interfaces or abstract types for dependencies that cross module boundaries.

## Testing

- Follow test-first development: Red, Green, Refactor.
- Write tests before production code. Start with a failing test (Red), implement the minimal change to make it pass (Green), then improve design while keeping tests green (Refactor).
- Tests should be clear, deterministic, and focused on behaviour rather than implementation details.
- Structure tests in three phases: Arrange, Act, Assert. Separate phases with an empty line; do not add `Arrange/Act/Assert` comments unless a reviewer asks for them.
- Keep assertions minimal. Ideally, each test has one assert. When checking multiple related fields, prefer asserting a full value/object/tuple in one statement instead of many separate asserts.
- Locate tests in a dedicated top-level `tests/` area or the language-appropriate equivalent; mirror module structure where practical.
- Tests should not rely on private internals of modules; prefer testing through public interfaces.
- Prefer automated tests that run quickly. Use integration tests sparingly and clearly distinguish them from unit tests.

## Commit Messages & Reviews

- Use a consistent commit message format (for example, Conventional Commits)and keep messages focused and actionable.
- Include a descriptive PR title and summary explaining motivation, key changes, and any migration or upgrade notes.
- Keep review comments specific and constructive; capture important decisions in the PR description or linked issue.

## Encoding & I/O

- Treat UTF-8 as the canonical encoding for text content. Specify encoding explicitly when reading or writing files if the platform or language requires it.
- Be defensive when parsing external or user-generated data: validate inputs and fail gracefully.

## Exceptions

- If a rule must be broken for a good reason, document the exception in the change and get explicit approval from the reviewer.

## References

- Python-specific conventions: `docs/python_conventions.md`
