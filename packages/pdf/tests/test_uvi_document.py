"""Red U5 contract for the separate German single-renter UVI document."""

from __future__ import annotations

import dataclasses
import os
import re
import runpy
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from pathlib import Path
from typing import Any, cast

import pytest
from pypdf import PdfReader

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
        assert heading not in html

    assert UVI_EXAMPLES["approved_hkv_provisional"]["label"] in html
    assert "Vergleichswerte auf Basis des bundesweiten Heizspiegels" in html
    assert UVI_EXAMPLES["approved_block_d2_heat_only"]["label"] in html
    assert "© co2online gemeinnützige GmbH" in html
    assert "Vergleich Durchschnittsnutzer" in html
    assert "Station" in html and "DWD" in html
    assert "Heizspiegel 2025" not in html
    assert "Rechtsstand 08/2026" in html
    assert disclaimer in html
    assert "Vom Aufrufer gelieferter 3-%-Risikohinweis" in html
    assert "Vom Aufrufer gelieferter Produktionskonflikt" in html


def test_u5_document_renders_only_approved_german_interpolation_provenance() -> None:
    """U5-PDF-REVIEW-04: internal interpolation identifiers never reach renters."""
    data, render, _ = _document()
    html = render(data)
    assert "linear_by_elapsed_days" not in html
    assert "linear nach verstrichenen Tagen interpoliert" not in html


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


def test_uvi_renders_each_comparison_with_its_own_basis_source_and_provenance() -> None:
    """Each visible comparison keeps its own audit trail instead of one blanket credit."""
    data, render, _ = _document()
    block_b = dataclasses.replace(
        data.block_b,
        basis_de="Rohvergleich mit dem Vormonat",
        attribution_de="Quelle: fernablesbarer Wärmezähler",
        provenance_de=("Vormonatsablesung heat-reading-previous",),
    )
    block_c = dataclasses.replace(
        data.block_c,
        basis_de="Witterungsbereinigter Vorjahresmonat",
        provenance_de=("DWD-Zielmonat weather-target", "DWD-Vorjahresmonat weather-prior"),
    )
    block_d2 = dataclasses.replace(
        data.block_d_or_d2,
        provenance_de=("Heizspiegel-Vintage heating-vintage-2025",),
    )

    html = render(
        dataclasses.replace(data, block_b=block_b, block_c=block_c, block_d_or_d2=block_d2)
    )

    for comparison_fact in (
        "Rohvergleich mit dem Vormonat",
        "Quelle: fernablesbarer Wärmezähler",
        "Vormonatsablesung heat-reading-previous",
        "Witterungsbereinigter Vorjahresmonat",
        "Quelle: Deutscher Wetterdienst",
        "DWD-Zielmonat weather-target",
        "DWD-Vorjahresmonat weather-prior",
        "normierter Durchschnittsnutzer",
        "Quelle: co2online gGmbH (Heizspiegel)",
        "Heizspiegel-Vintage heating-vintage-2025",
    ):
        assert comparison_fact in html


