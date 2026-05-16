"""Events related to factions."""

from dataclasses import dataclass
from datetime import datetime

from framework.events import IntegrationEvent
from tic.shared.models import Resources


@dataclass(frozen=True)
class FactionDataExtracted(IntegrationEvent):
    """Emitted when faction data was extracted from a savefile."""

    abductions: int
    armies: tuple[int, ...]
    atrocities: int
    campaign_id: int
    councilors: tuple[int, ...]
    current_date_time: datetime
    fleets: tuple[int, ...]
    id: int
    is_ai: bool
    mission_control_usage: int
    resources: Resources
    template_name: str
