"""Vacancy stays in the denominator — `08-F22`, `08-F23` and the Consumption rule.

Spec: `docs/02-data-model.md` § 5 "full denominator" basis table and its
"D0 Fiktivbelegung" subsection; original Page 01 § 3.5, § 4 D0 and edge cases
E17/E18/E19; `docs/08-statement-document.md` Appendix A (`08-F21`–`08-F23`).
Every expected figure is transcribed from `packages/domain/tests/berkay_01_golden.py`
with the golden field named beside it, or from the Page 01 § 6 reference object
where the golden records no such field (marked as such). Rechtsstand 08/2026;
the D0 convention itself is Rechtsstand 07/2026 — see below.

The rule under test, `docs/02` § 5: "The residual does not remove vacancy from
allocation." Area- and unit-days of a vacant unit stay in their totals, the
approved fictional person occupancy is *added* to the person-days, and
consumption gets nothing invented for it.

The D0 count is a flagged convention, not law
---------------------------------------------
The register row `Fiktivbelegung bei Leerstand` (`berkay-work/Rechtsstand-Register/
Rechtsstand-Register.csv`) reads "letzte bekannte Belegung der Einheit, mindestens
1, taggenau; umschaltbar auf „immer 1"", `Rechtsnatur: Konvention`, status
`verify-before-production`, Rechtsstand 07/2026, on LG Krefeld 2 S 56/09 and
BGH VIII ZR 180/12 — and that BGH decision expressly leaves the Ansatz a Tatfrage
of the individual case rather than settling it. So the count is **derived** (last
known occupancy of the unit, minimum 1, day-exact), never a number a caller
invents, and nothing here may read as settled law.

`docs/02` § 5 records the layering as an open decision: whether the adapter
derives the count and hands the engine landlord-side person-days, or the engine
derives it from a supplied history plus the mode. The assertions below are
therefore all about the **result** — how the denominator is composed and where the
fictional weight lands — and only `_with_fiction` touches the input shape.

Scope: weights and denominators, not cents
------------------------------------------
Page 01's cent figures for these fixtures generally need the `docs/02` § 5
renter-half-up + owner-residual method, while production NK keeps largest
remainder through Slice B (`CLAUDE.md` § 8.4; `docs/08` § 3a). Three cent claims
below are exceptions, each **computed both ways in this session** rather than
assumed:

* `08-F22` `without_fiction` `(33.843, 13.105, 3.771, 11.281)` — identical under
  half-up and largest remainder. Asserted, because it is the counterfactual the
  case law rejects and it is worth pinning exactly.
* `08-F22` `with_fiction` and `owner_residual` — the methods genuinely diverge
  here: largest remainder gives Weber `3.657` and the owner `1.859` against the
  golden's `3.658` / `1.858`. **Not asserted**; deferred to Slice C.
* `08-F23` `property_tax_owner` `37.381` — identical under both methods
  (`98.000 × 27.010/70.810 = 37.381,44`; renter half-ups `31.320 + 29.299` leave
  the same residual). Asserted, as the regression guard the area half already
  earns today. Its `waste_owner` `20.667` is likewise method-independent, but the
  person-day half cannot run at all yet, so nothing there asserts a cent.

The scale convention: an `AREA` weight is `area_sqm_x100 × days`, so the printed
m²·Tage of `docs/08` "Reference totals" is that number ÷ 100. Comments state the
de-scaled figure, assertions the scaled one — as in
`test_page01_edge_cases.py`.

The five D0 tests were `xfail(strict=True)` and are not any more
----------------------------------------------------------------
They were written before the input shape existed and by a different agent than
the one who satisfied them (`CLAUDE.md` § 10), so they were committed as strict
xfails: the assertions executed in full, and the moment the shape landed they
all reported `XPASS(strict)` — a failure the implementer had to clear by reading
each assertion. That is what happened; not one expected figure was relaxed to
clear it. The markers are gone because the behaviour is here, and they must not
come back: a D0 regression is now an ordinary red test.
"""

from decimal import Decimal
from typing import Final

