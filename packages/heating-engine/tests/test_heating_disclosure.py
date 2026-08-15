"""The intermediates the Heizkostenabrechnung's disclosure needs — carried, not discarded.

Spec: `docs/08-statement-document.md` → **"The carried-intermediates contract
(slice 3)"**, under *"Heizkostenabrechnung — the heating table's disclosure"*.
Rechtsstand 08/2026. Written before the engine change, red on purpose.

`HeatingResult`, `HeatingLine` and `Co2Result` today carry only what the money
table prints. Everything §§ 7, 8, 9, 9a, 9b HeizkostenV and § 7 Abs. 3
CO2KostAufG require the tenant to be *shown* — the pots of the vertical split,
the per-party Bemessungen of the horizontal one, which § 9 branch ran with which
operands, and the CO₂ Berechnungsgrundlagen incl. the Einstufung band — is
computed in `engine.py`/`co2.py` as a local and dropped. A tenant cannot
re-perform a calculation from figures the result threw away.

**This file must not move a single euro.** Every amount asserted here is the
amount the engine already produces; the demo path and the rendered PDF are
byte-identical after the change. The building is the worked example of `docs/08`
(A 50 m², B 30 m², C 20 m², B vacant from 01.07.2025 → landlord party).

**Re-based 05.08.2026 — the amounts moved, and no engine behaviour did.** The
demo's CO₂ *input* was wrong on its face (2.000 kg / 300,00 € ⇒ 150 €/t and
0,1 kg CO₂/kWh); it is now 4.000 kg / 261,80 €. Because the CO₂-Vermieteranteil
is deducted before the renter-facing split, every euro below follows the input.
The rule above still holds in the form that matters: **this file changes no
engine behaviour**, and every figure here is still what the engine produces from
the fixture `docs/08` → "The worked example" states. Provenance of the new
figures: `docs/06` → "Scenario 2 — the fuel, the emissions and the CO₂ price";
statutory basis in `docs/03` → "Where `total_co2_kg` and `co2_cost` come from".

**Re-shaped 14.08.2026 — the fourth row moved off `lines`, and no euro moved.**
`berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md` § 1: the
Eigentümeranteil is not a party but one residual line per Liegenschaft, so
`("unit-b", None)` is now
`result.owner_residual` and every four-element list below is three elements plus
the residual. **The three renter rows keep the values they have today**, because
this building has exactly one landlord party and that party's amount already
*was* the residual (`docs/03` § 9.2 → "What actually moves in the engine").

The delta was bounded in advance: **seven blocks in the whole suite move, one
cent each, and none of them is in this file.** Anything here that changes value
is a bug in the wiring, not a fixture to adjust. Model: `docs/02` → "The
Eigentümeranteil is a residual line, not a party"; document rules: `docs/08` →
"Die Eigentümerzeile".
"""

from decimal import Decimal

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
    HeatingResult,
    HeatingRules,
    HeatingUnit,
    WarmWaterInput,
    calculate_heating_statement,
)

YEAR_2025 = period("2025-01-01", "2026-01-01")  # 365 days
LEAP_YEAR_2024 = period("2024-01-01", "2025-01-01")  # 366 days
FIRST_HALF_2025 = period("2025-01-01", "2025-07-01")  # 181 days

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
# unit B's Jan–Jun stays exactly 5850 of 10 000 (585,0 ‰) and the Bemessungen
# below stay hand-checkable. Zehntelpromille, Σ 10 000 (K3, `docs/03` → "Seite
# 01b … (2) K3"). The demo path reads the live VDI 2067 table from rules-store
# and therefore splits unit B 583,3/416,7 ‰ — the two are not interchangeable.
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

# Bernd leaves unit B on 30.06.2025; Jul–Dec is a landlord (Leerstand) party.
OCCUPANCIES = (
    Occupancy("unit-a", "ten-a", period("2025-01-01")),
    Occupancy("unit-b", "ten-b", period("2024-08-01", "2025-07-01")),
    Occupancy("unit-c", "ten-c", period("2023-01-01")),
)


