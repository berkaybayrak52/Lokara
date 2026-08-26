"""M9 account-scoped guards, reminders, delivery schedules and checklists.

The router exposes immutable evidence and keeps authorization at the HTTP
boundary.  Guard calculations and delivery orchestration remain in their
respective engine/job layers; this module does not restate either rule set.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException
from lokara_adapters import EmailGateway, StubEmailGateway
from lokara_db import (
    Building,
    ChecklistInstance,
    ChecklistItemEvent,
    DeliveryScheduleVersion,
    EmailAttempt,
    EmailDeliveryStatusEvent,
    GuardEvaluation,
    GuardReminder,
    GuardResolutionEvent,
    Landlord,
    Meter,
    RecipientSuppressionEvent,
    Renter,
    RenterDeliveryArtifact,
    Role,
    Statement,
    StatementArchive,
    Tenancy,
    TenancyParty,
    Unit,
    new_id,
)
from lokara_guard_engine import (
    GuardSourceIdentity,
    RuleConflict,
    RuleEvidence,
    VacancyInput,
    VacancyRuleBundle,
    evaluate_vacancy,
)
from lokara_rules_store import (
    Page05Evidence,
    RuleNotFoundError,
    resolve_page05_g1_rules,
    resolve_page05_m9_rules,
)
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..authorization import PortalScope
from ..deps import PathAccountSession
from ..jobs import (
    GuardEvaluationOccurrence,
    RenterDeliveryRequest,
    ScheduledDeliveryKind,
    dispatch_renter_artifact,
    run_daily_guard_evaluations,
)

router = APIRouter(prefix="/a/{account_id}", tags=["guards-delivery"])

_WRITE_RESPONSES: dict[int | str, dict[str, Any]] = {
    403: {"description": "Die Rolle darf diese Aktion nicht ausführen."},
    404: {"description": "Die Ressource ist nicht sichtbar oder nicht vorhanden."},
    422: {"description": "Die Anfrage oder ihr Objektbezug ist ungültig."},
}
_SENDER_ADDRESS = "zustellung@lokara.de"
_email_gateway = StubEmailGateway(sender_address=_SENDER_ADDRESS)


def email_gateway_for_delivery() -> EmailGateway:
    """Inject the deterministic M9 adapter; a real provider is not selected."""

    return _email_gateway


def delivery_clock() -> datetime:
    """Inject the application clock so delivery evidence is testable."""

    return datetime.now(UTC)


class _ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


M9Action = Literal[
    "guards_read",
    "guard_run",
    "schedule_read",
    "schedule_write",
    "reminder_read",
    "checklist_read",
    "checklist_write",
    "delivery_read",
    "send",
    "confirm",
]


def authorize_m9_action(role: Role, action: M9Action | str) -> None:
    """Apply the M9 role matrix independently of navigation visibility."""

    if role is Role.OWNER:
        return
    if role is Role.EMPLOYEE and action in {
        "guards_read",
        "checklist_read",
        "checklist_write",
    }:
        return
    raise HTTPException(status_code=403, detail="Diese Rolle darf die Aktion nicht ausführen.")


def filter_m9_rows_for_scope(rows: Iterable[Any], scope: Any) -> list[Any]:
    """Filter account-level lists to an employee's assigned buildings."""

    if scope.role is Role.TAX_ADVISOR:
        raise HTTPException(status_code=403, detail="Diese Rolle darf M9 nicht verwenden.")
    if scope.role is not Role.EMPLOYEE:
        return list(rows)
    return [row for row in rows if row.building_id in scope.building_ids]


def require_m9_row_for_scope(row: Any, scope: Any) -> Any:
    """Hide an id-only resource outside an employee's assigned buildings."""

    if scope.role is Role.TAX_ADVISOR:
        raise HTTPException(status_code=403, detail="Diese Rolle darf M9 nicht verwenden.")
    if scope.role is Role.EMPLOYEE and row.building_id not in scope.building_ids:
        raise HTTPException(status_code=404, detail="Ressource nicht gefunden")
    return row


def _scope(session: Session) -> PortalScope:
    value = session.info.get("portal_scope")
    if not isinstance(value, PortalScope):
        raise RuntimeError("portal authorization scope is missing")
    return value


def _authorize(session: Session, action: M9Action) -> PortalScope:
    scope = _scope(session)
    authorize_m9_action(scope.role, action)
    return scope


def validate_delivery_relationships(
    context: Any,
    *,
    building: Any,
    unit: Any,
    tenancy: Any,
    renter: Any,
    tenancy_party: Any,
    artifact: Any,
) -> None:
    """Reject every forged link in one renter-delivery context."""

    expected = (
        building.id == context.building_id and artifact.building_id == context.building_id,
        unit.id == artifact.unit_id and unit.building_id == building.id,
        tenancy.id == artifact.tenancy_id and tenancy.unit_id == artifact.unit_id,
        renter.id == context.renter_id and artifact.renter_id == context.renter_id,
        tenancy_party.tenancy_id == artifact.tenancy_id
        and tenancy_party.renter_id == context.renter_id,
        artifact.id == context.artifact_id,
    )
    if not all(expected):
        raise HTTPException(status_code=422, detail="Ungültiger Zustellkontext.")


def validate_w1_delivery_confirmation(*, artifact: Any, evaluation: Any) -> None:
    """Require the complete annual-statement context before resolving W1."""

    if (
        artifact.artifact_kind != "ANNUAL_STATEMENT"
        or evaluation.guard_code != "W1"
        or any(
            getattr(artifact, field) != getattr(evaluation, field)
            for field in (
                "building_id",
                "unit_id",
                "tenancy_id",
                "renter_id",
                "occurrence_key",
            )
        )
    ):
        raise HTTPException(
            status_code=422,
            detail="Zustellung und W1-Auswertung haben keinen identischen Kontext.",
        )


@dataclass(frozen=True, slots=True)
class W1DeliveryConfirmationDecision:
    record_delivery_evidence: bool
    late_delivery: bool
    resolve_w1: bool
    append_resolution_event: bool


