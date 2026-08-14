"""Shared value objects: cents, periods, allocation keys, occupancy timelines,
legal rule-value shapes. Pure stdlib — engines and adapters build on this."""

from .allocation_key import AllocationKey
from .energy import (
    EmissionFactor,
    EnergyReference,
    EnergyReferenceMismatchError,
    co2_grams_from_energy,
)
from .legal_values import (
    Co2Step,
    Co2Table,
    DegreeDayTable,
    HeatingSplitBounds,
    WarmWaterFormula,
)
from .meter import (
    CANONICAL_UNITS,
    MeasurementUnit,
    MeterKind,
    ReadingReason,
    ReadingSource,
)
from .money import (
    ZERO_CENTS,
    Cents,
    NonIntegerCentsError,
    add_cents,
    cents,
    distribute_cents,
    distribute_cents_half_up,
    distribute_cents_owner_residual,
    format_eur,
)
from .occupancy import Occupancy, OccupancyOverlapError, Segment, build_unit_segments
from .period import Period, days_between, overlap_days, period, periods_overlap

__version__ = "0.1.0"

__all__ = [
    "CANONICAL_UNITS",
    "ZERO_CENTS",
    "AllocationKey",
    "Cents",
    "Co2Step",
    "Co2Table",
    "DegreeDayTable",
    "EmissionFactor",
    "EnergyReference",
    "EnergyReferenceMismatchError",
    "HeatingSplitBounds",
    "MeasurementUnit",
    "MeterKind",
    "NonIntegerCentsError",
    "Occupancy",
    "OccupancyOverlapError",
    "Period",
    "ReadingReason",
    "ReadingSource",
    "Segment",
    "WarmWaterFormula",
    "add_cents",
    "build_unit_segments",
    "cents",
    "co2_grams_from_energy",
    "days_between",
    "distribute_cents",
    "distribute_cents_half_up",
    "distribute_cents_owner_residual",
    "format_eur",
    "overlap_days",
    "period",
    "periods_overlap",
]
