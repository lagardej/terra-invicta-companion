"""Context for command handlers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandContext[StateT]:
    """Context loaded by the shell and passed to a command handler."""

    state: StateT | None = None
