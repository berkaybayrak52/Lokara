"""Executable U1 contract for the source-named examples in ``docs/16-uvi.md``."""

from datetime import date
from decimal import Decimal
from typing import Final, Protocol

import pytest
from lokara_domain.energy import EnergyReference
from lokara_domain.meter import MeasurementUnit, ReadingReason, ReadingSource
from lokara_domain.provenance import RuleConflict, RuleEvidence
from lokara_uvi_engine import (
    BlockAInput,
    BlockBInput,
    BlockCInput,
    BlockD2Input,
    BlockDInput,
    ComparableUnit,
    HeatReading,
    HkvProvisionalInput,
    LinearInterpolationInput,
    ResolvedHeizspiegelRow,
    UviRuleBundle,
    evaluate_block_a,
    evaluate_block_b,
    evaluate_block_c,
    evaluate_block_d,
    evaluate_block_d2,
    evaluate_hkv_provisional,
    interpolate_month,
)

# Restated here deliberately. This executable engine contract must not depend on
# pytest making packages/rules-store/tests importable.
EMIR_SPEC_BLOCK_A_KWH: Final[dict[str, object]] = {
    "reading_start_x1000": 12_340_000,
    "reading_end_x1000": 13_240_000,
    "measurement_unit": "KWH",
    "movement_kwh": "900",
    "result_kwh": 900,
}

EMIR_SPEC_BLOCK_B_PREVIOUS_MONTH: Final[dict[str, object]] = {
    "current_kwh": 900,
    "previous_kwh": 850,
    "delta_kwh": 50,
    "percent": "5.9",
}

EMIR_SPEC_BLOCK_C_WEATHER_ADJUSTED: Final[dict[str, object]] = {
    "current_kwh": 900,
    "previous_year_kwh": 1_000,
    "degree_days_current": 590,
    "degree_days_previous_year": 620,
    "adjusted_previous_year_unrounded_kwh": "951.6129032258064516129032258",
    "adjusted_previous_year_kwh": 952,
    "delta_unrounded_kwh": "-51.6129032258064516129032258",
    "delta_kwh": -52,
    "percent": "-5.5",
    "input_status": "arithmetic_fixture_not_authoritative_monthly_dwd_data",
    "rounding_note": "round4_displayed_kwh_control_adjacent_percent",
}

EMIR_SPEC_BLOCK_D_BUILDING_CROSS_SECTION: Final[dict[str, object]] = {
    "target": {"area_sqm": 80, "kwh": 900},
    "comparables": (
        {"area_sqm": 100, "kwh": 1_300},
        {"area_sqm": 120, "kwh": 1_560},
    ),
    "valid_units_including_target": 3,
    "minimum_valid_units_including_target": 3,
    "average_intensity_kwh_m2": "13.0",
    "expected_kwh": 1_040,
    "delta_kwh": -140,
    "percent": "-13.5",
}

APPROVED_BLOCK_D2_HEAT_ONLY: Final[dict[str, object]] = {
    "energy_source": "Erdgas",
    "size_class": "250-500",
    "heizspiegel_mittel_kwh_m2a": 114,
    "warm_water_deduction_kwh_m2a": 24,
    "heat_only_kwh_m2a": 90,
    "area_sqm": 80,
    "degree_day_share": "0.19",
    "norm_annual_kwh": 7_200,
    "norm_month_kwh": 1_368,
    "current_heat_kwh": 1_500,
    "delta_kwh": 132,
    "percent": "9.6",
    "label": "normierter, gebäudebezogener Richtwert",
    "attribution": "Quelle: co2online gGmbH (Heizspiegel)",
}

APPROVED_HKV_PROVISIONAL: Final[dict[str, object]] = {
    "measured_rolling_building_heat_kwh": 10_000,
    "unit_hkv_units": 300,
    "building_hkv_units": 1_000,
    "provisional_unit_kwh": 3_000,
    "label": "provisorisch, Endwert erst zur Jahresabrechnung",
    "missing_building_total_result": "blocked",
}

