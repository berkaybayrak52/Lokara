"""Page 01 edge cases the NK engine does not handle yet — written red, on purpose.

Spec: `docs/08-statement-document.md` "Page 01 output contract" and Appendix A
(`08-F11` … `08-F20`); `docs/02-data-model.md` § 5 "Owner residual and Page 01
statement model". Every expected figure below is transcribed from
`packages/domain/tests/berkay_01_golden.py`, the approved Page 01 oracle, and
the golden field it comes from is named beside it. Rechtsstand 08/2026.

Four rules, all of them written down long before the engine met them:

* **G2 / `08-F12`** — "A zero consumption denominator gives renters `0` and
  leaves the cost with the owner; it never silently changes to an area key."
  The engine currently refuses the whole cost with `NkInputError`, which turns a
  building that recorded no consumption into a failed statement instead of an
  owner-side line.
* **G1 / `08-F15`** — "More than 12 months hard-blocks before an engine run or
  render." The engine currently only rejects an *unbounded* period, so a
  455-day window allocates happily. Its two companions, `08-F14`'s 275-day
  Rumpfperiode and `08-F20`'s leap year, are the same rule's green half and must
  keep working while the block is added.
* **G3 / `08-F13`** — overlapping tenancies block, and the block states the
  over-allocated Bemessung. `OccupancyOverlapError` currently carries one unit
  and one date in a message, so the statement can say *that* there is an overlap
  but never *how much* was allocated twice.
* **G6 / `08-F11`** — "Credits stay separate negative lines". A negative cost
  currently cannot be allocated at all: `distribute_cents` floors with
  `int(q // 1)`, `Decimal` truncates toward zero rather than flooring toward
  -inf, and on a negative total the function trips its own reconciliation
  assert. Only the structural half of `08-F11` is asserted here — its cent
  figures are per-party half-up and stay deferred to Slice C; see the class
  docstring for why `10.061` and `!= 10.060` are both wrong to assert now.

The scale convention matters when reading the weight assertions: an `AREA`
weight is `area_sqm_x100 × days`, so the printed m²·Tage of `docs/08`
("Reference totals (Gesamtbemessung)") is that number ÷ 100. The tests assert
the engine's scaled weight and name the de-scaled figure the golden records.
"""

from decimal import Decimal
from typing import Final

import pytest
from lokara_domain import (
    AllocationKey,
    MeasurementUnit,
    Occupancy,
    OccupancyOverlapError,
    cents,
    days_between,
    period,
)
from lokara_nk_engine import (
    ConsumptionValue,
    CostItem,
    NkInput,
    NkInputError,
    NkResult,
    PersonCountPeriod,
    ShareLine,
    UnitBasis,
    calculate_nk_statement,
)

# Page 01's object: 194 m² over three units. `08-F14` and `08-F20` both state
# 194 m² of area-days (53.350 = 194 × 275; 71.004 = 194 × 366), `08-F16` and
# `08-F23` both state the 74 m² unit, and `08-F14`/`08-F20` the 58 m² one; the
# remaining 62 m² is what 194 - 58 - 74 leaves.
UNIT_A_SQM: Final = 58
UNIT_B_SQM: Final = 74
UNIT_C_SQM: Final = 62

PAGE_01_UNITS: Final = (
    UnitBasis(unit_id="unit-a", area_sqm_x100=UNIT_A_SQM * 100),
    UnitBasis(unit_id="unit-b", area_sqm_x100=UNIT_B_SQM * 100),
    UnitBasis(unit_id="unit-c", area_sqm_x100=UNIT_C_SQM * 100),
)

# `08-F14` "cost": the Grundsteuer of the same object, also `08-F23`'s
# `property_tax`. It is the only money figure `08-F14` allocates.
GRUNDSTEUER_CENTS: Final = 98_000


def lines_of(result: NkResult, cost_id: str) -> tuple[ShareLine, ...]:
    return tuple(line for line in result.lines if line.cost_id == cost_id)


def renter_share(result: NkResult, cost_id: str, tenancy_id: str) -> int:
    matches = [line for line in lines_of(result, cost_id) if line.tenancy_id == tenancy_id]
    assert len(matches) == 1, f"{tenancy_id} must have exactly one line for {cost_id}"
    return int(matches[0].amount)