import pytest
from lokara_domain import (
    AllocationKey,
    MeasurementUnit,
    Occupancy,
    Period,
    cents,
    days_between,
    period,
)
from lokara_nk_engine import (
    ConsumptionValue,
    CostItem,
    NkInput,
    NkResult,
    PersonCountPeriod,
    ShareLine,
    UnitBasis,
    calculate_nk_statement,
)

# Page 01 § 6 reference object: Musterstraße 12, 01.01.–31.12.2025 (365 days),
# WE-01 62 m² · WE-02 74 m² · WE-03 58 m² (Σ 194 m²).
YEAR: Final = period("2025-01-01", "2026-01-01")
WE_01_SQM: Final = 62
WE_02_SQM: Final = 74  # `08-F23` vacant_area_sqm
WE_03_SQM: Final = 58

UNITS: Final = (
    UnitBasis(unit_id="we-01", area_sqm_x100=WE_01_SQM * 100),
    UnitBasis(unit_id="we-02", area_sqm_x100=WE_02_SQM * 100),
    UnitBasis(unit_id="we-03", area_sqm_x100=WE_03_SQM * 100),
)

# Page 01 § 6 cost positions: Müllbeseitigung (Personen) and Grundsteuer (m²).
WASTE_CENTS: Final = 62_000  # `08-F22` cost / `08-F23` waste_cost
PROPERTY_TAX_CENTS: Final = 98_000  # `08-F23` property_tax


def lines_of(result: NkResult, cost_id: str) -> tuple[ShareLine, ...]:
    return tuple(line for line in result.lines if line.cost_id == cost_id)


def renter_weights(result: NkResult, cost_id: str) -> list[Decimal]:
    return [line.weight for line in lines_of(result, cost_id) if line.tenancy_id is not None]


def landlord_weight(result: NkResult, cost_id: str) -> Decimal:
    """The whole landlord side of one cost, whichever unit it is attributed to.

    Summed rather than matched to a single line on purpose: `docs/02` § 5 makes
    the owner side one residual, and how many rows carry it — one per vacant unit
    or one aggregate — is a rendering question this test does not decide.
    """
    return sum(
        (line.weight for line in lines_of(result, cost_id) if line.tenancy_id is None),
        Decimal(0),
    )


def landlord_amount(result: NkResult, cost_id: str) -> int:
    return sum(int(line.amount) for line in lines_of(result, cost_id) if line.tenancy_id is None)


def _with_fiction(
    renter_rows: tuple[PersonCountPeriod, ...],
    *,
    persons: int,
    vacancy: Period,
) -> tuple[PersonCountPeriod, ...]:
    """Adds D0's landlord-side person-days to a person-count list.

    **This function is the only thing in the file that touches the input shape**,
    and it is the layering `docs/02` § 5 settled on: the caller supplies
    already-derived person-days for the landlord, exactly as
    `ConsumptionValue.tenancy_id=None` already attributes a consumption value to
    the landlord. The engine stays pure and history-free; the mode, the minimum
    and the `keine` confirmation live outside it. Not one assertion below names
    an input field, so they held unchanged across that decision.

    `persons == 0` is the `keine` mode and adds no row at all — a zero-weight
    landlord row is not the same statement as "no fictional occupancy".
    """
    if persons == 0:
        return renter_rows
    return (*renter_rows, PersonCountPeriod(None, persons, vacancy))


