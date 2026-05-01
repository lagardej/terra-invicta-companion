"""Validation error returned by scoped savefile processors."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationFailure:
    """Validation error returned by scoped savefile processors."""

    reason: str
