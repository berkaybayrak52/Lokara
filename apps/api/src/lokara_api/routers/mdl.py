"""Confirmed Messdienstleister statements (docs/03 H7, docs/08 § 8).

The M4 shape, applied to a second document type: extraction proposes, nothing
is written, and this endpoint is the confirm step. What makes it more than a
create endpoint is that it **refuses** a statement the engine cannot accept —
an OCR decimal shift shows up as a control-sum mismatch, and `01b-F29` requires
that to block rather than to produce a wrong Abrechnung.

So the engine is dry-run against the submitted figures before anything is
persisted. A row that exists here is one that already produced a READY result;
a rejected upload leaves no trace to clean up.
"""

from datetime import timedelta

from fastapi import APIRouter, HTTPException, status
from lokara_db import Building, MdlBranch, MdlStatement, MdlStatementPosition
from lokara_domain import Period
from lokara_heating_engine import calculate_page01b_statement
from lokara_rules_store import CO2_SPLIT_TABLE, get_rule
from sqlalchemy import select

from ..deps import PathAccountSession
from ..schemas import MdlStatementCreate, MdlStatementOut
from ..statement_service import RULES_AS_OF, mdl_statement_input, period_label

router = APIRouter(prefix="/a/{account_id}")


@router.post("/buildings/{building_id}/mdl-statements", status_code=status.HTTP_201_CREATED)
def confirm_mdl_statement(
    account_id: str,
    building_id: str,
    body: MdlStatementCreate,
    session: PathAccountSession,
) -> MdlStatementOut:
    """Confirm one Messdienstleister statement for one building period.

    `period_to` is inclusive in the request, half-open in storage.

    A correction is a new call: it appends `version + 1` and leaves the earlier
    confirmation in place (`CLAUDE.md` § 3.2). Nothing here updates a row.
    """
    del account_id  # scoping happened in the dependency
    building = session.scalars(select(Building).where(Building.id == building_id)).first()
    if building is None:
        raise HTTPException(status_code=404, detail="Objekt nicht gefunden.")

    # Each position's tenancy must belong to *this* building. RLS already keeps
    # another account out; this closes the same-account, wrong-building case,
    # which is the relationship carried in the URL (`CLAUDE.md` § 3.3).
    own_tenancies = {tenancy.id for unit in building.units for tenancy in unit.tenancies}
    foreign = [p.tenancy_id for p in body.positions if p.tenancy_id not in own_tenancies]
    if foreign:
        raise HTTPException(
            status_code=404,
            detail=f"Mietverhältnis nicht in diesem Objekt: {', '.join(sorted(foreign))}.",
        )

    window = Period(valid_from=body.period_from, valid_to=body.period_to + timedelta(days=1))
    row = MdlStatement(
        account_id=building.account_id,
        building_id=building.id,
        branch=MdlBranch(body.branch),
        period_from=window.valid_from,
        period_to=window.valid_to,
        confirmed_total_cents=body.confirmed_total_cents,
        owner_position_cents=body.owner_position_cents,
        co2_kg_x1000=body.co2_kg_x1000,
        co2_cost_cents=body.co2_cost_cents,
        heated_area_sqm_x100=body.heated_area_sqm_x100,
        co2_evidence_present=body.co2_evidence_present,
        source_ref=body.source_ref,
        version=_next_version(session, building.id, window),
        positions=[
            MdlStatementPosition(
                account_id=building.account_id,
                tenancy_id=position.tenancy_id,
                amount_cents=position.amount_cents,
            )
            for position in body.positions
        ],
    )

    # Dry run before the write. The engine owns the control-sum tolerance and
    # the branch rules; re-deriving them here would give two answers that can
    # drift apart, and the one that matters is the one the statement will use.
    probe = calculate_page01b_statement(
        mdl_statement_input(row, get_rule(CO2_SPLIT_TABLE, RULES_AS_OF), window)
    )
    if probe.readiness != "READY":
        raise HTTPException(status_code=422, detail=probe.findings[0].message_de)

    session.add(row)
    session.flush()
    return MdlStatementOut(
        id=row.id,
        branch=row.branch.value,
        period_label=period_label(window),
        confirmed_total_cents=row.confirmed_total_cents,
        owner_position_cents=row.owner_position_cents,
        position_count=len(row.positions),
        source_ref=row.source_ref,
        version=row.version,
    )


def _next_version(session: PathAccountSession, building_id: str, window: Period) -> int:
    """One past the highest confirmation for this exact building period."""
    latest = session.scalars(
        select(MdlStatement)
        .where(
            MdlStatement.building_id == building_id,
            MdlStatement.period_from == window.valid_from,
            MdlStatement.period_to == window.valid_to,
        )
        .order_by(MdlStatement.version.desc())
    ).first()
    return 1 if latest is None else latest.version + 1


@router.get("/buildings/{building_id}/mdl-statements")
def list_mdl_statements(
    account_id: str, building_id: str, session: PathAccountSession
) -> list[MdlStatementOut]:
    """Every confirmation for this building, newest period and version first.

    Superseded versions are listed too: an append-only record whose earlier
    versions are invisible is not auditable.
    """
    del account_id
    rows = session.scalars(
        select(MdlStatement)
        .where(MdlStatement.building_id == building_id)
        .order_by(MdlStatement.period_from.desc(), MdlStatement.version.desc())
    ).all()
    return [
        MdlStatementOut(
            id=row.id,
            branch=row.branch.value,
            period_label=period_label(Period(valid_from=row.period_from, valid_to=row.period_to)),
            confirmed_total_cents=row.confirmed_total_cents,
            owner_position_cents=row.owner_position_cents,
            position_count=len(row.positions),
            source_ref=row.source_ref,
            version=row.version,
        )
        for row in rows
    ]