def units(
    *,
    heat_a: Decimal | None = Decimal(600),
    heat_b: Decimal | None = Decimal(250),
    heat_c: Decimal | None = Decimal(150),
) -> tuple[HeatingUnit, ...]:
    """50 + 30 + 20 = 100 m², so kg ÷ 100 is the CO₂ intensity by inspection."""
    return (
        HeatingUnit("unit-a", 5000, heat_consumption=heat_a, ww_consumption_m3=Decimal(20)),
        HeatingUnit("unit-b", 3000, heat_consumption=heat_b, ww_consumption_m3=Decimal(12)),
        HeatingUnit("unit-c", 2000, heat_consumption=heat_c, ww_consumption_m3=Decimal(8)),
    )


MEASURED_40_M3 = WarmWaterInput(volume_m3=Decimal(40))
# The demo's CO₂ fixture, re-based 05.08.2026: 4.000 kg Brennstoffemissionen and
# 261,80 € Kohlendioxidkosten ⇒ 65,45 €/t (55,00 € je Zertifikat, § 10 Abs. 2
# BEHG 2025, + 19 % USt per § 3 Abs. 3 CO2KostAufG) and 0,200 kg CO₂/kWh against
# the demo's 20.000 kWh Erdgas. The previous 2.000 kg / 300,00 € implied 150 €/t
# and half the emission factor of any fuel — `docs/06` → "Scenario 2 — the fuel,
# the emissions and the CO₂ price", statutory figures in `docs/03`.
CO2_4000_KG = Co2Input(total_co2_kg=Decimal(4000), co2_cost=cents(26_180))


def statement(
    *,
    billing_period: Period = YEAR_2025,
    total_cost: int = 1_030_000,
    total_energy_kwh: int = 20_000,
    heating_units: tuple[HeatingUnit, ...] | None = None,
    warm_water: WarmWaterInput | None = MEASURED_40_M3,
    co2: Co2Input | None = CO2_4000_KG,
) -> HeatingResult:
    return calculate_heating_statement(
        HeatingInput(
            billing_period=billing_period,
            total_cost=cents(total_cost),
            total_energy_kwh=Decimal(total_energy_kwh),
            units=units() if heating_units is None else heating_units,
            occupancies=OCCUPANCIES,
            rules=RULES,
            warm_water=warm_water,
            co2=co2,
        )
    )


class TestNothingThatRendersToday_Moves:
    """The guard on the whole slice: carrying intermediates changes no amount.

    These are the worked example's party totals in `docs/08` and the figures
    `scripts/assert_statement_pdf.py` pins. If this class ever goes red, the
    slice has stopped being a pure carry.
    """

    def test_the_worked_examples_party_totals_are_unchanged(self) -> None:
        """The three renter rows keep their cents exactly; the landlord row is
        the same 128.110 read off `owner_residual` instead of out of `lines`."""
        result = statement()
        rows = [(line.unit_id, line.tenancy_id, int(line.total)) for line in result.lines]
        assert rows == [
            ("unit-a", "ten-a", 560_397),
            ("unit-b", "ten-b", 149_553),
            ("unit-c", "ten-c", 176_232),
        ]
        owner = result.owner_residual
        assert int(owner.total) == 128_110
        co2 = result.co2
        assert co2 is not None
        assert sum(int(line.total) for line in result.lines) + int(owner.total) == 1_014_292
        assert (
            sum(int(line.total) for line in result.lines)
            + int(owner.total)
            + int(co2.landlord_amount)
            == 1_030_000
        )
        assert int(result.total) == 1_030_000

    def test_the_residual_is_the_vacancy_share_and_block_c_is_two_cents(self) -> None:
        """`docs/08` § 5 — the printed Eigentümeranteil is the residual; block
        (a) is what the Leerstandsaufstellung itemises per empty unit, and their
        difference is block (c). Same structure as Berkay's 17.531 vs 17.536.
        """
        owner = statement().owner_residual
        assert [origin.unit_id for origin in owner.origins] == ["unit-b"]
        origins_total = sum(int(origin.total) for origin in owner.origins)
        assert int(owner.rounding_difference) == int(owner.total) - origins_total


