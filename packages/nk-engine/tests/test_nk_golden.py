"""Golden fixtures for the NK engine (docs/03).

These tests are the spec — committed before the engine that satisfies them.
Every allocation asserts sum(shares) == input_total.
"""

from decimal import Decimal

import pytest
from lokara_domain import AllocationKey, Occupancy, cents, period
from lokara_nk_engine import (
    ConsumptionValue,
    CostItem,
    NkInput,
    NkInputError,
    PersonCountPeriod,
    ShareLine,
    UnitBasis,
    calculate_nk_statement,
)

YEAR_2025 = period("2025-01-01", "2026-01-01")

# The canonical building (lokara-arch.md §10 / docs/03): A 50 m², B 30 m², C 20 m²;
# Renter 2 moves out of B on Jun 30 (tenancy ends exclusive Jul 1), B vacant after.
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


def shares_of(
    result_lines: tuple[ShareLine, ...], cost_id: str
) -> list[tuple[str | None, str | None, int]]:
    return [
        (line.unit_id, line.tenancy_id, int(line.amount))
        for line in result_lines
        if line.cost_id == cost_id
    ]


class TestCanonicalGarbageCostFixture:
    """€1,200.00 garbage cost, key AREA, 365 days — MUST pass byte-for-byte (M1 DoD)."""

    def test_1200_eur_area_allocation_reconciles_to_the_cent(self) -> None:
        result = calculate_nk_statement(
            NkInput(
                billing_period=YEAR_2025,
                units=UNITS,
                occupancies=OCCUPANCIES,
                costs=(
                    CostItem(
                        cost_id="cost-garbage",
                        label="Müllabfuhr",
                        amount=cents(120000),
                        key=AllocationKey.AREA,
                    ),
                ),
            )
        )
        assert shares_of(result.lines, "cost-garbage") == [
            ("unit-a", "ten-a", 60000),  # 50 m² × 365 d = 18,250 → €600.00
            ("unit-b", "ten-b", 17852),  # 30 m² × 181 d = 5,430 → €178.52
            ("unit-b", None, 18148),  # VACANT Jul–Dec → landlord, €181.48
            ("unit-c", "ten-c", 24000),  # 20 m² × 365 d = 7,300 → €240.00
        ]
        assert sum(int(line.amount) for line in result.lines) == 120000
        assert result.total == 120000

    def test_weights_are_sqm_days(self) -> None:
        result = calculate_nk_statement(
            NkInput(
                billing_period=YEAR_2025,
                units=UNITS,
                occupancies=OCCUPANCIES,
                costs=(
                    CostItem(
                        cost_id="c",
                        label="Müllabfuhr",
                        amount=cents(120000),
                        key=AllocationKey.AREA,
                    ),
                ),
            )
        )
        # area_sqm_x100 × days: engine works on the x100 fixed-point values.
        assert [line.weight for line in result.lines] == [
            Decimal(5000 * 365),
            Decimal(3000 * 181),
            Decimal(3000 * 184),
            Decimal(2000 * 365),
        ]


class TestDirectAssignment:
    def test_direct_to_a_tenancy_bypasses_allocation_entirely(self) -> None:
        result = calculate_nk_statement(
            NkInput(
                billing_period=YEAR_2025,
                units=UNITS,
                occupancies=OCCUPANCIES,
                costs=(
                    CostItem(
                        cost_id="cost-repair",
                        label="Reparatur Wohnung C",
                        amount=cents(50000),
                        key=AllocationKey.DIRECT,
                        direct_tenancy_id="ten-c",
                    ),
                ),
            )
        )
        assert shares_of(result.lines, "cost-repair") == [("unit-c", "ten-c", 50000)]

    def test_direct_to_a_unit_is_day_weighted_within_that_unit_only(self) -> None:
        # €500 to unit B: renter 181 d, landlord (vacancy) 184 d; no other unit pays.
        result = calculate_nk_statement(
            NkInput(
                billing_period=YEAR_2025,
                units=UNITS,
                occupancies=OCCUPANCIES,
                costs=(
                    CostItem(
                        cost_id="cost-b-only",
                        label="Reparatur Einheit B",
                        amount=cents(50000),
                        key=AllocationKey.DIRECT,
                        direct_unit_id="unit-b",
                    ),
                ),
            )
        )
        assert shares_of(result.lines, "cost-b-only") == [
            ("unit-b", "ten-b", 24795),
            ("unit-b", None, 25205),
        ]
        assert sum(int(line.amount) for line in result.lines) == 50000