def test_uvi_warm_water_renders_distinct_previous_prior_year_and_d2_comparisons() -> None:
    """The warm-water table must not reuse D2 as its previous-month comparison."""
    data, render, _ = _document()
    _, data_type, _, _ = _pdf_api()
    fields = {field.name for field in dataclasses.fields(data_type)}
    assert {
        "warm_water_block_b",
        "warm_water_block_c",
        "warm_water_block_d2",
    } <= fields

    block_type = type(data.block_a)
    warm_water = _block(
        block_type,
        heading_de="Warmwasser — Monatsverbrauch",
        value_kwh=500,
        reference_kwh=None,
        delta_kwh=None,
        percent=None,
        provenance_de=("Zielablesung warm-water-target",),
    )
    warm_water_block_b = _block(
        block_type,
        heading_de="Warmwasser — Vormonat",
        value_kwh=500,
        reference_kwh=125,
        delta_kwh=375,
        percent=Decimal("300.0"),
        basis_de="Rohvergleich mit dem Vormonat",
        attribution_de="Quelle: fernablesbarer Warmwasserzähler",
        provenance_de=("Vormonatsablesung warm-water-previous",),
    )
    warm_water_block_c = _block(
        block_type,
        heading_de="Warmwasser — Vorjahresmonat",
        value_kwh=500,
        reference_kwh=250,
        delta_kwh=250,
        percent=Decimal("100.0"),
        label_de="nicht witterungsbereinigt",
        basis_de="Rohvergleich mit dem Vorjahresmonat",
        attribution_de="Quelle: fernablesbarer Warmwasserzähler",
        provenance_de=("Vorjahresablesung warm-water-prior-year",),
    )
    warm_water_block_d2 = _block(
        block_type,
        heading_de="Warmwasser — Durchschnittsnutzer",
        value_kwh=500,
        reference_kwh=365,
        delta_kwh=135,
        percent=Decimal("37.0"),
        basis_de="normierter Durchschnittsnutzer",
        attribution_de="Quelle: co2online gGmbH (Heizspiegel)",
        provenance_de=("Heizspiegel-Vintage warm-water-2025",),
    )
    html = render(
        dataclasses.replace(
            data,
            warm_water=warm_water,
            warm_water_block_b=warm_water_block_b,
            warm_water_block_c=warm_water_block_c,
            warm_water_block_d2=warm_water_block_d2,
        )
    )
    warm_section = html.split("WARMWASSER", maxsplit=1)[1].split("</section>", maxsplit=1)[0]
    visible_text = re.sub(r"<[^>]+>", " ", warm_section)
    visible_text = " ".join(visible_text.split())

    assert re.search(r"Vormonat\s+125\s+\+375\s+\+300(?:,|\.)0\s+%", visible_text)
    assert re.search(
        r"Vergleich Durchschnittsnutzer\s+365\s+\+135\s+\+37(?:,|\.)0\s+%",
        visible_text,
    )
    for comparison_fact in (
        "nicht witterungsbereinigt",
        "Rohvergleich mit dem Vormonat",
        "Vormonatsablesung warm-water-previous",
        "Rohvergleich mit dem Vorjahresmonat",
        "Vorjahresablesung warm-water-prior-year",
        "normierter Durchschnittsnutzer",
        "Quelle: co2online gGmbH (Heizspiegel)",
        "Heizspiegel-Vintage warm-water-2025",
    ):
        assert comparison_fact in warm_section


def test_uvi_rechtsstand_and_disclaimer_use_the_approved_aa_text_colour() -> None:
    """Tier-2 disclosures use Slate on white, the approved >=4.5:1 pair."""
    data, render, _ = _document()
    html = render(data).lower()
    style = html.split("<style>", maxsplit=1)[1].split("</style>", maxsplit=1)[0]

    for selector in (r"\.credit", r"\.disclaimer"):
        assert re.search(rf"{selector}[^{{]*\{{[^}}]*color:\s*#5c6a6b\b", style)


def _rendered_a4_text(data: Any) -> str:
    from lokara_pdf import render_html_to_pdf, uvi_document_html
    from playwright._impl._errors import Error as PlaywrightError

    try:
        pdf = render_html_to_pdf(uvi_document_html(data))
    except PlaywrightError as exc:
        if os.environ.get("LOKARA_REQUIRE_PDF"):
            raise
        pytest.skip(f"Playwright Chromium unavailable: {exc}")

    reader = PdfReader(BytesIO(pdf))
    assert len(reader.pages) == 1
    page = reader.pages[0]
    assert float(page.mediabox.width) == pytest.approx(595.92, abs=1)
    assert float(page.mediabox.height) == pytest.approx(842.88, abs=1)
    return page.extract_text() or ""


