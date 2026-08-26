"""Objekte / Einheiten / Mietverhältnisse — the M3 CRUD (docs/04 pages 2+3).

URL-scoped like every portal route: `PathAccountSession` verifies the caller's
Membership in the path account and sets the RLS context; every INSERT carries
that `account_id`, and the WITH CHECK policies underneath refuse anything else.

Temporal rows are create-only here: a Tenancy is immutable once written
(corrections are new versions — CLAUDE.md rule 2); the M-later edit flows will
version, never UPDATE.
"""

from datetime import UTC, date, datetime
from functools import lru_cache
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response
from lokara_adapters.geocoding import DisabledGeocodingGateway, GeocodingGateway
from lokara_db import AdvancePaymentPeriod, Building, Renter, Tenancy, TenancyParty, Unit, new_id
from lokara_domain import Period, cents, format_eur, periods_overlap
from lokara_pdf import (
    building_overview_filename,
    building_overview_html,
    render_html_to_pdf,
)
from sqlalchemy import select

from ..authorization import (
    portal_role,
    require_building,
    require_owner,
    require_resource_building,
    visible_building_ids,
)
from ..building_dashboard import build_dashboard, building_overview_data
from ..deps import PathAccountSession
from ..geocoding_http import NominatimGeocodingGateway
from ..schemas import (
    AdvancePaymentPeriodOut,
    BuildingCreate,
    BuildingDashboardResponse,
    BuildingDetailResponse,
    BuildingListResponse,
    BuildingSummary,
    SelfUsePeriodOut,
    TenancyCreate,
    TenancyOut,
    TenancyPreviewChoice,
    UnitCreate,
    UnitDetailResponse,
    UnitSummary,
)
from ..settings import ApiSettings

router = APIRouter(prefix="/a/{account_id}")


@lru_cache(maxsize=1)
def get_geocoding_gateway() -> GeocodingGateway:
    """Build the configured external-edge adapter once per API process."""
    settings = ApiSettings()
    if not settings.geocoding_enabled:
        return DisabledGeocodingGateway()
    return NominatimGeocodingGateway(
        endpoint=settings.geocoding_endpoint,
        contact_email=settings.geocoding_contact_email,
        timeout_seconds=settings.geocoding_timeout_seconds,
    )


def _is_active_today(valid_from: date, valid_to: date | None) -> bool:
    today = date.today()
    return valid_from <= today and (valid_to is None or today < valid_to)


def _building_summary(building: Building) -> BuildingSummary:
    return BuildingSummary(
        id=building.id,
        name=building.name,
        street=building.street,
        postal_code=building.postal_code,
        city=building.city,
        unit_count=len(building.units),
        building_type=building.building_type,
        latitude=building.latitude,
        longitude=building.longitude,
    )


@router.get("/buildings")
def list_buildings(account_id: str, session: PathAccountSession) -> BuildingListResponse:
    del account_id  # scoping happened in the dependency (RLS + membership)
    buildings = session.scalars(
        select(Building)
        .where(Building.archived_at.is_(None))
        .order_by(Building.created_at, Building.id)
    ).all()
    visible_ids = visible_building_ids(session)
    if visible_ids is not None:
        buildings = [building for building in buildings if building.id in visible_ids]
    return BuildingListResponse(buildings=[_building_summary(b) for b in buildings])


@router.post("/buildings", status_code=201)
def create_building(
    account_id: str,
    body: BuildingCreate,
    session: PathAccountSession,
    geocoding: Annotated[GeocodingGateway, Depends(get_geocoding_gateway)],
) -> BuildingSummary:
    require_owner(session)
    street = f"{body.street} {body.house_number}"
    address = f"{street}, {body.postal_code} {body.city}, {body.country}"
    latitude: float | None = None
    longitude: float | None = None
    try:
        coordinates = geocoding.geocode(address)
        if coordinates is not None:
            latitude = coordinates.latitude
            longitude = coordinates.longitude
    except Exception:
        # Geocoding is enrichment only. Provider/network failures must never
        # prevent the account-scoped building write.
        pass
    building = Building(
        id=new_id(),
        account_id=account_id,  # WITH CHECK refuses any other value
        name=body.name,
        street=street,
        postal_code=body.postal_code,
        city=body.city,
        building_type=body.building_type,
        is_residential=body.is_residential,
        country=body.country,
        latitude=latitude,
        longitude=longitude,
    )
    session.add(building)
    session.flush()
    return _building_summary(building)


