"""The Maßeinheit of the heating-consumption Bemessung — carried, not guessed.

Spec: `docs/08-statement-document.md` → **"`MeasurementUnit` travels with the
value — the plumbing decision (slice 5)"**, rules 1–4 and the demo values of
rule 7. Rechtsstand 08/2026. Written before the engine change, red on purpose.

The defect this closes is a value that travelled from the meter to the statement
**without its unit**, so the document could print the denominator only by
guessing what `1.000` meant — and withheld it instead. `MeterKind.HEAT` covers
both a building Wärmemengenzähler counting **kWh** and flat Heizkostenverteiler
counting dimensionless **HKV-Einheiten** (`packages/domain/.../meter.py`), so the
unit is genuinely not derivable from the kind.

Four rules, all from `docs/08`:

1. **The unit travels on the dataclass that carries the value.**
   `HeatingUnit.heat_consumption_unit` in, `HeatingResult.heat_consumption_unit`
   out. A side channel — a dict handed to the renderer beside the result —
   reintroduces the same failure mode one layer up, because two routes can
   disagree and the disagreement is silent.
2. **One key, one unit.** Mixed → `HeatingInputError`, never a silent pick: the
   Gesamtbemessung is a *sum*, `600 kWh + 250 HKV-Einheiten` means nothing, and
   BGH formal minimum #3 needs a denominator that can be checked.
3. **Absence propagates.** Any contributing value without a unit ⇒ `None`, and
   the renderer keeps printing `ohne Maßeinheit — nicht ausgewiesen`. Slice 5
   removes the cause, not the branch.
4. **`None` means "not applied", never "not carried".** Under § 9a Abs. 2 the
   consumption key was *replaced*, so there is no consumption Bemessung and no
   unit for one — exactly as `heat_consumption_weight` is already `None` there.

**No euro moves.** The unit is metadata about a weight the engine already
allocated by; `TestNoEuroMoves` is the guard on that.

**Re-shaped 14.08.2026 — and still no euro moves.** The Eigentümeranteil is one
residual line per Liegenschaft rather than a party (`docs/02` § 5 and `docs/03`
§ 9.2), so this building's Leerstand row moved
from `lines` to `result.owner_residual` carrying the same 128.110 — one landlord
party, whose amount already *was* the residual. Its 103,75 HKV-Einheiten are
still inside the denominator the unit labels; they are just no longer a party's
Bemessung. None of the seven blocks the rule moves is in this file
(`docs/03` § 9.2 → the fan-out table).
"""

from decimal import Decimal

import pytest
from lokara_domain import (
    Co2Step,
    Co2Table,
    DegreeDayTable,
    HeatingSplitBounds,
    MeasurementUnit,
    Occupancy,
    WarmWaterFormula,
    cents,
    period,
)
from lokara_heating_engine import (
    Co2Input,
    HeatingInput,
    HeatingInputError,
    HeatingResult,
    HeatingRules,
    HeatingUnit,
    WarmWaterInput,
    calculate_heating_statement,
)

YEAR_2025 = period("2025-01-01", "2026-01-01")  # 365 days

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
# Zehntelpromille, Σ 10 000 — K3, `docs/03` → "Seite 01b … (2) K3". Nothing in
# this file depends on the weights; it exists so the engine has a table at all.
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

# The worked example of `docs/08`: A 50 m², B 30 m², C 20 m²; Bernd leaves B on
# 30.06.2025, so Jul–Dec is a landlord party and unit B's single reading is
# split by Gradtagszahlen (585/415 ‰).
OCCUPANCIES = (
    Occupancy("unit-a", "ten-a", period("2025-01-01")),
    Occupancy("unit-b", "ten-b", period("2024-08-01", "2025-07-01")),
    Occupancy("unit-c", "ten-c", period("2023-01-01")),
)
MEASURED_40_M3 = WarmWaterInput(volume_m3=Decimal(40))
CO2_4000_KG = Co2Input(total_co2_kg=Decimal(4000), co2_cost=cents(26_180))

# `docs/08` rule 7, verified against `packages/adapters/.../meter.py` `_SPEC`:
# met_heat_a 1200 → 1800, met_heat_b 3400 → 3650, met_heat_c 880 → 1030, all
# three `HKV_UNITS`. Σ 1.000 — which could not have been kWh in any case, since
# the building's own meter reads 20.000 kWh over the same period.
HKV = MeasurementUnit.HKV_UNITS
KWH = MeasurementUnit.KWH
DEMO_HEAT_VALUES = (Decimal(600), Decimal(250), Decimal(150))
DEMO_HEAT_TOTAL = Decimal(1000)


