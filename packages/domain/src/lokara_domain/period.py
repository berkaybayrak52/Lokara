"""Temporal validity ranges.

A Period is a half-open range [valid_from, valid_to); valid_to=None means
open-ended ("still valid"). Dates are date-only; day counting is calendar-day
based. Anything that changes during a billing period is a row with such a
range, never a scalar (docs/02).
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Period:
    valid_from: date
    valid_to: date | None

    def __post_init__(self) -> None:
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError(
                f"Period valid_to ({self.valid_to}) must be after valid_from ({self.valid_from})"
            )


def period(valid_from_iso: str, valid_to_iso: str | None = None) -> Period:
    valid_from = date.fromisoformat(valid_from_iso)
    valid_to = date.fromisoformat(valid_to_iso) if valid_to_iso else None
    return Period(valid_from=valid_from, valid_to=valid_to)


def days_between(start: date, end: date) -> int:
    """Number of days in the half-open range [start, end)."""
    return (end - start).days


def overlap_days(p: Period, window_from: date, window_to: date) -> int:
    """Days a period overlaps a billing window [window_from, window_to)."""
    start = max(p.valid_from, window_from)
    end = window_to if p.valid_to is None else min(p.valid_to, window_to)
    if end <= start:
        return 0
    return (end - start).days


def periods_overlap(a: Period, b: Period) -> bool:
    """True if two periods share at least one day (used to reject RENTED/SELF_USED overlaps)."""
    a_starts_before_b_ends = b.valid_to is None or a.valid_from < b.valid_to
    b_starts_before_a_ends = a.valid_to is None or b.valid_from < a.valid_to
    return a_starts_before_b_ends and b_starts_before_a_ends
