"""Executable Page-07 contract for approved fixtures 14-F01 through 14-F14.

Expected values come from the approved data-only oracle. They are never passed
to the engine. The production package does not exist when this RED fixture is
introduced; a separate engine implementer owns making this suite green.
"""

# mypy: disable-error-code="import-not-found"

from __future__ import annotations

import importlib
import inspect
import sys
from dataclasses import asdict, dataclass, is_dataclass, replace
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ORACLE_DIR = Path(__file__).resolve().parents[2] / "rules-store" / "tests"
sys.path.insert(0, str(ORACLE_DIR))

from berkay_14_golden import (  # noqa: E402
    CONVENTION_IDS,
    EDGE_CASE_IDS,
    FIXTURE_IDS,
    FORMULA_IDS,
    PAGE_07_GOLDENS,
    REFERENCE_INPUTS,
)

DASH = "—"
INCOMPLETE_BADGE = "Daten unvollständig"
PRODUCT_DISCLAIMER = "rechtskonform, keine Rechts- oder Steuerberatung"
KPI_NAMES = (
    "factor",
    "gross_yield",
    "net_yield",
    "dscr",
    "equity_return",
    "cashflow",
    "break_even",
)


@dataclass(frozen=True)
class RuntimeInvestmentRuleBundle:
    default_building_share_bp: int = 7_500
    default_afa_rate_bp: int = 200
    default_marginal_tax_bp: int = 4_200
    interest_sensitivity_offsets_bp: tuple[int, ...] = (-100, -50, 0, 50, 100)
    repayment_sensitivity_steps_bp: tuple[int, ...] = (100, 200, 300, 400)
    dscr_amber_hundredths: int = 100
    dscr_green_hundredths: int = 120
    cashflow_amber_cents: int = 0
    cashflow_green_cents: int = 5_000
    source_evidence: tuple[str, ...] = ("docs/14-investment-kpis.md@07/2026",)
    rechtsstand: str = "07/2026"
    production_blocked: bool = True


def _api() -> ModuleType:
    return importlib.import_module("investment_engine")


def _plain(value: object) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _plain(asdict(value))
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return _plain(dump())
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return tuple(_plain(item) for item in value)
    return value


def _calculate(facts: dict[str, object]) -> dict[str, Any]:
    module = _api()
    input_type = module.InvestmentInput
    input_fields = inspect.signature(input_type).parameters
    assert "fixture_id" not in input_fields
    assert "expected" not in input_fields
    assert "golden_values" not in input_fields
    result = module.calculate_investment_snapshot(
        input_type(facts=facts), RuntimeInvestmentRuleBundle()
    )
    values = _plain(result)
    assert isinstance(values, dict)
    assert "golden_values" not in values
    assert values["rechtsstand"] == "07/2026"
    assert values["production_blocked"] is True
    evidence = values["source_evidence"]
    assert evidence == tuple(sorted(evidence, key=str))
    assert "docs/14-investment-kpis.md@07/2026" in evidence
    return values


def _reference(**overrides: object) -> dict[str, object]:
    facts: dict[str, object] = dict(REFERENCE_INPUTS)
    facts.update(overrides)
    return facts


def _without(facts: dict[str, object], *keys: str) -> dict[str, object]:
    return {key: value for key, value in facts.items() if key not in keys}


SEMANTIC_INPUTS: dict[str, dict[str, object]] = {
    "14-F01": _reference(financing_provenance="annahme"),
    "14-F02": _reference(financing_provenance="annahme"),
    "14-F03": _without(
        _reference(fixed_monthly_annuity_cents=180_000, financing_provenance="angebot"),
        "initial_repayment_bp",
    ),
    "14-F04": _reference(
        equity_cents=45_360_000,
        loan_cents=0,
        interest_bp=0,
        initial_repayment_bp=0,
        financing_provenance="annahme",
    ),
    "14-F05": _reference(financing_provenance="annahme"),
    "14-F06": {
        "purchase_price_cents": 31_000_000,
        "monthly_actual_rent_cents": 115_000,
    },
    "14-F07": _reference(vacancy_bp=500, financing_provenance="annahme"),
    "14-F08": _reference(
        financing_provenance="annahme",
        afa_reference={
            "source": "page_03_r13",
            "record_version": "page03-r13-v1",
            "annual_full_afa_cents": 512_000,
        },
    ),
    "14-F09": {
        "loan_cents": 34_000_000,
        "interest_bp": 390,
        "fixed_monthly_annuity_cents": 100_000,
        "financing_provenance": "annahme",
    },
    "14-F10": {
        "purchase_price_cents": 14_900_000,
        "acquisition_costs_cents": 1_802_900,
        "monthly_actual_rent_cents": 62_000,
        "vacancy_bp": 0,
        "administration_cents": 60_000,
        "maintenance_cents": 0,
        "reserve_cents": 0,
        "vacancy_risk_cents": 14_880,
        "equity_cents": 4_000_000,
        "loan_cents": 12_702_900,
        "interest_bp": 380,
        "initial_repayment_bp": 200,
        "marginal_tax_bp": 4_200,
        "building_share_bp": 7_500,
        "afa_rate_bp": 200,
        "financing_provenance": "annahme",
    },
    "14-F11": _reference(financing_provenance="annahme"),
    "14-F12": _reference(
        financing_provenance="annahme",
        bank_header={
            "address": "Musterstraße 1, 10115 Berlin",
            "property_type": "Mehrfamilienhaus",
            "year_built": 1978,
            "area_sqm_x100": 19_400,
            "unit_count": 3,
            "creator": "Beispiel Vermietung",
            "export_date": "2026-09-12",
            "layout_version": "bank-view-v1",
        },
        renter_names=("MUST NOT REACH BANK VIEW",),
    ),
    "14-F13": _reference(financing_provenance="annahme"),
    "14-F14": _reference(financing_provenance="annahme"),
}


def _computed(result: dict[str, Any]) -> dict[str, Any]:
    values = result.get("calculated_values")
    assert isinstance(values, dict), "InvestmentResult.calculated_values is missing"
    return values


def _oracle_int(case: dict[str, object], key: str) -> int:
    value = case[key]
    assert isinstance(value, int) and not isinstance(value, bool)
    return value


