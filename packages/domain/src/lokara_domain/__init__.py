"""Shared value objects: cents, periods, allocation keys, occupancy timelines,
legal rule-value shapes. Pure stdlib — engines and adapters build on this."""

from .allocation_key import AllocationKey
from .legal_values import (
    Co2Step,
    Co2Table,
    DegreeDayTable,
    HeatingSplitBounds,
    WarmWaterFormula,
)
from .money import (
    ZERO_CENTS,
    Cents,
    NonIntegerCentsError,
    add_cents,
    cents,
    distribute_cents,
    format_eur,
)
from .occupancy import Occupancy, OccupancyOverlapError, Segment, build_unit_segments
from .period import Period, days_between, overlap_days, period, periods_overlap

__version__ = "0.1.0"

__all__ = [
    "ZERO_CENTS",
    "AllocationKey",
    "Cents",
    "Co2Step",
    "Co2Table",
    "DegreeDayTable",
    "HeatingSplitBounds",
    "NonIntegerCentsError",
    "Occupancy",
    "OccupancyOverlapError",
    "Period",
    "Segment",
    "WarmWaterFormula",
    "add_cents",
    "build_unit_segments",
    "cents",
    "days_between",
    "distribute_cents",
    "format_eur",
    "overlap_days",
    "period",
    "periods_overlap",
]