APPROVED_BLOCK_C_RAW_WEATHER_FALLBACK: Final[dict[str, object]] = {
    "current_kwh": 900,
    "previous_year_kwh": 1_000,
    "monthly_degree_days": None,
    "raw_delta_kwh": -100,
    "raw_percent": "-10.0",
    "label": "nicht witterungsbereinigt",
    "implicit_factor_one": False,
}

APPROVED_LINEAR_MID_MONTH_INTERPOLATION: Final[dict[str, object]] = {
    "readings": (
        ("2025-01-15", "1000"),
        ("2025-02-15", "1310"),
        ("2025-03-15", "1590"),
    ),
    "interpolated_boundaries": (("2025-02-01", "1170"), ("2025-03-01", "1450")),
    "february_consumption_kwh": 280,
    "method": "linear_by_elapsed_days",
    "provenance_required": True,
}

UVI_EXAMPLES: Final[dict[str, dict[str, object]]] = {
    "emir_spec_block_a_kwh": EMIR_SPEC_BLOCK_A_KWH,
    "emir_spec_block_b_previous_month": EMIR_SPEC_BLOCK_B_PREVIOUS_MONTH,
    "emir_spec_block_c_weather_adjusted": EMIR_SPEC_BLOCK_C_WEATHER_ADJUSTED,
    "emir_spec_block_d_building_cross_section": EMIR_SPEC_BLOCK_D_BUILDING_CROSS_SECTION,
    "approved_block_d2_heat_only": APPROVED_BLOCK_D2_HEAT_ONLY,
    "approved_hkv_provisional": APPROVED_HKV_PROVISIONAL,
    "approved_block_c_raw_weather_fallback": APPROVED_BLOCK_C_RAW_WEATHER_FALLBACK,
    "approved_linear_mid_month_interpolation": APPROVED_LINEAR_MID_MONTH_INTERPOLATION,
}


class _RuleAwareResult(Protocol):
    @property
    def rule_evidence(self) -> tuple[RuleEvidence, ...]: ...

    @property
    def unresolved_conflicts(self) -> tuple[RuleConflict, ...]: ...


def _rule_evidence() -> RuleEvidence:
    return RuleEvidence(
        source="docs/16-uvi.md",
        register_row="UVI_REGISTER_ROWS",
        legal_basis="HeizkostenV § 6a",
        rechtsstand="08/2026",
        verification_status="verify-before-production",
    )


def _rule_conflict() -> RuleConflict:
    return RuleConflict(
        code="missing_uvi_register_rows",
        description="caller supplied",
        production_blocking=True,
        applies_to_media=("uvi",),
    )


def _uvi_rules() -> UviRuleBundle:
    return UviRuleBundle(
        evidence=(_rule_evidence(),),
        unresolved_conflicts=(_rule_conflict(),),
    )


def _assert_rule_passthrough(result: _RuleAwareResult, rules: UviRuleBundle) -> None:
    assert result.rule_evidence == rules.evidence
    assert result.unresolved_conflicts == rules.unresolved_conflicts


def test_u1_fixture_surface_restates_every_uvi_example() -> None:
    assert set(UVI_EXAMPLES) == {
        "emir_spec_block_a_kwh",
        "emir_spec_block_b_previous_month",
        "emir_spec_block_c_weather_adjusted",
        "emir_spec_block_d_building_cross_section",
        "approved_block_d2_heat_only",
        "approved_hkv_provisional",
        "approved_block_c_raw_weather_fallback",
        "approved_linear_mid_month_interpolation",
    }


def test_emir_spec_block_a_kwh_executes_reading_movement() -> None:
    rules = _uvi_rules()
    result = evaluate_block_a(
        BlockAInput(
            reading_start_x1000=12_340_000,
            reading_end_x1000=13_240_000,
            measurement_unit=MeasurementUnit.KWH,
            energy_reference=EnergyReference.HO,
        ),
        rules,
    )

    assert result.status == "ready"
    assert result.movement_kwh == Decimal("900")
    assert result.heat_kwh == 900
    assert result.measurement_unit is MeasurementUnit.KWH
    assert result.energy_reference is EnergyReference.HO
    assert result.label_de is None
    _assert_rule_passthrough(result, rules)