def _slots(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    slots = result.get("kpi_slots")
    assert isinstance(slots, dict)
    assert tuple(slots) == KPI_NAMES
    assert all(isinstance(slot, dict) for slot in slots.values())
    return slots


def _assert_no_float(value: object) -> None:
    assert not isinstance(value, float)
    if isinstance(value, dict):
        for item in value.values():
            _assert_no_float(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            _assert_no_float(item)


def test_fixture_formula_edge_and_convention_surfaces_are_exact() -> None:
    assert tuple(SEMANTIC_INPUTS) == tuple(f"14-F{number:02}" for number in range(1, 15))
    assert tuple(PAGE_07_GOLDENS) == FIXTURE_IDS == tuple(SEMANTIC_INPUTS)
    assert tuple(f"R{number}" for number in range(1, 11)) == FORMULA_IDS
    assert tuple(f"14-E{number:02}" for number in range(1, 16)) == EDGE_CASE_IDS
    assert tuple(f"14-K{number:02}" for number in range(1, 20)) == CONVENTION_IDS


@pytest.mark.parametrize("fixture_id", tuple(SEMANTIC_INPUTS))
def test_every_approved_fixture_executes_without_expected_output_input(fixture_id: str) -> None:
    result = _calculate(SEMANTIC_INPUTS[fixture_id])
    if fixture_id == "14-F09":
        assert result["outcome"] == "hard_block"
    else:
        assert _slots(result)


def test_f01_computes_r1_through_r7_and_all_seven_kpis_exactly() -> None:
    result = _calculate(SEMANTIC_INPUTS["14-F01"])
    computed = _computed(result)
    expected = PAGE_07_GOLDENS["14-F01"]
    exact_keys = (
        "annual_actual_rent_cents",
        "effective_rent_cents",
        "cash_costs_cents",
        "deductible_costs_cents",
        "noi_cents",
        "annual_interest_cents",
        "annual_repayment_cents",
        "annual_debt_service_cents",
        "afa_basis_cents",
        "annual_afa_cents",
        "tax_base_cents",
        "tax_cents",
        "cashflow_before_year_cents",
        "cashflow_after_year_cents",
        "factor_hundredths",
        "gross_yield_bp",
        "net_yield_bp",
        "dscr_hundredths",
        "equity_return_before_bp",
        "equity_return_after_bp",
        "cashflow_before_month_cents",
        "cashflow_after_month_cents",
        "break_even_before_month_cents",
        "break_even_after_month_cents",
    )
    assert {key: computed[key] for key in exact_keys} == {key: expected[key] for key in exact_keys}
    slots = _slots(result)
    assert all(slot["status"] == "available" for slot in slots.values())
    assert slots["factor"]["value"] == expected["factor_hundredths"]
    assert slots["gross_yield"]["value"] == expected["gross_yield_bp"]
    assert slots["net_yield"]["value"] == expected["net_yield_bp"]
    assert slots["dscr"]["value"] == expected["dscr_hundredths"]
    assert slots["equity_return"]["before_tax"] == expected["equity_return_before_bp"]
    assert slots["equity_return"]["after_tax"] == expected["equity_return_after_bp"]
    assert slots["cashflow"]["before_tax"] == expected["cashflow_before_month_cents"]
    assert slots["cashflow"]["after_tax"] == expected["cashflow_after_month_cents"]
    assert slots["break_even"]["before_tax"] == expected["break_even_before_month_cents"]
    assert slots["break_even"]["after_tax"] == expected["break_even_after_month_cents"]
    assert computed["normalized_period_months"] == 12


def test_f02_initial_repayment_schedule_has_twelve_exact_reconciling_rows() -> None:
    result = _calculate(SEMANTIC_INPUTS["14-F02"])
    computed = _computed(result)
    expected = PAGE_07_GOLDENS["14-F02"]
    assert computed["monthly_annuity_cents"] == expected["monthly_annuity_cents"]
    schedule = computed["schedule"]
    assert schedule == expected["schedule"]
    assert len(schedule) == 12
    assert all(opening - repayment == closing for opening, _, repayment, closing in schedule)
    assert sum(row[1] for row in schedule) == expected["annual_interest_cents"]
    assert sum(row[2] for row in schedule) == expected["annual_repayment_cents"]
    assert _oracle_int(expected, "annual_interest_cents") + _oracle_int(
        expected, "annual_repayment_cents"
    ) == _oracle_int(expected, "annual_debt_service_cents")
    assert schedule[-1][3] == expected["closing_balance_cents"]


def test_f03_uses_fixed_monthly_annuity_directly() -> None:
    result = _calculate(SEMANTIC_INPUTS["14-F03"])
    computed = _computed(result)
    expected = PAGE_07_GOLDENS["14-F03"]
    for key in (
        "monthly_annuity_cents",
        "annual_interest_cents",
        "annual_repayment_cents",
        "annual_debt_service_cents",
        "closing_balance_cents",
    ):
        assert computed[key] == expected[key]
    assert computed["monthly_annuity_cents"] == 180_000


def test_f04_all_equity_has_zero_debt_and_not_applicable_dscr() -> None:
    result = _calculate(SEMANTIC_INPUTS["14-F04"])
    computed = _computed(result)
    expected = PAGE_07_GOLDENS["14-F04"]
    for key in (
        "annual_interest_cents",
        "annual_repayment_cents",
        "annual_debt_service_cents",
        "tax_base_cents",
        "tax_cents",
        "cashflow_before_year_cents",
        "cashflow_after_year_cents",
        "cashflow_after_month_cents",
        "equity_return_after_bp",
        "break_even_after_year_cents",
        "break_even_after_month_cents",
    ):
        assert computed[key] == expected[key]
    dscr = _slots(result)["dscr"]
    assert dscr["status"] == "not_applicable"
    assert dscr["value"] == expected["dscr"]


def test_f04_all_equity_bank_view_uses_dash_and_a_soft_ltv_note() -> None:
    bank_view = _calculate(SEMANTIC_INPUTS["14-F04"])["bank_view"]
    assert bank_view["ltv_purchase_bp"] == DASH
    assert bank_view["ltv_total_bp"] == DASH
    assert bank_view["ltv_purchase_bp"] != 0
    assert bank_view["ltv_total_bp"] != 0
    assert isinstance(bank_view["ltv_note"], str)
    assert bank_view["ltv_note"].strip()


def test_f05_shows_both_equity_returns_and_keeps_cash_on_cash_in_tooltip() -> None:
    result = _calculate(SEMANTIC_INPUTS["14-F05"])
    computed = _computed(result)
    expected = PAGE_07_GOLDENS["14-F05"]
    assert computed["equity_return_before_bp"] == expected["equity_return_before_bp"]
    assert computed["equity_return_after_bp"] == expected["equity_return_after_bp"]
    assert computed["cash_on_cash_after_bp"] == expected["cash_on_cash_after_bp"]
    slot = _slots(result)["equity_return"]
    assert slot["display_columns"] == expected["display_columns"]
    assert slot["tooltip"] == expected["tooltip"]


def test_f06_partial_result_uses_dash_badge_and_required_input_gaps() -> None:
    result = _calculate(SEMANTIC_INPUTS["14-F06"])
    computed = _computed(result)
    expected = PAGE_07_GOLDENS["14-F06"]
    assert computed["annual_actual_rent_cents"] == expected["annual_actual_rent_cents"]
    assert computed["factor_hundredths"] == expected["factor_hundredths"]
    assert computed["gross_yield_bp"] == expected["gross_yield_bp"]
    slots = _slots(result)
    assert slots["factor"]["value"] == expected["factor_hundredths"]
    assert slots["gross_yield"]["value"] == expected["gross_yield_bp"]
    unavailable = expected["unavailable"]
    assert isinstance(unavailable, tuple)
    for name in unavailable:
        assert isinstance(name, str)
        slot = slots[name]
        assert slot["status"] == "unavailable"
        assert slot["value"] == DASH
        assert slot["badge"] == expected["badge"] == INCOMPLETE_BADGE
        assert slot["missing_inputs"]
        assert all(value != 0 for value in slot.values())
    bank_view = result["bank_view"]
    assert bank_view["renderable"] is True
    assert DASH in _plain(bank_view).values() or DASH in str(bank_view)


def test_f07_vacancy_changes_only_effective_rent_kpis_and_keeps_cost_break_even() -> None:
    base = _computed(_calculate(SEMANTIC_INPUTS["14-F01"]))
    computed = _computed(_calculate(SEMANTIC_INPUTS["14-F07"]))
    expected = PAGE_07_GOLDENS["14-F07"]
    for key in (
        "effective_rent_cents",
        "factor_hundredths",
        "gross_yield_bp",
        "noi_cents",
        "net_yield_bp",
        "dscr_hundredths",
        "tax_base_cents",
        "tax_cents",
        "cashflow_before_year_cents",
        "cashflow_after_year_cents",
        "cashflow_after_month_cents",
        "equity_return_after_bp",
        "break_even_after_month_cents",
    ):
        assert computed[key] == expected[key]
    assert computed["factor_hundredths"] == base["factor_hundredths"]
    assert computed["gross_yield_bp"] == base["gross_yield_bp"]
    assert computed["break_even_after_month_cents"] == base["break_even_after_month_cents"]


def test_f08_linked_page03_afa_wins_and_retains_source_and_version() -> None:
    result = _calculate(SEMANTIC_INPUTS["14-F08"])
    computed = _computed(result)
    expected = PAGE_07_GOLDENS["14-F08"]
    for key in (
        "annual_afa_cents",
        "tax_base_cents",
        "tax_cents",
        "cashflow_before_year_cents",
        "cashflow_after_year_cents",
        "cashflow_after_month_cents",
        "equity_return_after_bp",
    ):
        assert computed[key] == expected[key]
    assert computed["annual_afa_cents"] != expected["default_annual_afa_cents"]
    provenance = result["afa_provenance"]
    assert provenance["source"] == expected["afa_provenance"]
    assert provenance["record_version"] == "page03-r13-v1"
    assert provenance["badge"] == expected["badge"]


def test_f08_separates_page03_annual_afa_from_assumed_basis_provenance() -> None:
    result = _calculate(SEMANTIC_INPUTS["14-F08"])
    provenance = result["afa_provenance"]
    annual_afa = provenance["annual_afa"]
    basis = provenance["basis"]
    assert annual_afa["source"] == "page_03_r13"
    assert annual_afa["record_version"] == "page03-r13-v1"
    assert annual_afa["assumption"] is False
    assert basis["source"] == "acquisition_assumption"
    assert basis["record_version"] == "07/2026"
    assert basis["assumption"] is True
    assert basis["value_cents"] == PAGE_07_GOLDENS["14-F01"]["afa_basis_cents"]


def test_explicit_wizard_afa_basis_and_annual_value_are_used_and_provenanced() -> None:
    facts = _reference(
        financing_provenance="annahme",
        afa_reference={
            "source": "wizard",
            "record_version": "wizard-explicit-v1",
            "afa_basis_cents": 30_000_000,
            "annual_full_afa_cents": 600_000,
        },
    )
    result = _calculate(facts)
    computed = _computed(result)
    provenance = result["afa_provenance"]
    assert computed["afa_basis_cents"] == 30_000_000
    assert computed["annual_afa_cents"] == 600_000
    assert provenance["basis"] == {
        "source": "wizard",
        "record_version": "wizard-explicit-v1",
        "assumption": False,
        "value_cents": 30_000_000,
    }
    assert provenance["annual_afa"] == {
        "source": "wizard",
        "record_version": "wizard-explicit-v1",
        "assumption": False,
        "value_cents": 600_000,
    }


def test_nested_afa_provenance_requires_nonblank_string_source_and_version() -> None:
    module = _api()
    valid_references: tuple[tuple[str, dict[str, object]], ...] = (
        (
            "linked",
            {
                "source": "page_03_r13",
                "record_version": "page03-r13-v1",
                "annual_full_afa_cents": 600_000,
            },
        ),
        (
            "wizard",
            {
                "source": "wizard",
                "record_version": "wizard-explicit-v1",
                "afa_basis_cents": 30_000_000,
                "annual_full_afa_cents": 600_000,
            },
        ),
    )
    invalid_metadata: tuple[tuple[str, object, bool], ...] = (
        ("source", "", False),
        ("source", " ", False),
        ("source", [], False),
        ("source", {}, False),
        ("source", 123, False),
        ("source", "", True),
        ("record_version", "", False),
        ("record_version", " ", False),
        ("record_version", [], False),
        ("record_version", {}, False),
        ("record_version", 123, False),
        ("record_version", "", True),
    )
    failures: list[str] = []
    for path, valid_reference in valid_references:
        for field, invalid_value, omit in invalid_metadata:
            reference = dict(valid_reference)
            if omit:
                reference.pop(field)
            else:
                reference[field] = invalid_value
            try:
                module.calculate_investment_snapshot(
                    module.InvestmentInput(
                        facts=_reference(
                            financing_provenance="annahme",
                            afa_reference=reference,
                        )
                    ),
                    RuntimeInvestmentRuleBundle(),
                )
            except (TypeError, ValueError) as error:
                if field not in str(error):
                    failures.append(f"{path}.{field}={invalid_value!r}: wrong error: {error}")
            except Exception as error:
                failures.append(
                    f"{path}.{field}={invalid_value!r}: {type(error).__name__}: {error}"
                )
            else:
                label = "missing" if omit else repr(invalid_value)
                failures.append(f"{path}.{field}={label}: accepted")
    assert failures == [], "\n".join(failures)


def test_top_level_wizard_annual_afa_requires_nonblank_string_record_version() -> None:
    valid_facts = _reference(
        financing_provenance="annahme",
        annual_full_afa_cents=600_000,
        afa_record_version="wizard-top-level-v1",
    )
    valid_result = _calculate(valid_facts)
    assert valid_result["afa_provenance"]["source"] == "wizard_input"
    assert valid_result["afa_provenance"]["record_version"] == "wizard-top-level-v1"
    assert valid_result["afa_provenance"]["annual_afa"]["source"] == "wizard_input"
    assert valid_result["afa_provenance"]["annual_afa"]["record_version"] == "wizard-top-level-v1"

    module = _api()
    invalid_versions: tuple[tuple[object, bool], ...] = (
        ("", True),
        ("", False),
        (" ", False),
        ([], False),
        ({}, False),
        (123, False),
        (True, False),
    )
    failures: list[str] = []
    for invalid_version, omit in invalid_versions:
        facts = dict(valid_facts)
        if omit:
            facts.pop("afa_record_version")
        else:
            facts["afa_record_version"] = invalid_version
        try:
            module.calculate_investment_snapshot(
                module.InvestmentInput(facts=facts),
                RuntimeInvestmentRuleBundle(),
            )
        except (TypeError, ValueError) as error:
            if "afa_record_version" not in str(error):
                failures.append(f"{invalid_version!r}: wrong error: {error}")
        except Exception as error:
            failures.append(f"{invalid_version!r}: {type(error).__name__}: {error}")
        else:
            label = "missing" if omit else repr(invalid_version)
            failures.append(f"afa_record_version={label}: accepted")
    assert failures == [], "\n".join(failures)


def test_f09_non_positive_repayment_is_a_hard_block_without_partial_calculation() -> None:
    result = _calculate(SEMANTIC_INPUTS["14-F09"])
    expected = PAGE_07_GOLDENS["14-F09"]
    assert result["outcome"] == expected["outcome"]
    assert result["guard"]["first_interest_cents"] == expected["first_interest_cents"]
    assert result["guard"]["first_repayment_cents"] == expected["first_repayment_cents"]
    assert result["guard"]["first_repayment_cents"] <= 0
    assert result["calculated_values"] == {}
    assert result["kpi_slots"] == {}


def test_f10_negative_noi_cashflow_and_flat_tax_scenario_remain_numeric() -> None:
    result = _calculate(SEMANTIC_INPUTS["14-F10"])
    computed = _computed(result)
    expected = PAGE_07_GOLDENS["14-F10"]
    exact_keys = (
        "total_investment_cents",
        "annual_actual_rent_cents",
        "cash_costs_cents",
        "deductible_costs_cents",
        "monthly_annuity_cents",
        "annual_interest_cents",
        "annual_repayment_cents",
        "annual_debt_service_cents",
        "noi_cents",
        "afa_basis_cents",
        "annual_afa_cents",
        "net_yield_bp",
        "dscr_hundredths",
        "tax_base_cents",
        "tax_cents",
        "cashflow_before_year_cents",
        "cashflow_after_year_cents",
        "cashflow_after_month_cents",
        "equity_return_after_bp",
        "break_even_after_year_cents",
        "break_even_after_month_cents",
    )
    assert {key: computed[key] for key in exact_keys} == {key: expected[key] for key in exact_keys}
    assert computed["tax_cents"] < 0
    assert computed["cashflow_before_year_cents"] < 0
    assert computed["cashflow_after_year_cents"] < 0
    assert result["tax_scenario_label"] == expected["negative_tax_meaning"]
    assert _slots(result)["dscr"]["color"] == "red"
    assert _slots(result)["cashflow"]["color"] == "red"


def test_f11_factor_and_gross_are_independently_rounded_reciprocals() -> None:
    computed = _computed(_calculate(SEMANTIC_INPUTS["14-F11"]))
    expected = PAGE_07_GOLDENS["14-F11"]
    assert computed["factor_hundredths"] == expected["factor_hundredths"]
    assert computed["gross_yield_bp"] == expected["gross_yield_bp"]
    assert computed["factor_hundredths"] * computed["gross_yield_bp"] == expected["product"]
    assert _oracle_int(expected, "reciprocal_target") - _oracle_int(
        expected, "product"
    ) == _oracle_int(expected, "rounding_drift")


def test_f12_bank_view_uses_purchase_price_ltv_and_excludes_renter_names() -> None:
    result = _calculate(SEMANTIC_INPUTS["14-F12"])
    computed = _computed(result)
    expected = PAGE_07_GOLDENS["14-F12"]
    assert computed["ltv_purchase_bp"] == expected["ltv_purchase_bp"]
    assert computed["ltv_total_bp"] == expected["ltv_total_bp"]
    bank_view = result["bank_view"]
    assert bank_view["ltv_label"] == expected["ltv_label"]
    assert bank_view["renter_names_included"] is expected["renter_names_included"] is False
    assert bank_view["renderable"] is expected["partial_pdf_renderable"] is True
    assert "MUST NOT REACH BANK VIEW" not in str(bank_view)
    assert bank_view["layout_version"] == "bank-view-v1"
    assert bank_view["recalculated"] is False
    assert bank_view["disclosure"] == (
        "Vom Vermieter erstellte Zusammenfassung auf Basis eigener Angaben und Annahmen. "
        "Keine Immobilienbewertung, kein Beleihungswert, kein Gutachten, keine "
        "Bonitätsauskunft."
    )
    assert tuple(bank_view["blocks"]) == (
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
    repeated = _calculate(SEMANTIC_INPUTS["14-F12"])
    assert result["bank_view"] == repeated["bank_view"]


@pytest.mark.parametrize(
    "block_name",
    (
        "header_disclosure",
        "investment",
        "financing_ltv",
        "rent_and_planning_costs",
        "seven_kpis",
        "sensitivity",
        "twelve_month_schedule",
        "assumptions_method",
        "disclosure",
    ),
)
def test_f12_bank_view_contains_actual_data_for_every_declared_block(block_name: str) -> None:
    bank_view = _calculate(SEMANTIC_INPUTS["14-F12"])["bank_view"]
    assert block_name in bank_view
    assert bank_view[block_name]


def test_f12_bank_view_contains_frozen_investment_financing_rent_and_cost_data() -> None:
    result = _calculate(SEMANTIC_INPUTS["14-F12"])
    computed = _computed(result)
    bank_view = result["bank_view"]
    facts = SEMANTIC_INPUTS["14-F12"]
    assert bank_view["header_disclosure"]["header"] == facts["bank_header"]
    assert bank_view["investment"] == {
        "purchase_price_cents": facts["purchase_price_cents"],
        "acquisition_costs_cents": facts["acquisition_costs_cents"],
        "total_investment_cents": computed["total_investment_cents"],
    }
    financing = bank_view["financing_ltv"]
    for key in (
        "equity_cents",
        "loan_cents",
        "interest_bp",
        "initial_repayment_bp",
    ):
        assert financing[key] == facts[key]
    assert financing["monthly_annuity_cents"] == computed["monthly_annuity_cents"]
    assert financing["ltv_purchase_bp"] == computed["ltv_purchase_bp"]
    assert financing["ltv_total_bp"] == computed["ltv_total_bp"]
    assert financing["provenance"] == result["financing_provenance"]
    rent_and_costs = bank_view["rent_and_planning_costs"]
    for key in (
        "monthly_actual_rent_cents",
        "vacancy_bp",
        "administration_cents",
        "maintenance_cents",
        "reserve_cents",
        "vacancy_risk_cents",
    ):
        assert rent_and_costs[key] == facts[key]
    assert rent_and_costs["annual_actual_rent_cents"] == computed["annual_actual_rent_cents"]
    assert rent_and_costs["effective_rent_cents"] == computed["effective_rent_cents"]
    assert rent_and_costs["cash_costs_cents"] == computed["cash_costs_cents"]
    assert rent_and_costs["deductible_costs_cents"] == computed["deductible_costs_cents"]


def test_f12_bank_view_contains_frozen_kpis_sensitivity_and_schedule() -> None:
    result = _calculate(SEMANTIC_INPUTS["14-F12"])
    computed = _computed(result)
    bank_view = result["bank_view"]
    assert bank_view["seven_kpis"] == result["kpi_slots"]
    assert bank_view["sensitivity"] == {
        "interest": result["interest_sensitivity"],
        "repayment": result["repayment_sensitivity"],
    }
    assert bank_view["twelve_month_schedule"] == computed["schedule"]
    assert len(bank_view["twelve_month_schedule"]) == 12


def test_f12_bank_view_contains_versioned_assumptions_method_and_tax_provenance() -> None:
    result = _calculate(SEMANTIC_INPUTS["14-F12"])
    method = result["bank_view"]["assumptions_method"]
    definitions = method["convention_definitions"]
    assert tuple(definitions) == CONVENTION_IDS[:13]
    assert all(isinstance(text, str) and text.strip() for text in definitions.values())
    assert method["afa_provenance"] == result["afa_provenance"]
    assert method["financing_provenance"] == result["financing_provenance"]
    assert method["tax_provenance"] == result["tax_provenance"]
    assert method["source_evidence"] == result["source_evidence"]
    assert method["rechtsstand"] == result["rechtsstand"]
    assert method["production_blocked"] is True


def test_f12_bank_view_contains_both_required_disclosures() -> None:
    bank_view = _calculate(SEMANTIC_INPUTS["14-F12"])["bank_view"]
    assert bank_view["product_disclaimer"] == PRODUCT_DISCLAIMER
    assert bank_view["header_disclosure"]["product_disclaimer"] == PRODUCT_DISCLAIMER
    assert bank_view["header_disclosure"]["artifact_disclosure"] == bank_view["disclosure"]


def test_f12_bank_view_header_copies_only_approved_publication_keys() -> None:
    approved_header = {
        "address": "Musterstraße 1, 10115 Berlin",
        "property_type": "Mehrfamilienhaus",
        "year_built": 1978,
        "area_sqm_x100": 19_400,
        "unit_count": 3,
        "creator": "Beispiel Vermietung",
        "export_date": "2026-09-12",
        "layout_version": "bank-view-v1",
    }
    facts = _reference(
        financing_provenance="annahme",
        bank_header={
            **approved_header,
            "renter_identity": "MUST NOT REACH BANK VIEW",
            "iban": "DE00 0000 0000 0000 0000 00",
            "token": "secret-token",
            "account_id": "account-secret",
            "account_metadata": {"internal_reference": "secret"},
        },
    )
    bank_view = _calculate(facts)["bank_view"]
    assert bank_view["header"] == approved_header
    assert bank_view["header_disclosure"]["header"] == approved_header


def test_bank_view_validates_every_supplied_approved_header_value_before_publication() -> None:
    module = _api()
    invalid_headers: tuple[tuple[str, object], ...] = (
        ("address", 123),
        ("address", " "),
        ("property_type", 123),
        ("property_type", " "),
        ("creator", 123),
        ("creator", " "),
        ("year_built", "1978"),
        ("year_built", True),
        ("year_built", 0),
        ("area_sqm_x100", "19400"),
        ("area_sqm_x100", True),
        ("area_sqm_x100", -1),
        ("unit_count", "3"),
        ("unit_count", True),
        ("unit_count", -1),
        ("export_date", 20260912),
        ("export_date", " "),
        ("layout_version", 1),
        ("layout_version", " "),
    )
    failures: list[str] = []
    for field, invalid_value in invalid_headers:
        try:
            module.calculate_investment_snapshot(
                module.InvestmentInput(
                    facts=_reference(
                        financing_provenance="annahme",
                        bank_header={field: invalid_value},
                    )
                ),
                RuntimeInvestmentRuleBundle(),
            )
        except (TypeError, ValueError) as error:
            if field not in str(error):
                failures.append(f"{field}={invalid_value!r}: wrong error: {error}")
        except Exception as error:
            failures.append(f"{field}={invalid_value!r}: {type(error).__name__}: {error}")
        else:
            failures.append(f"{field}={invalid_value!r}: accepted")
    assert failures == [], "\n".join(failures)


def test_bank_view_keeps_missing_optional_header_values_missing() -> None:
    header = {"address": "Musterstraße 1, 10115 Berlin"}
    bank_view = _calculate(_reference(financing_provenance="annahme", bank_header=header))[
        "bank_view"
    ]
    assert bank_view["header"] == header
    assert bank_view["header_disclosure"]["header"] == header


def test_bank_view_layout_version_is_owned_by_runtime_input_without_engine_fallback() -> None:
    for layout_version in ("bank-layout-a", "bank-layout-b"):
        bank_view = _calculate(
            _reference(
                financing_provenance="annahme",
                bank_header={"layout_version": layout_version},
            )
        )["bank_view"]
        assert bank_view["layout_version"] == layout_version

    bank_view_without_layout = _calculate(
        _reference(financing_provenance="annahme", bank_header={})
    )["bank_view"]
    assert "layout_version" not in bank_view_without_layout


def test_f13_interest_sensitivity_is_five_complete_reruns_with_fixed_rent_kpis() -> None:
    result = _calculate(SEMANTIC_INPUTS["14-F13"])
    expected = PAGE_07_GOLDENS["14-F13"]
    rows = result["interest_sensitivity"]
    assert len(rows) == 5
    actual = tuple(
        (
            row["interest_bp"],
            row["monthly_annuity_cents"],
            row["annual_debt_service_cents"],
            row["annual_interest_cents"],
            row["annual_repayment_cents"],
            row["dscr_hundredths"],
            row["cashflow_after_month_cents"],
            row["equity_return_before_bp"],
            row["equity_return_after_bp"],
            row["break_even_after_month_cents"],
        )
        for row in rows
    )
    assert actual == expected["interest_steps"]
    assert tuple(row["interest_bp"] for row in rows) == (290, 340, 390, 440, 490)
    assert tuple(row["is_base"] for row in rows) == (False, False, True, False, False)
    assert all(row["factor_hundredths"] == 1_321 for row in rows)
    assert all(row["gross_yield_bp"] == 757 for row in rows)
    assert all(row["net_yield_bp"] == 542 for row in rows)
    assert rows[-1]["dscr_color"] == "amber"
    assert rows[-1]["cashflow_color"] == "amber"
    assert result["financing_provenance"]["source"] == "annahme"


def test_fixed_annuity_interest_sensitivity_retains_guarded_configured_rows() -> None:
    facts = _without(
        _reference(
            fixed_monthly_annuity_cents=120_000,
            financing_provenance="angebot",
        ),
        "initial_repayment_bp",
    )
    rows = _calculate(facts)["interest_sensitivity"]
    expected_interest_rates = (290, 340, 390, 440, 490)
    assert len(rows) == len(expected_interest_rates) == 5
    assert tuple(row["interest_bp"] for row in rows) == expected_interest_rates
    assert tuple(row["is_base"] for row in rows) == (False, False, True, False, False)

    expected_guards = (
        (440, 124_667, -4_667),
        (490, 138_833, -18_833),
    )
    for row, (interest_bp, first_interest_cents, first_repayment_cents) in zip(
        rows[-2:], expected_guards, strict=True
    ):
        assert set(row) == {"interest_bp", "is_base", "outcome", "guard"}
        assert row["interest_bp"] == interest_bp
        assert row["is_base"] is False
        assert row["outcome"] == "hard_block"
        guard = row["guard"]
        assert guard["first_interest_cents"] == first_interest_cents
        assert guard["first_repayment_cents"] == first_repayment_cents
        assert first_repayment_cents <= 0
        assert isinstance(guard["guard_text"], str) and guard["guard_text"].strip()


def test_f14_repayment_axis_shows_liquidity_and_debt_reduction_together() -> None:
    result = _calculate(SEMANTIC_INPUTS["14-F14"])
    expected = PAGE_07_GOLDENS["14-F14"]
    rows = result["repayment_sensitivity"]
    actual = tuple(
        (
            row["initial_repayment_bp"],
            row["monthly_annuity_cents"],
            row["annual_debt_service_cents"],
            row["dscr_hundredths"],
            row["cashflow_after_month_cents"],
            row["closing_balance_cents"],
            row["equity_return_after_bp"],
        )
        for row in rows
    )
    assert actual == expected["repayment_steps"]
    assert all(row["interest_bp"] == expected["constant_interest_bp"] for row in rows)
    assert result["repayment_axis_meaning"] == expected["axis_meaning"]
    assert [row["cashflow_after_month_cents"] for row in rows] == sorted(
        (row["cashflow_after_month_cents"] for row in rows), reverse=True
    )
    assert [row["closing_balance_cents"] for row in rows] == sorted(
        (row["closing_balance_cents"] for row in rows), reverse=True
    )
    assert rows[-1]["dscr_color"] == "red"
    assert rows[-1]["cashflow_color"] == "red"


def test_one_cent_loan_repayment_sensitivity_retains_all_guarded_configured_rows() -> None:
    facts = _without(
        _reference(
            loan_cents=1,
            fixed_monthly_annuity_cents=1,
            financing_provenance="angebot",
        ),
        "initial_repayment_bp",
    )
    rows = _calculate(facts)["repayment_sensitivity"]
    expected_steps = RuntimeInvestmentRuleBundle().repayment_sensitivity_steps_bp
    assert len(rows) == len(expected_steps) == 4
    assert tuple(row["initial_repayment_bp"] for row in rows) == expected_steps
    for row, repayment_bp in zip(rows, expected_steps, strict=True):
        assert set(row) == {"initial_repayment_bp", "outcome", "guard"}
        assert row["initial_repayment_bp"] == repayment_bp
        assert row["outcome"] == "hard_block"
        guard = row["guard"]
        assert guard["first_interest_cents"] == 0
        assert guard["first_repayment_cents"] == 0
        assert isinstance(guard["guard_text"], str) and guard["guard_text"].strip()


def test_e02_zero_or_missing_denominators_return_incomplete_dash_not_zero_or_error() -> None:
    cases: tuple[dict[str, object], ...] = (
        {"purchase_price_cents": 0, "monthly_actual_rent_cents": 115_000},
        {"purchase_price_cents": 31_000_000, "monthly_actual_rent_cents": 0},
        {"monthly_actual_rent_cents": 115_000},
    )
    for facts in cases:
        slots = _slots(_calculate(facts))
        for name in ("factor", "gross_yield"):
            slot = slots[name]
            assert slot["status"] == "unavailable"
            assert slot["value"] == DASH
            assert slot["badge"] == INCOMPLETE_BADGE


def test_e09_zero_tax_rate_makes_before_and_after_values_equal() -> None:
    result = _calculate(_reference(marginal_tax_bp=0, financing_provenance="annahme"))
    computed = _computed(result)
    assert computed["tax_cents"] == 0
    assert computed["cashflow_before_year_cents"] == computed["cashflow_after_year_cents"]
    assert computed["cashflow_before_month_cents"] == computed["cashflow_after_month_cents"]
    assert computed["equity_return_before_bp"] == computed["equity_return_after_bp"]
    assert computed["break_even_before_month_cents"] == computed["break_even_after_month_cents"]


def test_e10_non_twelve_month_input_is_normalized_to_a_full_year() -> None:
    result = _calculate(_reference(analysis_period_months=6, financing_provenance="annahme"))
    computed = _computed(result)
    assert computed["normalized_period_months"] == 12
    assert (
        computed["annual_actual_rent_cents"] == REFERENCE_INPUTS["monthly_actual_rent_cents"] * 12
    )
    assert "non_12_month_period_inapplicable" in result["findings"]


def test_e11_unrealistic_acquisition_costs_warn_but_do_not_block() -> None:
    result = _calculate(
        _reference(acquisition_costs_cents=50_000_000, financing_provenance="annahme")
    )
    assert result["outcome"] != "hard_block"
    assert _computed(result)
    assert "unrealistic_acquisition_costs" in result["warnings"]


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    (
        ("purchase_price_cents", 0),
        ("purchase_price_cents", -1),
        ("acquisition_costs_cents", -1),
        ("monthly_actual_rent_cents", -1),
        ("administration_cents", -1),
        ("maintenance_cents", -1),
        ("reserve_cents", -1),
        ("vacancy_risk_cents", -1),
        ("equity_cents", -1),
        ("loan_cents", -1),
        ("vacancy_bp", -1),
        ("vacancy_bp", 10_001),
        ("interest_bp", -1),
        ("initial_repayment_bp", -1),
        ("marginal_tax_bp", -1),
        ("marginal_tax_bp", 10_000),
        ("building_share_bp", -1),
        ("building_share_bp", 10_001),
        ("afa_rate_bp", -1),
    ),
)
def test_full_public_input_rejects_invalid_documented_ranges(
    field: str, invalid_value: int
) -> None:
    module = _api()
    facts = _reference(financing_provenance="annahme")
    facts[field] = invalid_value
    with pytest.raises(ValueError, match=field):
        module.calculate_investment_snapshot(
            module.InvestmentInput(facts=facts), RuntimeInvestmentRuleBundle()
        )


def test_partial_public_input_rejects_every_supplied_invalid_type_before_completeness() -> None:
    module = _api()
    invalid_facts = (
        *(
            (field, {field: "not-an-integer"})
            for field in (
                "purchase_price_cents",
                "acquisition_costs_cents",
                "monthly_actual_rent_cents",
                "vacancy_bp",
                "administration_cents",
                "maintenance_cents",
                "reserve_cents",
                "vacancy_risk_cents",
                "equity_cents",
                "loan_cents",
                "interest_bp",
                "initial_repayment_bp",
                "fixed_monthly_annuity_cents",
                "marginal_tax_bp",
                "building_share_bp",
                "afa_rate_bp",
                "annual_full_afa_cents",
            )
        ),
        (
            "afa_basis_cents",
            {
                "afa_reference": {
                    "source": "wizard",
                    "afa_basis_cents": "not-an-integer",
                }
            },
        ),
        (
            "annual_full_afa_cents",
            {
                "afa_reference": {
                    "source": "wizard",
                    "annual_full_afa_cents": "not-an-integer",
                }
            },
        ),
    )
    failures: list[str] = []
    for field, facts in invalid_facts:
        try:
            module.calculate_investment_snapshot(
                module.InvestmentInput(facts=facts),
                RuntimeInvestmentRuleBundle(),
            )
        except TypeError as error:
            if field not in str(error):
                failures.append(f"{field}: wrong TypeError: {error}")
        except Exception as error:
            failures.append(f"{field}: {type(error).__name__}: {error}")
        else:
            failures.append(f"{field}: accepted")
    assert failures == [], "\n".join(failures)


def test_partial_public_input_rejects_invalid_documented_ranges_before_completeness() -> None:
    module = _api()
    invalid_facts = (
        ("purchase_price_cents", {"purchase_price_cents": -1}),
        ("acquisition_costs_cents", {"acquisition_costs_cents": -1}),
        ("monthly_actual_rent_cents", {"monthly_actual_rent_cents": -1}),
        ("vacancy_bp", {"vacancy_bp": -1}),
        ("vacancy_bp", {"vacancy_bp": 10_001}),
        ("administration_cents", {"administration_cents": -1}),
        ("maintenance_cents", {"maintenance_cents": -1}),
        ("reserve_cents", {"reserve_cents": -1}),
        ("vacancy_risk_cents", {"vacancy_risk_cents": -1}),
        ("equity_cents", {"equity_cents": -1}),
        ("loan_cents", {"loan_cents": -1}),
        ("interest_bp", {"interest_bp": -1}),
        ("initial_repayment_bp", {"initial_repayment_bp": -1}),
        ("fixed_monthly_annuity_cents", {"fixed_monthly_annuity_cents": -1}),
        ("marginal_tax_bp", {"marginal_tax_bp": -1}),
        ("marginal_tax_bp", {"marginal_tax_bp": 10_000}),
        ("building_share_bp", {"building_share_bp": -1}),
        ("building_share_bp", {"building_share_bp": 10_001}),
        ("afa_rate_bp", {"afa_rate_bp": -1}),
        ("annual_full_afa_cents", {"annual_full_afa_cents": -1}),
        (
            "afa_basis_cents",
            {"afa_reference": {"source": "wizard", "afa_basis_cents": -1}},
        ),
        (
            "annual_full_afa_cents",
            {"afa_reference": {"source": "wizard", "annual_full_afa_cents": -1}},
        ),
    )
    failures: list[str] = []
    for field, facts in invalid_facts:
        try:
            module.calculate_investment_snapshot(
                module.InvestmentInput(facts=facts), RuntimeInvestmentRuleBundle()
            )
        except ValueError as error:
            if field not in str(error):
                failures.append(f"{field}: wrong ValueError: {error}")
        except Exception as error:
            failures.append(f"{field}: {type(error).__name__}: {error}")
        else:
            failures.append(f"{field}: accepted")
    assert failures == [], "\n".join(failures)


def test_runtime_rule_values_reject_invalid_documented_ranges_before_use() -> None:
    module = _api()
    base = RuntimeInvestmentRuleBundle()
    invalid_rules = (
        (
            "default_building_share_bp",
            replace(base, default_building_share_bp=-1),
        ),
        (
            "default_building_share_bp",
            replace(base, default_building_share_bp=10_001),
        ),
        ("default_afa_rate_bp", replace(base, default_afa_rate_bp=-1)),
        (
            "default_marginal_tax_bp",
            replace(base, default_marginal_tax_bp=-1),
        ),
        (
            "default_marginal_tax_bp",
            replace(base, default_marginal_tax_bp=10_000),
        ),
        (
            "interest_sensitivity_offsets_bp",
            replace(base, interest_sensitivity_offsets_bp=(-391, -50, 0, 50, 100)),
        ),
        (
            "interest_sensitivity_offsets_bp",
            replace(base, interest_sensitivity_offsets_bp=(-100, -50, 50, 100)),
        ),
        (
            "repayment_sensitivity_steps_bp",
            replace(base, repayment_sensitivity_steps_bp=(100, -1, 300, 400)),
        ),
        (
            "dscr_amber_hundredths",
            replace(base, dscr_amber_hundredths=-1),
        ),
        (
            "dscr_green_hundredths",
            replace(base, dscr_green_hundredths=-1),
        ),
        (
            "dscr_amber_hundredths",
            replace(base, dscr_amber_hundredths=121, dscr_green_hundredths=120),
        ),
        (
            "cashflow_amber_cents",
            replace(base, cashflow_amber_cents=5_001, cashflow_green_cents=5_000),
        ),
    )
    failures: list[str] = []
    for field, rules in invalid_rules:
        try:
            module.calculate_investment_snapshot(
                module.InvestmentInput(facts=_reference(financing_provenance="annahme")),
                rules,
            )
        except ValueError as error:
            if field not in str(error):
                failures.append(f"{field}: wrong ValueError: {error}")
        except Exception as error:
            failures.append(f"{field}: {type(error).__name__}: {error}")
        else:
            failures.append(f"{field}: accepted")
    assert failures == [], "\n".join(failures)


def test_runtime_repayment_sensitivity_steps_are_strictly_positive_ordered_and_complete() -> None:
    module = _api()
    base = RuntimeInvestmentRuleBundle()
    for invalid_steps in ((0, 100, 200, 300), (200, 100, 300, 400)):
        with pytest.raises(ValueError, match="repayment_sensitivity_steps_bp"):
            module.calculate_investment_snapshot(
                module.InvestmentInput(facts=_reference(financing_provenance="annahme")),
                replace(base, repayment_sensitivity_steps_bp=invalid_steps),
            )

    result = _plain(
        module.calculate_investment_snapshot(
            module.InvestmentInput(facts=_reference(financing_provenance="annahme")),
            base,
        )
    )
    rows = result["repayment_sensitivity"]
    assert len(rows) == len(base.repayment_sensitivity_steps_bp) == 4
    assert tuple(row["initial_repayment_bp"] for row in rows) == (
        base.repayment_sensitivity_steps_bp
    )


def test_runtime_source_evidence_and_rechtsstand_reject_blank_metadata() -> None:
    module = _api()
    base = RuntimeInvestmentRuleBundle()
    invalid_rules = (
        ("source_evidence", replace(base, source_evidence=())),
        ("source_evidence", replace(base, source_evidence=("",))),
        ("source_evidence", replace(base, source_evidence=("docs/14@07/2026", " "))),
        ("rechtsstand", replace(base, rechtsstand="")),
        ("rechtsstand", replace(base, rechtsstand=" ")),
    )
    failures: list[str] = []
    for field, rules in invalid_rules:
        try:
            module.calculate_investment_snapshot(
                module.InvestmentInput(facts=_reference(financing_provenance="annahme")),
                rules,
            )
        except ValueError as error:
            if field not in str(error):
                failures.append(f"{field}: wrong ValueError: {error}")
        except Exception as error:
            failures.append(f"{field}: {type(error).__name__}: {error}")
        else:
            failures.append(f"{field}: accepted")
    assert failures == [], "\n".join(failures)


def test_e15_repayment_control_clamps_at_non_positive_repayment_guard() -> None:
    module = _api()
    guard = _plain(
        module.clamp_repayment_control(
            loan_cents=34_000_000,
            interest_bp=390,
            requested_monthly_annuity_cents=100_000,
            rules=RuntimeInvestmentRuleBundle(),
        )
    )
    expected = PAGE_07_GOLDENS["14-F09"]
    assert guard["requested_monthly_annuity_cents"] == expected["monthly_annuity_cents"]
    assert guard["first_interest_cents"] == expected["first_interest_cents"]
    assert guard["applied_monthly_annuity_cents"] > guard["first_interest_cents"]
    assert guard["clamped"] is True
    assert isinstance(guard["guard_text"], str) and guard["guard_text"].strip()


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    (
        ("loan_cents", -1),
        ("interest_bp", -1),
        ("requested_monthly_annuity_cents", -1),
    ),
)
def test_public_repayment_control_rejects_negative_inputs_before_calculation(
    field: str, invalid_value: int
) -> None:
    module = _api()
    arguments = {
        "loan_cents": 34_000_000,
        "interest_bp": 390,
        "requested_monthly_annuity_cents": 180_000,
        "rules": RuntimeInvestmentRuleBundle(),
    }
    arguments[field] = invalid_value
    with pytest.raises(ValueError, match=field):
        module.clamp_repayment_control(**arguments)


def test_conventions_are_exposed_without_overall_score_target_or_recommendation() -> None:
    result = _calculate(SEMANTIC_INPUTS["14-F01"])
    assert result["applied_conventions"] == CONVENTION_IDS
    assert result["financing_provenance"]["source"] == "annahme"
    assert result["financing_provenance"]["badge"]
    assert result["afa_provenance"]["assumption"] is True
    assert result["afa_provenance"]["building_share_bp"] == 7_500
    assert result["afa_provenance"]["afa_rate_bp"] == 200
    assert result["tax_provenance"]["marginal_tax_bp"] == 4_200
    forbidden = {"overall_score", "purchase_decision", "winner", "default_target_return"}
    assert forbidden.isdisjoint(result)
    assert forbidden.isdisjoint(_computed(result))


def test_runtime_defaults_are_labelled_assumptions_and_not_engine_constants() -> None:
    facts = _without(
        _reference(financing_provenance="annahme"),
        "building_share_bp",
        "afa_rate_bp",
        "marginal_tax_bp",
    )
    result = _calculate(facts)
    computed = _computed(result)
    expected = PAGE_07_GOLDENS["14-F01"]
    assert computed["annual_afa_cents"] == expected["annual_afa_cents"]
    assert computed["tax_cents"] == expected["tax_cents"]
    assert result["afa_provenance"]["assumption"] is True
    assert result["afa_provenance"]["building_share_bp"] == 7_500
    assert result["afa_provenance"]["afa_rate_bp"] == 200
    assert result["tax_provenance"]["assumption"] is True
    assert result["tax_provenance"]["marginal_tax_bp"] == 4_200


def test_three_rent_kpis_do_not_require_financing_but_four_financing_kpis_do() -> None:
    facts = _without(
        _reference(financing_provenance="annahme"),
        "equity_cents",
        "loan_cents",
        "interest_bp",
        "initial_repayment_bp",
    )
    slots = _slots(_calculate(facts))
    assert all(slots[name]["status"] == "available" for name in KPI_NAMES[:3])
    for name in KPI_NAMES[3:]:
        assert slots[name]["status"] == "unavailable"
        assert slots[name]["value"] == DASH
        assert slots[name]["badge"] == INCOMPLETE_BADGE


@pytest.mark.parametrize("source", ("annahme", "indikativ", "angebot"))
def test_financing_source_is_retained_and_labelled(source: str) -> None:
    result = _calculate(_reference(financing_provenance=source))
    assert result["financing_provenance"]["source"] == source
    assert result["financing_provenance"]["badge"]


def test_liquidity_colours_follow_only_the_versioned_rule_thresholds() -> None:
    negative = _calculate(SEMANTIC_INPUTS["14-F10"])
    reference = _calculate(SEMANTIC_INPUTS["14-F01"])
    interest = _calculate(SEMANTIC_INPUTS["14-F13"])["interest_sensitivity"][-1]
    assert _slots(negative)["dscr"]["color"] == "red"
    assert _slots(negative)["cashflow"]["color"] == "red"
    assert _slots(reference)["dscr"]["color"] == "green"
    assert _slots(reference)["cashflow"]["color"] == "green"
    assert interest["dscr_color"] == "amber"
    assert interest["cashflow_color"] == "amber"


def test_exact_outputs_use_integer_cents_basis_points_or_decimal_never_float() -> None:
    for facts in SEMANTIC_INPUTS.values():
        result = _calculate(facts)
        _assert_no_float(result)


def test_rules_are_runtime_inputs_and_engine_contains_no_fixture_or_rate_dispatch() -> None:
    module = _api()
    rule_fields = set(inspect.signature(module.InvestmentRuleBundle).parameters)
    assert {
        "default_building_share_bp",
        "default_afa_rate_bp",
        "default_marginal_tax_bp",
        "interest_sensitivity_offsets_bp",
        "repayment_sensitivity_steps_bp",
        "dscr_amber_hundredths",
        "dscr_green_hundredths",
        "cashflow_amber_cents",
        "cashflow_green_cents",
        "source_evidence",
        "rechtsstand",
        "production_blocked",
    } <= rule_fields
    source = inspect.getsource(module)
    assert "fixture_id" not in source
    assert "14-F" not in source
    assert "berkay_14_golden" not in source
    assert "rules-store" not in source
    for forbidden_rate in (
        "default_building_share_bp = 7500",
        "default_afa_rate_bp = 200",
        "default_marginal_tax_bp = 4200",
        "return 7500",
        "return 4200",
    ):
        assert forbidden_rate not in source
