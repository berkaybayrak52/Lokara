"""Renter-scoped portal routes."""

from fastapi import APIRouter, HTTPException
from lokara_db import Building, Tenancy, Unit
from sqlalchemy import and_, select

from ..auth import RequireAuth
from ..deps import PathRenterSession, resolve_bootstrap_subject
from ..schemas import RenterOverviewResponse

router = APIRouter()


@router.get("/renter/{tenancy_id}", response_model=RenterOverviewResponse)
def renter_overview(
    tenancy_id: str,
    auth: RequireAuth,
    session: PathRenterSession,
) -> RenterOverviewResponse:
    contexts = resolve_bootstrap_subject(auth)
    if not any(
        context.context_kind == "RENTER_TENANCY" and context.tenancy_id == tenancy_id
        for context in contexts
    ):
        raise HTTPException(status_code=404, detail="Mietverhältnis nicht gefunden.")

    row = session.execute(
        select(
            Tenancy.id,
            Tenancy.valid_from,
            Tenancy.valid_to,
            Unit.label,
            Building.name,
            Building.street,
            Building.postal_code,
            Building.city,
        )
        .join(
            Unit,
            and_(Unit.id == Tenancy.unit_id, Unit.account_id == Tenancy.account_id),
        )
        .join(
            Building,
            and_(Building.id == Unit.building_id, Building.account_id == Unit.account_id),
        )
        .where(Tenancy.id == tenancy_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Mietverhältnis nicht gefunden.")

    return RenterOverviewResponse(
        tenancy_id=str(row.id),
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        unit_label=str(row.label),
        building_name=str(row.name),
        street=str(row.street),
        postal_code=str(row.postal_code),
        city=str(row.city),
    )
