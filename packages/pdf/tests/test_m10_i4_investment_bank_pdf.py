"""RED M10-I4 Bank-PDF contract from docs/14 § 4.9 (M10-I4-F01…F05)."""

from __future__ import annotations

import dataclasses
import os
import re
import runpy
from collections.abc import Callable
from html import unescape
from pathlib import Path
from typing import Any, cast

import pytest
from playwright._impl._errors import Error as PlaywrightError

BLOCK_ORDER = (
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
ARTIFACT_DISCLOSURE = (
    "Vom Vermieter erstellte Zusammenfassung auf Basis eigener Angaben und Annahmen. "
    "Keine Immobilienbewertung, kein Beleihungswert, kein Gutachten, keine Bonitätsauskunft."
)
DISCLAIMER = "rechtskonform, keine Rechts- oder Steuerberatung"
LTV_LABEL = "Auslauf zum Kaufpreis, nicht zum Beleihungswert"
_ORACLE_PATH = Path(__file__).resolve().parents[2] / "rules-store" / "tests" / "berkay_14_golden.py"
_ORACLE = runpy.run_path(str(_ORACLE_PATH))
PAGE_07_GOLDENS = cast(dict[str, dict[str, object]], _ORACLE["PAGE_07_GOLDENS"])
REFERENCE_INPUTS = cast(dict[str, int], _ORACLE["REFERENCE_INPUTS"])
F01 = PAGE_07_GOLDENS["14-F01"]
F02 = PAGE_07_GOLDENS["14-F02"]
F04 = PAGE_07_GOLDENS["14-F04"]
F12 = PAGE_07_GOLDENS["14-F12"]
F13 = PAGE_07_GOLDENS["14-F13"]
F14 = PAGE_07_GOLDENS["14-F14"]
_ENGINE_FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "investment-engine"
    / "tests"
    / "test_berkay_14_executable.py"
)


def _api() -> tuple[type[Any], Any, Any, dict[str, object]]:
    import lokara_pdf

    data_type = getattr(lokara_pdf, "InvestmentBankPdfData", None)
    html = getattr(lokara_pdf, "investment_bank_pdf_html", None)
    render = getattr(lokara_pdf, "render_investment_bank_pdf", None)
    layout = getattr(lokara_pdf, "DEFAULT_BANK_LAYOUT_SNAPSHOT", None)
    assert data_type is not None, "RED M10-I4: InvestmentBankPdfData is missing"
    assert callable(html), "RED M10-I4: investment_bank_pdf_html is missing"
    assert callable(render), "RED M10-I4: render_investment_bank_pdf is missing"
    assert isinstance(layout, dict), "RED M10-I4: canonical DEFAULT_BANK layout is missing"
    return data_type, html, render, layout


