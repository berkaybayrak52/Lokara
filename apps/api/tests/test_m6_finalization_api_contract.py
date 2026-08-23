"""Red owner-only M6-B HTTP contract from docs/02 and docs/08.

This intentionally reads the public OpenAPI surface rather than importing a
future router.  Missing routes therefore fail as an assertion, not an import
error, and the implementation remains free to organize its internals.
"""

import importlib
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

ACCOUNT = "{account_id}"
BUILDING = "{building_id}"
TENANCY = "{tenancy_id}"
DOCUMENT = "{document_id}"

FINALIZE = f"/a/{ACCOUNT}/buildings/{BUILDING}/statements/finalize"
HISTORY = f"/a/{ACCOUNT}/buildings/{BUILDING}/statements/history"
DOWNLOAD = f"/a/{ACCOUNT}/statement-documents/{DOCUMENT}/download"
ADDRESSES = f"/a/{ACCOUNT}/buildings/{BUILDING}/tenancies/{TENANCY}/delivery-addresses"
INSTRUCTIONS = f"/a/{ACCOUNT}/payment-credit-instructions"


def _openapi(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    # This contract reads only OpenAPI and needs no database. The app module
    # builds once at import time, so give its required local settings an
    # explicit test value before importing it.
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "m6b-openapi-contract-secret-32-chars")
    api = importlib.import_module("lokara_api")
    factory = api.create_app
    return cast(dict[str, object], TestClient(factory()).get("/openapi.json").json())


def _operations(schema: dict[str, object], path: str) -> dict[str, object]:
    paths = schema["paths"]
    assert isinstance(paths, dict)
    operations = paths[path]
    assert isinstance(operations, dict)
    return operations


