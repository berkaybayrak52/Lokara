"""The Maßeinheit of a `CONSUMPTION` key — carried, not guessed.

Spec: `docs/08-statement-document.md` → **"`MeasurementUnit` travels with the
value — the plumbing decision (slice 5)"**, rules 1–3, and *"Reference totals
(Gesamtbemessung) — one per allocation key"*. Rechtsstand 08/2026. Written
before the engine change, red on purpose.

`ConsumptionValue` carried `unit_id`, `tenancy_id`, `value` and no unit of
measure, so the statement could not print `Gesamtbemessung: 40 m³` — the
denominator BGH formal minimum #3 rests on — without guessing whether the figure
was m³, kWh or dimensionless HKV-Einheiten. A guessed unit on a
Verbrauchsabrechnung is a defect that reaches a tenant, so the total was
withheld instead.

Three rules, all from `docs/08`:

1. **The unit travels on the row that carries the value.**
   `ConsumptionValue.measurement_unit` in, `NkResult.consumption_unit` out — not
   a dict handed to the renderer alongside the result, which would let the value
   and its unit arrive by two routes and disagree silently.
2. **One key, one unit.** Mixed → `NkInputError`, never a silent pick: the
   reference total is a *sum*, and a denominator that cannot lawfully be summed
   fails minimum #3 before it is printed.
3. **Absence propagates.** Any row without a unit ⇒ `None`, and no reference
   total is printed for that cost — the state before this slice, kept for a
   building that records no Maßeinheit.

`NkResult.consumption_unit` is **one** field because `NkInput.consumptions` is
one flat tuple shared by every `CONSUMPTION` cost: "one key" is literally true
today. When a second, independently metered consumption key becomes
expressible, it becomes a mapping (`docs/08`, named and not designed there).

**No cent moves.** The unit labels a weight the engine already divided by;
every case below re-asserts `sum(shares) == input_total`.
"""

from decimal import Decimal

import pytest
from lokara_domain import AllocationKey, MeasurementUnit, Occupancy, cents, period
from lokara_nk_engine import (
    ConsumptionValue,
    CostItem,
    NkInput,
    NkInputError,
    NkResult,
    UnitBasis,
    calculate_nk_statement,
)

YEAR_2025 = period("2025-01-01", "2026-01-01")

# The canonical building of `docs/03`: A 50 m², B 30 m², C 20 m²; Bernd leaves
# unit B on 30.06.2025, so Jul–Dec falls to the landlord.
UNITS = (
    UnitBasis(unit_id="unit-a", area_sqm_x100=5000),
    UnitBasis(unit_id="unit-b", area_sqm_x100=3000),
    UnitBasis(unit_id="unit-c", area_sqm_x100=2000),
)
OCCUPANCIES = (
    Occupancy("unit-a", "ten-a", period("2025-01-01")),
    Occupancy("unit-b", "ten-b", period("2024-08-01", "2025-07-01")),
    Occupancy("unit-c", "ten-c", period("2023-01-01")),
)

CUBIC_METRE = MeasurementUnit.CUBIC_METRE
KWH = MeasurementUnit.KWH

WATER_COST = CostItem(
    cost_id="cost-water",
    label="Wasser/Abwasser",
    amount=cents(90_000),
    key=AllocationKey.CONSUMPTION,
)
# Warm-water volumes of the demo building, already period-resolved upstream by
# the meter adapter: 20 + 12 + 8 = 40 m³ (`docs/08` → "The worked example").
DEMO_VALUES = (Decimal(20), Decimal(12), Decimal(8))
DEMO_TOTAL = Decimal(40)


def consumptions(
    *,
    values: tuple[Decimal, Decimal, Decimal] = DEMO_VALUES,
    measurement_units: tuple[
        MeasurementUnit | None, MeasurementUnit | None, MeasurementUnit | None
    ] = (CUBIC_METRE, CUBIC_METRE, CUBIC_METRE),
) -> tuple[ConsumptionValue, ...]:
    return tuple(
        ConsumptionValue(
            unit_id=unit_id,
            tenancy_id=tenancy_id,
            value=value,
            measurement_unit=measurement_unit,
        )
        for unit_id, tenancy_id, value, measurement_unit in zip(
            ("unit-a", "unit-b", "unit-c"),
            ("ten-a", "ten-b", "ten-c"),
            values,
            measurement_units,
            strict=True,
        )
    )