def test_emir_spec_block_b_previous_month_uses_displayed_values() -> None:
    rules = _uvi_rules()
    result = evaluate_block_b(BlockBInput(current_heat_kwh=900, previous_month_heat_kwh=850), rules)

    assert result.status == "ready"
    assert result.delta_kwh == 50
    assert result.percent == Decimal("5.9")
    _assert_rule_passthrough(result, rules)


def test_block_b_exact_german_missing_and_zero_denominator_states() -> None:
    rules = _uvi_rules()
    missing = evaluate_block_b(
        BlockBInput(current_heat_kwh=900, previous_month_heat_kwh=None), rules
    )
    assert missing.status == "unavailable"
    assert missing.label_de == "liegt für den Vormonat noch nicht vor"
    assert missing.delta_kwh is None
    assert missing.percent is None

    zero = evaluate_block_b(BlockBInput(current_heat_kwh=900, previous_month_heat_kwh=0), rules)
    assert zero.status == "ready"
    assert zero.delta_kwh == 900
    assert zero.percent is None
    assert zero.label_de == "kein Vormonatsverbrauch"
    _assert_rule_passthrough(missing, rules)
    _assert_rule_passthrough(zero, rules)


def test_emir_spec_block_c_rounds_displayed_adjusted_kwh_before_percent() -> None:
    rules = _uvi_rules()
    result = evaluate_block_c(
        BlockCInput(
            current_heat_kwh=900,
            previous_year_heat_kwh=1_000,
            monthly_degree_days_current=Decimal(590),
            monthly_degree_days_previous_year=Decimal(620),
            previous_year_interpolation_notice_de=None,
            station_id="00433",
            distance_km=Decimal("12.4"),
            dataset_attribution_de="Quelle: Deutscher Wetterdienst",
            dataset_as_of="2025-08",
        ),
        rules,
    )

    assert result.status == "ready"
    assert result.weather_adjusted
    assert result.reference_kwh == 952
    assert result.delta_kwh == -52
    assert result.percent == Decimal("-5.5")
    assert result.label_de is None
    assert result.attribution_de == "Quelle: Deutscher Wetterdienst"
    assert result.station_id == "00433"
    assert result.distance_km == Decimal("12.4")
    assert result.dataset_as_of == "2025-08"
    assert not result.station_distance_over_50_km
    _assert_rule_passthrough(result, rules)


@pytest.mark.parametrize("missing_degree_days", (None, Decimal(0)))
def test_approved_block_c_raw_weather_fallback_is_explicit(
    missing_degree_days: Decimal | None,
) -> None:
    rules = _uvi_rules()
    result = evaluate_block_c(
        BlockCInput(
            current_heat_kwh=900,
            previous_year_heat_kwh=1_000,
            monthly_degree_days_current=Decimal(590),
            monthly_degree_days_previous_year=missing_degree_days,
            previous_year_interpolation_notice_de=None,
            station_id=None,
            distance_km=None,
            dataset_attribution_de=None,
            dataset_as_of=None,
        ),
        rules,
    )

    assert result.status == "ready"
    assert not result.weather_adjusted
    assert result.weather_adjustment_factor is None
    assert result.reference_kwh == 1_000
    assert result.delta_kwh == -100
    assert result.percent == Decimal("-10.0")
    assert result.label_de == "nicht witterungsbereinigt"
    _assert_rule_passthrough(result, rules)


