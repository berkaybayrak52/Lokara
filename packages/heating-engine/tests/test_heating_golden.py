"""Golden fixtures for the heating/CO₂ engine (M2) — committed before the engine.

§§7/8 base/consumption split, §9 warm-water separation, §9a estimation,
degree-day apportionment on renter change, CO2KostAufG 10-step split.
Every fixture reconciles to the input total to the cent.

**Re-shaped 14.08.2026 — an Eigentümerzeile at 0,00 €, and no cent moved.**
`berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md` § 1: the Eigentümeranteil is one residual
line per Liegenschaft, and § 1.3 Frage 1 makes it exist *"auch bei 0,00 €, auch
ohne Leerstand, auch ohne Eigennutzung"*. Every building in this file is fully
let, so each fixture gained an owner row and none of them gained an amount:

* **base/WW split and CO₂ split** — 50/30/20 divides every base pot; 600/250/150
  (= 12/5/3 over 20) and 20/12/8 (= 5/3/2 over 10) divide every consumption pot.
* **degree-day apportionment** — four parties, and each block's `round_half_up`
  shares already sum to the pot, incl. the exact half cent 11.157,5 → 11.158.
* **§ 9a estimation (all three)** — 600/250/212,5 over 1.062,5 and the pure area
  key both divide exactly.

The delta across the suite was bounded in advance: **seven blocks move, one cent
each, and none is in this file** (`docs/03` § 9.2 → the fan-out table). A value
that moves here is a bug in the wiring, not a fixture to adjust.
"""

from decimal import Decimal

import pytest
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
    HeatingInputError,
    HeatingRules,
    HeatingUnit,
    WarmWaterInput,
    calculate_heating_statement,
    landlord_share_percent_for_intensity,
)

YEAR_2025 = period("2025-01-01", "2026-01-01")

SPLIT_BOUNDS = HeatingSplitBounds(
    min_consumption_share=Decimal("0.5"), max_consumption_share=Decimal("0.7")
)
WW_FORMULA = WarmWaterFormula(
    factor_kwh_per_m3_kelvin=Decimal("2.5"),
    hot_temp_c=Decimal(60),
    cold_temp_c=Decimal(10),
    area_fallback_kwh_per_sqm_year=Decimal(32),
)
# Synthetic, **not** the rules-store table: the superseded 01/1981 shape ×10, so
# Jan–Jun stays a legible 5850 of 10 000 (585,0 ‰) and the hand-computed rows
# below can be checked by eye. The unit is Zehntelpromille, Σ 10 000 (K3,
# `docs/03` → "Seite 01b … (2) K3"); the live VDI 2067 table is pinned in
# `packages/rules-store/tests/test_rule_data.py` and is what the demo path uses.
DEGREE_DAYS = DegreeDayTable(
    tenth_promille_by_month=(1700, 1500, 1300, 800, 400, 150, 100, 100, 300, 800, 1200, 1650)
)
CO2_TABLE: Co2Table = (
    Co2Step(max_intensity_exclusive=Decimal(12), landlord_share_percent=0),
    Co2Step(max_intensity_exclusive=Decimal(17), landlord_share_percent=10),
    Co2Step(max_intensity_exclusive=Decimal(22), landlord_share_percent=20),
    Co2Step(max_intensity_exclusive=Decimal(27), landlord_share_percent=30),
    Co2Step(max_intensity_exclusive=Decimal(32), landlord_share_percent=40),
    Co2Step(max_intensity_exclusive=Decimal(37), landlord_share_percent=50),
    Co2Step(max_intensity_exclusive=Decimal(42), landlord_share_percent=60),
    Co2Step(max_intensity_exclusive=Decimal(47), landlord_share_percent=70),
    Co2Step(max_intensity_exclusive=Decimal(52), landlord_share_percent=80),
    Co2Step(max_intensity_exclusive=None, landlord_share_percent=95),
)

RULES = HeatingRules(
    consumption_share=Decimal("0.7"),
    split_bounds=SPLIT_BOUNDS,
    warm_water_formula=WW_FORMULA,
    degree_days=DEGREE_DAYS,
    co2_table=CO2_TABLE,
    co2_rechtsstand="Rechtsstand 01/2023",
)

FULL_YEAR_OCCUPANCIES = (
    Occupancy("unit-a", "ten-a", period("2025-01-01")),
    Occupancy("unit-b", "ten-b", period("2024-08-01")),
    Occupancy("unit-c", "ten-c", period("2023-01-01")),
)