class TestF22FictionalOccupancyEntersThePersonDayDenominator:
    """`08-F22` — one month of vacancy, and who pays the fixed waste fee for it.

    Page 01 E18: without the fictional occupancy "the tenants carry 100 % of
    person-keyed fixed costs, which contradicts BGH VIII ZR 159/05 / LG Krefeld
    2 S 56/09". `docs/02` § 5, Persons row: "The approved fictional-person
    occupancy is added before forming person-days."

    The building is the Page 01 § 6 reference object: Muster (WE-01, 3 persons,
    365 d), Schneider (WE-02, 01.01.–31.07., 2 persons, 212 d), Weber (WE-02,
    01.09.–31.12., 1 person, 122 d), Beispiel (WE-03, 1 person, 365 d) — and the
    August gap in WE-02 nobody covers. `3×365 + 2×212 + 1×122 + 1×365 = 2.006`
    is the golden's `person_days_without`; the last known occupancy of WE-02 is
    Schneider's 2, so D0 adds `2 × 31 = 62` and reaches `person_days_with`
    2.068. `08-F21` records that same vacancy as `vacancy_days` 31 and
    `fictional_persons` 2, which is where the 2 is checked against, not guessed.
    """

    VACANCY: Final = period("2025-08-01", "2025-09-01")  # `08-F21` vacancy_days 31
    LAST_KNOWN_OCCUPANCY_OF_WE_02: Final = 2  # `08-F21` fictional_persons

    OCCUPANCIES: Final = (
        Occupancy("we-01", "ten-muster", period("2025-01-01", "2026-01-01")),
        Occupancy("we-02", "ten-schneider", period("2025-01-01", "2025-08-01")),
        Occupancy("we-02", "ten-weber", period("2025-09-01", "2026-01-01")),
        Occupancy("we-03", "ten-beispiel", period("2025-01-01", "2026-01-01")),
    )
    # Order matters: it is the golden's tuple order (Muster, Schneider, Weber,
    # Beispiel) and largest-remainder ties break toward the lowest index.
    RENTER_PERSON_DAYS: Final = (
        PersonCountPeriod("ten-muster", 3, period("2025-01-01", "2026-01-01")),  # 3 × 365 = 1.095
        PersonCountPeriod("ten-schneider", 2, period("2025-01-01", "2025-08-01")),  # 2 × 212 = 424
        PersonCountPeriod("ten-weber", 1, period("2025-09-01", "2026-01-01")),  # 1 × 122 = 122
        PersonCountPeriod("ten-beispiel", 1, period("2025-01-01", "2026-01-01")),  # 1 × 365 = 365
    )

    def _result(self, fictional_persons: int) -> NkResult:
        return calculate_nk_statement(
            NkInput(
                billing_period=YEAR,
                units=UNITS,
                occupancies=self.OCCUPANCIES,
                costs=(
                    CostItem(
                        cost_id="cost-waste",
                        label="Müllbeseitigung",
                        amount=cents(WASTE_CENTS),
                        key=AllocationKey.PERSONS,
                    ),
                ),
                person_counts=_with_fiction(
                    self.RENTER_PERSON_DAYS,
                    persons=fictional_persons,
                    vacancy=self.VACANCY,
                ),
            )
        )

    def test_the_building_really_carries_the_31_day_august_vacancy(self) -> None:
        """Fixture self-check: the gap is 31 days, and it belongs to no tenancy."""
        assert days_between(self.VACANCY.valid_from, period("2025-09-01").valid_from) == 31
        covered = [o for o in self.OCCUPANCIES if o.unit_id == "we-02"]
        assert covered[0].period.valid_to == self.VACANCY.valid_from
        assert covered[1].period.valid_from == period("2025-09-01").valid_from

    def test_without_the_fiction_the_renters_carry_the_whole_august_fee(self) -> None:
        """The counterfactual E18 forbids — asserted so the fix has something to move.

        The four cents are the golden's `without_fiction`. They are asserted
        although this file otherwise avoids Page 01 cents: computed both ways in
        this session, half-up and largest remainder give the same four figures at
        this denominator, so nothing here presupposes the Slice C rounding.
        """
        result = self._result(fictional_persons=0)

        assert renter_weights(result, "cost-waste") == [
            Decimal(1_095),
            Decimal(424),
            Decimal(122),
            Decimal(365),
        ]
        # `08-F22` person_days_without — the denominator the case law objects to.
        assert sum(renter_weights(result, "cost-waste")) == Decimal(2_006)
        assert landlord_weight(result, "cost-waste") == Decimal(0)

        renter_amounts = [
            int(line.amount)
            for line in lines_of(result, "cost-waste")
            if line.tenancy_id is not None
        ]
        assert renter_amounts == [33_843, 13_105, 3_771, 11_281]  # F22 without_fiction
        # sum(shares) == input_total, asserted in every allocation test.
        assert sum(renter_amounts) == WASTE_CENTS
        assert landlord_amount(result, "cost-waste") == 0

    def test_the_fiction_adds_62_landlord_person_days_to_the_denominator(self) -> None:
        """The rule: `2.006` becomes `2.068`, and the 62 are the landlord's.

        Red until D0's landlord-side person-days can be expressed at all. No cent
        is asserted: `with_fiction` and `owner_residual` are exactly where
        half-up and largest remainder disagree (`3.658`/`1.858` against
        `3.657`/`1.859`), so this test states the denominator and the direction —
        every renter share must fall — and leaves the cents to Slice C.
        """
        with_fiction = self._result(fictional_persons=self.LAST_KNOWN_OCCUPANCY_OF_WE_02)
        without = self._result(fictional_persons=0)

        # The renters' own weights are untouched — D0 adds, it never re-weights.
        assert renter_weights(with_fiction, "cost-waste") == renter_weights(without, "cost-waste")
        assert landlord_weight(with_fiction, "cost-waste") == Decimal(62)
        total_weight = sum(line.weight for line in lines_of(with_fiction, "cost-waste"))
        assert total_weight == Decimal(2_068)  # F22 person_days_with

        # The fictional occupancy is a denominator weight, never a party: it may
        # not appear as a renter line (`docs/02` § 5, and it is not a `Renter`).
        assert len([line for line in lines_of(with_fiction, "cost-waste") if line.tenancy_id]) == 4

        # E18's point, as an inequality rather than a figure: every renter pays
        # less than in the counterfactual, and the difference is the landlord's.
        with_amounts = [
            int(line.amount)
            for line in lines_of(with_fiction, "cost-waste")
            if line.tenancy_id is not None
        ]
        without_amounts = [
            int(line.amount)
            for line in lines_of(without, "cost-waste")
            if line.tenancy_id is not None
        ]
        assert all(a < b for a, b in zip(with_amounts, without_amounts, strict=True))
        assert landlord_amount(with_fiction, "cost-waste") > 0
        assert sum(int(line.amount) for line in lines_of(with_fiction, "cost-waste")) == WASTE_CENTS

    @pytest.mark.parametrize(
        ("mode", "fictional_persons", "expected_person_days"),
        [
            # Register default: last known occupancy of WE-02 (Schneider's 2).
            ("letzteBelegung", 2, 2_006 + 2 * 31),
            # The documented switch — a different denominator, not a rounding nuance.
            ("immer1", 1, 2_006 + 1 * 31),
            # Only with a logged confirmation after the E18 hard warning; the
            # engine expresses it as the absence of a landlord row, not a zero one.
            ("keine", 0, 2_006),
        ],
    )
    def test_the_register_modes_produce_different_denominators(
        self, mode: str, fictional_persons: int, expected_person_days: int
    ) -> None:
        """Each Fiktivbelegung mode of the register row is a different denominator.

        The three counts come from the register rule (`max(1, last known)`, `1`,
        `0`); the person-days are `count × 31` day-exact on top of the golden's
        `person_days_without` 2.006. All three are now reachable, which is the
        point: the mode a landlord may use *only with a logged confirmation* is
        no longer the only one the engine can express.
        """
        result = self._result(fictional_persons=fictional_persons)
        total_weight = sum(line.weight for line in lines_of(result, "cost-waste"))

        assert total_weight == Decimal(expected_person_days), mode
        assert landlord_weight(result, "cost-waste") == Decimal(fictional_persons * 31)

    def test_no_mode_with_a_fiction_can_collapse_to_the_keine_denominator(self) -> None:
        """The register's "mindestens 1" has an observable consequence.

        A derived count is `max(1, last known)`, so even a unit whose last known
        occupancy is unknown or zero contributes `1 × 31` person-days. The
        derived and the always-1 branch may coincide, but neither may equal the
        `keine` denominator — that is the difference between an applied
        convention and a landlord's logged waiver of it.
        """
        denominators = {
            mode: sum(line.weight for line in lines_of(self._result(persons), "cost-waste"))
            for mode, persons in (("letzteBelegung", 2), ("immer1", 1), ("keine", 0))
        }
        assert denominators["letzteBelegung"] > denominators["immer1"] > denominators["keine"]