class TestBlockAVerticalSplit:
    """§§ 7, 8, 9 HeizkostenV — how 10.300,00 € became four pots.

    `docs/08` → Block A. Every one of these is a local in
    `calculate_heating_statement` today and reaches no reader.
    """

    def test_the_pots_of_the_vertical_split_are_carried(self) -> None:
        result = statement()
        assert int(result.billable_cost) == 1_014_292  # 10.300,00 minus 157,08 CO₂
        assert int(result.ww_pot) == 253_573  # 2.535,73 €
        assert int(result.heating_pot) == 760_719  # 7.607,19 €
        assert int(result.heat_base_pot) == 228_216  # 2.282,16 €
        assert int(result.heat_cons_pot) == 532_503  # 5.325,03 €
        assert int(result.ww_base_pot) == 76_072  # 760,72 €
        assert int(result.ww_cons_pot) == 177_501  # 1.775,01 €

    def test_every_pot_reconciles_to_the_one_above_it(self) -> None:
        """The vertical analogue of `sum(shares) == input_total`: a Block A the
        tenant adds up must add up."""
        result = statement()
        co2 = result.co2
        assert co2 is not None
        assert int(result.heat_base_pot) + int(result.heat_cons_pot) == int(result.heating_pot)
        assert int(result.ww_base_pot) + int(result.ww_cons_pot) == int(result.ww_pot)
        assert int(result.heating_pot) + int(result.ww_pot) == int(result.billable_cost)
        assert int(result.billable_cost) + int(co2.landlord_amount) == int(result.total)

    def test_without_a_co2_split_the_billable_cost_is_the_total(self) -> None:
        result = statement(total_cost=1_000_000, co2=None)
        assert result.co2 is None
        assert int(result.billable_cost) == int(result.total) == 1_000_000

    def test_the_applied_ratio_and_the_legal_bounds_are_both_carried(self) -> None:
        """Item 2: *what was applied* and *what the law permits* are two facts and
        the page prints two. Both come from the result — never a template literal,
        never the input passed alongside it."""
        result = statement()
        assert result.applied_consumption_share == Decimal("0.7")
        assert result.split_bounds.min_consumption_share == Decimal("0.5")
        assert result.split_bounds.max_consumption_share == Decimal("0.7")
        assert (
            result.split_bounds.min_consumption_share
            <= result.applied_consumption_share
            <= result.split_bounds.max_consumption_share
        )


class TestParagraph9WarmWaterSeparation:
    """§ 9 HeizkostenV — which branch ran, and with which operands.

    `docs/08` item 3: the two branches print *different* text and the measured
    one must never render the word Ersatzwert. Today the result cannot say which
    one ran, so the template would have to guess.
    """

    def test_the_measured_branch_carries_the_formula_it_applied(self) -> None:
        result = statement()
        separation = result.warm_water_separation
        assert separation is not None
        assert separation.method == "MEASURED"
        assert separation.volume_m3 == Decimal(40)
        assert separation.factor_kwh_per_m3_kelvin == Decimal("2.5")
        assert separation.hot_temp_c == Decimal(60)
        assert separation.cold_temp_c == Decimal(10)
        assert separation.q_ww_kwh == Decimal(5000)
        assert separation.total_energy_kwh == Decimal(20_000)
        # The printed line is reproducible from its own operands:
        # 2,5 × 40 m³ × (60 °C minus 10 °C) = 5.000 kWh von 20.000 kWh.
        assert (
            separation.factor_kwh_per_m3_kelvin
            * separation.volume_m3
            * (separation.hot_temp_c - separation.cold_temp_c)
            == separation.q_ww_kwh
        )

    def test_the_measured_branch_carries_no_fallback_operand(self) -> None:
        """A template that renders the Ersatzwert sentence here would print
        `None`, loudly — which is the point of the Nones."""
        result = statement()
        separation = result.warm_water_separation
        assert separation is not None
        assert separation.area_fallback_kwh_per_sqm_year is None
        assert separation.heated_area_sqm is None
        assert separation.period_days is None
        assert separation.reference_year_days is None

    def test_the_area_fallback_branch_carries_its_own_operands(self) -> None:
        """§ 9 Abs. 2 Ersatzwert: 32 kWh/m²/a × 100 m² × 365 von 365 Tagen."""
        result = statement(
            total_cost=1_000_000, warm_water=WarmWaterInput(volume_m3=None), co2=None
        )
        separation = result.warm_water_separation
        assert separation is not None
        assert separation.method == "AREA_FALLBACK"
        assert separation.area_fallback_kwh_per_sqm_year == Decimal(32)
        assert separation.heated_area_sqm == Decimal(100)
        assert separation.period_days == 365
        # The engine divides by a flat 365 here (it does *not* anchor a reference
        # year the way the CO₂ factor does). The result echoes what was divided
        # by; harmonising the two is a separate, euro-moving decision — see the
        # gap "§ 9's area fallback divides by a flat 365" in docs/08.
        assert separation.reference_year_days == 365
        assert separation.q_ww_kwh == Decimal(3200)
        assert separation.total_energy_kwh == Decimal(20_000)
        assert separation.volume_m3 is None
        assert separation.factor_kwh_per_m3_kelvin is None
        assert separation.hot_temp_c is None
        assert separation.cold_temp_c is None
        # 3.200 von 20.000 kWh → 16 % of the billable cost is warm water.
        assert int(result.ww_pot) == 160_000
        assert int(result.heating_pot) == 840_000

    def test_the_fallback_area_is_the_area_the_co2_split_used(self) -> None:
        """Two fields, one building: § 7 Abs. 3 needs `Co2Result` to be
        self-contained, § 9 Abs. 2 needs the operand it pro-rated. They must
        never be two different numbers on one page."""
        result = statement(warm_water=WarmWaterInput(volume_m3=None))
        separation = result.warm_water_separation
        co2 = result.co2
        assert separation is not None
        assert co2 is not None
        assert separation.heated_area_sqm == co2.heated_area_sqm == Decimal(100)

    def test_no_central_warm_water_carries_no_separation_at_all(self) -> None:
        result = statement(total_cost=1_000_000, warm_water=None, co2=None)
        assert result.warm_water_separation is None
        assert int(result.ww_pot) == 0
        assert int(result.ww_base_pot) == 0
        assert int(result.ww_cons_pot) == 0
        assert int(result.heating_pot) == int(result.billable_cost) == 1_000_000


