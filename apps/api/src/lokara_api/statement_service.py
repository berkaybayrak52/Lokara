"""Composes the demo statement: DB tenancy rows → both engines → one result.

One occupancy timeline drives every engine (docs/06) — NK and heating read the
same seeded tenancy rows, which is what makes the degree-day split visible on
the statement. Costs and meter totals are still fixture constants: they become
real data when the Kosten-erfassen and Zähler pages land (M3, next slice);
consumptions already flow through the meter adapter port.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from lokara_adapters import MeterGateway, MeterKind, StubMeterGateway
from lokara_db import Building, Unit
from lokara_domain import AllocationKey, Cents, Occupancy, Period, cents
from lokara_heating_engine import (
    Co2Input,
    HeatingInput,
    HeatingResult,
    HeatingRules,
    HeatingUnit,
    WarmWaterInput,
    calculate_heating_statement,
)
from lokara_nk_engine import CostItem, NkInput, NkResult, UnitBasis, calculate_nk_statement
from lokara_pdf import PartyKey, StatementData
from lokara_rules_store import (
    CO2_SPLIT_TABLE,
    DEFAULT_CONSUMPTION_SHARE,
    DEGREE_DAY_TABLE,
    HEATING_SPLIT_BOUNDS,
    WARM_WATER_FORMULA,
    get_rule,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

# The 2025 billing run of the seeded scenario (docs/06 Scenario 1 + 2).
BILLING_START = date(2025, 1, 1)
BILLING_END = date(2026, 1, 1)  # exclusive
BILLING_PERIOD = Period(valid_from=BILLING_START, valid_to=BILLING_END)
PERIOD_LABEL = "01.01.2025 – 31.12.2025"
RULES_AS_OF = date(2025, 12, 31)

# TODO(M3-next): these become entered costs / meter data once the
# Kosten-erfassen and Zähler pages exist.
GARBAGE_COST = CostItem(
    cost_id="cost-garbage",
    label="Müllabfuhr",
    amount=cents(120000),
    key=AllocationKey.AREA,
)
HEATING_TOTAL_COST = cents(1_030_000)  # incl. the €300.00 CO₂ portion
TOTAL_ENERGY_KWH = Decimal(20000)
WARM_WATER_VOLUME_M3 = Decimal(40)
CO2_INPUT = Co2Input(total_co2_kg=Decimal(2000), co2_cost=cents(30000))

ALLOCATION_KEY_LABELS: dict[AllocationKey, str] = {
    AllocationKey.AREA: "Wohnfläche (m²·Tage)",
    AllocationKey.PERSONS: "Personenzahl (Personen·Tage)",
    AllocationKey.CONSUMPTION: "Verbrauch",
    AllocationKey.UNITS: "Einheiten (Einheiten·Tage)",
    AllocationKey.DIRECT: "Direktzuordnung",
    AllocationKey.MEA: "Miteigentumsanteile (MEA·Tage)",
}

# Engine weights are scaled integers; de-scale at the render boundary (docs/03).
WEIGHT_DISPLAY_DIVISORS: dict[AllocationKey, Decimal] = {
    AllocationKey.AREA: Decimal(100),
    AllocationKey.MEA: Decimal(10000),
}


class NoDemoDataError(LookupError):
    """The account holds no seeded building yet."""


@dataclass(frozen=True)
class StatementBundle:
    building: Building
    nk_result: NkResult
    nk_costs: tuple[CostItem, ...]
    heating_result: HeatingResult
    party_labels: dict[PartyKey, str]
    rechtsstaende: tuple[str, ...]


def _party_labels(units: list[Unit]) -> dict[PartyKey, str]:
    labels: dict[PartyKey, str] = {}
    for unit in units:
        labels[(unit.id, None)] = f"{unit.label} — Leerstand → Vermieter"
        for tenancy in unit.tenancies:
            names = ", ".join(party.renter.legal_name for party in tenancy.parties)
            label = f"{unit.label} — {names}"
            if tenancy.valid_to is not None and tenancy.valid_to <= BILLING_END:
                moved_out = tenancy.valid_to - timedelta(days=1)  # valid_to is exclusive
                label += f" (Auszug {moved_out.strftime('%d.%m.%Y')})"
            labels[(unit.id, tenancy.id)] = label
    return labels


def _consumptions(
    gateway: MeterGateway, building_id: str
) -> dict[tuple[str, MeterKind], Decimal]:
    """Period consumption per unit/kind from opening+closing register values."""
    readings = gateway.list_readings(
        building_id, BILLING_START, BILLING_END - timedelta(days=1)
    )
    by_meter: dict[tuple[str, MeterKind], list[Decimal]] = {}
    for reading in readings:
        by_meter.setdefault((reading.unit_id, reading.kind), []).append(reading.value)
    return {
        key: max(values) - min(values) for key, values in by_meter.items() if len(values) >= 2
    }


def compute_statement(session: Session) -> StatementBundle:
    building = session.scalars(select(Building).limit(1)).first()
    if building is None:
        raise NoDemoDataError
    units = sorted(building.units, key=lambda u: u.label)
    if not units:
        raise NoDemoDataError

    occupancies = tuple(
        Occupancy(
            unit_id=unit.id,
            tenancy_id=tenancy.id,
            period=Period(valid_from=tenancy.valid_from, valid_to=tenancy.valid_to),
        )
        for unit in units
        for tenancy in unit.tenancies
    )

    nk_result = calculate_nk_statement(
        NkInput(
            billing_period=BILLING_PERIOD,
            units=tuple(
                UnitBasis(unit_id=u.id, area_sqm_x100=u.area_sqm_x100) for u in units
            ),
            occupancies=occupancies,
            costs=(GARBAGE_COST,),
        )
    )

    split_bounds = get_rule(HEATING_SPLIT_BOUNDS, RULES_AS_OF)
    warm_water = get_rule(WARM_WATER_FORMULA, RULES_AS_OF)
    degree_days = get_rule(DEGREE_DAY_TABLE, RULES_AS_OF)
    co2_table = get_rule(CO2_SPLIT_TABLE, RULES_AS_OF)

    consumption = _consumptions(StubMeterGateway(), building.id)
    heating_result = calculate_heating_statement(
        HeatingInput(
            billing_period=BILLING_PERIOD,
            total_cost=HEATING_TOTAL_COST,
            total_energy_kwh=TOTAL_ENERGY_KWH,
            units=tuple(
                HeatingUnit(
                    unit_id=u.id,
                    area_sqm_x100=u.area_sqm_x100,
                    heat_consumption=consumption.get((u.id, MeterKind.HEAT)),
                    ww_consumption_m3=consumption.get((u.id, MeterKind.WARM_WATER)),
                )
                for u in units
            ),
            occupancies=occupancies,
            rules=HeatingRules(
                consumption_share=DEFAULT_CONSUMPTION_SHARE,
                split_bounds=split_bounds.value,
                warm_water_formula=warm_water.value,
                degree_days=degree_days.value,
                co2_table=co2_table.value,
                co2_rechtsstand=co2_table.rechtsstand,
            ),
            warm_water=WarmWaterInput(volume_m3=WARM_WATER_VOLUME_M3),
            co2=CO2_INPUT,
        )
    )

    stamps = tuple(
        dict.fromkeys(
            (
                split_bounds.rechtsstand,
                warm_water.rechtsstand,
                degree_days.rechtsstand,
                co2_table.rechtsstand,
            )
        )
    )
    return StatementBundle(
        building=building,
        nk_result=nk_result,
        nk_costs=(GARBAGE_COST,),
        heating_result=heating_result,
        party_labels=_party_labels(units),
        rechtsstaende=stamps,
    )


def to_pdf_data(bundle: StatementBundle, landlord_name: str) -> StatementData:
    building = bundle.building
    return StatementData(
        landlord_name=landlord_name,
        building_label=f"{building.street}, {building.postal_code} {building.city}",
        period_label=PERIOD_LABEL,
        nk_result=bundle.nk_result,
        nk_costs=bundle.nk_costs,
        party_labels=bundle.party_labels,
        rechtsstaende=bundle.rechtsstaende,
        heating_result=bundle.heating_result,
    )


def input_total(costs: tuple[CostItem, ...]) -> Cents:
    return cents(sum(int(c.amount) for c in costs))