class TestF23WholePeriodVacancyStaysInTheDenominators:
    """`08-F23` — WE-02 is vacant for all 365 days and stays in every denominator.

    Page 01 E19: "All of that unit's shares fall to the owner; the unit stays in
    the Gesamtverteiler and is never removed from it" (BGH VIII ZR 159/05).
    `docs/02` § 5: vacant area-days remain in the total area-days, vacant
    unit-days in the total unit-days, and the fictional occupancy is added to the
    person-days.

    Only WE-01 (Muster, 3 persons) and WE-03 (Beispiel, 1 person) are let, so the
    person-days are `1.095 + 365 + 730 = 2.190` — the golden's
    `total_person_days`, with `fictional_person_days` 730 = 2 × 365 at WE-02's
    last known occupancy of 2 (`08-F21` `fictional_persons`).
    """

    OCCUPANCIES: Final = (
        Occupancy("we-01", "ten-muster", period("2025-01-01", "2026-01-01")),
        Occupancy("we-03", "ten-beispiel", period("2025-01-01", "2026-01-01")),
    )
    RENTER_PERSON_DAYS: Final = (
        PersonCountPeriod("ten-muster", 3, period("2025-01-01", "2026-01-01")),  # 1.095
        PersonCountPeriod("ten-beispiel", 1, period("2025-01-01", "2026-01-01")),  # 365
    )

    def _result(self, cost: CostItem, *, fictional_persons: int = 0) -> NkResult:
        return calculate_nk_statement(
            NkInput(
                billing_period=YEAR,
                units=UNITS,
                occupancies=self.OCCUPANCIES,
                costs=(cost,),
                person_counts=_with_fiction(
                    self.RENTER_PERSON_DAYS,
                    persons=fictional_persons,
                    vacancy=YEAR,
                ),
            )
        )

    @property
    def _property_tax(self) -> CostItem:
        return CostItem(
            cost_id="cost-tax",
            label="Grundsteuer",
            amount=cents(PROPERTY_TAX_CENTS),
            key=AllocationKey.AREA,
        )

    def test_the_vacant_area_days_stay_in_the_total_area_days(self) -> None:
        """Regression guard: this half already passes, and must keep passing.

        It is pinned rather than left implicit because everything else about
        `08-F23` is blocked, and an "unblocking" change to the persons path must
        not quietly drop the vacant unit out of the area denominator on the way.

        The owner's `37.381` is asserted although this file otherwise defers
        Page 01 cents: computed both ways in this session, `98.000 × 27.010 /
        70.810 = 37.381,44` truncates to `37.381` under largest remainder and the
        half-up renters (`31.320 + 29.299`) leave exactly the same residual, so
        the figure is method-independent and presupposes no Slice C rounding.
        """
        result = self._result(self._property_tax)
        lines = lines_of(result, "cost-tax")

        # 27.010 m²·Tage = 74 m² × 365 Tage, at the engine's ×100 scale.
        assert landlord_weight(result, "cost-tax") == Decimal(27_010 * 100)  # F23 vacant_area_days
        # 70.810 m²·Tage = 194 m² × 365 Tage — the vacant unit included.
        assert sum(line.weight for line in lines) == Decimal(70_810 * 100)  # F23 total_area_days

        assert landlord_amount(result, "cost-tax") == 37_381  # F23 property_tax_owner
        assert sum(int(line.amount) for line in lines) == PROPERTY_TAX_CENTS

    def test_the_vacant_unit_is_never_removed_from_the_gesamtverteiler(self) -> None:
        """E19 as a comparison: letting WE-02 changes no denominator at all.

        If vacancy were removed from the distributor, the two runs would differ —
        the whole point of BGH VIII ZR 159/05 is that they may not.
        """
        vacant = self._result(self._property_tax)
        fully_let = calculate_nk_statement(
            NkInput(
                billing_period=YEAR,
                units=UNITS,
                occupancies=(
                    *self.OCCUPANCIES,
                    Occupancy("we-02", "ten-hypothetical", period("2025-01-01", "2026-01-01")),
                ),
                costs=(self._property_tax,),
            )
        )

        assert sum(line.weight for line in lines_of(vacant, "cost-tax")) == sum(
            line.weight for line in lines_of(fully_let, "cost-tax")
        )
        # Vacancy stays in the single owner residual's denominator; it is not
        # a separate owner party line for WE-02.
        assert landlord_weight(vacant, "cost-tax") == Decimal(27_010 * 100)

    def test_the_vacant_unit_days_stay_in_the_unit_day_denominator(self) -> None:
        """`docs/02` § 5, Units row — the same rule on the `ANZ_WE` key.

        Page 01 § 6 records `nAnzWE = 3`; day-weighted over the year that is
        `3 × 365 = 1.095` unit-days, of which the vacant unit's 365 are the
        landlord's. No cent is asserted — the key here is which weights exist.
        """
        result = self._result(
            CostItem(
                cost_id="cost-chimney",
                label="Schornsteinreinigung",
                amount=cents(12_000),  # Page 01 § 6 cost position, WE key
                key=AllocationKey.UNITS,
            )
        )
        lines = lines_of(result, "cost-chimney")

        assert landlord_weight(result, "cost-chimney") == Decimal(365)
        assert sum(line.weight for line in lines) == Decimal(3 * 365)
        assert sum(int(line.amount) for line in lines) == 12_000

    def test_the_full_year_fiction_adds_730_person_days_to_the_denominator(self) -> None:
        """`fictional_person_days` 730 of `total_person_days` 2.190.

        Red for the same reason as `08-F22`: there is no way to express a
        landlord-side person count. This fixture is also the one that shows why
        the layering question is not academic — WE-02 has no tenancy inside the
        period at all, so its "last known occupancy" comes from before the
        billing period and cannot be derived from anything in `NkInput` today.

        `waste_owner` 20.667 is method-independent (`62.000 × 730/2.190 =
        20.666,67`; the owner holds the largest fractional remainder either way),
        but it is not asserted here: this test must stay red for exactly one
        reason — the missing input shape.
        """
        waste = CostItem(
            cost_id="cost-waste",
            label="Müllbeseitigung",
            amount=cents(WASTE_CENTS),
            key=AllocationKey.PERSONS,
        )
        result = self._result(waste, fictional_persons=2)
        lines = lines_of(result, "cost-waste")

        assert renter_weights(result, "cost-waste") == [Decimal(1_095), Decimal(365)]
        assert landlord_weight(result, "cost-waste") == Decimal(730)  # F23 fictional_person_days
        assert sum(line.weight for line in lines) == Decimal(2_190)  # F23 total_person_days
        assert sum(int(line.amount) for line in lines) == WASTE_CENTS