def evaluate_w1_delivery_confirmation(
    *,
    artifact: Any,
    evaluation: Any,
    delivered_on: date,
    today: date,
) -> W1DeliveryConfirmationDecision:
    """Separate legal delivery evidence from on-time W1 resolution."""

    validate_w1_delivery_confirmation(artifact=artifact, evaluation=evaluation)
    if delivered_on > today:
        raise HTTPException(
            status_code=422,
            detail="Ein Zustelldatum darf nicht in der Zukunft liegen.",
        )
    raw_boundary = evaluation.result_snapshot.get("boundary_date")
    if isinstance(raw_boundary, date):
        boundary = raw_boundary
    elif isinstance(raw_boundary, str):
        try:
            boundary = date.fromisoformat(raw_boundary)
        except ValueError as error:
            raise HTTPException(
                status_code=422, detail="Die eingefrorene W1-Grenze ist ungültig."
            ) from error
    else:
        raise HTTPException(status_code=422, detail="Die eingefrorene W1-Grenze fehlt.")
    late = delivered_on > boundary
    return W1DeliveryConfirmationDecision(
        record_delivery_evidence=True,
        late_delivery=late,
        resolve_w1=not late,
        append_resolution_event=not late,
    )


class GuardResponse(_ApiModel):
    id: str
    guard_code: str
    subject_type: str
    subject_id: str
    building_id: str
    unit_id: str | None
    tenancy_id: str | None
    renter_id: str | None
    occurrence_key: str
    input_snapshot: dict[str, object]
    result_snapshot: dict[str, object]
    rule_snapshot: dict[str, object]
    evaluated_at: datetime
    resolution_events: list[dict[str, object]] = Field(default_factory=list)


class GuardListResponse(_ApiModel):
    guards: list[GuardResponse]
    source_ids: list[str]


def guard_discovery_source_token(account_id: str) -> str:
    """Return the server-owned account discovery token used for a first guard run."""

    return f"account-scope:{account_id}"