def full_year_units() -> tuple[HeatingUnit, ...]:
    return (
        HeatingUnit("unit-a", 5000, heat_consumption=Decimal(600), ww_consumption_m3=Decimal(20)),
        HeatingUnit("unit-b", 3000, heat_consumption=Decimal(250), ww_consumption_m3=Decimal(12)),
        HeatingUnit("unit-c", 2000, heat_consumption=Decimal(150), ww_consumption_m3=Decimal(8)),
    )


class TestBaseConsumptionAndWarmWaterSplit:
    """§§7/8 + §9: €10,000, 20,000 kWh, 40 m³ WW (Q_ww = 125×40 = 5,000 kWh → 25 %)."""

    def test_hand_computed_table_reconciles(self) -> None:
        result = calculate_heating_statement(
            HeatingInput(
                billing_period=YEAR_2025,
                total_cost=cents(1_000_000),
                total_energy_kwh=Decimal(20000),
                units=full_year_units(),
                occupancies=FULL_YEAR_OCCUPANCIES,
                rules=RULES,
                warm_water=WarmWaterInput(volume_m3=Decimal(40)),
            )
        )
        rows = [
            (
                line.unit_id,
                line.tenancy_id,
                int(line.heating_base),
                int(line.heating_consumption),
                int(line.ww_base),
                int(line.ww_consumption),
                int(line.total),
            )
            for line in result.lines
        ]
        # Heating pot 750,000 (base 225,000 / cons 525,000); WW pot 250,000
        # (base 75,000 / cons 175,000). Base by area (50/30/20 m², full year),
        # heat cons by 600/250/150 units, WW cons by 20/12/8 m³.
        assert rows == [
            ("unit-a", "ten-a", 112500, 315000, 37500, 87500, 552500),
            ("unit-b", "ten-b", 67500, 131250, 22500, 52500, 273750),
            ("unit-c", "ten-c", 45000, 78750, 15000, 35000, 173750),
        ]
        # Every block divides exactly, so the Eigentümerzeile is 0,00 € — and it
        # still renders (§ 1.3 Frage 1). No vacancy, no self-use ⇒ block (a) is
        # empty and the Bemessung column stays blank, which is `None`, not 0.
        owner = result.owner_residual
        assert (
            int(owner.heating_base),
            int(owner.heating_consumption),
            int(owner.ww_base),
            int(owner.ww_consumption),
            int(owner.total),
        ) == (0, 0, 0, 0, 0)
        assert owner.origins == ()
        assert int(owner.rounding_difference) == 0
        assert owner.base_weight_sqm_days_x100 is None
        assert result.total == 1_000_000
        assert result.co2 is None
        assert result.estimated_unit_ids == ()
        assert result.consumption_fallback_to_area is False

    def test_consumption_share_outside_hkvo_bounds_is_rejected(self) -> None:
        bad_rules = HeatingRules(
            consumption_share=Decimal("0.8"),
            split_bounds=SPLIT_BOUNDS,
            warm_water_formula=WW_FORMULA,
            degree_days=DEGREE_DAYS,
        )
        with pytest.raises(HeatingInputError):
            calculate_heating_statement(
                HeatingInput(
                    billing_period=YEAR_2025,
                    total_cost=cents(1_000_000),
                    total_energy_kwh=Decimal(20000),
                    units=full_year_units(),
                    occupancies=FULL_YEAR_OCCUPANCIES,
                    rules=bad_rules,
                    warm_water=WarmWaterInput(volume_m3=Decimal(40)),
                )
            )


