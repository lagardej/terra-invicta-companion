# Terra Invicta Companion

A personal companion tool for [Terra Invicta](https://store.steampowered.com/app/1176470/Terra_Invicta/) and a learning project for AI-assisted development.

## Project Goals

- The developer makes all architecture, design, and feature decisions.
- AI agents generate implementations, refactors, and documentation under human oversight.
- The workflow is the product as much as the code: Red-Green-Refactor, scoped agents, enforced boundaries.

## Tech Stack

- **Language:** Python 3.14
- **Package manager:** uv
- **Task runner:** just
- **Linting/formatting:** ruff, pyright
- **Testing:** pytest

## Testing Strategy

- The completed reference slice is the `savefile` module, especially the `list` and `process` use cases.
- For a completed FCIS use case, use at most three test modules: `test_e2e.py`, `test_shell.py`, and `test_core.py`.
- `test_e2e.py` is optional and uses the e2e profile with real persistence and real wiring.
- `test_shell.py` is the default use-case test. It uses the integration profile with in-memory adapters and a fake core, and asserts command mapping, state loading, persistence, and published messages.
- `test_core.py` is optional and stays narrow: unit tests only at the public core boundary, never for helpers or private internals.
- Default class split inside each module is `TestSuccessPath` and `TestFailures`. Skip a class only when that branch is not meaningful at that boundary.
- Use `integration` for shell tests, `unit` for core boundary tests, and `e2e` only for real external infrastructure.
- Do not use the current `faction` module as the template yet; it is still work in progress.