def test_block_c_zero_current_degree_days_stays_weather_adjusted() -> None:
    rules = _uvi_rules()
    result = evaluate_block_c(
        BlockCInput(
            current_heat_kwh=900,
            previous_year_heat_kwh=1_000,
            monthly_degree_days_current=Decimal(0),
            monthly_degree_days_previous_year=Decimal(100),
            previous_year_interpolation_notice_de=None,
            station_id="00433",
            distance_km=Decimal("50.1"),
            dataset_attribution_de="Quelle: Deutscher Wetterdienst",
            dataset_as_of="2025-08",
        ),
        rules,
    )

    assert result.status == "ready"
    assert result.weather_adjusted
    assert result.weather_adjustment_factor == Decimal(0)
    assert result.reference_kwh == 0
    assert result.delta_kwh == 900
    assert result.percent is None
    assert result.label_de is None
    assert result.station_distance_over_50_km
    _assert_rule_passthrough(result, rules)


def test_block_c_exact_german_first_reference_year_state() -> None:
    rules = _uvi_rules()
    result = evaluate_block_c(
        BlockCInput(
            current_heat_kwh=900,
            previous_year_heat_kwh=None,
            monthly_degree_days_current=None,
            monthly_degree_days_previous_year=None,
            previous_year_interpolation_notice_de=None,
            station_id=None,
            distance_km=None,
            dataset_attribution_de=None,
            dataset_as_of=None,
        ),
        rules,
    )

    assert result.status == "unavailable"
    assert result.label_de == "liegt im ersten Bezugsjahr noch nicht vor"
    _assert_rule_passthrough(result, rules)


def test_emir_spec_block_d_building_cross_section_includes_target_in_minimum() -> None:
    rules = _uvi_rules()
    result = evaluate_block_d(
        BlockDInput(
            target=ComparableUnit(
                unit_id="target",
                area_sqm=Decimal(80),
                heat_kwh=900,
                device_category="physical_heat_meter",
            ),
            other_units=(
                ComparableUnit(
                    unit_id="other-1",
                    area_sqm=Decimal(100),
                    heat_kwh=1_300,
                    device_category="physical_heat_meter",
                ),
                ComparableUnit(
                    unit_id="other-2",
                    area_sqm=Decimal(120),
                    heat_kwh=1_560,
                    device_category="physical_heat_meter",
                ),
            ),
            minimum_valid_units_including_target=3,
        ),
        rules,
    )

    assert result.status == "ready"
    assert result.valid_units_including_target == 3
    assert result.average_intensity_kwh_m2 == Decimal("13.0")
    assert result.expected_target_kwh == 1_040
    assert result.delta_kwh == -140
    assert result.percent == Decimal("-13.5")
    assert result.basis_de == "Vergleich im Gebäude"
    _assert_rule_passthrough(result, rules)


def test_block_d_with_fewer_than_three_valid_units_selects_d2() -> None:
    rules = _uvi_rules()
    result = evaluate_block_d(
        BlockDInput(
            target=ComparableUnit(
                unit_id="target",
                area_sqm=Decimal(80),
                heat_kwh=900,
                device_category="physical_heat_meter",
            ),
            other_units=(),
            minimum_valid_units_including_target=3,
        ),
        rules,
    )

    assert result.status == "use_d2"
    assert result.valid_units_including_target == 1
    assert result.expected_target_kwh is None
    _assert_rule_passthrough(result, rules)


def test_block_d_caller_cannot_lower_fixed_three_valid_unit_threshold() -> None:
    rules = _uvi_rules()
    with pytest.raises(ValueError):
        evaluate_block_d(
            BlockDInput(
                target=ComparableUnit(
                    unit_id="target",
                    area_sqm=Decimal(80),
                    heat_kwh=900,
                    device_category="physical_heat_meter",
                ),
                other_units=(
                    ComparableUnit(
                        unit_id="other-1",
                        area_sqm=Decimal(100),
                        heat_kwh=1_300,
                        device_category="physical_heat_meter",
                    ),
                ),
                minimum_valid_units_including_target=2,
            ),
            rules,
        )