class TestCo2TenStepSplit:
    """CO2KostAufG: 2,000 kg over 100 m² → 20 kg/m²/a → landlord 20 %.

    These are **synthetic engine values**, chosen so the step selection and the
    pre-split deduction are legible (20 % of 300,00 € = 60,00 €). They are not a
    plausible building: 300,00 € for 2.000 kg implies 150 €/t against the 2025
    BEHG rate of 65,45 €/t incl. USt. The *demo's* fixture is a different thing
    and is required to be plausible on its face — `docs/06` → "Scenario 2 — the
    fuel, the emissions and the CO₂ price", statutory figures in `docs/03` →
    "Where `total_co2_kg` and `co2_cost` come from". Do not copy these numbers
    into a demo or a seed.
    """

    def test_landlord_share_is_deducted_before_the_renter_split(self) -> None:
        result = calculate_heating_statement(
            HeatingInput(
                billing_period=YEAR_2025,
                total_cost=cents(1_030_000),
                total_energy_kwh=Decimal(20000),
                units=full_year_units(),
                occupancies=FULL_YEAR_OCCUPANCIES,
                rules=RULES,
                warm_water=WarmWaterInput(volume_m3=Decimal(40)),
                co2=Co2Input(total_co2_kg=Decimal(2000), co2_cost=cents(30000)),
            )
        )
        co2 = result.co2
        assert co2 is not None
        assert co2.intensity_kg_per_sqm == Decimal(20)
        assert co2.landlord_share_percent == 20
        assert int(co2.landlord_amount) == 6000  # 20 % of €300.00
        assert int(co2.renter_amount) == 24000
        assert co2.rechtsstand == "Rechtsstand 01/2023"
        # Billable = 1,030,000 - 6,000 = 1,024,000 → WW pot 256,000 / heating pot 768,000.
        rows = [
            (
                line.unit_id,
                int(line.heating_base),
                int(line.heating_consumption),
                int(line.ww_base),
                int(line.ww_consumption),
                int(line.total),
            )
            for line in result.lines
        ]
        assert rows == [
            ("unit-a", 115200, 322560, 38400, 89600, 565760),
            ("unit-b", 69120, 134400, 23040, 53760, 280320),
            ("unit-c", 46080, 80640, 15360, 35840, 177920),
        ]
        # Fully let and every block divides exactly ⇒ Eigentümerzeile 0,00 €.
        owner = result.owner_residual
        assert int(owner.total) == 0
        assert owner.origins == ()
        # Renter lines + Eigentümeranteil + landlord CO₂ reconcile to the input.
        # The CO₂-Vermieteranteil is a **statutory deduction** (§ 7 CO2KostAufG)
        # taken before the split; the residual is what is left of a Blockbetrag
        # after it. Two figures with one bearer, never one (`docs/03` § 9.3).
        assert (
            sum(int(line.total) for line in result.lines)
            + int(owner.total)
            + int(co2.landlord_amount)
            == 1_030_000
        )
        assert result.total == 1_030_000

    def test_step_selection_boundaries(self) -> None:
        assert landlord_share_percent_for_intensity(Decimal("11.99"), CO2_TABLE) == 10
        assert landlord_share_percent_for_intensity(Decimal("11.9499"), CO2_TABLE) == 0
        assert landlord_share_percent_for_intensity(Decimal(12), CO2_TABLE) == 10
        assert landlord_share_percent_for_intensity(Decimal(20), CO2_TABLE) == 20
        assert landlord_share_percent_for_intensity(Decimal("51.99"), CO2_TABLE) == 95
        assert landlord_share_percent_for_intensity(Decimal("51.9499"), CO2_TABLE) == 80
        assert landlord_share_percent_for_intensity(Decimal(52), CO2_TABLE) == 95
        assert landlord_share_percent_for_intensity(Decimal(60), CO2_TABLE) == 95

    def test_co2_requires_the_table_and_rechtsstand(self) -> None:
        rules_without_co2 = HeatingRules(
            consumption_share=Decimal("0.7"),
            split_bounds=SPLIT_BOUNDS,
            warm_water_formula=WW_FORMULA,
            degree_days=DEGREE_DAYS,
        )
        with pytest.raises(HeatingInputError):
            calculate_heating_statement(
                HeatingInput(
                    billing_period=YEAR_2025,
                    total_cost=cents(1_030_000),
                    total_energy_kwh=Decimal(20000),
                    units=full_year_units(),
                    occupancies=FULL_YEAR_OCCUPANCIES,
                    rules=rules_without_co2,
                    warm_water=WarmWaterInput(volume_m3=Decimal(40)),
                    co2=Co2Input(total_co2_kg=Decimal(2000), co2_cost=cents(30000)),
                )
            )


