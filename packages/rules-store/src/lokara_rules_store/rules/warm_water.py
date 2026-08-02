"""§ 9 Abs. 2 HeizkostenV — separating warm-water energy from heating.

When the warm-water heat quantity is not measured directly:
Q(WW) = 2,5 kWh/(m³·K) × V × (60 °C - 10 °C) = 125 kWh per m³ warm water.
If the volume V is not measured either: 32 kWh per m² living area per year.
"""

from datetime import date
from decimal import Decimal

from lokara_domain import WarmWaterFormula

from ..store import RuleSet, RuleVersion

WARM_WATER_FORMULA: RuleSet[WarmWaterFormula] = RuleSet(
    key="hkvo.warm-water-formula",
    versions=(
        RuleVersion(
            valid_from=date(2009, 1, 1),
            source="§ 9 Abs. 2 HeizkostenV",
            value=WarmWaterFormula(
                factor_kwh_per_m3_kelvin=Decimal("2.5"),
                hot_temp_c=Decimal(60),
                cold_temp_c=Decimal(10),
                area_fallback_kwh_per_sqm_year=Decimal(32),
            ),
        ),
    ),
)
