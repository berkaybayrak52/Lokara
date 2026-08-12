"""Versioned rule data, one module per legal domain.

TODO(M7): Anlage-V line-number mappings (year-versioned) and SKR03/SKR04
category mappings arrive with the tax export milestone.
"""

from .co2_emission_factors import CO2_FALLBACK_EMISSION_FACTORS
from .co2_split import CO2_SPLIT_TABLE
from .degree_days import DEGREE_DAY_TABLE
from .heating_split import DEFAULT_CONSUMPTION_SHARE, HEATING_SPLIT_BOUNDS
from .warm_water import WARM_WATER_FORMULA

__all__ = [
    "CO2_FALLBACK_EMISSION_FACTORS",
    "CO2_SPLIT_TABLE",
    "DEFAULT_CONSUMPTION_SHARE",
    "DEGREE_DAY_TABLE",
    "HEATING_SPLIT_BOUNDS",
    "WARM_WATER_FORMULA",
]