def units(
    *,
    heat: tuple[Decimal | None, Decimal | None, Decimal | None] = DEMO_HEAT_VALUES,
    heat_units: tuple[MeasurementUnit | None, MeasurementUnit | None, MeasurementUnit | None] = (
        HKV,
        HKV,
        HKV,
    ),
) -> tuple[HeatingUnit, ...]:
    """50 + 30 + 20 = 100 m². The value and its unit are supplied per unit,
    because that is where the defect was: the two must not be separable."""
    areas = (5000, 3000, 2000)
    ww = (Decimal(20), Decimal(12), Decimal(8))
    return tuple(
        HeatingUnit(
            unit_id=unit_id,
            area_sqm_x100=area,
            heat_consumption=value,
            ww_consumption_m3=ww_value,
            heat_consumption_unit=measurement_unit,
        )
        for unit_id, area, value, ww_value, measurement_unit in zip(
            ("unit-a", "unit-b", "unit-c"), areas, heat, ww, heat_units, strict=True
        )
    )


def statement(
    *,
    heating_units: tuple[HeatingUnit, ...] | None = None,
    warm_water: WarmWaterInput | None = MEASURED_40_M3,
    co2: Co2Input | None = CO2_4000_KG,
) -> HeatingResult:
    return calculate_heating_statement(
        HeatingInput(
            billing_period=YEAR_2025,
            total_cost=cents(1_030_000),
            total_energy_kwh=Decimal(20_000),
            units=units() if heating_units is None else heating_units,
            occupancies=OCCUPANCIES,
            rules=RULES,
            warm_water=warm_water,
            co2=co2,
        )
    )


class TestTheUnitIsCarriedInputToResult:
    """Rule 1: the unit travels with the value, and the result surfaces it so the
    renderer reads it rather than being told it by a second party."""

    def test_three_agreeing_units_resolve_to_that_unit(self) -> None:
        result = statement()

        assert result.heat_consumption_unit is MeasurementUnit.HKV_UNITS

    def test_a_kwh_building_resolves_to_kwh(self) -> None:
        """The other lawful configuration: heat metered at Wärmemengenzähler in
        each flat. Same key, different unit — which is exactly why the unit
        cannot be inferred from `MeterKind.HEAT`."""
        result = statement(heating_units=units(heat_units=(KWH, KWH, KWH)))

        assert result.heat_consumption_unit is MeasurementUnit.KWH

    def test_the_bemessungen_it_labels_still_sum_to_the_denominator(self) -> None:
        """The unit is the label on a denominator, so the denominator has to be
        the one the engine divided by: Σ 1.000 HKV-Einheiten (`docs/08` rule 7),
        and the Nutzerwechsel split inside it."""
        result = statement()
        owner = result.owner_residual
        weights = [line.heat_consumption_weight for line in result.lines]
        assert all(w is not None for w in weights)

        assert [w for w in weights if w is not None] == [
            Decimal(600),
            Decimal("146.25"),
            Decimal(150),
        ]
        # The Leerstand's 103,75 HKV-Einheiten are the Fiktivbelegung on the
        # Eigentümerzeile — still inside the denominator the label belongs to,
        # just no longer a party (`docs/02`, D0).
        assert owner.heat_consumption_weight == Decimal("103.75")
        assert owner.heat_consumption_weight is not None
        assert (
            sum((w for w in weights if w is not None), owner.heat_consumption_weight)
            == DEMO_HEAT_TOTAL
        )


class TestOneKeyOneUnit:
    """Rule 2: mixed units are an input error, not a display problem.

    The Gesamtbemessung is a **sum**, and kWh + HKV-Einheiten is a number that
    means nothing. BGH formal minimum #3 requires the denominator to be
    checkable; an unsummable denominator fails it before it is ever printed.
    """

    def test_mixing_kwh_and_hkv_units_raises(self) -> None:
        with pytest.raises(HeatingInputError):
            statement(heating_units=units(heat_units=(KWH, HKV, HKV)))

    def test_the_engine_never_silently_picks_the_majority(self) -> None:
        """Two against one is still two different units. A majority vote would
        label one flat's Bemessung with another flat's device."""
        with pytest.raises(HeatingInputError):
            statement(heating_units=units(heat_units=(HKV, KWH, KWH)))

    def test_a_declared_unit_conflicts_even_without_a_reading(self) -> None:
        """A unit with no reading still declares its device. § 9a estimates its
        value from the measured flats — in *their* unit — so a conflicting
        declaration would put the wrong unit on that party's Bemessung. Unit C is
        20 % of the area, so this is an estimate, not the § 9a Abs. 2 fallback."""
        with pytest.raises(HeatingInputError):
            statement(
                heating_units=units(
                    heat=(Decimal(600), Decimal(250), None), heat_units=(HKV, HKV, KWH)
                )
            )

    def test_the_conflict_is_rejected_before_the_branches_run(self) -> None:
        """Validation that depends on which branch ran can be skipped by an
        unrelated data problem: here B + C (50 % of the area) have no reading, so
        § 9a Abs. 2 replaces the key — and the mixed declaration is still an
        error rather than an irrelevance."""
        with pytest.raises(HeatingInputError):
            statement(
                heating_units=units(heat=(Decimal(600), None, None), heat_units=(KWH, HKV, HKV))
            )


