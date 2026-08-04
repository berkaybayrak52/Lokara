"""§ 5 Abs. 1 Satz 4 CO2KostAufG — the Anlage table is per year, so a short
Abrechnungszeitraum shortens the table.

Spec: `docs/03-nk-heating-engines.md` § "The Stufenmodell is a per-year table —
a short Abrechnungszeitraum shortens the table". Rechtsstand 01/2023.

    "Ist ein Abrechnungszeitraum von unter einem Jahr vereinbart, so sind die
     Werte der Einstufungstabelle in der Anlage anteilig zu kürzen."

The statute shortens the *table*; it does not extrapolate the emissions. So
`intensity_kg_per_sqm` stays the period figure and the classification runs
against bounds multiplied by

    period_factor = min(1, days(period) / days(reference year))

with the reference year anchored on `valid_from`, so any full 12-month period —
leap or not — comes out at exactly 1 and nothing on the demo path moves.
"""

from decimal import Decimal

import pytest
from lokara_domain import (
    Co2Step,
    Co2Table,
    DegreeDayTable,
    HeatingSplitBounds,
    Occupancy,
    Period,
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
)

SPLIT_BOUNDS = HeatingSplitBounds(
    min_consumption_share=Decimal("0.5"), max_consumption_share=Decimal("0.7")
)
WW_FORMULA = WarmWaterFormula(
    factor_kwh_per_m3_kelvin=Decimal("2.5"),
    hot_temp_c=Decimal(60),
    cold_temp_c=Decimal(10),
    area_fallback_kwh_per_sqm_year=Decimal(32),
)
DEGREE_DAYS = DegreeDayTable(
    promille_by_month=(170, 150, 130, 80, 40, 15, 10, 10, 30, 80, 120, 165)
)
# Anlage CO2KostAufG, bounds in kg CO₂/m²/**a** — the per-year unit is the whole point.
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

# Long-standing renters, so occupancy never confounds the CO₂ classification.
OCCUPANCIES = (
    Occupancy("unit-a", "ten-a", period("2023-01-01")),
    Occupancy("unit-b", "ten-b", period("2023-01-01")),
    Occupancy("unit-c", "ten-c", period("2023-01-01")),
)


def units() -> tuple[HeatingUnit, ...]:
    """50 + 30 + 20 = 100 m², so kg ÷ 100 is the intensity by inspection."""
    return (
        HeatingUnit("unit-a", 5000, heat_consumption=Decimal(600), ww_consumption_m3=Decimal(20)),
        HeatingUnit("unit-b", 3000, heat_consumption=Decimal(250), ww_consumption_m3=Decimal(12)),
        HeatingUnit("unit-c", 2000, heat_consumption=Decimal(150), ww_consumption_m3=Decimal(8)),
    )


def heating_input(
    billing_period: Period,
    *,
    total_cost: int,
    total_energy_kwh: int,
    ww_volume_m3: int,
    total_co2_kg: int,
    co2_cost: int,
) -> HeatingInput:
    return HeatingInput(
        billing_period=billing_period,
        total_cost=cents(total_cost),
        total_energy_kwh=Decimal(total_energy_kwh),
        units=units(),
        occupancies=OCCUPANCIES,
        rules=RULES,
        warm_water=WarmWaterInput(volume_m3=Decimal(ww_volume_m3)),
        co2=Co2Input(total_co2_kg=Decimal(total_co2_kg), co2_cost=cents(co2_cost)),
    )


class TestInterimPeriodShortensTheAnlageTable:
    """The defect this file exists for.

    Abrechnungszeitraum 01.01.2025–01.07.2025 = **181 days**; reference year
    01.01.2025–01.01.2026 = **365 days** → factor 181/365 = 0,49589.

    1.950 kg CO₂ over 100 m² → intensity **19,5 kg CO₂/m²** for the period.

    * Against the unscaled per-year table: 17 ≤ 19,5 < 22 → Vermieter **20 %**.
    * Against the shortened table (§ 5 Abs. 1 S. 4): the bounds become
      … 32→15,868 · 37→**18,348** · 42→**20,827** … so 18,348 ≤ 19,5 < 20,827
      → Vermieter **60 %**. Equivalently 19,5 ÷ 0,49589 = 39,32 kg/m²/a.

    Neither reading is near a bound — 19,5 sits 2,5 inside a 5-wide band on the
    wrong reading and 1,15/1,33 inside the shortened band on the right one — so
    this pins a Stufe change, not a rounding accident.
    """

    def test_landlord_share_uses_the_shortened_table(self) -> None:
        result = calculate_heating_statement(
            heating_input(
                period("2025-01-01", "2025-07-01"),
                total_cost=530_000,
                total_energy_kwh=10_000,
                ww_volume_m3=20,
                total_co2_kg=1950,
                co2_cost=30_000,
            )
        )
        co2 = result.co2
        assert co2 is not None
        # The statute shortens the table, it does not annualise the emissions:
        # the disclosed value stays the period figure.
        assert co2.intensity_kg_per_sqm == Decimal("19.5")
        assert co2.landlord_share_percent == 60  # not 20 — that is the defect
        assert int(co2.landlord_amount) == 18_000  # 180,00 € of 300,00 €
        assert int(co2.renter_amount) == 12_000  # 120,00 €, not 240,00 €
        assert co2.rechtsstand == "Rechtsstand 01/2023"

    def test_the_renters_side_and_the_total_still_reconcile(self) -> None:
        result = calculate_heating_statement(
            heating_input(
                period("2025-01-01", "2025-07-01"),
                total_cost=530_000,
                total_energy_kwh=10_000,
                ww_volume_m3=20,
                total_co2_kg=1950,
                co2_cost=30_000,
            )
        )
        co2 = result.co2
        assert co2 is not None
        # Billable after the CO₂ deduction: 530.000 minus 18.000 = 512.000 cents.
        # Under-classified today it would be 524.000 — 120,00 € too much on the
        # renters' side of a legal document.
        assert sum(int(line.total) for line in result.lines) == 512_000
        assert sum(int(line.total) for line in result.lines) + int(co2.landlord_amount) == 530_000
        assert int(result.total) == 530_000


