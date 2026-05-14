"""Epoch-to-datetime conversion for savefile processing."""

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


def to_datetime(epoch: EpochLike) -> datetime:
    """Convert an epoch-like object to a timezone-aware datetime."""
    return datetime(
        year=epoch.year,
        month=epoch.month,
        day=epoch.day,
        hour=epoch.hour,
        minute=epoch.minute,
        second=epoch.second,
        microsecond=epoch.millisecond * 1000,
        tzinfo=UTC,
    )


@runtime_checkable
class EpochLike(Protocol):
    """Protocol for epoch-style date/time objects."""

    @property
    def year(self) -> int:
        """Return the year component."""
        ...

    @property
    def month(self) -> int:
        """Return the month component (1-12)."""
        ...

    @property
    def day(self) -> int:
        """Return the day of the month component."""
        ...

    @property
    def hour(self) -> int:
        """Return the hour component (0-23)."""
        ...

    @property
    def minute(self) -> int:
        """Return the minute component (0-59)."""
        ...

    @property
    def second(self) -> int:
        """Return the second component (0-59)."""
        ...

    @property
    def millisecond(self) -> int:
        """Return the millisecond component (0-999)."""
        ...


class EpochModel(BaseModel):
    """Pydantic model for validating epoch-like data structures."""

    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    millisecond: int