def _complete_bank_view() -> dict[str, object]:
    schedule = cast(tuple[tuple[int, int, int, int], ...], F02["schedule"])
    before_after = cast(dict[str, tuple[int, int]], F12["before_after_rows"])
    seven_kpis = {
        "factor": {"status": "available", "value": F01["factor_hundredths"]},
        "gross_yield": {"status": "available", "value": F01["gross_yield_bp"]},
        "net_yield": {"status": "available", "value": F01["net_yield_bp"]},
        "dscr": {"status": "available", "value": F01["dscr_hundredths"], "color": "green"},
        "equity_return": {
            "status": "available",
            "before_tax": before_after["equity_return"][0],
            "after_tax": before_after["equity_return"][1],
        },
        "cashflow": {
            "status": "available",
            "before_tax": before_after["cashflow_month_cents"][0],
            "after_tax": before_after["cashflow_month_cents"][1],
            "color": "green",
        },
        "break_even": {
            "status": "available",
            "before_tax": before_after["break_even_month_cents"][0],
            "after_tax": before_after["break_even_month_cents"][1],
        },
    }
    interest_steps = cast(tuple[tuple[int, ...], ...], F13["interest_steps"])
    interest = tuple(
        {
            "interest_bp": row[0],
            "dscr_hundredths": row[5],
            "cashflow_after_month_cents": row[6],
        }
        for row in interest_steps
    )
    repayment_steps = cast(tuple[tuple[int, ...], ...], F14["repayment_steps"])
    repayment = tuple(
        {
            "initial_repayment_bp": row[0],
            "dscr_hundredths": row[3],
            "cashflow_after_month_cents": row[4],
            "closing_balance_cents": row[5],
        }
        for row in repayment_steps
    )
    return {
        "renderable": True,
        "recalculated": False,
        "blocks": BLOCK_ORDER,
        "header_disclosure": {
            "header": {
                "address": "Musterstraße 1, 10115 Berlin",
                "property_type": "Mehrfamilienhaus",
                "year_built": 1995,
                "area_sqm_x100": 19_400,
                "unit_count": 4,
                "creator": "Eigentümer",
                "export_date": "2026-09-16",
                "layout_version": "DEFAULT_BANK/1",
            },
            "product_disclaimer": DISCLAIMER,
            "artifact_disclosure": ARTIFACT_DISCLOSURE,
        },
        "investment": {
            "purchase_price_cents": REFERENCE_INPUTS["purchase_price_cents"],
            "acquisition_costs_cents": REFERENCE_INPUTS["acquisition_costs_cents"],
            "total_investment_cents": REFERENCE_INPUTS["total_investment_cents"],
        },
        "financing_ltv": {
            "equity_cents": REFERENCE_INPUTS["equity_cents"],
            "loan_cents": REFERENCE_INPUTS["loan_cents"],
            "interest_bp": REFERENCE_INPUTS["interest_bp"],
            "initial_repayment_bp": REFERENCE_INPUTS["initial_repayment_bp"],
            "monthly_annuity_cents": F02["monthly_annuity_cents"],
            "ltv_purchase_bp": F12["ltv_purchase_bp"],
            "ltv_total_bp": F12["ltv_total_bp"],
            "ltv_label": F12["ltv_label"],
            "provenance": {"source": "annahme", "badge": "Finanzierung: Annahme"},
        },
        "rent_and_planning_costs": {
            "monthly_actual_rent_cents": REFERENCE_INPUTS["monthly_actual_rent_cents"],
            "vacancy_bp": REFERENCE_INPUTS["vacancy_bp"],
            "administration_cents": REFERENCE_INPUTS["administration_cents"],
            "maintenance_cents": REFERENCE_INPUTS["maintenance_cents"],
            "reserve_cents": REFERENCE_INPUTS["reserve_cents"],
            "vacancy_risk_cents": REFERENCE_INPUTS["vacancy_risk_cents"],
        },
        "seven_kpis": seven_kpis,
        "sensitivity": {"interest": interest, "repayment": repayment},
        "twelve_month_schedule": schedule,
        "assumptions_method": {
            "rechtsstand": "07/2026",
            "production_blocked": True,
            "convention_definitions": {
                f"14-K{number:02}": f"Gespeicherte Definition {number}" for number in range(1, 14)
            },
            "financing_provenance": {"badge": "Finanzierung: Annahme"},
            "afa_provenance": {"badge": "AfA-Annahme"},
        },
        "disclosure": ARTIFACT_DISCLOSURE,
        "product_disclaimer": DISCLAIMER,
        "ltv_label": LTV_LABEL,
        "renter_names_included": False,
    }


def _data(*, f12_partial_without_financing: bool = False) -> tuple[Any, Any, Any]:
    data_type, html, render, layout = _api()
    bank_view = _complete_bank_view()
    sensitivity = cast(dict[str, object], bank_view["sensitivity"])
    result = {
        "outcome": "calculated",
        "bank_view": bank_view,
        "kpi_slots": bank_view["seven_kpis"],
        "interest_sensitivity": sensitivity["interest"],
        "repayment_sensitivity": sensitivity["repayment"],
        "calculated_values": {"schedule": bank_view["twelve_month_schedule"]},
        "rechtsstand": "07/2026",
        "production_blocked": True,
    }
    if f12_partial_without_financing:
        # Page 07 F12/E12 supplies the missing-financing branch, not the all-equity branch.
        # Reuse only the approved engine fixture's inputs/runtime rule bundle and execute the
        # public engine. Neither expected values nor fabricated partial mappings reach it.
        fixture = runpy.run_path(str(_ENGINE_FIXTURE_PATH))
        source_facts = cast(dict[str, dict[str, object]], fixture["SEMANTIC_INPUTS"])["14-F12"]
        omitted = {
            "equity_cents",
            "loan_cents",
            "interest_bp",
            "initial_repayment_bp",
            "financing_provenance",
        }
        facts = {key: value for key, value in source_facts.items() if key not in omitted}
        calculate = cast(Callable[[dict[str, object]], dict[str, Any]], fixture["_calculate"])
        result = calculate(facts)
        bank_view = cast(dict[str, object], result["bank_view"])
    data = data_type(
        case_key="case-frozen-1",
        input_version=1,
        result_id="result-frozen-1",
        engine_version="lokara-investment-engine/0.1.0",
        layout_version_id="layout-default-v1",
        bank_view=bank_view,
        result_snapshot=result,
        layout_snapshot=layout,
    )
    return data, html, render


