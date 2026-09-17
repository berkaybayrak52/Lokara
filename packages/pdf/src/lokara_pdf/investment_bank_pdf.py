"""Deterministic Bank-PDF view over frozen investment snapshots."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from html import escape
from typing import cast

from .render import PdfOptions, render_html_to_pdf

_BLOCKS = (
    "header_disclosure",
    "investment",
    "financing_ltv",
    "rent_and_planning_costs",
    "seven_kpis",
    "sensitivity",
    "twelve_month_schedule",
    "assumptions_method",
    "disclosure",
)
_ARTIFACT_DISCLOSURE = (
    "Vom Vermieter erstellte Zusammenfassung auf Basis eigener Angaben und Annahmen. "
    "Keine Immobilienbewertung, kein Beleihungswert, kein Gutachten, keine Bonitätsauskunft."
)
_DISCLAIMER = "rechtskonform, keine Rechts- oder Steuerberatung"
_LTV_LABEL = "Auslauf zum Kaufpreis, nicht zum Beleihungswert"
_MISSING = "—"

DEFAULT_BANK_LAYOUT_SNAPSHOT: dict[str, object] = {
    "schema_version": "investment-bank-pdf-v1",
    "locale": "de-DE",
    "format": "A4",
    "blocks": list(_BLOCKS),
    "artifact_disclosure": _ARTIFACT_DISCLOSURE,
    "product_disclaimer": _DISCLAIMER,
    "ltv_label": _LTV_LABEL,
    "missing_value": _MISSING,
}


@dataclass(frozen=True, slots=True)
class InvestmentBankPdfData:
    """The complete frozen render boundary; no live rule or domain input is accepted."""

    case_key: str
    input_version: int
    result_id: str
    engine_version: str
    layout_version_id: str
    bank_view: dict[str, object]
    result_snapshot: dict[str, object]
    layout_snapshot: dict[str, object]


def _mapping(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def _sequence(value: object) -> list[object]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _number(value: int | str | None, divisor: int = 1, digits: int = 0) -> str:
    if value is None or value == _MISSING or not isinstance(value, int):
        return _MISSING
    scaled = Decimal(value) / Decimal(divisor)
    rendered = f"{scaled:,.{digits}f}"
    return rendered.replace(",", "\0").replace(".", ",").replace("\0", ".")


def _money(value: object) -> str:
    if not isinstance(value, int):
        return _MISSING
    return f"{_number(value, 100, 2)}\u202f€"


def _percent(value: object) -> str:
    if not isinstance(value, int):
        return _MISSING
    return f"{_number(value, 100, 2)} %"


def _export_date(value: object) -> str:
    if not isinstance(value, str):
        return _MISSING
    try:
        return date.fromisoformat(value).strftime("%d.%m.%Y")
    except ValueError:
        return value


def _hundredths(value: object) -> str:
    return _number(value if isinstance(value, int) else None, 100, 2)


def _row(label: str, value: str) -> str:
    return f'<tr><th scope="row">{escape(label)}</th><td>{escape(value)}</td></tr>'


def _section(block: str, heading: str, content: str) -> str:
    return (
        f'<section class="block" data-bank-pdf-block="{block}">'
        f"<h2>{escape(heading)}</h2>{content}</section>"
    )


def _kpi_value(key: str, slot: dict[str, object]) -> str:
    if slot.get("status") == "not_applicable":
        value = slot.get("value")
        return value if isinstance(value, str) else _MISSING
    if slot.get("status") != "available":
        return _MISSING
    if key == "factor":
        return _hundredths(slot.get("value"))
    if key in {"gross_yield", "net_yield"}:
        return _percent(slot.get("value"))
    if key == "dscr":
        return _hundredths(slot.get("value"))
    if key == "equity_return":
        before = _percent(slot.get("before_tax"))
        after = _percent(slot.get("after_tax"))
        return f"vor Steuer {before} · nach Steuer {after}"
    if key == "cashflow":
        before = _money(slot.get("before_tax"))
        after = _money(slot.get("after_tax"))
        return f"vor Steuer {before} · nach Steuer {after}"
    if key == "break_even":
        before = _money(slot.get("before_tax"))
        after = _money(slot.get("after_tax"))
        return f"vor Steuer {before} · nach Steuer {after}"
    return _MISSING


def _table(headers: tuple[str, ...], rows: Sequence[tuple[str, ...]], label: str) -> str:
    head = "".join(f'<th scope="col">{escape(item)}</th>' for item in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>" for row in rows
    )
    return (
        f'<table aria-label="{escape(label)}"><thead><tr>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table>"
    )


def investment_bank_pdf_html(data: InvestmentBankPdfData) -> str:
    """Render only the supplied snapshots; no arithmetic or live lookup occurs here."""

    layout_blocks = tuple(str(value) for value in _sequence(data.layout_snapshot.get("blocks")))
    if layout_blocks != _BLOCKS:
        raise ValueError("Die gespeicherte PDF-Vorlage hat eine unbekannte Blockreihenfolge.")
    view = data.bank_view
    header = _mapping(_mapping(view.get("header_disclosure")).get("header"))
    investment = _mapping(view.get("investment"))
    financing = _mapping(view.get("financing_ltv"))
    rent = _mapping(view.get("rent_and_planning_costs"))
    kpis = _mapping(view.get("seven_kpis"))
    sensitivity = _mapping(view.get("sensitivity"))
    assumptions = _mapping(view.get("assumptions_method"))
    area = header.get("area_sqm_x100")
    no_debt = isinstance(financing.get("loan_cents"), int) and financing.get("loan_cents") == 0

    header_rows = "".join(
        (
            _row("Objekt", str(header.get("address", _MISSING))),
            _row("Objektart", str(header.get("property_type", _MISSING))),
            _row("Baujahr", str(header.get("year_built", _MISSING))),
            _row(
                "Fläche",
                f"{_number(area, 100, 2)} m²" if isinstance(area, int) else _MISSING,
            ),
            _row("Einheiten", str(header.get("unit_count", _MISSING))),
            _row("Erstellt von", str(header.get("creator", _MISSING))),
            _row("Exportdatum", _export_date(header.get("export_date"))),
            _row("Vorlage", str(header.get("layout_version", _MISSING))),
        )
    )
    header_html = (
        '<h1>Investitionsübersicht</h1><table class="facts"><tbody>'
        f"{header_rows}</tbody></table>"
        f'<p class="notice">{escape(str(data.layout_snapshot["artifact_disclosure"]))}</p>'
    )
    investment_html = (
        '<table class="facts"><tbody>'
        + "".join(
            (
                _row("Kaufpreis", _money(investment.get("purchase_price_cents"))),
                _row("Erwerbsnebenkosten", _money(investment.get("acquisition_costs_cents"))),
                _row("Gesamtinvestition", _money(investment.get("total_investment_cents"))),
            )
        )
        + "</tbody></table>"
    )
    provenance = _mapping(financing.get("provenance"))
    financing_html = (
        '<table class="facts"><tbody>'
        + "".join(
            (
                _row("Eigenkapital", _money(financing.get("equity_cents"))),
                _row("Darlehen", _money(financing.get("loan_cents"))),
                _row("Sollzins", _percent(financing.get("interest_bp"))),
                _row("Anfängliche Tilgung", _percent(financing.get("initial_repayment_bp"))),
                _row("Monatliche Annuität", _money(financing.get("monthly_annuity_cents"))),
                _row("Auslauf Kaufpreis", _percent(financing.get("ltv_purchase_bp"))),
                _row("Auslauf Gesamtinvestition", _percent(financing.get("ltv_total_bp"))),
            )
        )
        + "</tbody></table>"
    )
    financing_html += (
        f"<p>{escape(str(financing.get('ltv_label', data.layout_snapshot['ltv_label'])))}</p>"
    )
    if isinstance(financing.get("loan_cents"), int) and financing.get("ltv_note"):
        financing_html += f'<p class="notice">{escape(str(financing["ltv_note"]))}</p>'
    if not isinstance(financing.get("loan_cents"), int):
        financing_html += '<p class="notice">Finanzierungsdaten fehlen – Daten unvollständig.</p>'
    if provenance.get("badge"):
        financing_html += f'<p class="badge">{escape(str(provenance["badge"]))}</p>'
    rent_html = (
        '<table class="facts"><tbody>'
        + "".join(
            (
                _row("Ist-Kaltmiete monatlich", _money(rent.get("monthly_actual_rent_cents"))),
                _row("Leerstand", _percent(rent.get("vacancy_bp"))),
                _row("Verwaltung", _money(rent.get("administration_cents"))),
                _row("Instandhaltung", _money(rent.get("maintenance_cents"))),
                _row("Rücklage", _money(rent.get("reserve_cents"))),
                _row("Mietausfallrisiko", _money(rent.get("vacancy_risk_cents"))),
            )
        )
        + "</tbody></table>"
    )

    kpi_labels = (
        ("factor", "Kaufpreisfaktor"),
        ("gross_yield", "Bruttomietrendite"),
        ("net_yield", "Nettomietrendite"),
        ("dscr", "DSCR"),
        ("equity_return", "Eigenkapitalrendite"),
        ("cashflow", "Cashflow monatlich"),
        ("break_even", "Break-Even-Miete monatlich"),
    )
    unavailable = any(
        _mapping(kpis.get(key)).get("status") not in {"available", "not_applicable"}
        for key, _ in kpi_labels
    )
    kpi_html = (
        '<table class="facts"><tbody>'
        + "".join(
            _row(label, _kpi_value(key, _mapping(kpis.get(key)))) for key, label in kpi_labels
        )
        + "</tbody></table>"
    )
    if unavailable:
        kpi_html += '<p class="notice">Daten unvollständig</p>'

    interest_rows = [
        (
            _percent(item.get("interest_bp")),
            _hundredths(item.get("dscr_hundredths")),
            _money(item.get("cashflow_after_month_cents")),
        )
        for item in (_mapping(value) for value in _sequence(sensitivity.get("interest")))
    ]
    repayment_rows = [
        (
            _percent(item.get("initial_repayment_bp")),
            _hundredths(item.get("dscr_hundredths")),
            _money(item.get("cashflow_after_month_cents")),
            _money(item.get("closing_balance_cents")),
        )
        for item in (_mapping(value) for value in _sequence(sensitivity.get("repayment")))
    ]
    sensitivity_html = "<h3>Zins-Stresstest</h3>" + _table(
        ("Sollzins", "DSCR", "Cashflow nach Steuer/Monat"), interest_rows, "Zinssensitivität"
    )
    sensitivity_html += "<h3>Tilgungsstruktur</h3>" + _table(
        ("Tilgung", "DSCR", "Cashflow nach Steuer/Monat", "Restschuld"),
        repayment_rows,
        "Tilgungssensitivität",
    )
    schedule_rows: list[tuple[str, ...]] = []
    for index, raw in enumerate(_sequence(view.get("twelve_month_schedule")), start=1):
        if not isinstance(raw, (list, tuple)) or len(raw) != 4:
            continue
        row = list(raw)
        schedule_rows.append(
            (str(index), _money(row[0]), _money(row[1]), _money(row[2]), _money(row[3]))
        )
    schedule_html = _table(
        ("Monat", "Anfangsschuld", "Zins", "Tilgung", "Restschuld"),
        schedule_rows,
        "Annuitätenplan Jahr 1",
    )
    if no_debt:
        sensitivity_html = (
            '<p class="notice">Kein Fremdkapital – keine Sensitivität erforderlich.</p>'
        )
    elif not interest_rows and not repayment_rows:
        sensitivity_html = (
            '<p class="notice">Daten unvollständig – ohne Finanzierung ist keine '
            "Sensitivität verfügbar.</p>"
        )
    if no_debt:
        schedule_html = (
            '<p class="notice">Kein Fremdkapital – kein Annuitätenplan erforderlich.</p>'
        )
    elif not schedule_rows:
        schedule_html = (
            '<p class="notice">Daten unvollständig – ohne Finanzierung ist kein '
            "Annuitätenplan verfügbar.</p>"
        )

    definitions = _mapping(assumptions.get("convention_definitions"))
    definitions_html = "".join(
        f"<li><strong>{escape(key)}</strong>: {escape(str(definitions.get(key, _MISSING)))}</li>"
        for key in (f"14-K{number:02}" for number in range(1, 14))
    )
    blocked = (
        '<p class="blocked">Nicht für den produktiven Einsatz freigegeben.</p>'
        if assumptions.get("production_blocked") is True
        else ""
    )
    rechtsstand = escape(str(assumptions.get("rechtsstand", _MISSING)))
    assumptions_html = f"<p><strong>Rechtsstand {rechtsstand}</strong></p>"
    assumptions_html += f"{blocked}<ol>{definitions_html}</ol>"
    disclosure = escape(str(data.layout_snapshot["artifact_disclosure"]))
    disclaimer = escape(str(data.layout_snapshot["product_disclaimer"]))

    sections = "".join(
        (
            _section("header_disclosure", "Grundlage", header_html),
            _section("investment", "Investition", investment_html),
            _section("financing_ltv", "Finanzierung und Auslauf", financing_html),
            _section("rent_and_planning_costs", "Miete und Planungskosten", rent_html),
            _section("seven_kpis", "Sieben Kennzahlen", kpi_html),
            _section("sensitivity", "Sensitivität", sensitivity_html),
            _section("twelve_month_schedule", "Annuitätenplan – zwölf Monate", schedule_html),
            _section("assumptions_method", "Annahmen und Methode", assumptions_html),
            _section(
                "disclosure",
                "Hinweise",
                f'<p>{disclosure}</p><p class="disclaimer">{disclaimer}</p>',
            ),
        )
    )
    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <title>Investitionsübersicht {escape(data.case_key)}</title>
  <style>
    @page {{ size: A4; margin: 16mm; }}
    :root {{ color: #18212a; background: #ffffff; font-family: Manrope, Arial, sans-serif; }}
    body {{ margin: 0; font-size: 9.5pt; line-height: 1.4; }}
    h1 {{ margin: 0 0 5mm; font-size: 22pt; }}
    h1, h2, h3 {{ font-family: Montserrat, Arial, sans-serif; }}
    h2 {{ margin: 0 0 3mm; color: #123f37; font-size: 14pt; }}
    h3 {{ margin: 4mm 0 2mm; font-size: 11pt; }}
    .block {{ break-inside: avoid; margin-bottom: 8mm; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 1.8mm 1mm; border-bottom: .25mm solid #5c6a6b; text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
    .facts th {{ width: 55%; font-weight: 500; color: #5c6a6b; }}
    .notice, .blocked {{ padding: 3mm; background: #fbf1e5; border-left: 1mm solid #92400e; }}
    .badge {{ display: inline-block; padding: 1mm 2mm; background: #e7efeb; color: #123f37; }}
    .disclaimer {{ color: #5c6a6b; font-style: italic; }}
    ol {{ padding-left: 6mm; }}
  </style>
</head>
<body><main>{sections}</main></body>
</html>"""


def render_investment_bank_pdf(data: InvestmentBankPdfData) -> bytes:
    """Render a reproducible A4 PDF and normalize volatile Chromium dates."""

    rendered = render_html_to_pdf(investment_bank_pdf_html(data), PdfOptions(format="A4"))
    return re.sub(
        rb"D:\d{14}[+-]\d{2}'\d{2}'",
        b"D:20000101000000+00'00'",
        rendered,
    )
