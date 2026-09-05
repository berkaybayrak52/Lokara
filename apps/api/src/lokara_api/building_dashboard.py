"""Server-owned Objekt-Dashboard projection (04_Objekt-Dashboard.md OD1).

One request, one `as_of`, one authority. The browser receives decided values —
money already in cents and formatted, unit state already resolved, facts already
prioritized — because a second aggregation in React is a second truth.

Everything here reads. Nothing in this module creates a receivable, a reminder or
a deadline: the rules that would generate recurring rent claims live in
`07_Zahlungen.md` and are not built yet, so an absent claim stays absent rather
than being invented (OD10 MUSS-INPUT).
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal, cast

from lokara_db import (
    AdvancePaymentPeriod,
    Building,
    CostEntry,
    Meter,
    MeterReading,
    Receivable,
    Renter,
    Role,
    SelfUseKind,
    SelfUsePeriod,
    Statement,
    Tenancy,
    TenancyParty,
    Unit,
    UnitProfileVersion,
)
from lokara_domain import cents, format_eur
from lokara_pdf import (
    BuildingOverviewData,
    BuildingOverviewFact,
    BuildingOverviewKpi,
    BuildingOverviewUnit,
    format_number_de,
)
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from .schemas import (
    BuildingDashboardBalance,
    BuildingDashboardFact,
    BuildingDashboardKpis,
    BuildingDashboardModule,
    BuildingDashboardModuleFact,
    BuildingDashboardNextEvent,
    BuildingDashboardOccupancy,
    BuildingDashboardPermissions,
    BuildingDashboardResponse,
    BuildingDashboardUnit,
    BuildingDashboardUsageKpi,
)

# OD7/OD9: how far ahead a move counts as something to know about today.
EVENT_PREVIEW_DAYS = 90
# OD7: the box is a summary, not an inbox.
MAX_FACTS = 3

BUILDING_TYPE_LABELS = {
    "WOHN_UND_GESCHAEFTSHAUS": "Wohn- und Geschäftshaus",
    "WOHNHAUS": "Wohnhaus",
    "GEWERBEIMMOBILIE": "Gewerbeimmobilie",
    "EINFAMILIENHAUS": "Einfamilienhaus",
}

_STATE_LABELS = {
    "RENTED": "Vermietet",
    "VACANT": "Leerstand",
    "SELF_USE": "Eigennutzung",
    "GRATUITOUS": "Unentgeltlich überlassen",
}


def _active(valid_from: date, valid_to: date | None, as_of: date) -> bool:
    """Half-open [valid_from, valid_to), the same convention as `Period`."""
    return valid_from <= as_of and (valid_to is None or valid_to > as_of)


def _sqm(area_sqm_x100: int) -> float:
    """Display only — allocation math never sees this float (docs/02)."""
    return area_sqm_x100 / 100


@dataclass(frozen=True)
class _UnitFacts:
    """Everything one unit row needs, resolved before rendering."""

    unit: Unit
    tenancies: list[Tenancy]
    self_use_kind: SelfUseKind | None
    party_names: list[str]
    open_cents: int
    has_receivable: bool
    next_event: BuildingDashboardNextEvent | None


def _unit_state(facts: _UnitFacts) -> str:
    # A running lease is the money-bearing fact and outranks a self-use row.
    if facts.tenancies:
        return "RENTED"
    if facts.self_use_kind is SelfUseKind.OWNER_OCCUPIED:
        return "SELF_USE"
    if facts.self_use_kind is SelfUseKind.FREE_OF_CHARGE:
        return "GRATUITOUS"
    return "VACANT"


def _avg_cold_rent_cents_per_sqm(cold_rent_cents: int, rented_area_sqm_x100: int) -> int | None:
    """Weighted object figure: total current rent ÷ rented area (OD4).

    Not the mean of the per-unit prices, and undefined — not zero — when nothing
    is let for money.
    """
    if rented_area_sqm_x100 <= 0:
        return None
    per_sqm = Decimal(cold_rent_cents) * 100 / Decimal(rented_area_sqm_x100)
    return int(per_sqm.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _collect_unit_facts(
    session: Session, *, building_id: str, unit_ids: list[str], as_of: date
) -> tuple[dict[str, list[Tenancy]], dict[str, SelfUseKind], dict[str, list[str]]]:
    """Three set-based reads, never one query per unit (OD17)."""
    if not unit_ids:
        return {}, {}, {}

    active_tenancies = session.scalars(
        select(Tenancy)
        .where(
            Tenancy.unit_id.in_(unit_ids),
            Tenancy.valid_from <= as_of,
            Tenancy.valid_to.is_(None) | (Tenancy.valid_to > as_of),
        )
        .order_by(Tenancy.valid_from, Tenancy.id)
    ).all()
    tenancies_by_unit: dict[str, list[Tenancy]] = defaultdict(list)
    for tenancy in active_tenancies:
        tenancies_by_unit[tenancy.unit_id].append(tenancy)

    self_use_rows = session.scalars(
        select(SelfUsePeriod).where(
            SelfUsePeriod.unit_id.in_(unit_ids),
            SelfUsePeriod.valid_from <= as_of,
            SelfUsePeriod.valid_to.is_(None) | (SelfUsePeriod.valid_to > as_of),
        )
    ).all()
    self_use_by_unit = {row.unit_id: row.kind for row in self_use_rows}

    tenancy_ids = [tenancy.id for tenancy in active_tenancies]
    names_by_tenancy: dict[str, list[str]] = defaultdict(list)
    if tenancy_ids:
        party_rows = session.execute(
            select(TenancyParty.tenancy_id, Renter.legal_name)
            .join(
                Renter,
                and_(
                    Renter.id == TenancyParty.renter_id,
                    Renter.account_id == TenancyParty.account_id,
                ),
            )
            .where(TenancyParty.tenancy_id.in_(tenancy_ids))
            .order_by(Renter.legal_name)
        ).all()
        for tenancy_id, legal_name in party_rows:
            names_by_tenancy[tenancy_id].append(legal_name)

    names_by_unit: dict[str, list[str]] = {}
    for unit_id, tenancies in tenancies_by_unit.items():
        names_by_unit[unit_id] = [
            name for tenancy in tenancies for name in names_by_tenancy.get(tenancy.id, [])
        ]
    del building_id
    return dict(tenancies_by_unit), self_use_by_unit, names_by_unit


def _open_receivables_by_unit(
    session: Session, *, unit_ids: list[str]
) -> tuple[dict[str, int], set[str]]:
    """Open principal per unit, straight from the authoritative receivable rows.

    Bank transactions are never summed here: a credit on the account is not a
    paid rent until the matching workflow says so (docs/15 § 5).
    """
    if not unit_ids:
        return {}, set()
    rows = session.execute(
        select(
            Tenancy.unit_id,
            func.coalesce(func.sum(Receivable.open_cents), 0),
            func.count(Receivable.id),
        )
        .select_from(Receivable)
        .join(
            Tenancy,
            and_(
                Tenancy.id == Receivable.tenancy_id,
                Tenancy.account_id == Receivable.account_id,
            ),
        )
        .where(Tenancy.unit_id.in_(unit_ids))
        .group_by(Tenancy.unit_id)
    ).all()
    open_by_unit = {unit_id: int(open_cents) for unit_id, open_cents, _ in rows}
    with_receivable = {unit_id for unit_id, _, count in rows if int(count) > 0}
    return open_by_unit, with_receivable


def _next_events(
    session: Session, *, unit_ids: list[str], as_of: date
) -> dict[str, BuildingDashboardNextEvent]:
    """The nearest move in or out inside the preview window, per unit (OD9)."""
    if not unit_ids:
        return {}
    horizon = as_of + timedelta(days=EVENT_PREVIEW_DAYS)
    rows = session.scalars(
        select(Tenancy).where(
            Tenancy.unit_id.in_(unit_ids),
            (Tenancy.valid_from > as_of) & (Tenancy.valid_from <= horizon)
            | (Tenancy.valid_to.is_not(None))
            & (Tenancy.valid_to > as_of)
            & (Tenancy.valid_to <= horizon),
        )
    ).all()

    events: dict[str, BuildingDashboardNextEvent] = {}
    for tenancy in rows:
        candidates: list[BuildingDashboardNextEvent] = []
        if as_of < tenancy.valid_from <= horizon:
            days = (tenancy.valid_from - as_of).days
            candidates.append(
                BuildingDashboardNextEvent(
                    kind="MOVE_IN",
                    event_date=tenancy.valid_from,
                    label=f"Einzug in {days} Tagen",
                )
            )
        if tenancy.valid_to is not None and as_of < tenancy.valid_to <= horizon:
            days = (tenancy.valid_to - as_of).days
            candidates.append(
                BuildingDashboardNextEvent(
                    kind="MOVE_OUT",
                    event_date=tenancy.valid_to,
                    label=f"Auszug in {days} Tagen",
                )
            )
        for candidate in candidates:
            current = events.get(tenancy.unit_id)
            if current is None or candidate.event_date < current.event_date:
                events[tenancy.unit_id] = candidate
    return events


def _balance(open_cents: int, has_receivable: bool) -> BuildingDashboardBalance:
    """Only three honest answers exist today (OD10).

    "Teilweise bezahlt", "zu prüfen" and "Nachzahlung offen" need the payment
    read model from `07_Zahlungen.md`; until it exists this projection says what
    the receivable rows actually carry.
    """
    if not has_receivable:
        return BuildingDashboardBalance(
            status="NONE", open_cents=0, open_eur=format_eur(cents(0)), label="Keine Forderung"
        )
    if open_cents <= 0:
        return BuildingDashboardBalance(
            status="SETTLED", open_cents=0, open_eur=format_eur(cents(0)), label="Ausgeglichen"
        )
    return BuildingDashboardBalance(
        status="OPEN",
        open_cents=open_cents,
        open_eur=format_eur(cents(open_cents)),
        label=f"{format_eur(cents(open_cents))} offen",
    )


def _facts(rows: list[_UnitFacts], *, account_id: str) -> tuple[list[BuildingDashboardFact], int]:
    """Build the prioritized fact list.

    Order: open money first, then the nearest date, then a stable id. Severity is
    decided here so the browser never invents urgency, and no fact claims a
    default, a fee or a legal consequence.
    """
    facts: list[BuildingDashboardFact] = []
    for row in rows:
        unit_href = f"/a/{account_id}/einheiten/{row.unit.id}"
        if row.open_cents > 0:
            facts.append(
                BuildingDashboardFact(
                    id=f"receivable:{row.unit.id}",
                    category="OPEN_RECEIVABLE",
                    severity="attention",
                    text=f"{format_eur(cents(row.open_cents))} offen",
                    unit_id=row.unit.id,
                    unit_label=row.unit.label,
                    action_label="Einheit öffnen",
                    action_href=unit_href,
                    event_date=None,
                )
            )
        event = row.next_event
        if event is not None:
            facts.append(
                BuildingDashboardFact(
                    id=f"{event.kind.lower()}:{row.unit.id}",
                    category="MOVE_OUT" if event.kind == "MOVE_OUT" else "MOVE_IN",
                    severity="info",
                    text=event.label,
                    unit_id=row.unit.id,
                    unit_label=row.unit.label,
                    action_label="Einheit öffnen",
                    action_href=unit_href,
                    event_date=event.event_date,
                )
            )

    severity_rank = {"attention": 0, "info": 1}
    facts.sort(
        key=lambda fact: (
            severity_rank[fact.severity],
            fact.event_date or date.max,
            fact.id,
        )
    )
    return facts[:MAX_FACTS], len(facts)


def _modules(
    session: Session,
    *,
    account_id: str,
    building_id: str,
    as_of: date,
    miet_soll_cents: int,
    open_cents: int,
    receivable_count: int,
) -> list[BuildingDashboardModule]:
    """Three compact summaries. "Vorgänge" is absent, not empty (OD11/OD12)."""
    payments = BuildingDashboardModule(
        key="payments",
        title="Zahlungen",
        available=True,
        unavailable_reason=None,
        facts=[
            BuildingDashboardModuleFact(
                label="Mietsoll (Monat)", value=format_eur(cents(miet_soll_cents))
            ),
            BuildingDashboardModuleFact(label="Offen", value=format_eur(cents(open_cents))),
            BuildingDashboardModuleFact(label="Forderungen", value=str(receivable_count)),
        ],
        action_label="Zu den Zahlungen",
        action_href=f"/a/{account_id}/zahlungen",
    )

    year_start = date(as_of.year, 1, 1)
    year_end = date(as_of.year + 1, 1, 1)
    cost_count = int(
        session.scalar(
            select(func.count(CostEntry.id)).where(
                CostEntry.building_id == building_id,
                CostEntry.voided_at.is_(None),
                CostEntry.period_from < year_end,
                CostEntry.period_to > year_start,
            )
        )
        or 0
    )
    latest_statement = session.scalar(
        select(Statement)
        .where(Statement.building_id == building_id)
        .order_by(Statement.created_at.desc())
        .limit(1)
    )
    statement_value = (
        f"{latest_statement.status.value}" if latest_statement is not None else "Noch keine"
    )
    costs = BuildingDashboardModule(
        key="costs_and_statement",
        title="Kosten & Abrechnung",
        available=True,
        unavailable_reason=None,
        facts=[
            BuildingDashboardModuleFact(label="Abrechnungsjahr", value=str(as_of.year)),
            BuildingDashboardModuleFact(label="Kostenpositionen", value=str(cost_count)),
            BuildingDashboardModuleFact(label="Abrechnung", value=statement_value),
        ],
        action_label="Zu den Kosten",
        action_href=f"/a/{account_id}/kosten",
    )

    meter_count = int(
        session.scalar(select(func.count(Meter.id)).where(Meter.building_id == building_id)) or 0
    )
    read_meter_ids = select(MeterReading.meter_id).where(
        MeterReading.read_at >= year_start,
        MeterReading.read_at < year_end,
    )
    unread_count = int(
        session.scalar(
            select(func.count(Meter.id)).where(
                Meter.building_id == building_id,
                Meter.id.not_in(read_meter_ids),
            )
        )
        or 0
    )
    meters = BuildingDashboardModule(
        key="meters",
        title="Zähler",
        available=True,
        unavailable_reason=None,
        facts=[
            BuildingDashboardModuleFact(label="Aktive Zähler", value=str(meter_count)),
            BuildingDashboardModuleFact(
                label=f"Ohne Ablesung {as_of.year}", value=str(unread_count)
            ),
            # The shared guard runs as a pure engine with no persisted projection
            # yet (PLAN.md G1), so this line stays honest instead of empty.
            BuildingDashboardModuleFact(label="Wächterhinweise", value="Noch nicht verfügbar"),
        ],
        action_label="Zu den Zählern",
        action_href=f"/a/{account_id}/zaehler",
    )
    return [payments, costs, meters]


def _miet_soll_cents(session: Session, *, tenancy_ids: list[str], as_of: date) -> int:
    """Contractual monthly Soll: cold rent plus the advance valid at `as_of`.

    `AdvancePaymentPeriod` is an append-only schedule without an end date, so the
    period in force is the newest one that has started (M6-A).
    """
    if not tenancy_ids:
        return 0
    base = int(
        session.scalar(
            select(func.coalesce(func.sum(Tenancy.base_rent_cents), 0)).where(
                Tenancy.id.in_(tenancy_ids)
            )
        )
        or 0
    )
    periods = session.scalars(
        select(AdvancePaymentPeriod)
        .where(
            AdvancePaymentPeriod.tenancy_id.in_(tenancy_ids),
            AdvancePaymentPeriod.valid_from <= as_of,
        )
        .order_by(AdvancePaymentPeriod.valid_from, AdvancePaymentPeriod.created_at)
    ).all()
    current: dict[str, int] = {}
    for period in periods:
        current[period.tenancy_id] = period.amount_cents
    return base + sum(current.values())


def build_dashboard(
    session: Session,
    *,
    account_id: str,
    building: Building,
    role: Role,
    as_of: date,
) -> BuildingDashboardResponse:
    """Compose the whole Objekt-Dashboard from one consistent `as_of`."""
    units = list(
        session.scalars(
            select(Unit).where(Unit.building_id == building.id).order_by(Unit.label, Unit.id)
        ).all()
    )
    unit_ids = [unit.id for unit in units]

    tenancies_by_unit, self_use_by_unit, names_by_unit = _collect_unit_facts(
        session, building_id=building.id, unit_ids=unit_ids, as_of=as_of
    )
    open_by_unit, units_with_receivable = _open_receivables_by_unit(session, unit_ids=unit_ids)
    events_by_unit = _next_events(session, unit_ids=unit_ids, as_of=as_of)

    rows = [
        _UnitFacts(
            unit=unit,
            tenancies=tenancies_by_unit.get(unit.id, []),
            self_use_kind=self_use_by_unit.get(unit.id),
            party_names=names_by_unit.get(unit.id, []),
            open_cents=open_by_unit.get(unit.id, 0),
            has_receivable=unit.id in units_with_receivable,
            next_event=events_by_unit.get(unit.id),
        )
        for unit in units
    ]

    unit_rows: list[BuildingDashboardUnit] = []
    cold_rent_cents = 0
    total_area_sqm_x100 = 0
    rented_area_sqm_x100 = 0
    occupancy = {"RENTED": 0, "VACANT": 0, "SELF_USE": 0, "GRATUITOUS": 0}

    # OD5: usage is authoritative only when a versioned profile says so. Read
    # the latest profile per unit in one query; never infer commercial use from
    # labels, names or rent amounts.
    profile_rows = session.scalars(
        select(UnitProfileVersion)
        .where(
            UnitProfileVersion.unit_id.in_(unit_ids),
            UnitProfileVersion.effective_from <= as_of,
        )
        .order_by(
            UnitProfileVersion.unit_id,
            UnitProfileVersion.effective_from.desc(),
            UnitProfileVersion.version.desc(),
        )
    ).all()
    profile_by_unit: dict[str, UnitProfileVersion] = {}
    for profile_row in profile_rows:
        profile_by_unit.setdefault(profile_row.unit_id, profile_row)
    usage_totals: dict[Literal["RESIDENTIAL", "COMMERCIAL", "OTHER"], tuple[int, int]] = {}

    for row in rows:
        state = _unit_state(row)
        occupancy[state] += 1
        total_area_sqm_x100 += row.unit.area_sqm_x100

        overlap = len(row.tenancies) > 1
        unit_rent: int | None = None
        if row.tenancies:
            unit_rent = sum(tenancy.base_rent_cents for tenancy in row.tenancies)
            cold_rent_cents += unit_rent
            rented_area_sqm_x100 += row.unit.area_sqm_x100
            profile = profile_by_unit.get(row.unit.id)
            if profile is not None:
                usage_type = cast(Literal["RESIDENTIAL", "COMMERCIAL", "OTHER"], profile.usage_type)
                area, rent = usage_totals.get(usage_type, (0, 0))
                usage_totals[usage_type] = (
                    area + row.unit.area_sqm_x100,
                    rent + unit_rent,
                )

        unit_rows.append(
            BuildingDashboardUnit(
                id=row.unit.id,
                label=row.unit.label,
                area_sqm_x100=row.unit.area_sqm_x100,
                area_sqm=_sqm(row.unit.area_sqm_x100),
                state=state,  # type: ignore[arg-type]
                state_label=_STATE_LABELS[state],
                party_names=row.party_names,
                has_tenancy_overlap=overlap,
                cold_rent_cents=None if overlap else unit_rent,
                cold_rent_eur=None
                if overlap or unit_rent is None
                else format_eur(cents(unit_rent)),
                balance=_balance(row.open_cents, row.has_receivable),
                next_event=row.next_event,
            )
        )

    facts, facts_total = _facts(rows, account_id=account_id)
    avg_per_sqm = _avg_cold_rent_cents_per_sqm(cold_rent_cents, rented_area_sqm_x100)
    tenancy_ids = [tenancy.id for row in rows for tenancy in row.tenancies]

    kpis = BuildingDashboardKpis(
        cold_rent_cents_monthly=cold_rent_cents,
        cold_rent_eur_monthly=format_eur(cents(cold_rent_cents)),
        total_area_sqm_x100=total_area_sqm_x100,
        total_area_sqm=_sqm(total_area_sqm_x100),
        rented_area_sqm_x100=rented_area_sqm_x100,
        rented_area_sqm=_sqm(rented_area_sqm_x100),
        avg_cold_rent_cents_per_sqm=avg_per_sqm,
        avg_cold_rent_eur_per_sqm=None if avg_per_sqm is None else format_eur(cents(avg_per_sqm)),
        occupancy=BuildingDashboardOccupancy(
            rented=occupancy["RENTED"],
            vacant=occupancy["VACANT"],
            # Both self-use kinds are "not let for money" for the occupancy count;
            # the unit row keeps them apart.
            self_use=occupancy["SELF_USE"] + occupancy["GRATUITOUS"],
            total=len(units),
        ),
        usage_breakdown=[
            BuildingDashboardUsageKpi(
                usage_type=usage_type,
                usage_label={
                    "RESIDENTIAL": "Wohnen",
                    "COMMERCIAL": "Gewerbe",
                    "OTHER": "Sonstige Nutzung",
                }[usage_type],
                rented_area_sqm_x100=area,
                rented_area_sqm=_sqm(area),
                cold_rent_cents_monthly=rent,
                cold_rent_eur_monthly=format_eur(cents(rent)),
                avg_cold_rent_cents_per_sqm=_avg_cold_rent_cents_per_sqm(rent, area),
                avg_cold_rent_eur_per_sqm=(
                    format_eur(cents(usage_average))
                    if (usage_average := _avg_cold_rent_cents_per_sqm(rent, area)) is not None
                    else None
                ),
            )
            for usage_type, (area, rent) in sorted(usage_totals.items())
        ],
    )

    modules = _modules(
        session,
        account_id=account_id,
        building_id=building.id,
        as_of=as_of,
        miet_soll_cents=_miet_soll_cents(session, tenancy_ids=tenancy_ids, as_of=as_of),
        open_cents=sum(open_by_unit.values()),
        receivable_count=len(units_with_receivable),
    )

    # OD14: no new role is invented here. Every action an employee has no
    # approved rule for stays owner-only, and the server refuses it either way.
    is_owner = role is Role.OWNER
    return BuildingDashboardResponse(
        as_of=as_of,
        id=building.id,
        name=building.name,
        street=building.street,
        postal_code=building.postal_code,
        city=building.city,
        country=building.country,
        building_type=building.building_type,
        building_type_label=BUILDING_TYPE_LABELS.get(
            building.building_type, building.building_type
        ),
        is_residential=building.is_residential,
        unit_count=len(units),
        kpis=kpis,
        facts=facts,
        facts_total=facts_total,
        units=unit_rows,
        modules=modules,
        permissions=BuildingDashboardPermissions(
            can_edit=is_owner, can_create_unit=is_owner, can_export_pdf=is_owner
        ),
    )


def building_overview_data(
    dashboard: BuildingDashboardResponse, *, generated_at: datetime
) -> BuildingOverviewData:
    """Map the finished projection onto the document (OD13).

    Every value below is copied, never recalculated. The four KPI strings, the
    unit states, the rents and the balances are exactly what the screen shows,
    so page and paper cannot drift apart.
    """
    occupancy = dashboard.kpis.occupancy
    occupancy_parts = [f"{occupancy.rented} von {occupancy.total} vermietet"]
    if occupancy.vacant:
        occupancy_parts.append(f"{occupancy.vacant} Leerstand")
    if occupancy.self_use:
        occupancy_parts.append(f"{occupancy.self_use} Eigennutzung")

    kpis = (
        BuildingOverviewKpi(
            label_de="Kaltmiete / Monat", value_de=dashboard.kpis.cold_rent_eur_monthly
        ),
        BuildingOverviewKpi(
            label_de="Gesamtfläche",
            value_de=f"{format_number_de(Decimal(dashboard.kpis.total_area_sqm_x100) / 100)} m²",
        ),
        BuildingOverviewKpi(
            label_de="Ø Kaltmiete / m²",
            value_de=(
                "–"
                if dashboard.kpis.avg_cold_rent_eur_per_sqm is None
                else dashboard.kpis.avg_cold_rent_eur_per_sqm
            ),
        ),
        BuildingOverviewKpi(label_de="Vermietungsstand", value_de=" · ".join(occupancy_parts)),
    )

    units = tuple(
        BuildingOverviewUnit(
            label=unit.label,
            state_de=unit.state_label,
            parties_de=", ".join(unit.party_names) if unit.party_names else "–",
            area_de=f"{format_number_de(Decimal(unit.area_sqm_x100) / 100)} m²",
            cold_rent_de=unit.cold_rent_eur or "–",
            balance_de=unit.balance.label if unit.balance is not None else "–",
        )
        for unit in dashboard.units
    )
    facts = tuple(
        BuildingOverviewFact(text_de=fact.text, unit_label=fact.unit_label)
        for fact in dashboard.facts
    )
    return BuildingOverviewData(
        building_name=dashboard.name,
        address_de=f"{dashboard.street}, {dashboard.postal_code} {dashboard.city}",
        building_type_de=dashboard.building_type_label,
        as_of=dashboard.as_of,
        generated_at=generated_at,
        kpis=kpis,
        units=units,
        facts=facts,
    )
