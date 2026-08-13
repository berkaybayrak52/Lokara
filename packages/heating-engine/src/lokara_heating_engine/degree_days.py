"""Degree-day (Gradtagszahlen) apportionment.

When a renter changes mid-period without an interim reading, the unit's
heating consumption is apportioned across the occupancy segments by the monthly
degree-day weights (partial months pro-rated by day). Warm water and base
costs are NOT weather-dependent — they are apportioned by days instead.

The table's unit is **Zehntelpromille** (Σ 10 000, K3), so every weight this
module returns is one too: a full year is 10 000, and the printed ‰ figure is
the weight divided by 10. De-scale at the render boundary, never here.
"""

import calendar
from datetime import date, timedelta
from decimal import Decimal

from lokara_domain import DegreeDayTable, Segment


def degree_day_weight(start: date, days: int, table: DegreeDayTable) -> Decimal:
    """Zehntelpromille weight of the range [start, start + days): the sum over
    calendar months of tenth_promille × covered_days / days_in_month. Exact for
    whole-month coverage."""
    end = start + timedelta(days=days)
    weight = Decimal(0)
    cursor = start
    while cursor < end:
        month_days = calendar.monthrange(cursor.year, cursor.month)[1]
        month_start = cursor.replace(day=1)
        next_month = (month_start + timedelta(days=month_days)).replace(day=1)
        covered = (min(end, next_month) - cursor).days
        tenth_promille = table.tenth_promille_by_month[cursor.month - 1]
        if covered == month_days:
            weight += Decimal(tenth_promille)
        else:
            weight += Decimal(tenth_promille) * Decimal(covered) / Decimal(month_days)
        cursor = min(end, next_month)
    return weight


def segment_degree_day_weights(
    segments: tuple[Segment, ...], table: DegreeDayTable
) -> list[Decimal]:
    return [degree_day_weight(s.start, s.days, table) for s in segments]
