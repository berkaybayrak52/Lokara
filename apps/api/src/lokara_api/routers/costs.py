"""Kosten erfassen (docs/04 M3 page 4) — cost entries + their allocation keys.

The key is never stored on the cost row: choosing (or changing) it INSERTs an
`AllocationKeyAssignment`. Re-keying therefore re-runs the calculation and
**deletes no entered data** — the old assignment stays as history (docs/03).
"""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from lokara_db import (
    AllocationKeyAssignment,
    Building,
    ConfirmedCostClassification,
    CostEntry,
    OperatingCostAgreement,
    Tenancy,
    Unit,
    new_id,
)
from lokara_domain import AllocationKey, cents, format_eur
from lokara_rules_store import CataloguePosition, ContractFacts, classify_position
from sqlalchemy import select

from ..deps import PathAccountSession
from ..schemas import (
    CostCreate,
    CostEntryOut,
    CostListResponse,
    CostVoid,
    CostVoidOut,
    KeyChoice,
    OperatingCostAgreementIn,
    OperatingCostAgreementOut,
)

router = APIRouter(prefix="/a/{account_id}")

ALLOCATION_KEY_LABELS: dict[AllocationKey, str] = {
    AllocationKey.AREA: "Wohnfläche (m²·Tage)",
    AllocationKey.PERSONS: "Personenzahl (Personen·Tage)",
    AllocationKey.CONSUMPTION: "Verbrauch",
    AllocationKey.UNITS: "Einheiten (Einheiten·Tage)",
    AllocationKey.DIRECT: "Direktzuordnung",
    AllocationKey.MEA: "Miteigentumsanteile (MEA·Tage)",
}


def _get_building(session: PathAccountSession, building_id: str) -> Building:
    """Resolve a URL building under RLS before reading or writing its costs."""
    building = session.scalar(
        select(Building).where(Building.id == building_id, Building.archived_at.is_(None))
    )
    if building is None:  # unknown, archived, or invisible under RLS
        raise HTTPException(status_code=404, detail="Building not found")
    return building


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
    classification = max(
        cost.classifications, key=lambda row: (row.confirmed_at, row.id), default=None
    )
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
        catalogue_id=None if classification is None else classification.catalogue_id,
        classification_findings=[] if classification is None else classification.findings,
        production_blocked=False if classification is None else classification.production_blocked,
        voided_at=cost.voided_at,
        void_reason=cost.void_reason,
        replaces_cost_id=cost.replaces_cost_entry_id,
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
    _get_building(session, building_id)
    costs = session.scalars(
        select(CostEntry)
        .where(CostEntry.building_id == building_id)
        .where(CostEntry.voided_at.is_(None))
        .order_by(CostEntry.created_at, CostEntry.id)
    ).all()
    return CostListResponse(costs=[_cost_out(c) for c in costs])


@router.post("/buildings/{building_id}/costs", status_code=201)
def create_cost(
    account_id: str, building_id: str, body: CostCreate, session: PathAccountSession
) -> CostEntryOut:
    _get_building(session, building_id)
    # New manual/OCR-confirmation flow: the catalogue identity is mandatory;
    # free-text remains evidence/label only. No contract fact is inferred here.
    result = classify_position(
        CataloguePosition(
            body.catalogue_id,
            body.amount_cents,
            receipt_date=body.payment_date or body.invoice_date or body.period_to,
            non_allocable_cents=body.non_allocable_cents,
            labour_cents=body.labour_cents,
            key_override=body.key_override,
            service_from=body.service_from,
            service_to=body.service_to,
            evidence=frozenset(body.special_rule_evidence),
        ),
        # Classification is object-level.  Per-renter agreement/naming is
        # supplied by immutable temporal agreement rows at calculation time.
        ContractFacts(
            allocation_agreed=True,
            named_other_costs=frozenset({body.catalogue_id}),
            mehrbelastung_clause=True,
        ),
    )
    if result.key is None:
        raise HTTPException(status_code=422, detail="Kostenart ist nicht umlagefähig")
    choice = KeyChoice(
        key=result.key,
        direct_unit_id=body.direct_unit_id,
        direct_tenancy_id=body.direct_tenancy_id,
    )
    _validate_direct_target(session, building_id, choice)
    if body.replaces_cost_id is not None:
        replaced = session.get(CostEntry, body.replaces_cost_id)
        if replaced is None or replaced.building_id != building_id or replaced.voided_at is None:
            raise HTTPException(
                status_code=422,
                detail="Replacement must refer to a voided cost of this building",
            )
    cost = CostEntry(
        id=new_id(),
        account_id=account_id,
        building_id=building_id,
        label=body.label,
        amount_cents=body.amount_cents,
        period_from=body.period_from,
        period_to=body.period_to,
        replaces_cost_entry_id=body.replaces_cost_id,
        new_cost=body.new_cost,
    )
    assignment = AllocationKeyAssignment(
        id=new_id(),
        account_id=account_id,
        cost_entry_id=cost.id,
        key=choice.key,
        direct_unit_id=choice.direct_unit_id,
        direct_tenancy_id=choice.direct_tenancy_id,
    )
    classification = ConfirmedCostClassification(
        id=new_id(),
        account_id=account_id,
        cost_entry_id=cost.id,
        allocation_key_assignment_id=assignment.id,
        catalogue_id=result.rule_id,
        rule_source=result.resolved_rule.source,
        rule_rechtsstand=result.resolved_rule.rechtsstand,
        source_amount_cents=body.amount_cents,
        allocable_cents=result.allocable_cents,
        non_allocable_cents=result.non_allocable_cents,
        labour_cents=result.labour_cents,
        key=result.key,
        key_source=result.key_source,
        findings=list(result.findings),
        special_rule_evidence=body.special_rule_evidence,
        production_blocked=result.production_blocked,
    )
    session.add_all([cost, assignment, classification])
    session.flush()
    session.refresh(cost)
    return _cost_out(cost)


