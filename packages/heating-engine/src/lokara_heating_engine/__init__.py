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
from .plant_co2 import (
    Co2PlausibilityWarning,
    PlantCo2Input,
    PlantCo2Result,
    assess_co2_plausibility,
    evaluate_plant_co2,
)
from .self_billing import (
    CapabilityWarning,
    DistrictHeatDisclosure,
    HeatingCostBlocks,
    HeatingCostPosition,
    InvoiceAllocation,
    OilConsumptionResult,
    OilPurchase,
    OilStockInput,
    OwnerBurdenPreview,
    PlantCostAggregation,
    WarmWaterCostSeparation,
    aggregate_plant_cost_positions,
    allocate_invoice_to_billing_period,
    calculate_oil_consumption,
    calculate_owner_burden_preview,
    form_heating_cost_blocks,
    separate_warm_water_costs,
)

__version__ = "0.1.0"

__all__ = [
    "CapabilityWarning",
    "Co2Input",
    "Co2PlausibilityWarning",
    "Co2Result",
    "DeviceReadingAggregation",
    "DeviceReadingLine",
    "DeviceReadingSpan",
    "DistrictHeatDisclosure",
    "HeatingCostBlocks",
    "HeatingCostPosition",
    "HeatingDevice",
    "HeatingInput",
    "HeatingInputError",
    "HeatingLine",
    "HeatingResult",
    "HeatingRules",
    "HeatingUnit",
    "InvoiceAllocation",
    "MdlGrossRescalingResult",
    "OilConsumptionResult",
    "OilPurchase",
    "OilStockInput",
    "OwnerBurdenPreview",
    "OwnerResidual",
    "OwnerResidualOrigin",
    "PlantCo2Input",
    "PlantCo2Result",
    "PlantCostAggregation",
    "WarmWaterCostSeparation",
    "WarmWaterInput",
    "WarmWaterSeparation",
    "aggregate_device_reading_spans",
    "aggregate_plant_cost_positions",
    "allocate_invoice_to_billing_period",
    "assess_co2_plausibility",
    "calculate_heating_statement",
    "calculate_oil_consumption",
    "calculate_owner_burden_preview",
    "degree_day_weight",
    "evaluate_plant_co2",
    "form_heating_cost_blocks",
    "landlord_share_percent_for_intensity",
    "rescale_mdl_gross_positions",
    "segment_degree_day_weights",
    "separate_warm_water_costs",
    "split_co2_cost",
]
