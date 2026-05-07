"""Domain events for faction updates."""

from dataclasses import dataclass
from datetime import datetime

from tic.shared.events.base import DomainEvent
from tic.shared.models import Resources


@dataclass(frozen=True)
class FactionUpdated(DomainEvent):
    """Emitted when faction data was updated from a savefile."""

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

    @classmethod
    def type(cls) -> str:
        """Return the unique string identifier for this message type."""
        return "faction.data_updated"