def statement(rows: tuple[ConsumptionValue, ...] | None = None) -> NkResult:
    return calculate_nk_statement(
        NkInput(
            billing_period=YEAR_2025,
            units=UNITS,
            occupancies=OCCUPANCIES,
            costs=(WATER_COST,),
            consumptions=consumptions() if rows is None else rows,
        )
    )


class TestTheUnitIsCarriedInputToResult:
    """Rule 1: `ConsumptionValue.measurement_unit` → `NkResult.consumption_unit`."""

    def test_three_agreeing_rows_resolve_to_that_unit(self) -> None:
        result = statement()

        assert result.consumption_unit is MeasurementUnit.CUBIC_METRE

    def test_a_kwh_metered_cost_resolves_to_kwh(self) -> None:
        """A `CONSUMPTION` cost is not always water — Wärmelieferung is billed
        per kWh. The unit is a property of the meter, never of the key."""
        result = statement(consumptions(measurement_units=(KWH, KWH, KWH)))

        assert result.consumption_unit is MeasurementUnit.KWH

    def test_the_reference_total_it_labels_is_the_sum_of_the_weights(self) -> None:
        """The unit labels a denominator, so the denominator has to be the one
        the engine divided by: Σ 40 m³ (`docs/08` → Reference totals)."""
        result = statement()
        weights = [line.weight for line in result.lines if line.cost_id == WATER_COST.cost_id]

        assert sum(weights, Decimal(0)) == DEMO_TOTAL

    def test_the_allocation_still_reconciles_to_the_cent(self) -> None:
        """`sum(shares) == input_total` — the invariant of every allocation test.
        Carrying a unit may not move a cent."""
        result = statement()
        shares = [int(line.amount) for line in result.lines if line.cost_id == WATER_COST.cost_id]

        assert sum(shares) == int(WATER_COST.amount)
        assert int(result.total) == int(WATER_COST.amount)


class TestOneKeyOneUnit:
    """Rule 2: mixed units on one key are an input error.

    `600 kWh + 250 m³` is not a quantity. The Gesamtbemessung is a sum, and BGH
    formal minimum #3 requires a denominator a renter can check — an unsummable
    one fails that before it reaches the page.
    """

    def test_mixing_cubic_metres_and_kwh_raises(self) -> None:
        with pytest.raises(NkInputError):
            statement(consumptions(measurement_units=(KWH, CUBIC_METRE, CUBIC_METRE)))

    def test_the_engine_never_silently_picks_the_majority(self) -> None:
        with pytest.raises(NkInputError):
            statement(consumptions(measurement_units=(CUBIC_METRE, KWH, KWH)))


class TestAbsencePropagates:
    """Rule 3: any row without a unit ⇒ `None`, and the cost prints no reference
    total — the conservative state this slice keeps rather than removes."""

    def test_one_missing_unit_makes_the_key_unit_less_even_when_the_others_agree(self) -> None:
        result = statement(consumptions(measurement_units=(CUBIC_METRE, None, CUBIC_METRE)))

        assert result.consumption_unit is None

    def test_no_unit_anywhere_is_the_state_before_this_slice(self) -> None:
        """`measurement_unit` defaults to `None`, so a caller that has not been
        taught the unit yet lands on the withholding branch rather than on a
        guessed one."""
        result = statement(consumptions(measurement_units=(None, None, None)))

        assert result.consumption_unit is None

    def test_a_statement_without_consumption_values_has_no_unit(self) -> None:
        """No `CONSUMPTION` cost at all: nothing was metered, so there is no unit
        to state — `None` means *not applied*, not *not carried*."""
        result = calculate_nk_statement(
            NkInput(
                billing_period=YEAR_2025,
                units=UNITS,
                occupancies=OCCUPANCIES,
                costs=(
                    CostItem(
                        cost_id="cost-garbage",
                        label="Müllabfuhr",
                        amount=cents(120_000),
                        key=AllocationKey.AREA,
                    ),
                ),
            )
        )

        assert result.consumption_unit is None
        assert int(result.total) == 120_000
