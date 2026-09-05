"""Pure UVI Block A-D2 calculations and monthly reading interpolation."""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from itertools import pairwise

from lokara_domain.meter import MeasurementUnit

from .models import (
    BlockAInput,
    BlockAResult,
    BlockBInput,
    BlockBResult,
    BlockCInput,
    BlockCResult,
    BlockD2Input,
    BlockD2Result,
    BlockDInput,
    BlockDResult,
    ComparableUnit,
    HeatReading,
    HkvProvisionalInput,
    HkvProvisionalResult,
    InterpolatedBoundary,
    LinearInterpolationInput,
    LinearInterpolationResult,
    NormalizedBlockAInput,
    UviRuleBundle,
    WarmWaterBlockAInput,
    WarmWaterBlockAResult,
    WarmWaterBlockD2Input,
    WarmWaterBlockD2Result,
)

# Lokara conventions pending legal confirmation; see docs/16-uvi.md § 12.
STATION_DISTANCE_WARNING_KM = Decimal("50")
MINIMUM_VALID_UNITS_INCLUDING_TARGET = 3

_ONE = Decimal(1)
_ONE_TENTH = Decimal("0.1")
_THOUSAND = Decimal(1000)
_PERCENT = Decimal(100)
_HKV_LABEL = "provisorisch, Endwert erst zur Jahresabrechnung"
_D2_BASIS = "normierter Durchschnittsnutzer"
_D2_LABEL = "normierter, gebäudebezogener Richtwert"
_D2_ATTRIBUTION = "Quelle: co2online gGmbH (Heizspiegel)"


def _require_nonnegative_integer(value: int, field: str) -> None:
    if isinstance(value, bool) or value < 0:
        raise ValueError(f"{field} must be an integer >= 0")


def _require_finite_nonnegative(value: Decimal, field: str) -> None:
    if not value.is_finite() or value < 0:
        raise ValueError(f"{field} must be finite and >= 0")


def _require_finite_positive(value: Decimal, field: str) -> None:
    if not value.is_finite() or value <= 0:
        raise ValueError(f"{field} must be finite and > 0")


def _whole_kwh(value: Decimal) -> int:
    return int(value.quantize(_ONE, rounding=ROUND_HALF_UP))


def _display_percent(delta_kwh: int, reference_kwh: int) -> Decimal | None:
    if reference_kwh == 0:
        return None
    return (Decimal(delta_kwh) / Decimal(reference_kwh) * _PERCENT).quantize(
        _ONE_TENTH, rounding=ROUND_HALF_UP
    )


def evaluate_block_a(input_: BlockAInput, rules: UviRuleBundle) -> BlockAResult:
    """Derive monthly heat from compatible scaled readings."""

    if isinstance(input_.reading_start_x1000, bool) or isinstance(input_.reading_end_x1000, bool):
        raise ValueError("scaled readings must be integers")
    raw_movement = Decimal(input_.reading_end_x1000 - input_.reading_start_x1000) / _THOUSAND
    if raw_movement < 0 and not input_.correctly_segmented_device_change:
        return BlockAResult(
            status="blocked",
            movement_kwh=None,
            heat_kwh=None,
            measurement_unit=input_.measurement_unit,
            energy_reference=input_.energy_reference,
            label_de=None,
            rule_evidence=rules.evidence,
            unresolved_conflicts=rules.unresolved_conflicts,
            data_quality_flag="negative_unsegmented_movement",
        )

    if input_.measurement_unit is MeasurementUnit.KWH:
        movement_kwh = raw_movement
    elif input_.measurement_unit is MeasurementUnit.CUBIC_METRE:
        factor = input_.calorific_factor_kwh_per_unit
        if factor is None:
            return BlockAResult(
                status="blocked",
                movement_kwh=None,
                heat_kwh=None,
                measurement_unit=input_.measurement_unit,
                energy_reference=input_.energy_reference,
                label_de=None,
                rule_evidence=rules.evidence,
                unresolved_conflicts=rules.unresolved_conflicts,
                data_quality_flag="missing_calorific_factor",
            )
        condition_number = input_.condition_number
        if condition_number is None:
            return BlockAResult(
                status="blocked",
                movement_kwh=None,
                heat_kwh=None,
                measurement_unit=input_.measurement_unit,
                energy_reference=input_.energy_reference,
                label_de=None,
                rule_evidence=rules.evidence,
                unresolved_conflicts=rules.unresolved_conflicts,
                data_quality_flag="missing_condition_number",
            )
        _require_finite_positive(factor, "calorific_factor_kwh_per_unit")
        _require_finite_positive(condition_number, "condition_number")
        movement_kwh = raw_movement * factor * condition_number
    else:
        return BlockAResult(
            status="blocked",
            movement_kwh=None,
            heat_kwh=None,
            measurement_unit=input_.measurement_unit,
            energy_reference=input_.energy_reference,
            label_de=None,
            rule_evidence=rules.evidence,
            unresolved_conflicts=rules.unresolved_conflicts,
            data_quality_flag="hkv_requires_provisional_building_total",
        )

    return BlockAResult(
        status="ready",
        movement_kwh=movement_kwh,
        heat_kwh=_whole_kwh(movement_kwh),
        measurement_unit=input_.measurement_unit,
        energy_reference=input_.energy_reference,
        label_de=None,
        rule_evidence=rules.evidence,
        unresolved_conflicts=rules.unresolved_conflicts,
    )


