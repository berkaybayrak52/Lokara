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
)

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


def _whole_kwh(value: Decimal) -> int:
    return int(value.quantize(_ONE, rounding=ROUND_HALF_UP))


def _display_percent(delta_kwh: int, reference_kwh: int) -> Decimal | None:
    if reference_kwh == 0:
        return None
    return (Decimal(delta_kwh) / Decimal(reference_kwh) * _PERCENT).quantize(
        _ONE_TENTH, rounding=ROUND_HALF_UP
    )


def evaluate_block_a(input_: BlockAInput) -> BlockAResult:
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
                data_quality_flag="missing_calorific_factor",
            )
        _require_finite_nonnegative(factor, "calorific_factor_kwh_per_unit")
        movement_kwh = raw_movement * factor
    else:
        return BlockAResult(
            status="blocked",
            movement_kwh=None,
            heat_kwh=None,
            measurement_unit=input_.measurement_unit,
            energy_reference=input_.energy_reference,
            data_quality_flag="hkv_requires_provisional_building_total",
        )

    return BlockAResult(
        status="ready",
        movement_kwh=movement_kwh,
        heat_kwh=_whole_kwh(movement_kwh),
        measurement_unit=input_.measurement_unit,
        energy_reference=input_.energy_reference,
    )


def evaluate_block_b(input_: BlockBInput) -> BlockBResult:
    """Compare current displayed heat with the previous displayed month."""

    _require_nonnegative_integer(input_.current_heat_kwh, "current_heat_kwh")
    previous = input_.previous_month_heat_kwh
    if previous is None:
        return BlockBResult(
            status="unavailable",
            delta_kwh=None,
            percent=None,
            label_de="liegt für den Vormonat noch nicht vor",
        )
    _require_nonnegative_integer(previous, "previous_month_heat_kwh")
    delta = input_.current_heat_kwh - previous
    if previous == 0:
        return BlockBResult(
            status="ready",
            delta_kwh=delta,
            percent=None,
            label_de="kein Vormonatsverbrauch",
        )
    return BlockBResult(
        status="ready",
        delta_kwh=delta,
        percent=_display_percent(delta, previous),
        label_de=None,
    )


def evaluate_block_c(input_: BlockCInput) -> BlockCResult:
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


def evaluate_block_d(input_: BlockDInput) -> BlockDResult:
    """Calculate the comparable building cross-section or select D2."""

    if input_.minimum_valid_units_including_target != 3:
        raise ValueError("minimum_valid_units_including_target must be exactly 3")
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
    )


def evaluate_block_d2(input_: BlockD2Input) -> BlockD2Result:
    """Calculate the heat-only, degree-day-weighted Heizspiegel fallback."""

    _require_nonnegative_integer(input_.current_heat_kwh, "current_heat_kwh")
    for name, value in (
        ("target_area_sqm", input_.target_area_sqm),
        ("heizspiegel_mittel_kwh_m2a", input_.heizspiegel_mittel_kwh_m2a),
        ("warm_water_deduction_kwh_m2a", input_.warm_water_deduction_kwh_m2a),
        ("monthly_degree_day_share", input_.monthly_degree_day_share),
    ):
        _require_finite_nonnegative(value, name)
    if input_.target_area_sqm == 0:
        raise ValueError("target_area_sqm must be > 0")
    if input_.monthly_degree_day_share > 1:
        raise ValueError("monthly_degree_day_share must be <= 1")
    if not input_.heizspiegel_vintage:
        raise ValueError("heizspiegel_vintage must not be empty")

    heat_only = input_.heizspiegel_mittel_kwh_m2a - input_.warm_water_deduction_kwh_m2a
    if heat_only <= 0:
        return BlockD2Result(
            status="blocked",
            heat_only_kwh_m2a=heat_only,
            norm_annual_kwh=None,
            norm_month_kwh=None,
            delta_kwh=None,
            percent=None,
            basis_de=_D2_BASIS,
            label_de=_D2_LABEL,
            attribution_de=_D2_ATTRIBUTION,
            heizspiegel_vintage=input_.heizspiegel_vintage,
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
        heizspiegel_vintage=input_.heizspiegel_vintage,
    )


def evaluate_hkv_provisional(input_: HkvProvisionalInput) -> HkvProvisionalResult:
    """Distribute a measured rolling building heat total by HKV units."""

    if input_.measurement_unit is not MeasurementUnit.HKV_UNITS:
        return HkvProvisionalResult(
            status="blocked",
            provisional_unit_kwh=None,
            label_de=None,
            measurement_unit=input_.measurement_unit,
            data_quality_flag="measurement_unit_is_not_hkv_units",
        )
    if not input_.explicit_hkv_allocator:
        return HkvProvisionalResult(
            status="blocked",
            provisional_unit_kwh=None,
            label_de=None,
            measurement_unit=input_.measurement_unit,
            data_quality_flag="missing_explicit_hkv_allocator_marker",
        )
    _require_finite_nonnegative(input_.unit_hkv_units, "unit_hkv_units")
    _require_finite_nonnegative(input_.building_hkv_units, "building_hkv_units")
    if input_.building_hkv_units == 0:
        return HkvProvisionalResult(
            status="blocked",
            provisional_unit_kwh=None,
            label_de=_HKV_LABEL,
            measurement_unit=input_.measurement_unit,
            data_quality_flag="non_positive_building_hkv_units",
        )
    building_heat = input_.measured_rolling_building_heat_kwh
    if building_heat is None:
        return HkvProvisionalResult(
            status="blocked",
            provisional_unit_kwh=None,
            label_de=_HKV_LABEL,
            measurement_unit=input_.measurement_unit,
            data_quality_flag="missing_measured_rolling_building_heat_total",
        )
    _require_nonnegative_integer(building_heat, "measured_rolling_building_heat_kwh")
    provisional = Decimal(building_heat) * input_.unit_hkv_units / input_.building_hkv_units
    return HkvProvisionalResult(
        status="ready",
        provisional_unit_kwh=_whole_kwh(provisional),
        label_de=_HKV_LABEL,
        measurement_unit=input_.measurement_unit,
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


def interpolate_month(input_: LinearInterpolationInput) -> LinearInterpolationResult:
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
    )