class TestBlockBBemessungen:
    """The horizontal half — one Bemessung per party per money column.

    `docs/08` → Block B. Invariant, per column: the parties' Bemessungen sum
    exactly to the Gesamtbemessung.
    """

    def test_base_weight_is_x100_scaled_and_the_name_says_so(self) -> None:
        """⚠️ `docs/03`: engine weights are ×100 fixed point. `18.250 m²·Tage`
        renders as `1.825.000` if the render boundary forgets to de-scale, and an
        integer comparison stays green through exactly that bug. This fixture
        pins **both** the carried scale and the de-scaled display value."""
        result = statement()
        owner = result.owner_residual
        carried = [line.base_weight_sqm_days_x100 for line in result.lines]
        assert carried == [
            Decimal(5000 * 365),  # A: 50 m² × 365 d
            Decimal(3000 * 181),  # B, Bernd: 30 m² × 181 d
            Decimal(2000 * 365),  # C: 20 m² × 365 d
        ]
        assert carried == [
            Decimal(1_825_000),
            Decimal(543_000),
            Decimal(730_000),
        ]
        # B, Leerstand → the Fiktivbelegung (D0) on the Eigentümerzeile, same
        # scale, same de-scaling rule: 30 m² × 184 d.
        assert owner.base_weight_sqm_days_x100 == Decimal(3000 * 184) == Decimal(552_000)
        # De-scaled once, at the render boundary — never per line and never twice.
        assert [w / 100 for w in carried] == [
            Decimal(18_250),
            Decimal(5_430),
            Decimal(7_300),
        ]
        assert owner.base_weight_sqm_days_x100 / 100 == Decimal(5_520)

    def test_the_base_bemessungen_sum_to_the_gesamtbemessung(self) -> None:
        """The Gesamtbemessung is unchanged at 36.500 m²·Tage — the vacancy is
        still in the denominator (D0/E19), it is just no longer a party. Summing
        `lines` alone would print a denominator 5.520 m²·Tage short of the one
        the renters' own shares were divided by."""
        result = statement()
        owner = result.owner_residual
        assert owner.base_weight_sqm_days_x100 is not None
        total = sum(
            (line.base_weight_sqm_days_x100 for line in result.lines),
            owner.base_weight_sqm_days_x100,
        )
        assert total == Decimal(3_650_000)
        assert total / 100 == Decimal(36_500)  # 36.500 m²·Tage, the printed figure

    def test_the_warm_water_bemessungen_sum_to_the_measured_total(self) -> None:
        result = statement()
        owner = result.owner_residual
        weights = [line.ww_consumption_weight_m3 for line in result.lines]
        assert None not in weights
        assert weights == [
            Decimal(20),
            Decimal(12) * Decimal(181) / Decimal(365),
            Decimal(8),
        ]
        assert owner.ww_consumption_weight_m3 == Decimal(12) * Decimal(184) / Decimal(365)
        assert owner.ww_consumption_weight_m3 is not None
        assert sum(
            (w for w in weights if w is not None), owner.ww_consumption_weight_m3
        ) == Decimal(40)

    def test_a_fractional_bemessung_displays_at_two_decimals(self) -> None:
        """`docs/08`: `5,950684931506849…` prints as `5,95`. The engine carries
        the exact value; rounding is the renderer's job and needs the exact one."""
        result = statement()
        owner = result.owner_residual
        weights = [line.ww_consumption_weight_m3 for line in result.lines]
        rounded = [None if w is None else w.quantize(Decimal("0.01")) for w in weights]
        assert rounded == [
            Decimal("20.00"),
            Decimal("5.95"),
            Decimal("8.00"),
        ]
        assert owner.ww_consumption_weight_m3 is not None
        assert owner.ww_consumption_weight_m3.quantize(Decimal("0.01")) == Decimal("6.05")

    def test_the_heat_bemessungen_sum_to_the_units_readings(self) -> None:
        result = statement()
        owner = result.owner_residual
        weights = [line.heat_consumption_weight for line in result.lines]
        assert None not in weights
        assert weights == [
            Decimal(600),
            Decimal("146.25"),  # 250 × 5850/10 000 (585,0 ‰)
            Decimal(150),
        ]
        assert owner.heat_consumption_weight == Decimal("103.75")  # 250 × 4150/10 000 (415,0 ‰)
        assert owner.heat_consumption_weight is not None
        # Σ 1.000 — the Gesamtbemessung the page may not print until the
        # measurement unit is carried (slice 5), but that the engine must carry.
        assert sum((w for w in weights if w is not None), owner.heat_consumption_weight) == Decimal(
            1000
        )

    def test_days_and_the_denominator_they_are_a_share_of(self) -> None:
        result = statement()
        assert [(line.days, line.unit_total_days) for line in result.lines] == [
            (365, 365),
            (181, 365),
            (365, 365),
        ]
        # The vacancy's Zeitanteil is still disclosed — Block C needs it (§ 9b
        # Abs. 3 is about Bemessung, not money), so it travels on the origin.
        origin = result.owner_residual.origins[0]
        assert (origin.days, origin.unit_total_days) == (184, 365)


