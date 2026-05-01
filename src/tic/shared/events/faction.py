"""Events related to factions."""

from dataclasses import dataclass
from datetime import datetime

from tic.shared.events.base import IntegrationEvent


@dataclass(frozen=True)
class FactionDataExtracted(IntegrationEvent):
    """Emitted when faction data was extracted from a savefile."""

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
        return "faction.data_extracted"


@dataclass(frozen=True)
class Resources:
    """Resources bag."""

    antimatter: float
    boost: float
    exotics: float
    fissiles: float
    influence: float
    metals: float
    mission_control: float
    money: float
    noble_metals: float
    operations: float
    volatiles: float
    water: float
