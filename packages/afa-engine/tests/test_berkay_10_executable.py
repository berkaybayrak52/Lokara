"""Semantic M7-A contract for approved Page-03 fixtures 10-F01…10-F34.

Expected values come from the approved oracle, but are never passed to the
engine. Incomplete raw cases remain explicit evidence-only traces.
"""

from __future__ import annotations

import importlib
import inspect
import sys
from dataclasses import asdict, dataclass, is_dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ORACLE_DIR = Path(__file__).resolve().parents[2] / "rules-store" / "tests"
sys.path.insert(0, str(ORACLE_DIR))

from berkay_10_golden import PAGE_03_GOLDENS  # noqa: E402


@dataclass(frozen=True)
class RuntimeAfaRuleBundle:
    linear_rates_bp: tuple[tuple[int | None, int | None, int], ...] = (
        (None, 1924, 250),
        (1925, 2022, 200),
        (2023, None, 300),
    )
    guard_rate_bp: int = 1_500
    market_disagio_limit_bp: int = 500
    source_evidence: tuple[str, ...] = ("docs/10-afa.md@08/2026",)
    rechtsstand: str = "07/2026"
    production_blocked: bool = True


def _api() -> ModuleType:
    return importlib.import_module("afa_engine")


def _mapping(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        result = dump()
        assert isinstance(result, dict)
        return result
    raise AssertionError("AfaResult must be a mapping, dataclass or Pydantic model")


def _calculate(facts: dict[str, object], tax_year: int = 2025) -> dict[str, Any]:
    module = _api()
    input_type = module.AfaInput
    assert "fixture_id" not in inspect.signature(input_type).parameters
    result = module.calculate_afa_record(
        input_type(facts=facts), RuntimeAfaRuleBundle(), tax_year=tax_year
    )
    values = _mapping(result)
    assert "golden_values" not in values, "engine must calculate, never echo expected fixture data"
    assert values["rechtsstand"] == "07/2026"
    assert values["production_blocked"] is True
    assert tuple(values["source_evidence"]) == tuple(sorted(values["source_evidence"], key=str))
    return values


def _computed(result: dict[str, Any]) -> dict[str, object]:
    values = result.get("calculated_values")
    assert isinstance(values, dict), "AfaResult.calculated_values is missing"
    return values


SEMANTIC_INPUTS: dict[str, dict[str, object]] = {
    "10-F01": {
        "erwerbsart": "kauf",
        "kaufpreis_cents": 48_000_000,
        "grunderwerbsteuer_cents": 3_120_000,
        "notar_grundbuch_cents": 720_000,
        "grundschuld_notar_cents": 45_000,
        "makler_cents": 1_713_600,
        "sonstige_ank_cents": 0,
        "movable_assets_cents": 0,
    },
    "10-F02": {
        "allocation_route": "bmf",
        "acquisition_cost_cents": 53_553_600,
        "land_area_sqm": 420,
        "land_value_cents_per_sqm": 34_000,
        "living_area_sqm_x100": 19_400,
        "building_type": "mfh",
        "nhk_cents_per_sqm_bgf": 72_500,
        "price_index_bp": 18_000,
        "year_built": 1978,
        "valuation_year": 2024,
        "useful_life_years": 80,
        "minimum_residual_bp": 3_000,
    },
    "10-F03": {
        "acquisition_cost_cents": 53_553_600,
        "contract_building_cents": 41_771_808,
        "contract_land_cents": 11_781_792,
        "comparison_bmf_building_cents": 27_005_129,
        "comparison_bmf_land_cents": 26_548_471,
        "year_built": 1978,
    },
    "10-F04": {"building_basis_cents": 27_005_129, "year_built": 1978},
    "10-F05": {
        "building_basis_cents": 45_000_000,
        "year_built": 2024,
        "completion_date": "2024-08-15",
    },
    "10-F06": {"building_basis_cents": 30_000_000, "year_built": 1912},
    "10-F07": {
        "building_basis_cents": 27_005_129,
        "year_built": 1978,
        "transfer_date": "2024-03-15",
    },
    "10-F08": {
        "building_basis_cents": 27_005_129,
        "year_built": 1978,
        "transfer_date": "2024-12-20",
    },
    "10-F09": {
        "annual_afa_cents": 540_103,
        "rented_area_months_x100": 158_400,
        "total_area_months_x100": 232_800,
    },
    "10-F10": {
        "annual_afa_cents": 540_103,
        "rented_area_months_x100": 195_600,
        "total_area_months_x100": 232_800,
    },
    "10-F11": {
        "annual_afa_cents": 540_103,
        "rented_area_months_x100": 195_600,
        "total_area_months_x100": 232_800,
        "started_rental_month_counts_fully": True,
    },
    "10-F12": {
        "annual_afa_cents": 540_103,
        "rented_area_months_x100": 189_400,
        "total_area_months_x100": 232_800,
    },
    "10-F13": {
        "building_basis_cents": 27_005_129,
        "year_built": 1978,
        "transfer_date": "2024-03-15",
        "series_start_year": 2024,
    },
    "10-F14": {
        "building_basis_cents": 27_005_129,
        "year_built": 1978,
        "opening_book_value_cents": 24_934_734,
        "sale_date": "2028-08-15",
    },
    "10-F15": {
        "building_basis_cents": 27_005_129,
        "guard_rate_bp": 1_500,
        "counted_measure_cents": (1_850_000, 920_000, 620_000, 480_000),
    },
    "10-F16": {
        "building_basis_cents": 27_005_129,
        "guard_rate_bp": 1_500,
        "counted_measures_by_year": ((2024, 2_770_000), (2025, 620_000), (2026, 1_730_000)),
        "rate_bp": 200,
    },
    "10-F17": {
        "building_basis_cents": 27_005_129,
        "previous_counted_cents": 3_870_000,
        "measures": (
            {
                "net_cents": 2_200_000,
                "class": "erweiterung",
                "leistung_bis": "2025-06-30",
            },
        ),
    },
    "10-F18": {
        "building_basis_cents": 27_005_129,
        "previous_counted_cents": 3_870_000,
        "measures": tuple(
            {
                "net_cents": amount,
                "class": "jaehrlichUeblich",
                "leistung_bis": f"{year}-12-31",
            }
            for year in (2024, 2025, 2026)
            for amount in (38_000, 12_000, 8_400)
        ),
    },
    "10-F19": {
        "building_basis_cents": 27_005_129,
        "guard_rate_bp": 1_500,
        "transfer_date": "2024-03-15",
        "previous_counted_cents": 3_870_000,
        "measures": (
            {"net_cents": 150_000, "leistung_bis": "2027-03-10"},
            {"net_cents": 900_000, "leistung_bis": "2027-03-20"},
        ),
    },
    "10-F20": {
        "building_basis_cents": 27_005_129,
        "later_production_cost_cents": 2_200_000,
        "rate_bp": 200,
        "opening_book_value_cents": 26_555_043,
    },
    "10-F21": {
        "nominal_cents": 40_000_000,
        "interest_bp": 360,
        "initial_repayment_bp": 200,
        "installment_count": 9,
        "day_count": "30/360",
    },
    "10-F22": {
        "nominal_cents": 40_000_000,
        "market_disagio_cents": 1_200_000,
        "non_market_disagio_cents": 3_200_000,
        "fixed_interest_years": 10,
        "first_year_months": 9,
    },
    "10-F23": {
        "nominal_cents": 40_000_000,
        "interest_bp": 360,
        "initial_repayment_bp": 200,
        "installment_count": 9,
        "special_repayment_cents": 500_000,
        "special_repayment_before_installment": 8,
        "day_count": "30/360",
    },
    "10-F24": {
        "interest_cents": 1_072_748,
        "rented_area_months_x100": 158_400,
        "total_area_months_x100": 232_800,
        "assignment": "object_proportional",
    },
    "10-F25": {
        "erwerbsart": "kauf",
        "allocation_route": "bmf",
        "kaufpreis_cents": 48_000_000,
        "grunderwerbsteuer_cents": 3_120_000,
        "notar_grundbuch_cents": 720_000,
        "grundschuld_notar_cents": 45_000,
        "makler_cents": 1_713_600,
        "sonstige_ank_cents": 0,
        "movable_assets_cents": 0,
        "land_area_sqm": 420,
        "land_value_cents_per_sqm": 34_000,
        "living_area_sqm_x100": 19_400,
        "building_type": "mfh",
        "nhk_cents_per_sqm_bgf": 72_500,
        "price_index_bp": 18_000,
        "year_built": 1978,
        "valuation_year": 2024,
        "useful_life_years": 80,
        "minimum_residual_bp": 3_000,
        "bmf_building_value_cents": 14_525_629,
        "bmf_property_value_cents": 28_805_629,
    },
    "10-F26": {"allocation_route": "bmf", "land_value_cents_per_sqm": None},
    "10-F27": {"building_basis_cents": 27_005_129, "year_built": None},
    "10-F28": {
        "allocation_route": "contract",
        "acquisition_cost_cents": 53_553_600,
        "contract_building_share_bp": 9_600,
        "year_built": 1978,
    },
    "10-F30": {
        "building_basis_cents": 27_005_129,
        "year_built": 1978,
        "transfer_date": None,
        "notary_date": "2024-02-12",
    },
    "10-F31": {
        "total_area_sqm_x100": 19_400,
        "self_use_periods": (
            {"area_sqm_x100": 21_000, "from": "2025-01-01", "to": "2025-12-31"},
            {"area_sqm_x100": 1, "from": "2025-06-01", "to": "2025-08-31"},
        ),
    },
    "10-F32": {
        "acquisition_type": "unentgeltlich",
        "predecessor_basis_cents": 18_000_000,
        "rate_bp": 200,
        "predecessor_accumulated_afa_cents": 5_400_000,
        "predecessor_months": 4,
        "successor_months": 8,
    },
    "10-F33": {
        "building_basis_cents": 27_005_129,
        "remaining_life_years": 25,
        "report_qualification": "oebuv",
    },
    "10-F34": {
        "allocation_route": "bmf",
        "purchase_price_cents": 48_000_000,
        "movable_assets_cents": 800_000,
        "ancillary_cost_cents": 5_553_600,
        "land_area_sqm": 420,
        "land_value_cents_per_sqm": 34_000,
        "living_area_sqm_x100": 19_400,
        "building_type": "mfh",
        "nhk_cents_per_sqm_bgf": 72_500,
        "price_index_bp": 18_000,
        "year_built": 1978,
        "valuation_year": 2024,
        "useful_life_years": 80,
        "minimum_residual_bp": 3_000,
    },
}

EVIDENCE_ONLY_IDS = frozenset(PAGE_03_GOLDENS) - set(SEMANTIC_INPUTS)


def test_only_f29_remains_evidence_only_after_docs_10_raw_input_reconciliation() -> None:
    assert {"10-F29"} == EVIDENCE_ONLY_IDS


@pytest.mark.parametrize("fixture_id", tuple(PAGE_03_GOLDENS))
def test_every_fixture_executes_without_expected_output_input(fixture_id: str) -> None:
    if fixture_id in EVIDENCE_ONLY_IDS:
        result = _calculate(
            {
                "allocation_route": "bmf",
                "year_built": 1930,
                "valuation_year": 2024,
                "useful_life_years": 80,
                "minimum_residual_bp": 3_000,
            }
        )
        assert result["production_blocked"] is True
        assert result["evidence_limit"] == "approved raw inputs are incomplete"
        assert result["calculated_values"] == {}
    else:
        assert _computed(_calculate(SEMANTIC_INPUTS[fixture_id]))


def test_acquisition_bmf_rates_and_month_rounding_are_computed() -> None:
    keys_by_case = {
        "10-F01": ("ancillary", "acquisition_cost"),
        "10-F02": ("building_cost", "land_cost", "production_blocked"),
        "10-F04": ("rate_bp", "annual_afa"),
        "10-F05": ("rate_bp", "annual_afa", "months", "first_year_afa"),
        "10-F06": ("rate_bp", "annual_afa"),
        "10-F07": ("months", "first_year_afa"),
        "10-F08": ("months", "first_year_afa", "twelve_month_product"),
    }
    for fixture_id, keys in keys_by_case.items():
        computed = _computed(_calculate(SEMANTIC_INPUTS[fixture_id], 2024))
        for key in keys:
            assert computed[key] == PAGE_03_GOLDENS[fixture_id][key]
    assert (
        _computed(_calculate(SEMANTIC_INPUTS["10-F01"]))["excluded_financing_cost_cents"] == 45_000
    )


@pytest.mark.parametrize("fixture_id", ("10-F09", "10-F10", "10-F11", "10-F12"))
def test_self_use_area_months_compute_deductible_afa(fixture_id: str) -> None:
    computed = _computed(_calculate(SEMANTIC_INPUTS[fixture_id]))
    expected = PAGE_03_GOLDENS[fixture_id]
    assert computed["deductible_afa"] == expected.get(
        "deductible_afa", expected.get("selected_result")
    )
    assert computed["non_deductible_afa"] == expected.get(
        "non_deductible_afa", expected.get("month_non_deductible")
    )
    if fixture_id == "10-F11":
        assert computed["verification_flag"] == "verify-before-production"


def test_guard_later_cost_finance_and_predecessor_strands_are_computed() -> None:
    expected_keys = {
        "10-F15": ("threshold", "cumulative", "buffer", "status"),
        "10-F16": ("threshold", "cumulative", "basis_by_year", "new_afa", "afa_delta"),
        "10-F19": ("cumulative", "buffer", "counterfactual_cumulative"),
        "10-F20": ("new_basis", "new_annual_afa", "closing_book_value"),
        "10-F21": ("monthly_annuity", "interest_schedule", "repayment_schedule", "closing_balance"),
        "10-F22": (
            "market_first_year_deduction",
            "non_market_first_year",
            "non_market_final_residual",
        ),
        "10-F23": ("interest_year", "interest_saving", "total_repayment", "closing_balance"),
        "10-F24": ("proportional_deductible", "proportional_non_deductible"),
        "10-F32": ("annual_afa", "opening_book_value", "predecessor_share", "successor_share"),
        "10-F33": ("annual_afa", "final_residual"),
        "10-F34": ("purchase_after_split", "acquisition_cost", "building_cost", "land_cost"),
    }
    for fixture_id, keys in expected_keys.items():
        computed = _computed(_calculate(SEMANTIC_INPUTS[fixture_id]))
        for key in keys:
            assert computed[key] == PAGE_03_GOLDENS[fixture_id][key]
    assert _computed(_calculate(SEMANTIC_INPUTS["10-F19"]))["required_date_field"] == "leistungBis"


@pytest.mark.parametrize("fixture_id", ("10-F26", "10-F27", "10-F30", "10-F31"))
def test_missing_or_invalid_normalized_inputs_hard_block(fixture_id: str) -> None:
    computed = _computed(_calculate(SEMANTIC_INPUTS[fixture_id]))
    assert computed["result"] == "hard_block"


def test_exact_outputs_use_integer_cents_or_decimal_never_float() -> None:
    values = _computed(_calculate(SEMANTIC_INPUTS["10-F04"]))
    assert values and all(not isinstance(value, float) for value in values.values())
    assert isinstance(values["annual_afa"], (int, Decimal))


@pytest.mark.parametrize(
    ("fixture_id", "expected_keys"),
    (
        ("10-F03", ("contract_building", "bmf_building", "annual_afa_delta", "warning")),
        ("10-F13", ("first_year_afa", "final_year", "final_residual", "final_book_value")),
        ("10-F14", ("months", "sale_year_afa", "closing_book_value")),
        ("10-F17", ("countable_for_15_percent", "later_production_cost", "cumulative")),
        ("10-F18", ("annual_total", "three_year_total", "countable_for_15_percent")),
        ("10-F25", ("correct_acquisition_cost", "immediate_financing_cost", "correct_annual_afa")),
        ("10-F28", ("building_cost", "land_cost", "annual_afa", "blocking")),
    ),
)
def test_previously_evidence_only_cases_now_use_approved_raw_inputs(
    fixture_id: str, expected_keys: tuple[str, ...]
) -> None:
    computed = _computed(_calculate(SEMANTIC_INPUTS[fixture_id]))
    for key in expected_keys:
        assert computed[key] == PAGE_03_GOLDENS[fixture_id][key]


def test_f25_uses_the_exact_approved_bmf_fraction_not_a_rounded_basis_point_share() -> None:
    facts = SEMANTIC_INPUTS["10-F25"]
    assert "building_share_bp" not in facts
    numerator = facts["bmf_building_value_cents"]
    denominator = facts["bmf_property_value_cents"]
    assert isinstance(numerator, int)
    assert isinstance(denominator, int)
    assert numerator == PAGE_03_GOLDENS["10-F02"]["building_value"]
    assert denominator == PAGE_03_GOLDENS["10-F02"]["property_value"]
    acquisition_cost = PAGE_03_GOLDENS["10-F25"]["correct_acquisition_cost"]
    assert isinstance(acquisition_cost, int)
    allocated = (Decimal(acquisition_cost) * Decimal(numerator) / Decimal(denominator)).quantize(
        Decimal(1), rounding=ROUND_HALF_UP
    )
    assert int(allocated) == PAGE_03_GOLDENS["10-F25"]["correct_building_cost"]


def test_gutachten_route_without_an_approved_share_is_evidence_only_and_blocked() -> None:
    result = _calculate(
        {
            "allocation_route": "gutachten",
            "acquisition_cost_cents": 53_553_600,
            "report_document_id": "report-without-approved-share",
            "report_building_share_bp": None,
        }
    )
    assert result["production_blocked"] is True
    assert result["calculated_values"] == {}
    assert any("gutachten" in str(finding).lower() for finding in result["findings"])


def test_rules_are_resolved_inputs_and_engine_contains_no_fixture_or_legal_rate_dispatch() -> None:
    module = _api()
    bundle_fields = set(inspect.signature(module.AfaRuleBundle).parameters)
    assert {
        "linear_rates_bp",
        "guard_rate_bp",
        "market_disagio_limit_bp",
        "source_evidence",
        "rechtsstand",
        "production_blocked",
    } <= bundle_fields
    source = inspect.getsource(module)
    assert "fixture_id" not in source
    assert "10-F" not in source
    for forbidden_rate in ("1_500", "guard_rate_bp = 1500", "return 250", "return 200"):
        assert forbidden_rate not in source


def test_disagio_maintenance_and_interest_emit_page04_handoff_without_dedup_guessing() -> None:
    for facts in (
        SEMANTIC_INPUTS["10-F16"],
        SEMANTIC_INPUTS["10-F22"],
        SEMANTIC_INPUTS["10-F24"],
    ):
        result = _calculate(facts)
        handoff = result.get("page04_handoff")
        assert isinstance(handoff, dict)
        assert handoff["production_blocked"] is True
        assert handoff["deduplicated"] is False
        assert handoff["mapping_status"] == "unresolved"
