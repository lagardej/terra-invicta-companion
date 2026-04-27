"""Tests for configuration loading."""

from pathlib import Path

import pytest

from tic.config import ConfigurationError, Settings


class TestSettings:
    """Settings loading from environment."""

    def test_missing_watch_dir_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TIC_WATCH_DIR", raising=False)

        with pytest.raises(ConfigurationError, match="TIC_WATCH_DIR"):
            Settings.load()

    def test_empty_watch_dir_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TIC_WATCH_DIR", "")

        with pytest.raises(ConfigurationError, match="TIC_WATCH_DIR"):
            Settings.load()

    def test_watch_dir_tilde_is_expanded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TIC_WATCH_DIR", "~")

        settings = Settings.load()

        assert not str(settings.watch_dir).startswith("~")

    def test_watch_dir_not_a_directory_raises(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("TIC_WATCH_DIR", str(tmp_path / "nonexistent"))

        with pytest.raises(ConfigurationError, match="TIC_WATCH_DIR"):
            Settings.load()

    def test_valid_settings(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("TIC_WATCH_DIR", str(tmp_path))
        monkeypatch.setenv("TIC_PORT", "9000")

        settings = Settings.load()

        assert settings.watch_dir == tmp_path
        assert settings.port == 9000

    def test_default_port(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("TIC_WATCH_DIR", str(tmp_path))
        monkeypatch.delenv("TIC_PORT", raising=False)

        settings = Settings.load()

        assert settings.port == 8000