class TestFullYearIsUntouched:
    """factor == 1 for any full 12-month period — the demo path must not move."""

    def test_full_calendar_year_keeps_the_unscaled_table(self) -> None:
        result = calculate_heating_statement(
            heating_input(
                period("2025-01-01", "2026-01-01"),  # 365 days
                total_cost=1_030_000,
                total_energy_kwh=20_000,
                ww_volume_m3=40,
                total_co2_kg=2000,
                co2_cost=30_000,
            )
        )
        co2 = result.co2
        assert co2 is not None
        assert co2.intensity_kg_per_sqm == Decimal(20)
        assert co2.landlord_share_percent == 20
        assert int(co2.landlord_amount) == 6_000
        assert int(co2.renter_amount) == 24_000
        assert int(result.total) == 1_030_000

    def test_full_leap_year_is_not_stretched_past_the_table(self) -> None:
        """366/366, not 366/365: a leap year is not *more* than a year. A naive
        divisor of 365 would scale the bounds up by 0,27 % and report an
        intensity of 19,945 instead of 20."""
        result = calculate_heating_statement(
            heating_input(
                period("2024-01-01", "2025-01-01"),  # 366 days
                total_cost=1_030_000,
                total_energy_kwh=20_000,
                ww_volume_m3=40,
                total_co2_kg=2000,
                co2_cost=30_000,
            )
        )
        co2 = result.co2
        assert co2 is not None
        assert co2.intensity_kg_per_sqm == Decimal(20)
        assert co2.landlord_share_percent == 20
        assert int(co2.landlord_amount) == 6_000
        assert int(co2.renter_amount) == 24_000
        assert int(result.total) == 1_030_000


class TestNoOverCorrection:
    """The open-ended top step has no bound to shorten."""

    def test_building_already_in_the_top_step_stays_at_95_percent(self) -> None:
        # 5.500 kg over 100 m² in 181 days = 55 kg/m², already past the 52
        # bound before any shortening — and past 25,79 after it.
        result = calculate_heating_statement(
            heating_input(
                period("2025-01-01", "2025-07-01"),
                total_cost=530_000,
                total_energy_kwh=10_000,
                ww_volume_m3=20,
                total_co2_kg=5500,
                co2_cost=30_000,
            )
        )
        co2 = result.co2
        assert co2 is not None
        assert co2.intensity_kg_per_sqm == Decimal(55)
        assert co2.landlord_share_percent == 95
        assert int(co2.landlord_amount) == 28_500
        assert int(co2.renter_amount) == 1_500
        assert sum(int(line.total) for line in result.lines) + 28_500 == 530_000


class TestPeriodLongerThanAYearIsRefused:
    """§ 5 Abs. 1 S. 4 shortens the table for periods *under* a year and says
    nothing about longer ones; for Wohnraum a longer Abrechnungszeitraum is not
    lawful anyway (§ 556 Abs. 3 S. 1 BGB). Stretching the bounds upward would
    push the building into a lower Stufe and shift cost onto the renter —
    an invented number in the direction § 7 Abs. 4 punishes. Refuse instead.
    See docs/03 § "Why a period > 12 months is refused rather than scaled"."""

    def test_fifteen_month_period_with_a_co2_split_is_rejected(self) -> None:
        with pytest.raises(HeatingInputError):
            calculate_heating_statement(
                heating_input(
                    period("2025-01-01", "2026-04-01"),  # 455 days
                    total_cost=1_030_000,
                    total_energy_kwh=20_000,
                    ww_volume_m3=40,
                    total_co2_kg=2000,
                    co2_cost=30_000,
                )
            )

    def test_the_same_period_without_a_co2_split_still_computes(self) -> None:
        """One refused legal split never blocks the Heizkosten — the § 9a rule."""
        result = calculate_heating_statement(
            HeatingInput(
                billing_period=period("2025-01-01", "2026-04-01"),
                total_cost=cents(1_000_000),
                total_energy_kwh=Decimal(20_000),
                units=units(),
                occupancies=OCCUPANCIES,
                rules=RULES,
                warm_water=WarmWaterInput(volume_m3=Decimal(40)),
            )
        )
        assert result.co2 is None
        assert sum(int(line.total) for line in result.lines) == 1_000_000
