"""Occupancy timelines.

Builds the per-unit party segments both engines allocate over: tenancy rows
(and explicit landlord/self-use rows) are clipped to the billing window,
overlaps are rejected (a day may never be both RENTED and SELF_USED — docs/02),
and uncovered gaps are derived as landlord (vacancy) segments. Vacancy is never
stored — it is always the remainder.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
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
    """Two occupancy rows claim the same day of one unit — a hard block.

    `docs/02` § 5: "overlapping tenancies in one unit block before calculation
    or rendering." The block alone is not enough for a statement: a landlord
    told only *that* an overlap exists cannot find the days in a lease file, so
    the error carries the over-allocated Bemessung as structured attributes and
    the statement layer prints them.

    The weights are expressed in the **applied key's printed unit** — m²·Tage,
    Personen·Tage or Einheiten·Tage — which is why the names are key-neutral.
    This module is key-agnostic on purpose (a timeline builder must not learn
    about allocation keys), so it raises in Einheiten·Tage: ``key_value`` is 1
    day-weight per day. The caller that knows the cost's key and the unit's
    de-scaled key value re-raises through :meth:`rescaled`, which is where
    `docs/08` "Reference totals" ÷100 / ÷10000 de-scaling is applied — once.

    * ``available_weight`` — what the unit has to give in the window.
    * ``allocated_weight`` — what the rows together claim.
    * ``overallocated_weight`` — the overlap itself, the part claimed twice.

    ``allocated - available`` is *not* the same figure whenever the unit also
    has uncovered (vacancy) days, so the overlap is measured directly.
    """

    def __init__(
        self,
        unit_id: str,
        day: date,
        *,
        overlap_days: int,
        available_days: int,
        allocated_days: int,
        key_value: Decimal = Decimal(1),
    ) -> None:
        self.unit_id = unit_id
        self.day = day
        self.overlap_days = overlap_days
        self.available_days = available_days
        self.allocated_days = allocated_days
        self.key_value = key_value
        self.available_weight = key_value * available_days
        self.allocated_weight = key_value * allocated_days
        self.overallocated_weight = key_value * overlap_days
        super().__init__(
            f"Unit {unit_id} has overlapping occupancies at {day.isoformat()}: "
            f"{allocated_days} days allocated against {available_days} available, "
            f"{overlap_days} of them twice"
        )

    def rescaled(self, key_value: Decimal) -> "OccupancyOverlapError":
        """The same block, restated in the applied key's printed unit.

        A new error rather than a mutated one: the raised value is evidence a
        statement prints, and evidence that can be edited after the fact is not
        evidence (`CLAUDE.md` § 3.2).
        """
        return OccupancyOverlapError(
            self.unit_id,
            self.day,
            overlap_days=self.overlap_days,
            available_days=self.available_days,
            allocated_days=self.allocated_days,
            key_value=key_value,
        )


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
    # Every overlapping pair is measured, not just the first one found: the
    # block has to state how much was claimed twice (docs/02 § 5), and stopping
    # at the first pair would understate a unit with two bad rows.
    overlap_total = 0
    first_overlap_day: date | None = None
    for (_, prev_end, _), (next_start, next_end, _) in pairwise(clipped):
        if next_start < prev_end:
            overlap_total += (min(prev_end, next_end) - next_start).days
            if first_overlap_day is None:
                first_overlap_day = next_start
    if first_overlap_day is not None:
        raise OccupancyOverlapError(
            unit_id,
            first_overlap_day,
            overlap_days=overlap_total,
            available_days=(window_to - window_from).days,
            allocated_days=sum((end - start).days for start, end, _ in clipped),
        )

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
