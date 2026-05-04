"""Faction update use case — functional core, no I/O."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from tic.faction.update.events import FactionUpdated
from tic.shared.command import CommandContext, CommandHandler
from tic.shared.log_call import log_call
from tic.shared.models import Resources


@dataclass(frozen=True)
class UpdateFaction:
    """Command to update a faction from extracted savefile data."""

    id: int
    abductions: int
    armies: tuple[int, ...]
    atrocities: int
    councilors: tuple[int, ...]
    current_date_time: datetime
    fleets: tuple[int, ...]
    is_ai: bool
    mission_control_usage: int
    template_name: str
    resources: Resources


@dataclass(frozen=True)
class FactionState:
    """Reconstructed state for idempotency checking."""

    current_date_time: datetime | None


class UpdateFactionHandler(CommandHandler[UpdateFaction, FactionUpdated, FactionState]):
    """Produces a FactionUpdated domain event from an UpdateFaction command."""

    @log_call()
    async def handle(
        self,
        command: UpdateFaction,
        context: CommandContext[FactionState],
    ) -> FactionUpdated:
        """Map the command payload to a FactionUpdated domain event."""
        return _to_updated(command)


def _to_updated(command: UpdateFaction) -> FactionUpdated:
    return FactionUpdated(
        id=command.id,
        abductions=command.abductions,
        armies=command.armies,
        atrocities=command.atrocities,
        councilors=command.councilors,
        current_date_time=command.current_date_time,
        fleets=command.fleets,
        is_ai=command.is_ai,
        mission_control_usage=command.mission_control_usage,
        template_name=command.template_name,
        resources=command.resources,
    )
