"""Semantic M7-B contract for approved Page-04 fixtures 11-F01…11-F16."""

from __future__ import annotations

import importlib
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ORACLE_DIR = Path(__file__).resolve().parents[2] / "rules-store" / "tests"
sys.path.insert(0, str(ORACLE_DIR))

from berkay_11_golden import (  # noqa: E402
    EXTF_WORKING_CONVENTION,
    PAGE_04_GOLDENS,
    PAGE_04_REGISTER_ROWS,
)

GENERATED_AT = datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC)


def _api() -> ModuleType:
    return importlib.import_module("export_engine")


def _str(case: dict[str, object], key: str) -> str:
    value = case[key]
    assert isinstance(value, str)
    return value


def _ints(case: dict[str, object], key: str) -> tuple[int, ...]:
    value = case[key]
    assert isinstance(value, tuple)
    assert all(isinstance(item, int) and not isinstance(item, bool) for item in value)
    return value


def _event(
    event_id: str,
    category: str | None,
    amount_cents: int,
    direction: str,
    payment_date: str | None,
    **extra: object,
) -> dict[str, object]:
    return {
        "event_id": event_id,
        "account_id": "account-1",
        "building_id": "building-1",
        "unit_id": "WE-01",
        "category": category,
        "amount_cents": amount_cents,
        "direction": direction,
        "payment_date": payment_date,
        "due_date": None,
        "receipt_reference": event_id,
        "source": "manuell",
        "version": 1,
        **extra,
    }


def _mapping(*, chart: str = "skr03") -> tuple[dict[str, object], ...]:
    accounts = {
        "grundsteuer": ("47", "4900", "6300"),
        "versicherung": ("48", "4360", "6400"),
        "hauswart": ("49", "4210", "6210"),
        "heizkosten": ("50", "4240", "6240"),
        "muellbeseitigung": ("50", "4250", "6250"),
        "bank": ("", "1200", "1800"),
    }
    return tuple(
        {
            "category": category,
            "anlage_v_line": line,
            "account": skr03 if chart == "skr03" else skr04,
            "verification_flag": "verify-before-production",
            "source_version": "m7-caller-test-mapping",
        }
        for category, (line, skr03, skr04) in accounts.items()
    )


def _overview(
    events: tuple[dict[str, object], ...],
    *,
    afa_handoff: dict[str, object] | None = None,
    mapping: tuple[dict[str, object], ...] | None = None,
) -> Any:
    result = _api().build_anlage_v_overview(
        ledger_events=events,
        afa_handoff=afa_handoff or {},
        mapping=mapping or _mapping(),
        tax_year=2025,
        generated_at=GENERATED_AT,
        register_rows=PAGE_04_REGISTER_ROWS,
    )
    assert not hasattr(result, "golden_values"), "overview must aggregate, never echo a fixture"
    assert result.production_blocked is True
    assert result.generated_at == GENERATED_AT
    assert result.rechtsstand == "07/2026"
    return result


@pytest.mark.parametrize("fixture_id", tuple(PAGE_04_GOLDENS))
def test_all_fixture_ids_have_a_source_evidence_trace_without_expected_outputs(
    fixture_id: str,
) -> None:
    trace = getattr(_api(), "trace_approved_fixture", None)
    assert callable(trace), "trace_approved_fixture is missing"
    result = trace(fixture_id=fixture_id, source="docs/11", register_rows=PAGE_04_REGISTER_ROWS)
    assert result.fixture_id == fixture_id
    assert result.expected_values_consumed is False
    assert tuple(result.source_evidence) == tuple(sorted(result.source_evidence, key=str))


@pytest.mark.parametrize("fixture_id", ("11-F04", "11-F05", "11-F06", "11-F07"))
def test_assign_tax_year_uses_only_payment_due_and_recurring_facts(fixture_id: str) -> None:
    case = PAGE_04_GOLDENS[fixture_id]
    payment = {
        "payment_date": case["payment_date"],
        "due_date": case.get("due_date"),
        "recurring": case["recurring"],
    }
    assert _api().assign_tax_year(payment) == case["tax_year"]


