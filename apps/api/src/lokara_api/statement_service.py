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
from enum import StrEnum

from lokara_adapters import (
    MeasurementUnit,
    MeterGateway,
    MeterKind,
    consumption_by_meter,
    device_reading_segments,
)
from lokara_db import Building, CostEntry, HeatingCostEntry, MdlStatement, Tenancy, Unit
from lokara_domain import (
    AllocationKey,
    Cents,
    Co2Table,
    Occupancy,
    Period,
    build_unit_segments,
    cents,
    overlap_days,
)
from lokara_heating_engine import (
    AnnualComparisonInput,
    Co2Input,
    DeviceReadingSpan,
    HeatingDevice,
    HeatingInput,
    HeatingLine,
    HeatingResult,
    HeatingRules,
    HeatingUnit,
    InvoiceCostInput,
    MdlCo2Calculation,
    MdlStatementInput,
    OwnerResidual,
    Page01bStatementResult,
    SelfBillingStatementInput,
    WarmWaterInput,
    calculate_page01b_statement,
)
from lokara_nk_engine import (
    ConsumptionValue,
    CostItem,
    NkInput,
    NkResult,
    ShareLine,
    UnitBasis,
    calculate_nk_statement,
)
from lokara_pdf import PartyKey, StatementData, rechtsstand_entry
from lokara_rules_store import (
    CO2_SPLIT_TABLE,
    DEFAULT_CONSUMPTION_SHARE,
    DEGREE_DAY_TABLE,
    HEATING_SPLIT_BOUNDS,
    WARM_WATER_FORMULA,
    ResolvedRule,
    get_rule,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from .meter_gateway import DbMeterGateway
from .person_counts import person_count_inputs

# The 2025 billing run of the seeded scenario (docs/06 Scenario 1 + 2).
#
# These are the **demo preset**, not the billing period. `compute_statement`
# takes an explicit building and window; the preset only supplies what
# `/statements/demo`, `verify_demo_path.sh` and `lokara-pdf-demo` mean by "the
# demo", so those keep producing a byte-identical bundle. Page 01's period rules
# (Rumpfperiode day-exact, >12 months hard-blocks, leap years keep their days)
# are properties of the passed window and are enforced in the engine.
BILLING_START = date(2025, 1, 1)
BILLING_END = date(2026, 1, 1)  # exclusive
BILLING_PERIOD = Period(valid_from=BILLING_START, valid_to=BILLING_END)
RULES_AS_OF = date(2025, 12, 31)


def period_label(window: Period) -> str:
    """`01.01.2025 – 31.12.2025` — inclusive on both ends, as a human reads it.

    The stored `valid_to` is exclusive, so the printed end is the day before it.
    A Rumpfperiode and a leap year both fall out of this without a special case.
    """
    assert window.valid_to is not None
    last_day = window.valid_to - timedelta(days=1)
    return f"{window.valid_from.strftime('%d.%m.%Y')} – {last_day.strftime('%d.%m.%Y')}"


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
    # The window this bundle was computed for. On the bundle rather than read
    # back from a module constant, because two runs of one building now differ
    # by exactly this and a statement that cannot state its own period is not a
    # statement (docs/08 § 4 minimum #1's header).
    window: Period
    nk_result: NkResult
    nk_costs: tuple[CostItem, ...]
    # None when the heating inputs are incomplete — `heating_missing_reason`
    # then carries the German explanation shown instead of an invented table.
    heating_result: HeatingResult | None
    page01b_result: Page01bStatementResult | None
    heating_input_total: Cents
    heating_missing_reason: str | None
    party_labels: dict[PartyKey, str]
    # German, statement-facing notes from building the NK inputs — a partial
    # self-use inside a vacancy, an unattributable meter. They are said on the
    # document rather than resolved silently (docs/08 rule 1).
    nk_findings: tuple[str, ...]
    # Two spellings of the same four rules, on purpose. `rechtsstaende` is the
    # bare stamp and is the JSON contract the portal page reads (mirrored by
    # Zod); `rechtsstand_entries` names each rule beside its date, which is what
    # a printed legal document owes (docs/08 item 6). The JSON side gains the
    # labels in its own slice, together with the web copy that renders them.
    rechtsstaende: tuple[str, ...]
    rechtsstand_entries: tuple[str, ...]


def _party_labels(units: list[Unit], window: Period) -> dict[PartyKey, str]:
    assert window.valid_to is not None  # the billing window is always bounded
    labels: dict[PartyKey, str] = {}
    for unit in units:
        labels[(unit.id, None)] = f"{unit.label} — Leerstand → Vermieter"
        for tenancy in unit.tenancies:
            names = ", ".join(party.renter.legal_name for party in tenancy.parties)
            label = f"{unit.label} — {names}"
            if tenancy.valid_to is not None and tenancy.valid_to <= window.valid_to:
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
    # Kaltwasser per unit. It belongs to no heating block — it is the NK
    # CONSUMPTION denominator (Wasser/Abwasser), which is why it was folded away
    # unused before this slice and why a CONSUMPTION-keyed cost had no data.
    cold_water_by_unit: dict[str, Decimal]
    cold_water_unit_by_unit: dict[str, MeasurementUnit]
    # The Maßeinheit the flat's heat devices count in, so the value never
    # travels to the statement without it (docs/08 → "`MeasurementUnit` travels
    # with the value"). A missing entry means the unit could not be established
    # for that flat, which propagates to the withheld disclosure rather than to
    # a guess.
    heat_unit_by_unit: dict[str, MeasurementUnit]
    devices: tuple[HeatingDevice, ...]
    device_spans: tuple[DeviceReadingSpan, ...]


def _meter_facts(gateway: MeterGateway, building_id: str, window: Period) -> MeterFacts:
    """Fold the building's readings into the heating engine's inputs.

    A *building-level* meter (``unit_id is None``) measures the whole system;
    a unit-level one measures a flat. Both can be ``HEAT`` — only the
    measurement unit separates the kWh Wärmemengenzähler from the
    dimensionless Heizkostenverteiler, and only the former may serve as the
    § 9 denominator.
    """
    # Closed window: a period needs its opening AND its closing register value.
    assert window.valid_to is not None
    readings = gateway.list_readings(
        building_id, window.valid_from, window.valid_to - timedelta(days=1)
    )
    consumptions = consumption_by_meter(readings).values()
    segmented = device_reading_segments(readings)

    total_energy: Decimal | None = None
    ww_volume: Decimal | None = None
    heat_by_unit: dict[str, Decimal] = {}
    ww_by_unit: dict[str, Decimal] = {}
    cold_by_unit: dict[str, Decimal] = {}
    heat_units_by_unit: dict[str, set[MeasurementUnit]] = {}
    cold_units_by_unit: dict[str, set[MeasurementUnit]] = {}
    for c in consumptions:
        if c.unit_id is None:
            if c.kind is MeterKind.HEAT and c.measurement_unit is MeasurementUnit.KWH:
                total_energy = (total_energy or Decimal(0)) + c.value
            elif c.kind is MeterKind.WARM_WATER:
                ww_volume = (ww_volume or Decimal(0)) + c.value
        elif c.kind is MeterKind.HEAT:
            heat_by_unit[c.unit_id] = heat_by_unit.get(c.unit_id, Decimal(0)) + c.value
            heat_units_by_unit.setdefault(c.unit_id, set()).add(c.measurement_unit)
        elif c.kind is MeterKind.WARM_WATER:
            ww_by_unit[c.unit_id] = ww_by_unit.get(c.unit_id, Decimal(0)) + c.value
        elif c.kind is MeterKind.COLD_WATER:
            cold_by_unit[c.unit_id] = cold_by_unit.get(c.unit_id, Decimal(0)) + c.value
            cold_units_by_unit.setdefault(c.unit_id, set()).add(c.measurement_unit)

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
        cold_water_by_unit=cold_by_unit,
        # Same rule as the heat units below: two cold-water meters on one flat
        # counting differently make their sum meaningless, so no unit is
        # declared and the statement withholds the reference total rather than
        # labelling a mixed figure (docs/08 rules 2/3).
        cold_water_unit_by_unit={
            unit_id: next(iter(units))
            for unit_id, units in cold_units_by_unit.items()
            if len(units) == 1
        },
        # Only where the flat's heat devices agree. Two devices on one flat
        # counting in different units make the sum above meaningless; the
        # honest answer is to declare no unit for that flat, which propagates
        # to the withheld disclosure. Picking one of them would label a summed
        # figure with a unit that is true of only part of it.
        heat_unit_by_unit={
            unit_id: next(iter(units))
            for unit_id, units in heat_units_by_unit.items()
            if len(units) == 1
        },
        devices=tuple(
            HeatingDevice(
                device_id=device.device_id,
                unit_id=device.unit_id,
                room=device.room,
                measurement_unit=device.measurement_unit,
                valuation_factor=device.valuation_factor,
            )
            for device in segmented.devices
        ),
        device_spans=tuple(
            DeviceReadingSpan(
                device_id=span.device_id,
                allocation_kind=span.allocation_kind,
                target_id=span.target_id,
                opening=span.opening,
                closing=span.closing,
                previous_period_units=span.previous_period_units,
                estimation_basis=span.estimation_basis,
                reading_reasons=tuple(reason.value for reason in span.reading_reasons),
                reading_sources=tuple(source.value for source in span.reading_sources),
                provenance_refs=span.provenance_refs,
            )
            for span in segmented.spans
        ),
    )