def test_approved_block_d2_heat_only_executes_normed_fallback() -> None:
    rules = _uvi_rules()
    resolved_row = ResolvedHeizspiegelRow(
        energy_source="Erdgas",
        requested_size_class="250-500",
        actual_size_class="250-500",
        heizspiegel_mittel_kwh_m2a=Decimal(114),
        warm_water_deduction_kwh_m2a=Decimal(24),
        heizspiegel_vintage="2025/billing-year-2024",
        fallback_label_de=None,
        evidence=rules.evidence,
    )
    result = evaluate_block_d2(
        BlockD2Input(
            current_heat_kwh=1_500,
            target_area_sqm=Decimal(80),
            monthly_degree_day_share=Decimal("0.19"),
            resolved_row=resolved_row,
        ),
        rules,
    )

    assert result.status == "ready"
    assert result.heat_only_kwh_m2a == Decimal(90)
    assert result.norm_annual_kwh == 7_200
    assert result.norm_month_kwh == 1_368
    assert result.delta_kwh == 132
    assert result.percent == Decimal("9.6")
    assert result.basis_de == "normierter Durchschnittsnutzer"
    assert result.label_de == "normierter, gebäudebezogener Richtwert"
    assert result.attribution_de == "Quelle: co2online gGmbH (Heizspiegel)"
    assert result.heizspiegel_vintage == "2025/billing-year-2024"
    assert result.actual_size_class == "250-500"
    assert result.fallback_label_de is None
    _assert_rule_passthrough(result, rules)


def test_block_d2_retains_distinct_bundle_and_resolved_row_evidence() -> None:
    bundle_evidence = _rule_evidence()
    resolved_row_evidence = RuleEvidence(
        source="docs/16-uvi.md § 8.2",
        register_row="HEIZSPIEGEL_D2_CONTRACT",
        legal_basis="HeizkostenV § 6a",
        rechtsstand="08/2026",
        verification_status="verify-before-production",
    )
    rules = UviRuleBundle(
        evidence=(bundle_evidence,),
        unresolved_conflicts=(_rule_conflict(),),
    )
    resolved_row = ResolvedHeizspiegelRow(
        energy_source="Erdgas",
        requested_size_class="250-500",
        actual_size_class="250-500",
        heizspiegel_mittel_kwh_m2a=Decimal(114),
        warm_water_deduction_kwh_m2a=Decimal(24),
        heizspiegel_vintage="2025/billing-year-2024",
        fallback_label_de=None,
        evidence=(resolved_row_evidence,),
    )

    result = evaluate_block_d2(
        BlockD2Input(
            current_heat_kwh=1_500,
            target_area_sqm=Decimal(80),
            monthly_degree_day_share=Decimal("0.19"),
            resolved_row=resolved_row,
        ),
        rules,
    )

    assert len(result.rule_evidence) == 2
    assert set(result.rule_evidence) == {bundle_evidence, resolved_row_evidence}


def test_block_d2_refuses_non_positive_heat_only_reference() -> None:
    rules = _uvi_rules()
    resolved_row = ResolvedHeizspiegelRow(
        energy_source="Erdgas",
        requested_size_class="ueber-500",
        actual_size_class="250-500",
        heizspiegel_mittel_kwh_m2a=Decimal(24),
        warm_water_deduction_kwh_m2a=Decimal(24),
        heizspiegel_vintage="2025/billing-year-2024",
        fallback_label_de="caller supplied",
        evidence=rules.evidence,
    )
    result = evaluate_block_d2(
        BlockD2Input(
            current_heat_kwh=1_500,
            target_area_sqm=Decimal(80),
            monthly_degree_day_share=Decimal("0.19"),
            resolved_row=resolved_row,
        ),
        rules,
    )

    assert result.status == "blocked"
    assert result.data_quality_flag == "non_positive_heat_only_mittel"
    assert result.norm_month_kwh is None
    assert result.actual_size_class == "250-500"
    assert result.fallback_label_de is None
    assert result.basis_de is None
    assert result.label_de is None
    assert result.attribution_de is None
    _assert_rule_passthrough(result, rules)


