"""Objekte / Einheiten / Mietverhältnisse — the M3 CRUD (docs/04 pages 2+3).

URL-scoped like every portal route: `PathAccountSession` verifies the caller's
Membership in the path account and sets the RLS context; every INSERT carries
that `account_id`, and the WITH CHECK policies underneath refuse anything else.

Temporal rows are create-only here: a Tenancy is immutable once written
(corrections are new versions — CLAUDE.md rule 2); the M-later edit flows will
version, never UPDATE.
"""

from datetime import date

from fastapi import APIRouter, HTTPException
from lokara_db import Building, Renter, Tenancy, TenancyParty, Unit, new_id
from lokara_domain import Period, cents, format_eur, periods_overlap
from sqlalchemy import select

from ..deps import PathAccountSession
from ..schemas import (
    BuildingCreate,
    BuildingDetailResponse,
    BuildingListResponse,
    BuildingSummary,
    SelfUsePeriodOut,
    TenancyCreate,
    TenancyOut,
    UnitCreate,
    UnitDetailResponse,
    UnitSummary,
)

router = APIRouter(prefix="/a/{account_id}")


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
    )


@router.get("/buildings")
def list_buildings(account_id: str, session: PathAccountSession) -> BuildingListResponse:
    del account_id  # scoping happened in the dependency (RLS + membership)
    buildings = session.scalars(
        select(Building).order_by(Building.created_at, Building.id)
    ).all()
    return BuildingListResponse(buildings=[_building_summary(b) for b in buildings])


@router.post("/buildings", status_code=201)
def create_building(
    account_id: str, body: BuildingCreate, session: PathAccountSession
) -> BuildingSummary:
    building = Building(
        id=new_id(),
        account_id=account_id,  # WITH CHECK refuses any other value
        name=body.name,
        street=body.street,
        postal_code=body.postal_code,
        city=body.city,
    )
    session.add(building)
    session.flush()
    return _building_summary(building)


def _get_building(session: PathAccountSession, building_id: str) -> Building:
    building = session.get(Building, building_id)
    if building is None:  # unknown OR invisible under RLS — same answer
        raise HTTPException(status_code=404, detail="Building not found")
    return building


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
            occupied_today=any(
                _is_active_today(t.valid_from, t.valid_to) for t in unit.tenancies
            ),
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
    return TenancyOut(
        id=tenancy.id,
        renter_names=[party.renter.legal_name for party in tenancy.parties],
        valid_from=tenancy.valid_from,
        valid_to=tenancy.valid_to,
        base_rent_cents=tenancy.base_rent_cents,
        base_rent_eur=format_eur(cents(tenancy.base_rent_cents)),
        advance_payment_cents=tenancy.advance_payment_cents,
        advance_payment_eur=format_eur(cents(tenancy.advance_payment_cents)),
        active_today=_is_active_today(tenancy.valid_from, tenancy.valid_to),
    )


def _get_unit(session: PathAccountSession, unit_id: str) -> Unit:
    unit = session.get(Unit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit


@router.get("/units/{unit_id}")
def unit_detail(
    account_id: str, unit_id: str, session: PathAccountSession
) -> UnitDetailResponse:
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
        advance_payment_cents=body.advance_payment_cents,
    )
    party = TenancyParty(
        id=new_id(), account_id=account_id, tenancy_id=tenancy.id, renter_id=renter.id
    )
    session.add_all([renter, tenancy, party])
    session.flush()
    session.refresh(tenancy)
    return _tenancy_out(tenancy)
