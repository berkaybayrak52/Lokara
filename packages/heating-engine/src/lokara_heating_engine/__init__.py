"""Pure heating + CO₂ engine — M2.

§§7/8 HKVO base/consumption split, §9 warm-water separation, §9a estimation,
degree-day apportionment on renter change, CO2KostAufG 10-step split. Every
legal ratio/table arrives as a resolved rules-store value with a Rechtsstand.
Depends only on lokara-domain.
"""

from .co2 import landlord_share_percent_for_intensity, split_co2_cost
from .degree_days import degree_day_weight, segment_degree_day_weights
from .device_readings import (
    DeviceReadingAggregation,
    DeviceReadingLine,
    DeviceReadingSpan,
    HeatingDevice,
    aggregate_device_reading_spans,
)
from .engine import calculate_heating_statement
from .inputs import (
    Co2Input,
    Co2Result,
    HeatingInput,
    HeatingInputError,
    HeatingLine,
    HeatingResult,
    HeatingRules,
    HeatingUnit,
    OwnerResidual,
    OwnerResidualOrigin,
    WarmWaterInput,
    WarmWaterSeparation,
)
from .mdl import MdlGrossRescalingResult, rescale_mdl_gross_positions

__version__ = "0.1.0"

__all__ = [
    "Co2Input",
    "Co2Result",
    "DeviceReadingAggregation",
    "DeviceReadingLine",
    "DeviceReadingSpan",
    "HeatingDevice",
    "HeatingInput",
    "HeatingInputError",
    "HeatingLine",
    "HeatingResult",
    "HeatingRules",
    "HeatingUnit",
    "MdlGrossRescalingResult",
    "OwnerResidual",
    "OwnerResidualOrigin",
    "WarmWaterInput",
    "WarmWaterSeparation",
    "aggregate_device_reading_spans",
    "calculate_heating_statement",
    "degree_day_weight",
    "landlord_share_percent_for_intensity",
    "rescale_mdl_gross_positions",
    "segment_degree_day_weights",
    "split_co2_cost",
]