def evaluate_normalized_block_a(
    input_: NormalizedBlockAInput, rules: UviRuleBundle
) -> BlockAResult:
    """Derive monthly heat from an already-normalized persisted movement."""

    movement_x1000 = input_.monthly_movement_x1000
    if isinstance(movement_x1000, bool) or movement_x1000 < 0:
        raise ValueError("monthly_movement_x1000 must be an integer >= 0")
    movement = Decimal(movement_x1000) / _THOUSAND

    if input_.measurement_unit is MeasurementUnit.KWH:
        heat = movement
    elif input_.measurement_unit is MeasurementUnit.CUBIC_METRE:
        factor = input_.calorific_factor_kwh_per_unit
        if factor is None:
            return BlockAResult(
                status="blocked",
                movement_kwh=None,
                heat_kwh=None,
                measurement_unit=input_.measurement_unit,
                energy_reference=input_.energy_reference,
                label_de=None,
                rule_evidence=rules.evidence,
                unresolved_conflicts=rules.unresolved_conflicts,
                data_quality_flag="missing_calorific_factor",
            )
        condition_number = input_.condition_number
        if condition_number is None:
            return BlockAResult(
                status="blocked",
                movement_kwh=None,
                heat_kwh=None,
                measurement_unit=input_.measurement_unit,
                energy_reference=input_.energy_reference,
                label_de=None,
                rule_evidence=rules.evidence,
                unresolved_conflicts=rules.unresolved_conflicts,
                data_quality_flag="missing_condition_number",
            )
        _require_finite_positive(factor, "calorific_factor_kwh_per_unit")
        _require_finite_positive(condition_number, "condition_number")
        heat = movement * factor * condition_number
    else:
        if not input_.explicit_hkv_allocator:
            return BlockAResult(
                status="blocked",
                movement_kwh=None,
                heat_kwh=None,
                measurement_unit=input_.measurement_unit,
                energy_reference=input_.energy_reference,
                label_de=None,
                rule_evidence=rules.evidence,
                unresolved_conflicts=rules.unresolved_conflicts,
                data_quality_flag="missing_explicit_hkv_allocator_marker",
            )
        building_heat_x1000 = input_.measured_building_heat_kwh_x1000
        if building_heat_x1000 is None:
            return BlockAResult(
                status="blocked",
                movement_kwh=None,
                heat_kwh=None,
                measurement_unit=input_.measurement_unit,
                energy_reference=input_.energy_reference,
                label_de=None,
                rule_evidence=rules.evidence,
                unresolved_conflicts=rules.unresolved_conflicts,
                data_quality_flag="missing_measured_building_heat_total",
            )
        if isinstance(building_heat_x1000, bool):
            raise ValueError("measured_building_heat_kwh_x1000 must be an integer")
        if building_heat_x1000 <= 0:
            return BlockAResult(
                status="blocked",
                movement_kwh=None,
                heat_kwh=None,
                measurement_unit=input_.measurement_unit,
                energy_reference=input_.energy_reference,
                label_de=None,
                rule_evidence=rules.evidence,
                unresolved_conflicts=rules.unresolved_conflicts,
                data_quality_flag="nonpositive_measured_building_heat_total",
            )
        building_movement_x1000 = input_.building_hkv_movement_x1000
        if building_movement_x1000 is None:
            return BlockAResult(
                status="blocked",
                movement_kwh=None,
                heat_kwh=None,
                measurement_unit=input_.measurement_unit,
                energy_reference=input_.energy_reference,
                label_de=None,
                rule_evidence=rules.evidence,
                unresolved_conflicts=rules.unresolved_conflicts,
                data_quality_flag="missing_building_hkv_movement",
            )
        if isinstance(building_movement_x1000, bool):
            raise ValueError("building_hkv_movement_x1000 must be an integer")
        if building_movement_x1000 <= 0:
            return BlockAResult(
                status="blocked",
                movement_kwh=None,
                heat_kwh=None,
                measurement_unit=input_.measurement_unit,
                energy_reference=input_.energy_reference,
                label_de=None,
                rule_evidence=rules.evidence,
                unresolved_conflicts=rules.unresolved_conflicts,
                data_quality_flag="nonpositive_building_hkv_movement",
            )
        heat = (
            Decimal(building_heat_x1000)
            * Decimal(movement_x1000)
            / Decimal(building_movement_x1000)
            / _THOUSAND
        )

    return BlockAResult(
        status="ready",
        movement_kwh=heat,
        heat_kwh=_whole_kwh(heat),
        measurement_unit=input_.measurement_unit,
        energy_reference=input_.energy_reference,
        label_de=_HKV_LABEL if input_.measurement_unit is MeasurementUnit.HKV_UNITS else None,
        rule_evidence=rules.evidence,
        unresolved_conflicts=rules.unresolved_conflicts,
    )


