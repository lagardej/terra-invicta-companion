"""Contracts for command handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar

_CommandT = TypeVar("_CommandT", contravariant=True)
_ResultT = TypeVar("_ResultT", covariant=True)
StateT = TypeVar("StateT")


@dataclass(frozen=True)
class CommandContext[StateT]:
    """Context loaded by the shell and passed to a command handler."""

    state: StateT | None = None


class CommandHandler(Protocol[_CommandT, _ResultT, StateT]):
    """Handler contract: handles a command using shell-built context."""

    async def handle(
        self, command: _CommandT, context: CommandContext[StateT]
    ) -> _ResultT:
        """Handle a command using context loaded by the shell."""
        ...