_MISSING: Final = object()


def required_error_field(error: BaseException, name: str) -> object:
    """Reads a field `docs/02` § 5 requires the raised error to carry.

    Deliberately `getattr`: the attribute does not exist yet, and writing
    `error.overallocated_weight` would make `mypy --strict` fail on *this* file
    rather than let the test fail on the missing behaviour.
    """
    value = getattr(error, name, _MISSING)
    assert value is not _MISSING, (
        f"{type(error).__name__} must carry `{name}`: docs/02 § 5 blocks overlapping "
        "tenancies before calculation, and the statement has to be able to state the "
        "figure instead of only reporting that an overlap exists"
    )
    return value


class TestF12ZeroConsumptionDenominator:
    """`08-F12` — the meters recorded nothing, so the owner keeps the cost.

    `docs/08` output contract: "A zero consumption denominator gives renters `0`
    and leaves the cost with the owner; it never silently changes to an area
    key." `docs/02` § 5 basis table, zero-denominator row: "Every renter share is
    zero; the complete amount remains in the owner residual with the required
    'no consumption values recorded' warning. The cost is not silently
    re-keyed."

    The golden records `denominator` 0, `renter_share` 0 and `owner_residual`
    126.000. NK keeps largest-remainder rounding here (`CLAUDE.md` § 8.4,
    `docs/08` § 3a) — this fixture is about *where* a zero-weight cost lands, not
    about how a non-zero one is rounded — so nothing below asserts an owner
    residual field on `NkResult`; it asserts the landlord-side line
    (`tenancy_id=None`) that the shipped result shape already has.
    """

    YEAR: Final = period("2025-01-01", "2026-01-01")
    OCCUPANCIES: Final = (
        Occupancy("unit-a", "ten-a", period("2025-01-01")),
        Occupancy("unit-b", "ten-b", period("2025-01-01")),
        Occupancy("unit-c", "ten-c", period("2025-01-01")),
    )
    # `08-F12` "owner_residual": the whole cost stays on the owner side.
    COST_CENTS: Final = 126_000
    # No invented consumption is added for the owner (`docs/02` § 5, Consumption
    # row) — the recorded renter values are simply all zero.
    ZERO_READINGS: Final = (
        ConsumptionValue("unit-a", "ten-a", Decimal(0), MeasurementUnit.KWH),
        ConsumptionValue("unit-b", "ten-b", Decimal(0), MeasurementUnit.KWH),
        ConsumptionValue("unit-c", "ten-c", Decimal(0), MeasurementUnit.KWH),
    )

    def _input(self, key: AllocationKey) -> NkInput:
        return NkInput(
            billing_period=self.YEAR,
            units=PAGE_01_UNITS,
            occupancies=self.OCCUPANCIES,
            costs=(
                CostItem(
                    cost_id="cost-heat-consumption",
                    label="Verbrauchskosten",
                    amount=cents(self.COST_CENTS),
                    key=key,
                ),
            ),
            consumptions=self.ZERO_READINGS,
        )

    def test_the_whole_cost_lands_on_the_landlord_side(self) -> None:
        result = calculate_nk_statement(self._input(AllocationKey.CONSUMPTION))
        lines = lines_of(result, "cost-heat-consumption")

        renter_lines = [line for line in lines if line.tenancy_id is not None]
        landlord_lines = [line for line in lines if line.tenancy_id is None]

        # `docs/08`: "Every cost line receives engine output" — a renter whose
        # meter read zero gets a rendered 0,00 € share, not a missing row the
        # document layer would have to invent.
        assert {line.tenancy_id for line in renter_lines} == {"ten-a", "ten-b", "ten-c"}
        assert [int(line.amount) for line in renter_lines] == [0, 0, 0]  # F12 renter_share
        assert sum(int(line.amount) for line in landlord_lines) == self.COST_CENTS
        # sum(shares) == input_total, asserted in every allocation test.
        assert sum(int(line.amount) for line in lines) == self.COST_CENTS
        assert int(result.total) == self.COST_CENTS

    def test_a_zero_denominator_never_silently_re_keys_to_area(self) -> None:
        consumption = calculate_nk_statement(self._input(AllocationKey.CONSUMPTION))
        # The counterfactual: what the same cost would look like if the key had
        # quietly become Wohnfläche. No golden figure is asserted here — the
        # point is only that the two runs must not agree.
        area = calculate_nk_statement(self._input(AllocationKey.AREA))

        area_shares = {
            line.tenancy_id: int(line.amount)
            for line in lines_of(area, "cost-heat-consumption")
            if line.tenancy_id is not None
        }
        assert all(share > 0 for share in area_shares.values())

        for line in lines_of(consumption, "cost-heat-consumption"):
            if line.tenancy_id is None:
                continue
            assert line.weight == Decimal(0)
            assert int(line.amount) != area_shares[line.tenancy_id]


