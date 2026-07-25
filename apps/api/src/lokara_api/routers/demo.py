"""Guarded demo endpoint proving the Phase E spine: JWT auth → membership
check → RLS-scoped session → typed contract response (consumed by apps/web)."""

from fastapi import APIRouter, HTTPException
from lokara_db import Account, Building
from lokara_db.seed import DEMO_ACCOUNT_ID, seed_demo
from lokara_domain import cents, format_eur
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import RequireAuth
from ..deps import AccountSession, raw_account_scoped_session
from ..schemas import DemoLoadResponse, DemoSummaryResponse, DemoTenancySummary

router = APIRouter(prefix="/demo")


@router.post("/load")
def load(auth: RequireAuth) -> DemoLoadResponse:
    """One-click "Demo-Szenario laden" (docs/04 Dashboard, docs/06).

    Idempotent merge of the fixed demo fixture — including the OWNER Membership
    this endpoint would otherwise be gated on, so it runs on the raw scoped
    session; RLS confines every write to the demo account context underneath.
    TODO(M5): restrict to the caller's own sandbox once real accounts exist.
    """
    del auth  # any authenticated caller may (re)load the fixed demo fixture
    with raw_account_scoped_session(DEMO_ACCOUNT_ID) as session:
        seed_demo(session)
    return DemoLoadResponse(ok=True, account_id=DEMO_ACCOUNT_ID)


def summary_response(session: Session, account: Account | None) -> DemoSummaryResponse:
    """Shared builder — also serves the URL-scoped /a/{account_id}/summary."""
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


@router.get("/summary")
def summary(auth: RequireAuth, session: AccountSession) -> DemoSummaryResponse:
    return summary_response(session, session.get(Account, auth.account_id))
