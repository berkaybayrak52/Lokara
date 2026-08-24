"""Pure Anlage-V aggregation, readiness and deterministic encoders."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class TaxEventSource(StrEnum):
    FINAPI = "finapi"
    MANUELL = "manuell"
    RECHNUNG = "rechnung"


@dataclass(frozen=True)
class TaxEvent:
    event_id: str
    account_id: str
    building_id: str
    unit_id: str | None
    payment_date: date | None
    due_date: date | None
    amount_cents: int
    direction: str
    category: str | None
    receipt_reference: str
    source: TaxEventSource
    version: int

    def __post_init__(self) -> None:
        if self.version <= 0:
            raise ValueError("version must be positive")
        if self.amount_cents <= 0:
            raise ValueError("amount_cents must be positive")
        if self.direction not in {"einnahme", "ausgabe"}:
            raise ValueError("direction must be einnahme or ausgabe")


@dataclass(frozen=True, order=True)
class ReadinessFinding:
    severity: str
    code: str
    finding_id: str = ""


@dataclass(frozen=True)
class ExportReadinessResult:
    findings: tuple[ReadinessFinding, ...]
    generated_at: datetime
    rechtsstand: str
    production_blocked: bool
    acknowledgements: tuple[dict[str, object], ...] = ()
    chosen_year_overrides: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True)
class AnlageVOverview:
    generated_at: datetime
    rechtsstand: str
    production_blocked: bool
    tax_year: int
    income_total_cents: int
    cash_cost_total_cents: int
    advertising_cost_total_cents: int
    result_cents: int
    advance_income_adjustment_cents: int
    event_components: dict[str, dict[str, int]]
    anlage_v_effect_by_event: dict[str, int]
    account_by_event: dict[str, str]
    findings: tuple[ReadinessFinding, ...]
    exported_categories: tuple[str, ...]
    source_evidence: tuple[str, ...]


@dataclass(frozen=True)
class FixtureTrace:
    fixture_id: str
    source: str
    expected_values_consumed: bool
    source_evidence: tuple[str, ...]


READINESS_FINDING_CODES = (
    "datev_without_adviser_or_client_number",
    "expected_rent_gap",
    "missing_selected_account",
    "no_payment_data_in_requested_period",
    "object_without_afa_record",
    "payment_without_category",
    "payment_without_date",
    "unconfirmed_interest_proposal",
    "unmatched_party",
    "unresolved_year_window",
    "vat_case_detected",
)


def _date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError("payment date must be ISO text or a date")


def _window(value: date) -> bool:
    return (value.month == 12 and value.day >= 22) or (value.month == 1 and value.day <= 10)


def assign_tax_year(payment: Mapping[str, object] | object) -> int:
    def field(name: str, default: object = None) -> object:
        if isinstance(payment, Mapping):
            return payment.get(name, default)
        return getattr(payment, name, default)

    paid = _date(field("payment_date", field("datum")))
    due_value = field("due_date", field("faelligkeitsdatum"))
    if bool(field("recurring", False)) and due_value is not None:
        due = _date(due_value)
        if _window(paid) and _window(due):
            return due.year
    return paid.year


def _evidence(rows: object) -> tuple[str, ...]:
    values: set[str] = set()
    if isinstance(rows, tuple):
        for row in rows:
            if isinstance(row, tuple):
                values.update(
                    str(row[index]) for index in (5, 6, 8) if len(row) > index and row[index]
                )
    return tuple(sorted(values))


def _rechtsstand(rows: object) -> str:
    if isinstance(rows, tuple):
        values = {str(row[8]) for row in rows if isinstance(row, tuple) and len(row) > 8}
        if len(values) == 1:
            return values.pop()
    return "unbekannt"


def _finding(severity: str, code: str, event_id: str = "") -> ReadinessFinding:
    return ReadinessFinding(severity=severity, code=code, finding_id=event_id)


def _event_id(event: Mapping[str, object]) -> str:
    return str(event.get("event_id", event.get("paymentId", "")))


def _integer(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    return value


def _selected_account(entry: Mapping[str, object], account_chart: object) -> str | None:
    if account_chart in {"skr03", "skr04"}:
        account = entry.get(f"{account_chart}_account")
        if account:
            return str(account)
    account = entry.get("account")
    return str(account) if account else None


def _semantic_findings(
    events: Sequence[Mapping[str, object]],
    *,
    afa_record: Mapping[str, object] | None,
    adviser_profile: Mapping[str, object] | None,
    mapping: Sequence[Mapping[str, object]],
    export_kind: str,
    chosen_year_overrides: Sequence[Mapping[str, object]] = (),
) -> tuple[ReadinessFinding, ...]:
    findings: list[ReadinessFinding] = []
    mapped = {str(item.get("category")): item for item in mapping}
    account_chart = adviser_profile.get("kontenrahmen") if adviser_profile is not None else None
    if not events:
        findings.append(_finding("rot", "no_payment_data_in_requested_period"))
    overridden_ids = {str(item.get("event_id")) for item in chosen_year_overrides}
    for event in events:
        event_id = _event_id(event)
        if event.get("payment_date") is None:
            findings.append(_finding("rot", "payment_without_date", event_id))
        category = event.get("category")
        if category is None:
            findings.append(_finding("gelb", "payment_without_category", event_id))
        elif str(category) not in {"rent_collection", "kaution", "nk_guthaben"}:
            entry = mapped.get(str(category))
            if entry is None or _selected_account(entry, account_chart) is None:
                findings.append(_finding("gelb", "missing_selected_account", event_id))
        if event.get("party_matched") is False:
            findings.append(_finding("gelb", "unmatched_party", event_id))
        if (
            bool(event.get("recurring", False))
            and event.get("due_date") is None
            and event.get("payment_date") is not None
            and _window(_date(event["payment_date"]))
            and event_id not in overridden_ids
        ):
            findings.append(_finding("gelb", "unresolved_year_window", event_id))
        expected_amount = event.get("expected_amount_cents")
        if expected_amount is not None and expected_amount != event.get("amount_cents"):
            findings.append(_finding("gelb", "expected_rent_gap", event_id))
        if bool(event.get("vat_case", False)):
            findings.append(_finding("gelb", "vat_case_detected", event_id))
    if afa_record is None:
        findings.append(_finding("gelb", "object_without_afa_record"))
    elif _integer(afa_record.get("zinsAbziehbarCent", 0), "zinsAbziehbarCent") and not bool(
        afa_record.get("zinsBestaetigt", False)
    ):
        findings.append(_finding("gelb", "unconfirmed_interest_proposal"))
    if export_kind == "datev_extf" and (
        adviser_profile is None
        or not adviser_profile.get("beraternummer")
        or not adviser_profile.get("mandantennummer")
    ):
        findings.append(_finding("rot", "datev_without_adviser_or_client_number"))
    return tuple(sorted(findings, key=lambda item: (item.severity, item.code, item.finding_id)))


def evaluate_export_readiness(
    *,
    ledger_events: Sequence[Mapping[str, object]],
    afa_record: Mapping[str, object] | None,
    adviser_profile: Mapping[str, object] | None,
    mapping: Sequence[Mapping[str, object]],
    export_kind: str,
    tax_year: int,
    generated_at: datetime,
    register_rows: object = (),
    extf_profile: Mapping[str, object] | None = None,
    resolved_rules: Mapping[str, object] | None = None,
    acknowledgements: Sequence[Mapping[str, object]] = (),
    chosen_year_overrides: Sequence[Mapping[str, object]] = (),
) -> ExportReadinessResult:
    del tax_year
    findings = _semantic_findings(
        ledger_events,
        afa_record=afa_record,
        adviser_profile=adviser_profile,
        mapping=mapping,
        export_kind=export_kind,
        chosen_year_overrides=chosen_year_overrides,
    )
    mapping_blocked = any(
        item.get("verification_flag") == "verify-before-production" for item in mapping
    )
    rules = resolved_rules or {}
    profile = extf_profile or {}
    rechtsstand = str(rules.get("rechtsstand", _rechtsstand(register_rows)))
    return ExportReadinessResult(
        findings=findings,
        generated_at=generated_at,
        rechtsstand=rechtsstand,
        production_blocked=(
            mapping_blocked
            or bool(rules.get("production_blocked", profile.get("production_blocked", True)))
            or any(item.severity == "rot" for item in findings)
        ),
        acknowledgements=tuple(dict(item) for item in acknowledgements),
        chosen_year_overrides=tuple(dict(item) for item in chosen_year_overrides),
    )


def _rent_components(event: Mapping[str, object]) -> dict[str, int]:
    amount = _integer(event["amount_cents"], "amount_cents")
    cold_due = _integer(event.get("cold_rent_due_cents", 0), "cold_rent_due_cents")
    advance_due = _integer(event.get("nk_advance_due_cents", 0), "nk_advance_due_cents")
    cold = min(amount, cold_due)
    advance = min(max(0, amount - cold), advance_due)
    return {
        "kaltmiete": cold,
        "nk_vorauszahlung": advance,
        "mieter_guthaben": amount - cold - advance,
    }


def build_anlage_v_overview(
    *,
    ledger_events: Sequence[Mapping[str, object]],
    afa_handoff: Mapping[str, object],
    mapping: Sequence[Mapping[str, object]],
    account_chart: str = "skr03",
    tax_year: int,
    generated_at: datetime,
    register_rows: object,
) -> AnlageVOverview:
    mapped = {str(item.get("category")): item for item in mapping}
    income = 0
    cash_cost = 0
    advance_adjustment = 0
    components: dict[str, dict[str, int]] = {}
    effects: dict[str, int] = {}
    accounts: dict[str, str] = {}
    categories: set[str] = set()
    for event in ledger_events:
        payment_date = event.get("payment_date", event.get("datum"))
        if payment_date is None or assign_tax_year(event) != tax_year:
            continue
        event_id = _event_id(event)
        category = event.get("category")
        amount = _integer(event["amount_cents"], "amount_cents")
        direction = str(event["direction"])
        if category == "rent_collection":
            split = _rent_components(event)
            components[event_id] = split
            income += split["kaltmiete"] + split["nk_vorauszahlung"]
            categories.update(
                key for key, value in split.items() if value and key != "mieter_guthaben"
            )
            effects[event_id] = split["kaltmiete"] + split["nk_vorauszahlung"]
        elif category == "kaution":
            effects[event_id] = 0
        elif category == "nk_guthaben" and direction == "ausgabe":
            income -= amount
            advance_adjustment -= amount
            effects[event_id] = -amount
            categories.add("nk_guthaben")
        elif category in {"kaltmiete", "nk_vorauszahlung"} and direction == "ausgabe":
            income -= amount
            effects[event_id] = -amount
            categories.add(str(category))
        elif direction == "einnahme":
            income += amount
            effects[event_id] = amount
            if category is not None:
                categories.add(str(category))
        else:
            cash_cost += amount
            effects[event_id] = -amount
            if category is not None:
                categories.add(str(category))
        if category is not None and str(category) in mapped:
            account = _selected_account(mapped[str(category)], account_chart)
            if account:
                accounts[event_id] = account

    afa = _integer(afa_handoff.get("afaAbziehbarCent", 0), "afaAbziehbarCent")
    interest = _integer(afa_handoff.get("zinsAbziehbarCent", 0), "zinsAbziehbarCent")
    if afa:
        categories.add("afa")
    if interest:
        categories.add("schuldzinsen")
    advertising = cash_cost + afa + interest
    findings = list(
        _semantic_findings(
            tuple(
                event
                for event in ledger_events
                if event.get("payment_date", event.get("datum")) is not None
                and assign_tax_year(event) == tax_year
            ),
            afa_record=afa_handoff if afa_handoff else None,
            adviser_profile={},
            mapping=mapping,
            export_kind="anlage_v",
        )
    )
    if interest and not bool(afa_handoff.get("zinsBestaetigt", False)):
        findings.append(_finding("gelb", "unconfirmed_interest_proposal"))
    return AnlageVOverview(
        generated_at=generated_at,
        rechtsstand=_rechtsstand(register_rows),
        production_blocked=True,
        tax_year=tax_year,
        income_total_cents=income,
        cash_cost_total_cents=cash_cost,
        advertising_cost_total_cents=advertising,
        result_cents=income - advertising,
        advance_income_adjustment_cents=advance_adjustment,
        event_components=components,
        anlage_v_effect_by_event=effects,
        account_by_event=accounts,
        findings=tuple(
            sorted(findings, key=lambda item: (item.severity, item.code, item.finding_id))
        ),
        exported_categories=tuple(sorted(categories - {"disagio", "erhaltungsaufwand"})),
        source_evidence=_evidence(register_rows),
    )


def trace_approved_fixture(*, fixture_id: str, source: str, register_rows: object) -> FixtureTrace:
    return FixtureTrace(
        fixture_id=fixture_id,
        source=source,
        expected_values_consumed=False,
        source_evidence=_evidence(register_rows),
    )


def _csv_bytes(
    headers: Iterable[Sequence[object]],
    columns: Sequence[object],
    rows: Iterable[Sequence[object]],
    *,
    encoding: str,
    delimiter: str,
    line_ending: str,
) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(
        stream,
        delimiter=delimiter,
        quotechar='"',
        quoting=csv.QUOTE_ALL,
        lineterminator=line_ending,
    )
    writer.writerows(headers)
    writer.writerow(columns)
    writer.writerows(rows)
    return stream.getvalue().encode(encoding)


def _overview_value(overview: Mapping[str, object] | AnlageVOverview, name: str) -> object:
    return overview.get(name) if isinstance(overview, Mapping) else getattr(overview, name, None)


def encode_anlage_v_csv(
    *,
    overview: Mapping[str, object] | AnlageVOverview,
    layout: Mapping[str, object],
    generated_at: datetime,
) -> bytes:
    columns = ("Kennzahl", "Betrag Cent", "Erzeugt am")
    rows = tuple(
        (label, _overview_value(overview, field), generated_at.isoformat())
        for label, field in (
            ("Einnahmen", "income_total_cents"),
            ("Werbungskosten", "advertising_cost_total_cents"),
            ("Ergebnis", "result_cents"),
        )
    )
    return _csv_bytes(
        (("Formjahr", layout.get("tax_year", _overview_value(overview, "tax_year"))),),
        columns,
        rows,
        encoding="windows-1252",
        delimiter=";",
        line_ending="\r\n",
    )


def encode_datev_extf(
    *,
    ledger_events: Sequence[Mapping[str, object]],
    overview: Mapping[str, object] | AnlageVOverview,
    mapping: Sequence[Mapping[str, object]],
    adviser_profile: Mapping[str, object],
    extf_profile: Mapping[str, object],
    generated_at: datetime,
) -> bytes:
    if extf_profile.get("production_blocked", False):
        raise ValueError("production export is blocked")
    if extf_profile.get("verification_flag") != "verified-test-only":
        raise ValueError("EXTF profile is not verified for test encoding")
    if extf_profile.get("official_datev_profile") is not False:
        raise ValueError("test encoding must not claim an official DATEV profile")
    if any(
        _integer(_overview_value(overview, key) or 0, key)
        for key in ("disagioAbziehbarCent", "erhaltungsaufwandCent")
    ):
        raise ValueError("Disagio or maintenance mapping is unresolved and blocked")
    header = extf_profile.get("header", ("EXTF-TEST", generated_at.isoformat()))
    columns = extf_profile.get("columns", ("Betrag", "Belegdatum", "Belegfeld 1", "Buchungstext"))
    if not isinstance(header, Sequence) or isinstance(header, (str, bytes)):
        raise TypeError("header must be a sequence")
    if not isinstance(columns, Sequence) or isinstance(columns, (str, bytes)):
        raise TypeError("columns must be a sequence")
    account_chart = adviser_profile.get("kontenrahmen", "skr03")
    mapped = {str(item.get("category")): item for item in mapping}
    rows: list[tuple[object, ...]] = []
    for event in sorted(
        ledger_events,
        key=lambda item: (
            str(item.get("payment_date", "")),
            _event_id(item),
            _integer(item.get("version", 1), "version"),
        ),
    ):
        category = str(event.get("category", ""))
        entry = mapped.get(category)
        if entry is None or _selected_account(entry, account_chart) is None:
            continue
        amount = _integer(event["amount_cents"], "amount_cents")
        amount_text = f"{amount // 100},{amount % 100:02d}"
        payment_date = _date(event["payment_date"])
        booking_text = str(
            event.get(
                "booking_text",
                f"{category} {event.get('unit_id') or 'Objekt'} {payment_date.year}",
            )
        )
        rows.append(
            (
                amount_text,
                payment_date.strftime("%d%m"),
                str(event.get("receipt_reference", _event_id(event))),
                booking_text,
            )
        )
    return _csv_bytes(
        (header,),
        columns,
        rows,
        encoding=str(extf_profile.get("encoding", "windows-1252")),
        delimiter=str(extf_profile.get("delimiter", ";")),
        line_ending=str(extf_profile.get("line_ending", "\r\n")),
    )


__all__ = [
    "READINESS_FINDING_CODES",
    "AnlageVOverview",
    "ExportReadinessResult",
    "FixtureTrace",
    "ReadinessFinding",
    "TaxEvent",
    "TaxEventSource",
    "assign_tax_year",
    "build_anlage_v_overview",
    "encode_anlage_v_csv",
    "encode_datev_extf",
    "evaluate_export_readiness",
    "trace_approved_fixture",
]