class TestAbsencePropagates:
    """Rule 3: any contributing value without a unit ⇒ `None`, so the renderer
    keeps printing `ohne Maßeinheit — nicht ausgewiesen`.

    This is the branch slice 5 deliberately **kept**: a building that genuinely
    records no Maßeinheit still owes the renter the honest disclosure, and the
    withheld cell is a sentence rather than a blank.
    """

    def test_one_missing_unit_makes_the_key_unit_less_even_when_the_others_agree(self) -> None:
        result = statement(heating_units=units(heat_units=(HKV, None, HKV)))

        assert result.heat_consumption_unit is None

    def test_no_unit_anywhere_is_the_state_before_this_slice(self) -> None:
        """`HeatingUnit.heat_consumption_unit` defaults to `None`, so every caller
        that has not been taught the unit yet lands on the withholding branch —
        which is why the default is acceptable here at all (`docs/08` rule 1)."""
        result = statement(heating_units=units(heat_units=(None, None, None)))

        assert result.heat_consumption_unit is None

    def test_an_unread_unit_with_a_known_unit_does_not_make_the_key_unit_less(self) -> None:
        """§ 9a estimation, not § 9a Abs. 2 fallback: unit C (20 % of the area)
        has no reading and its value is estimated from the measured flats. The
        estimate is in their unit by construction, and every value that *was*
        supplied carries the unit — so the key keeps it."""
        result = statement(
            heating_units=units(heat=(Decimal(600), Decimal(250), None), heat_units=(HKV, HKV, HKV))
        )

        assert result.estimated_unit_ids == ("unit-c",)
        assert result.heat_fallback_to_area is False
        assert result.heat_consumption_unit is MeasurementUnit.HKV_UNITS

    def test_an_unread_unit_that_declares_nothing_still_keeps_the_measured_unit(self) -> None:
        """The other half of the same rule: a flat with no reading supplies no
        value, so it cannot make the key unit-less. Its estimate is derived from
        the measured flats and is in their unit."""
        result = statement(
            heating_units=units(
                heat=(Decimal(600), Decimal(250), None), heat_units=(HKV, HKV, None)
            )
        )

        assert result.estimated_unit_ids == ("unit-c",)
        assert result.heat_consumption_unit is MeasurementUnit.HKV_UNITS


class TestTheAreaFallbackHasNoConsumptionUnit:
    """Rule 4: under § 9a Abs. 2 the consumption key was **replaced**, so no
    consumption Bemessung was applied and there is no unit for one.

    `None` here means *not applied*, exactly as `heat_consumption_weight` is
    already `None` in this branch — not *not carried*. The two `None`s never
    collide on the page, because the renderer branches on `heat_fallback_to_area`
    first and that row then states `Wohnfläche (m²·Tage) — § 9a Abs. 2
    HeizkostenV` with the m²·Tage denominator printed two rows above.
    """

    def test_the_unit_is_none_even_though_every_device_declared_one(self) -> None:
        # B + C = 50 % of the area without a reading → strictly more than 25 %.
        result = statement(
            heating_units=units(heat=(Decimal(600), None, None), heat_units=(HKV, HKV, HKV))
        )

        assert result.heat_fallback_to_area is True
        assert all(line.heat_consumption_weight is None for line in result.lines)
        # The withholding reaches the Eigentümerzeile too: no consumption
        # Bemessung was applied to that column for anybody (`docs/08` rule 4).
        assert result.owner_residual.heat_consumption_weight is None
        assert result.heat_consumption_unit is None


class TestNoEuroMoves:
    """The guard on the whole slice: the unit is metadata about a weight the
    engine already allocated by. If this class goes red, slice 5 stopped being a
    pure carry (`docs/08` → "It moves no euro")."""

    def test_the_worked_examples_party_totals_are_unchanged(self) -> None:
        result = statement()

        assert [int(line.total) for line in result.lines] == [
            560_397,
            149_553,
            176_232,
        ]
        assert int(result.owner_residual.total) == 128_110

    def test_the_statement_still_reconciles_to_the_invoice(self) -> None:
        """`Σ Mieteranteile + Eigentümeranteil == input_total`, the invariant of
        every allocation test — the CO₂-Vermieteranteil is deducted before the
        renter-facing split, so it is part of the sum too."""
        result = statement()
        co2 = result.co2
        assert co2 is not None

        assert (
            sum(int(line.total) for line in result.lines)
            + int(result.owner_residual.total)
            + int(co2.landlord_amount)
            == 1_030_000
        )
        assert int(result.total) == 1_030_000

    def test_the_unit_does_not_change_a_single_amount(self) -> None:
        """The same building, once with the unit recorded and once without: the
        two results differ in exactly one field."""
        with_unit = statement()
        without_unit = statement(heating_units=units(heat_units=(None, None, None)))

        assert [int(line.total) for line in with_unit.lines] == [
            int(line.total) for line in without_unit.lines
        ]
        assert int(with_unit.owner_residual.total) == int(without_unit.owner_residual.total)
        assert int(with_unit.heat_cons_pot) == int(without_unit.heat_cons_pot)
        assert with_unit.heat_consumption_unit is not without_unit.heat_consumption_unit