def _get_building(session: PathAccountSession, building_id: str) -> Building:
    return require_building(session, building_id)


@router.get("/buildings/{building_id}")
def building_detail(
    account_id: str, building_id: str, session: PathAccountSession
) -> BuildingDetailResponse:
    del account_id
    building = _get_building(session, building_id)
    units = [
        UnitSummary(
            id=unit.id,
            label=unit.label,
            area_sqm=unit.area_sqm_x100 / 100,
            tenancy_count=len(unit.tenancies),
            occupied_today=any(_is_active_today(t.valid_from, t.valid_to) for t in unit.tenancies),
        )
        for unit in sorted(building.units, key=lambda u: u.label)
    ]
    return BuildingDetailResponse(
        id=building.id,
        name=building.name,
        street=building.street,
        postal_code=building.postal_code,
        city=building.city,
        units=units,
    )


@router.get("/buildings/{building_id}/dashboard")
def building_dashboard(
    account_id: str, building_id: str, session: PathAccountSession
) -> BuildingDashboardResponse:
    """One server-owned read model for the Objektakte (04_Objekt-Dashboard.md OD1).

    Separate from `GET /buildings/{building_id}` on purpose: the lean consumers of
    the detail contract should not be made to load every financial and module
    projection to render a unit list.
    """
    building = _get_building(session, building_id)
    return build_dashboard(
        session,
        account_id=account_id,
        building=building,
        role=portal_role(session),
        as_of=date.today(),
    )


@router.get("/buildings/{building_id}/overview.pdf")
def building_overview_pdf(
    account_id: str, building_id: str, session: PathAccountSession
) -> Response:
    """Server-rendered object overview from the same snapshot the page shows.

    Owner-only, and refused server-side rather than hidden in the UI (OD14).
    The renderer receives finished strings; it recomputes nothing (OD13).
    """
    require_owner(session)
    building = _get_building(session, building_id)
    dashboard = build_dashboard(
        session,
        account_id=account_id,
        building=building,
        role=portal_role(session),
        as_of=date.today(),
    )
    document = building_overview_data(dashboard, generated_at=datetime.now(UTC))
    pdf = render_html_to_pdf(building_overview_html(document))
    filename = building_overview_filename(dashboard.name, dashboard.as_of)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{quote(filename)}"'},
    )


@router.get("/buildings/{building_id}/tenancies")
def list_building_tenancies(
    account_id: str, building_id: str, session: PathAccountSession
) -> list[TenancyPreviewChoice]:
    del account_id
    building = _get_building(session, building_id)
    return [
        TenancyPreviewChoice(
            id=tenancy.id,
            label=(
                f"{unit.label} — {', '.join(party.renter.legal_name for party in tenancy.parties)}"
            ),
        )
        for unit in sorted(building.units, key=lambda item: item.label)
        for tenancy in sorted(unit.tenancies, key=lambda item: item.valid_from)
    ]


@router.post("/buildings/{building_id}/units", status_code=201)
def create_unit(
    account_id: str, building_id: str, body: UnitCreate, session: PathAccountSession
) -> UnitSummary:
    building = _get_building(session, building_id)
    unit = Unit(
        id=new_id(),
        account_id=account_id,
        building_id=building.id,
        label=body.label,
        area_sqm_x100=body.area_sqm_x100,
    )
    session.add(unit)
    session.flush()
    return UnitSummary(
        id=unit.id,
        label=unit.label,
        area_sqm=unit.area_sqm_x100 / 100,
        tenancy_count=0,
        occupied_today=False,
    )


