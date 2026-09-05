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
    DEVICE_TYPE_FACTS,
    CalibrationDataState,
    ExternalHeatingStatus,
    HeatingBillingMode,
    HeatingCostCategory,
    MeasurementUnit,
    MeterDeviceType,
    MeterKind,
    MeterLifecycleEventType,
    ReadingReason,
    ReadingSource,
    RemoteReadability,
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
from .provenance import RuleConflict, RuleEvidence, SourceIdentity

__version__ = "0.1.0"

__all__ = [
    "CANONICAL_UNITS",
    "DEVICE_TYPE_FACTS",
    "ZERO_CENTS",
    "AllocationKey",
    "CalibrationDataState",
    "Cents",
    "Co2Step",
    "Co2Table",
    "DegreeDayTable",
    "EmissionFactor",
    "EnergyReference",
    "EnergyReferenceMismatchError",
    "ExternalHeatingStatus",
    "HeatingBillingMode",
    "HeatingCostCategory",
    "HeatingSplitBounds",
    "MeasurementUnit",
    "MeterDeviceType",
    "MeterKind",
    "MeterLifecycleEventType",
    "NonIntegerCentsError",
    "Occupancy",
    "OccupancyOverlapError",
    "Period",
    "ReadingReason",
    "ReadingSource",
    "RemoteReadability",
    "RuleConflict",
    "RuleEvidence",
    "Segment",
    "SourceIdentity",
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
