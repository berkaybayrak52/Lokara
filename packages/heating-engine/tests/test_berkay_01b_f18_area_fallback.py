"""`01b-F18` — exact WE-03-only § 9a Abs. 2 fallback.

Source: Page 01b E14/F18. Transcription: `docs/03-nk-heating-engines.md`
§§ 0, 4 H5/H6, 6 E14 and the F18 output override in § 9.1.
Rechtsstand 08/2026.

Only WE-03's relevant readings are missing: 58/194 = 29.90 %, not every
reading in the building. Emir confirmed on 16.08.2026 that Berkay's printed
cent table is authoritative and withdrew the earlier derived R1 override.
"""

from decimal import Decimal

from berkay_01b_golden import PAGE_01B_GOLDENS
from lokara_domain import (
    Co2Step,
    Co2Table,
    DegreeDayTable,
    HeatingSplitBounds,
    Occupancy,
    WarmWaterFormula,
    cents,
    period,
)
from lokara_heating_engine import (
    Co2Input,
    HeatingInput,
    HeatingResult,
    HeatingRules,
    HeatingUnit,
    WarmWaterInput,
    calculate_heating_statement,
)

CASE = PAGE_01B_GOLDENS["01b-F18"]
CO2_TABLE: Co2Table = (
    Co2Step(Decimal(12), 0),
    Co2Step(Decimal(17), 10),
    Co2Step(Decimal(22), 20),
    Co2Step(Decimal(27), 30),
    Co2Step(Decimal(32), 40),
    Co2Step(Decimal(37), 50),
    Co2Step(Decimal(42), 60),
    Co2Step(Decimal(47), 70),
    Co2Step(Decimal(52), 80),
    Co2Step(None, 95),
)
RULES = HeatingRules(
    consumption_share=Decimal("0.7"),
    split_bounds=HeatingSplitBounds(Decimal("0.5"), Decimal("0.7")),
    warm_water_formula=WarmWaterFormula(Decimal("2.5"), Decimal(60), Decimal(10), Decimal(32)),
    degree_days=DegreeDayTable(
        tenth_promille_by_month=(1700, 1500, 1300, 800, 400, 133, 133, 134, 300, 800, 1200, 1600)
    ),
    co2_table=CO2_TABLE,
    co2_rechtsstand="Rechtsstand 01/2023",
)


def _statement() -> HeatingResult:
    return calculate_heating_statement(
        HeatingInput(
            billing_period=period("2025-01-01", "2026-01-01"),
            total_cost=cents(350_600),
            total_energy_kwh=Decimal(28_000),
            units=(
                HeatingUnit("WE-01", 6200, Decimal("4100.0"), Decimal(34)),
                HeatingUnit("WE-02", 7400, Decimal("3600.0"), Decimal(21)),
                HeatingUnit("WE-03", 5800, None, None),
            ),
            occupancies=(
                Occupancy("WE-01", "Muster", period("2025-01-01")),
                Occupancy("WE-02", "Schneider", period("2025-01-01", "2025-08-01")),
                Occupancy("WE-02", "Weber", period("2025-09-01")),
                Occupancy("WE-03", "Beispiel", period("2025-01-01")),
            ),
            rules=RULES,
            warm_water=WarmWaterInput(volume_m3=Decimal(78)),
            co2=Co2Input(total_co2_kg=Decimal(5628), co2_cost=cents(30_954)),
        )
    )


def test_berkay_01b_f18_uses_only_we03_as_the_missing_area() -> None:
    units = _statement()
    assert CASE["missing_unit_ids"] == ("WE-03",)
    assert Decimal(str(CASE["affected_area_sqm"])) / Decimal(
        str(CASE["building_area_sqm"])
    ) == Decimal(58) / Decimal(194)
    assert units.heat_fallback_to_area is True
    assert units.ww_fallback_to_area is True


def test_berkay_01b_f18_berkay_cent_table_is_authoritative() -> None:
    result = _statement()
    renter_totals = tuple(int(line.total) for line in result.lines)
    owner_total = int(result.owner_residual.total)

    assert renter_totals == CASE["renter_totals"]
    assert owner_total == CASE["owner_total"]
    assert sum(renter_totals) + owner_total == CASE["billable_total"]
    assert result.co2 is not None
    assert sum(renter_totals) + owner_total + int(result.co2.landlord_amount) == 350_600
