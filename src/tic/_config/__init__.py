"""Configuration package."""

from tic._config.bootstrap import boot
from tic.shared.settings import ConfigurationError

__all__ = ["boot", "ConfigurationError"]
