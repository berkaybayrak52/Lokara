"""Server-owned UI-05B projection for one unit at one effective date."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from lokara_db import (
    AdvancePaymentPeriod,
    Role,
    SelfUseKind,
    Statement,
    StatementArchive,
    Tenancy,
    TenancyContractPosition,
    TenancyContractVersion,
    TenancyRentChange,
    Unit,
    UnitProfileVersion,
)
from lokara_domain import cents, format_eur
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .schemas import (
    UnitDashboardAction,
    UnitDashboardContractPosition,
    UnitDashboardDocument,
    UnitDashboardHistorySegment,
    UnitDashboardModule,
    UnitDashboardParty,
    UnitDashboardPermissions,
    UnitDashboardProfile,
    UnitDashboardRentChange,
    UnitDashboardResponse,
    UnitDashboardTenancy,
)

PROFILE_USAGE_LABELS = {
    "RESIDENTIAL": "Wohnen",
    "COMMERCIAL": "Gewerbe",
    "OTHER": "Sonstige Nutzung",
}
AMENITY_LABELS = {
    "BALCONY": "Balkon",
    "TERRACE": "Terrasse",
    "ELEVATOR": "Aufzug",
    "CELLAR": "Keller",
    "FITTED_KITCHEN": "Einbauküche",
    "BARRIER_REDUCED": "Barrierearm",
}
CONTRACT_TYPE_LABELS = {
    "RESIDENTIAL_OPEN_ENDED": "Wohnraummietvertrag · unbefristet",
    "RESIDENTIAL_FIXED_TERM": "Wohnraummietvertrag · befristet",
    "COMMERCIAL_OPEN_ENDED": "Gewerbemietvertrag · unbefristet",
    "COMMERCIAL_FIXED_TERM": "Gewerbemietvertrag · befristet",
    "OTHER": "Sonstiger Vertrag",
}
STATE_LABELS = {
    "RENTED": "Vermietet",
    "VACANT": "Leerstand",
    "SELF_USE": "Eigennutzung",
    "GRATUITOUS": "Unentgeltlich überlassen",
    "CONFLICT": "Datenkonflikt",
}

HistoryKind = Literal["RENTED", "VACANT", "SELF_USE", "GRATUITOUS"]
UnitState = Literal["RENTED", "VACANT", "SELF_USE", "GRATUITOUS", "CONFLICT"]


def _active(valid_from: date, valid_to: date | None, as_of: date) -> bool:
    return valid_from <= as_of and (valid_to is None or valid_to > as_of)


def _format_fixed(value_x100: int) -> str:
    whole, fraction = divmod(value_x100, 100)
    return f"{whole},{fraction:02d}"


def _format_decimal(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{quantized:.2f}".replace(".", ",")


def _display_end(exclusive_end: date | None) -> date | None:
    return exclusive_end - timedelta(days=1) if exclusive_end is not None else None


def _profile(session: Session, unit: Unit, as_of: date) -> UnitDashboardProfile:
    row = session.scalar(
        select(UnitProfileVersion)
        .where(
            UnitProfileVersion.unit_id == unit.id,
            UnitProfileVersion.effective_from <= as_of,
        )
        .order_by(UnitProfileVersion.effective_from.desc(), UnitProfileVersion.version.desc())
        .limit(1)
    )
    if row is None:
        return UnitDashboardProfile(
            version=None,
            usage_type=None,
            usage_label="Nicht dokumentiert",
            rooms_x100=None,
            rooms_display=None,
            amenities=[],
            amenity_labels=[],
            amenity_note=None,
            evidence_ref=None,
        )
    amenities = [item for item in row.amenities if item in AMENITY_LABELS]
    return UnitDashboardProfile(
        version=row.version,
        usage_type=row.usage_type,
        usage_label=PROFILE_USAGE_LABELS[row.usage_type],
        rooms_x100=row.rooms_x100,
        rooms_display=_format_fixed(row.rooms_x100) if row.rooms_x100 is not None else None,
        amenities=amenities,
        amenity_labels=[AMENITY_LABELS[item] for item in amenities],
        amenity_note=row.amenity_note,
        evidence_ref=row.evidence_ref,
    )


def _current_tenancy(
    session: Session, tenancy: Tenancy, unit: Unit, as_of: date
) -> UnitDashboardTenancy:
    contract = session.scalar(
        select(TenancyContractVersion)
        .where(
            TenancyContractVersion.tenancy_id == tenancy.id,
            TenancyContractVersion.effective_from <= as_of,
        )
        .order_by(
            TenancyContractVersion.effective_from.desc(),
            TenancyContractVersion.version.desc(),
        )
        .limit(1)
    )
    rent_change = session.scalar(
        select(TenancyRentChange)
        .where(
            TenancyRentChange.tenancy_id == tenancy.id,
            TenancyRentChange.effective_from <= as_of,
        )
        .order_by(TenancyRentChange.effective_from.desc())
        .limit(1)
    )
    advance = session.scalar(
        select(AdvancePaymentPeriod)
        .where(
            AdvancePaymentPeriod.tenancy_id == tenancy.id,
            AdvancePaymentPeriod.valid_from <= as_of,
        )
        .order_by(AdvancePaymentPeriod.valid_from.desc())
        .limit(1)
    )
    position_rows = session.scalars(
        select(TenancyContractPosition)
        .where(
            TenancyContractPosition.tenancy_id == tenancy.id,
            TenancyContractPosition.valid_from <= as_of,
            (
                (TenancyContractPosition.valid_to.is_(None))
                | (TenancyContractPosition.valid_to > as_of)
            ),
        )
        .order_by(TenancyContractPosition.position_type, TenancyContractPosition.created_at)
    ).all()
    cold_rent_cents = (
        rent_change.new_base_rent_cents if rent_change is not None else tenancy.base_rent_cents
    )
    advance_cents = advance.amount_cents if advance is not None else 0
    extra_cents = sum(
        row.monthly_amount_cents or 0 for row in position_rows if row.inclusion_type == "SEPARATE"
    )
    per_sqm = (
        Decimal(cold_rent_cents) / Decimal(unit.area_sqm_x100) if unit.area_sqm_x100 > 0 else None
    )
    positions = [
        UnitDashboardContractPosition(
            id=row.id,
            position_type=row.position_type,
            position_label="Garage" if row.position_type == "GARAGE" else "Stellplatz",
            inclusion_type=row.inclusion_type,
            inclusion_label=(
                "In der Kaltmiete enthalten"
                if row.inclusion_type == "INCLUDED"
                else "Separat vereinbart"
            ),
            label=row.label,
            monthly_amount_cents=row.monthly_amount_cents,
            monthly_amount_eur=(
                format_eur(cents(row.monthly_amount_cents))
                if row.monthly_amount_cents is not None
                else None
            ),
        )
        for row in position_rows
    ]
    return UnitDashboardTenancy(
        id=tenancy.id,
        parties=[
            UnitDashboardParty(
                id=party.renter.id,
                name=party.renter.legal_name,
                email=party.renter.email,
            )
            for party in sorted(tenancy.parties, key=lambda item: item.renter.legal_name)
        ],
        valid_from=tenancy.valid_from,
        valid_to=_display_end(tenancy.valid_to),
        contract_type=contract.contract_type if contract is not None else None,
        contract_type_label=(
            CONTRACT_TYPE_LABELS[contract.contract_type]
            if contract is not None
            else "Nicht dokumentiert"
        ),
        contract_evidence_ref=contract.evidence_ref if contract is not None else None,
        cold_rent_cents=cold_rent_cents,
        cold_rent_eur=format_eur(cents(cold_rent_cents)),
        cold_rent_per_sqm_eur=_format_decimal(per_sqm) if per_sqm is not None else None,
        advance_payment_cents=advance_cents,
        advance_payment_eur=format_eur(cents(advance_cents)),
        total_monthly_cents=cold_rent_cents + advance_cents + extra_cents,
        total_monthly_eur=format_eur(cents(cold_rent_cents + advance_cents + extra_cents)),
        positions=positions,
        last_rent_change=(
            UnitDashboardRentChange(
                effective_from=rent_change.effective_from,
                new_base_rent_cents=rent_change.new_base_rent_cents,
                new_base_rent_eur=format_eur(cents(rent_change.new_base_rent_cents)),
                evidence_ref=rent_change.evidence_ref,
            )
            if rent_change is not None
            else None
        ),
    )


@dataclass(frozen=True)
class _Interval:
    kind: HistoryKind
    label: str
    valid_from: date
    valid_to: date | None
    party_names: list[str]


def _history(unit: Unit, as_of: date) -> list[UnitDashboardHistorySegment]:
    explicit: list[_Interval] = [
        _Interval(
            kind="RENTED",
            label="Vermietet",
            valid_from=tenancy.valid_from,
            valid_to=tenancy.valid_to,
            party_names=sorted(party.renter.legal_name for party in tenancy.parties),
        )
        for tenancy in unit.tenancies
        if tenancy.valid_from <= as_of
    ]
    explicit.extend(
        _Interval(
            kind=("SELF_USE" if period.kind is SelfUseKind.OWNER_OCCUPIED else "GRATUITOUS"),
            label=(
                "Eigennutzung"
                if period.kind is SelfUseKind.OWNER_OCCUPIED
                else "Unentgeltlich überlassen"
            ),
            valid_from=period.valid_from,
            valid_to=period.valid_to,
            party_names=[],
        )
        for period in unit.self_use_periods
        if period.valid_from <= as_of
    )
    start = min(
        (row.valid_from for row in explicit),
        default=min(unit.created_at.date(), as_of),
    )
    boundaries = {start, as_of + timedelta(days=1)}
    for row in explicit:
        boundaries.add(max(row.valid_from, start))
        if row.valid_to is not None and start < row.valid_to <= as_of:
            boundaries.add(row.valid_to)
    points = sorted(boundaries)
    segments: list[UnitDashboardHistorySegment] = []
    for index, segment_start in enumerate(points[:-1]):
        segment_stop = points[index + 1]
        active = [
            row
            for row in explicit
            if row.valid_from <= segment_start
            and (row.valid_to is None or row.valid_to > segment_start)
        ]
        selected = next((item for item in active if item.kind == "RENTED"), None)
        if selected is None and active:
            selected = active[0]
        current = segment_start <= as_of < segment_stop
        segments.append(
            UnitDashboardHistorySegment(
                kind=selected.kind if selected is not None else "VACANT",
                label=selected.label if selected is not None else "Leerstand",
                valid_from=segment_start,
                valid_to=None if current else segment_stop - timedelta(days=1),
                party_names=selected.party_names if selected is not None else [],
                current=current,
            )
        )
    return list(reversed(segments))


def _documents(
    session: Session, account_id: str, unit: Unit, tenancy_id: str | None
) -> list[UnitDashboardDocument]:
    if tenancy_id is None:
        return []
    rows = session.execute(
        select(StatementArchive, func.octet_length(StatementArchive.content_bytes))
        .join(Statement, Statement.id == StatementArchive.statement_id)
        .where(
            StatementArchive.tenancy_id == tenancy_id,
            StatementArchive.audience == "TENANT",
            Statement.building_id == unit.building_id,
        )
        .order_by(StatementArchive.created_at.desc())
        .limit(5)
    ).all()
    return [
        UnitDashboardDocument(
            id=archive.id,
            statement_id=archive.statement_id,
            document_type=archive.document_type,
            filename=archive.filename,
            sha256=archive.sha256,
            size_bytes=size_bytes,
            created_at=archive.created_at,
            download_href=(
                f"/a/{account_id}/buildings/{unit.building_id}/statements/"
                f"{archive.statement_id}/documents/{archive.id}"
            ),
        )
        for archive, size_bytes in rows
    ]


def build_unit_dashboard(
    session: Session,
    *,
    account_id: str,
    unit: Unit,
    role: Role,
    as_of: date,
) -> UnitDashboardResponse:
    active_tenancies = [
        tenancy
        for tenancy in unit.tenancies
        if _active(tenancy.valid_from, tenancy.valid_to, as_of)
    ]
    active_self_use = [
        period
        for period in unit.self_use_periods
        if _active(period.valid_from, period.valid_to, as_of)
    ]
    conflict = (
        len(active_tenancies) > 1
        or len(active_self_use) > 1
        or bool(active_tenancies and active_self_use)
    )
    state: UnitState
    if conflict:
        state = "CONFLICT"
    elif active_tenancies:
        state = "RENTED"
    elif active_self_use and active_self_use[0].kind is SelfUseKind.OWNER_OCCUPIED:
        state = "SELF_USE"
    elif active_self_use:
        state = "GRATUITOUS"
    else:
        state = "VACANT"

    current = (
        _current_tenancy(session, active_tenancies[0], unit, as_of)
        if len(active_tenancies) == 1
        else None
    )
    is_owner = role is Role.OWNER
    future_tenancy = next(
        (
            tenancy
            for tenancy in sorted(unit.tenancies, key=lambda item: item.valid_from)
            if tenancy.valid_from > as_of
        ),
        None,
    )
    primary_action: UnitDashboardAction | None = None
    if is_owner and not conflict:
        if current is not None:
            primary_action = UnitDashboardAction(
                key="OPEN_TENANCY",
                label="Mietverhältnis ansehen",
                href="#aktuelles-mietverhaeltnis",
            )
        elif future_tenancy is None:
            primary_action = UnitDashboardAction(
                key="CREATE_TENANCY",
                label="Mietverhältnis anlegen",
                href="?createTenancy=1",
            )
        else:
            primary_action = UnitDashboardAction(
                key="OPEN_FUTURE_TENANCY",
                label="Künftiges Mietverhältnis ansehen",
                href="#mietverlauf",
            )

    history = _history(unit, as_of)
    visible_history = history[:10]
    documents = _documents(
        session,
        account_id,
        unit,
        active_tenancies[0].id if is_owner and len(active_tenancies) == 1 else None,
    )
    portal_available = is_owner and current is not None and not conflict
    if portal_available:
        portal_unavailable_reason = None
    elif not is_owner:
        portal_unavailable_reason = (
            "Aktivierungscodes für das Mieterportal können nur Eigentümer erstellen."
        )
    elif conflict:
        portal_unavailable_reason = (
            "Das Mieterportal ist wegen widersprüchlicher aktueller Nutzungszeiträume "
            "nicht verfügbar."
        )
    else:
        portal_unavailable_reason = (
            "Das Mieterportal ist nur für ein aktuelles Mietverhältnis verfügbar."
        )
    return UnitDashboardResponse(
        as_of=as_of,
        id=unit.id,
        label=unit.label,
        area_sqm_x100=unit.area_sqm_x100,
        area_sqm_display=_format_fixed(unit.area_sqm_x100),
        building_id=unit.building_id,
        building_name=unit.building.name,
        building_address=(
            f"{unit.building.street}, {unit.building.postal_code} {unit.building.city}"
        ),
        state=state,
        state_label=STATE_LABELS[state],
        profile=_profile(session, unit, as_of),
        current_tenancy=current,
        history=visible_history,
        history_total=len(history),
        history_has_more=len(history) > len(visible_history),
        documents=documents,
        modules=[
            UnitDashboardModule(
                key="PAYMENTS",
                available=is_owner,
                unavailable_reason=(
                    None if is_owner else "Zahlungsdaten sind nur für Eigentümer verfügbar."
                ),
            ),
            UnitDashboardModule(
                key="PORTAL",
                available=portal_available,
                unavailable_reason=portal_unavailable_reason,
            ),
            UnitDashboardModule(
                key="MESSAGES",
                available=False,
                unavailable_reason="Nachrichten sind für diese Ansicht noch nicht verfügbar.",
            ),
            UnitDashboardModule(
                key="DOCUMENTS",
                available=is_owner,
                unavailable_reason=(
                    None if is_owner else "Archivdownloads sind nur für Eigentümer:innen verfügbar."
                ),
            ),
        ],
        primary_action=primary_action,
        permissions=UnitDashboardPermissions(
            can_edit_profile=is_owner,
            can_create_tenancy=is_owner,
            can_record_contract_facts=is_owner,
        ),
    )