class GuardRunCreate(_ApiModel):
    today: date
    now: datetime
    source_ids: list[str] = Field(min_length=1)

    @field_validator("now")
    @classmethod
    def require_aware_now(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("now muss eine Zeitzone enthalten")
        return value

    @field_validator("source_ids")
    @classmethod
    def source_ids_are_nonblank_and_unique(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("sourceIds darf keine leeren Werte enthalten")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("sourceIds darf keine Duplikate enthalten")
        return cleaned


class GuardRunResponse(_ApiModel):
    account_id: str
    evaluated_occurrences: int
    existing_occurrences: int
    created_reminders: int
    push_available: bool
    production_blockers: tuple[str, ...]


class DeliveryScheduleCreate(_ApiModel):
    building_id: str | None = None
    delivery_kind: Literal["ANNUAL_STATEMENT", "UVI"]
    valid_from: date
    enabled: bool = False
    source_id: str = Field(min_length=1)

    @field_validator("building_id", "source_id")
    @classmethod
    def schedule_ids_are_nonblank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Objekt- und Quellen-ID dürfen nicht leer sein")
        return cleaned


class DeliveryScheduleResponse(_ApiModel):
    id: str
    building_id: str
    delivery_kind: str
    version: int
    enabled: bool
    supersedes_schedule_version_id: str | None
    valid_from: date
    schedule_snapshot: dict[str, object]
    created_at: datetime | None = None


class DeliveryScheduleListResponse(_ApiModel):
    schedules: list[DeliveryScheduleResponse]


class ReminderResponse(_ApiModel):
    id: str
    guard_evaluation_id: str
    occurrence_key: str
    building_id: str
    channel: str
    due_at: datetime
    idempotency_key: str
    payload_snapshot: dict[str, object]
    created_at: datetime


class ReminderListResponse(_ApiModel):
    reminders: list[ReminderResponse]


class ChecklistEventResponse(_ApiModel):
    id: str
    item_id: str
    event_type: str
    occurred_at: datetime
    actor_membership_id: str
    idempotency_key: str
    event_snapshot: dict[str, object]


class ChecklistResponse(_ApiModel):
    id: str
    building_id: str
    template_id: str
    template_version: int
    template_snapshot: dict[str, object]
    occurrence_key: str
    events: list[ChecklistEventResponse]


class ChecklistListResponse(_ApiModel):
    checklists: list[ChecklistResponse]
    production_blocked: bool
    blocker: str | None


class ChecklistItemEventCreate(_ApiModel):
    event_type: Literal["COMPLETED", "REOPENED"]
    occurred_at: datetime
    idempotency_key: str = Field(min_length=1, max_length=300)
    event_snapshot: dict[str, object] = Field(default_factory=dict)

    @field_validator("occurred_at")
    @classmethod
    def require_aware_occurrence(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurredAt muss eine Zeitzone enthalten")
        return value


class DeliveryCreate(_ApiModel):
    building_id: str = Field(min_length=1)
    renter_id: str = Field(min_length=1)
    artifact_id: str = Field(min_length=1)
    delivery_kind: Literal["ANNUAL_STATEMENT", "UVI"]
    occurrence_key: str = Field(min_length=1)


class DeliveryResponse(_ApiModel):
    id: str
    renter_id: str
    artifact_id: str
    building_id: str | None = None
    occurrence_key: str | None = None
    delivery_kind: str | None = None
    recipient: str | None = None
    blocked_reason: str | None
    blocked_detail: str | None = None
    provider_status: str | None
    provider_delivered_at: datetime | None = None
    attempted_at: datetime | None = None
    status_occurred_at: datetime | None = None
    suppression_events: list[dict[str, object]] = Field(default_factory=list)
    legally_confirmed: bool
    delivered_on: date | None
    evidence_reference: str | None


class DeliveryListResponse(_ApiModel):
    deliveries: list[DeliveryResponse]


class DeliveryConfirmationCreate(_ApiModel):
    delivered_on: date
    evidence_reference: str = Field(min_length=1, max_length=500)

    @field_validator("evidence_reference")
    @classmethod
    def evidence_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("evidenceReference darf nicht leer sein")
        return cleaned


def _guard_response(session: Session, account_id: str, row: GuardEvaluation) -> GuardResponse:
    events = session.scalars(
        select(GuardResolutionEvent)
        .where(
            GuardResolutionEvent.account_id == account_id,
            GuardResolutionEvent.guard_evaluation_id == row.id,
        )
        .order_by(GuardResolutionEvent.occurred_at, GuardResolutionEvent.id)
    ).all()
    return GuardResponse(
        id=row.id,
        guard_code=row.guard_code,
        subject_type=row.subject_type,
        subject_id=row.subject_id,
        building_id=row.building_id,
        unit_id=row.unit_id,
        tenancy_id=row.tenancy_id,
        renter_id=row.renter_id,
        occurrence_key=row.occurrence_key,
        input_snapshot=row.input_snapshot,
        result_snapshot=row.result_snapshot,
        rule_snapshot=row.rule_snapshot,
        evaluated_at=row.evaluated_at,
        resolution_events=[
            {
                "id": event.id,
                "event_type": event.event_type,
                "occurred_at": event.occurred_at.isoformat(),
                "evidence_reference": event.evidence_reference,
                "event_snapshot": event.event_snapshot,
            }
            for event in events
        ],
    )


@router.get("/guards")
def list_guards(account_id: str, session: PathAccountSession) -> GuardListResponse:
    scope = _authorize(session, "guards_read")
    rows = session.scalars(
        select(GuardEvaluation)
        .where(GuardEvaluation.account_id == account_id)
        .order_by(GuardEvaluation.evaluated_at.desc(), GuardEvaluation.id)
    ).all()
    return GuardListResponse(
        guards=[
            _guard_response(session, account_id, row)
            for row in filter_m9_rows_for_scope(rows, scope)
        ],
        source_ids=[guard_discovery_source_token(account_id)],
    )


@router.post("/guard-runs", responses=_WRITE_RESPONSES)
def create_guard_run(
    account_id: str, body: GuardRunCreate, session: PathAccountSession
) -> GuardRunResponse:
    _authorize(session, "guard_run")
    occurrences, source_blockers = _resolve_guard_sources(
        session,
        account_id=account_id,
        source_ids=body.source_ids,
        today=body.today,
    )
    result = run_daily_guard_evaluations(
        session,
        account_id=account_id,
        today=body.today,
        now=body.now,
        occurrences=occurrences,
    )
    return GuardRunResponse(
        account_id=result.account_id,
        evaluated_occurrences=result.evaluated_occurrences,
        existing_occurrences=result.existing_occurrences,
        created_reminders=result.created_reminders,
        push_available=result.push_available,
        production_blockers=tuple(sorted(set(result.production_blockers) | set(source_blockers))),
    )


def _blocked_guard_occurrence(
    *,
    guard_code: str,
    source_type: str,
    source_id: str,
    building_id: str,
    today: date,
    blockers: tuple[str, ...],
    unit_id: str | None = None,
    tenancy_id: str | None = None,
    renter_id: str | None = None,
    occurrence_key: str | None = None,
) -> GuardEvaluationOccurrence:
    applicable_evidence: tuple[Page05Evidence, ...]
    if guard_code in {"W1", "W2", "W4"}:
        resolved_g1 = resolve_page05_g1_rules(today)
        if guard_code == "W1":
            applicable_evidence = resolved_g1.value.w1.evidence
        elif guard_code == "W2":
            applicable_evidence = resolved_g1.value.w2.evidence
        else:
            applicable_evidence = resolved_g1.value.w4.evidence
    else:
        resolved_m9 = resolve_page05_m9_rules(today)
        if guard_code == "W3":
            applicable_evidence = resolved_m9.value.payment_arrears.evidence
        elif guard_code == "W5":
            applicable_evidence = resolved_m9.value.comparative_rent.evidence
        elif guard_code == "W6":
            applicable_evidence = resolved_m9.value.graduated_rent.evidence
        elif guard_code == "W7":
            applicable_evidence = resolved_m9.value.index_rent.evidence
        elif guard_code == "W8":
            applicable_evidence = resolved_m9.value.vacancy.evidence
        else:
            raise ValueError(f"Unsupported guard code: {guard_code}")
    evidence = [asdict(item) for item in applicable_evidence]
    rule_source = applicable_evidence[0].source
    rule_rechtsstand = ", ".join(dict.fromkeys(item.rechtsstand for item in applicable_evidence))
    warning_de = f"{guard_code}: Die Auswertung ist gesperrt, weil freigegebene Quelldaten fehlen."
    return GuardEvaluationOccurrence(
        guard_code=guard_code,
        occurrence_key=(
            occurrence_key
            if occurrence_key is not None
            else f"{guard_code.lower()}:{source_id}:{today.isoformat()}"
        ),
        subject_type=source_type,
        subject_id=source_id,
        building_id=building_id,
        unit_id=unit_id,
        tenancy_id=tenancy_id,
        renter_id=renter_id,
        input_snapshot={"source_id": source_id, "today": today.isoformat()},
        result_snapshot={
            "guard_code": guard_code,
            "stage": "source_missing",
            "active": False,
            "resolved": False,
            "warning_de": warning_de,
            "escalation_channels": [],
            "production_blockers": list(blockers),
        },
        rule_snapshot={
            "status": "approved_inputs_missing",
            "source": rule_source,
            "rechtsstand": rule_rechtsstand,
            "evidence": evidence,
        },
        production_blockers=blockers,
    )


def _vacancy_rule_bundle(today: date) -> tuple[VacancyRuleBundle, dict[str, object]]:
    resolved = resolve_page05_m9_rules(today)
    source = resolved.value.vacancy
    evidence = tuple(
        RuleEvidence(
            source=item.source,
            register_row=item.register_row,
            legal_basis=item.legal_basis,
            rechtsstand=item.rechtsstand,
            verification_status=item.verification_status,
        )
        for item in source.evidence
    )
    conflicts = tuple(
        RuleConflict(
            code=item.code,
            description=item.description,
            production_blocking=True,
        )
        for item in source.production_blockers
    )
    bundle = VacancyRuleBundle(
        evidence=evidence,
        unresolved_conflicts=conflicts,
        threshold_days=source.threshold_days,
        rent_period_days=source.rent_period_days,
        warning_de=source.warning_de,
        channels_by_stage=source.channels_by_stage,
        resolution_event=source.resolution_event,
    )
    return bundle, {
        "key": resolved.key,
        "source": resolved.source,
        "rechtsstand": resolved.rechtsstand,
        "bundle": cast(dict[str, object], asdict(bundle)),
    }


def _unit_vacancy_occurrence(
    session: Session,
    *,
    account_id: str,
    unit: Unit,
    today: date,
) -> GuardEvaluationOccurrence:
    tenancies = session.scalars(
        select(Tenancy)
        .where(Tenancy.account_id == account_id, Tenancy.unit_id == unit.id)
        .order_by(Tenancy.valid_from, Tenancy.id)
    ).all()
    active = any(
        tenancy.valid_from <= today and (tenancy.valid_to is None or today < tenancy.valid_to)
        for tenancy in tenancies
    )
    ended = [
        tenancy
        for tenancy in tenancies
        if tenancy.valid_to is not None and tenancy.valid_to <= today
    ]
    if not ended:
        return _blocked_guard_occurrence(
            guard_code="W8",
            source_type="unit",
            source_id=unit.id,
            building_id=unit.building_id,
            today=today,
            blockers=("W8-LAST-TENANCY-SOURCE-MISSING",),
        )
    previous = max(ended, key=lambda tenancy: cast(date, tenancy.valid_to))
    assert previous.valid_to is not None
    input_ = VacancyInput(
        source_identity=GuardSourceIdentity(source_type="unit", source_id=unit.id),
        today=today,
        last_tenancy_ended_on=previous.valid_to,
        active_tenancy=active,
        target_rent_cents=previous.base_rent_cents,
        unit_label=unit.label,
    )
    rules, rule_snapshot = _vacancy_rule_bundle(today)
    result = evaluate_vacancy(input_, rules)
    return GuardEvaluationOccurrence(
        guard_code=result.guard_code,
        occurrence_key=f"w8:{unit.id}:{today.isoformat()}",
        subject_type="unit",
        subject_id=unit.id,
        building_id=unit.building_id,
        input_snapshot=cast(dict[str, object], asdict(input_)),
        result_snapshot=cast(dict[str, object], asdict(result)),
        rule_snapshot=rule_snapshot,
        reminder_channels=tuple(channel.upper() for channel in result.escalation_channels),
        production_blockers=result.production_blockers,
    )


def _resolve_guard_sources(
    session: Session,
    *,
    account_id: str,
    source_ids: list[str],
    today: date,
) -> tuple[tuple[GuardEvaluationOccurrence, ...], tuple[str, ...]]:
    """Resolve client IDs to account rows; never accept client-authored results."""

    discovery_token = guard_discovery_source_token(account_id)
    expanded_source_ids: list[str] = []
    for source_id in source_ids:
        if source_id != discovery_token:
            expanded_source_ids.append(source_id)
            continue
        for model in (Unit, RenterDeliveryArtifact, Statement, Tenancy, Meter):
            expanded_source_ids.extend(
                session.scalars(select(model.id).where(model.account_id == account_id)).all()
            )

    occurrences: list[GuardEvaluationOccurrence] = []
    missing: list[str] = []
    for source_id in dict.fromkeys(expanded_source_ids):
        unit = session.scalar(
            select(Unit).where(Unit.account_id == account_id, Unit.id == source_id)
        )
        if unit is not None:
            try:
                occurrences.append(
                    _unit_vacancy_occurrence(session, account_id=account_id, unit=unit, today=today)
                )
            except RuleNotFoundError:
                occurrences.append(
                    _blocked_guard_occurrence(
                        guard_code="W8",
                        source_type="unit",
                        source_id=unit.id,
                        building_id=unit.building_id,
                        today=today,
                        blockers=("W8-APPROVED-RULE-VERSION-MISSING",),
                    )
                )
            continue
        artifact = session.scalar(
            select(RenterDeliveryArtifact).where(
                RenterDeliveryArtifact.account_id == account_id,
                RenterDeliveryArtifact.id == source_id,
            )
        )
        if artifact is not None:
            guard_code = "W1" if artifact.artifact_kind == "ANNUAL_STATEMENT" else "W4"
            occurrences.append(
                _blocked_guard_occurrence(
                    guard_code=guard_code,
                    source_type="renter_delivery_artifact",
                    source_id=artifact.id,
                    building_id=artifact.building_id,
                    unit_id=artifact.unit_id,
                    tenancy_id=artifact.tenancy_id,
                    renter_id=artifact.renter_id,
                    today=today,
                    occurrence_key=artifact.occurrence_key,
                    blockers=(f"{guard_code}-APPROVED-NORMALIZED-INPUTS-MISSING",),
                )
            )
            continue
        statement = session.scalar(
            select(Statement).where(Statement.account_id == account_id, Statement.id == source_id)
        )
        if statement is not None:
            occurrences.append(
                _blocked_guard_occurrence(
                    guard_code="W1",
                    source_type="statement",
                    source_id=statement.id,
                    building_id=statement.building_id,
                    today=today,
                    blockers=(
                        "W1-RENTER-DELIVERY-CONTEXT-MISSING",
                        "W1-APPROVED-RULE-BUNDLE-MISSING",
                    ),
                )
            )
            continue
        tenancy = session.scalar(
            select(Tenancy).where(Tenancy.account_id == account_id, Tenancy.id == source_id)
        )
        if tenancy is not None:
            unit = session.scalar(
                select(Unit).where(Unit.account_id == account_id, Unit.id == tenancy.unit_id)
            )
            if unit is None:
                missing.append(f"SOURCE-CONTEXT-MISSING:{source_id}")
                continue
            for guard_code in ("W3", "W5", "W6", "W7"):
                occurrences.append(
                    _blocked_guard_occurrence(
                        guard_code=guard_code,
                        source_type="tenancy",
                        source_id=tenancy.id,
                        building_id=unit.building_id,
                        today=today,
                        blockers=(f"{guard_code}-NORMALIZED-SOURCE-INPUTS-MISSING",),
                    )
                )
            continue
        meter = session.scalar(
            select(Meter).where(Meter.account_id == account_id, Meter.id == source_id)
        )
        if meter is not None:
            occurrences.append(
                _blocked_guard_occurrence(
                    guard_code="W2",
                    source_type="meter",
                    source_id=meter.id,
                    building_id=meter.building_id,
                    today=today,
                    blockers=(
                        "W2-ORIGINAL-CALIBRATION-DATE-SOURCE-MISSING",
                        "W2-APPROVED-RULE-BUNDLE-MISSING",
                    ),
                )
            )
            continue
        missing.append(f"SOURCE-NOT-FOUND:{source_id}")
    return tuple(occurrences), tuple(missing)


def _schedule_response(row: DeliveryScheduleVersion) -> DeliveryScheduleResponse:
    return DeliveryScheduleResponse(
        id=row.id,
        building_id=row.building_id,
        delivery_kind=row.delivery_kind,
        version=row.version,
        enabled=row.enabled,
        supersedes_schedule_version_id=row.supersedes_schedule_version_id,
        valid_from=row.valid_from,
        schedule_snapshot=row.schedule_snapshot,
        created_at=row.created_at,
    )


@router.get("/delivery-schedules")
def list_delivery_schedules(
    account_id: str, session: PathAccountSession
) -> DeliveryScheduleListResponse:
    scope = _authorize(session, "schedule_read")
    rows = session.scalars(
        select(DeliveryScheduleVersion)
        .where(DeliveryScheduleVersion.account_id == account_id)
        .order_by(
            DeliveryScheduleVersion.building_id,
            DeliveryScheduleVersion.delivery_kind,
            DeliveryScheduleVersion.version,
        )
    ).all()
    return DeliveryScheduleListResponse(
        schedules=[_schedule_response(row) for row in filter_m9_rows_for_scope(rows, scope)]
    )


@router.post("/delivery-schedules", status_code=201, responses=_WRITE_RESPONSES)
def create_delivery_schedule(
    account_id: str,
    body: DeliveryScheduleCreate,
    session: PathAccountSession,
) -> DeliveryScheduleResponse:
    _authorize(session, "schedule_write")
    if body.delivery_kind == "UVI":
        raise HTTPException(
            status_code=422,
            detail="Für UVI ist noch keine freigegebene unveränderliche Dokumentquelle vorhanden.",
        )
    source_context = session.execute(
        select(StatementArchive, Statement)
        .join(
            Statement,
            (Statement.id == StatementArchive.statement_id)
            & (Statement.account_id == StatementArchive.account_id),
        )
        .join(
            Tenancy,
            (Tenancy.id == StatementArchive.tenancy_id)
            & (Tenancy.account_id == StatementArchive.account_id),
        )
        .join(
            Unit,
            (Unit.id == Tenancy.unit_id) & (Unit.account_id == Tenancy.account_id),
        )
        .where(
            StatementArchive.account_id == account_id,
            StatementArchive.id == body.source_id,
            StatementArchive.audience == "TENANT",
            StatementArchive.tenancy_id.is_not(None),
        )
    ).one_or_none()
    if source_context is None:
        raise HTTPException(status_code=404, detail="Mieterausfertigung nicht gefunden")
    archive, statement = source_context
    building_id = statement.building_id
    if body.building_id is not None and body.building_id != building_id:
        raise HTTPException(
            status_code=422,
            detail="Mieterausfertigung und Objekt gehören nicht zur selben Abrechnung.",
        )
    building = session.scalar(
        select(Building).where(Building.account_id == account_id, Building.id == building_id)
    )
    if building is None:
        raise HTTPException(status_code=404, detail="Objekt nicht gefunden")
    if archive.tenancy_id is None:
        raise HTTPException(status_code=404, detail="Abrechnung nicht gefunden")
    occurrence_key = f"annual-statement:{statement.id}:{archive.id}:{archive.tenancy_id}"
    previous = session.scalar(
        select(DeliveryScheduleVersion)
        .where(
            DeliveryScheduleVersion.account_id == account_id,
            DeliveryScheduleVersion.building_id == building_id,
            DeliveryScheduleVersion.delivery_kind == body.delivery_kind,
        )
        .order_by(DeliveryScheduleVersion.version.desc())
        .limit(1)
    )
    row = DeliveryScheduleVersion(
        id=new_id(),
        account_id=account_id,
        building_id=building_id,
        delivery_kind=body.delivery_kind,
        version=1 if previous is None else previous.version + 1,
        enabled=body.enabled,
        supersedes_schedule_version_id=None if previous is None else previous.id,
        valid_from=body.valid_from,
        schedule_snapshot={
            "enabled": body.enabled,
            "valid_from": body.valid_from.isoformat(),
            "statement_archive_id": archive.id,
            "statement_id": statement.id,
            "statement_period": {
                "period_start": statement.period_start.isoformat(),
                "period_end": statement.period_end.isoformat(),
            },
            "occurrence_key": occurrence_key,
        },
    )
    session.add(row)
    session.flush()
    return _schedule_response(row)


@router.get("/reminders")
def list_reminders(account_id: str, session: PathAccountSession) -> ReminderListResponse:
    scope = _authorize(session, "reminder_read")
    rows = session.execute(
        select(GuardReminder, GuardEvaluation.building_id)
        .join(GuardEvaluation, GuardEvaluation.id == GuardReminder.guard_evaluation_id)
        .where(
            GuardReminder.account_id == account_id,
            GuardEvaluation.account_id == account_id,
        )
        .order_by(GuardReminder.due_at.desc(), GuardReminder.id)
    ).all()
    visible = filter_m9_rows_for_scope(
        [
            _ReminderRow(reminder=reminder, building_id=building_id)
            for reminder, building_id in rows
        ],
        scope,
    )
    return ReminderListResponse(
        reminders=[
            ReminderResponse(
                id=item.reminder.id,
                guard_evaluation_id=item.reminder.guard_evaluation_id,
                occurrence_key=item.reminder.occurrence_key,
                building_id=item.building_id,
                channel=item.reminder.channel,
                due_at=item.reminder.due_at,
                idempotency_key=item.reminder.idempotency_key,
                payload_snapshot=item.reminder.payload_snapshot,
                created_at=item.reminder.created_at,
            )
            for item in visible
        ]
    )


class _ReminderRow:
    def __init__(self, *, reminder: GuardReminder, building_id: str) -> None:
        self.reminder = reminder
        self.building_id = building_id


def _checklist_response(
    session: Session, account_id: str, row: ChecklistInstance
) -> ChecklistResponse:
    events = session.scalars(
        select(ChecklistItemEvent)
        .where(
            ChecklistItemEvent.account_id == account_id,
            ChecklistItemEvent.checklist_instance_id == row.id,
        )
        .order_by(ChecklistItemEvent.occurred_at, ChecklistItemEvent.id)
    ).all()
    return ChecklistResponse(
        id=row.id,
        building_id=row.building_id,
        template_id=row.template_id,
        template_version=row.template_version,
        template_snapshot=row.template_snapshot,
        occurrence_key=row.occurrence_key,
        events=[
            ChecklistEventResponse(
                id=event.id,
                item_id=event.item_id,
                event_type=event.event_type,
                occurred_at=event.occurred_at,
                actor_membership_id=event.actor_membership_id,
                idempotency_key=event.idempotency_key,
                event_snapshot=event.event_snapshot,
            )
            for event in events
        ],
    )


@router.get("/checklists")
def list_checklists(account_id: str, session: PathAccountSession) -> ChecklistListResponse:
    scope = _authorize(session, "checklist_read")
    rows = session.scalars(
        select(ChecklistInstance)
        .where(ChecklistInstance.account_id == account_id)
        .order_by(ChecklistInstance.created_at, ChecklistInstance.id)
    ).all()
    visible = filter_m9_rows_for_scope(rows, scope)
    return ChecklistListResponse(
        checklists=[_checklist_response(session, account_id, row) for row in visible],
        production_blocked=True,
        blocker="Kein freigegebener produktiver Checklisten-Katalog vorhanden.",
    )


def _template_has_item(snapshot: dict[str, object], item_id: str) -> bool:
    raw_items = snapshot.get("items")
    if not isinstance(raw_items, list):
        return False
    return any(
        isinstance(item, dict) and item.get("id", item.get("item_id")) == item_id
        for item in raw_items
    )


@router.post(
    "/checklists/{id}/items/{item_id}/events",
    status_code=201,
    responses=_WRITE_RESPONSES,
)
def create_checklist_item_event(
    account_id: str,
    id: str,
    item_id: str,
    body: ChecklistItemEventCreate,
    session: PathAccountSession,
) -> ChecklistEventResponse:
    scope = _authorize(session, "checklist_write")
    checklist = session.scalar(
        select(ChecklistInstance).where(
            ChecklistInstance.account_id == account_id, ChecklistInstance.id == id
        )
    )
    if checklist is None:
        raise HTTPException(status_code=404, detail="Checkliste nicht gefunden")
    require_m9_row_for_scope(checklist, scope)
    if not _template_has_item(checklist.template_snapshot, item_id):
        raise HTTPException(status_code=422, detail="Eintrag gehört nicht zu dieser Checkliste.")
    existing = session.scalar(
        select(ChecklistItemEvent).where(
            ChecklistItemEvent.account_id == account_id,
            ChecklistItemEvent.idempotency_key == body.idempotency_key,
        )
    )
    if existing is not None:
        if existing.checklist_instance_id != id or existing.item_id != item_id:
            raise HTTPException(status_code=422, detail="Idempotenzschlüssel ist bereits belegt.")
        return ChecklistEventResponse(
            id=existing.id,
            item_id=existing.item_id,
            event_type=existing.event_type,
            occurred_at=existing.occurred_at,
            actor_membership_id=existing.actor_membership_id,
            idempotency_key=existing.idempotency_key,
            event_snapshot=existing.event_snapshot,
        )
    event = ChecklistItemEvent(
        id=new_id(),
        account_id=account_id,
        checklist_instance_id=id,
        item_id=item_id,
        event_type=body.event_type,
        occurred_at=body.occurred_at,
        actor_membership_id=scope.membership_id,
        idempotency_key=body.idempotency_key,
        event_snapshot=body.event_snapshot,
    )
    session.add(event)
    session.flush()
    return ChecklistEventResponse(
        id=event.id,
        item_id=event.item_id,
        event_type=event.event_type,
        occurred_at=event.occurred_at,
        actor_membership_id=event.actor_membership_id,
        idempotency_key=event.idempotency_key,
        event_snapshot=event.event_snapshot,
    )


def _latest_provider_event(
    session: Session, account_id: str, attempt_id: str
) -> EmailDeliveryStatusEvent | None:
    return session.scalar(
        select(EmailDeliveryStatusEvent)
        .where(
            EmailDeliveryStatusEvent.account_id == account_id,
            EmailDeliveryStatusEvent.email_attempt_id == attempt_id,
        )
        .order_by(EmailDeliveryStatusEvent.occurred_at.desc(), EmailDeliveryStatusEvent.id.desc())
        .limit(1)
    )


def _legal_event(
    session: Session, account_id: str, artifact: RenterDeliveryArtifact
) -> GuardResolutionEvent | None:
    return session.scalar(
        select(GuardResolutionEvent)
        .join(GuardEvaluation, GuardEvaluation.id == GuardResolutionEvent.guard_evaluation_id)
        .where(
            GuardResolutionEvent.account_id == account_id,
            GuardEvaluation.account_id == account_id,
            GuardEvaluation.guard_code == "W1",
            GuardEvaluation.building_id == artifact.building_id,
            GuardEvaluation.unit_id == artifact.unit_id,
            GuardEvaluation.tenancy_id == artifact.tenancy_id,
            GuardEvaluation.renter_id == artifact.renter_id,
            GuardEvaluation.occurrence_key == artifact.occurrence_key,
            GuardResolutionEvent.event_type.in_(
                (
                    "statement_sent",
                    "statement_delivery_evidence_late",
                    "statement_sent_correction",
                    "statement_delivery_evidence_late_correction",
                )
            ),
            GuardResolutionEvent.renter_delivery_artifact_id == artifact.id,
        )
        .order_by(GuardResolutionEvent.occurred_at.desc(), GuardResolutionEvent.id.desc())
        .limit(1)
    )


def guard_resolution_idempotency_key(
    *,
    account_id: str,
    delivery_id: str,
    delivered_on: date,
    evidence_reference: str,
) -> str:
    """Stable, account-scoped identity for one owner delivery assertion."""

    material = "\x00".join((account_id, delivery_id, delivered_on.isoformat(), evidence_reference))
    return sha256(material.encode("utf-8")).hexdigest()


def _delivery_response(
    session: Session, account_id: str, artifact: RenterDeliveryArtifact
) -> DeliveryResponse:
    attempt = session.scalar(
        select(EmailAttempt)
        .where(
            EmailAttempt.account_id == account_id,
            EmailAttempt.renter_delivery_artifact_id == artifact.id,
        )
        .order_by(EmailAttempt.attempted_at.desc(), EmailAttempt.id.desc())
        .limit(1)
    )
    provider = None if attempt is None else _latest_provider_event(session, account_id, attempt.id)
    suppression_events = (
        []
        if attempt is None
        else session.scalars(
            select(RecipientSuppressionEvent)
            .where(
                RecipientSuppressionEvent.account_id == account_id,
                RecipientSuppressionEvent.normalized_recipient == attempt.normalized_recipient,
            )
            .order_by(
                RecipientSuppressionEvent.occurred_at,
                RecipientSuppressionEvent.id,
            )
        ).all()
    )
    legal = _legal_event(session, account_id, artifact)
    delivered_on_raw = None if legal is None else legal.event_snapshot.get("delivered_on")
    return DeliveryResponse(
        id=artifact.id,
        renter_id=artifact.renter_id,
        artifact_id=artifact.id,
        building_id=artifact.building_id,
        occurrence_key=artifact.occurrence_key,
        delivery_kind=artifact.artifact_kind,
        recipient=None if attempt is None else attempt.normalized_recipient,
        blocked_reason=("PRODUCTION_BLOCKED" if artifact.production_blocked else None),
        blocked_detail=(
            "Dokument ist nicht produktionsfreigegeben." if artifact.production_blocked else None
        ),
        provider_status=None if provider is None else provider.status,
        provider_delivered_at=(
            provider.occurred_at
            if provider is not None and provider.status == "DELIVERED"
            else None
        ),
        attempted_at=None if attempt is None else attempt.attempted_at,
        status_occurred_at=None if provider is None else provider.occurred_at,
        suppression_events=[
            {
                "id": event.id,
                "normalizedAddress": event.normalized_recipient,
                "reason": event.reason,
                "occurredAt": event.occurred_at.isoformat(),
            }
            for event in suppression_events
        ],
        legally_confirmed=legal is not None,
        delivered_on=(
            date.fromisoformat(delivered_on_raw) if isinstance(delivered_on_raw, str) else None
        ),
        evidence_reference=None if legal is None else legal.evidence_reference,
    )


@router.get("/deliveries")
def list_deliveries(account_id: str, session: PathAccountSession) -> DeliveryListResponse:
    scope = _authorize(session, "delivery_read")
    rows = session.scalars(
        select(RenterDeliveryArtifact)
        .where(RenterDeliveryArtifact.account_id == account_id)
        .order_by(RenterDeliveryArtifact.generated_at.desc(), RenterDeliveryArtifact.id)
    ).all()
    return DeliveryListResponse(
        deliveries=[
            _delivery_response(session, account_id, row)
            for row in filter_m9_rows_for_scope(rows, scope)
        ]
    )


def _delivery_context(
    session: Session, account_id: str, body: DeliveryCreate
) -> tuple[RenterDeliveryArtifact, Building, Renter]:
    artifact = session.scalar(
        select(RenterDeliveryArtifact).where(
            RenterDeliveryArtifact.account_id == account_id,
            RenterDeliveryArtifact.id == body.artifact_id,
        )
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="Zustelldokument nicht gefunden")
    building = session.scalar(
        select(Building).where(
            Building.account_id == account_id,
            Building.id == artifact.building_id,
        )
    )
    unit = session.scalar(
        select(Unit).where(Unit.account_id == account_id, Unit.id == artifact.unit_id)
    )
    tenancy = session.scalar(
        select(Tenancy).where(Tenancy.account_id == account_id, Tenancy.id == artifact.tenancy_id)
    )
    renter = session.scalar(
        select(Renter).where(Renter.account_id == account_id, Renter.id == artifact.renter_id)
    )
    party = session.scalar(
        select(TenancyParty).where(
            TenancyParty.account_id == account_id,
            TenancyParty.tenancy_id == artifact.tenancy_id,
            TenancyParty.renter_id == artifact.renter_id,
        )
    )
    if any(value is None for value in (building, unit, tenancy, renter, party)):
        raise HTTPException(status_code=422, detail="Zustellkontext ist unvollständig.")
    assert building is not None and unit is not None and tenancy is not None
    assert renter is not None and party is not None
    validate_delivery_relationships(
        body,
        building=building,
        unit=unit,
        tenancy=tenancy,
        renter=renter,
        tenancy_party=party,
        artifact=artifact,
    )
    if (
        body.building_id != artifact.building_id
        or body.renter_id != artifact.renter_id
        or body.delivery_kind != artifact.artifact_kind
        or body.occurrence_key != artifact.occurrence_key
    ):
        raise HTTPException(status_code=422, detail="Anfrage passt nicht zum Zustelldokument.")
    return artifact, building, renter


@router.post("/deliveries", responses=_WRITE_RESPONSES)
def create_delivery(
    account_id: str,
    body: DeliveryCreate,
    session: PathAccountSession,
    gateway: Annotated[EmailGateway, Depends(email_gateway_for_delivery)],
    now: Annotated[datetime, Depends(delivery_clock)],
) -> DeliveryResponse:
    _authorize(session, "send")
    artifact, building, renter = _delivery_context(session, account_id, body)
    landlord = None
    if building.landlord_id is not None:
        landlord = session.scalar(
            select(Landlord).where(
                Landlord.account_id == account_id, Landlord.id == building.landlord_id
            )
        )
    if landlord is None or not landlord.legal_name.strip():
        return DeliveryResponse(
            id=artifact.id,
            renter_id=renter.id,
            artifact_id=artifact.id,
            building_id=building.id,
            occurrence_key=artifact.occurrence_key,
            delivery_kind=artifact.artifact_kind,
            blocked_reason="PRODUCTION_BLOCKED",
            blocked_detail="Der Vermieter-Absendername fehlt.",
            provider_status=None,
            provider_delivered_at=None,
            legally_confirmed=False,
            delivered_on=None,
            evidence_reference=None,
        )
    kind = ScheduledDeliveryKind(body.delivery_kind)
    subject = (
        "Ihre Betriebskostenabrechnung"
        if kind is ScheduledDeliveryKind.ANNUAL_STATEMENT
        else "Ihre monatliche Verbrauchsinformation"
    )
    result = dispatch_renter_artifact(
        session,
        account_id=account_id,
        today=now.date(),
        now=now,
        request=RenterDeliveryRequest(
            building_id=body.building_id,
            renter_id=body.renter_id,
            delivery_kind=kind,
            occurrence_key=body.occurrence_key,
            subject_de=subject,
            html_body_de="Das angeforderte Dokument finden Sie im Anhang.",
            from_name=landlord.legal_name,
            sender_address=_SENDER_ADDRESS,
            artifact_id=body.artifact_id,
        ),
        gateway=gateway,
    )
    if result.blocked:
        blocked = result.blocked[0]
        return DeliveryResponse(
            id=artifact.id,
            renter_id=artifact.renter_id,
            artifact_id=artifact.id,
            building_id=artifact.building_id,
            occurrence_key=artifact.occurrence_key,
            delivery_kind=artifact.artifact_kind,
            blocked_reason=blocked.reason.value,
            blocked_detail=blocked.detail,
            provider_status=None,
            provider_delivered_at=None,
            legally_confirmed=False,
            delivered_on=None,
            evidence_reference=None,
        )
    return _delivery_response(session, account_id, artifact)


@router.post("/deliveries/{id}/confirm", responses=_WRITE_RESPONSES)
def confirm_delivery(
    account_id: str,
    id: str,
    body: DeliveryConfirmationCreate,
    session: PathAccountSession,
    now: Annotated[datetime, Depends(delivery_clock)],
) -> DeliveryResponse:
    scope = _authorize(session, "confirm")
    artifact = session.scalar(
        select(RenterDeliveryArtifact).where(
            RenterDeliveryArtifact.account_id == account_id,
            RenterDeliveryArtifact.id == id,
        )
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="Zustellung nicht gefunden")
    if artifact.artifact_kind != "ANNUAL_STATEMENT":
        raise HTTPException(
            status_code=422,
            detail="Nur eine Betriebskostenabrechnung kann W1 auflösen.",
        )
    evaluation = session.scalar(
        select(GuardEvaluation)
        .where(
            GuardEvaluation.account_id == account_id,
            GuardEvaluation.guard_code == "W1",
            GuardEvaluation.building_id == artifact.building_id,
            GuardEvaluation.unit_id == artifact.unit_id,
            GuardEvaluation.tenancy_id == artifact.tenancy_id,
            GuardEvaluation.renter_id == artifact.renter_id,
            GuardEvaluation.occurrence_key == artifact.occurrence_key,
        )
        .order_by(GuardEvaluation.evaluated_at.desc())
        .limit(1)
    )
    if evaluation is None:
        raise HTTPException(
            status_code=422,
            detail="Keine passende W1-Auswertung für diese Zustellung gefunden.",
        )
    decision = evaluate_w1_delivery_confirmation(
        artifact=artifact,
        evaluation=evaluation,
        delivered_on=body.delivered_on,
        today=now.date(),
    )
    idempotency_key = guard_resolution_idempotency_key(
        account_id=account_id,
        delivery_id=artifact.id,
        delivered_on=body.delivered_on,
        evidence_reference=body.evidence_reference,
    )
    existing = _legal_event(session, account_id, artifact)
    idempotent_event = session.scalar(
        select(GuardResolutionEvent).where(
            GuardResolutionEvent.account_id == account_id,
            GuardResolutionEvent.idempotency_key == idempotency_key,
        )
    )
    if (
        idempotent_event is not None
        and getattr(idempotent_event, "idempotency_key", None) == idempotency_key
    ):
        return _delivery_response(session, account_id, artifact)
    existing_delivered_on = (
        None if existing is None else existing.event_snapshot.get("delivered_on")
    )
    existing_key = None if existing is None else getattr(existing, "idempotency_key", None)
    if existing is not None and not existing_key and isinstance(existing_delivered_on, str):
        existing_key = guard_resolution_idempotency_key(
            account_id=account_id,
            delivery_id=artifact.id,
            delivered_on=date.fromisoformat(existing_delivered_on),
            evidence_reference=existing.evidence_reference,
        )
    exact_replay = existing is not None and existing_key == idempotency_key
    if not exact_replay:
        is_correction = existing is not None
        if is_correction:
            event_type = (
                "statement_sent_correction"
                if decision.resolve_w1
                else "statement_delivery_evidence_late_correction"
            )
        else:
            event_type = (
                "statement_sent"
                if decision.append_resolution_event
                else "statement_delivery_evidence_late"
            )
        event_snapshot: dict[str, object] = {
            "artifact_id": artifact.id,
            "delivered_on": body.delivered_on.isoformat(),
            "confirmed_by_owner": True,
            "late_delivery": decision.late_delivery,
            "resolves_w1": decision.resolve_w1,
            "is_correction": is_correction,
        }
        if existing is not None:
            event_snapshot["supersedes_event_id"] = existing.id
            event_snapshot["corrects_delivered_on"] = existing_delivered_on
        session.add(
            GuardResolutionEvent(
                id=new_id(),
                account_id=account_id,
                guard_evaluation_id=evaluation.id,
                event_type=event_type,
                occurred_at=now,
                evidence_reference=body.evidence_reference,
                event_snapshot=event_snapshot,
                idempotency_key=idempotency_key,
                renter_delivery_artifact_id=artifact.id,
                confirmed_by_membership_id=scope.membership_id,
            )
        )
        session.flush()
    return _delivery_response(session, account_id, artifact)
