"""Degree-day (Gradtagszahlen) apportionment.

When a renter changes mid-period without an interim reading, the unit's
heating consumption is apportioned across the occupancy segments by monthly
degree-day promille (partial months pro-rated by day). Warm water and base
costs are NOT weather-dependent — they are apportioned by days instead.
"""

import calendar
from datetime import date, timedelta
from decimal import Decimal

from lokara_domain import DegreeDayTable, Segment


def degree_day_weight(start: date, days: int, table: DegreeDayTable) -> Decimal:
    """Promille weight of the range [start, start + days): the sum over
    calendar months of promille × covered_days / days_in_month. Exact for
    whole-month coverage."""
    end = start + timedelta(days=days)
    weight = Decimal(0)
    cursor = start
    while cursor < end:
        month_days = calendar.monthrange(cursor.year, cursor.month)[1]
        month_start = cursor.replace(day=1)
        next_month = (month_start + timedelta(days=month_days)).replace(day=1)
        covered = (min(end, next_month) - cursor).days
        promille = table.promille_by_month[cursor.month - 1]
        if covered == month_days:
            weight += Decimal(promille)
        else:
            weight += Decimal(promille) * Decimal(covered) / Decimal(month_days)
        cursor = min(end, next_month)
    return weight


def segment_degree_day_weights(
    segments: tuple[Segment, ...], table: DegreeDayTable
) -> list[Decimal]:
    return [degree_day_weight(s.start, s.days, table) for s in segments]
