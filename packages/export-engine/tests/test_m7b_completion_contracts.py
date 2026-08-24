"""RED M7-B completion contracts derived from docs/11 §§3–9."""

from __future__ import annotations

import dataclasses
import inspect
from datetime import UTC, datetime
from enum import Enum
from typing import Any, cast

import export_engine
import pytest

GENERATED_AT = datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC)


def test_normalized_tax_event_has_stable_identity_free_versioned_shape() -> None:
    event_type = getattr(export_engine, "TaxEvent", None)
    source_type = getattr(export_engine, "TaxEventSource", None)
    assert dataclasses.is_dataclass(event_type)
    assert isinstance(source_type, type) and issubclass(source_type, Enum)
    assert {member.value for member in source_type} == {"finapi", "manuell", "rechnung"}
    fields = {field.name for field in dataclasses.fields(event_type)}
    assert {
        "event_id",
        "account_id",
        "building_id",
        "unit_id",
        "payment_date",
        "due_date",
        "amount_cents",
        "direction",
        "category",
        "receipt_reference",
        "source",
        "version",
    } <= fields
    assert fields.isdisjoint({"renter_id", "renter_name", "mieter_id", "mieter_name"})
    event_factory = cast(Any, event_type)
    with pytest.raises((TypeError, ValueError)):
        event_factory(
            event_id="event-1",
            account_id="account-1",
            building_id="building-1",
            unit_id=None,
            payment_date=None,
            due_date=None,
            amount_cents=10_000,
            direction="ausgabe",
            category=None,
            receipt_reference="ledger-1",
            source=cast(Any, source_type).MANUELL,
            version=0,
        )


def test_readiness_projects_every_docs_11_finding_and_freezes_user_evidence() -> None:
    readiness_codes = getattr(export_engine, "READINESS_FINDING_CODES", ())
    assert set(readiness_codes) == {
        "payment_without_date",
        "datev_without_adviser_or_client_number",
        "no_payment_data_in_requested_period",
        "unmatched_party",
        "payment_without_category",
        "missing_selected_account",
        "object_without_afa_record",
        "unresolved_year_window",
        "unconfirmed_interest_proposal",
        "expected_rent_gap",
        "vat_case_detected",
    }
    evaluate = cast(Any, export_engine.evaluate_export_readiness)
    result = evaluate(
        ledger_events=(
            {
                "event_id": "window",
                "account_id": "account-1",
                "building_id": "building-1",
                "unit_id": "unit-1",
                "payment_date": "2025-01-05",
                "due_date": None,
                "amount_cents": 60_000,
                "direction": "einnahme",
                "category": "kaltmiete",
                "receipt_reference": "ledger-window",
                "source": "finapi",
                "version": 1,
                "party_matched": False,
                "recurring": True,
                "expected_amount_cents": 62_000,
            },
            {
                "event_id": "window-unresolved",
                "account_id": "account-1",
                "building_id": "building-1",
                "unit_id": "unit-1",
                "payment_date": "2025-12-28",
                "due_date": None,
                "amount_cents": 62_000,
                "direction": "einnahme",
                "category": "kaltmiete",
                "receipt_reference": "ledger-unresolved",
                "source": "finapi",
                "version": 1,
                "party_matched": True,
                "recurring": True,
                "expected_amount_cents": 62_000,
            },
        ),
        afa_record={"afaAbziehbarCent": 540_103},
        adviser_profile={"beraternummer": "123", "mandantennummer": "456"},
        mapping=(),
        export_kind="anlage_v_csv",
        tax_year=2025,
        generated_at=GENERATED_AT,
        resolved_rules={"production_blocked": True, "rechtsstand": "07/2026"},
        acknowledgements=(
            {"finding_code": "unmatched_party", "acknowledged_at": GENERATED_AT.isoformat()},
        ),
        chosen_year_overrides=(
            {
                "event_id": "window",
                "chosen_tax_year": 2025,
                "reason": "user-confirmed window assignment",
            },
        ),
    )
    codes = {finding.code for finding in result.findings}
    assert {"unmatched_party", "unresolved_year_window", "expected_rent_gap"} <= codes
    assert result.acknowledgements == (
        {"finding_code": "unmatched_party", "acknowledged_at": GENERATED_AT.isoformat()},
    )
    assert result.chosen_year_overrides[0]["event_id"] == "window"
    assert dataclasses.is_dataclass(result)
    assert vars(type(result))["__dataclass_params__"].frozen
    assert cast(Any, result).production_blocked is True


def test_csv_and_extf_encoders_accept_normalized_domain_inputs_not_caller_rows() -> None:
    csv_parameters = set(inspect.signature(export_engine.encode_anlage_v_csv).parameters)
    assert {"overview", "layout", "generated_at"} <= csv_parameters
    assert "rows" not in csv_parameters
    extf_parameters = set(inspect.signature(export_engine.encode_datev_extf).parameters)
    assert {
        "ledger_events",
        "overview",
        "mapping",
        "adviser_profile",
        "extf_profile",
        "generated_at",
    } <= extf_parameters
    assert "rows" not in extf_parameters


def test_encoders_exclude_unmapped_disagio_and_maintenance_and_never_emit_renter_names() -> None:
    encoder = cast(Any, export_engine.encode_datev_extf)
    with pytest.raises(ValueError, match=r"blocked|mapping|production"):
        encoder(
            ledger_events=(
                {
                    "event_id": "event-1",
                    "unit_id": "WE-01",
                    "payment_date": "2025-03-01",
                    "amount_cents": 10_000,
                    "direction": "ausgabe",
                    "category": "instandhaltung",
                    "receipt_reference": "ledger-1",
                    "source": "rechnung",
                    "version": 1,
                },
            ),
            overview={"disagioAbziehbarCent": 10_000, "erhaltungsaufwandCent": 20_000},
            mapping=(),
            adviser_profile={"beraternummer": "123", "mandantennummer": "456"},
            extf_profile={"production_blocked": True},
            generated_at=GENERATED_AT,
        )