class TestDegreeDayApportionment:
    """Renter change in unit B at Jul 1, single annual reading of 250 heat units:
    Jan–Jun 5850 / Jul–Dec 4150 Zehntelpromille of this file's synthetic table
    (585,0 ‰ / 415,0 ‰) → 146.25 vs 103.75 units. The ×10 rescale of K3 is a
    change of unit, not of ratio, so no cent below moves. WW (not
    weather-dependent) and base costs split by days instead."""

    def test_mid_period_renter_change_without_interim_reading(self) -> None:
        occupancies = (
            Occupancy("unit-a", "ten-a", period("2025-01-01")),
            Occupancy("unit-b", "ten-b1", period("2024-08-01", "2025-07-01")),
            Occupancy("unit-b", "ten-b2", period("2025-07-01")),
            Occupancy("unit-c", "ten-c", period("2023-01-01")),
        )
        result = calculate_heating_statement(
            HeatingInput(
                billing_period=YEAR_2025,
                total_cost=cents(1_000_000),
                total_energy_kwh=Decimal(20000),
                units=full_year_units(),
                occupancies=occupancies,
                rules=RULES,
                warm_water=WarmWaterInput(volume_m3=Decimal(40)),
            )
        )
        rows = [
            (
                line.unit_id,
                line.tenancy_id,
                int(line.heating_base),
                int(line.heating_consumption),
                int(line.ww_base),
                int(line.ww_consumption),
                int(line.total),
            )
            for line in result.lines
        ]
        assert rows == [
            ("unit-a", "ten-a", 112500, 315000, 37500, 87500, 552500),
            ("unit-b", "ten-b1", 33473, 76781, 11158, 26034, 147446),
            ("unit-b", "ten-b2", 34027, 54469, 11342, 26466, 126304),
            ("unit-c", "ten-c", 45000, 78750, 15000, 35000, 173750),
        ]
        # A Nutzerwechsel is **not** a vacancy: both segments are Mietverhält-
        # nisse, so both keep a money row and the Eigentümerzeile is 0,00 €.
        # `11.157,5 → 11.158` is the exact half cent — R1 half-up, and the block
        # still sums to its pot, so nothing is left for the residual.
        owner = result.owner_residual
        assert int(owner.total) == 0
        assert owner.origins == ()
        assert len(result.lines) == 4
        assert sum(int(line.total) for line in result.lines) + int(owner.total) == 1_000_000


class TestParagraph9aEstimation:
    """§9a: missing readings are estimated from the measured units' per-m²
    average; if the affected area exceeds 25 %, the whole consumption portion
    falls back to the fixed (area) key. No central warm water here."""

    def _input(self, units: tuple[HeatingUnit, ...]) -> HeatingInput:
        return HeatingInput(
            billing_period=YEAR_2025,
            total_cost=cents(750_000),
            total_energy_kwh=Decimal(15000),
            units=units,
            occupancies=FULL_YEAR_OCCUPANCIES,
            rules=RULES,
            warm_water=None,
        )

    def test_single_missing_reading_is_estimated_per_sqm(self) -> None:
        units = (
            HeatingUnit("unit-a", 5000, heat_consumption=Decimal(600)),
            HeatingUnit("unit-b", 3000, heat_consumption=Decimal(250)),
            HeatingUnit("unit-c", 2000, heat_consumption=None),  # 20 % of area
        )
        result = calculate_heating_statement(self._input(units))
        # Estimate C: (600+250)/(50+30) m² × 20 m² = 212.5 units.
        # Cons pot 525,000 over [600, 250, 212.5]; base pot 225,000 by area.
        rows = [
            (line.unit_id, int(line.heating_base), int(line.heating_consumption))
            for line in result.lines
        ]
        assert rows == [
            ("unit-a", 112500, 296471),
            ("unit-b", 67500, 123529),
            ("unit-c", 45000, 105000),
        ]
        assert result.estimated_unit_ids == ("unit-c",)
        assert result.consumption_fallback_to_area is False
        assert int(result.owner_residual.total) == 0
        assert (
            sum(int(line.total) for line in result.lines) + int(result.owner_residual.total)
            == 750_000
        )

    def test_more_than_25_percent_missing_falls_back_to_area(self) -> None:
        units = (
            HeatingUnit("unit-a", 5000, heat_consumption=Decimal(600)),
            HeatingUnit("unit-b", 3000, heat_consumption=None),
            HeatingUnit("unit-c", 2000, heat_consumption=None),  # 50 % of area missing
        )
        result = calculate_heating_statement(self._input(units))
        rows = [
            (line.unit_id, int(line.heating_base), int(line.heating_consumption))
            for line in result.lines
        ]
        # Consumption pot allocated like the base pot: by day-weighted area.
        assert rows == [
            ("unit-a", 112500, 262500),
            ("unit-b", 67500, 157500),
            ("unit-c", 45000, 105000),
        ]
        assert result.consumption_fallback_to_area is True
        assert int(result.owner_residual.total) == 0
        assert (
            sum(int(line.total) for line in result.lines) + int(result.owner_residual.total)
            == 750_000
        )

    def test_all_readings_missing_falls_back_to_area(self) -> None:
        units = (
            HeatingUnit("unit-a", 5000, heat_consumption=None),
            HeatingUnit("unit-b", 3000, heat_consumption=None),
            HeatingUnit("unit-c", 2000, heat_consumption=None),
        )
        result = calculate_heating_statement(self._input(units))
        assert result.consumption_fallback_to_area is True
        assert int(result.owner_residual.total) == 0
        assert (
            sum(int(line.total) for line in result.lines) + int(result.owner_residual.total)
            == 750_000
        )