class TestF15PeriodLongerThanTwelveMonths:
    """`08-F15` — 455 days, and `period_months_max` is 12.

    `docs/02` § 5 step 1: "A period longer than 12 months blocks before
    calculation or rendering." `docs/08` "Period boundary" says the same in the
    document's words. `_billing_window` currently rejects only an unbounded
    period, so this window is allocated instead of refused.
    """

    OVERLONG: Final = period("2025-01-01", "2026-04-01")  # 455 days
    OCCUPANCIES: Final = (Occupancy("unit-a", "ten-a", period("2025-01-01")),)

    def test_the_fixture_window_really_is_the_455_days_the_golden_states(self) -> None:
        assert days_between(self.OVERLONG.valid_from, period("2026-04-01").valid_from) == 455

    def test_a_455_day_period_hard_blocks(self) -> None:
        with pytest.raises(NkInputError, match=r"(?i)12\s*month"):
            calculate_nk_statement(
                NkInput(
                    billing_period=self.OVERLONG,
                    units=PAGE_01_UNITS,
                    occupancies=self.OCCUPANCIES,
                    costs=(
                        CostItem(
                            cost_id="cost-tax",
                            label="Grundsteuer",
                            amount=cents(GRUNDSTEUER_CENTS),
                            key=AllocationKey.AREA,
                        ),
                    ),
                )
            )

    def test_the_block_is_a_period_precondition_not_a_cost_side_effect(self) -> None:
        """The rule says *before* calculation, so it fires with nothing to allocate."""
        with pytest.raises(NkInputError, match=r"(?i)12\s*month"):
            calculate_nk_statement(
                NkInput(
                    billing_period=self.OVERLONG,
                    units=PAGE_01_UNITS,
                    occupancies=self.OCCUPANCIES,
                    costs=(),
                )
            )