class TestBlockCNutzerwechsel:
    """§ 9b HeizkostenV — Gradtagszahlen for the consumption, Zeitanteile for the rest.

    `docs/08` → Block C: `01.01.–30.06.2025 585 ‰ von 1.000 ‰`, and
    `12 m³ × 181 von 365 Tagen = 5,95 m³`.

    The carried figures are **Zehntelpromille** since K3 (`docs/03` → "Seite 01b
    … (2) K3"): the pair below is 5850/10 000, which the page prints as
    `585,0 ‰ von 1.000 ‰`. De-scaling by 10 happens once, at the renderer.

    **The vacancy segment still gets a Block C line (14.08.2026).** § 9b Abs. 3
    disclosure is about *Bemessung*, not about money: a unit used by a renter to
    30.06. and standing empty afterwards owes the reader both Zeitanteile, and
    the two must still sum to the unit's denominator. So the segment keeps its
    line here and loses only its **money row** — which is exactly why
    `OwnerResidualOrigin` carries the Bemessungen and not just the amounts
    (`docs/08` → "Die Eigentümerzeile" § 3 and § 6).
    """

    def test_tenth_promille_is_carried_with_its_per_unit_total(self) -> None:
        """Never a bare `585,0 ‰`: over a partial billing period a unit's parties
        sum to less than 1.000 ‰ and the bare figure would read as wrong."""
        result = statement()
        assert [
            (line.degree_day_promille, line.unit_degree_day_promille_total) for line in result.lines
        ] == [
            (Decimal(10_000), Decimal(10_000)),
            (Decimal(5850), Decimal(10_000)),
            (Decimal(10_000), Decimal(10_000)),
        ]
        origin = result.owner_residual.origins[0]
        assert (origin.degree_day_promille, origin.unit_degree_day_promille_total) == (
            Decimal(4150),
            Decimal(10_000),
        )

    def test_the_unit_total_is_the_denominator_that_was_applied(self) -> None:
        """Unit B's two Block-C segments are now one renter line plus one origin,
        and they must still add up to the unit's own denominator — otherwise the
        printed `von 1.000 ‰` is a denominator nothing on the page sums to."""
        result = statement()
        renter = next(line for line in result.lines if line.unit_id == "unit-b")
        origin = next(o for o in result.owner_residual.origins if o.unit_id == "unit-b")
        assert renter.degree_day_promille + origin.degree_day_promille == (
            renter.unit_degree_day_promille_total
        )
        assert origin.unit_degree_day_promille_total == renter.unit_degree_day_promille_total
        assert [renter.heat_consumption_weight, origin.heat_consumption_weight] == [
            Decimal(250) * Decimal(5850) / Decimal(10_000),
            Decimal(250) * Decimal(4150) / Decimal(10_000),
        ]

    def test_the_printed_derivation_is_reproducible_from_the_carried_fields(self) -> None:
        """`12 m³ × 181 von 365 Tagen = 5,95 m³` — every operand of that sentence
        comes off the line, and the unit's reading is the exact sum of its
        segments' Bemessungen (which is why it is not carried a second time)."""
        result = statement()
        renter = next(line for line in result.lines if line.unit_id == "unit-b")
        origin = next(o for o in result.owner_residual.origins if o.unit_id == "unit-b")
        shares = [renter.ww_consumption_weight_m3, origin.ww_consumption_weight_m3]
        assert None not in shares
        unit_reading = sum((s for s in shares if s is not None), Decimal(0))
        assert unit_reading == Decimal(12)
        for days, total_days, share in (
            (renter.days, renter.unit_total_days, renter.ww_consumption_weight_m3),
            (origin.days, origin.unit_total_days, origin.ww_consumption_weight_m3),
        ):
            assert share is not None
            assert share == unit_reading * Decimal(days) / Decimal(total_days)


