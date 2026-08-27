"""M6-B owner-only immutable Page-01 statement finalization and archives."""
# ruff: noqa: E501

from collections.abc import Iterable
from dataclasses import fields, is_dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from hashlib import sha256
from html import escape
from typing import Literal, cast

from fastapi import APIRouter, HTTPException, Response
from lokara_db import (
    AdvanceReconciliation,
    DeliveryAddress,
    PaymentInstruction,
    Statement,
    StatementArchive,
    StatementDraft,
    StatementSettlement,
    StatementStatus,
    Tenancy,
    new_id,
)
from lokara_domain import Period, cents, format_eur, overlap_days
from lokara_heating_engine import HeatingLine, HeatingResult, Page01bStatementResult
from lokara_heating_engine import __version__ as HEATING_ENGINE_VERSION
from lokara_nk_engine import CostItem, ShareLine
from lokara_nk_engine import __version__ as NK_ENGINE_VERSION
from lokara_pdf import DISCLAIMER, PdfOptions, render_html_to_pdf
from sqlalchemy import select

from ..authorization import require_building, require_owner
from ..deps import PathAccountSession
from ..schemas import (
    DeliveryAddressCreate,
    FinalizedDocumentOut,
    FinalizeStatementCreate,
    FinalizeStatementOut,
    PaymentInstructionCreate,
    StatementHistoryOut,
)
from ..statement_service import (
    ALLOCATION_KEY_LABELS,
    STATEMENT_AUTHORITY_ENVELOPE_INCOMPLETE,
    WEIGHT_DISPLAY_DIVISORS,
    EmptyTenancyError,
    StatementAudience,
    StatementBundle,
    StatementProductionBlockedError,
    StatementProjection,
    compute_statement,
    project_statement,
    statement_authority_envelope_is_complete,
)

router = APIRouter(prefix="/a/{account_id}/buildings/{building_id}")
root_router = APIRouter(prefix="/a/{account_id}")

_DOCUMENT_PDF_OPTIONS = PdfOptions(
    display_header_footer=True,
    footer_template=(
        '<div style="width:100%;font-size:8px;color:#596565;text-align:center;">'
        'Seite <span class="pageNumber"></span> von <span class="totalPages"></span></div>'
    ),
)

_A4_DOCUMENT_CSS = """
<style>
  * { box-sizing: border-box; }
  html { color: #202a2b; font-family: Arial, Helvetica, sans-serif; font-size: 10.5pt; }
  body { margin: 0; line-height: 1.45; }
  h1 { margin: 0 0 7mm; font-size: 19pt; line-height: 1.15; }
  h2 { margin: 8mm 0 3mm; border-bottom: 1.2px solid #202a2b; padding-bottom: 2mm; font-size: 13pt; break-after: avoid; }
  h3 { margin: 5mm 0 2mm; font-size: 11pt; break-after: avoid; }
  p { margin: 0 0 3mm; }
  table { width: 100%; border-collapse: collapse; font-size: 8.5pt; }
  thead { display: table-header-group; }
  tr { break-inside: avoid; }
  th { border-bottom: 1.2px solid #202a2b; padding: 2.2mm 1.5mm; text-align: left; vertical-align: bottom; }
  td { border-bottom: .5px solid #c7cece; padding: 2.2mm 1.5mm; vertical-align: top; }
  th:last-child, td:last-child { text-align: right; }
  ul { margin: 2mm 0 4mm; padding-left: 5mm; }
  .document-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 8mm; margin-bottom: 8mm; }
  .document-meta > :last-child { text-align: right; }
  .address { min-height: 35mm; margin-top: 8mm; }
  .sender-line { border-bottom: .5px solid #6b7575; padding-bottom: 1mm; font-size: 8pt; color: #596565; }
  .subject { margin: 8mm 0 5mm; font-size: 13pt; font-weight: 700; }
  .summary { margin: 6mm 0; border-top: 1.2px solid #202a2b; border-bottom: 1.2px solid #202a2b; padding: 4mm 0; }
  .summary-row { display: flex; justify-content: space-between; gap: 8mm; margin: 1.5mm 0; }
  .summary-row strong { font-size: 12pt; }
  .muted { color: #596565; font-size: 9pt; }
  .draft-banner { margin: 0 0 7mm; border: 1px solid #202a2b; padding: 2.5mm; text-align: center; font-weight: 700; letter-spacing: .05em; }
  .page-break { break-before: page; }
  .avoid-break { break-inside: avoid; }
</style>
"""


def _document_html(
    title: str, body: str, *, draft: bool = False, production_blocked: bool = False
) -> str:
    banner = '<div class="draft-banner">ENTWURF - NICHT VERSENDET</div>' if draft else ""
    if production_blocked:
        banner += (
            '<div class="draft-banner">TECHNISCHE DEMO - RECHTSWERTE NICHT '
            "PRODUKTIONSFREIGEGEBEN</div>"
        )
    return (
        '<!doctype html><html lang="de"><head><meta charset="utf-8">'
        f"<title>{escape(title)}</title>{_A4_DOCUMENT_CSS}</head><body>{banner}{body}</body></html>"
    )


def _decimal_de(value: Decimal) -> str:
    return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _number_de(value: Decimal, *, places: int = 0) -> str:
    """German fixed-point display; never expose engine weights verbatim."""
    return f"{value:,.{places}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _nk_weight(cost: CostItem, weight: Decimal, consumption_unit: object | None) -> str:
    divisor = WEIGHT_DISPLAY_DIVISORS.get(cost.key)
    display = weight if divisor is None else weight / divisor
    unit = {
        "AREA": "m²·Tage",
        "PERSONS": "Personen·Tage",
        "UNITS": "Einheiten·Tage",
        "MEA": "MEA·Tage",
        "DIRECT": "Direktzuordnung",
    }.get(cost.key.value)
    if cost.key.value == "CONSUMPTION":
        unit = {"KWH": "kWh", "CUBIC_METRE": "m³", "HKV_UNITS": "HKV-Einheiten"}.get(
            str(getattr(consumption_unit, "value", consumption_unit)), "Verbrauch"
        )
    return f"{_number_de(display)} {unit}" if unit else _number_de(display)


def _allocation_explanation(cost: CostItem) -> str:
    return {
        "AREA": "Verteilung nach Wohnfläche und Nutzungstagen.",
        "PERSONS": "Verteilung nach Personenzahl und Nutzungstagen.",
        "CONSUMPTION": "Verteilung nach abgelesenem Verbrauch.",
        "UNITS": "Verteilung nach Einheiten und Nutzungstagen.",
        "DIRECT": "Direkte Zuordnung zu Ihrer Einheit.",
        "MEA": "Verteilung nach Miteigentumsanteilen und Nutzungstagen.",
    }[cost.key.value]


def _instruction_for_saldo(instruction_text: str, saldo: int, *, late_positive: bool) -> str:
    if saldo == 0 or late_positive:
        return ""
    prefix = "Zahlung:" if saldo > 0 else "Guthaben:"
    return next(
        (
            line.removeprefix(prefix).strip()
            for line in instruction_text.splitlines()
            if line.startswith(prefix)
        ),
        "",
    )


def _nk_numerator(
    cost: CostItem, line: ShareLine, tenancy: Tenancy, period_start: date, period_end: date
) -> str:
    if cost.key.value not in {"AREA", "MEA", "PERSONS", "UNITS"}:
        return _nk_weight(cost, line.weight, None)
    valid_from = getattr(tenancy, "valid_from", period_start)
    valid_to = getattr(tenancy, "valid_to", None) or period_end + timedelta(days=1)
    days = (min(valid_to, period_end + timedelta(days=1)) - max(valid_from, period_start)).days
    if days <= 0:
        return _nk_weight(cost, line.weight, None)
    divisor = WEIGHT_DISPLAY_DIVISORS.get(cost.key, Decimal(1))
    unit = _nk_weight(cost, Decimal(1), None).split(" ", maxsplit=1)[1]
    base = line.weight / divisor / Decimal(days)
    return f"{_number_de(base)} × {days} Tage = {_number_de(line.weight / divisor)} {unit}"


