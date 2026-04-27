"""Domain events."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SavefileChangeDetected:
    """Emitted when a savefile change is detected on disk."""

    path: Path