class TestParagraph9aFallbackWithholdsAConsumptionBemessung:
    """§ 9a Abs. 2 — when a column falls back to the area key, its consumption
    Bemessung was not applied and must not be shown.

    Block B states an Umlageschlüssel **per column**, so the result has to say
    per column which key was used. `consumption_fallback_to_area` (heat *or* warm
    water) cannot express the mixed case below.
    """

    def test_heating_falls_back_while_warm_water_does_not(self) -> None:
        result = statement(
            total_cost=1_000_000,
            heating_units=units(heat_b=None, heat_c=None),  # 50 % of the area
            co2=None,
        )
        assert result.heat_fallback_to_area is True
        assert result.ww_fallback_to_area is False
        assert result.consumption_fallback_to_area is True  # unchanged meaning: heat or ww
        owner = result.owner_residual
        assert [line.heat_consumption_weight for line in result.lines] == [None] * 3
        # The withholding is `None` on the Eigentümerzeile too: no consumption
        # Bemessung was applied to that column for anybody, so none may be shown
        # for anybody (`docs/08` rule 4 — `None` means *not applied*).
        assert owner.heat_consumption_weight is None
        ww = [line.ww_consumption_weight_m3 for line in result.lines]
        assert None not in ww
        assert owner.ww_consumption_weight_m3 is not None
        assert sum((w for w in ww if w is not None), owner.ww_consumption_weight_m3) == Decimal(40)
        # The Fläche·Tage Bemessung is still carried — it is what was applied to
        # *both* heating columns in this case.
        assert owner.base_weight_sqm_days_x100 is not None
        assert sum(
            (line.base_weight_sqm_days_x100 for line in result.lines),
            owner.base_weight_sqm_days_x100,
        ) == Decimal(3_650_000)
        assert sum(int(line.total) for line in result.lines) + int(owner.total) == 1_000_000

    def test_no_central_warm_water_is_not_a_fallback(self) -> None:
        """No warm-water column exists at all — that is not § 9a Abs. 2, and the
        page must not claim a fallback happened."""
        result = statement(total_cost=1_000_000, warm_water=None, co2=None)
        assert result.ww_fallback_to_area is False
        assert result.heat_fallback_to_area is False
        assert [line.ww_consumption_weight_m3 for line in result.lines] == [None] * 3
        assert result.owner_residual.ww_consumption_weight_m3 is None