class TestPersonsKey:
    def test_mid_period_person_count_change_is_day_weighted(self) -> None:
        # Tenancy A: 2 persons Jan–Jun (181 d), 3 persons Jul–Dec (184 d).
        # Tenancy C: 1 person all year. Weights 362 / 552 / 365 of €600.00.
        result = calculate_nk_statement(
            NkInput(
                billing_period=YEAR_2025,
                units=UNITS,
                occupancies=OCCUPANCIES,
                costs=(
                    CostItem(
                        cost_id="cost-water",
                        label="Wasser",
                        amount=cents(60000),
                        key=AllocationKey.PERSONS,
                    ),
                ),
                person_counts=(
                    PersonCountPeriod("ten-a", 2, period("2025-01-01", "2025-07-01")),
                    PersonCountPeriod("ten-a", 3, period("2025-07-01")),
                    PersonCountPeriod("ten-c", 1, period("2025-01-01")),
                ),
            )
        )
        assert shares_of(result.lines, "cost-water") == [
            ("unit-a", "ten-a", 16982),
            ("unit-a", "ten-a", 25895),
            ("unit-c", "ten-c", 17123),
        ]
        assert sum(int(line.amount) for line in result.lines) == 60000


class TestConsumptionKey:
    def test_allocates_by_normalized_meter_values(self) -> None:
        result = calculate_nk_statement(
            NkInput(
                billing_period=YEAR_2025,
                units=UNITS,
                occupancies=OCCUPANCIES,
                costs=(
                    CostItem(
                        cost_id="cost-cold-water",
                        label="Kaltwasser",
                        amount=cents(90000),
                        key=AllocationKey.CONSUMPTION,
                    ),
                ),
                consumptions=(
                    ConsumptionValue("unit-a", "ten-a", Decimal("45.5")),
                    ConsumptionValue("unit-b", "ten-b", Decimal("30.25")),
                    ConsumptionValue("unit-c", "ten-c", Decimal("24.25")),
                ),
            )
        )
        assert shares_of(result.lines, "cost-cold-water") == [
            ("unit-a", "ten-a", 40950),
            ("unit-b", "ten-b", 27225),
            ("unit-c", "ten-c", 21825),
        ]
        assert sum(int(line.amount) for line in result.lines) == 90000


class TestUnitsKey:
    def test_each_unit_weighs_its_occupied_days(self) -> None:
        result = calculate_nk_statement(
            NkInput(
                billing_period=YEAR_2025,
                units=UNITS,
                occupancies=OCCUPANCIES,
                costs=(
                    CostItem(
                        cost_id="cost-fee",
                        label="Grundgebühr",
                        amount=cents(30000),
                        key=AllocationKey.UNITS,
                    ),
                ),
            )
        )
        # Weights: 365 / 181 / 184 / 365 days (1 per unit per day).
        lines = shares_of(result.lines, "cost-fee")
        assert [w for (_, _, w) in lines] == [10000, 4959, 5041, 10000]
        assert sum(int(line.amount) for line in result.lines) == 30000


class TestMeaKey:
    def test_allocates_by_co_ownership_share(self) -> None:
        units = (
            UnitBasis(unit_id="unit-a", area_sqm_x100=5000, mea_x10000=5000),
            UnitBasis(unit_id="unit-b", area_sqm_x100=3000, mea_x10000=3000),
            UnitBasis(unit_id="unit-c", area_sqm_x100=2000, mea_x10000=2000),
        )
        result = calculate_nk_statement(
            NkInput(
                billing_period=YEAR_2025,
                units=units,
                occupancies=OCCUPANCIES,
                costs=(
                    CostItem(
                        cost_id="cost-weg",
                        label="WEG-Verwaltung",
                        amount=cents(120000),
                        key=AllocationKey.MEA,
                    ),
                ),
            )
        )
        # Same proportions as the canonical AREA fixture (MEA mirrors the areas here).
        assert shares_of(result.lines, "cost-weg") == [
            ("unit-a", "ten-a", 60000),
            ("unit-b", "ten-b", 17852),
            ("unit-b", None, 18148),
            ("unit-c", "ten-c", 24000),
        ]