def _f04_all_equity_data() -> tuple[Any, Any, Any]:
    data_type, html, render, layout = _api()
    fixture = runpy.run_path(str(_ENGINE_FIXTURE_PATH))
    source_facts = cast(dict[str, dict[str, object]], fixture["SEMANTIC_INPUTS"])["14-F04"]
    calculate = cast(Callable[[dict[str, object]], dict[str, Any]], fixture["_calculate"])
    result = calculate(source_facts)
    bank_view = cast(dict[str, object], result["bank_view"])
    data = data_type(
        case_key="case-f04-all-equity",
        input_version=1,
        result_id="result-f04-all-equity",
        engine_version="lokara-investment-engine/0.1.0",
        layout_version_id="layout-default-v1",
        bank_view=bank_view,
        result_snapshot=result,
        layout_snapshot=layout,
    )
    return data, html, render


def test_m10_i4_f01_renderer_input_is_frozen_slotted_and_snapshot_only() -> None:
    data, _html, _render = _data()
    data_type = type(data)
    assert dataclasses.is_dataclass(data_type)
    assert cast(Any, data_type).__dataclass_params__.frozen
    assert "__slots__" in vars(data_type)
    assert {field.name for field in dataclasses.fields(data_type)} == {
        "case_key",
        "input_version",
        "result_id",
        "engine_version",
        "layout_version_id",
        "bank_view",
        "result_snapshot",
        "layout_snapshot",
    }
    assert data.bank_view["recalculated"] is False


def test_m10_i4_f02_exact_blocks_order_and_approved_german_copy() -> None:
    data, render_html, _render_pdf = _data()
    html = render_html(data)
    positions = [html.index(f'data-bank-pdf-block="{block}"') for block in BLOCK_ORDER]
    assert positions == sorted(positions)
    assert html.count('data-bank-pdf-block="') == len(BLOCK_ORDER)
    for required in (ARTIFACT_DISCLOSURE, DISCLAIMER, LTV_LABEL, "Rechtsstand 07/2026"):
        assert required in html
    for number in range(1, 14):
        assert f"14-K{number:02}" in html


