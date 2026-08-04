"""Normalized heating-engine inputs/outputs.

Plain frozen dataclasses; every legal ratio/table arrives as a resolved rule
value (lokara-domain shapes) — the engine never hardcodes a legal number.
"""

from dataclasses import dataclass
from decimal import Decimal

from lokara_domain import (
    Cents,
    Co2Table,
    DegreeDayTable,
    HeatingSplitBounds,
    Occupancy,
    Period,
    WarmWaterFormula,
)


@dataclass(frozen=True)
class HeatingUnit:
    unit_id: str
    area_sqm_x100: int
    # Measured heating consumption (heat-meter units). None → §9a estimation.
    heat_consumption: Decimal | None
    # Measured warm-water volume (m³). None → §9a estimation (if WW exists).
    ww_consumption_m3: Decimal | None = None


@dataclass(frozen=True)
class WarmWaterInput:
    """Central warm water exists. volume_m3=None → § 9 Abs. 2 area fallback."""

    volume_m3: Decimal | None


@dataclass(frozen=True)
class Co2Input:
    total_co2_kg: Decimal
    co2_cost: Cents


@dataclass(frozen=True)
class HeatingRules:
    """Resolved rule values (from lokara-rules-store, as of the law date)."""

    consumption_share: Decimal
    split_bounds: HeatingSplitBounds
    warm_water_formula: WarmWaterFormula
    degree_days: DegreeDayTable
    co2_table: Co2Table | None = None
    co2_rechtsstand: str | None = None


@dataclass(frozen=True)
class HeatingInput:
    billing_period: Period
    # Total cost of the heating system incl. warm-water generation.
    total_cost: Cents
    # Fuel energy content over the period (kWh) — denominator for § 9.
    total_energy_kwh: Decimal
    units: tuple[HeatingUnit, ...]
    occupancies: tuple[Occupancy, ...]
    rules: HeatingRules
    warm_water: WarmWaterInput | None = None
    co2: Co2Input | None = None


@dataclass(frozen=True)
class HeatingLine:
    """One party's share. tenancy_id=None → landlord (vacancy/self-use)."""

    unit_id: str
    tenancy_id: str | None
    heating_base: Cents
    heating_consumption: Cents
    ww_base: Cents
    ww_consumption: Cents
    total: Cents


@dataclass(frozen=True)
class Co2Result:
    # kg CO₂/m² **over the Abrechnungszeitraum** — not annualised (§ 7 Abs. 3).
    intensity_kg_per_sqm: Decimal
    # § 5 Abs. 1 S. 4 CO2KostAufG: the factor the Anlage's finite bounds were
    # shortened by. Exactly 1 for a full year. Rendering the gekürzt band needs it.
    period_factor: Decimal
    landlord_share_percent: int
    landlord_amount: Cents
    renter_amount: Cents
    # e.g. "Rechtsstand 01/2023" — must appear on the statement.
    rechtsstand: str


@dataclass(frozen=True)
class HeatingResult:
    lines: tuple[HeatingLine, ...]
    co2: Co2Result | None
    # Units whose missing readings were estimated per § 9a.
    estimated_unit_ids: tuple[str, ...]
    # True when > 25 % of the area lacked readings and the consumption
    # portion was allocated by the fixed (area) key instead (§ 9a Abs. 2).
    consumption_fallback_to_area: bool
    total: Cents


class HeatingInputError(ValueError):
    pass
