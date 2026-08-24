"""Red U5 contract for the separate German single-renter UVI document."""

from __future__ import annotations

import dataclasses
import runpy
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, cast

import pytest

_ORACLE_PATH = (
    Path(__file__).resolve().parents[2] / "rules-store" / "tests" / "berkay_uvi_golden.py"
)
_ORACLE = runpy.run_path(str(_ORACLE_PATH))
UVI_EXAMPLES = cast(dict[str, dict[str, object]], _ORACLE["UVI_EXAMPLES"])


def _pdf_api() -> tuple[type[Any], type[Any], Any, str]:
    import lokara_pdf

    block_type = getattr(lokara_pdf, "UviDocumentBlock", None)
    data_type = getattr(lokara_pdf, "UviDocumentData", None)
    render = getattr(lokara_pdf, "uvi_document_html", None)
    disclaimer = lokara_pdf.DISCLAIMER
    assert block_type is not None, "U5 UviDocumentBlock is missing"
    assert data_type is not None, "U5 UviDocumentData is missing"
    assert callable(render), "U5 uvi_document_html(data) is missing"
    return block_type, data_type, render, disclaimer


def _block(block_type: type[Any], **changes: object) -> Any:
    values: dict[str, object] = {
        "heading_de": "Block B — Vergleich zum Vormonat",
        "status": "ready",
        "value_kwh": 900,
        "reference_kwh": 850,
        "delta_kwh": 50,
        "percent": Decimal("5.9"),
        "label_de": None,
        "basis_de": None,
        "attribution_de": None,
        "provenance_de": (),
        "data_quality_flag": None,
    }
    values.update(changes)
    return block_type(**values)


def _document() -> tuple[Any, Any, str]:
    block_type, data_type, render, disclaimer = _pdf_api()
    block_a_case = UVI_EXAMPLES["approved_hkv_provisional"]
    block_b_case = UVI_EXAMPLES["emir_spec_block_b_previous_month"]
    block_c_case = UVI_EXAMPLES["emir_spec_block_c_weather_adjusted"]
    block_d2_case = UVI_EXAMPLES["approved_block_d2_heat_only"]
    target_heat_kwh = block_b_case["current_kwh"]

    block_a = _block(
        block_type,
        heading_de="Block A — Monatsverbrauch",
        value_kwh=target_heat_kwh,
        reference_kwh=None,
        delta_kwh=None,
        percent=None,
        label_de=block_a_case["label"],
        provenance_de=("Ablesungen r-1 und r-2 · linear nach verstrichenen Tagen interpoliert",),
    )
    block_b = _block(
        block_type,
        value_kwh=target_heat_kwh,
        reference_kwh=block_b_case["previous_kwh"],
        delta_kwh=block_b_case["delta_kwh"],
        percent=Decimal(cast(str, block_b_case["percent"])),
    )
    block_c = _block(
        block_type,
        heading_de="Block C — Vorjahresmonat",
        value_kwh=target_heat_kwh,
        reference_kwh=block_c_case["adjusted_previous_year_kwh"],
        delta_kwh=block_c_case["delta_kwh"],
        percent=Decimal(cast(str, block_c_case["percent"])),
        attribution_de="Quelle: Deutscher Wetterdienst",
        provenance_de=("Station 00433 · 12,4 km · Datenstand 2025-08",),
    )
    block_d2 = _block(
        block_type,
        heading_de="Block D2 — Durchschnittsnutzer",
        value_kwh=target_heat_kwh,
        reference_kwh=block_d2_case["norm_month_kwh"],
        delta_kwh=cast(int, target_heat_kwh) - cast(int, block_d2_case["norm_month_kwh"]),
        percent=Decimal("-34.2"),
        label_de=block_d2_case["label"],
        basis_de="normierter Durchschnittsnutzer",
        attribution_de=block_d2_case["attribution"],
        provenance_de=("Heizspiegel 2025 · Abrechnungsjahr 2024",),
    )
    data = data_type(
        title_de="Monatliche Verbrauchsinformation",
        target_month=date(2026, 7, 1),
        unit_label="WE 1",
        block_a=block_a,
        block_b=block_b,
        block_c=block_c,
        block_d_or_d2=block_d2,
        legal_risks_de=("Vom Aufrufer gelieferter 3-%-Risikohinweis; kein automatischer Abzug.",),
        unresolved_conflicts_de=("Vom Aufrufer gelieferter Produktionskonflikt.",),
        rechtsstand="08/2026",
        disclaimer=disclaimer,
    )
    return data, render, disclaimer


def test_u5_document_types_are_frozen_and_slotted() -> None:
    """U5-PDF-01: the renderer consumes immutable archive-shaped document data."""
    block_type, data_type, _, _ = _pdf_api()
    for value_type in (block_type, data_type):
        parameters = value_type.__dataclass_params__
        assert parameters.frozen
        assert "__slots__" in vars(value_type)
    data, _, _ = _document()
    with pytest.raises(dataclasses.FrozenInstanceError):
        data.unit_label = "WE 2"