def _heating_html(
    *,
    line: HeatingLine,
    all_lines: Iterable[HeatingLine],
    result: HeatingResult | None,
) -> str:
    """Tenant-safe HeizkostenV Blocks A--C from the one selected result."""
    lines = tuple(all_lines)
    if result is None:
        return ""
    co2 = getattr(result, "co2", None)
    co2_text = "kein CO₂-Aufteilungsbetrag"
    if co2 is not None:
        co2_text = (
            f"CO₂-Kosten {format_eur(co2.co2_cost)}; Mieteranteil {format_eur(co2.renter_amount)}; "
            f"Vermieteranteil {co2.landlord_share_percent} %"
        )
    base_denominator = sum(item.base_weight_sqm_days_x100 for item in lines) / Decimal(100)
    heat_denominator = sum(
        (item.heat_consumption_weight or Decimal(0) for item in lines), Decimal(0)
    )
    ww_denominator = sum(
        (item.ww_consumption_weight_m3 or Decimal(0) for item in lines), Decimal(0)
    )
    heat_unit = {"KWH": "kWh", "CUBIC_METRE": "m³", "HKV_UNITS": "HKV-Einheiten"}.get(
        str(getattr(result.heat_consumption_unit, "value", None)), "Verbrauch"
    )
    return f"""
    <section><h2>Heiz- und Warmwasserkosten</h2>
    <h3>Block A — Kosten und CO₂</h3><p>Gesamtkosten: {escape(format_eur(result.total))}; abrechenbare Kosten: {escape(format_eur(result.billable_cost))}; {escape(co2_text)}.</p>
    <h3>Block B — Kostenanteile und Umlageschlüssel</h3>
    <p>Heizkosten: Grundkosten {escape(format_eur(result.heat_base_pot))}, Verbrauchskosten {escape(format_eur(result.heat_cons_pot))}; Warmwasser: Grundkosten {escape(format_eur(result.ww_base_pot))}, Verbrauchskosten {escape(format_eur(result.ww_cons_pot))}.</p>
    <p>Angewandter Heizkosten-Schlüssel: {_decimal_de(result.applied_consumption_share * Decimal(100))} % Verbrauch / {_decimal_de((Decimal(1) - result.applied_consumption_share) * Decimal(100))} % Grundkosten; Flächenanteile nach m²·Tagen, Verbrauchsanteile nach abgelesenem Verbrauch (§§ 7–9 HeizkostenV).</p>
    <p>Flächenbemessung: {_number_de(line.base_weight_sqm_days_x100 / Decimal(100))} m²·Tage von {_number_de(base_denominator)} m²·Tage. Heizverbrauch: {_decimal_de(line.heat_consumption_weight or Decimal(0))} {escape(heat_unit)} von {_decimal_de(heat_denominator)} {escape(heat_unit)}. Warmwasserverbrauch: {_decimal_de(line.ww_consumption_weight_m3 or Decimal(0))} m³ von {_decimal_de(ww_denominator)} m³. Warmwassertrennung: {"zentral nach § 9 HeizkostenV" if result.warm_water_separation is not None else "keine zentrale Warmwassertrennung"}.</p>
    <h3>Block C — Ihr Anteil und Herleitung</h3>
    <p>Heizung Grundkosten {escape(format_eur(line.heating_base))}; Heizung Verbrauchskosten {escape(format_eur(line.heating_consumption))}; Warmwasser Grundkosten {escape(format_eur(line.ww_base))}; Warmwasser Verbrauchskosten {escape(format_eur(line.ww_consumption))}.</p>
    <p>Operator: Anteil = Kostenanteil × Bemessung ÷ Gesamtbemessung. Flächen-Numerator: {_number_de(line.base_weight_sqm_days_x100 / Decimal(100 * line.days))} m² × {line.days} Tage = {_number_de(line.base_weight_sqm_days_x100 / Decimal(100))} m²·Tage; Gradtagszahlen {_decimal_de(line.degree_day_promille)} ‰ ÷ {_decimal_de(line.unit_degree_day_promille_total)} ‰.</p></section>"""


