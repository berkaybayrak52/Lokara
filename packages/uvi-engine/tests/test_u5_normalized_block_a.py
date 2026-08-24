"""Red U4b contract for Block A from an already-normalized monthly movement."""

from __future__ import annotations

import dataclasses
import runpy
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol, cast, get_type_hints

import pytest
from lokara_domain.energy import EnergyReference
from lokara_domain.meter import MeasurementUnit
from lokara_domain.provenance import RuleConflict, RuleEvidence
from lokara_uvi_engine import UviRuleBundle

_ORACLE_PATH = (
    Path(__file__).resolve().parents[2] / "rules-store" / "tests" / "berkay_uvi_golden.py"
)
_ORACLE = runpy.run_path(str(_ORACLE_PATH))
UVI_EXAMPLES = cast(dict[str, dict[str, object]], _ORACLE["UVI_EXAMPLES"])


class _Result(Protocol):
    status: str
    heat_kwh: int | None
    label_de: str | None
    data_quality_flag: str | None
    rule_evidence: tuple[RuleEvidence, ...]
    unresolved_conflicts: tuple[RuleConflict, ...]


def _api() -> tuple[type[Any], Any]:
    import lokara_uvi_engine

    input_type = getattr(lokara_uvi_engine, "NormalizedBlockAInput", None)
    evaluator = getattr(lokara_uvi_engine, "evaluate_normalized_block_a", None)
    assert input_type is not None, "U4b NormalizedBlockAInput is missing"
    assert callable(evaluator), "U4b evaluate_normalized_block_a is missing"
    return input_type, evaluator


def _rules() -> UviRuleBundle:
    evidence = RuleEvidence(
        source="docs/16-uvi.md § 3.1",
        register_row="UVI_REGISTER_ROWS",
        legal_basis="HeizkostenV § 6a",
        rechtsstand="08/2026",
        verification_status="verify-before-production",
    )
    conflict = RuleConflict(
        code="missing_uvi_register_rows",
        description="caller supplied",
        production_blocking=True,
        applies_to_media=("uvi",),
    )
    return UviRuleBundle(evidence=(evidence,), unresolved_conflicts=(conflict,))


def _assert_rules(result: _Result, rules: UviRuleBundle) -> None:
    assert result.rule_evidence == rules.evidence
    assert result.unresolved_conflicts == rules.unresolved_conflicts


def test_u4b_normalized_input_has_no_fake_cumulative_endpoints() -> None:
    """U4b-A01: the new boundary names the persisted movement directly."""
    input_type, _ = _api()
    fields = {field.name for field in dataclasses.fields(input_type)}
    assert "monthly_movement_x1000" in fields
    assert {"reading_start_x1000", "reading_end_x1000"}.isdisjoint(fields)
    assert {
        "measurement_unit",
        "energy_reference",
        "calorific_factor_kwh_per_unit",
        "explicit_hkv_allocator",
        "measured_building_heat_kwh_x1000",
        "building_hkv_movement_x1000",
    } <= fields
    assert get_type_hints(input_type)["measured_building_heat_kwh_x1000"] == int | None


def test_u4b_source_named_kwh_month_executes_without_rebased_endpoints() -> None:
    """U4b-A02: the approved Block A movement stays 900 kWh."""
    input_type, evaluate = _api()
    case = UVI_EXAMPLES["emir_spec_block_a_kwh"]
    rules = _rules()
    monthly_x1000 = int(Decimal(cast(str, case["movement_kwh"])) * Decimal(1000))

    result = cast(
        _Result,
        evaluate(
            input_type(
                monthly_movement_x1000=monthly_x1000,
                measurement_unit=MeasurementUnit.KWH,
                energy_reference=EnergyReference.HO,
            ),
            rules,
        ),
    )

    assert result.status == "ready"
    assert result.heat_kwh == case["result_kwh"]
    assert result.label_de is None
    _assert_rules(result, rules)


def test_u4b_cubic_month_blocks_without_a_versioned_calorific_factor() -> None:
    """U4b-A03: no factor is inferred from energy source, meter unit or invoice text."""
    input_type, evaluate = _api()
    case = UVI_EXAMPLES["emir_spec_block_a_kwh"]
    rules = _rules()
    monthly_x1000 = int(Decimal(cast(str, case["movement_kwh"])) * Decimal(1000))

    result = cast(
        _Result,
        evaluate(
            input_type(
                monthly_movement_x1000=monthly_x1000,
                measurement_unit=MeasurementUnit.CUBIC_METRE,
                energy_reference=EnergyReference.HO,
                calorific_factor_kwh_per_unit=None,
            ),
            rules,
        ),
    )

    assert result.status == "blocked"
    assert result.heat_kwh is None
    assert result.data_quality_flag == "missing_calorific_factor"
    assert result.label_de is None
    _assert_rules(result, rules)


def test_u4b_source_named_hkv_month_uses_same_month_building_evidence() -> None:
    """U4b-A04: the approved provisional HKV case keeps its exact label and result."""
    input_type, evaluate = _api()
    case = UVI_EXAMPLES["approved_hkv_provisional"]
    rules = _rules()

    result = cast(
        _Result,
        evaluate(
            input_type(
                monthly_movement_x1000=cast(int, case["unit_hkv_units"]) * 1000,
                measurement_unit=MeasurementUnit.HKV_UNITS,
                energy_reference=EnergyReference.HO,
                explicit_hkv_allocator=True,
                measured_building_heat_kwh_x1000=(
                    cast(int, case["measured_rolling_building_heat_kwh"]) * 1000
                ),
                building_hkv_movement_x1000=cast(int, case["building_hkv_units"]) * 1000,
            ),
            rules,
        ),
    )

    assert result.status == "ready"
    assert result.heat_kwh == case["provisional_unit_kwh"]
    assert result.label_de == case["label"]
    _assert_rules(result, rules)


@pytest.mark.parametrize("building_total", (None, 0, -1), ids=("missing", "zero", "negative"))
def test_u4b_hkv_blocks_missing_or_nonpositive_building_total(
    building_total: int | None,
) -> None:
    """U4b-A05: a purchase, estimate, absent or nonpositive total never qualifies."""
    input_type, evaluate = _api()
    case = UVI_EXAMPLES["approved_hkv_provisional"]
    rules = _rules()
    result = cast(
        _Result,
        evaluate(
            input_type(
                monthly_movement_x1000=cast(int, case["unit_hkv_units"]) * 1000,
                measurement_unit=MeasurementUnit.HKV_UNITS,
                energy_reference=EnergyReference.HO,
                explicit_hkv_allocator=True,
                measured_building_heat_kwh_x1000=(
                    building_total * 1000 if building_total is not None else None
                ),
                building_hkv_movement_x1000=cast(int, case["building_hkv_units"]) * 1000,
            ),
            rules,
        ),
    )

    assert result.status == "blocked"
    assert result.heat_kwh is None
    assert result.data_quality_flag in {
        "missing_measured_building_heat_total",
        "nonpositive_measured_building_heat_total",
    }
    assert result.label_de is None
    _assert_rules(result, rules)
