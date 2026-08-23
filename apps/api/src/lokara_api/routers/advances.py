"""M6-A owner-only temporal advances and confirmed owner preview evidence."""

from datetime import date

from fastapi import APIRouter, HTTPException
from lokara_db import (
    AdvanceAllocation,
    AdvancePayment,
    AdvancePaymentPeriod,
    AdvanceReconciliation,
    AdvanceReconciliationAllocation,
    Tenancy,
    new_id,
)
from sqlalchemy import select

from ..authorization import require_building, require_owner
from ..deps import PathAccountSession
from ..schemas import (
    AdvancePaymentCreate,
    AdvancePaymentOut,
    AdvanceReconciliationCreate,
    AdvanceReconciliationOut,
    AdvanceScheduleSuccessorCreate,
)

router = APIRouter(prefix="/a/{account_id}/buildings/{building_id}/tenancies/{tenancy_id}")


def _tenancy(session: PathAccountSession, building_id: str, tenancy_id: str) -> Tenancy:
    require_building(session, building_id)
    tenancy = session.get(Tenancy, tenancy_id)
    if tenancy is None or tenancy.unit.building_id != building_id:
        raise HTTPException(status_code=404, detail="Mietverhältnis nicht gefunden.")
    return tenancy


@router.post("/advance-payments", status_code=201)
def create_advance_payment(
    account_id: str,
    building_id: str,
    tenancy_id: str,
    body: AdvancePaymentCreate,
    session: PathAccountSession,
) -> AdvancePaymentOut:
    require_owner(session)
    _tenancy(session, building_id, tenancy_id)
    if body.period_end < body.period_start:
        raise HTTPException(
            status_code=422, detail="Das Ende liegt vor dem Beginn des Abrechnungszeitraums."
        )
    payment = AdvancePayment(
        id=new_id(),
        account_id=account_id,
        tenancy_id=tenancy_id,
        amount_cents=body.amount_cents,
        payment_date=body.payment_date,
        evidence_ref=body.evidence_ref,
        reversal_of_id=None,
    )
    allocation = AdvanceAllocation(
        id=new_id(),
        account_id=account_id,
        payment_id=payment.id,
        tenancy_id=tenancy_id,
        period_start=body.period_start,
        period_end=body.period_end,
        amount_cents=body.amount_cents,
    )
    session.add_all([payment, allocation])
    session.flush()
    return AdvancePaymentOut(
        id=payment.id,
        allocation_id=allocation.id,
        amount_cents=payment.amount_cents,
        payment_date=payment.payment_date,
        evidence_ref=payment.evidence_ref,
        reversal_of_id=None,
    )


@router.post("/advance-payments/{payment_id}/reversal", status_code=201)
def reverse_advance_payment(
    account_id: str, building_id: str, tenancy_id: str, payment_id: str, session: PathAccountSession
) -> AdvancePaymentOut:
    require_owner(session)
    _tenancy(session, building_id, tenancy_id)
    original = session.get(AdvancePayment, payment_id)
    if original is None or original.tenancy_id != tenancy_id or original.reversal_of_id is not None:
        raise HTTPException(status_code=404, detail="Vorauszahlung nicht gefunden.")
    original_allocation = session.scalar(
        select(AdvanceAllocation).where(AdvanceAllocation.payment_id == payment_id)
    )
    if original_allocation is None:
        raise HTTPException(status_code=422, detail="Zu dieser Vorauszahlung fehlt die Zuordnung.")
    reversal = AdvancePayment(
        id=new_id(),
        account_id=account_id,
        tenancy_id=tenancy_id,
        amount_cents=original.amount_cents,
        payment_date=date.today(),
        evidence_ref=f"Korrektur zu {original.evidence_ref}",
        reversal_of_id=original.id,
    )
    allocation = AdvanceAllocation(
        id=new_id(),
        account_id=account_id,
        payment_id=reversal.id,
        tenancy_id=tenancy_id,
        period_start=original_allocation.period_start,
        period_end=original_allocation.period_end,
        amount_cents=original_allocation.amount_cents,
    )
    session.add_all([reversal, allocation])
    session.flush()
    return AdvancePaymentOut(
        id=reversal.id,
        allocation_id=allocation.id,
        amount_cents=reversal.amount_cents,
        payment_date=reversal.payment_date,
        evidence_ref=reversal.evidence_ref,
        reversal_of_id=original.id,
    )