def test_f01_f03_aggregate_real_ledger_and_handoff_cents() -> None:
    events = (
        tuple(
            _event(f"rent-{month}", "kaltmiete", 194_000, "einnahme", f"2025-{month:02}-01")
            for month in range(1, 13)
        )
        + tuple(
            _event(
                f"advance-{month}", "nk_vorauszahlung", 47_000, "einnahme", f"2025-{month:02}-01"
            )
            for month in range(1, 13)
        )
        + tuple(
            _event(f"cost-{index}", category, amount, "ausgabe", "2025-03-15")
            for index, (category, amount) in enumerate(
                zip(
                    (
                        "grundsteuer",
                        "versicherung",
                        "hauswart",
                        "heizkosten",
                        "muellbeseitigung",
                        "bank",
                    ),
                    (98_000, 124_000, 180_000, 360_000, 72_000, 150_000),
                    strict=True,
                )
            )
        )
    )
    result = _overview(
        events,
        afa_handoff={
            "afaAbziehbarCent": 540_103,
            "zinsAbziehbarCent": 840_000,
            "zinsBestaetigt": False,
            "disagioAbziehbarCent": 10_000,
            "erhaltungsaufwandCent": 20_000,
        },
    )
    assert result.income_total_cents == PAGE_04_GOLDENS["11-F01"]["income_total"]
    assert result.cash_cost_total_cents == PAGE_04_GOLDENS["11-F02"]["cash_cost_total"]
    assert (
        result.advertising_cost_total_cents == PAGE_04_GOLDENS["11-F02"]["advertising_cost_total"]
    )
    assert result.result_cents == PAGE_04_GOLDENS["11-F03"]["result"]
    assert "disagio" not in result.exported_categories
    assert "erhaltungsaufwand" not in result.exported_categories


@pytest.mark.parametrize(
    ("fixture_id", "payment", "cold", "advance", "credit"),
    (
        ("11-F08", 77_000, 62_000, 15_000, 0),
        ("11-F09", 60_000, 60_000, 0, 0),
        ("11-F15", 80_000, 62_000, 15_000, 3_000),
    ),
)
def test_rent_payment_splits_are_computed_from_soll(
    fixture_id: str, payment: int, cold: int, advance: int, credit: int
) -> None:
    result = _overview(
        (
            _event(
                fixture_id,
                "rent_collection",
                payment,
                "einnahme",
                "2025-03-01",
                cold_rent_due_cents=62_000,
                nk_advance_due_cents=15_000,
            ),
        )
    )
    components = result.event_components[fixture_id]
    assert components == {
        "kaltmiete": cold,
        "nk_vorauszahlung": advance,
        "mieter_guthaben": credit,
    }
    assert sum(components.values()) == payment


def test_refund_deposit_mapping_and_vat_readiness_are_computed() -> None:
    events = (
        _event("11-F10", "nk_guthaben", 20_000, "ausgabe", "2025-06-01"),
        _event("11-F11", "kaution", 174_000, "einnahme", "2025-02-01"),
        _event("11-F14", "grundsteuer", 98_000, "ausgabe", "2025-03-15"),
        _event("11-F16", "versicherung", 119_000, "ausgabe", "2025-04-01", vat_case=True),
    )
    skr03 = _overview(events, mapping=_mapping(chart="skr03"))
    skr04 = _overview(events, mapping=_mapping(chart="skr04"))
    assert skr03.advance_income_adjustment_cents == -20_000
    assert skr03.anlage_v_effect_by_event["11-F11"] == 0
    assert skr03.account_by_event["11-F14"] == "4900"
    assert skr04.account_by_event["11-F14"] == "6300"
    assert "vat_case_detected" in {finding.code for finding in skr03.findings}


def test_readiness_derives_red_and_yellow_findings_from_normalized_inputs() -> None:
    result = _api().evaluate_export_readiness(
        ledger_events=(
            _event("no-date", None, 10_000, "ausgabe", None),
            _event("vat", "versicherung", 119_000, "ausgabe", "2025-03-01", vat_case=True),
        ),
        afa_record=None,
        adviser_profile={"beraternummer": None, "mandantennummer": None},
        mapping=_mapping(),
        export_kind="datev_extf",
        tax_year=2025,
        generated_at=GENERATED_AT,
        register_rows=PAGE_04_REGISTER_ROWS,
        extf_profile=EXTF_WORKING_CONVENTION,
    )
    codes = {finding.code for finding in result.findings}
    assert {
        "payment_without_date",
        "payment_without_category",
        "object_without_afa_record",
        "datev_without_adviser_or_client_number",
        "vat_case_detected",
    } <= codes
    assert result.production_blocked is True


def test_overview_filters_events_by_assign_tax_year_before_aggregation() -> None:
    events = (
        _event("ordinary-2025", "kaltmiete", 10_000, "einnahme", "2025-06-01"),
        _event(
            "window-into-2025",
            "kaltmiete",
            20_000,
            "einnahme",
            "2024-12-30",
            due_date="2025-01-02",
            recurring=True,
        ),
        _event(
            "window-into-2026",
            "kaltmiete",
            30_000,
            "einnahme",
            "2025-12-30",
            due_date="2026-01-02",
            recurring=True,
        ),
        _event("ordinary-2024", "kaltmiete", 40_000, "einnahme", "2024-06-01"),
    )
    result = _overview(events)
    assert result.income_total_cents == 30_000
    assert set(result.anlage_v_effect_by_event) == {"ordinary-2025", "window-into-2025"}