def evaluate_block_b(input_: BlockBInput, rules: UviRuleBundle) -> BlockBResult:
    """Compare current displayed heat with the previous displayed month."""

    _require_nonnegative_integer(input_.current_heat_kwh, "current_heat_kwh")
    previous = input_.previous_month_heat_kwh
    if previous is None:
        return BlockBResult(
            status="unavailable",
            delta_kwh=None,
            percent=None,
            label_de="liegt für den Vormonat noch nicht vor",
            rule_evidence=rules.evidence,
            unresolved_conflicts=rules.unresolved_conflicts,
        )
    _require_nonnegative_integer(previous, "previous_month_heat_kwh")
    delta = input_.current_heat_kwh - previous
    if previous == 0:
        return BlockBResult(
            status="ready",
            delta_kwh=delta,
            percent=None,
            label_de="kein Vormonatsverbrauch",
            rule_evidence=rules.evidence,
            unresolved_conflicts=rules.unresolved_conflicts,
        )
    return BlockBResult(
        status="ready",
        delta_kwh=delta,
        percent=_display_percent(delta, previous),
        label_de=None,
        rule_evidence=rules.evidence,
        unresolved_conflicts=rules.unresolved_conflicts,
    )


def evaluate_warm_water_block_a(
    input_: WarmWaterBlockAInput, rules: UviRuleBundle, *, rule_source: str | None = None
) -> WarmWaterBlockAResult:
    """Convert a measured warm-water volume using the resolved § 9 rule.

    The factor is deliberately an input: the engine never supplies a water-to-energy
    default.  An absent rule is a blocked result, not an estimate.
    """
    if isinstance(input_.reading_start_x1000, bool) or isinstance(input_.reading_end_x1000, bool):
        raise ValueError("scaled readings must be integers")
    volume = Decimal(input_.reading_end_x1000 - input_.reading_start_x1000) / _THOUSAND
    if volume < 0:
        return WarmWaterBlockAResult(
            "blocked",
            None,
            None,
            input_.factor_kwh_per_m3,
            rule_source,
            "negative_unsegmented_movement",
            rules.evidence,
            rules.unresolved_conflicts,
        )
    factor = input_.factor_kwh_per_m3
    if factor is None:
        return WarmWaterBlockAResult(
            "blocked",
            volume,
            None,
            None,
            rule_source,
            "missing_warm_water_conversion",
            rules.evidence,
            rules.unresolved_conflicts,
        )
    _require_finite_positive(factor, "factor_kwh_per_m3")
    energy = volume * factor
    return WarmWaterBlockAResult(
        "ready",
        volume,
        _whole_kwh(energy),
        factor,
        rule_source,
        None,
        rules.evidence,
        rules.unresolved_conflicts,
    )


