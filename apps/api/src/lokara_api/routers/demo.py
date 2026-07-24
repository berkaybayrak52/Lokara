"""Guarded demo endpoint proving the Phase E spine: JWT auth → membership
check → RLS-scoped session → typed contract response (consumed by apps/web)."""

from fastapi import APIRouter, HTTPException
from lokara_db import Account, Building
from lokara_domain import cents, format_eur
from sqlalchemy import select

from ..auth import RequireAuth
from ..deps import AccountSession
from ..schemas import DemoSummaryResponse, DemoTenancySummary

router = APIRouter(prefix="/demo")


@router.get("/summary")
def summary(auth: RequireAuth, session: AccountSession) -> DemoSummaryResponse:
    account = session.get(Account, auth.account_id)
    building = session.scalars(select(Building).limit(1)).first()
    if account is None or building is None:
        raise HTTPException(
            status_code=404, detail="No demo data — run `uv run lokara-seed-demo` first."
        )

    tenancies: list[DemoTenancySummary] = []
    for unit in sorted(building.units, key=lambda u: u.label):
        for tenancy in unit.tenancies:
            tenancies.append(
                DemoTenancySummary(
                    unit_label=unit.label,
                    area_sqm=unit.area_sqm_x100 / 100,
                    renter_names=[party.renter.legal_name for party in tenancy.parties],
                    valid_from=tenancy.valid_from.isoformat(),
                    valid_to=tenancy.valid_to.isoformat() if tenancy.valid_to else None,
                    base_rent_eur=format_eur(cents(tenancy.base_rent_cents)),
                )
            )
    return DemoSummaryResponse(
        account_name=account.name,
        building_name=building.name,
        building_address=f"{building.street}, {building.postal_code} {building.city}",
        unit_count=len(building.units),
        tenancies=tenancies,
    )
