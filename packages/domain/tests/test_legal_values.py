from decimal import Decimal

import pytest
from lokara_domain import DegreeDayTable, WarmWaterFormula


class TestDegreeDayTable:
    def test_rejects_tables_not_summing_to_1000(self) -> None:
        with pytest.raises(ValueError):
            DegreeDayTable(promille_by_month=(100,) * 12)


class TestWarmWaterFormula:
    def test_computes_energy_for_volume(self) -> None:
        formula = WarmWaterFormula(
            factor_kwh_per_m3_kelvin=Decimal("2.5"),
            hot_temp_c=Decimal(60),
            cold_temp_c=Decimal(10),
            area_fallback_kwh_per_sqm_year=Decimal(32),
        )
        # § 9 Abs. 2 HeizkostenV: 2.5 kWh/(m³·K) × V × 50 K = 125 kWh per m³.
        assert formula.energy_kwh_for_volume(Decimal(40)) == Decimal(5000)