def evaluate_warm_water_block_c(
    current_warm_water_kwh: int,
    previous_year_warm_water_kwh: int | None,
    rules: UviRuleBundle,
) -> BlockBResult:
    """Raw prior-year warm-water comparison; no weather adjustment is possible."""
    return evaluate_block_b(
        BlockBInput(current_warm_water_kwh, previous_year_warm_water_kwh), rules
    )


def evaluate_warm_water_block_d2(
    input_: WarmWaterBlockD2Input, rules: UviRuleBundle
) -> WarmWaterBlockD2Result:
    """Compare WW with the Heizspiegel warm-water component (not heat-only D2)."""
    _require_nonnegative_integer(input_.current_warm_water_kwh, "current_warm_water_kwh")
    for name, value in (
        ("target_area_sqm", input_.target_area_sqm),
        ("monthly_share", input_.monthly_share),
        ("warm_water_deduction_kwh_m2a", input_.warm_water_deduction_kwh_m2a),
    ):
        _require_finite_nonnegative(value, name)
    if input_.target_area_sqm == 0:
        raise ValueError("target_area_sqm must be > 0")
    if input_.monthly_share > 1:
        raise ValueError("monthly_share must be <= 1")
    if not input_.heizspiegel_vintage:
        raise ValueError("heizspiegel_vintage must not be empty")
    norm = _whole_kwh(
        input_.warm_water_deduction_kwh_m2a * input_.target_area_sqm * input_.monthly_share
    )
    delta = input_.current_warm_water_kwh - norm
    return WarmWaterBlockD2Result(
        "ready",
        norm,
        delta,
        _display_percent(delta, norm),
        input_.warm_water_deduction_kwh_m2a,
        input_.heizspiegel_vintage,
        input_.attribution_de,
        None,
        rules.evidence,
        rules.unresolved_conflicts,
    )


def evaluate_block_c(input_: BlockCInput, rules: UviRuleBundle) -> BlockCResult:
    """Compare to prior-year heat, weather-adjusting only with usable degree days."""

    _require_nonnegative_integer(input_.current_heat_kwh, "current_heat_kwh")
    previous = input_.previous_year_heat_kwh
    if previous is None:
        return BlockCResult(
            status="unavailable",
            weather_adjusted=False,
            weather_adjustment_factor=None,
            reference_kwh=None,
            delta_kwh=None,
            percent=None,
            label_de="liegt im ersten Bezugsjahr noch nicht vor",
            previous_year_interpolation_notice_de=input_.previous_year_interpolation_notice_de,
            attribution_de=input_.dataset_attribution_de,
            station_id=input_.station_id,
            distance_km=input_.distance_km,
            dataset_as_of=input_.dataset_as_of,
            station_distance_over_50_km=(
                input_.distance_km is not None and input_.distance_km > STATION_DISTANCE_WARNING_KM
            ),
            rule_evidence=rules.evidence,
            unresolved_conflicts=rules.unresolved_conflicts,
        )
    _require_nonnegative_integer(previous, "previous_year_heat_kwh")
    current_days = input_.monthly_degree_days_current
    previous_days = input_.monthly_degree_days_previous_year
    for name, value in (
        ("monthly_degree_days_current", current_days),
        ("monthly_degree_days_previous_year", previous_days),
    ):
        if value is not None:
            _require_finite_nonnegative(value, name)

    if current_days is not None and previous_days is not None and previous_days > 0:
        usable_weather = True
        factor = current_days / previous_days
        reference = _whole_kwh(Decimal(previous) * factor)
        label = None
    else:
        usable_weather = False
        factor = None
        reference = previous
        label = "nicht witterungsbereinigt"
    delta = input_.current_heat_kwh - reference
    return BlockCResult(
        status="ready",
        weather_adjusted=usable_weather,
        weather_adjustment_factor=factor,
        reference_kwh=reference,
        delta_kwh=delta,
        percent=_display_percent(delta, reference),
        label_de=label,
        previous_year_interpolation_notice_de=input_.previous_year_interpolation_notice_de,
        attribution_de=input_.dataset_attribution_de,
        station_id=input_.station_id,
        distance_km=input_.distance_km,
        dataset_as_of=input_.dataset_as_of,
        station_distance_over_50_km=(
            input_.distance_km is not None and input_.distance_km > STATION_DISTANCE_WARNING_KM
        ),
        rule_evidence=rules.evidence,
        unresolved_conflicts=rules.unresolved_conflicts,
    )


