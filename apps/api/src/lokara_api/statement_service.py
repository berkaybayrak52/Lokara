"""Composes the statement: DB rows → both engines → one result.

**Every number now comes from entered data.** One occupancy timeline drives
both engines (docs/06) — NK and heating read the same tenancy rows, which is
what makes the degree-day split visible on the statement. Betriebskosten are
`CostEntry` rows keyed by their latest `AllocationKeyAssignment`; the heating
system's cost and CO₂ figures are the `HeatingCostEntry` off the fuel invoice;
and every consumption — per flat *and* the building totals — is derived from
`MeterReading` rows through the Phase D `MeterGateway` port. No fixture
constants remain in this module.

What is deliberately *not* here: any fallback that invents a number. If the
heating inputs are incomplete the statement says so; the NK part still
computes, because one missing meter must not block the Betriebskosten.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from lokara_adapters import (
    MeasurementUnit,
    MeterGateway,
    MeterKind,
    consumption_by_meter,
)
from lokara_db import Building, CostEntry, HeatingCostEntry, Unit
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
from lokara_pdf import PartyKey, StatementData, rechtsstand_entry
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

from .meter_gateway import DbMeterGateway

# The 2025 billing run of the seeded scenario (docs/06 Scenario 1 + 2).
BILLING_START = date(2025, 1, 1)
BILLING_END = date(2026, 1, 1)  # exclusive
BILLING_PERIOD = Period(valid_from=BILLING_START, valid_to=BILLING_END)
PERIOD_LABEL = "01.01.2025 – 31.12.2025"
RULES_AS_OF = date(2025, 12, 31)

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
    # None when the heating inputs are incomplete — `heating_missing_reason`
    # then carries the German explanation shown instead of an invented table.
    heating_result: HeatingResult | None
    heating_input_total: Cents
    heating_missing_reason: str | None
    party_labels: dict[PartyKey, str]
    # Two spellings of the same four rules, on purpose. `rechtsstaende` is the
    # bare stamp and is the JSON contract the portal page reads (mirrored by
    # Zod); `rechtsstand_entries` names each rule beside its date, which is what
    # a printed legal document owes (docs/08 item 6). The JSON side gains the
    # labels in its own slice, together with the web copy that renders them.
    rechtsstaende: tuple[str, ...]
    rechtsstand_entries: tuple[str, ...]


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


@dataclass(frozen=True)
class MeterFacts:
    """Everything the heating engine needs that a meter can answer."""

    # Building-level Wärmemengenzähler, in kWh — the § 9 energy denominator.
    total_energy_kwh: Decimal | None
    # Building-level Warmwasserzähler, in m³. None with `has_warm_water` True
    # means central warm water exists but is unmeasured → § 9 Abs. 2 fallback.
    warm_water_volume_m3: Decimal | None
    has_warm_water: bool
    # Per unit; a missing entry is a missing reading → § 9a estimate.
    heat_by_unit: dict[str, Decimal]
    ww_by_unit: dict[str, Decimal]


def _meter_facts(gateway: MeterGateway, building_id: str) -> MeterFacts:
    """Fold the building's readings into the heating engine's inputs.

    A *building-level* meter (``unit_id is None``) measures the whole system;
    a unit-level one measures a flat. Both can be ``HEAT`` — only the
    measurement unit separates the kWh Wärmemengenzähler from the
    dimensionless Heizkostenverteiler, and only the former may serve as the
    § 9 denominator.
    """
    # Closed window: a period needs its opening AND its closing register value.
    readings = gateway.list_readings(
        building_id, BILLING_START, BILLING_END - timedelta(days=1)
    )
    consumptions = consumption_by_meter(readings).values()

    total_energy: Decimal | None = None
    ww_volume: Decimal | None = None
    heat_by_unit: dict[str, Decimal] = {}
    ww_by_unit: dict[str, Decimal] = {}
    for c in consumptions:
        if c.unit_id is None:
            if c.kind is MeterKind.HEAT and c.measurement_unit is MeasurementUnit.KWH:
                total_energy = (total_energy or Decimal(0)) + c.value
            elif c.kind is MeterKind.WARM_WATER:
                ww_volume = (ww_volume or Decimal(0)) + c.value
        elif c.kind is MeterKind.HEAT:
            heat_by_unit[c.unit_id] = heat_by_unit.get(c.unit_id, Decimal(0)) + c.value
        elif c.kind is MeterKind.WARM_WATER:
            ww_by_unit[c.unit_id] = ww_by_unit.get(c.unit_id, Decimal(0)) + c.value

    return MeterFacts(
        total_energy_kwh=total_energy,
        warm_water_volume_m3=ww_volume,
        # Central warm water is a property of the installation, so it follows
        # from a warm-water meter EXISTING — not from whether that meter
        # happened to produce a usable pair this period. An unread one still
        # means § 9 applies, via the area fallback.
        has_warm_water=any(r.kind is MeterKind.WARM_WATER for r in readings),
        heat_by_unit=heat_by_unit,
        ww_by_unit=ww_by_unit,
    )


def _heating_costs(session: Session, building_id: str) -> tuple[HeatingCostEntry, ...]:
    return tuple(
        session.scalars(
            select(HeatingCostEntry)
            .where(
                HeatingCostEntry.building_id == building_id,
                HeatingCostEntry.period_from < BILLING_END,
                HeatingCostEntry.period_to > BILLING_START,
            )
            .order_by(HeatingCostEntry.created_at, HeatingCostEntry.id)
        ).all()
    )


def _co2_input(rows: tuple[HeatingCostEntry, ...]) -> Co2Input | None:
    """CO₂ emissions + their price, off the fuel invoice (§ 5 CO2KostAufG).

    Both are needed: without the kg there is no intensity to grade, without
    the € there is nothing to split. A Wärmelieferung invoice that states
    neither simply produces no CO₂ block.
    """
    total_kg = sum(r.co2_kg_x1000 or 0 for r in rows)
    total_cost = sum(r.co2_cost_cents or 0 for r in rows)
    if total_kg <= 0 or total_cost <= 0:
        return None
    return Co2Input(
        total_co2_kg=Decimal(total_kg) / Decimal(1000), co2_cost=cents(total_cost)
    )


def _nk_costs(session: Session, building_id: str) -> tuple[CostItem, ...]:
    """Entered costs overlapping the billing period, each with the key from its
    LATEST assignment — the cost row itself never carries a key, so re-keying
    changes only what the engine is told, never what the user typed."""
    from .routers.costs import current_assignment  # local: avoids a router cycle

    rows = session.scalars(
        select(CostEntry)
        .where(
            CostEntry.building_id == building_id,
            CostEntry.period_from < BILLING_END,
            CostEntry.period_to > BILLING_START,
        )
        .order_by(CostEntry.created_at, CostEntry.id)
    ).all()
    items: list[CostItem] = []
    for row in rows:
        assignment = current_assignment(row)
        items.append(
            CostItem(
                cost_id=row.id,
                label=row.label,
                amount=cents(row.amount_cents),
                key=assignment.key,
                direct_unit_id=assignment.direct_unit_id,
                direct_tenancy_id=assignment.direct_tenancy_id,
            )
        )
    return tuple(items)


def compute_statement(session: Session) -> StatementBundle:
    # Oldest building = the seeded demo object; user-created ones come later.
    building = session.scalars(
        select(Building).order_by(Building.created_at, Building.id).limit(1)
    ).first()
    if building is None:
        raise NoDemoDataError
    units = sorted(building.units, key=lambda u: u.label)
    if not units:
        raise NoDemoDataError
    nk_costs = _nk_costs(session, building.id)

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
            costs=nk_costs,
        )
    )

    split_bounds = get_rule(HEATING_SPLIT_BOUNDS, RULES_AS_OF)
    warm_water_rule = get_rule(WARM_WATER_FORMULA, RULES_AS_OF)
    degree_days = get_rule(DEGREE_DAY_TABLE, RULES_AS_OF)
    co2_table = get_rule(CO2_SPLIT_TABLE, RULES_AS_OF)

    heating_costs = _heating_costs(session, building.id)
    heating_total = cents(sum(r.amount_cents for r in heating_costs))
    facts = _meter_facts(DbMeterGateway(session), building.id)

    heating_result: HeatingResult | None = None
    missing = _heating_missing_reason(heating_costs, facts)
    if missing is None:
        # Narrowed by _heating_missing_reason; assert so mypy and a future
        # reader see why this cannot be None.
        assert facts.total_energy_kwh is not None
        heating_result = calculate_heating_statement(
            HeatingInput(
                billing_period=BILLING_PERIOD,
                total_cost=heating_total,
                total_energy_kwh=facts.total_energy_kwh,
                units=tuple(
                    HeatingUnit(
                        unit_id=u.id,
                        area_sqm_x100=u.area_sqm_x100,
                        heat_consumption=facts.heat_by_unit.get(u.id),
                        ww_consumption_m3=facts.ww_by_unit.get(u.id),
                    )
                    for u in units
                ),
                occupancies=occupancies,
                rules=HeatingRules(
                    consumption_share=DEFAULT_CONSUMPTION_SHARE,
                    split_bounds=split_bounds.value,
                    warm_water_formula=warm_water_rule.value,
                    degree_days=degree_days.value,
                    co2_table=co2_table.value,
                    co2_rechtsstand=co2_table.rechtsstand,
                ),
                warm_water=(
                    WarmWaterInput(volume_m3=facts.warm_water_volume_m3)
                    if facts.has_warm_water
                    else None
                ),
                co2=_co2_input(heating_costs),
            )
        )

    stamps = tuple(
        dict.fromkeys(
            (
                split_bounds.rechtsstand,
                warm_water_rule.rechtsstand,
                degree_days.rechtsstand,
                co2_table.rechtsstand,
            )
        )
    )
    entries = tuple(
        dict.fromkeys(
            (
                rechtsstand_entry(split_bounds),
                rechtsstand_entry(warm_water_rule),
                rechtsstand_entry(degree_days),
                rechtsstand_entry(co2_table),
            )
        )
    )
    return StatementBundle(
        building=building,
        nk_result=nk_result,
        nk_costs=nk_costs,
        heating_result=heating_result,
        heating_input_total=heating_total,
        heating_missing_reason=missing,
        party_labels=_party_labels(units),
        rechtsstaende=stamps,
        rechtsstand_entries=entries,
    )


def _heating_missing_reason(
    heating_costs: tuple[HeatingCostEntry, ...], facts: MeterFacts
) -> str | None:
    """German explanation of why no heating statement can be produced — or None.

    Refusing beats estimating: a Heizkostenabrechnung built on a guessed
    energy total is not correctable later, it is just wrong.
    """
    if not heating_costs:
        return (
            "Für den Abrechnungszeitraum sind keine Heizkosten erfasst — "
            "bitte die Rechnung des Energieversorgers unter Zähler eintragen."
        )
    if facts.total_energy_kwh is None:
        return (
            "Kein Wärmemengenzähler (kWh) am Gebäude mit je einer Ablesung zu "
            "Beginn und Ende des Zeitraums — ohne ihn fehlt die Energiemenge "
            "nach § 9 HeizkostenV."
        )
    return None


def to_pdf_data(bundle: StatementBundle, landlord_name: str) -> StatementData:
    building = bundle.building
    return StatementData(
        landlord_name=landlord_name,
        building_label=f"{building.street}, {building.postal_code} {building.city}",
        period_label=PERIOD_LABEL,
        nk_result=bundle.nk_result,
        nk_costs=bundle.nk_costs,
        party_labels=bundle.party_labels,
        rechtsstaende=bundle.rechtsstand_entries,
        heating_result=bundle.heating_result,
    )


def input_total(costs: tuple[CostItem, ...]) -> Cents:
    return cents(sum(int(c.amount) for c in costs))
