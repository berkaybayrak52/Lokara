"""H2 — a billing period under a year annualises the **intensity**, end to end.

Spec: `docs/03-nk-heating-engines.md` → **"Seite 01b … (3) CO₂ short billing
period"**. Rechtsstand 01/2023 for the Anlage, 07/2026 for H2.

    if nTage not in (365, 366):
        spezifisch_kg_pro_m2_a = (co2Gramm / 1e6) / gesamtflaecheM2 × 365 / nTage
    step = lookup10(spezifisch_kg_pro_m2_a)      # against the UNSHORTENED table

**This file was `test_co2_period_factor.py` and pinned the opposite mechanic** —
§ 5 Abs. 1 S. 4 read as *"shorten every finite bound by days/reference-year and
leave the intensity as the period figure"*. That reading is **SUPERSEDED**
(12.08.2026); the section that argues it is kept and marked in `docs/03` rather
than deleted, so nobody re-derives it and "fixes" `co2.py` back. The module was
renamed because `period_factor` no longer exists: the factor is now
`annualisation_factor`, it is **≥ 1**, and it multiplies the intensity instead
of the bounds.

**Why the change is safe, and why that claim is asserted here rather than
believed:** `i × 365/d < b` ⇔ `i < b × d/365`, so both readings select the
**same step**. No Einstufung moves, no cent moves. What moves is the pair the
statement prints — and § 7 Abs. 3 CO2KostAufG is about exactly that pair. The
old reading printed a 181-day figure under a `kg CO₂/m²/a` header against a band
(18,35 – 20,83) that appears in no statute annex; H2 prints an annualised figure
against the Anlage's own 37 – 42.

Companion: `test_berkay_01b_co2_stufen.py` pins H2 on the `split_co2_cost`
primitive with Berkay's own figures. This file keeps the assertion at the
`calculate_heating_statement` boundary, where the CO₂ deduction has to reach the
renters' side of the statement.
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
# Synthetic, **not** the rules-store table (the superseded 01/1981 shape ×10).
# Zehntelpromille, Σ 10 000 — K3, `docs/03` → "Seite 01b … (2) K3". Nothing here
# depends on the weights: every occupancy below runs the whole period, so no
# degree-day apportionment happens and the table only has to exist and be valid.
DEGREE_DAYS = DegreeDayTable(
    tenth_promille_by_month=(1700, 1500, 1300, 800, 400, 150, 100, 100, 300, 800, 1200, 1650)
)
# Anlage CO2KostAufG, bounds in kg CO₂/m²/**a** — the per-year unit is what makes
# annualising the intensity necessary at all.
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

FIRST_HALF_2025 = period("2025-01-01", "2025-07-01")  # 181 days
ANNUALISATION_181 = Decimal(365) / Decimal(181)


def annualised(period_intensity: Decimal) -> Decimal:
    """`i × 365 / 181`, in that order — **not** `i × ANNUALISATION_181`.

    R2 (`docs/03` § 5): a quotient is recomputed, never reused once rounded.
    The engine multiplies by 365 and then divides by the days, so at 28
    significant digits it lands on a different last digit than a pre-divided
    factor would. Asserting against the pre-divided form would quietly demand
    the engine cache the factor, which R2 forbids.
    """
    return period_intensity * Decimal(365) / Decimal(181)


def units() -> tuple[HeatingUnit, ...]:
    """50 + 30 + 20 = 100 m², so kg ÷ 100 is the period intensity by inspection."""
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


class TestInterimPeriodAnnualisesTheIntensity:
    """The defect this file exists for, restated under H2.

    Abrechnungszeitraum 01.01.2025–01.07.2025 = **181 days** → the annualisation
    factor is 365/181 = 2,0165…

    1.950 kg CO₂ over 100 m² = **19,5 kg CO₂/m² over the period**, annualised
    **39,32 kg CO₂/m²/a**.

    * Naively, comparing the period figure against the per-year table:
      17 ≤ 19,5 < 22 → Vermieter **20 %**. That is the defect.
    * Under H2: 37 ≤ 39,32 < 42 → Vermieter **60 %**.

    39,32 sits 2,3 inside a 5-wide band, so this pins a Stufe change and not a
    rounding accident.
    """

    def test_landlord_share_uses_the_annualised_intensity(self) -> None:
        result = calculate_heating_statement(
            heating_input(
                FIRST_HALF_2025,
                total_cost=530_000,
                total_energy_kwh=10_000,
                ww_volume_m3=20,
                total_co2_kg=1950,
                co2_cost=30_000,
            )
        )
        co2 = result.co2
        assert co2 is not None
        # H2 annualises the emissions figure; it does not shorten the table. The
        # disclosed value is therefore per year, as its column header claims.
        assert co2.intensity_kg_per_sqm == annualised(Decimal(1950) / Decimal(100))
        assert co2.intensity_kg_per_sqm.quantize(Decimal("0.01")) == Decimal("39.32")
        assert co2.annualisation_factor == ANNUALISATION_181
        assert co2.landlord_share_percent == 60  # not 20 — that is the defect
        assert int(co2.landlord_amount) == 18_000  # 180,00 € of 300,00 €
        assert int(co2.renter_amount) == 12_000  # 120,00 €, not 240,00 €
        assert co2.rechtsstand == "Rechtsstand 01/2023"

    def test_the_band_disclosed_is_the_anlages_own_unshortened_pair(self) -> None:
        """`docs/03` §(3): the printed band must be one a tenant can look up in
        the published Anlage. The superseded reading printed 18,35 – 20,83."""
        result = calculate_heating_statement(
            heating_input(
                FIRST_HALF_2025,
                total_cost=530_000,
                total_energy_kwh=10_000,
                ww_volume_m3=20,
                total_co2_kg=1950,
                co2_cost=30_000,
            )
        )
        co2 = result.co2
        assert co2 is not None
        assert co2.band_min_inclusive == Decimal(37)
        assert co2.band_max_exclusive == Decimal(42)
        assert co2.band_min_inclusive <= co2.intensity_kg_per_sqm < co2.band_max_exclusive
        # The days behind the factor, which `(181 von 365 Tagen)` needs and
        # 2,0165745856… cannot be un-divided into.
        assert co2.period_days == 181
        assert co2.reference_year_days == 365

    def test_both_readings_select_the_same_step(self) -> None:
        """Why replacing the shortened-table reading moved no money — asserted,
        not assumed. `i × 365/d < b` ⇔ `i < b × d/365`, so the superseded
        mechanic (period figure 19,5 against bounds 18,348…/20,827…) and H2
        (39,32… against 37/42) reach the same 60 %. This equivalence is the whole
        safety argument of `docs/03` §(3) and stays asserted."""
        result = calculate_heating_statement(
            heating_input(
                FIRST_HALF_2025,
                total_cost=530_000,
                total_energy_kwh=10_000,
                ww_volume_m3=20,
                total_co2_kg=1950,
                co2_cost=30_000,
            )
        )
        co2 = result.co2
        assert co2 is not None
        period_figure = Decimal(1950) / Decimal(100)
        shortened_lower = Decimal(37) * Decimal(181) / Decimal(365)
        shortened_upper = Decimal(42) * Decimal(181) / Decimal(365)
        assert shortened_lower.quantize(Decimal("0.001")) == Decimal("18.348")
        assert shortened_upper.quantize(Decimal("0.001")) == Decimal("20.827")
        assert shortened_lower <= period_figure < shortened_upper  # old reading → 60 %
        assert co2.landlord_share_percent == 60  # new reading → the same 60 %

    def test_the_renters_side_and_the_total_still_reconcile(self) -> None:
        result = calculate_heating_statement(
            heating_input(
                FIRST_HALF_2025,
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
        # Under-classified (20 %) it would be 524.000 — 120,00 € too much on the
        # renters' side of a legal document.
        # Fully let, and all four blocks divide exactly (115.200 / 268.800 /
        # 38.400 / 89.600 against 50/30/20, 12/5/3 and 5/3/2) ⇒ the
        # Eigentümerzeile is 0,00 € here. It still renders (§ 1.3 Frage 1).
        owner = result.owner_residual
        assert int(owner.total) == 0
        assert sum(int(line.total) for line in result.lines) + int(owner.total) == 512_000
        assert (
            sum(int(line.total) for line in result.lines)
            + int(owner.total)
            + int(co2.landlord_amount)
            == 530_000
        )
        assert int(result.total) == 530_000


class TestFullYearIsUntouched:
    """`nTage ∈ {365, 366}` → factor exactly 1 — the demo path must not move."""

    def test_full_calendar_year_is_not_annualised(self) -> None:
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
        assert co2.annualisation_factor == Decimal(1)
        assert co2.intensity_kg_per_sqm == Decimal(20)
        assert co2.landlord_share_percent == 20
        assert int(co2.landlord_amount) == 6_000
        assert int(co2.renter_amount) == 24_000
        assert int(result.total) == 1_030_000

    def test_full_leap_year_is_not_annualised_either(self) -> None:
        """366 is in H2's exemption set, so a leap year is left alone: a naive
        `365/366` would report 19,945 instead of 20 and, at a bound, a different
        Stufe. (The exemption is Berkay's rule as written — a 366-day
        *non-calendar* period is left un-annualised too, recorded as an open
        convention in `docs/03` § 7 no. 8, not decided here.)"""
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
        assert co2.annualisation_factor == Decimal(1)
        assert co2.intensity_kg_per_sqm == Decimal(20)
        assert co2.landlord_share_percent == 20
        assert int(co2.landlord_amount) == 6_000
        assert int(co2.renter_amount) == 24_000
        assert int(result.total) == 1_030_000


class TestNoOverCorrection:
    """The open-ended top step has no bound, so annualising cannot push past it."""

    def test_building_already_in_the_top_step_stays_at_95_percent(self) -> None:
        # 5.500 kg over 100 m² in 181 days = 55 kg/m² for the period, already
        # past the 52 bound before annualisation and 110,91 kg/m²/a after it.
        # 95 % either way: there is no eleventh step to over-correct into.
        result = calculate_heating_statement(
            heating_input(
                FIRST_HALF_2025,
                total_cost=530_000,
                total_energy_kwh=10_000,
                ww_volume_m3=20,
                total_co2_kg=5500,
                co2_cost=30_000,
            )
        )
        co2 = result.co2
        assert co2 is not None
        assert co2.intensity_kg_per_sqm == annualised(Decimal(5500) / Decimal(100))
        assert co2.intensity_kg_per_sqm.quantize(Decimal("0.01")) == Decimal("110.91")
        assert co2.landlord_share_percent == 95
        assert co2.band_min_inclusive == Decimal(52)
        assert co2.band_max_exclusive is None
        assert int(co2.landlord_amount) == 28_500
        assert int(co2.renter_amount) == 1_500
        # ⚠️ **One of the seven blocks that move** under the Eigentümer-Residuum
        # (`docs/03` § 9.2 → the fan-out table), and the only one in this file.
        # Billable 501.500 ⇒ `ww_base_pot` = 37.613, split by 50/30/20:
        # 18.806,5 → **18.807** (R1 half-up, up from 18.806 under
        # largest-remainder), 11.283,9 → 11.284, 7.522,6 → 7.523. Σ = 37.614,
        # so the residual is **-1**. The other three blocks divide exactly.
        # A value moving anywhere else in this file is a wiring bug.
        owner = result.owner_residual
        assert int(owner.ww_base) == -1
        assert int(owner.total) == -1
        assert owner.origins == ()  # fully let ⇒ the whole line is block (c)
        assert int(owner.rounding_difference) == -1
        assert sum(int(line.total) for line in result.lines) + int(owner.total) + 28_500 == 530_000


class TestPeriodLongerThanAYearIsRefused:
    """Still refused under H2, and not as a leftover: Berkay's E24 makes a period
    over twelve months a validation error inherited from Seite 01 (E6), so
    annualisation never sees one. Annualising downward would shrink the
    intensity, push the building into a **lower** Stufe and shift cost onto the
    renter — an invented number in the direction § 7 Abs. 4 punishes. For
    Wohnraum such a period is not lawful anyway (§ 556 Abs. 3 S. 1 BGB). See
    `docs/03` § "Why a period > 12 months is refused rather than scaled"."""

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
        assert int(result.owner_residual.total) == 0
        assert (
            sum(int(line.total) for line in result.lines) + int(result.owner_residual.total)
            == 1_000_000
        )