def _is_valid_comparable(unit: ComparableUnit, category: str) -> bool:
    return (
        unit.device_category == category
        and unit.area_sqm is not None
        and unit.area_sqm.is_finite()
        and unit.area_sqm > 0
        and unit.heat_kwh is not None
        and not isinstance(unit.heat_kwh, bool)
        and unit.heat_kwh >= 0
    )


def evaluate_block_d(input_: BlockDInput, rules: UviRuleBundle) -> BlockDResult:
    """Calculate the comparable building cross-section or select D2."""

    if input_.minimum_valid_units_including_target != MINIMUM_VALID_UNITS_INCLUDING_TARGET:
        raise ValueError(
            "minimum_valid_units_including_target must be the documented Lokara convention (3)"
        )
    target = input_.target
    if not target.unit_id:
        raise ValueError("target unit_id must not be empty")
    if target.area_sqm is None or not target.area_sqm.is_finite() or target.area_sqm <= 0:
        return BlockDResult(
            status="blocked",
            valid_units_including_target=0,
            average_intensity_kwh_m2=None,
            expected_target_kwh=None,
            delta_kwh=None,
            percent=None,
            basis_de=None,
            rule_evidence=rules.evidence,
            unresolved_conflicts=rules.unresolved_conflicts,
            data_quality_flag="missing_or_non_positive_target_area",
        )
    if target.heat_kwh is None:
        return BlockDResult(
            status="blocked",
            valid_units_including_target=0,
            average_intensity_kwh_m2=None,
            expected_target_kwh=None,
            delta_kwh=None,
            percent=None,
            basis_de=None,
            rule_evidence=rules.evidence,
            unresolved_conflicts=rules.unresolved_conflicts,
            data_quality_flag="missing_target_heat_kwh",
        )
    _require_nonnegative_integer(target.heat_kwh, "target.heat_kwh")

    eligible = tuple(
        unit for unit in input_.other_units if _is_valid_comparable(unit, target.device_category)
    )
    valid_count = 1 + len(eligible)
    if valid_count < input_.minimum_valid_units_including_target:
        return BlockDResult(
            status="use_d2",
            valid_units_including_target=valid_count,
            average_intensity_kwh_m2=None,
            expected_target_kwh=None,
            delta_kwh=None,
            percent=None,
            basis_de=None,
            rule_evidence=rules.evidence,
            unresolved_conflicts=rules.unresolved_conflicts,
        )

    intensities = tuple(
        Decimal(unit.heat_kwh) / unit.area_sqm
        for unit in eligible
        if unit.heat_kwh is not None and unit.area_sqm is not None
    )
    average_exact = sum(intensities, start=Decimal(0)) / Decimal(len(intensities))
    expected = _whole_kwh(average_exact * target.area_sqm)
    delta = target.heat_kwh - expected
    return BlockDResult(
        status="ready",
        valid_units_including_target=valid_count,
        average_intensity_kwh_m2=average_exact.quantize(_ONE_TENTH, rounding=ROUND_HALF_UP),
        expected_target_kwh=expected,
        delta_kwh=delta,
        percent=_display_percent(delta, expected),
        basis_de="Vergleich im Gebäude",
        rule_evidence=rules.evidence,
        unresolved_conflicts=rules.unresolved_conflicts,
    )


