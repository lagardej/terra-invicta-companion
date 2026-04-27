# AGENTS.md

Read this file at the start of every session. Rules are absolute.

---

## Session start

1. Read this file.
2. Read your instruction file.
3. Read `.tic/<your-role>/SESSION.md` if it exists — resume from it.
4. Read only the files directly needed for the task.

---

## Branch rules

- `main` is protected. No agent commits to `main`. No agent merges into `main`.
- Every feature lives on `feature/<slug>`.
- Agents commit freely on the feature branch.
- Only the human merges into `main`, after `just ci` passes.
- Commit format: `type(scope): description`
  — types: `feat` `fix` `test` `refactor` `docs` `chore`

---

## Development cycle

> BRANCH → DESIGN → TESTS (RED) → IMPLEMENT (GREEN) → REFACTOR → CI → MERGE

- TESTS before IMPLEMENT. Always. No exceptions.
- RED means the tests fail because the code does not exist yet.
- GREEN means the minimum code to pass the tests. Nothing more.
- REFACTOR only when tests are green. No behaviour changes.
- CI (`just ci`) must pass before the human merges.

---

## Justfile recipes

Use `just --list` to view the available recipes. Prefer these recipes over ad-hoc shell commands so the workflow stays consistent across sessions and environments.

- **Default verification:**
  - `just ci` — run format, lint, type checks, and tests with coverage. Use this as the primary verification command before handoff or merge discussion.
- **Check group:**
  - `just check-fmt` — format (check-only);
  - `just check-lint` — Ruff lint check;
  - `just check-type` — Pyright type checks.
- **Fix group:**
  - `just fix` — Ruff autofix;
  - `just fmt` — format code;
  - `just autofix` — convenience group that runs `just fix` then `just fmt`.
- **Test group:**
  - `just test` — run tests;
  - `just test-cov` — run tests with coverage;
  - `just test-gremlins` — run mutation tests (pytest-gremlins);

- When Python-based tooling must be run directly, invoke it through `uv run ...` (the `justfile` recipes already use `uv run` where appropriate).

---

## Coding conventions

Coding conventions and style guidance for agent code and documentation live in the `docs/agents` directory. Follow those conventions for formatting, naming, tests-first workflow, and commit messages when working on agent-related changes.

- Language-agnostic conventions: [docs/agents/coding_conventions.md](docs/agents/coding_conventions.md)
- Python-specific conventions: [docs/agents/python_conventions.md](docs/agents/python_conventions.md)

See those files for full guidance and examples.

## Scratchpad

Each role's scratchpad is split into two areas:

**Workflow files** — at `.tic/<your-role>/`, read by the human and other roles:

- `SESSION.md` — session state, written at the end of every session
- `HANDOFF.md` — output summary for the next role, written when a handoff is needed

**Scratch space** — at `.tic/<your-role>/scratch/`, free-form and private:

- Notes, drafts, intermediate analysis, working files
- Never promoted to tracked files
- Can be wiped at any time without consequence
- Other roles do not rely on anything here

SESSION.md format:

```md
# SESSION — <role> — <YYYY-MM-DD>
## Branch
## Step
## Done
## Next
## Open questions
```

When your output is needed by another role, write `.tic/<your-role>/HANDOFF.md`. The human reads it and routes to the next agent.

---

## Never

- Commit to `main`.
- Merge branches.
- Write outside your write boundary.
- Invent architecture or domain rules — ask first.
- Write implementation before tests exist.
- Add dependencies to `pyproject.toml` without human approval.
- Assume context from a previous session exists — it does not.
- Commit or stage any file under `.tic/` — scratchpad is local-only and always gitignored. Using `git add -f` or `--force` to bypass `.gitignore` is forbidden.