def _heating_costs(
    session: Session, building_id: str, window: Period
) -> tuple[HeatingCostEntry, ...]:
    return tuple(
        session.scalars(
            select(HeatingCostEntry)
            .where(
                HeatingCostEntry.building_id == building_id,
                HeatingCostEntry.period_from < window.valid_to,
                HeatingCostEntry.period_to > window.valid_from,
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
    return Co2Input(total_co2_kg=Decimal(total_kg) / Decimal(1000), co2_cost=cents(total_cost))


def _nk_costs(session: Session, building_id: str, window: Period) -> tuple[CostItem, ...]:
    """Entered costs overlapping the billing period, each with the key from its
    LATEST assignment — the cost row itself never carries a key, so re-keying
    changes only what the engine is told, never what the user typed."""
    from .routers.costs import current_assignment  # local: avoids a router cycle

    rows = session.scalars(
        select(CostEntry)
        .where(
            CostEntry.building_id == building_id,
            CostEntry.period_from < window.valid_to,
            CostEntry.period_to > window.valid_from,
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


def compute_statement(
    session: Session,
    *,
    building_id: str | None = None,
    window: Period | None = None,
) -> StatementBundle:
    """One building, one inclusive period, one calculation (docs/02 § 5 step 1).

    Both arguments default to the demo preset so `/statements/demo`,
    `verify_demo_path.sh` and `lokara-pdf-demo` keep producing the bundle they
    always did. The session is already account-scoped by RLS, so selecting a
    building the caller may not see returns no row rather than another
    account's — but the caller still verifies the relationship in the URL
    (`CLAUDE.md` § 3.3); RLS is the backstop, not the authorization.
    """
    window = window or BILLING_PERIOD
    if building_id is None:
        # Oldest building = the seeded demo object; an explicit id is the
        # ordinary path, and this branch is only what "the demo" means.
        building = session.scalars(
            select(Building).order_by(Building.created_at, Building.id).limit(1)
        ).first()
    else:
        building = session.scalars(select(Building).where(Building.id == building_id)).first()
    if building is None:
        raise NoDemoDataError
    units = sorted(building.units, key=lambda u: u.label)
    if not units:
        raise NoDemoDataError
    nk_costs = _nk_costs(session, building.id, window)

    occupancies = tuple(
        Occupancy(
            unit_id=unit.id,
            tenancy_id=tenancy.id,
            period=Period(valid_from=tenancy.valid_from, valid_to=tenancy.valid_to),
        )
        for unit in units
        for tenancy in unit.tenancies
    )

    facts = _meter_facts(DbMeterGateway(session), building.id, window)
    persons = person_count_inputs(
        session,
        units=units,
        occupancies=occupancies,
        window=window,
        mode=building.fiktivbelegung_mode,
    )
    consumptions, consumption_findings = _nk_consumptions(units, occupancies, facts, window)

    nk_result = calculate_nk_statement(
        NkInput(
            billing_period=window,
            units=tuple(UnitBasis(unit_id=u.id, area_sqm_x100=u.area_sqm_x100) for u in units),
            occupancies=occupancies,
            costs=nk_costs,
            person_counts=persons.rows,
            consumptions=consumptions,
        )
    )
    nk_findings = (*persons.findings, *consumption_findings)

    split_bounds = get_rule(HEATING_SPLIT_BOUNDS, RULES_AS_OF)
    warm_water_rule = get_rule(WARM_WATER_FORMULA, RULES_AS_OF)
    degree_days = get_rule(DEGREE_DAY_TABLE, RULES_AS_OF)
    co2_table = get_rule(CO2_SPLIT_TABLE, RULES_AS_OF)

    heating_costs = _heating_costs(session, building.id, window)
    heating_total = cents(sum(r.amount_cents for r in heating_costs))

    heating_result: HeatingResult | None = None
    page01b_result: Page01bStatementResult | None = None
    # A confirmed Messdienstleister statement replaces the self-billing run
    # rather than competing with it: `docs/08` — "MDL pass-through and
    # self-billing are different inputs", and `docs/03` H7 forbids recomputing
    # MDL amounts. If one exists for this building period, its figures are the
    # statement's figures and no §§ 7/8 calculation is performed at all.
    mdl = _confirmed_mdl(session, building.id, window)
    missing = None if mdl is not None else _heating_missing_reason(heating_costs, facts)
    if mdl is not None:
        page01b_result = calculate_page01b_statement(mdl_statement_input(mdl, co2_table, window))
        if page01b_result.readiness != "READY":
            missing = page01b_result.findings[0].message_de
        # `heating_result` stays None by design: a passed-through statement has
        # no §§ 7/8/9 column split to print, and inventing one would be exactly
        # the recomputation H7 forbids. The renderers read `page01b_result`.
    elif missing is None:
        # Narrowed by _heating_missing_reason; assert so mypy and a future
        # reader see why this cannot be None.
        assert facts.total_energy_kwh is not None
        heating_input = HeatingInput(
            billing_period=window,
            total_cost=heating_total,
            total_energy_kwh=facts.total_energy_kwh,
            units=tuple(
                HeatingUnit(
                    unit_id=u.id,
                    area_sqm_x100=u.area_sqm_x100,
                    heat_consumption=facts.heat_by_unit.get(u.id),
                    ww_consumption_m3=facts.ww_by_unit.get(u.id),
                    # The unit rides with the value all the way from the
                    # meter: the DB row and the adapter both carry it, and
                    # dropping it here is what left the statement guessing.
                    heat_consumption_unit=facts.heat_unit_by_unit.get(u.id),
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
        page01b_result = calculate_page01b_statement(
            SelfBillingStatementInput(
                heating=heating_input,
                invoice_costs=tuple(
                    InvoiceCostInput(
                        kind="other",
                        amount=cents(row.amount_cents),
                        period_from=row.period_from,
                        period_to=row.period_to,
                    )
                    for row in heating_costs
                ),
                devices=facts.devices,
                device_spans=facts.device_spans,
                annual_comparison=AnnualComparisonInput(
                    current_heat=sum(facts.heat_by_unit.values(), Decimal(0)),
                    previous_heat=None,
                    current_warm_water=(
                        sum(facts.ww_by_unit.values(), Decimal(0)) if facts.has_warm_water else None
                    ),
                    previous_warm_water=None,
                ),
            )
        )
        if page01b_result.readiness == "READY":
            assert page01b_result.values is not None
            heating_result = page01b_result.values.heating_result
        else:
            missing = page01b_result.findings[0].message_de

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
        window=window,
        nk_result=nk_result,
        nk_costs=nk_costs,
        heating_result=heating_result,
        page01b_result=page01b_result,
        heating_input_total=heating_total,
        heating_missing_reason=missing,
        party_labels=_party_labels(units, window),
        nk_findings=nk_findings,
        rechtsstaende=stamps,
        rechtsstand_entries=entries,
    )


class StatementAudience(StrEnum):
    """Who a projection is built for (Page 01 § 4 D1, `docs/02` § 5 step 4)."""

    OWNER = "OWNER"
    """Vermieter-Gesamtübersicht — every party and the full reconciliation."""

    TENANT = "TENANT"
    """Mieter-Einzelabrechnung — exactly one covered tenancy and nothing else."""

    TAX = "TAX"
    """Leerstandsaufstellung — the owner-side vacancy evidence, no renter data."""


class UnknownTenancyError(LookupError):
    """The requested tenancy is not a covered tenancy of this building/period.

    Deliberately an error and not an empty projection: `docs/02` § 5 requires a
    tenant projection to name "one existing, account- and building-valid
    `tenancy_id`", and a missing or foreign id "fails instead of falling back to
    the owner projection". Returning the owner view for an unrecognised id is
    the exact disclosure this type exists to make impossible.
    """


class EmptyTenancyError(LookupError):
    """The tenancy exists but has zero clipped usage days in this window.

    `docs/08`: "Zero clipped usage days produces no tenant document or portal
    item and is not itself vacancy." Separate from
    :class:`UnknownTenancyError` because the two are different answers — one is
    "no such party here", the other is "that party has nothing this period" —
    and collapsing them would tell a caller which tenancy ids exist.
    """


@dataclass(frozen=True)
class StatementProjection:
    """One audience's view of one calculation, built before anything renders.

    `docs/08` § 3: "The server constructs each projection from the selected
    result before rendering. It never renders an all-renters PDF and crops,
    covers or hides rows afterward; hidden PDF structure is still a disclosure."

    That is why this is its own type rather than a flag on `StatementBundle`:
    what a renderer is not given, it cannot leak.
    """

    audience: StatementAudience
    tenancy_id: str | None
    window: Period
    building: Building
    nk_costs: tuple[CostItem, ...]
    nk_lines: tuple[ShareLine, ...]
    heating_lines: tuple[HeatingLine, ...]
    # Present for OWNER and TAX; never for TENANT — the Eigentümeranteil is not
    # a renter's business and is not part of a Mieter-Einzelabrechnung.
    owner_residual: OwnerResidual | None
    party_labels: dict[PartyKey, str]
    findings: tuple[str, ...]


def project_statement(
    bundle: StatementBundle,
    audience: StatementAudience,
    *,
    tenancy_id: str | None = None,
) -> StatementProjection:
    """Select the audience's slice of one already-computed result.

    Never recalculates: Page 01 § 4 D1 selects a document type *from* the one
    calculation, so two audiences of one run can never disagree about a figure.
    """
    heating_lines = bundle.heating_result.lines if bundle.heating_result is not None else ()
    owner_residual = (
        bundle.heating_result.owner_residual if bundle.heating_result is not None else None
    )
    if audience is StatementAudience.OWNER:
        return StatementProjection(
            audience=audience,
            tenancy_id=None,
            window=bundle.window,
            building=bundle.building,
            nk_costs=bundle.nk_costs,
            nk_lines=bundle.nk_result.lines,
            heating_lines=heating_lines,
            owner_residual=owner_residual,
            party_labels=bundle.party_labels,
            findings=bundle.nk_findings,
        )
    if audience is StatementAudience.TAX:
        return StatementProjection(
            audience=audience,
            tenancy_id=None,
            window=bundle.window,
            building=bundle.building,
            nk_costs=bundle.nk_costs,
            # Owner-side rows only. The vacancy annex keeps its origin unit and
            # cost type (`docs/08`), which is why the lines are filtered rather
            # than summed into one figure here.
            nk_lines=tuple(line for line in bundle.nk_result.lines if line.tenancy_id is None),
            heating_lines=(),
            owner_residual=owner_residual,
            party_labels={
                key: label for key, label in bundle.party_labels.items() if key[1] is None
            },
            findings=bundle.nk_findings,
        )

    if tenancy_id is None:
        raise UnknownTenancyError("A tenant projection requires a tenancy id")
    tenancy = _covered_tenancy(bundle, tenancy_id)
    assert bundle.window.valid_to is not None
    used_days = overlap_days(
        Period(valid_from=tenancy.valid_from, valid_to=tenancy.valid_to),
        bundle.window.valid_from,
        bundle.window.valid_to,
    )
    if used_days == 0:
        raise EmptyTenancyError(tenancy_id)
    return StatementProjection(
        audience=audience,
        tenancy_id=tenancy_id,
        window=bundle.window,
        building=bundle.building,
        nk_costs=bundle.nk_costs,
        nk_lines=tuple(line for line in bundle.nk_result.lines if line.tenancy_id == tenancy_id),
        heating_lines=tuple(line for line in heating_lines if line.tenancy_id == tenancy_id),
        owner_residual=None,
        party_labels={
            key: label for key, label in bundle.party_labels.items() if key[1] == tenancy_id
        },
        # The findings are building-wide operational notes naming other units,
        # so they stay on the landlord's side of the boundary.
        findings=(),
    )


def _covered_tenancy(bundle: StatementBundle, tenancy_id: str) -> Tenancy:
    """The tenancy, if it belongs to this building — otherwise a refusal.

    The session is already account-scoped, so a foreign account's tenancy is
    invisible here; this closes the remaining case, a tenancy of *another
    building* inside the same account (`CLAUDE.md` § 3.3: each endpoint verifies
    the relationship carried in the URL, and a hidden link is not authorization).
    """
    for unit in bundle.building.units:
        for tenancy in unit.tenancies:
            if tenancy.id == tenancy_id:
                return tenancy
    raise UnknownTenancyError(tenancy_id)


def _nk_consumptions(
    units: list[Unit],
    occupancies: tuple[Occupancy, ...],
    facts: MeterFacts,
    window: Period,
) -> tuple[tuple[ConsumptionValue, ...], tuple[str, ...]]:
    """Per-unit Kaltwasser as the NK CONSUMPTION Bemessung, with its Maßeinheit.

    Attribution is the whole difficulty. A cold-water meter yields one figure for
    the window, and `ConsumptionValue` names one party — so the figure can only
    be attributed when the unit had exactly one renter across the window.

    With a renter change there is no honest split: `docs/08` forbids
    document-layer money math, and inventing a day-weighted division of a
    consumption is exactly that (a flat is not used evenly, which is why
    consumption is metered rather than apportioned). Heating solves this with
    interim readings at the change (K3 device spans); NK has no equivalent input
    yet. So such a unit contributes **no** consumption row and the statement says
    why, rather than allocating a guess.

    A zero reading is *not* a missing one: it is passed through and prints a
    0,00 EUR line (`08-F12`). Only a unit with no cold-water meter at all is
    absent here.
    """
    assert window.valid_to is not None
    values: list[ConsumptionValue] = []
    findings: list[str] = []
    for unit in units:
        value = facts.cold_water_by_unit.get(unit.id)
        if value is None:
            continue
        segments = build_unit_segments(unit.id, occupancies, window.valid_from, window.valid_to)
        parties = {segment.tenancy_id for segment in segments if segment.days > 0}
        if len(parties) != 1:
            findings.append(
                f"{unit.label}: Im Abrechnungszeitraum gab es einen Nutzerwechsel, aber nur "
                "einen Kaltwasser-Zählerstand für den gesamten Zeitraum. Der Verbrauch wird "
                "keiner Partei zugeordnet; für eine verbrauchsabhängige Umlage ist eine "
                "Zwischenablesung zum Wechseltag erforderlich."
            )
            continue
        values.append(
            ConsumptionValue(
                unit_id=unit.id,
                tenancy_id=next(iter(parties)),
                value=value,
                measurement_unit=facts.cold_water_unit_by_unit.get(unit.id),
            )
        )
    return tuple(values), tuple(findings)


def _confirmed_mdl(session: Session, building_id: str, window: Period) -> MdlStatement | None:
    """The current confirmed MDL statement for exactly this building period.

    Exactly, not overlapping: an MDL statement is a document for a stated
    period, and reading one that covers a different period would silently bill
    the wrong months. The highest `version` wins — corrections append
    (`CLAUDE.md` § 3.2), and the superseded rows stay for the audit trail.
    """
    return session.scalars(
        select(MdlStatement)
        .where(
            MdlStatement.building_id == building_id,
            MdlStatement.period_from == window.valid_from,
            MdlStatement.period_to == window.valid_to,
        )
        .order_by(MdlStatement.version.desc(), MdlStatement.id.desc())
    ).first()


def mdl_statement_input(
    row: MdlStatement, co2_table: ResolvedRule[Co2Table], window: Period
) -> MdlStatementInput:
    """The stored confirmation as the engine's input — no arithmetic on the way.

    Positions are ordered by tenancy id so a rerun is byte-identical, and the
    engine's `renter_ids` are tenancy ids, which is what makes the rendered
    party labels resolve without a second lookup.
    """
    positions = sorted(row.positions, key=lambda position: position.tenancy_id)
    co2: MdlCo2Calculation | None = None
    if (
        row.co2_kg_x1000 is not None
        and row.co2_cost_cents is not None
        and row.heated_area_sqm_x100 is not None
    ):
        co2 = MdlCo2Calculation(
            total_co2_kg=Decimal(row.co2_kg_x1000) / Decimal(1000),
            co2_cost=cents(row.co2_cost_cents),
            heated_area_sqm=Decimal(row.heated_area_sqm_x100) / Decimal(100),
            table=co2_table.value,
            rechtsstand=co2_table.rechtsstand,
            billing_period=window,
        )
    return MdlStatementInput(
        branch=row.branch.value,
        renter_ids=tuple(position.tenancy_id for position in positions),
        renter_positions=tuple(position.amount_cents for position in positions),
        owner_position=row.owner_position_cents,
        confirmed_total=row.confirmed_total_cents,
        co2=co2,
        co2_evidence_present=row.co2_evidence_present,
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
        period_label=period_label(bundle.window),
        nk_result=bundle.nk_result,
        nk_costs=bundle.nk_costs,
        party_labels=bundle.party_labels,
        rechtsstaende=bundle.rechtsstand_entries,
        heating_result=bundle.heating_result,
        page01b_result=bundle.page01b_result,
    )


def input_total(costs: tuple[CostItem, ...]) -> Cents:
    return cents(sum(int(c.amount) for c in costs))
