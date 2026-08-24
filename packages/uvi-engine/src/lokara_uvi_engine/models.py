"""Immutable normalized inputs and deterministic results for the UVI engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from lokara_domain.energy import EnergyReference
from lokara_domain.meter import MeasurementUnit, ReadingReason, ReadingSource


@dataclass(frozen=True, slots=True)
class BlockAInput:
    reading_start_x1000: int
    reading_end_x1000: int
    measurement_unit: MeasurementUnit
    energy_reference: EnergyReference
    calorific_factor_kwh_per_unit: Decimal | None = None
    correctly_segmented_device_change: bool = False


@dataclass(frozen=True, slots=True)
class BlockAResult:
    status: str
    movement_kwh: Decimal | None
    heat_kwh: int | None
    measurement_unit: MeasurementUnit
    energy_reference: EnergyReference
    data_quality_flag: str | None = None


@dataclass(frozen=True, slots=True)
class BlockBInput:
    current_heat_kwh: int
    previous_month_heat_kwh: int | None


@dataclass(frozen=True, slots=True)
class BlockBResult:
    status: str
    delta_kwh: int | None
    percent: Decimal | None
    label_de: str | None


@dataclass(frozen=True, slots=True)
class BlockCInput:
    current_heat_kwh: int
    previous_year_heat_kwh: int | None
    monthly_degree_days_current: Decimal | None
    monthly_degree_days_previous_year: Decimal | None
    previous_year_interpolation_notice_de: str | None


@dataclass(frozen=True, slots=True)
class BlockCResult:
    status: str
    weather_adjusted: bool
    weather_adjustment_factor: Decimal | None
    reference_kwh: int | None
    delta_kwh: int | None
    percent: Decimal | None
    label_de: str | None
    previous_year_interpolation_notice_de: str | None


@dataclass(frozen=True, slots=True)
class ComparableUnit:
    unit_id: str
    area_sqm: Decimal | None
    heat_kwh: int | None
    device_category: str


@dataclass(frozen=True, slots=True)
class BlockDInput:
    target: ComparableUnit
    other_units: tuple[ComparableUnit, ...]
    minimum_valid_units_including_target: int


@dataclass(frozen=True, slots=True)
class BlockDResult:
    status: str
    valid_units_including_target: int
    average_intensity_kwh_m2: Decimal | None
    expected_target_kwh: int | None
    delta_kwh: int | None
    percent: Decimal | None
    basis_de: str | None
    data_quality_flag: str | None = None


@dataclass(frozen=True, slots=True)
class BlockD2Input:
    current_heat_kwh: int
    target_area_sqm: Decimal
    energy_source: str
    building_size_class: str
    heizspiegel_mittel_kwh_m2a: Decimal
    warm_water_deduction_kwh_m2a: Decimal
    monthly_degree_day_share: Decimal
    heizspiegel_vintage: str


@dataclass(frozen=True, slots=True)
class BlockD2Result:
    status: str
    heat_only_kwh_m2a: Decimal
    norm_annual_kwh: int | None
    norm_month_kwh: int | None
    delta_kwh: int | None
    percent: Decimal | None
    basis_de: str
    label_de: str
    attribution_de: str
    heizspiegel_vintage: str
    data_quality_flag: str | None = None


@dataclass(frozen=True, slots=True)
class HkvProvisionalInput:
    measured_rolling_building_heat_kwh: int | None
    unit_hkv_units: Decimal
    building_hkv_units: Decimal
    measurement_unit: MeasurementUnit
    explicit_hkv_allocator: bool


@dataclass(frozen=True, slots=True)
class HkvProvisionalResult:
    status: str
    provisional_unit_kwh: int | None
    label_de: str | None
    measurement_unit: MeasurementUnit
    data_quality_flag: str | None = None


@dataclass(frozen=True, slots=True)
class HeatReading:
    reading_id: str
    value: Decimal
    read_at: date
    source: ReadingSource
    reason: ReadingReason


@dataclass(frozen=True, slots=True)
class LinearInterpolationInput:
    month: date
    readings: tuple[HeatReading, ...]
    measurement_unit: MeasurementUnit
    energy_reference: EnergyReference


@dataclass(frozen=True, slots=True)
class InterpolatedBoundary:
    at: date
    value: Decimal


@dataclass(frozen=True, slots=True)
class LinearInterpolationResult:
    status: str
    boundary_start: InterpolatedBoundary
    boundary_end: InterpolatedBoundary
    consumption_kwh: int
    method: str
    source_reading_ids: tuple[str, ...]
    source_dates: tuple[date, ...]
    source_reading_reasons: tuple[ReadingReason, ...]
    source_reading_sources: tuple[ReadingSource, ...]
    measurement_unit: MeasurementUnit
    energy_reference: EnergyReference
