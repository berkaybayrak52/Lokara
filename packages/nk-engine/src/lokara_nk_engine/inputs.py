"""Normalized NK engine inputs/outputs.

Plain frozen dataclasses — adapters map DB rows to these; no SQLAlchemy or
vendor types ever reach the engine (docs/03 shared engine contract).
"""

from dataclasses import dataclass, field
from decimal import Decimal

from lokara_domain import AllocationKey, Cents, Occupancy, Period


@dataclass(frozen=True)
class UnitBasis:
    unit_id: str
    # Fixed-point m² × 100 (docs/02: areas are integers, never floats).
    area_sqm_x100: int
    # Miteigentumsanteil × 10000, only needed for the MEA key.
    mea_x10000: int | None = None


@dataclass(frozen=True)
class PersonCountPeriod:
    """Temporal person count of a tenancy — a row, never a scalar (docs/02)."""

    tenancy_id: str
    count: int
    period: Period


@dataclass(frozen=True)
class ConsumptionValue:
    """Period-resolved consumption of one party, normalized upstream by the
    meter adapter. tenancy_id=None attributes the value to the landlord."""

    unit_id: str
    tenancy_id: str | None
    value: Decimal


@dataclass(frozen=True)
class CostItem:
    cost_id: str
    label: str
    amount: Cents
    # The key comes from a per-period assignment, never from the cost row
    # itself — re-running with a different key destroys no data (docs/03).
    key: AllocationKey
    direct_unit_id: str | None = None
    direct_tenancy_id: str | None = None


@dataclass(frozen=True)
class NkInput:
    billing_period: Period
    units: tuple[UnitBasis, ...]
    occupancies: tuple[Occupancy, ...]
    costs: tuple[CostItem, ...]
    person_counts: tuple[PersonCountPeriod, ...] = field(default=())
    consumptions: tuple[ConsumptionValue, ...] = field(default=())


@dataclass(frozen=True)
class ShareLine:
    """One allocated share of one cost. tenancy_id=None → landlord side
    (vacancy/self-use). The PDF layer formats these; the engine only computes."""

    cost_id: str
    unit_id: str | None
    tenancy_id: str | None
    weight: Decimal
    amount: Cents


@dataclass(frozen=True)
class NkResult:
    lines: tuple[ShareLine, ...]
    total: Cents


class NkInputError(ValueError):
    pass
