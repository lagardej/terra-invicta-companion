[private]
default:
    @just --list

# Run all checks and tests with coverage
[group('ci')]
ci: (check-fmt) (check-lint) (check-type) (test-cov)

#
#
# ── Setup ─────────────────────────────────────────────────────────────────────

# Install all dependencies
[group('setup')]
install:
    @uv venv --prompt "terra-invicta-companion"
    @uv sync --dev
    @uv run -- python -m pre_commit install
    @uv run -- python -m pre_commit install --hook-type pre-push
    @just doctor

# Upgrade all dependencies to latest allowed versions
[group('setup')]
update:
    @uv lock --upgrade
    @uv sync --dev
    @uv run -- python -m pre_commit autoupdate
    @just doctor

# Remove build artifacts, caches, and venv
[arg("venv", long="with-venv", value="true", help="Whether to remove the virtual environment (default: false)")]
[arg("nuke", long="nuke", value="true", help="Also remove venv, uv.lock, and uv cache (default: false)")]
[group('setup')]
clean venv="false" nuke="false":
    #!/usr/bin/env bash
    if [ "{{ nuke }}" = "true" ]; then
        echo "It's the only way to be sure."
        echo "Removing virtual environment..."
        rm -rf .venv
        echo "Removing uv.lock..."
        rm -f uv.lock
        echo "Clearing uv cache..."
        uv cache clean
    elif [ "{{ venv }}" = "true" ]; then
        echo "Removing virtual environment..."
        rm -rf .venv
    fi
    echo "Removing caches and build artifacts..."
    rm -rf .ruff_cache .pytest_cache dist build mutants
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type d -name ".pytest_cache" -exec rm -rf {} +
    find . -type d -name "htmlcov" -exec rm -rf {} +
    find . -name "*.pyc" -delete
    find . -name ".coverage" -delete

# Show toolchain versions for quick troubleshooting
[group('setup')]
doctor:
    @echo "$(just --version)"
    @echo "$(uv --version)"
    @echo "$(uv run -- python --version)"
    @echo "$(uv run -- pyright --version)"
    @echo "$(uv run -- pytest --version)"
    @echo "$(uv run -- ruff --version)"

# Check for outdated dependencies
[group('setup')]
deps-check:
    @uv run -- pip list --outdated

#
#
# ── Check ─────────────────────────────────────────────────────────────────────

# Ruff format check (no writes)
[group('check')]
check-fmt:
    uv run ruff format --check .

# Ruff lint check
[group('check')]
check-lint:
    uv run ruff check .

# Pyright type checking
[group('check')]
check-type:
    uv run pyright .

#
#
# ── Test ──────────────────────────────────────────────────────────────────────

# Run tests
[group('test')]
test *args="":
    uv run pytest {{ args }}

# Run tests with coverage
[group('test')]
test-cov *args="":
    uv run pytest --cov {{ args }}

# Run mutation tests (pytest-gremlins)
[group('test')]
test-gremlins *args="":
    uv run pytest --gremlins --gremlins-html-dir build/reports/pytest-gremlins {{ args }}

# Generate reports index; pass --open to open in browser
[group('test')]
reports open="":
    uv run python -m abcdef.site {{ if open == "--open" { "--open" } else { "" } }}

# Run tests in watch mode
[group('test')]
test-watch *args="":
    uv run ptw . -- {{ args }}

#
#
# ── Fix ───────────────────────────────────────────────────────────────────────

# Ruff lint autofix
[group('fix')]
fix:
    uv run ruff check --fix .

# Ruff format
[group('fix')]
fmt:
    uv run ruff format .

# Autofix lint and format issues
[group('fix')]
autofix: (fix) (fmt)

# Generate the site/index using scripts/generate_index.py
[group('scripts')]
gen-index *args="":
    uv run python scripts/generate_index.py {{ args }}

# Validate a savefile against the Pydantic schema and report model errors
[group('scripts')]
validate-save *args:
    uv run python scripts/validate_savefile.py {{ args }}
