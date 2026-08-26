"""M7 account-scoped AfA and tax-export workspace."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from hashlib import sha256
from typing import Literal, Protocol, cast

from afa_engine import AfaInput, AfaResult, AfaRuleBundle, calculate_afa_record
from export_engine import (
    TaxEventSource,
    assign_tax_year,
    build_anlage_v_overview,
    encode_anlage_v_csv,
    encode_datev_extf,
)
from export_engine import evaluate_export_readiness as evaluate_export_readiness
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse
from lokara_db import (
    AfaRecordVersion,
    Building,
    Role,
    TaxAdviserProfileVersion,
    TaxEvent,
    TaxExportArchive,
    TaxExportArtifact,
    TaxExportReadinessAttempt,
    TaxMappingVersion,
    new_id,
)
from lokara_pdf import (
    TAX_DISCLAIMER,
    AnlageVOverviewData,
    AnlageVOverviewLine,
    AnlageVSourceRef,
    anlage_v_overview_html,
    render_html_to_pdf,
)
from lokara_rules_store import (
    ANLAGE_V_LAYOUTS,
    VERIFIED_TEST_EXTF_PROFILES,
    AnlageVLayout,
    ExtfProfile,
    ResolvedAfaRuleBundle,
    ResolvedRule,
    get_rule,
)
from lokara_rules_store import (
    resolve_afa_rule_bundle as _resolve_afa_rule_bundle,
)
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import TaxAccountSession
from ..deps import tax_account_session_for_path as _tax_account_session_for_path

tax_account_session_for_path = _tax_account_session_for_path

router = APIRouter(prefix="/a/{account_id}/tax", tags=["tax"])

TaxAction = Literal[
    "read", "afa_write", "event_write", "profile_write", "mapping_write", "generate"
]


class PaymentAllocationComponents(Protocol):
    id: str
    costs_cents: int
    interest_cents: int
    principal_cents: int
    base_rent_cents: int
    nk_advance_cents: int
    heating_advance_cents: int
    garage_cents: int


def authorize_tax_action(role: Role, action: str) -> None:
    allowed = role is Role.OWNER or (
        role is Role.TAX_ADVISOR and action in {"read", "profile_write", "mapping_write"}
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="Keine Berechtigung für diese Steuerfunktion.")


def _authorize(session: Session, action: TaxAction) -> None:
    role = session.info.get("tax_role")
    if not isinstance(role, Role):
        raise RuntimeError("tax authorization scope is missing")
    authorize_tax_action(role, action)


class TaxApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class AfaRuleIn(TaxApiModel):
    register_rows: list[list[str]] = Field(default_factory=list)
    rechtsstand: str = "07/2026"


class AfaRequest(TaxApiModel):
    building_id: str
    tax_year: int = Field(ge=1900, le=2200)
    facts: dict[str, object]
    generated_at: datetime

    @field_validator("facts")
    @classmethod
    def _facts_have_no_renter_identity(cls, value: dict[str, object]) -> dict[str, object]:
        forbidden = {
            "renter",
            "renterid",
            "rentername",
            "renter_id",
            "renter_name",
            "mieter",
            "mieterid",
            "mietername",
            "mieter_id",
            "mieter_name",
        }

        def inspect(item: object) -> None:
            if isinstance(item, dict):
                for key, nested in item.items():
                    if isinstance(key, str) and key.lower() in forbidden:
                        raise ValueError("AfA facts must not contain renter identity fields")
                    inspect(nested)
            elif isinstance(item, list):
                for nested in item:
                    inspect(nested)

        inspect(value)
        return value


class AfaResponse(TaxApiModel):
    id: str | None = None
    version: int | None = None
    building_id: str
    tax_year: int
    result: dict[str, object]
    annual_afa_cents: int | None = None
    tax_year_afa_cents: int
    deductible_afa_cents: int
    non_deductible_afa_cents: int
    rechtsstand: str
    production_blocked: bool
    generated_at: datetime


class AfaHistoryResponse(TaxApiModel):
    records: list[AfaResponse]


class TaxBuildingResponse(TaxApiModel):
    id: str
    label: str


class TaxBuildingListResponse(TaxApiModel):
    buildings: list[TaxBuildingResponse]


class TaxEventCreate(TaxApiModel):
    building_id: str
    unit_id: str | None = None
    payment_date: date | None = None
    due_date: date | None = None
    category: str | None = Field(default=None, max_length=100)
    amount_cents: int = Field(ge=0)
    direction: Literal["einnahme", "ausgabe"]
    receipt_reference: str = Field(min_length=1, max_length=200)
    source: Literal["finapi", "manuell", "rechnung"] = "manuell"
    version: int = Field(default=1, ge=1)
    source_payment_allocation_id: str | None = None
    source_context: dict[str, object] = Field(default_factory=dict)
    recorded_at: datetime


class TaxEventCorrectionCreate(TaxApiModel):
    """A correction supersedes one stored event; it never re-parents or re-labels it.

    Stream fields are accepted so the client may echo what it displayed, but the
    superseded row decides them. Only the cash facts and the reason are correctable.
    """

    building_id: str
    unit_id: str | None = None
    payment_date: date | None = None
    due_date: date | None = None
    category: str | None = Field(default=None, max_length=100)
    amount_cents: int = Field(ge=0)
    direction: Literal["einnahme", "ausgabe"]
    receipt_reference: str | None = Field(default=None, min_length=1, max_length=200)
    source: dict[str, object] = Field(default_factory=dict)
    source_payment_allocation_id: str | None = None
    recorded_at: datetime
    correction_reason: str = Field(min_length=1, max_length=500)


class TaxEventResponse(TaxApiModel):
    id: str
    building_id: str
    unit_id: str | None
    payment_date: date | None
    due_date: date | None
    category: str | None
    amount_cents: int
    direction: str
    receipt_reference: str
    source: str
    version: int
    supersedes_tax_event_id: str | None
    recorded_at: datetime


class TaxEventListResponse(TaxApiModel):
    events: list[TaxEventResponse]


class AdviserProfile(TaxApiModel):
    beraternummer: str | None = Field(default=None, max_length=20)
    mandantennummer: str | None = Field(default=None, max_length=20)
    kontenrahmen: Literal["skr03", "skr04"] | None = None
    sachkontenlaenge: int | None = Field(default=None, ge=4, le=8)
    wj_beginn: date | None = None

    @field_validator("kontenrahmen", mode="before")
    @classmethod
    def _normalize_kontenrahmen(cls, value: object) -> object:
        return value.lower() if isinstance(value, str) else value


class AdviserProfileCreate(TaxApiModel):
    profile: AdviserProfile
    generated_at: datetime


class AdviserProfileResponse(TaxApiModel):
    id: str
    version: int
    profile: AdviserProfile
    production_blocked: bool
    generated_at: datetime


class TaxMappingEntry(TaxApiModel):
    tax_year: int = Field(ge=1900, le=2200)
    category: str = Field(min_length=1, max_length=100)
    anlage_v_line: str | None = Field(default=None, max_length=20)
    skr03_account: str | None = Field(default=None, max_length=20)
    skr04_account: str | None = Field(default=None, max_length=20)
    direction: Literal[
        "einnahme", "ausgabe", "non_cash", "sachbuchung", "clearing", "counter_account"
    ]
    valid_from: date
    valid_to: date | None = None
    verification_flag: Literal["verify-before-production"]
    source_version: str = Field(min_length=1, max_length=100)
    account_override: str | None = Field(default=None, max_length=20)
    override_by_tax_advisor: bool = False
    override_at: datetime | None = None


class TaxMappingCreate(TaxApiModel):
    tax_year: int | None = Field(default=None, ge=1900, le=2200)
    mapping: list[TaxMappingEntry]
    source_version: str = Field(min_length=1, max_length=100)
    rechtsstand: str
    generated_at: datetime


class TaxMappingResponse(TaxApiModel):
    id: str
    tax_year: int
    version: int
    mapping: list[TaxMappingEntry]
    source_version: str
    rechtsstand: str
    production_blocked: bool
    generated_at: datetime


class ReadinessRequest(TaxApiModel):
    export_kind: Literal["anlage_v_pdf", "anlage_v_csv", "datev_extf"]
    building_id: str
    tax_year: int = Field(ge=1900, le=2200)
    generated_at: datetime
    afa_record_version_id: str | None = None
    adviser_profile_version_id: str | None = None
    mapping_version_id: str


class ReadinessResponse(TaxApiModel):
    id: str
    findings: list[dict[str, object]]
    rechtsstand: str
    production_blocked: bool
    generated_at: datetime


class GenerateExportRequest(ReadinessRequest):
    pass


class VerifiedTestArtifact(TaxApiModel):
    """One artifact the server generated itself. It is never built from a client payload."""

    artifact_kind: Literal["anlage_v_pdf", "anlage_v_csv", "datev_extf"]
    filename: str = Field(min_length=1, max_length=200)
    mime_type: str = Field(min_length=1, max_length=100)
    content_bytes: bytes


class VerifiedTestBundle(TaxApiModel):
    """The exact bytes one verified-test generation produced, in archive order."""

    bundle_id: str = Field(min_length=1, max_length=100)
    artifacts: list[VerifiedTestArtifact]


class ExportArtifactResponse(TaxApiModel):
    id: str
    artifact_kind: str
    filename: str
    sha256: str


class ExportResponse(TaxApiModel):
    id: str
    version: int
    readiness_attempt_id: str
    sha256: str
    generated_at: datetime
    artifacts: list[ExportArtifactResponse]
    readiness_findings: list[dict[str, object]]
    blockers: list[str]
    afa_rechtsstand: str
    export_rechtsstand: str
    export_kind: Literal["anlage_v_pdf", "anlage_v_csv", "datev_extf"]
    building_id: str | None = None
    tax_year: int | None = None


class ExportHistoryResponse(TaxApiModel):
    exports: list[ExportResponse]


PUBLIC_TAX_RESPONSE_SCHEMAS = (
    TaxBuildingResponse,
    TaxBuildingListResponse,
    AfaResponse,
    AfaHistoryResponse,
    TaxEventResponse,
    TaxEventListResponse,
    AdviserProfileResponse,
    TaxMappingResponse,
    ReadinessResponse,
    ExportArtifactResponse,
    ExportResponse,
    ExportHistoryResponse,
)


@router.get("/buildings", response_model=TaxBuildingListResponse)
def list_tax_buildings(account_id: str, session: TaxAccountSession) -> TaxBuildingListResponse:
    del account_id
    _authorize(session, "read")
    rows = session.scalars(
        select(Building)
        .where(Building.archived_at.is_(None))
        .order_by(Building.street, Building.postal_code, Building.city, Building.id)
    ).all()
    return TaxBuildingListResponse(
        buildings=[
            TaxBuildingResponse(
                id=row.id,
                label=f"{row.street}, {row.postal_code} {row.city}",
            )
            for row in rows
        ]
    )


def resolve_afa_rule_bundle(tax_year: int) -> ResolvedAfaRuleBundle:
    """Resolve the immutable AfA authority bundle at the selected year end."""

    return _resolve_afa_rule_bundle(date(tax_year, 12, 31))


def _engine_rule_bundle(resolved: ResolvedAfaRuleBundle) -> AfaRuleBundle:
    return AfaRuleBundle(
        linear_rates_bp=resolved.linear_rates_bp,
        guard_rate_bp=resolved.guard_rate_bp,
        market_disagio_limit_bp=resolved.market_disagio_limit_bp,
        source_evidence=resolved.source_evidence,
        rechtsstand=resolved.rechtsstand,
        production_blocked=resolved.production_blocked,
    )


def _required_int(facts: dict[str, object], name: str) -> int:
    value = facts.get(name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"missing integer field {name}")
    return value


def _optional_int(facts: dict[str, object], name: str, default: int = 0) -> int:
    value = facts.get(name, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"invalid integer field {name}")
    return value


def _engine_result(normalized: dict[str, object], rules: AfaRuleBundle, tax_year: int) -> AfaResult:
    return calculate_afa_record(AfaInput(facts=normalized), rules, tax_year)


def _afa_result(body: AfaRequest) -> tuple[dict[str, object], str, bool]:
    facts = body.facts
    resolved = resolve_afa_rule_bundle(body.tax_year)
    rules = _engine_rule_bundle(resolved)
    normalized_inputs: list[dict[str, object]] = []
    findings: list[dict[str, object]] = []
    page04_handoffs: list[dict[str, object]] = []
    acquisition: dict[str, object] = {}

    def calculate(normalized: dict[str, object]) -> dict[str, object]:
        normalized_inputs.append(normalized)
        engine_result = _engine_result(normalized, rules, body.tax_year)
        findings.extend(
            {"code": finding.code, "message": finding.message}
            for finding in engine_result.findings
            if {"code": finding.code, "message": finding.message} not in findings
        )
        if engine_result.page04_handoff is not None:
            page04_handoffs.append(dict(engine_result.page04_handoff))
        return dict(engine_result.calculated_values)

    try:
        acquisition_type = facts.get("erwerbsart")
        year_built = _required_int(facts, "fertigstellungsjahr")
        if acquisition_type == "kauf":
            acquisition = calculate(
                {
                    "kaufpreis_cents": _required_int(facts, "kaufpreisCent"),
                    "grunderwerbsteuer_cents": _required_int(facts, "grunderwerbsteuerCent"),
                    "notar_grundbuch_cents": _required_int(facts, "notarGrundbuchCent"),
                    "grundschuld_notar_cents": _required_int(facts, "grundschuldkostenCent"),
                    "makler_cents": _required_int(facts, "maklerprovisionCent"),
                    "sonstige_ank_cents": _required_int(facts, "sonstigeAnkCent"),
                    "movable_assets_cents": _required_int(facts, "beweglicheWgCent"),
                }
            )
            acquisition_total = _required_int(acquisition, "acquisition_cost")
            route = facts.get("aufteilungsWeg")
            if route == "vertrag":
                building_basis = _required_int(facts, "vertragGebaeudeCent")
                land_basis = _required_int(facts, "vertragBodenCent")
                if building_basis + land_basis != acquisition_total:
                    raise ValueError("contract allocation does not reconcile")
                normalized_inputs.append(
                    {
                        "allocation_route": "contract",
                        "acquisition_cost_cents": acquisition_total,
                        "contract_building_cents": building_basis,
                        "contract_land_cents": land_basis,
                    }
                )
            elif route == "bmf":
                allocation = calculate(
                    {
                        "allocation_route": "bmf",
                        "acquisition_cost_cents": acquisition_total,
                        "land_area_sqm": _required_int(facts, "grundstuecksflaecheM2"),
                        "land_value_cents_per_sqm": _required_int(facts, "bodenrichtwertCentProM2"),
                        "living_area_sqm_x100": _required_int(facts, "wohnflaecheGesamt"),
                        "building_type": facts.get("gebaeudetyp"),
                        "nhk_cents_per_sqm_bgf": _required_int(facts, "nhkCentProM2Bgf"),
                        "price_index_bp": _required_int(facts, "baupreisindexBp"),
                        "useful_life_years": _required_int(facts, "gesamtnutzungsdauerJahre"),
                        "valuation_year": body.tax_year,
                        "year_built": year_built,
                        # R3b is a server-side approved convention, never a client input.
                        "minimum_residual_bp": 3_000,
                    }
                )
                building_basis = _required_int(allocation, "building_cost")
                land_basis = _required_int(allocation, "land_cost")
            elif route == "gutachten":
                share_bp = _required_int(facts, "gutachtenGebaeudeanteilBp")
                allocation = calculate(
                    {
                        "allocation_route": "contract",
                        "acquisition_cost_cents": acquisition_total,
                        "contract_building_share_bp": share_bp,
                        "year_built": year_built,
                    }
                )
                building_basis = _required_int(allocation, "building_cost")
                land_basis = _required_int(allocation, "land_cost")
                normalized_inputs[-1] = {
                    **normalized_inputs[-1],
                    "allocation_route": "gutachten",
                    "report_building_share_bp": share_bp,
                    "report_document_id": facts.get("gutachtenDokumentId"),
                }
            else:
                raise ValueError("allocation route is invalid")
        elif acquisition_type == "neubau":
            building_basis = _required_int(facts, "herstellungskostenCent")
            land_basis = _required_int(facts, "grundstueckskostenCent")
            acquisition_total = building_basis
            normalized_inputs.append(
                {
                    "acquisition_type": "neubau",
                    "building_basis_cents": building_basis,
                    "land_cost_cents": land_basis,
                    "outdoor_assets_cents": _optional_int(facts, "aussenanlagenCent"),
                }
            )
        elif acquisition_type == "unentgeltlich":
            predecessor = calculate(
                {
                    "acquisition_type": "unentgeltlich",
                    "predecessor_basis_cents": _required_int(facts, "bemessungsgrundlageCent"),
                    "rate_bp": _required_int(facts, "afaSatzBp"),
                    "predecessor_accumulated_afa_cents": _required_int(facts, "kumulierteAfaCent"),
                    "predecessor_months": _optional_int(facts, "vorgaengerMonate"),
                }
            )
            building_basis = _required_int(facts, "bemessungsgrundlageCent")
            land_basis = 0
            acquisition_total = building_basis
        else:
            raise ValueError("acquisition type is invalid")

        relevant_date_name = (
            "fertigstellungsdatum" if acquisition_type == "neubau" else "uebergangNutzenLastenDatum"
        )
        relevant_date = date.fromisoformat(str(facts[relevant_date_name]))
        if acquisition_type == "unentgeltlich":
            annual_afa_cents = _required_int(predecessor, "annual_afa")
            selected_afa_cents = annual_afa_cents
        else:
            annual_facts: dict[str, object] = {
                "building_basis_cents": building_basis,
                "year_built": year_built,
                "completion_date" if acquisition_type == "neubau" else "transfer_date": str(
                    facts[relevant_date_name]
                ),
            }
            report_years = facts.get("rndGutachtenJahre")
            qualification = facts.get("rndGutachtenQualifikation")
            if isinstance(report_years, int) and qualification in {"oebuv", "zertifiziert"}:
                report_values = calculate(
                    {
                        "building_basis_cents": building_basis,
                        "remaining_life_years": report_years,
                        "report_qualification": qualification,
                        "report_date": facts.get("rndGutachtenDatum"),
                    }
                )
                annual_afa_cents = _required_int(report_values, "annual_afa")
                selected_afa_cents = annual_afa_cents
            else:
                annual = calculate(annual_facts)
                annual_afa_cents = _required_int(annual, "annual_afa")
                selected_afa_cents = annual_afa_cents
                if body.tax_year == relevant_date.year:
                    selected_afa_cents = _required_int(annual, "first_year_afa")
                elif body.tax_year < relevant_date.year:
                    selected_afa_cents = 0
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise HTTPException(status_code=422, detail="Die AfA-Angaben sind ungültig.") from exc

    calculated_values = dict(acquisition)
    calculated_values.update(
        acquisition_total_cents=acquisition_total,
        building_basis_cents=building_basis,
        land_basis_cents=land_basis,
    )
    allowed_start_month = 1
    if body.tax_year == relevant_date.year:
        allowed_start_month = relevant_date.month
    elif body.tax_year < relevant_date.year:
        allowed_start_month = 13

    total_area = facts.get("wohnflaecheGesamt")
    if not isinstance(total_area, int) or total_area <= 0:
        raise ValueError("total living area is invalid")
    allowed_months = max(0, 13 - allowed_start_month)
    rented_area_months = total_area * allowed_months
    periods = facts.get("selfUsePeriods", [])
    if not isinstance(periods, list):
        raise ValueError("self-use periods are invalid")
    for period in periods:
        if not isinstance(period, dict):
            raise ValueError("self-use period is invalid")
        start = date.fromisoformat(str(period["vonDatum"]))
        end_value = period.get("bisDatum")
        end = date.fromisoformat(str(end_value)) if end_value else date.max
        area = period.get("selbstgenutzteFlaeche")
        if not isinstance(area, int) or not 0 <= area <= total_area:
            raise ValueError("self-use area is invalid")
        for month in range(allowed_start_month, 13):
            month_start = date(body.tax_year, month, 1)
            month_end = (
                date(body.tax_year + 1, 1, 1) if month == 12 else date(body.tax_year, month + 1, 1)
            )
            if start < month_end and end >= month_start:
                rented_area_months -= area
    if rented_area_months < 0:
        raise ValueError("self-use periods overlap or exceed the total area")
    total_area_months = total_area * allowed_months
    if selected_afa_cents == 0 or total_area_months == 0:
        deductible_afa_cents = 0
        non_deductible_afa_cents = 0
    else:
        use_values = calculate(
            {
                "annual_afa_cents": selected_afa_cents,
                "rented_area_months_x100": rented_area_months,
                "total_area_months_x100": total_area_months,
                "started_rental_month_counts_fully": True,
            }
        )
        deductible_afa_cents = _required_int(use_values, "deductible_afa")
        non_deductible_afa_cents = _required_int(use_values, "non_deductible_afa")

    measures = facts.get("massnahmen", facts.get("maßnahmen"))
    if isinstance(measures, list) and measures:
        normalized_measures = [
            {
                "net_cents": _required_int(cast(dict[str, object], item), "nettoCent"),
                "leistung_bis": cast(dict[str, object], item).get("leistungBis"),
                "class": cast(dict[str, object], item).get("klasse"),
                "document_id": cast(dict[str, object], item).get("belegId"),
            }
            for item in measures
            if isinstance(item, dict)
        ]
        measure_values = calculate(
            {
                "measures": normalized_measures,
                "previous_counted_cents": _optional_int(facts, "bisherAngerechnetCent"),
                "transfer_date": str(facts.get("uebergangNutzenLastenDatum")),
                "building_basis_cents": building_basis,
            }
        )
        calculated_values["later_costs"] = measure_values

    loans = facts.get("darlehen")
    if isinstance(loans, list):
        loan_results: list[dict[str, object]] = []
        disagio_results: list[dict[str, object]] = []
        for item in loans:
            if not isinstance(item, dict):
                raise HTTPException(status_code=422, detail="Die Darlehensangaben sind ungültig.")
            loan_facts: dict[str, object] = {
                "nominal_cents": _required_int(item, "nominalbetragCent"),
                "interest_bp": _required_int(item, "sollzinsBpProJahr"),
                "initial_repayment_bp": _required_int(item, "anfaenglicheTilgungBp"),
                "installment_count": _optional_int(item, "ratenAnzahl", 12),
                "assignment": item.get("zuordnung"),
                "first_installment_date": item.get("ersteRateDatum"),
            }
            special = item.get("sondertilgung")
            if isinstance(special, list) and special and isinstance(special[0], dict):
                loan_facts.update(
                    special_repayment_cents=_required_int(special[0], "betragCent"),
                    special_repayment_before_installment=_required_int(special[0], "vorRate"),
                )
            loan_results.append(calculate(loan_facts))
            market_disagio = item.get("marktueblichesDisagioCent")
            non_market_disagio = item.get("nichtMarktueblichesDisagioCent")
            if isinstance(market_disagio, int) and isinstance(non_market_disagio, int):
                disagio_results.append(
                    calculate(
                        {
                            "nominal_cents": _required_int(item, "nominalbetragCent"),
                            "market_disagio_cents": market_disagio,
                            "non_market_disagio_cents": non_market_disagio,
                            "fixed_interest_years": _required_int(item, "zinsbindungJahre"),
                            "first_year_months": _optional_int(item, "disagioErstjahrMonate", 12),
                        }
                    )
                )
        calculated_values["loans"] = loan_results
        if disagio_results:
            calculated_values["disagio"] = disagio_results
    calculated_values["annual_afa_cents"] = selected_afa_cents
    calculated_values["tax_year_afa_cents"] = selected_afa_cents
    calculated_values["deductible_afa_cents"] = deductible_afa_cents
    calculated_values["non_deductible_afa_cents"] = non_deductible_afa_cents
    snapshot: dict[str, object] = {
        "calculated_values": calculated_values,
        "findings": findings,
        "source_evidence": list(resolved.source_evidence),
        "normalized_inputs": normalized_inputs,
        "page04_handoffs": page04_handoffs,
    }
    return snapshot, resolved.rechtsstand, resolved.production_blocked


@router.post("/afa/preview", response_model=AfaResponse)
def preview_afa(account_id: str, body: AfaRequest, session: TaxAccountSession) -> AfaResponse:
    del account_id
    _authorize(session, "read")
    result, rechtsstand, blocked = _afa_result(body)
    return AfaResponse(
        building_id=body.building_id,
        tax_year=body.tax_year,
        result=result,
        annual_afa_cents=_annual_afa_from_snapshot(result),
        tax_year_afa_cents=_afa_amounts_from_snapshot(result)[0],
        deductible_afa_cents=_afa_amounts_from_snapshot(result)[1],
        non_deductible_afa_cents=_afa_amounts_from_snapshot(result)[2],
        rechtsstand=rechtsstand,
        production_blocked=blocked,
        generated_at=body.generated_at,
    )


@router.post("/afa", response_model=AfaResponse, status_code=201)
def create_afa(account_id: str, body: AfaRequest, session: TaxAccountSession) -> AfaResponse:
    _authorize(session, "afa_write")
    result, rechtsstand, blocked = _afa_result(body)
    resolved_rules = resolve_afa_rule_bundle(body.tax_year)
    previous = session.scalar(
        select(AfaRecordVersion)
        .where(
            AfaRecordVersion.building_id == body.building_id,
            AfaRecordVersion.tax_year == body.tax_year,
        )
        .order_by(AfaRecordVersion.version.desc())
    )
    row = AfaRecordVersion(
        id=new_id(),
        account_id=account_id,
        building_id=body.building_id,
        tax_year=body.tax_year,
        version=previous.version + 1 if previous else 1,
        input_snapshot={"facts": body.facts},
        result_snapshot=result,
        rule_snapshot={
            "linear_rates_bp": [list(row) for row in resolved_rules.linear_rates_bp],
            "guard_rate_bp": resolved_rules.guard_rate_bp,
            "market_disagio_limit_bp": resolved_rules.market_disagio_limit_bp,
            "source_evidence": list(resolved_rules.source_evidence),
            "rechtsstand": resolved_rules.rechtsstand,
            "production_blocked": resolved_rules.production_blocked,
        },
        rechtsstand=rechtsstand,
        production_blocked=blocked,
        supersedes_afa_record_version_id=previous.id if previous else None,
        generated_at=body.generated_at,
    )
    session.add(row)
    session.flush()
    return _afa_out(row)


def _afa_out(row: AfaRecordVersion) -> AfaResponse:
    return AfaResponse(
        id=row.id,
        version=row.version,
        building_id=row.building_id,
        tax_year=row.tax_year,
        result=row.result_snapshot,
        annual_afa_cents=_annual_afa_from_snapshot(row.result_snapshot),
        tax_year_afa_cents=_afa_amounts_from_snapshot(row.result_snapshot)[0],
        deductible_afa_cents=_afa_amounts_from_snapshot(row.result_snapshot)[1],
        non_deductible_afa_cents=_afa_amounts_from_snapshot(row.result_snapshot)[2],
        rechtsstand=row.rechtsstand,
        production_blocked=row.production_blocked,
        generated_at=row.generated_at,
    )


def _annual_afa_from_snapshot(snapshot: dict[str, object]) -> int:
    calculated = snapshot.get("calculated_values")
    if not isinstance(calculated, dict):
        raise ValueError("AfA snapshot has no calculated annual AfA")
    value = calculated.get("annual_afa_cents")
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("AfA snapshot has no true annual AfA")
    return value


def _afa_amounts_from_snapshot(snapshot: dict[str, object]) -> tuple[int, int, int]:
    calculated = snapshot.get("calculated_values")
    if not isinstance(calculated, dict):
        raise ValueError("AfA snapshot has no calculated tax-year amounts")
    values = tuple(
        calculated.get(name)
        for name in (
            "tax_year_afa_cents",
            "deductible_afa_cents",
            "non_deductible_afa_cents",
        )
    )
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in values):
        raise ValueError("AfA snapshot has incomplete tax-year amounts")
    return cast(tuple[int, int, int], values)


@router.get("/afa/history", response_model=AfaHistoryResponse)
def afa_history(account_id: str, session: TaxAccountSession) -> AfaHistoryResponse:
    del account_id
    _authorize(session, "read")
    rows = session.scalars(
        select(AfaRecordVersion).order_by(
            AfaRecordVersion.tax_year.desc(), AfaRecordVersion.version.desc()
        )
    ).all()
    return AfaHistoryResponse(records=[_afa_out(row) for row in rows])


def _event_out(row: TaxEvent) -> TaxEventResponse:
    return TaxEventResponse(
        id=row.id,
        building_id=row.building_id,
        unit_id=row.unit_id,
        payment_date=row.payment_date,
        due_date=row.due_date,
        category=row.category,
        amount_cents=row.amount_cents,
        direction=row.direction,
        receipt_reference=row.receipt_reference,
        source=row.source,
        version=row.version,
        supersedes_tax_event_id=row.supersedes_tax_event_id,
        recorded_at=row.recorded_at,
    )


@router.get("/events", response_model=TaxEventListResponse)
def list_events(account_id: str, session: TaxAccountSession) -> TaxEventListResponse:
    del account_id
    _authorize(session, "read")
    rows = session.scalars(
        select(TaxEvent).order_by(TaxEvent.recorded_at.desc(), TaxEvent.id)
    ).all()
    return TaxEventListResponse(events=[_event_out(row) for row in rows])


def _new_event(
    account_id: str,
    body: TaxEventCreate,
    *,
    supersedes_id: str | None,
    source_component: str,
    source: dict[str, object],
) -> TaxEvent:
    return TaxEvent(
        id=new_id(),
        account_id=account_id,
        building_id=body.building_id,
        unit_id=body.unit_id,
        payment_date=body.payment_date,
        due_date=body.due_date,
        category=body.category,
        amount_cents=body.amount_cents,
        direction=body.direction,
        receipt_reference=body.receipt_reference,
        source=body.source,
        version=body.version,
        source_payment_allocation_id=body.source_payment_allocation_id,
        source_component=source_component,
        supersedes_tax_event_id=supersedes_id,
        source_snapshot=source,
        recorded_at=body.recorded_at,
    )


@router.post("/events", response_model=TaxEventResponse, status_code=201)
def create_event(
    account_id: str, body: TaxEventCreate, session: TaxAccountSession
) -> TaxEventResponse:
    _authorize(session, "event_write")
    row = _new_event(
        account_id,
        body,
        supersedes_id=None,
        source_component="manual",
        source=body.source_context,
    )
    session.add(row)
    session.flush()
    return _event_out(row)


@router.post("/events/{event_id}/corrections", response_model=TaxEventResponse, status_code=201)
def correct_event(
    account_id: str,
    event_id: str,
    body: TaxEventCorrectionCreate,
    session: TaxAccountSession,
) -> TaxEventResponse:
    _authorize(session, "event_write")
    previous = session.get(TaxEvent, event_id)
    if previous is None:
        raise HTTPException(status_code=404, detail="Steuerereignis nicht gefunden.")
    source_snapshot = dict(body.source)
    source_snapshot["correction_reason"] = body.correction_reason
    # Building, allocation, component and receipt identify the stream the corrected row
    # belongs to. They are read from the superseded row, never from the correction payload.
    row = TaxEvent(
        id=new_id(),
        account_id=account_id,
        building_id=getattr(previous, "building_id", None) or body.building_id,
        unit_id=getattr(previous, "unit_id", None) or body.unit_id,
        payment_date=body.payment_date,
        due_date=body.due_date,
        category=body.category,
        amount_cents=body.amount_cents,
        direction=body.direction,
        receipt_reference=(
            getattr(previous, "receipt_reference", None) or body.receipt_reference or previous.id
        ),
        source=getattr(previous, "source", None) or TaxEventSource.MANUELL.value,
        version=int(getattr(previous, "version", 0) or 0) + 1,
        source_payment_allocation_id=getattr(previous, "source_payment_allocation_id", None),
        source_component=getattr(previous, "source_component", None) or "manual",
        supersedes_tax_event_id=previous.id,
        source_snapshot=source_snapshot,
        recorded_at=body.recorded_at,
    )
    session.add(row)
    session.flush()
    return _event_out(row)


def materialize_payment_allocation_components(
    *,
    account_id: str,
    building_id: str,
    unit_id: str | None = None,
    allocation: PaymentAllocationComponents,
    payment_date: date,
    recorded_at: datetime,
    source_context: dict[str, object],
    session: Session,
) -> list[TaxEvent]:
    """Copy accepted M6 allocation components without inferring tax categories."""
    allocation_id = allocation.id
    source_value = source_context.get("source", TaxEventSource.FINAPI.value)
    if source_value not in {item.value for item in TaxEventSource}:
        raise ValueError("tax event source is invalid")
    receipt_base = source_context.get("receipt_reference") or source_context.get(
        "bank_transaction_id"
    )
    if not isinstance(receipt_base, str) or not receipt_base:
        receipt_base = allocation_id
    named_rent_components = any(
        amount != 0
        for amount in (
            allocation.base_rent_cents,
            allocation.nk_advance_cents,
            allocation.heating_advance_cents,
            allocation.garage_cents,
        )
    )
    specifications: tuple[tuple[str, int, str | None], ...] = (
        ("costs", allocation.costs_cents, None),
        ("interest", allocation.interest_cents, None),
        ("base_rent", allocation.base_rent_cents, "kaltmiete"),
        ("nk_advance", allocation.nk_advance_cents, "nk_vorauszahlung"),
        ("heating_advance", allocation.heating_advance_cents, "nk_vorauszahlung"),
        ("garage", allocation.garage_cents, None),
        ("principal", allocation.principal_cents, None),
    )
    nonzero_signs = {amount > 0 for _, amount, _ in specifications if amount != 0}
    if len(nonzero_signs) > 1:
        raise ValueError("payment allocation components must have one consistent sign")
    reversal = source_context.get("ledger_kind") == "REVERSAL" or nonzero_signs == {False}
    direction = "ausgabe" if reversal else "einnahme"
    rows: list[TaxEvent] = []
    for source_component, amount_cents, category in specifications:
        if amount_cents == 0 or (source_component == "principal" and named_rent_components):
            continue
        existing = session.scalar(
            select(TaxEvent.id).where(
                TaxEvent.source_payment_allocation_id == allocation_id,
                TaxEvent.source_component == source_component,
            )
        )
        if existing is not None:
            continue
        source_snapshot = dict(source_context)
        source_snapshot["source_component"] = source_component
        row = TaxEvent(
            id=new_id(),
            account_id=account_id,
            building_id=building_id,
            unit_id=unit_id,
            payment_date=payment_date,
            due_date=None,
            category=category,
            amount_cents=abs(amount_cents),
            direction=direction,
            receipt_reference=f"{receipt_base}:{source_component}",
            source=str(source_value),
            version=1,
            source_payment_allocation_id=allocation_id,
            source_component=source_component,
            supersedes_tax_event_id=None,
            source_snapshot=source_snapshot,
            recorded_at=recorded_at,
        )
        session.add(row)
        rows.append(row)
    session.flush()
    return rows


def _profile_out(row: TaxAdviserProfileVersion) -> AdviserProfileResponse:
    return AdviserProfileResponse(
        id=row.id,
        version=row.version,
        profile=AdviserProfile.model_validate(row.profile_snapshot),
        production_blocked=row.production_blocked,
        generated_at=row.generated_at,
    )


@router.get("/adviser-profile", response_model=AdviserProfileResponse)
def get_adviser_profile(account_id: str, session: TaxAccountSession) -> AdviserProfileResponse:
    del account_id
    _authorize(session, "read")
    row = session.scalar(
        select(TaxAdviserProfileVersion).order_by(TaxAdviserProfileVersion.version.desc())
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Noch kein Steuerberaterprofil vorhanden.")
    return _profile_out(row)


@router.post("/adviser-profile", response_model=AdviserProfileResponse, status_code=201)
def create_adviser_profile(
    account_id: str, body: AdviserProfileCreate, session: TaxAccountSession
) -> AdviserProfileResponse:
    _authorize(session, "profile_write")
    previous = session.scalar(
        select(TaxAdviserProfileVersion).order_by(TaxAdviserProfileVersion.version.desc())
    )
    row = TaxAdviserProfileVersion(
        id=new_id(),
        account_id=account_id,
        version=previous.version + 1 if previous else 1,
        profile_snapshot=body.profile.model_dump(mode="json"),
        production_blocked=True,
        supersedes_profile_version_id=previous.id if previous else None,
        generated_at=body.generated_at,
    )
    session.add(row)
    session.flush()
    return _profile_out(row)


def _mapping_out(row: TaxMappingVersion) -> TaxMappingResponse:
    return TaxMappingResponse(
        id=row.id,
        tax_year=row.tax_year,
        version=row.version,
        mapping=[
            TaxMappingEntry.model_validate(entry)
            for entry in cast(list[dict[str, object]], row.mapping_snapshot)
        ],
        source_version=row.source_version,
        rechtsstand=row.rechtsstand,
        production_blocked=row.production_blocked,
        generated_at=row.generated_at,
    )


@router.get("/mappings/{tax_year}", response_model=TaxMappingResponse)
def get_mapping(account_id: str, tax_year: int, session: TaxAccountSession) -> TaxMappingResponse:
    del account_id
    _authorize(session, "read")
    row = session.scalar(
        select(TaxMappingVersion)
        .where(TaxMappingVersion.tax_year == tax_year)
        .order_by(TaxMappingVersion.version.desc())
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Für dieses Steuerjahr fehlt eine Zuordnung.")
    return _mapping_out(row)


@router.post("/mappings/{tax_year}", response_model=TaxMappingResponse, status_code=201)
def create_mapping(
    account_id: str, tax_year: int, body: TaxMappingCreate, session: TaxAccountSession
) -> TaxMappingResponse:
    _authorize(session, "mapping_write")
    if body.tax_year is not None and body.tax_year != tax_year:
        raise HTTPException(
            status_code=422,
            detail="Das Steuerjahr im Inhalt muss dem Steuerjahr im Pfad entsprechen.",
        )
    if any(entry.tax_year != tax_year for entry in body.mapping):
        raise HTTPException(
            status_code=422,
            detail="Alle Zuordnungen müssen dem Steuerjahr im Pfad entsprechen.",
        )
    previous = session.scalar(
        select(TaxMappingVersion)
        .where(TaxMappingVersion.tax_year == tax_year)
        .order_by(TaxMappingVersion.version.desc())
    )
    row = TaxMappingVersion(
        id=new_id(),
        account_id=account_id,
        tax_year=tax_year,
        version=previous.version + 1 if previous else 1,
        mapping_snapshot=[entry.model_dump(mode="json") for entry in body.mapping],
        source_version=body.source_version,
        rechtsstand=body.rechtsstand,
        production_blocked=True,
        supersedes_mapping_version_id=previous.id if previous else None,
        generated_at=body.generated_at,
    )
    session.add(row)
    session.flush()
    return _mapping_out(row)


def _readiness_attempt(account_id: str, body: ReadinessRequest) -> TaxExportReadinessAttempt:
    findings: list[object] = [
        {
            "severity": "rot",
            "code": "authority_unverified",
            "message": "Anlage-V- und DATEV-Autorität ist vor Produktion zu prüfen.",
        }
    ]
    return TaxExportReadinessAttempt(
        id=new_id(),
        account_id=account_id,
        building_id=body.building_id,
        afa_record_version_id=getattr(body, "afa_record_version_id", None),
        adviser_profile_version_id=getattr(body, "adviser_profile_version_id", None),
        mapping_version_id=getattr(body, "mapping_version_id", ""),
        tax_year=body.tax_year,
        export_kind={"DATEV": "datev_extf"}.get(body.export_kind, body.export_kind),
        input_snapshot=(
            body.model_dump(mode="json")
            if isinstance(body, BaseModel)
            else {
                "building_id": body.building_id,
                "tax_year": body.tax_year,
                "export_kind": body.export_kind,
            }
        ),
        findings_snapshot=findings,
        production_blocked=True,
        generated_at=body.generated_at,
    )


def _readiness_out(row: TaxExportReadinessAttempt) -> ReadinessResponse:
    result_snapshot = row.input_snapshot.get("readiness_result", {})
    rechtsstand = (
        str(result_snapshot.get("rechtsstand", "07/2026"))
        if isinstance(result_snapshot, dict)
        else "07/2026"
    )
    return ReadinessResponse(
        id=row.id,
        findings=cast(list[dict[str, object]], row.findings_snapshot),
        rechtsstand=rechtsstand,
        production_blocked=row.production_blocked,
        generated_at=row.generated_at,
    )


def _build_validated_readiness_attempt(
    account_id: str, body: ReadinessRequest, session: Session
) -> TaxExportReadinessAttempt:
    afa = (
        session.get(AfaRecordVersion, body.afa_record_version_id)
        if body.afa_record_version_id
        else None
    )
    if body.afa_record_version_id and (
        afa is None or afa.building_id != body.building_id or afa.tax_year != body.tax_year
    ):
        raise HTTPException(status_code=422, detail="Der AfA-Datensatz passt nicht zur Auswahl.")
    profile = (
        session.get(TaxAdviserProfileVersion, body.adviser_profile_version_id)
        if body.adviser_profile_version_id
        else None
    )
    if body.adviser_profile_version_id and profile is None:
        raise HTTPException(status_code=422, detail="Das Steuerberaterprofil wurde nicht gefunden.")
    mapping = session.get(TaxMappingVersion, body.mapping_version_id)
    if mapping is None or mapping.tax_year != body.tax_year:
        raise HTTPException(status_code=422, detail="Die Zuordnung passt nicht zum Steuerjahr.")

    events = session.scalars(
        select(TaxEvent)
        .where(TaxEvent.building_id == body.building_id)
        .order_by(TaxEvent.recorded_at, TaxEvent.id)
    ).all()
    superseded_ids = {
        supersedes_id
        for event in events
        if (supersedes_id := getattr(event, "supersedes_tax_event_id", None)) is not None
    }
    ledger_events: list[dict[str, object]] = []
    for event in events:
        if event.id in superseded_ids:
            continue
        # The readiness engine never sees tenant identity: it gets the cash-basis facts
        # plus the stored provenance snapshot, and nothing that names an account or a unit.
        normalized: dict[str, object] = {
            "event_id": event.id,
            "payment_date": event.payment_date,
            "due_date": event.due_date,
            "category": event.category,
            "amount_cents": event.amount_cents,
            "direction": event.direction,
            "source": dict(event.source_snapshot),
        }
        if event.payment_date is None:
            ledger_events.append(normalized)
            continue
        assignment_input = dict(normalized)
        assignment_input["recurring"] = bool(event.source_snapshot.get("recurring", False))
        if assign_tax_year(assignment_input) == body.tax_year:
            ledger_events.append(normalized)
    mapping_snapshot = cast(list[dict[str, object]], mapping.mapping_snapshot)
    result = evaluate_export_readiness(
        ledger_events=ledger_events,
        afa_record=afa.result_snapshot if afa is not None else None,
        adviser_profile=profile.profile_snapshot if profile is not None else None,
        mapping=mapping_snapshot,
        export_kind=body.export_kind,
        tax_year=body.tax_year,
        generated_at=body.generated_at,
        register_rows=(
            ("tax.export", "", "verify-before-production", "", "", "", "", "", "07/2026"),
        ),
        extf_profile={"production_blocked": True},
    )
    findings = [
        {
            "severity": finding.severity,
            "code": finding.code,
            "finding_id": finding.finding_id,
        }
        for finding in result.findings
    ]
    blockers: list[str] = []
    for finding in result.findings:
        message = getattr(finding, "message", None)
        if finding.severity == "rot" and isinstance(message, str) and message:
            blockers.append(message)
    if result.production_blocked and not blockers:
        blockers = ["Der Export ist gesperrt, weil erforderliche Prüfungen noch offen sind."]
    input_snapshot = body.model_dump(mode="json")
    input_snapshot["blockers"] = blockers
    input_snapshot["readiness_result"] = {
        "findings": findings,
        "rechtsstand": result.rechtsstand,
        "production_blocked": True,
        "generated_at": body.generated_at.isoformat(),
    }
    return TaxExportReadinessAttempt(
        id=new_id(),
        account_id=account_id,
        building_id=body.building_id,
        afa_record_version_id=body.afa_record_version_id,
        adviser_profile_version_id=body.adviser_profile_version_id,
        mapping_version_id=body.mapping_version_id,
        tax_year=body.tax_year,
        export_kind=body.export_kind,
        input_snapshot=input_snapshot,
        findings_snapshot=findings,
        production_blocked=True,
        generated_at=body.generated_at,
    )


@router.post("/readiness", response_model=ReadinessResponse, status_code=201)
def evaluate_readiness(
    account_id: str, body: ReadinessRequest, session: TaxAccountSession
) -> ReadinessResponse:
    _authorize(session, "generate")
    row = _build_validated_readiness_attempt(account_id, body, session)
    session.add(row)
    session.flush()
    return _readiness_out(row)


@router.post("/exports", response_model=ExportResponse, status_code=201)
def generate_export(
    account_id: str,
    body: GenerateExportRequest,
    session: TaxAccountSession,
) -> Response:
    # Authorization precedes construction, so the "every failed attempt is durable"
    # contract is unaffected. This was the one authorization site in the file whose
    # failure mode was "allow": a missing `tax_role` skipped the check and still wrote
    # an append-only readiness attempt that nothing can remove.
    _authorize(session, "generate")
    readiness = (
        _build_validated_readiness_attempt(account_id, body, session)
        if isinstance(body, BaseModel)
        else _readiness_attempt(account_id, body)
    )
    session.add(readiness)
    session.flush()
    return JSONResponse(
        status_code=422,
        content={"detail": "Export gesperrt: Die Quellen müssen zuerst geprüft werden."},
    )


_VERIFIED_TEST_BUNDLE_ID = "m7-server-generated-v1"

# `source_snapshot` is caller-written JSON: `create_event` stores `source_context` and
# `correct_event` stores `source` verbatim, and neither is key-restricted. Splatting it
# over the projection let a stored blob override `amount_cents`, `direction`, `category`
# or `payment_date` — so the archived bytes and their hash would no longer re-derive from
# the append-only columns, which is the whole GoBD claim. Only these engine signals may
# be read from it, and the columns are written last so nothing can shadow them.
# `booking_text` is deliberately absent: docs/11 § 8 requires it to default to the unit,
# never to caller-supplied text that could carry a renter name.
_LEDGER_SIGNAL_KEYS = frozenset(
    {
        "cold_rent_due_cents",
        "nk_advance_due_cents",
        "party_matched",
        "recurring",
        "expected_amount_cents",
        "vat_case",
    }
)


def _ledger_signals(snapshot: object) -> dict[str, object]:
    if not isinstance(snapshot, dict):
        return {}
    return {key: value for key, value in snapshot.items() if key in _LEDGER_SIGNAL_KEYS}


def resolve_verified_export_rule_bundle(
    tax_year: int, generated_at: datetime
) -> tuple[ResolvedRule[AnlageVLayout], ResolvedRule[ExtfProfile]]:
    """Resolve the Anlage-V layout and the test-only EXTF profile for one generation."""

    layout = get_rule(ANLAGE_V_LAYOUTS, date(tax_year, 12, 31))
    extf = get_rule(VERIFIED_TEST_EXTF_PROFILES, generated_at.date())
    if extf.value.production_blocked or extf.value.verification_flag != "verified-test-only":
        raise ValueError("verified-test EXTF rules are unresolved")
    return layout, extf


def _rechtsstand_evidence(primary: object, stored: object) -> str:
    for value in (primary, stored):
        if isinstance(value, str) and value:
            return value
    raise ValueError("verified archive requires AfA and export Rechtsstand evidence")


def archive_verified_test_artifacts(
    account_id: str,
    readiness_attempt_id: str,
    bundle: VerifiedTestBundle,
    generated_at: datetime,
    session: Session,
) -> ExportResponse:
    """Freeze exactly the bytes the server generated, against loaded readiness evidence."""

    readiness = session.get(TaxExportReadinessAttempt, readiness_attempt_id)
    if readiness is None or readiness.account_id != account_id:
        raise ValueError("verified archive requires referenced readiness evidence")
    if not bundle.artifacts:
        raise ValueError("a verified archive needs at least one server-generated artifact")
    snapshot = readiness.input_snapshot if isinstance(readiness.input_snapshot, dict) else {}
    # ``findings`` is the domain name a readiness result carries; ``findings_snapshot`` is
    # the column it is frozen into. Neither is defaulted: missing evidence is a refusal.
    findings_value = getattr(readiness, "findings", None)
    if findings_value is None:
        findings_value = getattr(readiness, "findings_snapshot", None)
    if not isinstance(findings_value, list) or not all(
        isinstance(item, dict) for item in findings_value
    ):
        raise ValueError("readiness findings evidence is invalid")
    blockers_value = snapshot.get("blockers")
    if not isinstance(blockers_value, list) or not all(
        isinstance(item, str) for item in blockers_value
    ):
        raise ValueError("readiness blocker evidence is missing or invalid")
    afa_row = (
        session.get(AfaRecordVersion, afa_id)
        if (afa_id := getattr(readiness, "afa_record_version_id", None))
        else None
    )
    mapping_row = (
        session.get(TaxMappingVersion, mapping_id)
        if (mapping_id := getattr(readiness, "mapping_version_id", None))
        else None
    )
    afa_rechtsstand = _rechtsstand_evidence(
        snapshot.get("afa_rechtsstand"), getattr(afa_row, "rechtsstand", None)
    )
    export_rechtsstand = _rechtsstand_evidence(
        getattr(readiness, "rechtsstand", None), getattr(mapping_row, "rechtsstand", None)
    )
    building_id = str(getattr(readiness, "building_id", "") or "")
    tax_year = int(getattr(readiness, "tax_year", 0) or 0)
    export_kind = str(getattr(readiness, "export_kind", "") or bundle.artifacts[0].artifact_kind)
    blocked = bool(blockers_value) or bool(getattr(readiness, "production_blocked", False))
    # One archive stream is one logical export: account, building, tax year and kind. A
    # second attempt for the same stream supersedes the first, whichever readiness ran it.
    previous = session.scalar(
        select(TaxExportArchive)
        .where(
            TaxExportArchive.account_id == account_id,
            TaxExportArchive.building_id == building_id,
            TaxExportArchive.tax_year == tax_year,
            TaxExportArchive.export_kind == export_kind,
        )
        .order_by(TaxExportArchive.version.desc())
    )
    superseded = previous if isinstance(previous, TaxExportArchive) else None
    archive = TaxExportArchive(
        id=new_id(),
        account_id=account_id,
        readiness_attempt_id=readiness_attempt_id,
        building_id=building_id,
        tax_year=tax_year,
        export_kind=export_kind,
        version=superseded.version + 1 if superseded is not None else 1,
        input_snapshot={
            "verified_test_bundle_id": bundle.bundle_id,
            "readiness_findings": findings_value,
            "blockers": blockers_value,
            "afa_rechtsstand": afa_rechtsstand,
            "export_rechtsstand": export_rechtsstand,
        },
        production_blocked=blocked,
        sha256=sha256(b"".join(item.content_bytes for item in bundle.artifacts)).hexdigest(),
        supersedes_archive_id=superseded.id if superseded is not None else None,
        generated_at=generated_at,
    )
    session.add(archive)
    artifacts = [
        TaxExportArtifact(
            id=new_id(),
            account_id=account_id,
            archive_id=archive.id,
            artifact_kind=item.artifact_kind,
            content_bytes=item.content_bytes,
            sha256=sha256(item.content_bytes).hexdigest(),
            mime_type=item.mime_type,
            filename=item.filename,
            production_blocked=blocked,
            generated_at=generated_at,
        )
        for item in bundle.artifacts
    ]
    for row in artifacts:
        session.add(row)
    session.flush()
    return _export_out(archive, artifacts)


def generate_verified_test_export(
    account_id: str,
    readiness_attempt_id: str,
    generated_at: datetime,
    session: Session,
) -> ExportResponse:
    """Generate and archive server-owned verified-test artifacts; never a public route."""

    readiness = session.get(TaxExportReadinessAttempt, readiness_attempt_id)
    if readiness is None or readiness.account_id != account_id:
        raise ValueError("verified generation requires referenced readiness evidence")
    blockers = readiness.input_snapshot.get("blockers")
    if readiness.production_blocked or blockers:
        raise ValueError("blocked runtime readiness cannot generate verified artifacts")
    afa = session.get(AfaRecordVersion, readiness.afa_record_version_id)
    mapping = session.get(TaxMappingVersion, readiness.mapping_version_id)
    profile = (
        session.get(TaxAdviserProfileVersion, readiness.adviser_profile_version_id)
        if readiness.adviser_profile_version_id
        else None
    )
    if afa is None or mapping is None:
        raise ValueError("verified test generation requires stored AfA and mapping evidence")
    if afa.production_blocked or mapping.production_blocked:
        raise ValueError("runtime or unresolved rule bundles cannot generate verified artifacts")
    layout, resolved_extf = resolve_verified_export_rule_bundle(readiness.tax_year, generated_at)
    events = session.scalars(
        select(TaxEvent)
        .where(TaxEvent.building_id == readiness.building_id)
        .order_by(TaxEvent.payment_date, TaxEvent.id, TaxEvent.version)
    ).all()
    superseded = {
        row.supersedes_tax_event_id for row in events if row.supersedes_tax_event_id is not None
    }
    ledger_events = [
        {
            **_ledger_signals(row.source_snapshot),
            "event_id": row.id,
            "account_id": row.account_id,
            "building_id": row.building_id,
            "unit_id": row.unit_id,
            "payment_date": row.payment_date,
            "due_date": row.due_date,
            "amount_cents": row.amount_cents,
            "direction": row.direction,
            "category": row.category,
            "receipt_reference": row.receipt_reference,
            "source": row.source,
            "version": row.version,
        }
        for row in events
        if row.id not in superseded
    ]
    calculated = afa.result_snapshot.get("calculated_values", {})
    if not isinstance(calculated, dict):
        raise ValueError("verified AfA snapshot is invalid")
    mapping_rows = cast(list[dict[str, object]], mapping.mapping_snapshot)
    account_chart = (
        str(profile.profile_snapshot.get("kontenrahmen", "skr03"))
        if profile is not None
        else "skr03"
    )
    overview = build_anlage_v_overview(
        ledger_events=ledger_events,
        afa_handoff={
            "afaAbziehbarCent": calculated.get("deductible_afa_cents", 0),
            "zinsAbziehbarCent": calculated.get("deductible_interest_cents", 0),
            "zinsBestaetigt": calculated.get("interest_confirmed", False),
        },
        mapping=mapping_rows,
        account_chart=account_chart,
        tax_year=readiness.tax_year,
        generated_at=generated_at,
        register_rows=(
            (
                "tax.export.verified-test",
                "",
                "verified-test-only",
                "",
                "",
                layout.source,
                resolved_extf.source,
                "",
                mapping.rechtsstand,
            ),
        ),
    )
    if readiness.export_kind == "anlage_v_csv":
        artifact = VerifiedTestArtifact(
            artifact_kind="anlage_v_csv",
            filename=f"anlage-v-{readiness.tax_year}.csv",
            mime_type="text/csv; charset=windows-1252",
            content_bytes=encode_anlage_v_csv(
                overview=overview,
                layout={"tax_year": readiness.tax_year},
                generated_at=generated_at,
            ),
        )
    elif readiness.export_kind == "datev_extf":
        if profile is None:
            raise ValueError("verified DATEV generation requires an adviser profile")
        artifact = VerifiedTestArtifact(
            artifact_kind="datev_extf",
            filename=f"EXTF_TEST_{readiness.tax_year}.csv",
            mime_type="text/csv; charset=windows-1252",
            content_bytes=encode_datev_extf(
                ledger_events=ledger_events,
                overview=overview,
                mapping=mapping_rows,
                adviser_profile=profile.profile_snapshot,
                extf_profile=asdict(resolved_extf.value),
                generated_at=generated_at,
            ),
        )
    elif readiness.export_kind == "anlage_v_pdf":
        building = session.get(Building, readiness.building_id)
        building_label = (
            f"{building.street}, {building.postal_code} {building.city}"
            if building is not None
            else "Testobjekt"
        )
        cold_rent = sum(parts.get("kaltmiete", 0) for parts in overview.event_components.values())
        advances = sum(
            parts.get("nk_vorauszahlung", 0) for parts in overview.event_components.values()
        )
        payment_count = sum(1 for row in ledger_events if row.get("direction") == "einnahme")
        cost_count = sum(1 for row in ledger_events if row.get("direction") == "ausgabe")
        document = AnlageVOverviewData(
            title_de="Anlage-V-Übersicht",
            building_label=building_label,
            tax_year=readiness.tax_year,
            generated_at=generated_at,
            lines=(
                AnlageVOverviewLine(
                    "Kaltmiete",
                    cold_rent,
                    (AnlageVSourceRef("payment_events", payment_count, readiness.tax_year),),
                ),
                AnlageVOverviewLine(
                    "Nebenkostenvorauszahlungen",
                    advances,
                    (AnlageVSourceRef("payment_events", payment_count, readiness.tax_year),),
                ),
                AnlageVOverviewLine(
                    "Werbungskosten",
                    overview.advertising_cost_total_cents,
                    (
                        AnlageVSourceRef("cost_events", cost_count, readiness.tax_year),
                        AnlageVSourceRef("afa_record", 1, readiness.tax_year),
                    ),
                ),
                AnlageVOverviewLine(
                    "Ergebnis",
                    overview.result_cents,
                    (AnlageVSourceRef("tax_calculation", 1, readiness.tax_year),),
                ),
            ),
            blockers_de=(),
            rechtsstand=f"AfA {afa.rechtsstand} · Export {mapping.rechtsstand}",
            production_blocked=False,
            disclaimer=TAX_DISCLAIMER,
            verified_test_bundle_id=_VERIFIED_TEST_BUNDLE_ID,
        )
        artifact = VerifiedTestArtifact(
            artifact_kind="anlage_v_pdf",
            filename=f"anlage-v-{readiness.tax_year}.pdf",
            mime_type="application/pdf",
            content_bytes=render_html_to_pdf(anlage_v_overview_html(document)),
        )
    else:
        raise ValueError("unsupported verified export kind")
    return archive_verified_test_artifacts(
        account_id,
        readiness_attempt_id,
        VerifiedTestBundle(bundle_id=_VERIFIED_TEST_BUNDLE_ID, artifacts=[artifact]),
        generated_at,
        session,
    )


def _export_out(archive: TaxExportArchive, artifacts: list[TaxExportArtifact]) -> ExportResponse:
    snapshot = archive.input_snapshot if isinstance(archive.input_snapshot, dict) else {}
    required_evidence = (
        "readiness_findings",
        "blockers",
        "afa_rechtsstand",
        "export_rechtsstand",
    )
    if any(key not in snapshot for key in required_evidence):
        raise ValueError("archive is missing readiness or Rechtsstand evidence")
    findings = snapshot["readiness_findings"]
    blockers = snapshot["blockers"]
    if not isinstance(findings, list) or not all(isinstance(value, dict) for value in findings):
        raise ValueError("archive readiness evidence is invalid")
    if not isinstance(blockers, list) or not all(isinstance(value, str) for value in blockers):
        raise ValueError("archive blocker evidence is invalid")
    afa_rechtsstand = snapshot["afa_rechtsstand"]
    export_rechtsstand = snapshot["export_rechtsstand"]
    if not isinstance(afa_rechtsstand, str) or not isinstance(export_rechtsstand, str):
        raise ValueError("archive Rechtsstand evidence is invalid")
    return ExportResponse(
        id=archive.id,
        version=archive.version,
        readiness_attempt_id=archive.readiness_attempt_id,
        sha256=archive.sha256,
        generated_at=archive.generated_at,
        artifacts=[
            ExportArtifactResponse(
                id=row.id,
                artifact_kind=row.artifact_kind,
                filename=row.filename,
                sha256=row.sha256,
            )
            for row in artifacts
        ],
        readiness_findings=cast(list[dict[str, object]], findings),
        blockers=cast(list[str], blockers),
        afa_rechtsstand=afa_rechtsstand,
        export_rechtsstand=export_rechtsstand,
        export_kind=cast(
            Literal["anlage_v_pdf", "anlage_v_csv", "datev_extf"],
            getattr(archive, "export_kind", snapshot.get("export_kind", "anlage_v_pdf")),
        ),
        building_id=getattr(archive, "building_id", None),
        tax_year=getattr(archive, "tax_year", None),
    )


@router.get("/exports", response_model=ExportHistoryResponse)
def export_history(account_id: str, session: TaxAccountSession) -> ExportHistoryResponse:
    del account_id
    _authorize(session, "read")
    archives = session.scalars(
        select(TaxExportArchive).order_by(TaxExportArchive.generated_at.desc())
    ).all()
    values = []
    for archive in archives:
        artifacts = session.scalars(
            select(TaxExportArtifact)
            .where(TaxExportArtifact.archive_id == archive.id)
            .order_by(TaxExportArtifact.artifact_kind)
        ).all()
        values.append(_export_out(archive, list(artifacts)))
    return ExportHistoryResponse(exports=values)


@router.get("/exports/{export_id}/artifacts/{artifact_id}")
def download_artifact(
    account_id: str, export_id: str, artifact_id: str, session: TaxAccountSession
) -> Response:
    del account_id
    _authorize(session, "read")
    row = session.scalar(
        select(TaxExportArtifact).where(
            TaxExportArtifact.id == artifact_id, TaxExportArtifact.archive_id == export_id
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Exportartefakt nicht gefunden.")
    return Response(
        content=row.content_bytes,
        media_type=row.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{row.filename}"'},
    )