def evaluate_block_d2(input_: BlockD2Input, rules: UviRuleBundle) -> BlockD2Result:
    """Calculate the heat-only, degree-day-weighted Heizspiegel fallback."""

    _require_nonnegative_integer(input_.current_heat_kwh, "current_heat_kwh")
    resolved_row = input_.resolved_row
    rule_evidence = tuple(dict.fromkeys((*rules.evidence, *resolved_row.evidence)))
    for name, value in (
        ("target_area_sqm", input_.target_area_sqm),
        ("heizspiegel_mittel_kwh_m2a", resolved_row.heizspiegel_mittel_kwh_m2a),
        ("warm_water_deduction_kwh_m2a", resolved_row.warm_water_deduction_kwh_m2a),
        ("monthly_degree_day_share", input_.monthly_degree_day_share),
    ):
        _require_finite_nonnegative(value, name)
    if input_.target_area_sqm == 0:
        raise ValueError("target_area_sqm must be > 0")
    if input_.monthly_degree_day_share > 1:
        raise ValueError("monthly_degree_day_share must be <= 1")
    if not resolved_row.heizspiegel_vintage:
        raise ValueError("heizspiegel_vintage must not be empty")

    heat_only = resolved_row.heizspiegel_mittel_kwh_m2a - resolved_row.warm_water_deduction_kwh_m2a
    if heat_only <= 0:
        return BlockD2Result(
            status="blocked",
            heat_only_kwh_m2a=heat_only,
            norm_annual_kwh=None,
            norm_month_kwh=None,
            delta_kwh=None,
            percent=None,
            basis_de=None,
            label_de=None,
            attribution_de=None,
            heizspiegel_vintage=resolved_row.heizspiegel_vintage,
            actual_size_class=resolved_row.actual_size_class,
            fallback_label_de=None,
            rule_evidence=rule_evidence,
            unresolved_conflicts=rules.unresolved_conflicts,
            data_quality_flag="non_positive_heat_only_mittel",
        )
    norm_annual_exact = heat_only * input_.target_area_sqm
    norm_month_exact = norm_annual_exact * input_.monthly_degree_day_share
    norm_annual = _whole_kwh(norm_annual_exact)
    norm_month = _whole_kwh(norm_month_exact)
    delta = input_.current_heat_kwh - norm_month
    return BlockD2Result(
        status="ready",
        heat_only_kwh_m2a=heat_only,
        norm_annual_kwh=norm_annual,
        norm_month_kwh=norm_month,
        delta_kwh=delta,
        percent=_display_percent(delta, norm_month),
        basis_de=_D2_BASIS,
        label_de=_D2_LABEL,
        attribution_de=_D2_ATTRIBUTION,
        heizspiegel_vintage=resolved_row.heizspiegel_vintage,
        actual_size_class=resolved_row.actual_size_class,
        fallback_label_de=resolved_row.fallback_label_de,
        rule_evidence=rule_evidence,
        unresolved_conflicts=rules.unresolved_conflicts,
    )