class TestF14AndF20TheGreenHalfOfTheSamePeriodRule:
    """A shorter Rumpfperiode is day-exact and a leap year keeps its actual days.

    Both are `docs/08` "Period boundary" and `docs/02` § 5 step 1. They are
    asserted here because the `08-F15` block above must not be bought by
    clamping, normalising or month-counting a period that is legitimately short
    or legitimately 366 days long.
    """

    def test_f14_275_day_rumpfperiode_is_day_exact(self) -> None:
        # 01.04.2025–31.12.2025 inclusive = 275 days; the tenancy runs to
        # 31.10.2025 inclusive = 214 usage days (`08-F14` period_days/usage_days).
        rumpf = period("2025-04-01", "2026-01-01")
        result = calculate_nk_statement(
            NkInput(
                billing_period=rumpf,
                units=PAGE_01_UNITS,
                occupancies=(Occupancy("unit-a", "ten-a", period("2025-04-01", "2025-11-01")),),
                costs=(
                    CostItem(
                        cost_id="cost-tax",
                        label="Grundsteuer",
                        amount=cents(GRUNDSTEUER_CENTS),
                        key=AllocationKey.AREA,
                    ),
                ),
            )
        )
        lines = lines_of(result, "cost-tax")

        # 12.412 m²·Tage = 58 m² × 214 Tage, at the engine's ×100 area scale.
        renter_line = next(line for line in lines if line.tenancy_id == "ten-a")
        assert renter_line.weight == Decimal(12_412 * 100)  # F14 party_area_days
        # 53.350 m²·Tage = 194 m² × 275 Tage — the full denominator, vacancy included
        # (`docs/02` § 5: vacant area-days stay in the total area-days).
        assert sum(line.weight for line in lines) == Decimal(53_350 * 100)  # F14 total_area_days
        assert int(renter_line.amount) == 22_800  # F14 share
        assert sum(int(line.amount) for line in lines) == GRUNDSTEUER_CENTS

    def test_f20_leap_year_keeps_its_366_days_and_gets_no_special_money_rule(self) -> None:
        # 2024 is a leap year: 366 days, and the 74 m² unit is let for the first
        # 213 of them (`08-F20` period_days / partial_usage_days).
        leap_year = period("2024-01-01", "2025-01-01")
        result = calculate_nk_statement(
            NkInput(
                billing_period=leap_year,
                units=PAGE_01_UNITS,
                occupancies=(
                    Occupancy("unit-a", "ten-a", period("2024-01-01", "2025-01-01")),
                    Occupancy("unit-b", "ten-b", period("2024-01-01", "2024-08-01")),
                ),
                costs=(
                    CostItem(
                        cost_id="cost-tax",
                        label="Grundsteuer",
                        amount=cents(GRUNDSTEUER_CENTS),
                        key=AllocationKey.AREA,
                    ),
                ),
            )
        )
        lines = lines_of(result, "cost-tax")
        weights = {line.tenancy_id: line.weight for line in lines if line.tenancy_id is not None}

        # 21.228 = 58 × 366 and 15.762 = 74 × 213 — the leap day is counted, not
        # normalised away to a 365-day year.
        assert weights["ten-a"] == Decimal(21_228 * 100)  # F20 full_year_party_area_days
        assert weights["ten-b"] == Decimal(15_762 * 100)  # F20 partial_area_days
        assert sum(line.weight for line in lines) == Decimal(71_004 * 100)  # F20 total_area_days

        # "no special money rule": the ordinary allocation produces the golden's
        # two shares. `08-F20` records no cost of its own, so this run uses the
        # object's Grundsteuer from `08-F14`/`08-F23`; every integer cost that is
        # consistent with both golden shares yields exactly these two figures, so
        # no invented number decides the assertion.
        assert renter_share(result, "cost-tax", "ten-a") == 29_299  # F20 full_year_share
        assert renter_share(result, "cost-tax", "ten-b") == 21_755  # F20 partial_share
        assert sum(int(line.amount) for line in lines) == GRUNDSTEUER_CENTS


class TestF13OverlappingTenanciesStateTheOverAllocation:
    """`08-F13` — two tenancies claim the same 31 days of one 74 m² unit.

    `docs/02` § 5: "overlapping tenancies in one unit block before calculation or
    rendering." The block is shipped. What is missing is the figure: the golden
    records `available_area_days` 27.010 (= 74 × 365), `allocated_area_days`
    29.304 (= 74 × 396) and `overallocated_area_days` 2.294 (= 74 × 31), and a
    landlord who is told only "there is an overlap" cannot find the 31 days in a
    lease file. `08-F13`'s `probe_total` 101.175 against a 98.000 cost is what
    happens when that over-allocation is allowed to reach money — 3.175 cents of
    a cost allocated twice — which is why it blocks rather than warns.

    The weights are asserted de-scaled to the printed m²·Tage of `docs/08`
    "Reference totals (Gesamtbemessung)": "De-scale the sum once. `36.500
    m²·Tage` must never render as `3.650.000`."
    """

    YEAR: Final = period("2025-01-01", "2026-01-01")

    def test_the_fixture_dates_really_overlap_by_the_31_days_the_golden_states(self) -> None:
        first_end = period("2025-08-01").valid_from
        second_start = period("2025-07-01").valid_from
        assert days_between(second_start, first_end) == 31  # F13 overlap_days

    def test_the_block_carries_the_over_allocated_bemessung(self) -> None:
        with pytest.raises(OccupancyOverlapError) as raised:
            calculate_nk_statement(
                NkInput(
                    billing_period=self.YEAR,
                    units=PAGE_01_UNITS,
                    occupancies=(
                        # 01.01.–31.07. inclusive: 212 days (`08-F16` usage_days).
                        Occupancy("unit-b", "ten-b1", period("2025-01-01", "2025-08-01")),
                        # 01.07.–31.12. inclusive: 184 days — 31 of them already let.
                        Occupancy("unit-b", "ten-b2", period("2025-07-01", "2026-01-01")),
                    ),
                    costs=(
                        CostItem(
                            cost_id="cost-tax",
                            label="Grundsteuer",
                            amount=cents(GRUNDSTEUER_CENTS),
                            key=AllocationKey.AREA,
                        ),
                    ),
                )
            )

        error = raised.value
        assert required_error_field(error, "unit_id") == "unit-b"
        assert required_error_field(error, "overlap_days") == 31  # F13 overlap_days
        # In the applied key's printed unit — m²·Tage here, Personen·Tage or
        # Einheiten·Tage for the other keys, which is why the names are not
        # area-specific.
        assert required_error_field(error, "available_weight") == Decimal(27_010)
        assert required_error_field(error, "allocated_weight") == Decimal(29_304)
        assert required_error_field(error, "overallocated_weight") == Decimal(2_294)


