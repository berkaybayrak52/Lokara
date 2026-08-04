"""Kosten erfassen (docs/04 M3 page 4) — cost entries + their allocation keys.

The key is never stored on the cost row: choosing (or changing) it INSERTs an
`AllocationKeyAssignment`. Re-keying therefore re-runs the calculation and
**deletes no entered data** — the old assignment stays as history (docs/03).
"""

from fastapi import APIRouter, HTTPException
from lokara_db import AllocationKeyAssignment, CostEntry, Tenancy, Unit, new_id
from lokara_domain import AllocationKey, cents, format_eur
from sqlalchemy import select

from ..deps import PathAccountSession
from ..schemas import CostCreate, CostEntryOut, CostListResponse, KeyChoice

router = APIRouter(prefix="/a/{account_id}")

ALLOCATION_KEY_LABELS: dict[AllocationKey, str] = {
    AllocationKey.AREA: "Wohnfläche (m²·Tage)",
    AllocationKey.PERSONS: "Personenzahl (Personen·Tage)",
    AllocationKey.CONSUMPTION: "Verbrauch",
    AllocationKey.UNITS: "Einheiten (Einheiten·Tage)",
    AllocationKey.DIRECT: "Direktzuordnung",
    AllocationKey.MEA: "Miteigentumsanteile (MEA·Tage)",
}


def current_assignment(cost: CostEntry) -> AllocationKeyAssignment:
    """The newest assignment wins; ties broken by id so the order is total.

    A cost always has at least one — creation writes it in the same
    transaction, so a missing one is a bug, not a user-facing state.
    """
    if not cost.key_assignments:
        raise HTTPException(
            status_code=500, detail=f"Cost {cost.id} has no allocation key assignment"
        )
    return max(cost.key_assignments, key=lambda a: (a.created_at, a.id))


def _cost_out(cost: CostEntry) -> CostEntryOut:
    assignment = current_assignment(cost)
    return CostEntryOut(
        id=cost.id,
        label=cost.label,
        amount_cents=cost.amount_cents,
        amount_eur=format_eur(cents(cost.amount_cents)),
        period_from=cost.period_from,
        period_to=cost.period_to,
        key=assignment.key,
        key_label=ALLOCATION_KEY_LABELS[assignment.key],
        direct_unit_id=assignment.direct_unit_id,
        direct_tenancy_id=assignment.direct_tenancy_id,
        assignment_count=len(cost.key_assignments),
    )


def _validate_direct_target(
    session: PathAccountSession, building_id: str, choice: KeyChoice
) -> None:
    """A DIRECT target must be a unit (or a tenancy of a unit) in THIS building.
    RLS already confines the lookup to the account."""
    if choice.key is not AllocationKey.DIRECT:
        return
    unit_id = choice.direct_unit_id
    if choice.direct_tenancy_id is not None:
        tenancy = session.get(Tenancy, choice.direct_tenancy_id)
        if tenancy is None:
            raise HTTPException(status_code=422, detail="Unknown direct tenancy")
        unit_id = tenancy.unit_id
    if unit_id is None:
        raise HTTPException(status_code=422, detail="DIRECT requires a target")
    unit = session.get(Unit, unit_id)
    if unit is None or unit.building_id != building_id:
        raise HTTPException(status_code=422, detail="Direct target is not in this building")


@router.get("/buildings/{building_id}/costs")
def list_costs(account_id: str, building_id: str, session: PathAccountSession) -> CostListResponse:
    del account_id  # scoping happened in the dependency
    costs = session.scalars(
        select(CostEntry)
        .where(CostEntry.building_id == building_id)
        .order_by(CostEntry.created_at, CostEntry.id)
    ).all()
    return CostListResponse(costs=[_cost_out(c) for c in costs])


@router.post("/buildings/{building_id}/costs", status_code=201)
def create_cost(
    account_id: str, building_id: str, body: CostCreate, session: PathAccountSession
) -> CostEntryOut:
    _validate_direct_target(session, building_id, body)
    cost = CostEntry(
        id=new_id(),
        account_id=account_id,
        building_id=building_id,
        label=body.label,
        amount_cents=body.amount_cents,
        period_from=body.period_from,
        period_to=body.period_to,
    )
    assignment = AllocationKeyAssignment(
        id=new_id(),
        account_id=account_id,
        cost_entry_id=cost.id,
        key=body.key,
        direct_unit_id=body.direct_unit_id,
        direct_tenancy_id=body.direct_tenancy_id,
    )
    session.add_all([cost, assignment])
    session.flush()
    session.refresh(cost)
    return _cost_out(cost)


@router.delete("/costs/{cost_id}", status_code=204)
def delete_cost(account_id: str, cost_id: str, session: PathAccountSession) -> None:
    """Removes a mis-entered cost and its assignment history.

    Deliberately a real DELETE, not a soft one: a cost entry is *input*, not a
    legally-relevant record — the immutability rule (CLAUDE.md rule 2) binds
    what is *issued* (statements, exports, ledger). TODO(M4): refuse once a
    FINALIZED statement covers the cost's period; a correction then becomes a
    new statement version instead.
    """
    del account_id
    cost = session.get(CostEntry, cost_id)
    if cost is None:
        raise HTTPException(status_code=404, detail="Cost entry not found")
    for assignment in list(cost.key_assignments):
        session.delete(assignment)
    session.delete(cost)


@router.post("/costs/{cost_id}/key")
def reassign_key(
    account_id: str, cost_id: str, body: KeyChoice, session: PathAccountSession
) -> CostEntryOut:
    """Change the Umlageschlüssel: appends a new assignment, never an UPDATE.

    The cost row and every prior assignment stay exactly as entered — that is
    the objego/immocloud pain point this product refuses to reproduce
    (docs/06 Scenario 3).
    """
    cost = session.get(CostEntry, cost_id)
    if cost is None:  # unknown OR invisible under RLS — same answer
        raise HTTPException(status_code=404, detail="Cost entry not found")
    _validate_direct_target(session, cost.building_id, body)
    session.add(
        AllocationKeyAssignment(
            id=new_id(),
            account_id=account_id,
            cost_entry_id=cost.id,
            key=body.key,
            direct_unit_id=body.direct_unit_id,
            direct_tenancy_id=body.direct_tenancy_id,
        )
    )
    session.flush()
    session.refresh(cost)
    return _cost_out(cost)