def _dereference_schema(schema: dict[str, object], value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    reference = value.get("$ref")
    if reference is None:
        return value
    assert isinstance(reference, str)
    name = reference.removeprefix("#/components/schemas/")
    components = schema["components"]
    assert isinstance(components, dict)
    schemas = components["schemas"]
    assert isinstance(schemas, dict)
    resolved = schemas[name]
    assert isinstance(resolved, dict)
    return resolved


def test_m6b_owner_finalization_and_archive_routes_are_publicly_defined(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """M6B-F02--F04/F10/F16--F19/CORR: the five owner capabilities exist."""
    schema = _openapi(monkeypatch)
    for path, methods in {
        FINALIZE: {"post"},
        HISTORY: {"get"},
        DOWNLOAD: {"get"},
        ADDRESSES: {"get", "post"},
        INSTRUCTIONS: {"get", "post"},
    }.items():
        assert methods <= set(_operations(schema, path))


def test_m6b_finalize_request_keeps_dates_inclusive_and_correction_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """M6B-CORR/F18: correction and late-positive override cannot be implicit."""
    schema = _openapi(monkeypatch)
    operation = _operations(schema, FINALIZE)["post"]
    assert isinstance(operation, dict)
    request_body = operation["requestBody"]
    assert isinstance(request_body, dict)
    content = request_body["content"]
    assert isinstance(content, dict)
    media_type = content["application/json"]
    assert isinstance(media_type, dict)
    json_schema = _dereference_schema(schema, media_type["schema"])
    properties = json_schema["properties"]
    assert isinstance(properties, dict)
    assert {"periodStart", "periodEnd"} <= set(properties)
    assert {"supersedesStatementId", "latePositiveExceptionReason"} <= set(properties)


def test_m6b_has_no_renter_delivery_or_bank_matching_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """M6B-ISO: archives are owner-only technical records, not portal delivery."""
    schema = _openapi(monkeypatch)
    paths = schema["paths"]
    assert isinstance(paths, dict)
    finalization_paths = [path for path in paths if "statement" in path and "final" in path]
    assert finalization_paths == [FINALIZE]
    assert not any("bank" in path or "finapi" in path for path in finalization_paths)


def test_m6b_late_positive_with_exception_uses_the_positive_document_branch() -> None:
    """M6B-F18: the override is recorded, then enables `Nachzahlung` copy."""
    from lokara_api.routers.finalized_statements import _tenant_html

    tenancy = SimpleNamespace(
        unit=SimpleNamespace(building=SimpleNamespace(name="Musterhaus"), label="WE 1")
    )
    address = SimpleNamespace(
        addressee="Anna Beispiel",
        street="Musterstraße 1",
        postal_code="10115",
        city="Berlin",
        country="DE",
    )
    common: Any = {
        "tenancy": tenancy,
        "address": address,
        "period_start": date(2025, 1, 1),
        "period_end": date(2025, 12, 31),
        "subtotal": 100,
        "advances": 0,
        "saldo": 100,
        "instruction_text": "Zahlung: Bitte überweisen.",
        "rechtsstaende": ("§ 556 BGB — 08/2026",),
        "nk_lines": (),
        "nk_costs": (),
        "all_nk_lines": (),
        "heating_lines": (),
        "all_heating_lines": (),
    }
    assert "<strong>Nachzahlung:" in _tenant_html(**common, late_positive=False)
    assert "<strong>Rechnerischer Saldo:" in _tenant_html(**common, late_positive=True)


def test_m6b_late_positive_without_exception_has_no_instruction_copy() -> None:
    """M6B-F18: the arithmetic stays, but neither demand nor credit copy prints."""
    from lokara_api.routers.finalized_statements import _tenant_html

    tenancy = SimpleNamespace(
        unit=SimpleNamespace(building=SimpleNamespace(name="Musterhaus"), label="WE 1")
    )
    address = SimpleNamespace(
        addressee="Anna Beispiel",
        street="Musterstraße 1",
        postal_code="10115",
        city="Berlin",
        country="DE",
    )
    html = _tenant_html(
        tenancy=cast(Any, tenancy),
        address=cast(Any, address),
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        subtotal=100,
        advances=0,
        saldo=100,
        instruction_text="Zahlung: Bitte überweisen. Guthaben: Wir erstatten.",
        rechtsstaende=("§ 556 BGB — 08/2026",),
        nk_lines=(),
        nk_costs=(),
        all_nk_lines=(),
        heating_lines=(),
        all_heating_lines=(),
        late_positive=True,
    )
    assert "Rechnerischer Saldo:" in html
    assert "Bitte überweisen" not in html
    assert "Wir erstatten" not in html


def test_m6b_snapshot_keeps_complete_calculation_and_trimmed_exception() -> None:
    """M6B-IMM: final evidence retains inputs, results, projections and provenance."""
    from lokara_api.routers.finalized_statements import _finalized_snapshot
    from lokara_domain import Period

    projection = SimpleNamespace(
        audience=SimpleNamespace(value="OWNER"),
        tenancy_id=None,
        window=Period(date(2025, 1, 1), date(2026, 1, 1)),
        nk_costs=(),
        nk_lines=(),
        heating_lines=(),
        owner_residual=None,
        party_labels={},
        findings=("Leerstand",),
        non_allocable_costs=(),
    )
    tenant_projection = SimpleNamespace(**{**projection.__dict__, "tenancy_id": "tenancy-1"})
    bundle = SimpleNamespace(
        normalized_inputs={"nk": {"amount": Decimal("12.34")}, "page01b": None},
        rechtsstaende=("08/2026",),
        rechtsstand_entries=("§ 556 BGB — 08/2026",),
        nk_result={"total": 1234},
        heating_result=None,
        page01b_result=None,
        heating_input_total=Decimal("12.34"),
        heating_missing_reason=None,
        nk_findings=("Hinweis",),
    )
    address = SimpleNamespace(
        id="address-1",
        version=1,
        valid_from=date(2025, 1, 1),
        addressee="Anna Beispiel",
        street="Musterstraße 1",
        postal_code="10115",
        city="Berlin",
        country="DE",
    )
    reconciliation = SimpleNamespace(id="recon-1", version=2, total_cents=100)
    instruction = SimpleNamespace(
        id="instruction-1", version=3, valid_from=date(2025, 1, 1), instruction_text="Text"
    )
    snapshot = _finalized_snapshot(
        bundle=cast(Any, bundle),
        owner_projection=cast(Any, projection),
        vacancy_projection=cast(Any, projection),
        eligible=cast(
            Any,
            [
                (
                    SimpleNamespace(
                        id="tenancy-1",
                        unit=SimpleNamespace(label="WE 1"),
                        valid_from=date(2025, 1, 1),
                        valid_to=None,
                    ),
                    tenant_projection,
                    address,
                    reconciliation,
                    200,
                    100,
                )
            ],
        ),
        instruction=cast(Any, instruction),
        exception_reason="begründet",
        landlord_name="Vermieter Beispiel",
        building_name="Musterhaus",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
    )
    assert {
        "normalized_inputs",
        "calculation_results",
        "owner_output",
        "vacancy_output",
        "tenant_outputs",
        "rule_versions",
        "findings",
        "provenance",
    } <= set(snapshot)
    assert snapshot["normalized_inputs"] == {"nk": {"amount": "12.34"}, "page01b": None}
    assert snapshot["late_positive_exception_reason"] == "begründet"
    assert "archive_render_inputs" not in snapshot
    final_render = cast(dict[str, object], snapshot["final_render"])
    frozen_tenants = cast(list[dict[str, object]], final_render["tenants"])
    assert cast(dict[str, object], frozen_tenants[0]["address"])["addressee"] == "Anna Beispiel"


def test_m6b_snapshot_renderers_need_only_persisted_data_and_exclude_other_tenants() -> None:
    """M6B-IMM/F16: snapshot-only renderers need no ORM or live calculation."""
    from lokara_api.routers.finalized_statements import (
        _owner_html_from_snapshot,
        _tenant_html_from_snapshot,
    )
    from lokara_pdf import render_html_to_pdf

    render: dict[str, object] = {
        "owner": {
            "landlord_name": "Vermieter",
            "building_name": "Musterhaus",
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "created_on": "2026-08-23",
            "cost_rows": [],
            "heating_rows": [
                {
                    "party_label": "WE 1 — Anna Beispiel",
                    "heating_base_cents": 1000,
                    "heating_consumption_cents": 2000,
                    "ww_base_cents": 300,
                    "ww_consumption_cents": 400,
                    "total_cents": 3700,
                }
            ],
            "heating_summary": {
                "total_cents": 4000,
                "billable_cents": 3700,
                "co2_landlord_cents": 300,
                "heat_base_cents": 1000,
                "heat_consumption_cents": 2000,
                "ww_base_cents": 300,
                "ww_consumption_cents": 400,
                "renter_lines_total_cents": 3600,
                "owner_residual_cents": 100,
            },
            "reconciliations": [
                {"tenancy_id": "tenancy-a", "advances_cents": 28000, "saldo_cents": 857}
            ],
            "zero_day_tenancy_ids": ["tenancy-zero"],
            "vacancy": {
                "block_a": [],
                "block_b": [{"label": "Nicht umlagefähig", "amount_cents": 10080}],
                "block_c_rounding_cents": 0,
            },
            "notices": ["Heizhinweis"],
            "rechtsstaende": ["08/2026"],
        },
        "tenants": [
            {
                "tenancy_id": "tenancy-a",
                "building_name": "Musterhaus",
                "unit_label": "WE 1",
                "period_start": "2025-01-01",
                "period_end": "2025-12-31",
                "created_on": "2026-08-23",
                "address": {
                    "addressee": "Anna Beispiel",
                    "street": "Weg 1",
                    "postal_code": "10115",
                    "city": "Berlin",
                    "country": "DE",
                },
                "projection": {
                    "nk_rows": [
                        {
                            "label": "Müll",
                            "total_cents": 10000,
                            "allocation_label": "Wohnfläche",
                            "allocation_explanation": (
                                "Verteilung nach Wohnfläche und Nutzungstagen."
                            ),
                            "numerator": "30,0 × 181 Tage = 5.430,0 m²·Tage",
                            "denominator": "10.860,0 m²·Tage",
                            "share_cents": 5000,
                        }
                    ],
                    "heating_rows": [],
                },
                "meter_evidence": [],
                "notices": ["Heizhinweis"],
                "reconciliation": {"id": "recon-a", "version": 1, "advances_cents": 28000},
                "subtotal_cents": 28857,
                "saldo_cents": 857,
                "saldo_branch": "NACHZAHLUNG",
                "instruction": "Bitte überweisen.",
                "rechtsstaende": ["08/2026"],
            }
        ],
    }
    owner_html = _owner_html_from_snapshot(render)
    tenants = cast(list[dict[str, object]], render["tenants"])
    tenant_html = _tenant_html_from_snapshot(tenants[0])
    assert "100,80" in owner_html and "Heizung Verbrauch" in owner_html and "37,00" in owner_html
    assert "CO₂-Vermieteranteil: 3,00" in owner_html
    assert "Abgleich Heizkosten" in owner_html and "Eigentümerrest" in owner_html
    assert "Anna Beispiel" in tenant_html and "tenancy-zero" not in tenant_html
    assert "Mieter B" not in tenant_html and "28.857" not in tenant_html
    assert "Verteilung nach Wohnfläche und Nutzungstagen." in tenant_html
    assert render_html_to_pdf(owner_html).startswith(b"%PDF")
    assert render_html_to_pdf(tenant_html).startswith(b"%PDF")


def test_m6b_archive_renderers_keep_owner_vacancy_and_tenant_carriers_separate() -> None:
    """M6B-F14/F16/F17/F21: archive strings keep their audience boundaries."""
    from lokara_api.routers.finalized_statements import _tenant_html, _vacancy_html
    from lokara_domain import AllocationKey, cents
    from lokara_nk_engine import CostItem, ShareLine

    cost = CostItem("cost-1", "Müll", cents(10000), AllocationKey.AREA)
    tenant_line = ShareLine("cost-1", "unit-1", "tenancy-1", Decimal("1825000"), cents(5000))
    owner_line = ShareLine("cost-1", "unit-vacant", None, Decimal("1825000"), cents(5000))
    residual = SimpleNamespace(
        origins=(
            SimpleNamespace(
                unit_id="unit-vacant",
                heating_base=cents(1),
                heating_consumption=cents(2),
                ww_base=cents(3),
                ww_consumption=cents(4),
                total=cents(10),
            ),
        ),
        rounding_difference=cents(5),
    )
    vacancy = SimpleNamespace(
        nk_costs=(cost,),
        nk_lines=(owner_line,),
        owner_residual=residual,
        findings=("Nicht umlagefähig",),
        non_allocable_costs=(("Nicht umlagefähig", 10080),),
    )
    owner_html = _vacancy_html(cast(Any, vacancy))
    assert "Leerstandsaufstellung" in owner_html
    assert "(a)" in owner_html and "(b)" in owner_html and "(c)" in owner_html
    assert "Rundungsdifferenz" in owner_html and "Nicht umlagefähig" in owner_html
    assert "100,80" in owner_html
    assert "Anna Beispiel" not in owner_html

    tenancy = SimpleNamespace(
        id="tenancy-1",
        unit=SimpleNamespace(building=SimpleNamespace(name="Musterhaus"), label="WE 1"),
    )
    address = SimpleNamespace(
        addressee="Anna Beispiel",
        street="Musterstraße 1",
        postal_code="10115",
        city="Berlin",
        country="DE",
    )
    html = _tenant_html(
        tenancy=cast(Any, tenancy),
        address=cast(Any, address),
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        subtotal=5000,
        advances=0,
        saldo=5000,
        instruction_text="Zahlung",
        rechtsstaende=("08/2026",),
        nk_lines=(tenant_line,),
        nk_costs=(cost,),
        all_nk_lines=(tenant_line, owner_line),
        heating_lines=(),
        all_heating_lines=(),
        late_positive=False,
    )
    assert "18.250 m²·Tage" in html
    assert "36.500 m²·Tage" in html
    assert "unit-vacant" not in html