class TestCo2Berechnungsgrundlagen:
    """§ 7 Abs. 3 CO2KostAufG — the Einstufung *and* the grounds it was computed on.

    `docs/08` item 5: `CO₂-Emissionen des Gebäudes 4.000 kg · beheizte Fläche
    100 m² → 40 kg CO₂/m²/Jahr · Einstufung: 37 bis unter 42 · CO₂-Kosten
    261,80 €`. Three of those four inputs reach `Co2Result` nowhere today.
    """

    def test_the_inputs_of_the_einstufung_are_carried(self) -> None:
        result = statement()
        co2 = result.co2
        assert co2 is not None
        assert co2.total_co2_kg == Decimal(4000)
        assert co2.heated_area_sqm == Decimal(100)
        assert int(co2.co2_cost) == 26_180
        # The disclosed intensity is reproducible from the two disclosed operands.
        assert co2.intensity_kg_per_sqm == co2.total_co2_kg / co2.heated_area_sqm
        # …and the split of the disclosed cost adds up for the reader.
        assert int(co2.landlord_amount) + int(co2.renter_amount) == int(co2.co2_cost)

    def test_the_einstufung_is_a_band_not_a_step_number(self) -> None:
        """`Co2Step` carries no ordinal, so a step number would be invented. The
        band is the pair of bounds the intensity was actually compared against."""
        result = statement()
        co2 = result.co2
        assert co2 is not None
        assert co2.landlord_share_percent == 60
        lower, upper = co2.band_min_inclusive, co2.band_max_exclusive
        assert lower is not None and upper is not None
        assert lower == Decimal(37)
        assert upper == Decimal(42)
        assert lower <= co2.intensity_kg_per_sqm < upper

    def test_the_first_step_has_no_lower_bound(self) -> None:
        """`unter 12 kg CO₂/m²/Jahr` — the Anlage's first step has no lower bound
        and the engine must not invent a 0."""
        result = statement(co2=Co2Input(total_co2_kg=Decimal(1000), co2_cost=cents(30_000)))
        co2 = result.co2
        assert co2 is not None
        assert co2.intensity_kg_per_sqm == Decimal(10)
        assert co2.landlord_share_percent == 0
        assert co2.band_min_inclusive is None
        assert co2.band_max_exclusive == Decimal(12)

    def test_the_open_ended_top_step_has_no_upper_bound(self) -> None:
        result = statement(co2=Co2Input(total_co2_kg=Decimal(5500), co2_cost=cents(30_000)))
        co2 = result.co2
        assert co2 is not None
        assert co2.intensity_kg_per_sqm == Decimal(55)
        assert co2.landlord_share_percent == 95
        assert co2.band_min_inclusive == Decimal(52)
        assert co2.band_max_exclusive is None

    def test_the_full_year_days_are_carried_alongside_the_factor(self) -> None:
        """`annualisation_factor` alone cannot be un-divided back into
        `181 von 365`, so both day counts stay on the result."""
        result = statement()
        co2 = result.co2
        assert co2 is not None
        assert co2.period_days == 365
        assert co2.reference_year_days == 365
        assert co2.annualisation_factor == Decimal(1)

    def test_a_leap_year_is_366_days_and_is_not_annualised(self) -> None:
        """H2 triggers on `nTage ∉ {365, 366}`, so a leap year is left alone and
        the band stays the Anlage's own. `reference_year_days` is the flat 365
        H2 divides by (`docs/03` §(3) "Divisor", open item § 7 no. 8) — the
        field echoes what was divided by, not the length of this year; the
        anchored reference year now only decides whether a period exceeds twelve
        months. Before H2 this assertion read 366 of 366."""
        result = statement(billing_period=LEAP_YEAR_2024)
        co2 = result.co2
        assert co2 is not None
        assert co2.period_days == 366
        assert co2.reference_year_days == 365
        assert co2.annualisation_factor == Decimal(1)
        assert co2.intensity_kg_per_sqm == Decimal(40)
        assert co2.band_min_inclusive == Decimal(37)
        assert co2.band_max_exclusive == Decimal(42)