class TestPeriodLengthIndependence:
    """Interim (<12 months) and >12-month statements — day-count-driven, never 365 assumed."""

    def test_interim_statement_jan_to_jun(self) -> None:
        # Window Jan 1 – Jul 1 (181 days); B's renter leaves Mar 31 (ends Apr 1, 90 d).
        result = calculate_nk_statement(
            NkInput(
                billing_period=period("2025-01-01", "2025-07-01"),
                units=UNITS,
                occupancies=(
                    Occupancy("unit-a", "ten-a", period("2025-01-01")),
                    Occupancy("unit-b", "ten-b", period("2024-08-01", "2025-04-01")),
                    Occupancy("unit-c", "ten-c", period("2023-01-01")),
                ),
                costs=(
                    CostItem(
                        cost_id="cost-garbage",
                        label="Müllabfuhr",
                        amount=cents(120000),
                        key=AllocationKey.AREA,
                    ),
                ),
            )
        )
        # Weights (m²·days ×100): A 5000×181, B renter 3000×90, B vacant 3000×91, C 2000×181.
        assert shares_of(result.lines, "cost-garbage") == [
            ("unit-a", "ten-a", 60000),
            ("unit-b", "ten-b", 17901),
            ("unit-b", None, 18099),
            ("unit-c", "ten-c", 24000),
        ]

    def test_18_month_statement(self) -> None:
        # Window Jan 1 2025 – Jul 1 2026 (546 days); B renter out Jun 30 2025, vacant after.
        result = calculate_nk_statement(
            NkInput(
                billing_period=period("2025-01-01", "2026-07-01"),
                units=UNITS,
                occupancies=OCCUPANCIES,
                costs=(
                    CostItem(
                        cost_id="cost-garbage",
                        label="Müllabfuhr",
                        amount=cents(120000),
                        key=AllocationKey.AREA,
                    ),
                ),
            )
        )
        # Weights: A 5000×546, B renter 3000×181, B vacant 3000×365, C 2000×546.
        assert shares_of(result.lines, "cost-garbage") == [
            ("unit-a", "ten-a", 60000),
            ("unit-b", "ten-b", 11934),
            ("unit-b", None, 24066),
            ("unit-c", "ten-c", 24000),
        ]


class TestValidation:
    def test_direct_without_target_is_rejected(self) -> None:
        with pytest.raises(NkInputError):
            calculate_nk_statement(
                NkInput(
                    billing_period=YEAR_2025,
                    units=UNITS,
                    occupancies=OCCUPANCIES,
                    costs=(
                        CostItem(
                            cost_id="c",
                            label="x",
                            amount=cents(100),
                            key=AllocationKey.DIRECT,
                        ),
                    ),
                )
            )

    def test_direct_to_unknown_unit_is_rejected(self) -> None:
        with pytest.raises(NkInputError):
            calculate_nk_statement(
                NkInput(
                    billing_period=YEAR_2025,
                    units=UNITS,
                    occupancies=OCCUPANCIES,
                    costs=(
                        CostItem(
                            cost_id="c",
                            label="x",
                            amount=cents(100),
                            key=AllocationKey.DIRECT,
                            direct_unit_id="unit-zzz",
                        ),
                    ),
                )
            )

    def test_persons_key_without_person_counts_is_rejected(self) -> None:
        with pytest.raises(NkInputError):
            calculate_nk_statement(
                NkInput(
                    billing_period=YEAR_2025,
                    units=UNITS,
                    occupancies=OCCUPANCIES,
                    costs=(
                        CostItem(
                            cost_id="c",
                            label="x",
                            amount=cents(100),
                            key=AllocationKey.PERSONS,
                        ),
                    ),
                )
            )

    def test_mea_key_without_mea_values_is_rejected(self) -> None:
        with pytest.raises(NkInputError):
            calculate_nk_statement(
                NkInput(
                    billing_period=YEAR_2025,
                    units=UNITS,  # no mea_x10000 set
                    occupancies=OCCUPANCIES,
                    costs=(
                        CostItem(
                            cost_id="c",
                            label="x",
                            amount=cents(100),
                            key=AllocationKey.MEA,
                        ),
                    ),
                )
            )

    def test_rerun_with_a_different_key_destroys_no_input(self) -> None:
        # "Changing a key re-runs the calc and cascades into no stored data" —
        # inputs are frozen; two runs over the same input give independent results.
        base = NkInput(
            billing_period=YEAR_2025,
            units=UNITS,
            occupancies=OCCUPANCIES,
            costs=(
                CostItem(
                    cost_id="c",
                    label="Müllabfuhr",
                    amount=cents(120000),
                    key=AllocationKey.AREA,
                ),
            ),
        )
        first = calculate_nk_statement(base)
        rerun = calculate_nk_statement(
            NkInput(
                billing_period=base.billing_period,
                units=base.units,
                occupancies=base.occupancies,
                costs=(
                    CostItem(
                        cost_id="c",
                        label="Müllabfuhr",
                        amount=cents(120000),
                        key=AllocationKey.UNITS,
                    ),
                ),
            )
        )
        assert first.total == rerun.total == 120000
        assert calculate_nk_statement(base).lines == first.lines  # deterministic