def _accepted_warm_water_document() -> tuple[Any, str]:
    data, _, disclaimer = _document()
    block_type = type(data.block_a)
    warm_water = _block(
        block_type,
        heading_de="Warmwasser — Monatsverbrauch",
        value_kwh=500,
        reference_kwh=None,
        delta_kwh=None,
        percent=None,
        provenance_de=("Zielablesung warm-water-target",),
    )
    warm_water_block_b = _block(
        block_type,
        heading_de="Warmwasser — Vormonat",
        value_kwh=500,
        reference_kwh=125,
        delta_kwh=375,
        percent=Decimal("300.0"),
        basis_de="Rohvergleich mit dem Vormonat",
        attribution_de="Quelle: fernablesbarer Warmwasserzähler",
        provenance_de=("Vormonatsablesung warm-water-previous",),
    )
    warm_water_block_c = _block(
        block_type,
        heading_de="Warmwasser — Vorjahresmonat",
        value_kwh=500,
        reference_kwh=250,
        delta_kwh=250,
        percent=Decimal("100.0"),
        label_de="nicht witterungsbereinigt",
        basis_de="Rohvergleich mit dem Vorjahresmonat",
        attribution_de="Quelle: fernablesbarer Warmwasserzähler",
        provenance_de=("Vorjahresablesung warm-water-prior-year",),
    )
    warm_water_block_d2 = _block(
        block_type,
        heading_de="Warmwasser — Durchschnittsnutzer",
        value_kwh=500,
        reference_kwh=365,
        delta_kwh=135,
        percent=Decimal("37.0"),
        basis_de="normierter Durchschnittsnutzer",
        attribution_de="Quelle: co2online gGmbH (Heizspiegel)",
        provenance_de=("Heizspiegel-Vintage warm-water-2025",),
    )
    return (
        dataclasses.replace(
            data,
            warm_water=warm_water,
            warm_water_block_b=warm_water_block_b,
            warm_water_block_c=warm_water_block_c,
            warm_water_block_d2=warm_water_block_d2,
            unresolved_conflicts_de=("Produktionsprüfung UVI-Register offen.",),
            vermieter_name="Vermieter GmbH",
            vermieter_strasse="Vermieterweg 1",
            vermieter_plz_ort="10115 Berlin",
            vermieter_telefon="030 1234567",
            vermieter_email="kontakt@vermieter.example",
            absenderzeile="Vermieter GmbH · Vermieterweg 1 · 10115 Berlin",
            mieter_name="Erika Mustermann",
            mieter_strasse="Musterstraße 12",
            mieter_plz_ort="10115 Berlin",
            liegenschaft_nr="L-100",
            nutzeinheit_nr="WE-1",
            objekt_adresse="Musterstraße 12, 10115 Berlin",
            naechster_monat="August 2026",
            support_code="UVI-TAIL-001",
            gruss_ort="Berlin",
            dwd_station="00433",
        ),
        disclaimer,
    )


def test_rendered_warm_water_uvi_keeps_all_required_tail_content_on_its_a4_page() -> None:
    """The accepted warm-water document must not clip its required closing content."""
    data, disclaimer = _accepted_warm_water_document()

    text = _rendered_a4_text(data)

    for required_tail in (
        "Offene Prüfpunkte",
        "Produktionsprüfung UVI-Register offen.",
        "Rechtsstand 08/2026",
        disclaimer,
        "Ihre nächste Verbrauchsinformation erhalten Sie im August 2026",
        "Sie haben Fragen?",
        "030 1234567",
        "kontakt@vermieter.example",
        "UVI-TAIL-001",
        "Berlin",
        "Mit freundlichen Grüßen",
        "Vermieter GmbH",
        "Erstellt mit Lokara",
    ):
        assert required_tail in text


def test_rendered_raw_weather_fallback_uses_only_its_actual_comparison_provenance() -> None:
    """A raw Block C fallback must not retain weather-adjusted or blanket source claims."""
    data, _, _ = _document()
    block_c = dataclasses.replace(
        data.block_c,
        reference_kwh=1_000,
        delta_kwh=-100,
        percent=Decimal("-10.0"),
        label_de="nicht witterungsbereinigt",
        basis_de="Rohvergleich mit dem Vorjahresmonat",
        attribution_de="Quelle: fernablesbarer Wärmezähler",
        provenance_de=("Vorjahresablesung fallback-prior-year",),
    )
    building_comparison = dataclasses.replace(
        data.block_d_or_d2,
        heading_de="Block D — Vergleich im Gebäude",
        basis_de="Vergleich im Gebäude",
        attribution_de=None,
        provenance_de=("Gebäudevergleich aus drei gültigen Nutzeinheiten",),
    )
    fallback = dataclasses.replace(
        data,
        block_c=block_c,
        block_d_or_d2=building_comparison,
        dwd_station=None,
    )

    text = _rendered_a4_text(fallback)

    assert "nicht witterungsbereinigt" in text
    assert "Rohvergleich mit dem Vorjahresmonat" in text
    assert "Quelle: fernablesbarer Wärmezähler" in text
    assert "Vorjahresablesung fallback-prior-year" in text
    assert "Vergleich im Gebäude" in text
    assert "Gebäudevergleich aus drei gültigen Nutzeinheiten" in text
    assert "Vorjahresmonat (witterungsbereinigt)" not in text
    assert "Heizspiegel" not in text
    assert "Deutscher Wetterdienst" not in text
    assert "Station —" not in text