def test_block_d2_ready_result_carries_resolved_fallback_without_inventing_text() -> None:
    rules = _uvi_rules()
    resolved_row = ResolvedHeizspiegelRow(
        energy_source="Wärmepumpe",
        requested_size_class="ueber-500",
        actual_size_class="250-500",
        heizspiegel_mittel_kwh_m2a=Decimal(36),
        warm_water_deduction_kwh_m2a=Decimal(8),
        heizspiegel_vintage="2025/billing-year-2024",
        fallback_label_de="caller supplied",
        evidence=rules.evidence,
    )

    result = evaluate_block_d2(
        BlockD2Input(
            current_heat_kwh=1_500,
            target_area_sqm=Decimal(80),
            monthly_degree_day_share=Decimal("0.19"),
            resolved_row=resolved_row,
        ),
        rules,
    )

    assert result.status == "ready"
    assert result.actual_size_class == "250-500"
    assert result.fallback_label_de == "caller supplied"
    _assert_rule_passthrough(result, rules)


def test_every_blocked_uvi_result_suppresses_renter_facing_text() -> None:
    rules = _uvi_rules()
    blocked_a = (
        evaluate_block_a(
            BlockAInput(
                reading_start_x1000=2_000,
                reading_end_x1000=1_000,
                measurement_unit=MeasurementUnit.KWH,
                energy_reference=EnergyReference.HO,
            ),
            rules,
        ),
        evaluate_block_a(
            BlockAInput(
                reading_start_x1000=1_000,
                reading_end_x1000=2_000,
                measurement_unit=MeasurementUnit.CUBIC_METRE,
                energy_reference=EnergyReference.HO,
            ),
            rules,
        ),
        evaluate_block_a(
            BlockAInput(
                reading_start_x1000=1_000,
                reading_end_x1000=2_000,
                measurement_unit=MeasurementUnit.HKV_UNITS,
                energy_reference=EnergyReference.HO,
            ),
            rules,
        ),
    )
    blocked_d = (
        evaluate_block_d(
            BlockDInput(
                target=ComparableUnit(
                    unit_id="target",
                    area_sqm=None,
                    heat_kwh=900,
                    device_category="physical_heat_meter",
                ),
                other_units=(),
                minimum_valid_units_including_target=3,
            ),
            rules,
        ),
        evaluate_block_d(
            BlockDInput(
                target=ComparableUnit(
                    unit_id="target",
                    area_sqm=Decimal(80),
                    heat_kwh=None,
                    device_category="physical_heat_meter",
                ),
                other_units=(),
                minimum_valid_units_including_target=3,
            ),
            rules,
        ),
    )
    blocked_hkv = (
        evaluate_hkv_provisional(
            HkvProvisionalInput(
                measured_rolling_building_heat_kwh=10_000,
                unit_hkv_units=Decimal(300),
                building_hkv_units=Decimal(1_000),
                measurement_unit=MeasurementUnit.KWH,
                explicit_hkv_allocator=True,
            ),
            rules,
        ),
        evaluate_hkv_provisional(
            HkvProvisionalInput(
                measured_rolling_building_heat_kwh=10_000,
                unit_hkv_units=Decimal(300),
                building_hkv_units=Decimal(1_000),
                measurement_unit=MeasurementUnit.HKV_UNITS,
                explicit_hkv_allocator=False,
            ),
            rules,
        ),
        evaluate_hkv_provisional(
            HkvProvisionalInput(
                measured_rolling_building_heat_kwh=10_000,
                unit_hkv_units=Decimal(300),
                building_hkv_units=Decimal(0),
                measurement_unit=MeasurementUnit.HKV_UNITS,
                explicit_hkv_allocator=True,
            ),
            rules,
        ),
        evaluate_hkv_provisional(
            HkvProvisionalInput(
                measured_rolling_building_heat_kwh=None,
                unit_hkv_units=Decimal(300),
                building_hkv_units=Decimal(1_000),
                measurement_unit=MeasurementUnit.HKV_UNITS,
                explicit_hkv_allocator=True,
            ),
            rules,
        ),
    )

    for result in (*blocked_a, *blocked_d, *blocked_hkv):
        assert result.status == "blocked"
        assert getattr(result, "basis_de", None) is None
        assert getattr(result, "label_de", None) is None
        assert getattr(result, "attribution_de", None) is None
        _assert_rule_passthrough(result, rules)


