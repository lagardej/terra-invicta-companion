"""Epoch-to-datetime conversion for savefile processing."""

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class EpochLike(Protocol):
    """Protocol for epoch-style date/time objects."""

    @property
    def year(self) -> int: ...

    @property
    def month(self) -> int: ...

    @property
    def day(self) -> int: ...

    @property
    def hour(self) -> int: ...

    @property
    def minute(self) -> int: ...

    @property
    def second(self) -> int: ...

    @property
    def millisecond(self) -> int: ...


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