class TestF11CreditsStaySeparateNegativeLines:
    """`08-F11` — a 62.000 cost and a -5.000 credit: the structural half only.

    `docs/08` output contract: "Credits stay separate negative lines." Slice B
    proves the *structure* of that sentence — a negative cost allocates at all,
    and the credit survives as its own line keyed to its own `cost_id` instead of
    being merged into or netted against the gross line. Both hold under either
    rounding rule.

    **What is deliberately not asserted here, and why.** The golden's
    `credit_share` -882 and `linewise_share` 10.061 are per-party half-up
    figures. Production NK is largest remainder until Slice C implements the
    reviewed Page 02 method (`CLAUDE.md` § 8.4; `docs/08` § 3a: "production NK
    remains on its pre-Page-02 method"), and the decision recorded for this slice
    is to keep it that way. Largest remainder over these weights gives the party
    -883, so the line-wise total is 10.060 — which is also exactly
    `forbidden_net_first_share` (57.000 × 365/2.068 = 10.060,4). For this fixture
    the correct line-wise result and the forbidden net-first result are therefore
    the *same number* under the current rule, and the discrimination the golden
    draws cannot be observed at all until the rounding moves. Asserting 10.061
    would demand Slice C work from Slice B; asserting `!= 10.060` would fail on
    correct Slice B behaviour. Both figures stay with `08-F11`'s Slice C entry in
    `packages/domain/tests/test_page01_slice_b_coverage.py`.

    **The one Slice B defect this class does pin** is independent of any rounding
    question: `distribute_cents` cannot allocate a negative total at all.
    `money.py` floors with `int(q // 1)`, and `Decimal.__floordiv__` truncates
    toward zero instead of flooring toward -inf, so on a negative total every
    "floor" is one too high, `remainder` comes out negative, the
    `by_remainder[:remainder]` slice drops entries from the end instead of adding
    cents, and the function trips its own `assert sum(result) == total`. A credit
    line is currently unrepresentable in NK.

    **The weight structure comes from `08-F22`**, which allocates the same 62.000
    cost: person-days 1.095 / 424 / 122 / 365 with the approved fictional
    occupancy taking `person_days_with` to 2.068, at which
    `62.000 × 365 / 2.068` gives the golden's `gross_share` 10.943 under both
    rounding rules. `08-F22`'s own building carries those last 62 person-days as
    D0 Fiktivbelegung on a vacant unit, and no NK input can express that today
    (`PersonCountPeriod.tenancy_id` is a required `str`), so this fixture carries
    them as a fifth short tenancy. That substitution cannot change the rules under
    test: an owner weight only ever enters the denominator (`docs/02` § 5), and
    the fraction 365/2.068 is identical either way.
    """

    YEAR: Final = period("2025-01-01", "2026-01-01")
    UNITS: Final = tuple(
        UnitBasis(unit_id=f"unit-{suffix}", area_sqm_x100=5_000) for suffix in "abcde"
    )
    OCCUPANCIES: Final = tuple(
        Occupancy(f"unit-{suffix}", f"ten-{suffix}", period("2025-01-01")) for suffix in "abcde"
    )
    # 1.095 + 424 + 122 + 365 + 62 = 2.068 Personen·Tage (`08-F22` person_days_with).
    PERSON_DAYS: Final = (
        PersonCountPeriod("ten-a", 3, period("2025-01-01", "2026-01-01")),  # 3 × 365 = 1.095
        PersonCountPeriod("ten-b", 4, period("2025-01-01", "2025-04-17")),  # 4 × 106 =   424
        PersonCountPeriod("ten-c", 2, period("2025-01-01", "2025-03-03")),  # 2 ×  61 =   122
        PersonCountPeriod("ten-d", 1, period("2025-01-01", "2026-01-01")),  # 1 × 365 =   365
        PersonCountPeriod("ten-e", 2, period("2025-12-01", "2026-01-01")),  # 2 ×  31 =    62
    )
    GROSS_CENTS: Final = 62_000  # F11 gross_cost
    CREDIT_CENTS: Final = -5_000  # F11 credit_cost

    def _result(self, *, with_credit: bool = True) -> NkResult:
        gross = CostItem(
            cost_id="cost-waste",
            label="Müllabfuhr",
            amount=cents(self.GROSS_CENTS),
            key=AllocationKey.PERSONS,
        )
        credit = CostItem(
            cost_id="cost-waste-credit",
            label="Gutschrift Müllabfuhr",
            amount=cents(self.CREDIT_CENTS),
            key=AllocationKey.PERSONS,
        )
        return calculate_nk_statement(
            NkInput(
                billing_period=self.YEAR,
                units=self.UNITS,
                occupancies=self.OCCUPANCIES,
                costs=(gross, credit) if with_credit else (gross,),
                person_counts=self.PERSON_DAYS,
            )
        )

    def test_the_fixture_weights_are_the_2068_person_days_of_f22(self) -> None:
        """Green self-check of the fixture: the gross cost alone already allocates."""
        gross_only = self._result(with_credit=False)
        weights = [line.weight for line in lines_of(gross_only, "cost-waste")]
        assert weights == [
            Decimal(1_095),
            Decimal(424),
            Decimal(122),
            Decimal(365),
            Decimal(62),
            Decimal(0),  # the mandatory owner residual is not a new denominator party
        ]
        assert sum(weights) == Decimal(2_068)  # F22 person_days_with
        # ...and at that denominator the party at 365 Personen·Tage already
        # reaches the golden's gross figure; only the credit line is missing.
        assert renter_share(gross_only, "cost-waste", "ten-d") == 10_943  # F11 gross_share

    def test_a_negative_cost_allocates_and_reconciles_to_its_own_total(self) -> None:
        """The floor defect, stated as the rule it breaks.

        Every allocation reconciles to its input total, and a credit is an input
        total like any other. `08-F11` `credit_cost` is -5.000, so the credit
        line's shares must sum to -5.000 — today the run does not get that far.
        No per-party cent figure is asserted: which party absorbs the leftover
        cent is exactly the Slice C question this slice defers.
        """
        result = self._result()

        credit_lines = lines_of(result, "cost-waste-credit")
        assert credit_lines, "the credit must be allocated, not dropped"
        assert sum(int(line.amount) for line in credit_lines) == self.CREDIT_CENTS
        assert all(int(line.amount) <= 0 for line in credit_lines)

    def test_the_credit_keeps_its_own_line_instead_of_being_netted_away(self) -> None:
        """The structural half of "credits stay separate negative lines".

        Provable under either rounding rule: the party holds two lines, one per
        `cost_id`, the credit one is negative, and the gross line is bit-for-bit
        what it was without the credit. A netted engine would show one line of
        57.000-worth instead, and no `cost_id` to point a renter's Belegeinsicht
        at.
        """
        result = self._result()
        gross_only = self._result(with_credit=False)

        party_lines = [line for line in result.lines if line.tenancy_id == "ten-d"]
        assert [line.cost_id for line in party_lines] == ["cost-waste", "cost-waste-credit"]
        assert int(party_lines[1].amount) < 0

        # The gross cost is untouched by the credit's presence: it is still the
        # golden's `gross_share`, and still reconciles to its own 62.000.
        assert int(party_lines[0].amount) == 10_943  # F11 gross_share
        assert int(party_lines[0].amount) == renter_share(gross_only, "cost-waste", "ten-d")
        assert sum(int(line.amount) for line in lines_of(result, "cost-waste")) == self.GROSS_CENTS