def test_u5_representative_document_uses_one_target_heat_value_in_every_ready_block() -> None:
    """U5-PDF-REVIEW-01: A, B, C and D2 describe one renter-month target value."""
    data, _, _ = _document()
    ready_blocks = (data.block_a, data.block_b, data.block_c, data.block_d_or_d2)
    assert all(block.status == "ready" for block in ready_blocks)
    assert {block.value_kwh for block in ready_blocks} == {data.block_a.value_kwh}
    for comparison in (data.block_b, data.block_c, data.block_d_or_d2):
        assert comparison.value_kwh is not None
        assert comparison.reference_kwh is not None
        assert comparison.delta_kwh is not None
        assert comparison.percent is not None
        assert comparison.delta_kwh == comparison.value_kwh - comparison.reference_kwh
        expected_percent = (
            Decimal(comparison.delta_kwh) / Decimal(comparison.reference_kwh) * Decimal(100)
        ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        assert comparison.percent == expected_percent


def test_u5_document_contains_the_source_named_blocks_and_provenance() -> None:
    """U5-PDF-02: one German renter page carries A/B/C/D2 and exact source labels."""
    data, render, disclaimer = _document()
    html = render(data)

    assert '<html lang="de">' in html
    assert "<title>Monatliche Verbrauchsinformation" in html
    assert "<h1" in html
    assert html.count("<h2") >= 4
    assert "Juli 2026" in html
    assert "WE 1" in html
    for heading in ("Block A", "Block B", "Block C", "Block D2"):
        assert heading in html

    assert UVI_EXAMPLES["approved_hkv_provisional"]["label"] in html
    assert "Quelle: Deutscher Wetterdienst" in html
    assert UVI_EXAMPLES["approved_block_d2_heat_only"]["label"] in html
    assert UVI_EXAMPLES["approved_block_d2_heat_only"]["attribution"] in html
    assert "normierter Durchschnittsnutzer" in html
    assert "Station 00433" in html and "12,4 km" in html
    assert "Heizspiegel 2025" in html
    assert "Rechtsstand 08/2026" in html
    assert disclaimer in html
    assert "Vom Aufrufer gelieferter 3-%-Risikohinweis" in html
    assert "Vom Aufrufer gelieferter Produktionskonflikt" in html


def test_u5_document_renders_only_approved_german_interpolation_provenance() -> None:
    """U5-PDF-REVIEW-04: internal interpolation identifiers never reach renters."""
    data, render, _ = _document()
    html = render(data)
    assert "linear_by_elapsed_days" not in html
    assert "linear nach verstrichenen Tagen interpoliert" in html


def test_u5_document_never_leaks_landlord_or_other_party_data() -> None:
    """U5-PDF-03: the input and output are one-unit, never an all-party view."""
    data, render, _ = _document()
    assert {field.name for field in dataclasses.fields(data)}.isdisjoint(
        {"building_units", "all_units", "all_tenancies", "party_labels", "landlord_view"}
    )
    html = render(data)
    for forbidden in ("WE 2", "Mieter B", "Vermieter-Gesamtübersicht", "alle Mietparteien"):
        assert forbidden not in html


def test_u5_document_is_a_frozen_result_carrier_not_an_input_resolver() -> None:
    """U5-PDF-04: authoritative prerequisite resolution stays server-side before render."""
    _, data_type, _, _ = _pdf_api()
    fields = {field.name for field in dataclasses.fields(data_type)}
    assert "unresolved_conflicts_de" in fields
    assert fields.isdisjoint(
        {
            "monthly_degree_days_current",
            "monthly_degree_days_previous_year",
            "energy_source",
            "heizspiegel_mittel_kwh_m2a",
            "warm_water_deduction_kwh_m2a",
            "reading_start_x1000",
            "reading_end_x1000",
        }
    )


def test_u5_blocked_fields_emit_no_renter_facing_comparison_copy() -> None:
    """U5-PDF-05: blocked engine fields cannot become invented tenant labels."""
    block_type, data_type, render, disclaimer = _pdf_api()
    ready = _block(block_type)
    blocked = _block(
        block_type,
        heading_de="Block D2 — Durchschnittsnutzer",
        status="blocked",
        value_kwh=None,
        reference_kwh=None,
        delta_kwh=None,
        percent=None,
        label_de=None,
        basis_de=None,
        attribution_de=None,
        provenance_de=(),
        data_quality_flag="non_positive_heat_only_mittel",
    )
    data = data_type(
        title_de="Monatliche Verbrauchsinformation",
        target_month=date(2026, 7, 1),
        unit_label="WE 1",
        block_a=ready,
        block_b=ready,
        block_c=ready,
        block_d_or_d2=blocked,
        legal_risks_de=(),
        unresolved_conflicts_de=("Vom Aufrufer gelieferter Produktionskonflikt.",),
        rechtsstand="08/2026",
        disclaimer=disclaimer,
    )
    with pytest.raises(ValueError, match="label_de") as refused:
        render(data)

    message = str(refused.value)
    assert "normierter Durchschnittsnutzer" not in message
    assert "normierter, gebäudebezogener Richtwert" not in message
    assert "Quelle: co2online gGmbH (Heizspiegel)" not in message
    assert "non_positive_heat_only_mittel" not in message


def test_u5_non_ready_block_requires_approved_absence_copy_or_renderer_refusal() -> None:
    """U5-PDF-REVIEW-02: a blocked comparison cannot render as a heading-only card."""
    block_type, _, render, _ = _pdf_api()
    data, _, _ = _document()
    blocked = _block(
        block_type,
        status="blocked",
        value_kwh=None,
        reference_kwh=None,
        delta_kwh=None,
        percent=None,
        label_de=None,
        data_quality_flag="missing_previous_month",
    )
    with pytest.raises(ValueError, match="label_de"):
        render(dataclasses.replace(data, block_b=blocked))

    approved_copy = "liegt für den Vormonat noch nicht vor"
    labelled = dataclasses.replace(blocked, label_de=approved_copy)
    html = render(dataclasses.replace(data, block_b=labelled))
    assert approved_copy in html
    assert "missing_previous_month" not in html
