"""Occupancy timelines.

Builds the per-unit party segments both engines allocate over: tenancy rows
(and explicit landlord/self-use rows) are clipped to the billing window,
overlaps are rejected (a day may never be both RENTED and SELF_USED — docs/02),
and uncovered gaps are derived as landlord (vacancy) segments. Vacancy is never
stored — it is always the remainder.
"""

from dataclasses import dataclass
from datetime import date
from itertools import pairwise

from .period import Period, overlap_days


@dataclass(frozen=True)
class Occupancy:
    """One temporal occupancy row for a unit.

    tenancy_id=None marks an explicit landlord-side row (self-use). Vacancy is
    never passed in — the timeline builder derives it from the gaps.
    """

    unit_id: str
    tenancy_id: str | None
    period: Period


@dataclass(frozen=True)
class Segment:
    """A contiguous occupancy slice of a unit inside the billing window."""

    tenancy_id: str | None  # None → landlord (vacancy or self-use)
    start: date
    days: int


class OccupancyOverlapError(ValueError):
    def __init__(self, unit_id: str, day: date) -> None:
        super().__init__(f"Unit {unit_id} has overlapping occupancies at {day.isoformat()}")


def build_unit_segments(
    unit_id: str,
    occupancies: tuple[Occupancy, ...],
    window_from: date,
    window_to: date,
) -> tuple[Segment, ...]:
    """Clips a unit's occupancy rows to [window_from, window_to), rejects
    overlaps, and fills uncovered gaps with landlord (vacancy) segments.

    Segments come back in chronological order; deterministic ordering matters
    because largest-remainder tie-breaks go to the lowest index.
    """
    rows = [o for o in occupancies if o.unit_id == unit_id]
    clipped: list[tuple[date, date, str | None]] = []
    for row in rows:
        days = overlap_days(row.period, window_from, window_to)
        if days == 0:
            continue
        start = max(row.period.valid_from, window_from)
        end = window_to if row.period.valid_to is None else min(row.period.valid_to, window_to)
        clipped.append((start, end, row.tenancy_id))

    clipped.sort(key=lambda c: c[0])
    for (_, prev_end, _), (next_start, _, _) in pairwise(clipped):
        if next_start < prev_end:
            raise OccupancyOverlapError(unit_id, next_start)

    segments: list[Segment] = []
    cursor = window_from
    for start, end, tenancy_id in clipped:
        if start > cursor:
            segments.append(Segment(tenancy_id=None, start=cursor, days=(start - cursor).days))
        segments.append(Segment(tenancy_id=tenancy_id, start=start, days=(end - start).days))
        cursor = end
    if cursor < window_to:
        segments.append(Segment(tenancy_id=None, start=cursor, days=(window_to - cursor).days))
    return tuple(segments)