def _tenancy_out(tenancy: Tenancy) -> TenancyOut:
    periods = sorted(tenancy.advance_payment_periods, key=lambda item: item.valid_from)
    return TenancyOut(
        id=tenancy.id,
        renter_names=[party.renter.legal_name for party in tenancy.parties],
        valid_from=tenancy.valid_from,
        valid_to=tenancy.valid_to,
        base_rent_cents=tenancy.base_rent_cents,
        base_rent_eur=format_eur(cents(tenancy.base_rent_cents)),
        advance_payment_schedule=[
            AdvancePaymentPeriodOut(
                id=item.id,
                amount_cents=item.amount_cents,
                amount_eur=format_eur(cents(item.amount_cents)),
                valid_from=item.valid_from,
                valid_to=(periods[index + 1].valid_from if index + 1 < len(periods) else None),
                predecessor_id=item.predecessor_id,
                declaration_ref=item.declaration_ref,
            )
            for index, item in enumerate(periods)
        ],
        active_today=_is_active_today(tenancy.valid_from, tenancy.valid_to),
    )


def _get_unit(session: PathAccountSession, unit_id: str) -> Unit:
    unit = session.get(Unit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    require_resource_building(session, unit.building_id)
    return unit


@router.get("/units/{unit_id}")
def unit_detail(account_id: str, unit_id: str, session: PathAccountSession) -> UnitDetailResponse:
    del account_id
    unit = _get_unit(session, unit_id)
    tenancies = sorted(unit.tenancies, key=lambda t: t.valid_from, reverse=True)
    self_use = sorted(unit.self_use_periods, key=lambda s: s.valid_from, reverse=True)
    return UnitDetailResponse(
        id=unit.id,
        label=unit.label,
        area_sqm=unit.area_sqm_x100 / 100,
        building_id=unit.building_id,
        building_name=unit.building.name,
        tenancies=[_tenancy_out(t) for t in tenancies],
        self_use_periods=[
            SelfUsePeriodOut(kind=s.kind.value, valid_from=s.valid_from, valid_to=s.valid_to)
            for s in self_use
        ],
    )


@router.post("/units/{unit_id}/tenancies", status_code=201)
def create_tenancy(
    account_id: str, unit_id: str, body: TenancyCreate, session: PathAccountSession
) -> TenancyOut:
    unit = _get_unit(session, unit_id)

    # docs/02 invariant: a unit's tenancy periods never overlap. Period itself
    # rejects valid_to <= valid_from.
    try:
        new_period = Period(valid_from=body.valid_from, valid_to=body.valid_to)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    for existing in unit.tenancies:
        existing_period = Period(valid_from=existing.valid_from, valid_to=existing.valid_to)
        if periods_overlap(new_period, existing_period):
            raise HTTPException(
                status_code=422,
                detail=(
                    "Tenancy overlaps an existing one "
                    f"({existing.valid_from.isoformat()} – "
                    f"{existing.valid_to.isoformat() if existing.valid_to else 'offen'})"
                ),
            )

    renter = Renter(id=new_id(), account_id=account_id, legal_name=body.renter_name)
    tenancy = Tenancy(
        id=new_id(),
        account_id=account_id,
        unit_id=unit.id,
        valid_from=body.valid_from,
        valid_to=body.valid_to,
        base_rent_cents=body.base_rent_cents,
    )
    schedule = AdvancePaymentPeriod(
        id=new_id(),
        account_id=account_id,
        tenancy_id=tenancy.id,
        amount_cents=body.initial_advance_payment_cents,
        valid_from=body.valid_from,
        predecessor_id=None,
        declaration_ref=body.advance_declaration_ref,
    )
    party = TenancyParty(
        id=new_id(), account_id=account_id, tenancy_id=tenancy.id, renter_id=renter.id
    )
    session.add_all([renter, tenancy, party, schedule])
    session.flush()
    session.refresh(tenancy)
    return _tenancy_out(tenancy)