def _snapshot_value(value: object) -> object:
    """Make normalized engine values durable JSON without losing precision.

    The archive must reproduce the exact calculation, rather than a display
    projection. Decimal therefore stays a decimal string and every dataclass
    field remains named; neither is delegated to a lossy JSON default hook.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _snapshot_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, dict):
        return {str(key): _snapshot_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_snapshot_value(item) for item in value]
    raise TypeError(f"Cannot snapshot normalized value {type(value).__name__}")


def _projection_snapshot(projection: StatementProjection) -> dict[str, object]:
    """Persist a selected projection without serializing live SQLAlchemy rows."""
    return {
        "audience": projection.audience.value,
        "tenancy_id": projection.tenancy_id,
        "window": _snapshot_value(projection.window),
        "nk_costs": _snapshot_value(projection.nk_costs),
        "nk_lines": _snapshot_value(projection.nk_lines),
        "heating_lines": _snapshot_value(projection.heating_lines),
        "owner_residual": _snapshot_value(projection.owner_residual),
        "party_labels": _snapshot_value(
            {
                f"{unit_id}:{tenancy_id or 'OWNER'}": label
                for (unit_id, tenancy_id), label in projection.party_labels.items()
            }
        ),
        "findings": list(projection.findings),
        "non_allocable_costs": [
            {"label": label, "amount_cents": amount}
            for label, amount in projection.non_allocable_costs
        ],
    }


def _frozen_production_blockers(*surfaces: object) -> list[str]:
    """Collect unresolved production/legal flags already frozen in M6-B data."""

    blockers: list[str] = []
    flagged_statuses = {
        "verify-before-production",
        "unsicher",
        "uncertain",
        "blocked",
        "missing",
    }

    def visit(value: object, path: str) -> None:
        if isinstance(value, dict):
            explicit = value.get("production_blockers")
            if isinstance(explicit, (list, tuple)):
                blockers.extend(str(item) for item in explicit if str(item).strip())
            verification = value.get("verification_status")
            legal_status = value.get("legal_status")
            status = value.get("status")
            selected_status = (
                verification
                if isinstance(verification, str)
                else legal_status
                if isinstance(legal_status, str)
                else status
                if isinstance(status, str) and status.strip().lower() in flagged_statuses
                else None
            )
            if isinstance(selected_status, str) and selected_status.strip().lower() not in {
                "geprüft",
                "verified",
                "approved",
                "closed",
            }:
                marker = (
                    value.get("name")
                    or value.get("code")
                    or value.get("source")
                    or value.get("legal_basis")
                    or path
                )
                blockers.append(f"{marker}: {selected_status}")
            conflicts = value.get("unresolved_conflicts")
            if isinstance(conflicts, (list, tuple)):
                for conflict in conflicts:
                    if isinstance(conflict, dict) and conflict.get("production_blocking") is True:
                        blockers.append(
                            str(conflict.get("code") or "UNRESOLVED-PRODUCTION-CONFLICT")
                        )
            if value.get("production_blocked") is True and not explicit:
                blockers.append(f"PRODUCTION-BLOCKED:{path}")
            for key, item in value.items():
                if key not in {"production_blockers", "unresolved_conflicts"}:
                    visit(item, f"{path}.{key}")
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")
        elif isinstance(value, str) and any(
            marker in value.lower() for marker in ("verify-before-production", "unsicher")
        ):
            blockers.append(value)

    for index, surface in enumerate(surfaces):
        visit(surface, f"surface[{index}]")
    return list(dict.fromkeys(blockers))


def _finalized_snapshot(
    *,
    bundle: StatementBundle,
    owner_projection: StatementProjection,
    vacancy_projection: StatementProjection,
    eligible: list[
        tuple[Tenancy, StatementProjection, DeliveryAddress, AdvanceReconciliation, int, int]
    ],
    instruction: PaymentInstruction,
    exception_reason: str | None,
    landlord_name: str = "Vermieter",
    building_name: str = "Objekt",
    period_start: date | None = None,
    period_end: date | None = None,
    zero_day_tenancy_ids: Iterable[str] = (),
) -> dict[str, object]:
    """Complete M6-B calculation evidence, independent from mutable live rows."""
    normalized_inputs = _snapshot_value(bundle.normalized_inputs)
    calculation_results = {
        "nk": _snapshot_value(bundle.nk_result),
        "heating": _snapshot_value(bundle.heating_result),
        "page01b": _snapshot_value(bundle.page01b_result),
        "heating_input_total": _snapshot_value(bundle.heating_input_total),
        "heating_missing_reason": bundle.heating_missing_reason,
    }
    findings = list(bundle.nk_findings)
    provenance = _snapshot_value(
        bundle.page01b_result.provenance if bundle.page01b_result is not None else ()
    )
    statement_rule_evidence = [dict(row) for row in getattr(bundle, "statement_rule_evidence", ())]
    snapshot: dict[str, object] = {
        "snapshot_version": "M6-B/2",
        "engine_versions": {
            "nk_engine": NK_ENGINE_VERSION,
            "heating_engine": HEATING_ENGINE_VERSION,
            "statement_finalizer": "M6-B/1",
        },
        "rule_versions": {
            "rechtsstaende": list(bundle.rechtsstaende),
            "entries": list(bundle.rechtsstand_entries),
        },
        "normalized_inputs": normalized_inputs,
        "calculation_results": calculation_results,
        "findings": findings,
        "provenance": provenance,
        "statement_rule_evidence": statement_rule_evidence,
        "owner_output": _projection_snapshot(owner_projection),
        "vacancy_output": _projection_snapshot(vacancy_projection),
        "tenant_outputs": [
            {
                "projection": _projection_snapshot(projection),
                "address": {
                    "id": address.id,
                    "version": address.version,
                    "valid_from": address.valid_from.isoformat(),
                    "addressee": address.addressee,
                    "street": address.street,
                    "postal_code": address.postal_code,
                    "city": address.city,
                    "country": address.country,
                },
                "reconciliation": {
                    "id": reconciliation.id,
                    "version": reconciliation.version,
                    "total_cents": reconciliation.total_cents,
                },
                "subtotal_cents": subtotal,
                "saldo_cents": saldo,
            }
            for _tenancy, projection, address, reconciliation, subtotal, saldo in eligible
        ],
        "payment_credit_instruction": {
            "id": instruction.id,
            "version": instruction.version,
            "valid_from": instruction.valid_from.isoformat(),
            "value": instruction.instruction_text,
        },
        "late_positive_exception_reason": exception_reason,
        # This is deliberately data, never pre-rendered HTML.  Final archive
        # renderers below accept only this JSON-safe branch, so a later change
        # to an ORM row or the live calculation cannot enter an old document.
        "final_render": _final_render_payload(
            owner_projection=owner_projection,
            vacancy_projection=vacancy_projection,
            eligible=eligible,
            instruction=instruction,
            landlord_name=landlord_name,
            building_name=building_name,
            period_start=period_start,
            period_end=period_end,
            zero_day_tenancy_ids=zero_day_tenancy_ids,
            rechtsstaende=bundle.rechtsstand_entries,
            heating_result=bundle.heating_result,
            page01b_result=bundle.page01b_result,
            late_positive_exception_reason=exception_reason,
        ),
    }
    production_blockers = _frozen_production_blockers(
        normalized_inputs,
        calculation_results,
        findings,
        provenance,
        statement_rule_evidence,
    )
    # Freezing the blocker list without the inventory it was derived from produces an
    # envelope whose empty list cannot be distinguished from a clean statement. The
    # finalizer records that fact here, so the M9 delivery path reads it as data
    # rather than re-deriving it from a snapshot it did not build.
    if not statement_authority_envelope_is_complete(production_blockers, statement_rule_evidence):
        production_blockers.insert(0, STATEMENT_AUTHORITY_ENVELOPE_INCOMPLETE)
    snapshot["production_blockers"] = production_blockers
    final_render = cast(dict[str, object], snapshot["final_render"])
    cast(dict[str, object], final_render["owner"])["production_blocked"] = bool(production_blockers)
    for tenant in cast(list[dict[str, object]], final_render["tenants"]):
        tenant["production_blocked"] = bool(production_blockers)
    return snapshot


def _archive_out(row: StatementArchive) -> FinalizedDocumentOut:
    return FinalizedDocumentOut(
        id=row.id,
        audience=cast(Literal["OWNER", "TENANT"], row.audience),
        tenancy_id=row.tenancy_id,
        document_type=(
            "OWNER_OVERVIEW"
            if row.audience == "OWNER"
            else cast(
                Literal["COVER_LETTER", "TENANT_STATEMENT"],
                row.document_type,
            )
        ),
        filename=row.filename,
        sha256=row.sha256,
    )


def _history(session: PathAccountSession, statement: Statement) -> StatementHistoryOut:
    documents = session.scalars(
        select(StatementArchive).where(StatementArchive.statement_id == statement.id)
    ).all()
    return StatementHistoryOut(
        id=statement.id,
        version=statement.version,
        status=cast(Literal["FINALIZED", "SUPERSEDED"], statement.status.value),
        period_start=statement.period_start,
        period_end=statement.period_end,
        content_hash=statement.content_hash,
        finalized_at=statement.finalized_at,
        supersedes_statement_id=statement.supersedes_statement_id,
        documents=[_archive_out(row) for row in documents],
    )


def _address(session: PathAccountSession, tenancy_id: str, period_end: date) -> DeliveryAddress:
    row = session.scalar(
        select(DeliveryAddress)
        .where(DeliveryAddress.tenancy_id == tenancy_id, DeliveryAddress.valid_from <= period_end)
        .order_by(DeliveryAddress.version.desc(), DeliveryAddress.created_at.desc())
    )
    if row is None:
        raise HTTPException(
            status_code=422, detail="Für ein Mietverhältnis fehlt eine Zustelladresse."
        )
    return row


def _instruction(
    session: PathAccountSession, building_id: str, period_end: date
) -> PaymentInstruction:
    del building_id
    row = session.scalar(
        select(PaymentInstruction)
        .where(PaymentInstruction.valid_from <= period_end)
        .order_by(PaymentInstruction.version.desc(), PaymentInstruction.created_at.desc())
    )
    if row is None:
        raise HTTPException(
            status_code=422, detail="Für das Objekt fehlen Zahlungs- und Guthabenhinweise."
        )
    return row


def _tenant_html(
    *,
    tenancy: Tenancy,
    address: DeliveryAddress,
    period_start: date,
    period_end: date,
    subtotal: int,
    advances: int,
    saldo: int,
    instruction_text: str,
    rechtsstaende: tuple[str, ...],
    nk_lines: Iterable[ShareLine],
    nk_costs: Iterable[CostItem],
    all_nk_lines: Iterable[ShareLine],
    heating_lines: Iterable[HeatingLine],
    all_heating_lines: Iterable[HeatingLine],
    late_positive: bool,
    heating_result: HeatingResult | None = None,
    page01b_result: Page01bStatementResult | None = None,
) -> str:
    # This renderer receives only a selected tenancy's lines and values.  It is
    # intentionally not a redacted owner document (docs/08 §3).
    costs = {cost.cost_id: cost for cost in nk_costs}
    all_lines = tuple(all_nk_lines)
    rows = "".join(
        f"<tr><td>{escape(costs[line.cost_id].label)}</td><td>{escape(format_eur(costs[line.cost_id].amount))}</td><td>{escape(ALLOCATION_KEY_LABELS[costs[line.cost_id].key])}</td><td>{escape(_nk_numerator(costs[line.cost_id], line, tenancy, period_start, period_end))}</td><td>{escape(_nk_weight(costs[line.cost_id], sum((item.weight for item in all_lines if item.cost_id == line.cost_id), Decimal(0)), None))}</td><td>{escape(format_eur(line.amount))}</td></tr>"
        for line in nk_lines
    )
    heating = "".join(
        _heating_html(line=line, all_lines=all_heating_lines, result=heating_result)
        for line in heating_lines
    )
    device_rows = ""
    if page01b_result is not None:
        device_rows = "".join(
            f"<li>{escape(item.device_id)}: {escape(item.room)}; {escape(_decimal_de(item.opening or Decimal(0)))}–{escape(_decimal_de(item.closing or Decimal(0)))} {escape(item.measurement_unit.value)}; Faktor {escape(_decimal_de(item.valuation_factor))}; Ablesestatus: {'geschätzt' if item.estimated else 'abgelesen'}; Gründe: {escape(', '.join(item.reading_reasons) or 'keine Angabe')}; Quellen: {escape(', '.join(item.reading_sources) or 'keine Angabe')}; Nachweise: {escape(', '.join(item.provenance_refs) or 'keine Angabe')}</li>"
            for item in page01b_result.device_evidence
            if item.target_id == getattr(tenancy, "id", None)
        )
    notices = ""
    if page01b_result is not None:
        notices = "".join(f"<li>{escape(risk.message_de)}</li>" for risk in page01b_result.risks)
    saldo_label = (
        "Rechnerischer Saldo"
        if late_positive
        else ("Nachzahlung" if saldo > 0 else "Guthaben" if saldo < 0 else "Saldo")
    )
    # A late positive balance without the explicit exception is still shown for
    # auditability, but cannot carry either the payment demand or the credit
    # copy bundled in the owner instruction record.
    instruction = _instruction_for_saldo(instruction_text, saldo, late_positive=late_positive)
    return f"""<!doctype html><html lang=\"de\"><meta charset=\"utf-8\"><body>
    <h1>Mieter-Einzelabrechnung</h1>
    <p>{escape(address.addressee)}<br>{escape(address.street)}<br>{escape(address.postal_code)} {escape(address.city)}<br>{escape(address.country)}</p>
    <p>Objekt: {escape(tenancy.unit.building.name)}, {escape(tenancy.unit.label)}<br>
    Abrechnungszeitraum: {period_start.strftime("%d.%m.%Y")}–{period_end.strftime("%d.%m.%Y")}<br>
    Erstellt am: {date.today().strftime("%d.%m.%Y")}</p>
    <h2>Kosten und Ihr Anteil</h2><table><tr><th>Kostenart</th><th>Gesamtkosten</th><th>Umlageschlüssel</th><th>Ihre Bemessung</th><th>Gesamtbemessung</th><th>Anteil</th></tr>{rows}</table>
    <p>Berechnung je Kostenart: Anteil = Gesamtkosten × Ihre Bemessung ÷ Gesamtbemessung.</p>
    {heating}<section><h2>Zählernachweise</h2><ul>{device_rows}</ul></section><section><h2>Hinweise</h2><ul>{notices}</ul></section>
    <p>Ihr Anteil gesamt: {escape(format_eur(cents(subtotal)))}<br>Geleistete Vorauszahlungen: {escape(format_eur(cents(advances)))}<br><strong>{saldo_label}: {escape(format_eur(cents(saldo)))}</strong></p>
    <p>{escape(instruction)}</p>
    <p>{escape(DISCLAIMER)}</p><p>Rechtsstand: {escape(", ".join(rechtsstaende))}</p>
    </body></html>"""


def _vacancy_html(projection: StatementProjection) -> str:
    """The owner-only Leerstandsaufstellung, with all three required blocks."""
    costs = {cost.cost_id: cost for cost in projection.nk_costs}
    nk_rows = "".join(
        f"<tr><td>{escape(line.unit_id or 'Objekt')}</td><td>{escape(costs[line.cost_id].label)}</td><td>{escape(format_eur(line.amount))}</td></tr>"
        for line in projection.nk_lines
    )
    residual = projection.owner_residual
    origin_rows = ""
    rounding = ""
    if residual is not None:
        origin_rows = "".join(
            f"<tr><td>{escape(origin.unit_id)}</td><td>Heizung {escape(format_eur(origin.heating_base))}; Verbrauch {escape(format_eur(origin.heating_consumption))}; Warmwasser Grund {escape(format_eur(origin.ww_base))}; Verbrauch {escape(format_eur(origin.ww_consumption))}</td><td>{escape(format_eur(origin.total))}</td></tr>"
            for origin in residual.origins
        )
        if int(residual.rounding_difference) != 0:
            rounding = (
                f"<p>Rundungsdifferenz: {escape(format_eur(residual.rounding_difference))}</p>"
            )
    non_allocable = "".join(
        f"<li>{escape(label)}: {escape(format_eur(cents(amount)))}</li>"
        for label, amount in getattr(projection, "non_allocable_costs", ())
    )
    return f"""<section><h2>Leerstandsaufstellung</h2>
    <h3>(a) Leerstand und Eigennutzung je Einheit/Kostenart</h3><table><tr><th>Einheit</th><th>Kostenart</th><th>Betrag</th></tr>{nk_rows}{origin_rows}</table>
    <h3>(b) Nicht umlagefähige Zuordnungen</h3><ul>{non_allocable}</ul>
    <h3>(c) Rundungsdifferenz</h3>{rounding}</section>"""


def _final_render_payload(
    *,
    owner_projection: StatementProjection,
    vacancy_projection: StatementProjection,
    eligible: list[
        tuple[Tenancy, StatementProjection, DeliveryAddress, AdvanceReconciliation, int, int]
    ],
    instruction: PaymentInstruction,
    landlord_name: str,
    building_name: str,
    period_start: date | None,
    period_end: date | None,
    zero_day_tenancy_ids: Iterable[str],
    rechtsstaende: tuple[str, ...],
    heating_result: HeatingResult | None,
    page01b_result: Page01bStatementResult | None,
    late_positive_exception_reason: str | None,
) -> dict[str, object]:
    """Select all final-document fields while live rows are still in scope."""
    if period_start is None or period_end is None:
        raise ValueError("Final render payload requires a bounded billing period.")
    owner_costs = {cost.cost_id: cost for cost in owner_projection.nk_costs}
    vacancy_costs = {cost.cost_id: cost for cost in vacancy_projection.nk_costs}
    vacancy_residual = vacancy_projection.owner_residual
    vacancy = {
        "block_a": [
            {
                "unit_id": line.unit_id or "Objekt",
                "label": vacancy_costs[line.cost_id].label,
                "amount_cents": int(line.amount),
            }
            for line in vacancy_projection.nk_lines
        ]
        + (
            [
                {
                    "unit_id": origin.unit_id,
                    "label": "Heizung "
                    + "; ".join(
                        (
                            f"Grund {format_eur(origin.heating_base)}",
                            f"Verbrauch {format_eur(origin.heating_consumption)}",
                            f"Warmwasser Grund {format_eur(origin.ww_base)}",
                            f"Verbrauch {format_eur(origin.ww_consumption)}",
                        )
                    ),
                    "amount_cents": int(origin.total),
                }
                for origin in vacancy_residual.origins
            ]
            if vacancy_residual is not None
            else []
        ),
        "block_b": [
            {"label": label, "amount_cents": amount}
            for label, amount in vacancy_projection.non_allocable_costs
        ],
        "block_c_rounding_cents": (
            int(vacancy_residual.rounding_difference) if vacancy_residual is not None else 0
        ),
    }
    tenants: list[dict[str, object]] = []
    for tenancy, projection, address, reconciliation, subtotal, saldo in eligible:
        costs = {cost.cost_id: cost for cost in projection.nk_costs}
        all_lines = tuple(line for line in owner_projection.nk_lines if line.cost_id in costs)
        # The selected tenant's NK denominator/numerator strings are frozen at
        # finalization.  Rendering only lays out these carriers; it does not
        # recalculate a share from a current tenancy timeline.
        nk_rows = [
            {
                "label": costs[line.cost_id].label,
                "total_cents": int(costs[line.cost_id].amount),
                "allocation_label": ALLOCATION_KEY_LABELS[costs[line.cost_id].key],
                "allocation_explanation": _allocation_explanation(costs[line.cost_id]),
                "numerator": _nk_numerator(
                    costs[line.cost_id], line, tenancy, period_start, period_end
                ),
                "denominator": _nk_weight(
                    costs[line.cost_id],
                    sum(
                        (item.weight for item in all_lines if item.cost_id == line.cost_id),
                        Decimal(0),
                    ),
                    None,
                ),
                "share_cents": int(line.amount),
            }
            for line in projection.nk_lines
        ]
        heating_rows: list[dict[str, object]] = []
        if heating_result is not None:
            selected_heating = tuple(projection.heating_lines)
            all_heating = tuple(heating_result.lines)
            result = heating_result
            for line in selected_heating:
                heating_rows.append(
                    {
                        "total_cents": int(result.total),
                        "billable_cents": int(result.billable_cost),
                        "co2_text": (
                            "kein CO₂-Aufteilungsbetrag"
                            if result.co2 is None
                            else f"CO₂-Kosten {format_eur(result.co2.co2_cost)}; Mieteranteil {format_eur(result.co2.renter_amount)}; Vermieteranteil {result.co2.landlord_share_percent} %"
                        ),
                        "heat_base_cents": int(result.heat_base_pot),
                        "heat_consumption_cents": int(result.heat_cons_pot),
                        "ww_base_cents": int(result.ww_base_pot),
                        "ww_consumption_cents": int(result.ww_cons_pot),
                        "consumption_share": str(result.applied_consumption_share),
                        "base_weight": str(line.base_weight_sqm_days_x100 / Decimal(100)),
                        "base_denominator": str(
                            sum(item.base_weight_sqm_days_x100 for item in all_heating)
                            / Decimal(100)
                        ),
                        "heat_weight": str(line.heat_consumption_weight or Decimal(0)),
                        "heat_denominator": str(
                            sum(
                                (
                                    item.heat_consumption_weight or Decimal(0)
                                    for item in all_heating
                                ),
                                Decimal(0),
                            )
                        ),
                        "ww_weight": str(line.ww_consumption_weight_m3 or Decimal(0)),
                        "ww_denominator": str(
                            sum(
                                (
                                    item.ww_consumption_weight_m3 or Decimal(0)
                                    for item in all_heating
                                ),
                                Decimal(0),
                            )
                        ),
                        "heat_unit": str(
                            getattr(result.heat_consumption_unit, "value", "Verbrauch")
                        ),
                        "warm_water_separation": result.warm_water_separation is not None,
                        "line": {
                            "heating_base_cents": int(line.heating_base),
                            "heating_consumption_cents": int(line.heating_consumption),
                            "ww_base_cents": int(line.ww_base),
                            "ww_consumption_cents": int(line.ww_consumption),
                            "days": line.days,
                            "degree_day_promille": str(line.degree_day_promille),
                            "unit_degree_day_promille_total": str(
                                line.unit_degree_day_promille_total
                            ),
                        },
                    }
                )
        device_evidence = (
            []
            if page01b_result is None
            else [
                _snapshot_value(item)
                for item in page01b_result.device_evidence
                if item.target_id == tenancy.id
            ]
        )
        notices = (
            [] if page01b_result is None else [risk.message_de for risk in page01b_result.risks]
        )
        late_positive = saldo > 0 and date.today() > period_end.replace(year=period_end.year + 1)
        withheld = late_positive and late_positive_exception_reason is None
        tenants.append(
            {
                "tenancy_id": tenancy.id,
                "landlord_name": landlord_name,
                "building_name": building_name,
                "unit_label": tenancy.unit.label,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "created_on": date.today().isoformat(),
                "address": {
                    "addressee": address.addressee,
                    "street": address.street,
                    "postal_code": address.postal_code,
                    "city": address.city,
                    "country": address.country,
                },
                "projection": {"nk_rows": nk_rows, "heating_rows": heating_rows},
                "meter_evidence": device_evidence,
                "notices": notices,
                "reconciliation": {
                    "id": reconciliation.id,
                    "version": reconciliation.version,
                    "advances_cents": reconciliation.total_cents,
                },
                "subtotal_cents": subtotal,
                "saldo_cents": saldo,
                "saldo_branch": (
                    "RECHNERISCHER_SALDO"
                    if withheld
                    else "NACHZAHLUNG"
                    if saldo > 0
                    else "GUTHABEN"
                    if saldo < 0
                    else "SALDO"
                ),
                "instruction": (
                    ""
                    if withheld
                    else _instruction_for_saldo(
                        instruction.instruction_text, saldo, late_positive=False
                    )
                ),
                "rechtsstaende": list(rechtsstaende),
            }
        )
    return {
        "owner": {
            "landlord_name": landlord_name,
            "building_name": building_name,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "created_on": date.today().isoformat(),
            "projection": _projection_snapshot(owner_projection),
            "cost_rows": [
                {
                    "cost_label": owner_costs[line.cost_id].label,
                    "party_label": owner_projection.party_labels.get(
                        (line.unit_id, line.tenancy_id), line.unit_id or "Objekt"
                    ),
                    "amount_cents": int(line.amount),
                }
                for line in owner_projection.nk_lines
            ],
            "heating_rows": [
                {
                    "party_label": owner_projection.party_labels.get(
                        (line.unit_id, line.tenancy_id), line.unit_id
                    ),
                    "heating_base_cents": int(line.heating_base),
                    "heating_consumption_cents": int(line.heating_consumption),
                    "ww_base_cents": int(line.ww_base),
                    "ww_consumption_cents": int(line.ww_consumption),
                    "total_cents": int(line.total),
                }
                for line in owner_projection.heating_lines
            ],
            "heating_summary": (
                None
                if heating_result is None
                else {
                    "total_cents": int(heating_result.total),
                    "billable_cents": int(heating_result.billable_cost),
                    "co2_landlord_cents": (
                        0 if heating_result.co2 is None else int(heating_result.co2.landlord_amount)
                    ),
                    "heat_base_cents": int(heating_result.heat_base_pot),
                    "heat_consumption_cents": int(heating_result.heat_cons_pot),
                    "ww_base_cents": int(heating_result.ww_base_pot),
                    "ww_consumption_cents": int(heating_result.ww_cons_pot),
                    "renter_lines_total_cents": sum(
                        int(line.total) for line in heating_result.lines
                    ),
                    "owner_residual_cents": int(heating_result.owner_residual.total),
                }
            ),
            "reconciliations": [
                {"tenancy_id": tenancy.id, "advances_cents": rec.total_cents, "saldo_cents": saldo}
                for tenancy, _projection, _address, rec, _subtotal, saldo in eligible
            ],
            "zero_day_tenancy_ids": list(zero_day_tenancy_ids),
            "vacancy": vacancy,
            "notices": []
            if page01b_result is None
            else [risk.message_de for risk in page01b_result.risks],
            "rechtsstaende": list(rechtsstaende),
        },
        "tenants": tenants,
    }


def _snapshot_date(value: object) -> date:
    return date.fromisoformat(cast(str, value))


def _snapshot_decimal(value: object) -> Decimal:
    return Decimal(cast(str, value))


def _vacancy_html_from_snapshot(vacancy: dict[str, object]) -> str:
    block_a = cast(list[dict[str, object]], vacancy["block_a"])
    block_b = cast(list[dict[str, object]], vacancy["block_b"])
    rows = "".join(
        f"<tr><td>{escape(cast(str, row['unit_id']))}</td><td>{escape(cast(str, row['label']))}</td><td>{escape(format_eur(cents(cast(int, row['amount_cents']))))}</td></tr>"
        for row in block_a
    )
    non_allocable = "".join(
        f"<li>{escape(cast(str, row['label']))}: {escape(format_eur(cents(cast(int, row['amount_cents']))))}</li>"
        for row in block_b
    )
    rounding = cast(int, vacancy["block_c_rounding_cents"])
    return f"""<section><h2>Leerstandsaufstellung</h2>
    <h3>(a) Leerstand und Eigennutzung je Einheit/Kostenart</h3><table><tr><th>Einheit</th><th>Kostenart</th><th>Betrag</th></tr>{rows}</table>
    <h3>(b) Nicht umlagefähige Zuordnungen</h3><ul>{non_allocable}</ul>
    <h3>(c) Rundungsdifferenz</h3>{f"<p>Rundungsdifferenz: {escape(format_eur(cents(rounding)))}</p>" if rounding else ""}</section>"""


def _owner_html_from_snapshot(render: dict[str, object]) -> str:
    """Render an owner archive solely from ``final_render.owner`` JSON data."""
    owner = cast(dict[str, object], render["owner"])
    period_start, period_end = (
        _snapshot_date(owner["period_start"]),
        _snapshot_date(owner["period_end"]),
    )
    reconciliation = "".join(
        f"<p>Mietverhältnis {escape(cast(str, row['tenancy_id']))}: bestätigte Vorauszahlungen {escape(format_eur(cents(cast(int, row['advances_cents']))))}; Saldo {escape(format_eur(cents(cast(int, row['saldo_cents']))))}</p>"
        for row in cast(list[dict[str, object]], owner["reconciliations"])
    )
    cost_rows = "".join(
        f"<tr><td>{escape(cast(str, row['cost_label']))}</td><td>{escape(cast(str, row['party_label']))}</td><td>{escape(format_eur(cents(cast(int, row['amount_cents']))))}</td></tr>"
        for row in cast(list[dict[str, object]], owner["cost_rows"])
    )
    heating_rows = "".join(
        f"<tr><td>{escape(cast(str, row['party_label']))}</td><td>{escape(format_eur(cents(cast(int, row['heating_base_cents']))))}</td><td>{escape(format_eur(cents(cast(int, row['heating_consumption_cents']))))}</td><td>{escape(format_eur(cents(cast(int, row['ww_base_cents']))))}</td><td>{escape(format_eur(cents(cast(int, row['ww_consumption_cents']))))}</td><td>{escape(format_eur(cents(cast(int, row['total_cents']))))}</td></tr>"
        for row in cast(list[dict[str, object]], owner["heating_rows"])
    )
    heating_summary = cast(dict[str, object] | None, owner["heating_summary"])
    heating_summary_html = ""
    if heating_summary is not None:
        heating_summary_html = (
            "<p>Gesamtkosten: "
            f"{escape(format_eur(cents(cast(int, heating_summary['total_cents']))))}; "
            f"abrechenbare Kosten: {escape(format_eur(cents(cast(int, heating_summary['billable_cents']))))}; "
            f"CO₂-Vermieteranteil: {escape(format_eur(cents(cast(int, heating_summary['co2_landlord_cents']))))}.</p>"
            "<p>Abgleich Heizkosten: Mieteranteile "
            f"{escape(format_eur(cents(cast(int, heating_summary['renter_lines_total_cents']))))} + Eigentümerrest "
            f"{escape(format_eur(cents(cast(int, heating_summary['owner_residual_cents']))))} = "
            f"{escape(format_eur(cents(cast(int, heating_summary['billable_cents']))))}.</p>"
        )
    zero_days = "".join(
        f"<p>Keine Mieter-Einzelabrechnung für Mietverhältnis {escape(tenancy_id)}: null Nutzungstage im Abrechnungszeitraum.</p>"
        for tenancy_id in cast(list[str], owner["zero_day_tenancy_ids"])
    )
    notices = "".join(f"<li>{escape(note)}</li>" for note in cast(list[str], owner["notices"]))
    body = f"""
    <div class="document-meta"><div><strong>{escape(cast(str, owner["landlord_name"]))}</strong><br>{escape(cast(str, owner["building_name"]))}</div><div>Erstellt am {_snapshot_date(owner["created_on"]).strftime("%d.%m.%Y")}</div></div>
    <h1>Vermieterübersicht</h1><p>Abrechnungszeitraum: {period_start.strftime("%d.%m.%Y")} - {period_end.strftime("%d.%m.%Y")}</p>
    <section><h2>Kostenübersicht</h2><table><tr><th>Kostenart</th><th>Partei</th><th>Anteil</th></tr>{cost_rows}</table><h3>Heiz- und Warmwasserkosten</h3>{heating_summary_html}<table><tr><th>Partei</th><th>Heizung Grund</th><th>Heizung Verbrauch</th><th>Warmwasser Grund</th><th>Warmwasser Verbrauch</th><th>Gesamt</th></tr>{heating_rows}</table></section><section><h2>Finalisierungsnachweis</h2>{reconciliation}{zero_days}{_vacancy_html_from_snapshot(cast(dict[str, object], owner["vacancy"]))}</section>
    <section><h2>Hinweise</h2><ul>{notices}</ul></section><p class="muted">{escape(DISCLAIMER)}</p><p class="muted">Rechtsstand: {escape(", ".join(cast(list[str], owner["rechtsstaende"])))}</p>"""
    return _document_html(
        "Vermieterübersicht",
        body,
        production_blocked=bool(owner.get("production_blocked", False)),
    )


def _cover_letter_html_from_snapshot(tenant: dict[str, object], *, draft: bool = False) -> str:
    """A restrained business letter from already frozen statement fields."""
    address = cast(dict[str, object], tenant["address"])
    labels = {
        "RECHNERISCHER_SALDO": "Rechnerischer Saldo",
        "NACHZAHLUNG": "Nachzahlung",
        "GUTHABEN": "Guthaben",
        "SALDO": "Ausgeglichen",
    }
    branch = cast(str, tenant["saldo_branch"])
    amount = escape(format_eur(cents(abs(cast(int, tenant["saldo_cents"])))))
    instruction = escape(cast(str, tenant["instruction"]))
    body = f"""
    <div class="sender-line">{escape(cast(str, tenant["landlord_name"]))}</div>
    <div class="address">{escape(cast(str, address["addressee"]))}<br>{escape(cast(str, address["street"]))}<br>{escape(cast(str, address["postal_code"]))} {escape(cast(str, address["city"]))}<br>{escape(cast(str, address["country"]))}</div>
    <p style="text-align:right">{escape(cast(str, tenant["building_name"]))}, {_snapshot_date(tenant["created_on"]).strftime("%d.%m.%Y")}</p>
    <p class="subject">Betriebs- und Heizkostenabrechnung {_snapshot_date(tenant["period_end"]).year}</p>
    <p>Guten Tag {escape(cast(str, address["addressee"]))},</p>
    <p>anbei erhalten Sie Ihre Betriebs- und Heizkostenabrechnung für die Einheit {escape(cast(str, tenant["unit_label"]))} im Zeitraum {_snapshot_date(tenant["period_start"]).strftime("%d.%m.%Y")} - {_snapshot_date(tenant["period_end"]).strftime("%d.%m.%Y")}.</p>
    <div class="summary"><div class="summary-row"><span>{labels[branch]}</span><strong>{amount}</strong></div></div>
    {f"<p>{instruction}</p>" if instruction else ""}
    <p>Bitte bewahren Sie die beigefügten Unterlagen auf. Bei Rückfragen können Sie sich an den Absender wenden.</p>
    <p>Mit freundlichen Grüßen</p><p style="margin-top:10mm">{escape(cast(str, tenant["landlord_name"]))}</p>
    <p class="muted" style="margin-top:14mm">Anlage: Betriebs- und Heizkostenabrechnung {_snapshot_date(tenant["period_end"]).year}</p>
    <p class="muted">{escape(DISCLAIMER)}</p>
    """
    return _document_html(
        "Anschreiben zur Abrechnung",
        body,
        draft=draft,
        production_blocked=bool(tenant.get("production_blocked", False)),
    )


def _tenant_html_from_snapshot(tenant: dict[str, object], *, draft: bool = False) -> str:
    """Render one tenant archive solely from its selected JSON-safe payload."""
    address = cast(dict[str, object], tenant["address"])
    projection = cast(dict[str, object], tenant["projection"])
    rows = "".join(
        f"<tr><td>{escape(cast(str, row['label']))}</td><td>{escape(format_eur(cents(cast(int, row['total_cents']))))}</td><td>{escape(cast(str, row['allocation_label']))}<br>{escape(cast(str, row['allocation_explanation']))}</td><td>{escape(cast(str, row['numerator']))}</td><td>{escape(cast(str, row['denominator']))}</td><td>{escape(format_eur(cents(cast(int, row['share_cents']))))}</td></tr>"
        for row in cast(list[dict[str, object]], projection["nk_rows"])
    )
    heating = "".join(
        _heating_html_from_snapshot(row)
        for row in cast(list[dict[str, object]], projection["heating_rows"])
    )
    devices = "".join(
        f"<li>{escape(cast(str, row['device_id']))}: {escape(cast(str, row['room']))}; {escape(_decimal_de(_snapshot_decimal(row['opening']) if row['opening'] is not None else Decimal(0)))}–{escape(_decimal_de(_snapshot_decimal(row['closing']) if row['closing'] is not None else Decimal(0)))} {escape(cast(str, row['measurement_unit']))}; Faktor {escape(_decimal_de(_snapshot_decimal(row['valuation_factor'])))}; Ablesestatus: {'geschätzt' if row['estimated'] else 'abgelesen'}; Gründe: {escape(', '.join(cast(list[str], row['reading_reasons'])) or 'keine Angabe')}; Quellen: {escape(', '.join(cast(list[str], row['reading_sources'])) or 'keine Angabe')}; Nachweise: {escape(', '.join(cast(list[str], row['provenance_refs'])) or 'keine Angabe')}</li>"
        for row in cast(list[dict[str, object]], tenant["meter_evidence"])
    )
    notices = "".join(f"<li>{escape(note)}</li>" for note in cast(list[str], tenant["notices"]))
    labels = {
        "RECHNERISCHER_SALDO": "Rechnerischer Saldo",
        "NACHZAHLUNG": "Nachzahlung",
        "GUTHABEN": "Guthaben",
        "SALDO": "Saldo",
    }
    body = f"""
    <div class="document-meta"><div><strong>{escape(cast(str, tenant["building_name"]))}</strong><br>Einheit {escape(cast(str, tenant["unit_label"]))}</div><div>{escape(cast(str, address["addressee"]))}<br>Erstellt am {_snapshot_date(tenant["created_on"]).strftime("%d.%m.%Y")}</div></div>
    <h1>Betriebs- und Heizkostenabrechnung</h1>
    <p>Abrechnungszeitraum: {_snapshot_date(tenant["period_start"]).strftime("%d.%m.%Y")} - {_snapshot_date(tenant["period_end"]).strftime("%d.%m.%Y")}</p>
    <h2>Umlagefähige Kosten und Ihr Anteil</h2><table><thead><tr><th>Kostenart</th><th>Gesamtkosten</th><th>Umlageschlüssel</th><th>Ihre Bemessung</th><th>Gesamtbemessung</th><th>Anteil</th></tr></thead><tbody>{rows}</tbody></table><p class="muted">Berechnung je Kostenart: Anteil = Gesamtkosten x Ihre Bemessung / Gesamtbemessung.</p>
    {heating}<section><h2>Zählernachweise</h2><ul>{devices}</ul></section><section><h2>Hinweise</h2><ul>{notices}</ul></section>
    <div class="summary"><div class="summary-row"><span>Ihr Anteil gesamt</span><span>{escape(format_eur(cents(cast(int, tenant["subtotal_cents"]))))}</span></div><div class="summary-row"><span>Bestätigte Vorauszahlungen</span><span>{escape(format_eur(cents(cast(int, cast(dict[str, object], tenant["reconciliation"])["advances_cents"]))))}</span></div><div class="summary-row"><strong>{labels[cast(str, tenant["saldo_branch"])]}</strong><strong>{escape(format_eur(cents(cast(int, tenant["saldo_cents"]))))}</strong></div></div><p>{escape(cast(str, tenant["instruction"]))}</p><p class="muted">{escape(DISCLAIMER)}</p><p class="muted">Rechtsstand: {escape(", ".join(cast(list[str], tenant["rechtsstaende"])))}</p>"""
    return _document_html(
        "Betriebs- und Heizkostenabrechnung",
        body,
        draft=draft,
        production_blocked=bool(tenant.get("production_blocked", False)),
    )


def _heating_html_from_snapshot(row: dict[str, object]) -> str:
    line = cast(dict[str, object], row["line"])
    consumption_share = _snapshot_decimal(row["consumption_share"])
    heat_unit = {"KWH": "kWh", "CUBIC_METRE": "m³", "HKV_UNITS": "HKV-Einheiten"}.get(
        cast(str, row["heat_unit"]), "Verbrauch"
    )
    return f"""<section><h2>Heiz- und Warmwasserkosten</h2><h3>Block A — Kosten und CO₂</h3><p>Gesamtkosten: {escape(format_eur(cents(cast(int, row["total_cents"]))))}; abrechenbare Kosten: {escape(format_eur(cents(cast(int, row["billable_cents"]))))}; {escape(cast(str, row["co2_text"]))}.</p><h3>Block B — Kostenanteile und Umlageschlüssel</h3><p>Heizkosten: Grundkosten {escape(format_eur(cents(cast(int, row["heat_base_cents"]))))}, Verbrauchskosten {escape(format_eur(cents(cast(int, row["heat_consumption_cents"]))))}; Warmwasser: Grundkosten {escape(format_eur(cents(cast(int, row["ww_base_cents"]))))}, Verbrauchskosten {escape(format_eur(cents(cast(int, row["ww_consumption_cents"]))))}.</p><p>Angewandter Heizkosten-Schlüssel: {_decimal_de(consumption_share * Decimal(100))} % Verbrauch / {_decimal_de((Decimal(1) - consumption_share) * Decimal(100))} % Grundkosten; Flächenanteile nach m²·Tagen, Verbrauchsanteile nach abgelesenem Verbrauch (§§ 7–9 HeizkostenV).</p><p>Flächenbemessung: {_number_de(_snapshot_decimal(row["base_weight"]))} m²·Tage von {_number_de(_snapshot_decimal(row["base_denominator"]))} m²·Tage. Heizverbrauch: {_decimal_de(_snapshot_decimal(row["heat_weight"]))} {escape(heat_unit)} von {_decimal_de(_snapshot_decimal(row["heat_denominator"]))} {escape(heat_unit)}. Warmwasserverbrauch: {_decimal_de(_snapshot_decimal(row["ww_weight"]))} m³ von {_decimal_de(_snapshot_decimal(row["ww_denominator"]))} m³. Warmwassertrennung: {"zentral nach § 9 HeizkostenV" if row["warm_water_separation"] else "keine zentrale Warmwassertrennung"}.</p><h3>Block C — Ihr Anteil und Herleitung</h3><p>Heizung Grundkosten {escape(format_eur(cents(cast(int, line["heating_base_cents"]))))}; Heizung Verbrauchskosten {escape(format_eur(cents(cast(int, line["heating_consumption_cents"]))))}; Warmwasser Grundkosten {escape(format_eur(cents(cast(int, line["ww_base_cents"]))))}; Warmwasser Verbrauchskosten {escape(format_eur(cents(cast(int, line["ww_consumption_cents"]))))}.</p><p>Operator: Anteil = Kostenanteil × Bemessung ÷ Gesamtbemessung. Flächen-Numerator: {_number_de(_snapshot_decimal(row["base_weight"]) / Decimal(cast(int, line["days"])))} m² × {line["days"]} Tage = {_number_de(_snapshot_decimal(row["base_weight"]))} m²·Tage; Gradtagszahlen {_decimal_de(_snapshot_decimal(line["degree_day_promille"]))} ‰ ÷ {_decimal_de(_snapshot_decimal(line["unit_degree_day_promille_total"]))} ‰.</p></section>"""


@router.get("/statements/preview.pdf")
def preview_tenant_document(
    account_id: str,
    building_id: str,
    draft_id: str,
    tenancy_id: str,
    session: PathAccountSession,
    document_type: Literal["COVER_LETTER", "TENANT_STATEMENT"] = "TENANT_STATEMENT",
) -> Response:
    """Render one audience-selected draft document without archiving its bytes."""
    del account_id
    require_owner(session)
    building = require_building(session, building_id)
    draft = session.get(StatementDraft, draft_id)
    if draft is None or draft.building_id != building_id:
        raise HTTPException(status_code=404, detail="Abrechnungsentwurf nicht gefunden.")
    tenancy = session.get(Tenancy, tenancy_id)
    if tenancy is None or tenancy.unit.building_id != building_id:
        raise HTTPException(status_code=404, detail="Mietverhältnis nicht gefunden.")
    window = Period(draft.period_start, draft.period_end + timedelta(days=1))
    assert window.valid_to is not None
    if (
        overlap_days(
            Period(tenancy.valid_from, tenancy.valid_to), window.valid_from, window.valid_to
        )
        == 0
    ):
        raise HTTPException(
            status_code=422,
            detail="Das Mietverhältnis liegt nicht im Abrechnungszeitraum.",
        )
    try:
        bundle = compute_statement(session, building_id=building_id, window=window)
        projection = project_statement(
            bundle,
            StatementAudience.TENANT,
            tenancy_id=tenancy.id,
            allow_production_blocked=True,
        )
        owner_projection = project_statement(bundle, StatementAudience.OWNER)
        vacancy_projection = project_statement(bundle, StatementAudience.TAX)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail="Die Dokumentvorschau ist wegen unvollständiger Abrechnungsdaten blockiert.",
        ) from exc
    reconciliation = session.scalar(
        select(AdvanceReconciliation)
        .where(
            AdvanceReconciliation.tenancy_id == tenancy.id,
            AdvanceReconciliation.period_start == draft.period_start,
            AdvanceReconciliation.period_end == draft.period_end,
        )
        .order_by(AdvanceReconciliation.version.desc())
    )
    if reconciliation is None:
        raise HTTPException(status_code=422, detail="Vorauszahlungen sind noch nicht bestätigt.")
    subtotal = sum(int(line.amount) for line in projection.nk_lines) + sum(
        int(line.total) for line in projection.heating_lines
    )
    render = _final_render_payload(
        owner_projection=owner_projection,
        vacancy_projection=vacancy_projection,
        eligible=[
            (
                tenancy,
                projection,
                _address(session, tenancy.id, draft.period_end),
                reconciliation,
                subtotal,
                subtotal - reconciliation.total_cents,
            )
        ],
        instruction=_instruction(session, building_id, draft.period_end),
        landlord_name=(building.landlord.legal_name if building.landlord else "Vermieter"),
        building_name=building.name,
        period_start=draft.period_start,
        period_end=draft.period_end,
        zero_day_tenancy_ids=(),
        rechtsstaende=bundle.rechtsstand_entries,
        heating_result=bundle.heating_result,
        page01b_result=bundle.page01b_result,
        late_positive_exception_reason=None,
    )
    tenant = cast(list[dict[str, object]], render["tenants"])[0]
    tenant["production_blocked"] = bool(bundle.page02_production_blocked)
    html = (
        _cover_letter_html_from_snapshot(tenant, draft=True)
        if document_type == "COVER_LETTER"
        else _tenant_html_from_snapshot(tenant, draft=True)
    )
    pdf = render_html_to_pdf(html, _DOCUMENT_PDF_OPTIONS)
    filename = (
        f"entwurf-anschreiben-{tenancy.id}.pdf"
        if document_type == "COVER_LETTER"
        else f"entwurf-abrechnung-{tenancy.id}.pdf"
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post("/tenancies/{tenancy_id}/delivery-addresses", status_code=201)
def create_delivery_address(
    account_id: str,
    building_id: str,
    tenancy_id: str,
    body: DeliveryAddressCreate,
    session: PathAccountSession,
) -> dict[str, str]:
    require_owner(session)
    require_building(session, building_id)
    tenancy = session.get(Tenancy, tenancy_id)
    if tenancy is None or tenancy.unit.building_id != building_id:
        raise HTTPException(status_code=404, detail="Mietverhältnis nicht gefunden.")
    previous = session.scalar(
        select(DeliveryAddress.version)
        .where(DeliveryAddress.tenancy_id == tenancy_id)
        .order_by(DeliveryAddress.version.desc())
    )
    row = DeliveryAddress(
        id=new_id(),
        account_id=account_id,
        tenancy_id=tenancy_id,
        version=(previous + 1 if previous is not None else 1),
        addressee=body.addressee,
        street=body.street,
        postal_code=body.postal_code,
        city=body.city,
        country=body.country,
        valid_from=body.valid_from,
    )
    session.add(row)
    session.flush()
    return {"id": row.id}


@root_router.get("/buildings/{building_id}/tenancies/{tenancy_id}/delivery-addresses")
def list_delivery_addresses(
    account_id: str, building_id: str, tenancy_id: str, session: PathAccountSession
) -> list[dict[str, object]]:
    del account_id
    require_owner(session)
    require_building(session, building_id)
    tenancy = session.get(Tenancy, tenancy_id)
    if tenancy is None or tenancy.unit.building_id != building_id:
        raise HTTPException(status_code=404, detail="Mietverhältnis nicht gefunden.")
    return [
        {
            "id": row.id,
            "version": row.version,
            "addressee": row.addressee,
            "street": row.street,
            "postal_code": row.postal_code,
            "city": row.city,
            "country": row.country,
            "valid_from": row.valid_from,
        }
        for row in session.scalars(
            select(DeliveryAddress)
            .where(DeliveryAddress.tenancy_id == tenancy_id)
            .order_by(DeliveryAddress.version.desc())
        ).all()
    ]


@router.post("/payment-instructions", status_code=201)
def create_payment_instruction(
    account_id: str, building_id: str, body: PaymentInstructionCreate, session: PathAccountSession
) -> dict[str, str]:
    require_owner(session)
    require_building(session, building_id)
    previous = session.scalar(
        select(PaymentInstruction.version).order_by(PaymentInstruction.version.desc())
    )
    row = PaymentInstruction(
        id=new_id(),
        account_id=account_id,
        version=(previous + 1 if previous is not None else 1),
        instruction_text=f"Zahlung: {body.payment_text}\nGuthaben: {body.credit_text}",
        valid_from=body.valid_from,
    )
    session.add(row)
    session.flush()
    return {"id": row.id}


@root_router.get("/payment-credit-instructions")
def list_payment_credit_instructions(
    account_id: str, session: PathAccountSession
) -> list[dict[str, object]]:
    del account_id
    require_owner(session)
    return [
        {
            "id": row.id,
            "version": row.version,
            "instruction_text": row.instruction_text,
            "valid_from": row.valid_from,
        }
        for row in session.scalars(
            select(PaymentInstruction).order_by(PaymentInstruction.version.desc())
        ).all()
    ]


@root_router.post("/payment-credit-instructions", status_code=201)
def create_account_payment_credit_instruction(
    account_id: str, body: PaymentInstructionCreate, session: PathAccountSession
) -> dict[str, str]:
    require_owner(session)
    previous = session.scalar(
        select(PaymentInstruction.version).order_by(PaymentInstruction.version.desc())
    )
    row = PaymentInstruction(
        id=new_id(),
        account_id=account_id,
        version=(previous + 1 if previous is not None else 1),
        instruction_text=f"Zahlung: {body.payment_text}\nGuthaben: {body.credit_text}",
        valid_from=body.valid_from,
    )
    session.add(row)
    session.flush()
    return {"id": row.id}


@router.post("/statements/finalize", status_code=201)
def finalize_statement(
    account_id: str, building_id: str, body: FinalizeStatementCreate, session: PathAccountSession
) -> FinalizeStatementOut:
    require_owner(session)
    building = require_building(session, building_id)
    draft = session.get(StatementDraft, body.draft_id) if body.draft_id is not None else None
    if body.draft_id is not None and (
        draft is None
        or draft.building_id != building_id
        or draft.period_start != body.period_start
        or draft.period_end != body.period_end
    ):
        raise HTTPException(status_code=404, detail="Abrechnungsentwurf nicht gefunden.")
    if draft is not None and draft.version != body.draft_version:
        raise HTTPException(
            status_code=409,
            detail=(
                "Der Entwurf wurde an anderer Stelle geändert. "
                "Bitte laden Sie die aktuelle Fassung."
            ),
        )
    if draft is not None and draft.status != "READY":
        raise HTTPException(
            status_code=422,
            detail="Der Entwurf ist noch nicht bereit. Bitte lösen Sie zuerst alle Blocker.",
        )
    window = Period(valid_from=body.period_start, valid_to=body.period_end + timedelta(days=1))
    assert window.valid_to is not None
    try:
        bundle = compute_statement(session, building_id=building_id, window=window)
    except Exception as exc:  # calculation input errors are a no-write hard stop
        raise HTTPException(
            status_code=422, detail=f"Die Abrechnung kann nicht finalisiert werden: {exc}"
        ) from exc
    if bundle.heating_missing_reason:
        raise HTTPException(
            status_code=422,
            detail="Die Abrechnung enthält unvollständige Heizdaten.",
        )
    existing = session.scalars(
        select(Statement)
        .where(
            Statement.building_id == building_id,
            Statement.period_start == body.period_start,
            Statement.period_end == body.period_end,
        )
        .order_by(Statement.version.desc())
    ).all()
    latest = existing[0] if existing else None
    if latest is not None:
        if (
            body.supersedes_statement_id != latest.id
            or latest.status is not StatementStatus.FINALIZED
        ):
            raise HTTPException(
                status_code=422,
                detail="Eine Korrektur muss die jüngste finalisierte Version ausdrücklich benennen.",
            )
    elif body.supersedes_statement_id is not None:
        raise HTTPException(
            status_code=422,
            detail="Die benannte Vorgängerversion passt nicht zum Abrechnungszeitraum.",
        )

    eligible: list[
        tuple[Tenancy, StatementProjection, DeliveryAddress, AdvanceReconciliation, int, int]
    ] = []
    for unit in building.units:
        for tenancy in unit.tenancies:
            if (
                overlap_days(
                    Period(tenancy.valid_from, tenancy.valid_to), window.valid_from, window.valid_to
                )
                == 0
            ):
                continue
            reconciliation = session.scalar(
                select(AdvanceReconciliation)
                .where(
                    AdvanceReconciliation.tenancy_id == tenancy.id,
                    AdvanceReconciliation.period_start == body.period_start,
                    AdvanceReconciliation.period_end == body.period_end,
                )
                .order_by(AdvanceReconciliation.version.desc())
            )
            if reconciliation is None:
                raise HTTPException(
                    status_code=422,
                    detail="Für jedes Mietverhältnis fehlt eine bestätigte Vorauszahlungsabstimmung.",
                )
            try:
                projection = project_statement(
                    bundle,
                    StatementAudience.TENANT,
                    tenancy_id=tenancy.id,
                    allow_production_blocked=True,
                )
            except (EmptyTenancyError, StatementProductionBlockedError) as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            subtotal = sum(int(line.amount) for line in projection.nk_lines) + sum(
                int(line.total) for line in projection.heating_lines
            )
            eligible.append(
                (
                    tenancy,
                    projection,
                    _address(session, tenancy.id, body.period_end),
                    reconciliation,
                    subtotal,
                    subtotal - reconciliation.total_cents,
                )
            )
    instruction = _instruction(session, building_id, body.period_end)
    late_positive = date.today() > body.period_end.replace(year=body.period_end.year + 1)
    exception_reason = (
        body.late_positive_exception_reason.strip() or None
        if body.late_positive_exception_reason is not None
        else None
    )
    # Render every artifact before adding any persistent row: a renderer failure
    # leaves the surrounding transaction with no partial archive.
    landlord_name = building.landlord.legal_name if building.landlord else "Vermieter"
    zero_day_tenancies = [
        tenancy
        for unit in building.units
        for tenancy in unit.tenancies
        if overlap_days(
            Period(tenancy.valid_from, tenancy.valid_to), window.valid_from, window.valid_to
        )
        == 0
    ]
    owner_projection = project_statement(bundle, StatementAudience.OWNER)
    vacancy_projection = project_statement(bundle, StatementAudience.TAX)
    # Freeze the complete selected calculation and normalized final render
    # payload before rendering.  PDF generation only receives values read back
    # from this object, never a live ORM or calculation object.
    render_payload = _finalized_snapshot(
        bundle=bundle,
        owner_projection=owner_projection,
        vacancy_projection=vacancy_projection,
        eligible=eligible,
        instruction=instruction,
        exception_reason=exception_reason,
        landlord_name=landlord_name,
        building_name=building.name,
        period_start=body.period_start,
        period_end=body.period_end,
        zero_day_tenancy_ids=(tenancy.id for tenancy in zero_day_tenancies),
    )
    if draft is not None:
        render_payload["draft"] = {
            "id": draft.id,
            "version": draft.version,
            "title": draft.title,
            "selected_unit_ids": list(draft.selected_unit_ids),
            "overrides": dict(draft.overrides),
            "correction_reason": draft.correction_reason,
        }
    final_render = cast(dict[str, object], render_payload["final_render"])
    owner_pdf = render_html_to_pdf(_owner_html_from_snapshot(final_render), _DOCUMENT_PDF_OPTIONS)
    frozen_tenants = cast(list[dict[str, object]], final_render["tenants"])
    tenant_statement_pdfs = [
        render_html_to_pdf(_tenant_html_from_snapshot(tenant), _DOCUMENT_PDF_OPTIONS)
        for tenant in frozen_tenants
    ]
    cover_letter_pdfs = [
        render_html_to_pdf(_cover_letter_html_from_snapshot(tenant), _DOCUMENT_PDF_OPTIONS)
        for tenant in frozen_tenants
    ]
    statement = Statement(
        id=new_id(),
        account_id=account_id,
        building_id=building_id,
        period_start=body.period_start,
        period_end=body.period_end,
        version=(latest.version + 1 if latest else 1),
        status=StatementStatus.FINALIZED,
        total_cents=sum(x[4] for x in eligible),
        content_hash=sha256(owner_pdf).hexdigest(),
        finalized_at=datetime.now(),
        supersedes_statement_id=(latest.id if latest else None),
        finalized_snapshot=render_payload,
    )
    session.add(statement)
    session.flush()
    archives = [
        StatementArchive(
            id=new_id(),
            account_id=account_id,
            statement_id=statement.id,
            audience="OWNER",
            tenancy_id=None,
            document_type="OWNER_OVERVIEW",
            content_bytes=owner_pdf,
            sha256=sha256(owner_pdf).hexdigest(),
            mime_type="application/pdf",
            filename=f"abrechnung-v{statement.version}-vermieter.pdf",
        )
    ]
    for (tenancy, _, _, _, _, _), cover_pdf, statement_pdf in zip(
        eligible, cover_letter_pdfs, tenant_statement_pdfs, strict=True
    ):
        archives.extend(
            (
                StatementArchive(
                    id=new_id(),
                    account_id=account_id,
                    statement_id=statement.id,
                    audience="TENANT",
                    tenancy_id=tenancy.id,
                    document_type="COVER_LETTER",
                    content_bytes=cover_pdf,
                    sha256=sha256(cover_pdf).hexdigest(),
                    mime_type="application/pdf",
                    filename=f"anschreiben-v{statement.version}-{tenancy.id}.pdf",
                ),
                StatementArchive(
                    id=new_id(),
                    account_id=account_id,
                    statement_id=statement.id,
                    audience="TENANT",
                    tenancy_id=tenancy.id,
                    document_type="TENANT_STATEMENT",
                    content_bytes=statement_pdf,
                    sha256=sha256(statement_pdf).hexdigest(),
                    mime_type="application/pdf",
                    filename=f"abrechnung-v{statement.version}-{tenancy.id}.pdf",
                ),
            )
        )
    session.add_all(archives)
    session.add_all(
        StatementSettlement(
            id=new_id(),
            account_id=account_id,
            statement_id=statement.id,
            tenancy_id=t.id,
            amount_cents=abs(saldo),
            origin_saldo_cents=saldo,
            kind=("RECEIVABLE" if saldo > 0 else "CREDIT_REFUND"),
            late_positive_exception_reason=(
                exception_reason if late_positive and saldo > 0 else None
            ),
        )
        for t, _, _, _, _, saldo in eligible
        if saldo != 0 and not (late_positive and saldo > 0 and exception_reason is None)
    )
    if latest is not None:
        latest.status = StatementStatus.SUPERSEDED
    if draft is not None:
        draft.status = "FINALIZED"
        draft.final_statement_id = statement.id
        draft.current_step = 6
        draft.version += 1
        draft.updated_at = datetime.now()
    session.flush()
    result = _history(session, statement)
    settlements = session.scalars(
        select(StatementSettlement).where(StatementSettlement.statement_id == statement.id)
    ).all()
    return FinalizeStatementOut(
        **result.model_dump(),
        settlements=[
            {"tenancy_id": row.tenancy_id, "saldo_cents": row.origin_saldo_cents, "kind": row.kind}
            for row in settlements
        ],
    )


@router.get("/statements/history")
def statement_history(
    account_id: str, building_id: str, session: PathAccountSession
) -> list[StatementHistoryOut]:
    del account_id
    require_owner(session)
    require_building(session, building_id)
    return [
        _history(session, row)
        for row in session.scalars(
            select(Statement)
            .where(Statement.building_id == building_id)
            .order_by(Statement.period_start.desc(), Statement.version.desc())
        ).all()
    ]


@router.get("/statements/{statement_id}/documents/{document_id}")
def download_archived_document(
    account_id: str,
    building_id: str,
    statement_id: str,
    document_id: str,
    session: PathAccountSession,
) -> Response:
    del account_id
    require_owner(session)
    require_building(session, building_id)
    row = session.scalar(
        select(StatementArchive)
        .join(Statement)
        .where(
            StatementArchive.id == document_id,
            StatementArchive.statement_id == statement_id,
            Statement.building_id == building_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Archivdokument nicht gefunden.")
    return Response(
        content=row.content_bytes,
        media_type=row.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{row.filename}"',
            "X-Content-SHA256": row.sha256,
        },
    )


@root_router.get("/statement-documents/{document_id}/download")
def download_archived_document_by_id(
    account_id: str, document_id: str, session: PathAccountSession
) -> Response:
    del account_id
    require_owner(session)
    row = session.get(StatementArchive, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Archivdokument nicht gefunden.")
    return Response(
        content=row.content_bytes,
        media_type=row.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{row.filename}"',
            "X-Content-SHA256": row.sha256,
        },
    )