def _visible(html: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", unescape(html)).replace("\u202f", " ").split())


def _block(html: str, name: str) -> str:
    return html.split(f'data-bank-pdf-block="{name}"', maxsplit=1)[1].split(
        "</section>", maxsplit=1
    )[0]


def test_m10_i4_f02_uses_german_export_date() -> None:
    data, render_html, _render_pdf = _data()
    visible = _visible(render_html(data))
    assert "Exportdatum 16.09.2026" in visible


def test_m10_i4_f02_uses_two_decimals_for_every_money_value_including_zero() -> None:
    data, render_html, _render_pdf = _data()
    visible = _visible(render_html(data))
    for expected in (
        "420.000,00 €",
        "33.600,00 €",
        "453.600,00 €",
        "113.600,00 €",
        "340.000,00 €",
        "1.671,67 €",
        "2.650,00 €",
        "3.600,00 €",
        "3.000,00 €",
        "0,00 €",
        "636,00 €",
    ):
        assert expected in visible
    money_tokens = re.findall(r"([+-]?[0-9][0-9.,]*)\s*€", visible)
    assert money_tokens
    assert all(
        re.fullmatch(r"[+-]?(?:[0-9]{1,3}(?:\.[0-9]{3})*|[0-9]+),[0-9]{2}", token)
        for token in money_tokens
    )


def test_m10_i4_f03_f12_partial_data_stays_renderable_without_fabricated_zero() -> None:
    data, render_html, _render_pdf = _data(f12_partial_without_financing=True)
    html = render_html(data)
    assert F12["partial_pdf_renderable"] is True
    assert "Daten unvollständig" in html
    assert len(re.findall(r">\s*—\s*<", html)) >= 5
    assert "Finanzierungsdaten fehlen" in html
    assert "Kein Fremdkapital" not in _visible(_block(html, "financing_ltv"))


@pytest.mark.parametrize(
    ("key", "oracle_key", "rendered_value"),
    (
        ("factor", "factor_hundredths", "13,21"),
        ("gross_yield", "gross_yield_bp", "7,57 %"),
        ("net_yield", "net_yield_bp", "5,42 %"),
    ),
)
def test_m10_i4_f03_actual_no_financing_view_preserves_rent_kpis(
    key: str, oracle_key: str, rendered_value: str
) -> None:
    data, render_html, _render_pdf = _data(f12_partial_without_financing=True)
    assert data.bank_view["renderable"] is True
    assert data.bank_view == data.result_snapshot["bank_view"]
    slot = data.bank_view["seven_kpis"][key]
    assert slot["status"] == "available"
    assert slot["value"] == F01[oracle_key]
    assert rendered_value in _visible(_block(render_html(data), "seven_kpis"))


@pytest.mark.parametrize(
    ("key", "label"),
    (
        ("dscr", "DSCR"),
        ("equity_return", "Eigenkapitalrendite"),
        ("cashflow", "Cashflow"),
        ("break_even", "Break-Even"),
    ),
)
def test_m10_i4_f03_actual_missing_financing_kpis_are_standalone_dashes(
    key: str, label: str
) -> None:
    data, render_html, _render_pdf = _data(f12_partial_without_financing=True)
    assert data.bank_view["seven_kpis"][key]["status"] == "unavailable"
    kpis = _block(render_html(data), "seven_kpis")
    row = next(row for row in re.findall(r"<tr\b[^>]*>.*?</tr>", kpis, re.S) if label in row)
    cells = re.findall(r"<(?:td|th)\b[^>]*>(.*?)</(?:td|th)>", row, re.S)
    assert cells[1:]
    assert all(_visible(cell) == "—" for cell in cells[1:])


@pytest.mark.parametrize("key", ("ltv_purchase_bp", "ltv_total_bp"))
def test_m10_i4_f03_actual_missing_loan_ltv_is_standalone_dash(key: str) -> None:
    data, render_html, _render_pdf = _data(f12_partial_without_financing=True)
    assert data.bank_view["financing_ltv"][key] == "—"
    label = "Kaufpreis" if key == "ltv_purchase_bp" else "Gesamtinvestition"
    block = _block(render_html(data), "financing_ltv")
    row = next(row for row in re.findall(r"<tr\b[^>]*>.*?</tr>", block, re.S) if label in row)
    cells = re.findall(r"<(?:td|th)\b[^>]*>(.*?)</(?:td|th)>", row, re.S)
    assert _visible(cells[-1]) == "—"


@pytest.mark.parametrize(
    ("block", "note"),
    (
        (
            "sensitivity",
            "Daten unvollständig – ohne Finanzierung ist keine Sensitivität verfügbar.",
        ),
        (
            "twelve_month_schedule",
            "Daten unvollständig – ohne Finanzierung ist kein Annuitätenplan verfügbar.",
        ),
    ),
)
def test_m10_i4_f03_actual_empty_block_has_own_honest_note_and_no_table(
    block: str, note: str
) -> None:
    data, render_html, _render_pdf = _data(f12_partial_without_financing=True)
    section = _block(render_html(data), block)
    assert note in _visible(section)
    assert "<table" not in section


def test_m10_i4_f04_actual_all_equity_dscr_is_not_applicable_without_missing_badge() -> None:
    data, render_html, _render_pdf = _f04_all_equity_data()
    dscr = data.result_snapshot["kpi_slots"]["dscr"]
    assert dscr == {"status": "not_applicable", "value": F04["dscr"]}
    section = _block(render_html(data), "seven_kpis")
    row = next(row for row in re.findall(r"<tr\b[^>]*>.*?</tr>", section, re.S) if "DSCR" in row)
    assert str(F04["dscr"]) in _visible(row)
    assert "Daten unvollständig" not in _visible(section)


@pytest.mark.parametrize("block", ("sensitivity", "twelve_month_schedule"))
def test_m10_i4_f04_actual_all_equity_empty_financing_block_says_no_debt(
    block: str,
) -> None:
    data, render_html, _render_pdf = _f04_all_equity_data()
    section = _block(render_html(data), block)
    visible = _visible(section)
    assert "Kein Fremdkapital" in visible
    assert "Daten unvollständig" not in visible
    assert "<table" not in section


def test_m10_i4_f04_pdf_has_no_identity_or_product_decision_surface() -> None:
    data, render_html, _render_pdf = _data()
    fields = {field.name.casefold() for field in dataclasses.fields(type(data))}
    assert fields.isdisjoint({"renter", "renter_id", "renter_name", "mieter", "mieter_name"})
    html = render_html(data)
    for forbidden in (
        "Erika Mustermann",
        "Mietername",
        "Marktwert:",
        "Beleihungswert:",
        "Kaufempfehlung",
        "Anlageempfehlung",
        "Kreditzusage",
        "automatisch senden",
        "Jetzt kaufen",
        "Tarif buchen",
    ):
        assert forbidden not in html


def test_m10_i4_f05_two_chromium_renders_are_byte_identical() -> None:
    data, _html, render_pdf = _data()
    try:
        first = render_pdf(data)
        second = render_pdf(data)
    except PlaywrightError as exc:
        if os.environ.get("LOKARA_REQUIRE_PDF"):
            raise
        pytest.skip(f"Playwright Chromium unavailable: {exc}")
    assert first.startswith(b"%PDF-")
    assert first == second