def test_approved_hkv_provisional_uses_measured_building_total() -> None:
    rules = _uvi_rules()
    result = evaluate_hkv_provisional(
        HkvProvisionalInput(
            measured_rolling_building_heat_kwh=10_000,
            unit_hkv_units=Decimal(300),
            building_hkv_units=Decimal(1_000),
            measurement_unit=MeasurementUnit.HKV_UNITS,
            explicit_hkv_allocator=True,
        ),
        rules,
    )

    assert result.status == "ready"
    assert result.provisional_unit_kwh == 3_000
    assert result.label_de == "provisorisch, Endwert erst zur Jahresabrechnung"
    assert result.measurement_unit is MeasurementUnit.HKV_UNITS
    _assert_rule_passthrough(result, rules)


def test_approved_hkv_provisional_blocks_when_building_total_is_missing() -> None:
    rules = _uvi_rules()
    result = evaluate_hkv_provisional(
        HkvProvisionalInput(
            measured_rolling_building_heat_kwh=None,
            unit_hkv_units=Decimal(300),
            building_hkv_units=Decimal(1_000),
            measurement_unit=MeasurementUnit.HKV_UNITS,
            explicit_hkv_allocator=True,
        ),
        rules,
    )

    assert result.status == "blocked"
    assert result.provisional_unit_kwh is None
    assert result.data_quality_flag == "missing_measured_rolling_building_heat_total"
    assert result.label_de is None
    _assert_rule_passthrough(result, rules)


def test_approved_linear_mid_month_interpolation_retains_provenance() -> None:
    rules = _uvi_rules()
    readings = (
        HeatReading(
            reading_id="r-jan-15",
            value=Decimal("1000"),
            read_at=date(2025, 1, 15),
            source=ReadingSource.MDL,
            reason=ReadingReason.INTERIM,
        ),
        HeatReading(
            reading_id="r-feb-15",
            value=Decimal("1310"),
            read_at=date(2025, 2, 15),
            source=ReadingSource.MDL,
            reason=ReadingReason.INTERIM,
        ),
        HeatReading(
            reading_id="r-mar-15",
            value=Decimal("1590"),
            read_at=date(2025, 3, 15),
            source=ReadingSource.MDL,
            reason=ReadingReason.INTERIM,
        ),
    )
    interpolation_input = LinearInterpolationInput(
        month=date(2025, 2, 1),
        readings=readings,
        measurement_unit=MeasurementUnit.KWH,
        energy_reference=EnergyReference.HO,
    )

    result = interpolate_month(interpolation_input, rules)

    assert result.status == "ready"
    assert result.boundary_start.at == date(2025, 2, 1)
    assert result.boundary_start.value == Decimal("1170")
    assert result.boundary_end.at == date(2025, 3, 1)
    assert result.boundary_end.value == Decimal("1450")
    assert result.consumption_kwh == 280
    assert result.method == "linear_by_elapsed_days"
    assert result.source_reading_ids == ("r-jan-15", "r-feb-15", "r-mar-15")
    assert result.source_dates == (
        date(2025, 1, 15),
        date(2025, 2, 15),
        date(2025, 3, 15),
    )
    assert result.source_reading_reasons == (
        ReadingReason.INTERIM,
        ReadingReason.INTERIM,
        ReadingReason.INTERIM,
    )
    assert result.source_reading_sources == (
        ReadingSource.MDL,
        ReadingSource.MDL,
        ReadingSource.MDL,
    )
    assert result.measurement_unit is MeasurementUnit.KWH
    assert result.energy_reference is EnergyReference.HO
    _assert_rule_passthrough(result, rules)
