"""Owner-only investment entitlement and immutable case snapshots."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict
from datetime import UTC, date, datetime
from hashlib import sha256
from importlib.metadata import version as package_version
from typing import Literal

from fastapi import APIRouter, HTTPException, Response, status
from investment_engine import InvestmentInput, calculate_investment_snapshot
from lokara_db import (
    InvestmentEntitlementEvent,
    InvestmentInputSnapshot,
    InvestmentLayoutVersion,
    InvestmentResultSnapshot,
    new_id,
)
from lokara_pdf import (
    DEFAULT_BANK_LAYOUT_SNAPSHOT,
    InvestmentBankPdfData,
    render_investment_bank_pdf,
)
from lokara_rules_store import resolve_investment_rule_bundle
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel
from sqlalchemy import select, text

from ..authorization import portal_membership_id, require_owner
from ..deps import PathAccountSession

router = APIRouter(prefix="/a/{account_id}/investment", tags=["investment"])

_ENTITLEMENT_KEY = "INVESTMENT"
_DEFAULT_LAYOUT_KEY = "DEFAULT_BANK"
_CANONICAL_VERSION = "postgres-jsonb-text-v1"
_ENGINE_VERSION = f"lokara-investment-engine/{package_version('lokara-investment-engine')}"


class InvestmentApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        strict=True,
    )


class AfaReferenceIn(InvestmentApiModel):
    afa_basis_cents: int | None = Field(default=None, ge=0)
    annual_full_afa_cents: int | None = Field(default=None, ge=0)
    source: str | None = Field(default=None, min_length=1)
    record_version: str | None = Field(default=None, min_length=1)


class BankHeaderIn(InvestmentApiModel):
    address: str | None = Field(default=None, min_length=1)
    property_type: str | None = Field(default=None, min_length=1)
    year_built: int | None = Field(default=None, ge=1)
    area_sqm_x100: int | None = Field(default=None, ge=0)
    unit_count: int | None = Field(default=None, ge=0)
    creator: str | None = Field(default=None, min_length=1)
    export_date: str | None = Field(default=None, min_length=1)
    layout_version: str | None = Field(default=None, min_length=1)


class InvestmentFactsIn(InvestmentApiModel):
    purchase_price_cents: int | None = Field(default=None, ge=0)
    acquisition_costs_cents: int | None = Field(default=None, ge=0)
    monthly_actual_rent_cents: int | None = Field(default=None, ge=0)
    vacancy_bp: int | None = Field(default=None, ge=0, le=10_000)
    administration_cents: int | None = Field(default=None, ge=0)
    maintenance_cents: int | None = Field(default=None, ge=0)
    reserve_cents: int | None = Field(default=None, ge=0)
    vacancy_risk_cents: int | None = Field(default=None, ge=0)
    equity_cents: int | None = Field(default=None, ge=0)
    loan_cents: int | None = Field(default=None, ge=0)
    interest_bp: int | None = Field(default=None, ge=0)
    initial_repayment_bp: int | None = Field(default=None, ge=0)
    fixed_monthly_annuity_cents: int | None = Field(default=None, ge=0)
    marginal_tax_bp: int | None = Field(default=None, ge=0, le=9_999)
    building_share_bp: int | None = Field(default=None, ge=0, le=10_000)
    afa_rate_bp: int | None = Field(default=None, ge=0)
    annual_full_afa_cents: int | None = Field(default=None, ge=0)
    afa_record_version: str | None = Field(default=None, min_length=1)
    analysis_period_months: int | None = Field(default=None, ge=0)
    financing_provenance: Literal["annahme", "indikativ", "angebot"] | None = None
    afa_reference: AfaReferenceIn | None = None
    bank_header: BankHeaderIn | None = None

    @model_validator(mode="after")
    def validate_financing_and_afa_provenance(self) -> InvestmentFactsIn:
        if self.initial_repayment_bp is not None and self.fixed_monthly_annuity_cents is not None:
            raise ValueError("only one repayment input may be supplied")
        if self.annual_full_afa_cents is not None and self.afa_record_version is None:
            raise ValueError("afaRecordVersion is required with annualFullAfaCents")
        if (
            self.afa_reference is not None
            and (
                self.afa_reference.afa_basis_cents is not None
                or self.afa_reference.annual_full_afa_cents is not None
            )
            and (self.afa_reference.source is None or self.afa_reference.record_version is None)
        ):
            raise ValueError("AfA reference provenance is incomplete")
        return self


class EntitlementWrite(InvestmentApiModel):
    enabled: bool


class EntitlementResponse(InvestmentApiModel):
    enabled: bool
    event_id: str | None
    version: int | None
    recorded_at: datetime | None


class InvestmentCaseCreate(InvestmentApiModel):
    facts: InvestmentFactsIn
    layout_version_id: str | None = Field(default=None, min_length=1)


class InvestmentCaseResponse(InvestmentApiModel):
    case_key: str
    version: int
    result_id: str
    outcome: str
    calculated_values: dict[str, object]
    kpi_slots: dict[str, object]
    rechtsstand: str
    production_blocked: bool
    findings: list[str]
    warnings: list[str]


class SensitivityResponse(InvestmentApiModel):
    interest_sensitivity: list[dict[str, object]]
    repayment_sensitivity: list[dict[str, object]]
    repayment_axis_meaning: str


class BankViewResponse(InvestmentApiModel):
    bank_view: dict[str, object]


def _stored_dict(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RuntimeError("Stored investment snapshot object is malformed")
    return value


def _stored_list(value: object) -> list[object]:
    if not isinstance(value, (list, tuple)):
        raise RuntimeError("Stored investment snapshot array is malformed")
    return list(value)


def _latest_entitlement(
    session: PathAccountSession, account_id: str
) -> InvestmentEntitlementEvent | None:
    return session.scalar(
        select(InvestmentEntitlementEvent)
        .where(
            InvestmentEntitlementEvent.account_id == account_id,
            InvestmentEntitlementEvent.entitlement_key == _ENTITLEMENT_KEY,
        )
        .order_by(InvestmentEntitlementEvent.version.desc())
        .limit(1)
    )


def _entitlement_response(event: InvestmentEntitlementEvent | None) -> EntitlementResponse:
    if event is None:
        return EntitlementResponse(
            enabled=False,
            event_id=None,
            version=None,
            recorded_at=None,
        )
    return EntitlementResponse(
        enabled=event.enabled,
        event_id=event.id,
        version=event.version,
        recorded_at=event.recorded_at,
    )


def _require_enabled(session: PathAccountSession, account_id: str) -> None:
    event = _latest_entitlement(session, account_id)
    if event is None or not event.enabled:
        raise HTTPException(status_code=403, detail="Investment access is not enabled")


def _stored_case(
    session: PathAccountSession,
    account_id: str,
    case_key: str,
) -> tuple[InvestmentInputSnapshot, InvestmentResultSnapshot]:
    row = session.execute(
        select(InvestmentInputSnapshot, InvestmentResultSnapshot)
        .join(
            InvestmentResultSnapshot,
            InvestmentResultSnapshot.input_snapshot_id == InvestmentInputSnapshot.id,
        )
        .where(
            InvestmentInputSnapshot.account_id == account_id,
            InvestmentResultSnapshot.account_id == account_id,
            InvestmentInputSnapshot.case_key == case_key,
        )
        .order_by(InvestmentInputSnapshot.version.desc())
        .limit(1)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Investment case not found")
    return row[0], row[1]


def _case_response(
    input_snapshot: InvestmentInputSnapshot,
    result_snapshot: InvestmentResultSnapshot,
) -> InvestmentCaseResponse:
    result = result_snapshot.result_snapshot
    return InvestmentCaseResponse(
        case_key=input_snapshot.case_key,
        version=input_snapshot.version,
        result_id=result_snapshot.id,
        outcome=str(result["outcome"]),
        calculated_values=_stored_dict(result["calculated_values"]),
        kpi_slots=_stored_dict(result["kpi_slots"]),
        rechtsstand=str(result["rechtsstand"]),
        production_blocked=bool(result["production_blocked"]),
        findings=[str(item) for item in _stored_list(result["findings"])],
        warnings=[str(item) for item in _stored_list(result["warnings"])],
    )


def _canonical_input_bytes(
    session: PathAccountSession,
    *,
    facts: dict[str, object],
    rules: dict[str, object],
    financing: dict[str, object],
    afa: dict[str, object],
    layout_version_id: str | None,
) -> bytes:
    value = session.scalar(
        text(
            "SELECT convert_to(jsonb_build_object("
            "'afa_provenance', CAST(:afa AS jsonb), "
            "'financing_provenance', CAST(:financing AS jsonb), "
            "'input', CAST(:facts AS jsonb), "
            "'layout_version_id', CAST(:layout_id AS text), "
            "'rules', CAST(:rules AS jsonb))::text, 'UTF8')"
        ),
        {
            "afa": json.dumps(afa),
            "financing": json.dumps(financing),
            "facts": json.dumps(facts),
            "layout_id": layout_version_id,
            "rules": json.dumps(rules),
        },
    )
    if not isinstance(value, bytes):
        raise RuntimeError("PostgreSQL did not return canonical investment input bytes")
    return value


def _canonical_result_bytes(session: PathAccountSession, result: dict[str, object]) -> bytes:
    value = session.scalar(
        text("SELECT convert_to(CAST(:result AS jsonb)::text, 'UTF8')"),
        {"result": json.dumps(result)},
    )
    if not isinstance(value, bytes):
        raise RuntimeError("PostgreSQL did not return canonical investment result bytes")
    return value


def _afa_provenance_snapshot(
    facts: dict[str, object],
    rules: dict[str, object],
    engine_afa: dict[str, object],
) -> dict[str, object]:
    if engine_afa:
        return engine_afa
    reference = facts.get("afa_reference")
    if isinstance(reference, dict) and (
        reference.get("afa_basis_cents") is not None
        or reference.get("annual_full_afa_cents") is not None
    ):
        return {
            "source": reference["source"],
            "record_version": reference["record_version"],
            "assumption": False,
        }
    if facts.get("annual_full_afa_cents") is not None:
        return {
            "source": "wizard_input",
            "record_version": facts["afa_record_version"],
            "assumption": False,
        }
    return {
        "source": "acquisition_assumption",
        "record_version": rules["rechtsstand"],
        "assumption": True,
        "building_share_bp": facts.get("building_share_bp", rules["default_building_share_bp"]),
        "afa_rate_bp": facts.get("afa_rate_bp", rules["default_afa_rate_bp"]),
    }


def _default_layout_version(session: PathAccountSession, account_id: str) -> str:
    """Resolve the canonical account layout under one transaction-scoped stream lock."""

    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:stream_key, 0))"),
        {"stream_key": f"{account_id}:{_DEFAULT_LAYOUT_KEY}"},
    )
    previous = session.scalar(
        select(InvestmentLayoutVersion)
        .where(
            InvestmentLayoutVersion.account_id == account_id,
            InvestmentLayoutVersion.layout_key == _DEFAULT_LAYOUT_KEY,
        )
        .order_by(InvestmentLayoutVersion.version.desc())
        .limit(1)
    )
    if previous is not None and previous.layout_snapshot == DEFAULT_BANK_LAYOUT_SNAPSHOT:
        return previous.id
    layout = InvestmentLayoutVersion(
        id=new_id(),
        account_id=account_id,
        layout_key=_DEFAULT_LAYOUT_KEY,
        version=1 if previous is None else previous.version + 1,
        layout_snapshot=deepcopy(DEFAULT_BANK_LAYOUT_SNAPSHOT),
        supersedes_layout_version_id=None if previous is None else previous.id,
    )
    session.add(layout)
    session.flush()
    return layout.id


@router.get("/entitlement", response_model=EntitlementResponse)
def get_entitlement(account_id: str, session: PathAccountSession) -> EntitlementResponse:
    require_owner(session)
    return _entitlement_response(_latest_entitlement(session, account_id))


@router.post(
    "/entitlement",
    response_model=EntitlementResponse,
    status_code=status.HTTP_201_CREATED,
)
def append_entitlement(
    account_id: str,
    payload: EntitlementWrite,
    session: PathAccountSession,
) -> EntitlementResponse:
    require_owner(session)
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:stream_key, 0))"),
        {"stream_key": f"{account_id}:{_ENTITLEMENT_KEY}"},
    )
    previous = session.scalar(
        select(InvestmentEntitlementEvent)
        .where(
            InvestmentEntitlementEvent.account_id == account_id,
            InvestmentEntitlementEvent.entitlement_key == _ENTITLEMENT_KEY,
        )
        .order_by(InvestmentEntitlementEvent.version.desc())
        .limit(1)
    )
    event = InvestmentEntitlementEvent(
        id=new_id(),
        account_id=account_id,
        entitlement_key=_ENTITLEMENT_KEY,
        version=1 if previous is None else previous.version + 1,
        enabled=payload.enabled,
        supersedes_entitlement_event_id=None if previous is None else previous.id,
        recorded_by_membership_id=portal_membership_id(session),
    )
    session.add(event)
    session.flush()
    return _entitlement_response(event)


@router.post(
    "/cases",
    response_model=InvestmentCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_case(
    account_id: str,
    payload: InvestmentCaseCreate,
    session: PathAccountSession,
) -> InvestmentCaseResponse:
    require_owner(session)
    _require_enabled(session, account_id)
    layout_version_id = payload.layout_version_id
    if layout_version_id is not None:
        layout_exists = session.scalar(
            select(InvestmentLayoutVersion.id).where(
                InvestmentLayoutVersion.id == layout_version_id,
                InvestmentLayoutVersion.account_id == account_id,
            )
        )
        if layout_exists is None:
            raise HTTPException(status_code=422, detail="Invalid investment layout version")
    else:
        layout_version_id = _default_layout_version(session, account_id)

    facts = payload.facts.model_dump(
        mode="json",
        by_alias=False,
        exclude_unset=True,
        exclude_none=True,
    )
    rules_bundle = resolve_investment_rule_bundle(date(2026, 7, 1))
    rules = asdict(rules_bundle)
    try:
        calculated = calculate_investment_snapshot(InvestmentInput(facts=facts), rules_bundle)
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = asdict(calculated)
    financing = {
        "source": calculated.financing_provenance["source"],
        "record_version": rules_bundle.rechtsstand,
    }
    afa = _afa_provenance_snapshot(facts, rules, dict(calculated.afa_provenance))
    canonical_input = _canonical_input_bytes(
        session,
        facts=facts,
        rules=rules,
        financing=financing,
        afa=afa,
        layout_version_id=layout_version_id,
    )
    canonical_result = _canonical_result_bytes(session, result)
    now = datetime.now(UTC)
    case_key = new_id()
    input_id = new_id()
    result_id = new_id()
    stored_input = InvestmentInputSnapshot(
        id=input_id,
        account_id=account_id,
        case_key=case_key,
        version=1,
        input_snapshot=facts,
        rule_snapshot=rules,
        financing_provenance_snapshot=financing,
        afa_provenance_snapshot=afa,
        layout_version_id=layout_version_id,
        canonical_payload_version=_CANONICAL_VERSION,
        canonical_payload_bytes=canonical_input,
        sha256=sha256(canonical_input).hexdigest(),
        supersedes_input_snapshot_id=None,
        frozen_at=now,
    )
    session.add(stored_input)
    session.flush()
    stored_result = InvestmentResultSnapshot(
        id=result_id,
        account_id=account_id,
        input_snapshot_id=input_id,
        engine_version=_ENGINE_VERSION,
        result_snapshot=result,
        canonical_payload_version=_CANONICAL_VERSION,
        canonical_result_bytes=canonical_result,
        sha256=sha256(canonical_result).hexdigest(),
        calculated_at=now,
    )
    session.add(stored_result)
    session.flush()
    return _case_response(stored_input, stored_result)


@router.get("/cases/{case_key}", response_model=InvestmentCaseResponse)
def get_case(
    account_id: str,
    case_key: str,
    session: PathAccountSession,
) -> InvestmentCaseResponse:
    require_owner(session)
    _require_enabled(session, account_id)
    stored_input, stored_result = _stored_case(session, account_id, case_key)
    return _case_response(stored_input, stored_result)


@router.get("/cases/{case_key}/sensitivity", response_model=SensitivityResponse)
def get_sensitivity(
    account_id: str,
    case_key: str,
    session: PathAccountSession,
) -> SensitivityResponse:
    require_owner(session)
    _require_enabled(session, account_id)
    _stored_input, stored_result = _stored_case(session, account_id, case_key)
    result = stored_result.result_snapshot
    return SensitivityResponse(
        interest_sensitivity=[
            _stored_dict(item) for item in _stored_list(result["interest_sensitivity"])
        ],
        repayment_sensitivity=[
            _stored_dict(item) for item in _stored_list(result["repayment_sensitivity"])
        ],
        repayment_axis_meaning=str(result["repayment_axis_meaning"]),
    )


@router.get("/cases/{case_key}/bank-view", response_model=BankViewResponse)
def get_bank_view(
    account_id: str,
    case_key: str,
    session: PathAccountSession,
) -> BankViewResponse:
    require_owner(session)
    _require_enabled(session, account_id)
    _stored_input, stored_result = _stored_case(session, account_id, case_key)
    return BankViewResponse(bank_view=_stored_dict(stored_result.result_snapshot["bank_view"]))


@router.get("/cases/{case_key}/bank-pdf")
def get_bank_pdf(
    account_id: str,
    case_key: str,
    session: PathAccountSession,
) -> Response:
    require_owner(session)
    _require_enabled(session, account_id)
    stored_input, stored_result = _stored_case(session, account_id, case_key)
    if stored_input.layout_version_id is None:
        raise HTTPException(
            status_code=409,
            detail="Für dieses Prüfobjekt ist keine PDF-Vorlage gespeichert.",
        )
    layout = session.scalar(
        select(InvestmentLayoutVersion).where(
            InvestmentLayoutVersion.id == stored_input.layout_version_id,
            InvestmentLayoutVersion.account_id == account_id,
        )
    )
    if layout is None:
        raise HTTPException(status_code=404, detail="Investment case not found")
    result = _stored_dict(stored_result.result_snapshot)
    data = InvestmentBankPdfData(
        case_key=stored_input.case_key,
        input_version=stored_input.version,
        result_id=stored_result.id,
        engine_version=stored_result.engine_version,
        layout_version_id=layout.id,
        bank_view=_stored_dict(result["bank_view"]),
        result_snapshot=result,
        layout_snapshot=_stored_dict(layout.layout_snapshot),
    )
    return Response(
        content=render_investment_bank_pdf(data),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (f'attachment; filename="investitionsuebersicht-{case_key}.pdf"')
        },
    )