class TestConsumptionAddsNothingForAVacantUnit:
    """`docs/02` § 5, Consumption row: "No invented consumption is added."

    The counterpart to D0, and the reason the two rows are separate: a vacant
    unit *is* added to the person-days by convention, and *is not* given a
    consumption value by anything. Page 01 § 4 D0 says it in one line —
    "Consumption denominators are untouched — a vacant unit consumes nothing."

    Building: `08-F23`'s — WE-02 vacant all year, WE-01 and WE-03 let. The two
    m³ figures are the Page 01 § 6 reference object's per-tenancy water
    consumption (Muster 95 m³, Beispiel 41 m³); the golden records no per-unit
    water field, so they are named to the Page rather than to a golden field.
    """

    OCCUPANCIES: Final = (
        Occupancy("we-01", "ten-muster", period("2025-01-01", "2026-01-01")),
        Occupancy("we-03", "ten-beispiel", period("2025-01-01", "2026-01-01")),
    )
    MUSTER_M3: Final = Decimal(95)
    BEISPIEL_M3: Final = Decimal(41)
    WATER_CENTS: Final = 126_000  # Page 01 § 6 Wasserversorgung

    def _result(self, consumptions: tuple[ConsumptionValue, ...]) -> NkResult:
        return calculate_nk_statement(
            NkInput(
                billing_period=YEAR,
                units=UNITS,
                occupancies=self.OCCUPANCIES,
                costs=(
                    CostItem(
                        cost_id="cost-water",
                        label="Wasserversorgung",
                        amount=cents(self.WATER_CENTS),
                        key=AllocationKey.CONSUMPTION,
                    ),
                ),
                consumptions=consumptions,
            )
        )

    RECORDED: Final = (
        ConsumptionValue("we-01", "ten-muster", Decimal(95), MeasurementUnit.CUBIC_METRE),
        ConsumptionValue("we-03", "ten-beispiel", Decimal(41), MeasurementUnit.CUBIC_METRE),
    )

    def test_the_vacant_unit_contributes_no_consumption_weight(self) -> None:
        result = self._result(self.RECORDED)
        lines = lines_of(result, "cost-water")

        assert renter_weights(result, "cost-water") == [self.MUSTER_M3, self.BEISPIEL_M3]
        assert landlord_weight(result, "cost-water") == Decimal(0)
        # The denominator is the recorded values and nothing else — 136 m³, not
        # 203: WE-02's usual consumption is not carried over into a vacancy.
        assert sum(line.weight for line in lines) == Decimal(136)
        assert sum(int(line.amount) for line in lines) == self.WATER_CENTS
        assert result.consumption_unit is MeasurementUnit.CUBIC_METRE

    def test_a_recorded_zero_for_the_vacant_unit_prints_a_line_and_moves_no_money(self) -> None:
        """`docs/02` § 5: a vacant unit with no consumption "can contribute 0,00 €".

        A recorded zero is a reading, not an invented value: the line exists so
        the owner overview can show it, and every renter share stays bit-for-bit
        what it was.
        """
        without_row = self._result(self.RECORDED)
        with_zero_row = self._result(
            (
                *self.RECORDED,
                ConsumptionValue("we-02", None, Decimal(0), MeasurementUnit.CUBIC_METRE),
            )
        )

        assert landlord_weight(with_zero_row, "cost-water") == Decimal(0)
        assert landlord_amount(with_zero_row, "cost-water") == 0
        assert any(
            line.unit_id is None and line.tenancy_id is None
            for line in lines_of(with_zero_row, "cost-water")
        )
        assert [
            int(line.amount)
            for line in lines_of(with_zero_row, "cost-water")
            if line.tenancy_id is not None
        ] == [
            int(line.amount)
            for line in lines_of(without_row, "cost-water")
            if line.tenancy_id is not None
        ]

    def test_an_invented_landlord_consumption_would_change_every_renter_share(self) -> None:
        """Why the rule needs a test rather than a comment.

        Fabricating a value for the vacant unit — the obvious "fix" once D0 has
        taught the codebase to give the landlord a person weight — moves money
        away from the renters on a key where no reading exists to justify it.
        The two runs must differ, and the recorded-values run is the correct one.
        """
        honest = self._result(self.RECORDED)
        fabricated = self._result(
            (
                *self.RECORDED,
                # WE-02's consumption in a year it *was* let. Page 01 § 6 records
                # 48 + 19 m³ for Schneider and Weber; nothing entitles it to a
                # vacant year.
                ConsumptionValue("we-02", None, Decimal(67), MeasurementUnit.CUBIC_METRE),
            )
        )

        honest_amounts = [
            int(line.amount)
            for line in lines_of(honest, "cost-water")
            if line.tenancy_id is not None
        ]
        fabricated_amounts = [
            int(line.amount)
            for line in lines_of(fabricated, "cost-water")
            if line.tenancy_id is not None
        ]
        assert all(a > b for a, b in zip(honest_amounts, fabricated_amounts, strict=True))
        assert sum(honest_amounts) == self.WATER_CENTS
