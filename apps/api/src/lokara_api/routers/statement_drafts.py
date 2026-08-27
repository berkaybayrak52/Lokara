"""UI-05A statement register, resumable drafts and readiness projection."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException
from lokara_db import (
    AdvanceReconciliation,
    CostEntry,
    DeliveryAddress,
    PaymentInstruction,
    Statement,
    StatementDraft,
    StatementSettlement,
    StatementStatus,
    new_id,
)
from lokara_domain import Period
from sqlalchemy import select

from ..authorization import require_building, require_owner
from ..deps import PathAccountSession
from ..schemas import (
    StatementDraftCostOut,
    StatementDraftCreate,
    StatementDraftDocumentOut,
    StatementDraftOut,
    StatementDraftReadinessOut,
    StatementDraftUnitOut,
    StatementDraftUpdate,
    StatementPeriodSuggestionOut,
    StatementReadinessFindingOut,
    StatementRecordOut,
)
from ..statement_service import StatementAudience, compute_statement, project_statement

router = APIRouter(prefix="/a/{account_id}")


def _draft(session: PathAccountSession, draft_id: str) -> StatementDraft:
    row = session.get(StatementDraft, draft_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Abrechnungsentwurf nicht gefunden.")
    require_building(session, row.building_id)
    return row


def _draft_out(session: PathAccountSession, row: StatementDraft) -> StatementDraftOut:
    building = require_building(session, row.building_id)
    return StatementDraftOut(
        id=row.id,
        building_id=row.building_id,
        building_name=building.name,
        title=row.title,
        period_start=row.period_start,
        period_end=row.period_end,
        status=row.status,  # type: ignore[arg-type]
        current_step=row.current_step,
        version=row.version,
        selected_unit_ids=list(row.selected_unit_ids),
        overrides=dict(row.overrides),
        final_statement_id=row.final_statement_id,
        correction_of_statement_id=row.correction_of_statement_id,
        correction_reason=row.correction_reason,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _period_label(start: date, end: date) -> str:
    return f"{start.strftime('%d.%m.%Y')} - {end.strftime('%d.%m.%Y')}"


def _overlaps(start: date, end: date | None, period_start: date, period_end: date) -> bool:
    return start <= period_end and (end is None or end > period_start)


def _latest_advance_cents(tenancy: object, period_end: date) -> int | None:
    periods = [
        row
        for row in getattr(tenancy, "advance_payment_periods", ())
        if row.valid_from <= period_end
    ]
    return max(periods, key=lambda row: row.valid_from).amount_cents if periods else None


@router.get("/statement-records")
def statement_records(account_id: str, session: PathAccountSession) -> list[StatementRecordOut]:
    del account_id
    require_owner(session)
    rows: list[StatementRecordOut] = []
    for draft in session.scalars(
        select(StatementDraft)
        .where(StatementDraft.status.not_in(("FINALIZED", "CANCELLED")))
        .order_by(StatementDraft.updated_at.desc())
    ).all():
        building = require_building(session, draft.building_id)
        rows.append(
            StatementRecordOut(
                id=draft.id,
                kind="DRAFT",
                building_id=draft.building_id,
                building_name=building.name,
                title=draft.title,
                unit_count=len(building.units),
                period_start=draft.period_start,
                period_end=draft.period_end,
                status=draft.status,
                result_summary="Noch kein Ergebnis",
                created_at=draft.created_at,
                updated_at=draft.updated_at,
            )
        )
    for statement in session.scalars(
        select(Statement)
        .where(Statement.status.in_((StatementStatus.FINALIZED, StatementStatus.SUPERSEDED)))
        .order_by(Statement.finalized_at.desc(), Statement.created_at.desc())
    ).all():
        building = require_building(session, statement.building_id)
        settlements = session.scalars(
            select(StatementSettlement).where(StatementSettlement.statement_id == statement.id)
        ).all()
        receivable_count = sum(row.kind == "RECEIVABLE" for row in settlements)
        credit_count = sum(row.kind == "CREDIT_REFUND" for row in settlements)
        parts = []
        if receivable_count:
            parts.append(f"{receivable_count} Nachzahlung{'en' if receivable_count != 1 else ''}")
        if credit_count:
            parts.append(f"{credit_count} Guthaben")
        rows.append(
            StatementRecordOut(
                id=statement.id,
                kind="FINAL",
                building_id=statement.building_id,
                building_name=building.name,
                title=(
                    f"Betriebs- und Heizkostenabrechnung "
                    f"{statement.period_end.year} - {building.name}"
                ),
                unit_count=len(building.units),
                period_start=statement.period_start,
                period_end=statement.period_end,
                status=(
                    "KORRIGIERT" if statement.status is StatementStatus.SUPERSEDED else "FINALIZED"
                ),
                result_summary=" · ".join(parts) or "Ausgeglichen",
                created_at=statement.created_at,
                updated_at=statement.finalized_at or statement.created_at,
            )
        )
    return sorted(rows, key=lambda row: row.updated_at, reverse=True)


@router.get("/statement-period-suggestions")
def statement_period_suggestions(
    account_id: str,
    building_id: str,
    session: PathAccountSession,
) -> list[StatementPeriodSuggestionOut]:
    del account_id
    require_owner(session)
    require_building(session, building_id)
    costs = session.scalars(
        select(CostEntry)
        .where(CostEntry.building_id == building_id, CostEntry.voided_at.is_(None))
        .order_by(CostEntry.period_to.desc())
    ).all()
    if not costs:
        return []
    period_end = max(cost.period_to for cost in costs) - timedelta(days=1)
    period_start = min(cost.period_from for cost in costs if cost.period_from <= period_end)
    if (period_end - period_start).days > 366:
        period_start = date(period_end.year, 1, 1)
    already_finalized = session.scalar(
        select(Statement.id).where(
            Statement.building_id == building_id,
            Statement.period_start == period_start,
            Statement.period_end == period_end,
            Statement.status == StatementStatus.FINALIZED,
        )
    )
    if already_finalized is not None:
        return []
    return [
        StatementPeriodSuggestionOut(
            period_start=period_start,
            period_end=period_end,
            label=f"{period_start.strftime('%d.%m.%Y')} - {period_end.strftime('%d.%m.%Y')}",
            reason="Aus den vorhandenen Kosten- und Nutzungsdaten vorgeschlagen",
        )
    ]


@router.post("/statement-drafts", status_code=201)
def create_statement_draft(
    account_id: str,
    body: StatementDraftCreate,
    session: PathAccountSession,
) -> StatementDraftOut:
    require_owner(session)
    building = require_building(session, body.building_id)
    correction = None
    if body.correction_of_statement_id is not None:
        correction = session.get(Statement, body.correction_of_statement_id)
        if correction is None or correction.building_id != building.id:
            raise HTTPException(status_code=404, detail="Vorgängerabrechnung nicht gefunden.")
        latest = session.scalar(
            select(Statement)
            .where(
                Statement.building_id == building.id,
                Statement.period_start == correction.period_start,
                Statement.period_end == correction.period_end,
                Statement.status == StatementStatus.FINALIZED,
            )
            .order_by(Statement.version.desc())
        )
        if latest is None or latest.id != correction.id:
            raise HTTPException(
                status_code=422,
                detail="Nur die jüngste finalisierte Fassung kann korrigiert werden.",
            )
        if not (body.correction_reason or "").strip():
            raise HTTPException(status_code=422, detail="Für eine Korrektur fehlt der Grund.")
    title = (body.title or "").strip() or (
        f"Betriebs- und Heizkostenabrechnung {body.period_end.year} - {building.name}"
    )
    row = StatementDraft(
        id=new_id(),
        account_id=account_id,
        building_id=building.id,
        title=title,
        period_start=body.period_start,
        period_end=body.period_end,
        status="DRAFT",
        current_step=1,
        version=1,
        selected_unit_ids=[unit.id for unit in building.units],
        overrides={},
        final_statement_id=None,
        correction_of_statement_id=(correction.id if correction is not None else None),
        correction_reason=(body.correction_reason or "").strip() or None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(row)
    session.flush()
    return _draft_out(session, row)


@router.get("/statement-drafts/{draft_id}")
def get_statement_draft(
    account_id: str, draft_id: str, session: PathAccountSession
) -> StatementDraftOut:
    del account_id
    require_owner(session)
    return _draft_out(session, _draft(session, draft_id))


@router.patch("/statement-drafts/{draft_id}")
def update_statement_draft(
    account_id: str,
    draft_id: str,
    body: StatementDraftUpdate,
    session: PathAccountSession,
) -> StatementDraftOut:
    del account_id
    require_owner(session)
    row = _draft(session, draft_id)
    if row.status in {"FINALIZED", "CANCELLED"}:
        raise HTTPException(
            status_code=409, detail="Dieser Entwurf kann nicht mehr geändert werden."
        )
    if row.version != body.version:
        raise HTTPException(
            status_code=409,
            detail=(
                "Der Entwurf wurde an anderer Stelle geändert. "
                "Bitte laden Sie die aktuelle Fassung."
            ),
        )
    if body.title is not None:
        if not body.title.strip():
            raise HTTPException(status_code=422, detail="Der Titel darf nicht leer sein.")
        row.title = body.title.strip()
    if body.current_step is not None:
        row.current_step = body.current_step
    if body.selected_unit_ids is not None:
        building = require_building(session, row.building_id)
        known = {unit.id for unit in building.units}
        selected = list(dict.fromkeys(body.selected_unit_ids))
        if not selected or not set(selected).issubset(known):
            raise HTTPException(status_code=422, detail="Die Einheitenauswahl ist ungültig.")
        row.selected_unit_ids = selected
    if body.overrides is not None:
        row.overrides = dict(body.overrides)
    if body.correction_reason is not None:
        row.correction_reason = body.correction_reason.strip() or None
    row.status = "DRAFT"
    row.version += 1
    row.updated_at = datetime.now(UTC)
    session.flush()
    return _draft_out(session, row)


@router.post("/statement-drafts/{draft_id}/cancel")
def cancel_statement_draft(
    account_id: str, draft_id: str, session: PathAccountSession
) -> StatementDraftOut:
    del account_id
    require_owner(session)
    row = _draft(session, draft_id)
    if row.status == "FINALIZED":
        raise HTTPException(
            status_code=409, detail="Eine finalisierte Abrechnung bleibt unverändert."
        )
    row.status = "CANCELLED"
    row.version += 1
    row.updated_at = datetime.now(UTC)
    session.flush()
    return _draft_out(session, row)


@router.post("/statement-drafts/{draft_id}/readiness")
def statement_draft_readiness(
    account_id: str, draft_id: str, session: PathAccountSession
) -> StatementDraftReadinessOut:
    require_owner(session)
    row = _draft(session, draft_id)
    building = require_building(session, row.building_id)
    findings: list[StatementReadinessFindingOut] = []
    units: list[StatementDraftUnitOut] = []
    costs: list[StatementDraftCostOut] = []
    documents = [
        StatementDraftDocumentOut(
            key="owner-overview",
            tenancy_id=None,
            recipient="Vermieter",
            document_type="Vermieterübersicht",
            readiness="READY",
        )
    ]
    bundle = None
    owner_projection = None
    try:
        bundle = compute_statement(
            session,
            building_id=building.id,
            window=Period(row.period_start, row.period_end + timedelta(days=1)),
        )
        owner_projection = project_statement(bundle, StatementAudience.OWNER)
    except (LookupError, ValueError):
        findings.append(
            StatementReadinessFindingOut(
                code="statement_inputs_invalid",
                area="Grundlagen",
                severity="BLOCKER",
                message="Die Abrechnungsdaten sind noch nicht vollständig oder widerspruchsfrei.",
                correction_route=f"/a/{account_id}/buildings/{building.id}",
                allowed_actions=["Daten prüfen"],
            )
        )
    if bundle is not None:
        if bundle.page02_production_blocked:
            findings.append(
                StatementReadinessFindingOut(
                    code="cost_rules_production_blocked",
                    area="Kosten & Verteilung",
                    severity="WARNING",
                    message=(
                        "Mindestens eine Kostenklassifizierung ist rechtlich noch nicht "
                        "produktionsfreigegeben. Ein klar gekennzeichneter technischer "
                        "Demoausdruck ist möglich."
                    ),
                    correction_route=f"/a/{account_id}/kosten",
                    allowed_actions=["Kosten prüfen"],
                    provenance="BetrKV-Katalog / Rechtsstand",
                )
            )
        if bundle.heating_missing_reason:
            findings.append(
                StatementReadinessFindingOut(
                    code="heating_input_missing",
                    area="Kosten & Verteilung",
                    severity="BLOCKER",
                    message=bundle.heating_missing_reason,
                    correction_route=f"/a/{account_id}/zaehler",
                    allowed_actions=["Zählerdaten prüfen"],
                )
            )
        findings.extend(
            StatementReadinessFindingOut(
                code=f"nk_finding_{index + 1}",
                area="Kosten & Verteilung",
                severity="WARNING",
                message=message,
                correction_route=f"/a/{account_id}/kosten",
                allowed_actions=["Kosten prüfen"],
            )
            for index, message in enumerate(bundle.nk_findings)
        )
        for cost in bundle.nk_costs:
            costs.append(
                StatementDraftCostOut(
                    cost_id=cost.cost_id,
                    label=cost.label,
                    period_label=_period_label(row.period_start, row.period_end),
                    amount_cents=int(cost.amount),
                    allocable_cents=int(cost.amount),
                    allocation_key=cost.key.value,
                    status="READY",
                )
            )
    instruction = session.scalar(
        select(PaymentInstruction)
        .where(PaymentInstruction.valid_from <= row.period_end)
        .order_by(PaymentInstruction.version.desc())
    )
    if instruction is None:
        findings.append(
            StatementReadinessFindingOut(
                code="payment_instruction_missing",
                area="Absender & Konto",
                severity="BLOCKER",
                message="Zahlungs- und Guthabenhinweise fehlen.",
                correction_route=f"/a/{account_id}/abrechnung/{row.id}?step=2",
                allowed_actions=["Hinweise ergänzen"],
            )
        )
    selected = set(row.selected_unit_ids)
    for unit in sorted(building.units, key=lambda item: item.label):
        tenancies = [
            tenancy
            for tenancy in sorted(unit.tenancies, key=lambda item: item.valid_from)
            if _overlaps(tenancy.valid_from, tenancy.valid_to, row.period_start, row.period_end)
        ]
        if not tenancies:
            self_use = next(
                (
                    use
                    for use in unit.self_use_periods
                    if _overlaps(use.valid_from, use.valid_to, row.period_start, row.period_end)
                ),
                None,
            )
            usage = (
                "Eigennutzung"
                if self_use is not None and self_use.kind.value == "OWNER_OCCUPIED"
                else "Mietfreie Nutzung"
                if self_use is not None
                else "Leerstand"
            )
            units.append(
                StatementDraftUnitOut(
                    unit_id=unit.id,
                    tenancy_id=None,
                    label=unit.label,
                    usage=usage,
                    party="Eigentümer",
                    period_label=_period_label(row.period_start, row.period_end),
                    person_count="-",
                    area_sqm=f"{Decimal(unit.area_sqm_x100) / Decimal(100):.2f}",
                    contractual_advance_cents=None,
                    actual_advances_cents=None,
                    saldo_cents=None,
                    included=unit.id in selected,
                    status="READY",
                )
            )
            continue
        for tenancy in tenancies:
            party = ", ".join(item.renter.legal_name for item in tenancy.parties) or "Mieter"
            reconciliation = session.scalar(
                select(AdvanceReconciliation)
                .where(
                    AdvanceReconciliation.tenancy_id == tenancy.id,
                    AdvanceReconciliation.period_start == row.period_start,
                    AdvanceReconciliation.period_end == row.period_end,
                )
                .order_by(AdvanceReconciliation.version.desc())
            )
            address = session.scalar(
                select(DeliveryAddress)
                .where(
                    DeliveryAddress.tenancy_id == tenancy.id,
                    DeliveryAddress.valid_from <= row.period_end,
                )
                .order_by(DeliveryAddress.version.desc())
            )
            status: Literal["READY", "WARNING", "BLOCKER"] = "READY"
            if reconciliation is None:
                status = "BLOCKER"
                findings.append(
                    StatementReadinessFindingOut(
                        code="advance_reconciliation_missing",
                        area="Prüfung & Vorauszahlungen",
                        severity="BLOCKER",
                        entity_type="TENANCY",
                        entity_id=tenancy.id,
                        message=f"Vorauszahlungen für {party} sind noch nicht bestätigt.",
                        correction_route=f"/a/{account_id}/abrechnung/{row.id}?step=5",
                        allowed_actions=["Vorauszahlungen bestätigen"],
                    )
                )
            if address is None:
                status = "BLOCKER"
                findings.append(
                    StatementReadinessFindingOut(
                        code="delivery_address_missing",
                        area="Absender & Konto",
                        severity="BLOCKER",
                        entity_type="TENANCY",
                        entity_id=tenancy.id,
                        message=f"Für {party} fehlt eine Zustelladresse.",
                        correction_route=f"/a/{account_id}/abrechnung/{row.id}?step=2",
                        allowed_actions=["Adresse ergänzen"],
                    )
                )
            saldo = None
            if bundle is not None and reconciliation is not None:
                tenant_projection = project_statement(
                    bundle,
                    StatementAudience.TENANT,
                    tenancy_id=tenancy.id,
                    allow_production_blocked=True,
                )
                subtotal = sum(int(line.amount) for line in tenant_projection.nk_lines) + sum(
                    int(line.total) for line in tenant_projection.heating_lines
                )
                saldo = subtotal - reconciliation.total_cents
            counts = [
                count.count
                for count in tenancy.person_counts
                if _overlaps(count.valid_from, count.valid_to, row.period_start, row.period_end)
            ]
            period_from = max(tenancy.valid_from, row.period_start)
            period_to = min(
                tenancy.valid_to or (row.period_end + timedelta(days=1)),
                row.period_end + timedelta(days=1),
            ) - timedelta(days=1)
            units.append(
                StatementDraftUnitOut(
                    unit_id=unit.id,
                    tenancy_id=tenancy.id,
                    label=unit.label,
                    usage="Vermietet",
                    party=party,
                    period_label=_period_label(period_from, period_to),
                    person_count=(
                        str(sum(counts) / len(counts)).replace(".", ",")
                        if counts
                        else "Nicht erfasst"
                    ),
                    area_sqm=f"{Decimal(unit.area_sqm_x100) / Decimal(100):.2f}",
                    contractual_advance_cents=_latest_advance_cents(tenancy, row.period_end),
                    actual_advances_cents=(reconciliation.total_cents if reconciliation else None),
                    saldo_cents=saldo,
                    included=unit.id in selected,
                    status=status,
                )
            )
            documents.extend(
                (
                    StatementDraftDocumentOut(
                        key=f"cover-{tenancy.id}",
                        tenancy_id=tenancy.id,
                        recipient=party,
                        document_type="Anschreiben",
                        readiness=("READY" if status == "READY" else "BLOCKED"),
                    ),
                    StatementDraftDocumentOut(
                        key=f"statement-{tenancy.id}",
                        tenancy_id=tenancy.id,
                        recipient=party,
                        document_type="Mieter-Einzelabrechnung",
                        readiness=("READY" if status == "READY" else "BLOCKED"),
                    ),
                )
            )
    if row.correction_of_statement_id is not None and not (row.correction_reason or "").strip():
        findings.append(
            StatementReadinessFindingOut(
                code="correction_reason_missing",
                area="Grundlagen",
                severity="BLOCKER",
                message="Für die Korrektur fehlt der Grund.",
                correction_route=f"/a/{account_id}/abrechnung/{row.id}?step=1",
                allowed_actions=["Korrekturgrund ergänzen"],
            )
        )
    blockers = [finding for finding in findings if finding.severity == "BLOCKER"]
    overall = "READY" if not blockers else "REVIEW_REQUIRED"
    if row.status == "FINALIZED":
        overall = "FINALIZED"
    elif row.status != overall:
        row.status = overall
        row.version += 1
        row.updated_at = datetime.now(UTC)
        session.flush()
    nk_total = int(bundle.nk_result.total) if bundle is not None else None
    heating_total = None
    owner_total = None
    heating_path = None
    if bundle is not None:
        if bundle.page01b_result is not None and bundle.page01b_result.values is not None:
            heating_path = bundle.page01b_result.values.path
            heating_total = int(bundle.page01b_result.values.source_total)
        elif bundle.heating_result is not None:
            heating_path = "SELF_BILLING"
            heating_total = int(bundle.heating_result.total)
        if owner_projection is not None:
            owner_total = sum(
                int(line.amount) for line in owner_projection.nk_lines if line.tenancy_id is None
            )
            if owner_projection.owner_residual is not None:
                owner_total += int(owner_projection.owner_residual.total)
    return StatementDraftReadinessOut(
        draft=_draft_out(session, row),
        overall_status=overall,  # type: ignore[arg-type]
        findings=findings,
        units=units,
        costs=costs,
        documents=documents,
        nk_total_cents=nk_total,
        heating_total_cents=heating_total,
        allocable_total_cents=(nk_total + (heating_total or 0) if nk_total is not None else None),
        owner_total_cents=owner_total,
        heating_path=heating_path,
    )