class TestCo2BandOverAShortPeriod:
    """H2 — the intensity is annualised and the band disclosed is the **unshortened** one.

    Replaces the § 5 Abs. 1 S. 4 reading this class used to pin (every finite
    bound × 181/365, intensity left as the period figure, page printing
    `Einstufung: 18,3 bis unter 20,8 … anteilig gekürzt`). Superseded
    12.08.2026 — `docs/03-nk-heating-engines.md` → "Seite 01b … (3) CO₂ short
    billing period"; the old section is kept and marked there so nobody
    re-derives it.

    01.01.–01.07.2025 = 181 days; 1.950 kg over 100 m² = 19,5 kg/m² **over the
    period**, annualised 19,5 × 365/181 = 39,32… kg/m²/a → Stufe 37 – < 42,
    Vermieter 60 %. Same step as the shortened-table reading, same cents; what
    moved is the pair the page prints, and § 7 Abs. 3 CO2KostAufG is about
    exactly that pair. The renderer must still not derive either figure itself —
    a second implementation of a legal rule in the template layer is how the two
    drift apart.
    """

    def _result(self) -> HeatingResult:
        return statement(
            billing_period=FIRST_HALF_2025,
            total_cost=530_000,
            total_energy_kwh=10_000,
            warm_water=WarmWaterInput(volume_m3=Decimal(20)),
            co2=Co2Input(total_co2_kg=Decimal(1950), co2_cost=cents(30_000)),
        )

    def test_the_carried_band_is_the_anlages_own(self) -> None:
        co2 = self._result().co2
        assert co2 is not None
        assert co2.landlord_share_percent == 60
        # The disclosed intensity is the annualised one — the header over it
        # reads kg CO₂/m²/**Jahr**, and now the figure under it does too.
        assert co2.intensity_kg_per_sqm == Decimal("19.5") * Decimal(365) / Decimal(181)
        assert co2.intensity_kg_per_sqm.quantize(Decimal("0.01")) == Decimal("39.32")
        lower, upper = co2.band_min_inclusive, co2.band_max_exclusive
        assert lower is not None and upper is not None
        # Unscaled: the pair a tenant can look up in the published Anlage.
        assert lower == Decimal(37)
        assert upper == Decimal(42)
        assert lower <= co2.intensity_kg_per_sqm < upper

    def test_both_readings_select_the_same_step(self) -> None:
        """The equivalence that makes the change safe, asserted rather than
        believed: `i × 365/d < b` ⇔ `i < b × d/365`. The superseded reading
        compared the **period** figure 19,5 against bounds shortened to
        18,348…/20,827…; H2 compares 39,32… against 37/42. Same Stufe, same
        60 %, same cents — only the printed pair moves (`docs/03` §(3))."""
        co2 = self._result().co2
        assert co2 is not None
        period_figure = Decimal("19.5")
        shortened_lower = Decimal(37) * Decimal(181) / Decimal(365)
        shortened_upper = Decimal(42) * Decimal(181) / Decimal(365)
        assert shortened_lower.quantize(Decimal("0.001")) == Decimal("18.348")
        assert shortened_upper.quantize(Decimal("0.001")) == Decimal("20.827")
        assert shortened_lower <= period_figure < shortened_upper
        assert co2.landlord_share_percent == 60
        assert int(co2.landlord_amount) == 18_000  # 60 % of 300,00 €
        assert int(co2.renter_amount) == 12_000

    def test_the_days_behind_the_factor_are_carried(self) -> None:
        """`(181 von 365 Tagen)` is required copy; it is not recoverable from
        2,0165745856353591160220994475."""
        co2 = self._result().co2
        assert co2 is not None
        assert co2.period_days == 181
        assert co2.reference_year_days == 365
        assert co2.annualisation_factor == Decimal(365) / Decimal(181)
