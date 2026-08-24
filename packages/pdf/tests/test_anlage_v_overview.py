"""RED M7-E contract for the German archived Anlage-V overview."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from typing import Any, cast

import pytest


def _pdf_api() -> tuple[type[Any], type[Any], Any, str]:
    import lokara_pdf

    line_type = getattr(lokara_pdf, "AnlageVOverviewLine", None)
    data_type = getattr(lokara_pdf, "AnlageVOverviewData", None)
    render = getattr(lokara_pdf, "anlage_v_overview_html", None)
    assert line_type is not None, "RED M7-E: AnlageVOverviewLine is missing"
    assert data_type is not None, "RED M7-E: AnlageVOverviewData is missing"
    assert callable(render), "RED M7-E: anlage_v_overview_html is missing"
    return line_type, data_type, render, lokara_pdf.DISCLAIMER


def _source_ref_type() -> type[Any]:
    import lokara_pdf

    ref_type = getattr(lokara_pdf, "AnlageVSourceRef", None)
    assert ref_type is not None, (
        "RED M7-E: source references must be structured server-produced values"
    )
    return cast(type[Any], ref_type)


def _document() -> tuple[Any, Any, str]:
    line_type, data_type, render, disclaimer = _pdf_api()
    source_ref = _source_ref_type()
    data = data_type(
        title_de="Anlage-V-Übersicht",
        building_label="Musterstraße 12",
        tax_year=2025,
        generated_at=datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC),
        lines=(
            line_type(
                label_de="Kaltmiete",
                amount_cents=2_328_000,
                source_refs=(source_ref(kind="payment_events", count=12, tax_year=2025),),
            ),
            line_type(
                label_de="Nebenkostenvorauszahlungen",
                amount_cents=564_000,
                source_refs=(source_ref(kind="payment_events", count=12, tax_year=2025),),
            ),
            line_type(
                label_de="Werbungskosten",
                amount_cents=2_364_103,
                source_refs=(
                    source_ref(kind="cost_events", count=8, tax_year=2025),
                    source_ref(kind="afa_record", count=1, tax_year=2025),
                ),
            ),
            line_type(
                label_de="Ergebnis",
                amount_cents=527_897,
                source_refs=(source_ref(kind="tax_calculation", count=1, tax_year=2025),),
            ),
        ),
        blockers_de=(
            "Anlage-V-Zeilennummern sind nicht verifiziert.",
            "DATEV-Konten und EXTF-Parameter sind nicht verifiziert.",
        ),
        rechtsstand="AfA 08/2026 · Export 07/2026",
        production_blocked=True,
        disclaimer=disclaimer,
    )
    return data, render, disclaimer


def test_anlage_v_types_are_frozen_archive_shaped_values() -> None:
    line_type, data_type, _, _ = _pdf_api()
    for value_type in (line_type, data_type):
        assert dataclasses.is_dataclass(value_type)
        assert vars(value_type)["__dataclass_params__"].frozen
        assert "__slots__" in vars(value_type)


def test_german_overview_has_year_rechtsstand_disclaimer_and_visible_blockers() -> None:
    data, render, disclaimer = _document()
    first = render(data)
    second = render(data)
    assert first == second
    assert '<html lang="de">' in first
    assert "Anlage-V-Übersicht" in first
    assert "Musterstraße 12" in first
    assert "Steuerjahr 2025" in first
    assert "23.280,00" in first
    assert "5.640,00" in first
    assert "23.641,03" in first
    assert "5.278,97" in first
    assert "23.280,00 € + 5.640,00 € - 23.641,03 € = 5.278,97 €" in first
    assert "Erstellt: 02.01.2025, 03:04 Uhr" in first
    assert "Rechtsstand AfA 08/2026 · Export 07/2026" in first
    assert disclaimer in first
    assert "Anlage-V-Zeilennummern sind nicht verifiziert" in first
    assert "DATEV-Konten und EXTF-Parameter sind nicht verifiziert" in first
    assert "Export gesperrt" in first


def test_tax_pdf_contains_no_renter_identity_surface() -> None:
    _, data_type, _, _ = _pdf_api()
    field_names = {field.name.lower() for field in dataclasses.fields(data_type)}
    assert field_names.isdisjoint(
        {"renter", "renter_id", "renter_name", "mieter", "mieter_id", "mieter_name"}
    )
    data, render, _ = _document()
    html = render(data)
    for forbidden in ("Mieter", "Mietername", "renter", "tenancy"):
        assert forbidden not in html
    for raw_id in ("payment-1", "cost-1", "calc-1", "building-1", "readiness-1"):
        assert raw_id not in html


@pytest.mark.parametrize("identity_field", ("renter_name", "mieter_name", "tenancy_id"))
def test_tax_pdf_source_references_have_no_free_text_identity_surface(
    identity_field: str,
) -> None:
    source_ref = _source_ref_type()
    field_names = {field.name for field in dataclasses.fields(source_ref)}
    assert field_names == {"kind", "count", "tax_year"}
    with pytest.raises(TypeError):
        source_ref(
            kind="payment_events",
            count=1,
            tax_year=2025,
            **{identity_field: "Erika Mustermann"},
        )


@pytest.mark.parametrize(
    "legacy_ref",
    ("Zahlungseingänge 2025", "Kosten und AfA 2025", "Berechnung Steuerjahr 2025"),
)
def test_tax_pdf_rejects_every_legacy_string_source_reference(legacy_ref: str) -> None:
    line_type, _, _, _ = _pdf_api()
    with pytest.raises(TypeError, match=r"AnlageVSourceRef|source"):
        line_type(label_de="Kaltmiete", amount_cents=2_328_000, source_refs=(legacy_ref,))


def test_tax_pdf_rejects_an_overview_result_that_does_not_reconcile() -> None:
    data, render, _ = _document()
    lines = tuple(
        dataclasses.replace(line, amount_cents=527_896) if line.label_de == "Ergebnis" else line
        for line in data.lines
    )
    with pytest.raises(ValueError, match=r"Ergebnis|Abstimmung|result"):
        render(dataclasses.replace(data, lines=lines))


def test_blocked_overview_cannot_hide_or_enable_real_downloads() -> None:
    data, render, _ = _document()
    assert data.production_blocked is True
    html = render(data)
    assert "download" not in html.lower()
    assert "DATEV-zertifiziert" not in html
    assert "DATEV-Schnittstelle" not in html


def test_blocked_pdf_uses_plain_export_copy_and_concrete_source_reason() -> None:
    data, render, _ = _document()
    html = render(data)
    assert "Export gesperrt" in html
    assert "Anlage-V-Zeilennummern sind nicht verifiziert" in html
    assert "Produktionsausgabe" not in html


def test_unblocked_archive_requires_an_explicit_verified_test_bundle() -> None:
    _, data_type, render, disclaimer = _pdf_api()
    with pytest.raises(ValueError, match="verified test bundle"):
        render(
            data_type(
                title_de="Anlage-V-Übersicht",
                building_label="Testobjekt",
                tax_year=2025,
                generated_at=datetime(2025, 1, 2, tzinfo=UTC),
                lines=(),
                blockers_de=(),
                rechtsstand="07/2026",
                production_blocked=False,
                disclaimer=disclaimer,
                verified_test_bundle_id=None,
            )
        )