@router.post("/costs/{cost_id}/void")
def void_cost(
    account_id: str, cost_id: str, body: CostVoid, session: PathAccountSession
) -> CostVoidOut:
    """Void an entered cost without erasing its evidence or history."""
    cost = session.get(CostEntry, cost_id)
    if cost is None:
        raise HTTPException(status_code=404, detail="Cost entry not found")
    if cost.voided_at is not None:
        raise HTTPException(status_code=422, detail="Cost entry is already voided")
    cost.voided_at = datetime.now(UTC)
    cost.void_reason = body.reason
    session.flush()
    return CostVoidOut(
        id=cost.id,
        voided_at=cost.voided_at,
        successor_workflow_target=(
            f"/a/{account_id}/buildings/{cost.building_id}/costs?replacesCostId={cost.id}"
        ),
    )


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
    assignment = AllocationKeyAssignment(
        id=new_id(),
        account_id=account_id,
        cost_entry_id=cost.id,
        key=body.key,
        direct_unit_id=body.direct_unit_id,
        direct_tenancy_id=body.direct_tenancy_id,
    )
    session.add(assignment)
    previous = max(cost.classifications, key=lambda row: (row.confirmed_at, row.id), default=None)
    if previous is not None:
        session.add(
            ConfirmedCostClassification(
                id=new_id(),
                account_id=account_id,
                cost_entry_id=cost.id,
                allocation_key_assignment_id=assignment.id,
                catalogue_id=previous.catalogue_id,
                rule_source=previous.rule_source,
                rule_rechtsstand=previous.rule_rechtsstand,
                source_amount_cents=previous.source_amount_cents,
                allocable_cents=previous.allocable_cents,
                non_allocable_cents=previous.non_allocable_cents,
                labour_cents=previous.labour_cents,
                key=body.key,
                key_source="re-keyed",
                findings=previous.findings,
                special_rule_evidence=previous.special_rule_evidence,
                production_blocked=previous.production_blocked,
            )
        )
    session.flush()
    session.refresh(cost)
    return _cost_out(cost)


def _active_agreements(rows: list[OperatingCostAgreement]) -> list[OperatingCostAgreement]:
    """Keep revisions immutable: a row named by a later revision is historic."""
    revised_ids = {row.revises_id for row in rows if row.revises_id is not None}
    return [row for row in rows if row.id not in revised_ids]


def _periods_overlap(left: OperatingCostAgreement, right: OperatingCostAgreement) -> bool:
    left_end = left.valid_to
    right_end = right.valid_to
    return (right_end is None or left.valid_from < right_end) and (
        left_end is None or right.valid_from < left_end
    )


def _agreement_out(row: OperatingCostAgreement) -> OperatingCostAgreementOut:
    return OperatingCostAgreementOut(
        id=row.id,
        tenancy_id=row.tenancy_id,
        allocation_agreed=row.allocation_agreed,
        mehrbelastung_clause=row.mehrbelastung_clause,
        named_other_costs=row.named_other_costs,
        contractual_keys={key: AllocationKey(value) for key, value in row.contractual_keys.items()},
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        revises_id=row.revises_id,
        created_at=row.created_at,
    )


@router.get("/tenancies/{tenancy_id}/operating-cost-agreements")
def list_operating_cost_agreements(
    account_id: str, tenancy_id: str, session: PathAccountSession
) -> list[OperatingCostAgreementOut]:
    del account_id
    if session.get(Tenancy, tenancy_id) is None:
        raise HTTPException(status_code=404, detail="Tenancy not found")
    rows = session.scalars(
        select(OperatingCostAgreement)
        .where(OperatingCostAgreement.tenancy_id == tenancy_id)
        .order_by(OperatingCostAgreement.created_at, OperatingCostAgreement.id)
    ).all()
    return [_agreement_out(row) for row in rows]


@router.post("/tenancies/{tenancy_id}/operating-cost-agreements", status_code=201)
def create_operating_cost_agreement(
    account_id: str,
    tenancy_id: str,
    body: OperatingCostAgreementIn,
    session: PathAccountSession,
) -> OperatingCostAgreementOut:
    if session.get(Tenancy, tenancy_id) is None:
        raise HTTPException(status_code=404, detail="Tenancy not found")
    rows = session.scalars(
        select(OperatingCostAgreement).where(OperatingCostAgreement.tenancy_id == tenancy_id)
    ).all()
    if body.revises_id is not None and not any(row.id == body.revises_id for row in rows):
        raise HTTPException(
            status_code=422, detail="Revision target is not an agreement of this tenancy"
        )
    candidate = OperatingCostAgreement(
        id=new_id(),
        account_id=account_id,
        tenancy_id=tenancy_id,
        allocation_agreed=body.allocation_agreed,
        mehrbelastung_clause=body.mehrbelastung_clause,
        named_other_costs=body.named_other_costs,
        contractual_keys={key: value.value for key, value in body.contractual_keys.items()},
        valid_from=body.valid_from,
        valid_to=body.valid_to,
        revises_id=body.revises_id,
    )
    active = _active_agreements([*rows, candidate])
    if any(_periods_overlap(candidate, other) for other in active if other.id != candidate.id):
        raise HTTPException(
            status_code=422, detail="Active operating-cost agreement periods overlap"
        )
    session.add(candidate)
    session.flush()
    session.refresh(candidate)
    return _agreement_out(candidate)
