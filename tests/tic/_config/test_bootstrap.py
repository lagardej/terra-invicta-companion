"""Application context test — verifies the app boots without error."""

from __future__ import annotations

from pathlib import Path

import pytest

from tic._config.bootstrap import boot
from tic.shared.application import Application


@pytest.fixture(autouse=True)
def _env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    monkeypatch.setenv("TIC_APP_DIR", str(app_dir))
    monkeypatch.setenv("TIC_ENV", "dev")
    monkeypatch.setenv("TIC_LOG_LEVEL", "INFO")
    monkeypatch.setenv("TIC_PORT", "8000")
    monkeypatch.setenv("TIC_WATCH_DIR", str(watch_dir))


def test_context_loads() -> None:
    app = boot()
    assert isinstance(app, Application)