def evaluate_hkv_provisional(
    input_: HkvProvisionalInput, rules: UviRuleBundle
) -> HkvProvisionalResult:
    """Distribute a measured rolling building heat total by HKV units."""

    if input_.measurement_unit is not MeasurementUnit.HKV_UNITS:
        return HkvProvisionalResult(
            status="blocked",
            provisional_unit_kwh=None,
            label_de=None,
            measurement_unit=input_.measurement_unit,
            rule_evidence=rules.evidence,
            unresolved_conflicts=rules.unresolved_conflicts,
            data_quality_flag="measurement_unit_is_not_hkv_units",
        )
    if not input_.explicit_hkv_allocator:
        return HkvProvisionalResult(
            status="blocked",
            provisional_unit_kwh=None,
            label_de=None,
            measurement_unit=input_.measurement_unit,
            rule_evidence=rules.evidence,
            unresolved_conflicts=rules.unresolved_conflicts,
            data_quality_flag="missing_explicit_hkv_allocator_marker",
        )
    _require_finite_nonnegative(input_.unit_hkv_units, "unit_hkv_units")
    _require_finite_nonnegative(input_.building_hkv_units, "building_hkv_units")
    if input_.building_hkv_units == 0:
        return HkvProvisionalResult(
            status="blocked",
            provisional_unit_kwh=None,
            label_de=None,
            measurement_unit=input_.measurement_unit,
            rule_evidence=rules.evidence,
            unresolved_conflicts=rules.unresolved_conflicts,
            data_quality_flag="non_positive_building_hkv_units",
        )
    building_heat = input_.measured_rolling_building_heat_kwh
    if building_heat is None:
        return HkvProvisionalResult(
            status="blocked",
            provisional_unit_kwh=None,
            label_de=None,
            measurement_unit=input_.measurement_unit,
            rule_evidence=rules.evidence,
            unresolved_conflicts=rules.unresolved_conflicts,
            data_quality_flag="missing_measured_rolling_building_heat_total",
        )
    _require_nonnegative_integer(building_heat, "measured_rolling_building_heat_kwh")
    provisional = Decimal(building_heat) * input_.unit_hkv_units / input_.building_hkv_units
    return HkvProvisionalResult(
        status="ready",
        provisional_unit_kwh=_whole_kwh(provisional),
        label_de=_HKV_LABEL,
        measurement_unit=input_.measurement_unit,
        rule_evidence=rules.evidence,
        unresolved_conflicts=rules.unresolved_conflicts,
    )


def _next_month(month: date) -> date:
    if month.month == 12:
        return date(month.year + 1, 1, 1)
    return date(month.year, month.month + 1, 1)


def _interpolate_at(readings: tuple[HeatReading, ...], boundary: date) -> Decimal:
    for reading in readings:
        if reading.read_at == boundary:
            return reading.value
    for left, right in pairwise(readings):
        if left.read_at < boundary < right.read_at:
            elapsed = Decimal((boundary - left.read_at).days)
            span = Decimal((right.read_at - left.read_at).days)
            return left.value + (right.value - left.value) * elapsed / span
    raise ValueError(f"missing readings around month boundary: {boundary.isoformat()}")


def interpolate_month(
    input_: LinearInterpolationInput, rules: UviRuleBundle
) -> LinearInterpolationResult:
    """Interpolate calendar-month boundaries by elapsed days and retain provenance."""

    if input_.month.day != 1:
        raise ValueError("month must be the first day of a calendar month")
    if input_.measurement_unit is not MeasurementUnit.KWH:
        raise ValueError("monthly interpolation currently requires KWH readings")
    if len(input_.readings) < 2:
        raise ValueError("at least two readings are required")
    readings = tuple(sorted(input_.readings, key=lambda reading: reading.read_at))
    if readings != input_.readings:
        raise ValueError("readings must be ordered by read_at")
    if len({reading.reading_id for reading in readings}) != len(readings):
        raise ValueError("reading_id values must be unique")
    if len({reading.read_at for reading in readings}) != len(readings):
        raise ValueError("read_at values must be unique")
    for reading in readings:
        if not reading.reading_id:
            raise ValueError("reading_id must not be empty")
        _require_finite_nonnegative(reading.value, "reading.value")

    boundary_start_date = input_.month
    boundary_end_date = _next_month(input_.month)
    start_value = _interpolate_at(readings, boundary_start_date)
    end_value = _interpolate_at(readings, boundary_end_date)
    movement = end_value - start_value
    if movement < 0:
        raise ValueError("negative unsegmented monthly movement")
    consumption = _whole_kwh(movement)
    return LinearInterpolationResult(
        status="ready",
        boundary_start=InterpolatedBoundary(boundary_start_date, start_value),
        boundary_end=InterpolatedBoundary(boundary_end_date, end_value),
        consumption_kwh=consumption,
        method="linear_by_elapsed_days",
        source_reading_ids=tuple(reading.reading_id for reading in readings),
        source_dates=tuple(reading.read_at for reading in readings),
        source_reading_reasons=tuple(reading.reason for reading in readings),
        source_reading_sources=tuple(reading.source for reading in readings),
        measurement_unit=input_.measurement_unit,
        energy_reference=input_.energy_reference,
        rule_evidence=rules.evidence,
        unresolved_conflicts=rules.unresolved_conflicts,
    )