@router.post("/reconciliations", status_code=201)
def confirm_advance_reconciliation(
    account_id: str,
    building_id: str,
    tenancy_id: str,
    period_start: date,
    period_end: date,
    body: AdvanceReconciliationCreate,
    session: PathAccountSession,
) -> AdvanceReconciliationOut:
    require_owner(session)
    _tenancy(session, building_id, tenancy_id)
    if period_end < period_start:
        raise HTTPException(
            status_code=422, detail="Das Ende liegt vor dem Beginn des Abrechnungszeitraums."
        )
    allocation_ids = list(dict.fromkeys(body.allocation_ids))
    allocations = (
        session.scalars(
            select(AdvanceAllocation).where(AdvanceAllocation.id.in_(allocation_ids))
        ).all()
        if allocation_ids
        else []
    )
    if len(allocations) != len(allocation_ids) or any(
        row.tenancy_id != tenancy_id
        or row.period_start != period_start
        or row.period_end != period_end
        for row in allocations
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "Die Vorauszahlungszuordnungen passen nicht zu diesem Mietverhältnis und Zeitraum."
            ),
        )
    reversed_payments = session.scalars(
        select(AdvancePayment).where(AdvancePayment.reversal_of_id.is_not(None))
    ).all()
    reversal_ids = {row.id for row in reversed_payments}
    total = sum(
        -row.amount_cents if row.payment_id in reversal_ids else row.amount_cents
        for row in allocations
    )
    previous = session.scalar(
        select(AdvanceReconciliation)
        .where(
            AdvanceReconciliation.tenancy_id == tenancy_id,
            AdvanceReconciliation.period_start == period_start,
            AdvanceReconciliation.period_end == period_end,
        )
        .order_by(AdvanceReconciliation.version.desc())
    )
    reconciliation = AdvanceReconciliation(
        id=new_id(),
        account_id=account_id,
        tenancy_id=tenancy_id,
        period_start=period_start,
        period_end=period_end,
        version=(previous.version + 1 if previous else 1),
        total_cents=total,
        supersedes_id=previous.id if previous else None,
    )
    session.add(reconciliation)
    session.add_all(
        [
            AdvanceReconciliationAllocation(
                id=new_id(),
                account_id=account_id,
                reconciliation_id=reconciliation.id,
                allocation_id=row.id,
            )
            for row in allocations
        ]
    )
    session.flush()
    return AdvanceReconciliationOut(
        id=reconciliation.id,
        version=reconciliation.version,
        total_cents=total,
        allocation_ids=allocation_ids,
    )


@router.post("/advance-schedule", status_code=201)
def add_advance_schedule_successor(
    account_id: str,
    building_id: str,
    tenancy_id: str,
    body: AdvanceScheduleSuccessorCreate,
    session: PathAccountSession,
) -> dict[str, str]:
    require_owner(session)
    tenancy = _tenancy(session, building_id, tenancy_id)
    if body.valid_from < tenancy.valid_from or (
        tenancy.valid_to is not None and body.valid_from >= tenancy.valid_to
    ):
        raise HTTPException(status_code=422, detail="Der Beginn liegt nicht im Mietverhältnis.")
    predecessor = session.scalar(
        select(AdvancePaymentPeriod)
        .where(
            AdvancePaymentPeriod.tenancy_id == tenancy_id,
            AdvancePaymentPeriod.valid_from < body.valid_from,
        )
        .order_by(AdvancePaymentPeriod.valid_from.desc())
    )
    if (
        predecessor is None
        or session.scalar(
            select(AdvancePaymentPeriod).where(
                AdvancePaymentPeriod.tenancy_id == tenancy_id,
                AdvancePaymentPeriod.valid_from == body.valid_from,
            )
        )
        is not None
    ):
        raise HTTPException(
            status_code=422,
            detail="Der Vorauszahlungsbeginn muss einem bestehenden Zeitraum folgen.",
        )
    successor = AdvancePaymentPeriod(
        id=new_id(),
        account_id=account_id,
        tenancy_id=tenancy_id,
        amount_cents=body.amount_cents,
        valid_from=body.valid_from,
        predecessor_id=predecessor.id,
        declaration_ref=body.declaration_ref,
    )
    session.add(successor)
    session.flush()
    return {"id": successor.id}