@pytest.mark.parametrize(
    ("account_chart", "expected_account"),
    (("skr03", "4900"), ("skr04", "6300")),
)
def test_overview_selects_account_from_the_requested_chart(
    account_chart: str, expected_account: str
) -> None:
    mapping = (
        {
            "category": "grundsteuer",
            "anlage_v_line": "47",
            "skr03_account": "4900",
            "skr04_account": "6300",
            "verification_flag": "verify-before-production",
            "source_version": "m7-caller-test-mapping",
        },
    )
    result = _api().build_anlage_v_overview(
        ledger_events=(_event("tax-1", "grundsteuer", 98_000, "ausgabe", "2025-03-15"),),
        afa_handoff={},
        mapping=mapping,
        account_chart=account_chart,
        tax_year=2025,
        generated_at=GENERATED_AT,
        register_rows=PAGE_04_REGISTER_ROWS,
    )
    assert result.account_by_event == {"tax-1": expected_account}


def test_outgoing_income_reversals_reduce_income_and_keep_income_accounts() -> None:
    mapping = (
        {
            "category": "kaltmiete",
            "skr03_account": "8400",
            "skr04_account": "4400",
            "verification_flag": "verify-before-production",
            "source_version": "m7-caller-test-mapping",
        },
        {
            "category": "nk_vorauszahlung",
            "skr03_account": "8410",
            "skr04_account": "4410",
            "verification_flag": "verify-before-production",
            "source_version": "m7-caller-test-mapping",
        },
    )
    result = _api().build_anlage_v_overview(
        ledger_events=(
            _event(
                "rent-refund",
                "kaltmiete",
                60_000,
                "ausgabe",
                "2025-03-15",
                source_component="base_rent",
            ),
            _event(
                "advance-refund",
                "nk_vorauszahlung",
                15_000,
                "ausgabe",
                "2025-03-15",
                source_component="nk_advance",
            ),
        ),
        afa_handoff={},
        mapping=mapping,
        account_chart="skr04",
        tax_year=2025,
        generated_at=GENERATED_AT,
        register_rows=PAGE_04_REGISTER_ROWS,
    )
    assert result.income_total_cents == -75_000
    assert result.cash_cost_total_cents == 0
    assert result.anlage_v_effect_by_event == {
        "rent-refund": -60_000,
        "advance-refund": -15_000,
    }
    assert result.account_by_event == {
        "rent-refund": "4400",
        "advance-refund": "4410",
    }
    assert {"kaltmiete", "nk_vorauszahlung"} <= set(result.exported_categories)


def test_f12_f13_test_only_extf_bytes_are_deterministic_and_balanced() -> None:
    f12 = PAGE_04_GOLDENS["11-F12"]
    profile = {
        "profile_id": "m7-test-only-v1",
        "verification_flag": "verified-test-only",
        "encoding": "windows-1252",
        "delimiter": ";",
        "line_ending": "\r\n",
        "decimal_separator": ",",
        "header": ("EXTF-TEST", GENERATED_AT.isoformat()),
        "columns": ("Betrag", "Belegdatum", "Belegfeld 1", "Buchungstext"),
        "official_datev_profile": False,
    }
    events = (
        _event(
            "income-11-F12",
            "kaltmiete",
            92_000,
            "einnahme",
            "2025-03-14",
            unit_id="WE-01",
            receipt_reference=f12["income_reference"],
            booking_text=f12["income_text"],
        ),
        _event(
            "expense-11-F12",
            "heizkosten",
            36_000,
            "ausgabe",
            "2025-03-14",
            unit_id="WE-01",
            receipt_reference=f12["expense_reference"],
            booking_text=f12["encoding_probe"],
        ),
    )
    kwargs = {
        "ledger_events": events,
        "overview": _overview(events),
        "mapping": _mapping(),
        "adviser_profile": {"beraternummer": "123", "mandantennummer": "456"},
        "extf_profile": profile,
        "generated_at": GENERATED_AT,
    }
    first = _api().encode_datev_extf(**kwargs)
    second = _api().encode_datev_extf(**kwargs)
    assert first == second
    assert _str(f12, "encoding_probe").encode("windows-1252") in first
    f13 = PAGE_04_GOLDENS["11-F13"]
    assert sum(_ints(f13, "debit_parts")) == sum(_ints(f13, "credit_parts")) == 128_000
