"""Page-02 rounding replaces NK largest remainder with an owner residual."""

from decimal import Decimal

from lokara_domain import AllocationKey, Occupancy, cents, period
from lokara_nk_engine import CostItem, NkInput, UnitBasis, calculate_nk_statement


def test_renter_lines_round_half_up_and_one_unweighted_owner_residual_reconciles() -> None:
    result = calculate_nk_statement(
        NkInput(
            billing_period=period("2025-01-01", "2025-01-02"),
            units=(
                UnitBasis("a", 100),
                UnitBasis("b", 100),
                UnitBasis("c", 100),
            ),
            occupancies=(
                Occupancy("a", "ta", period("2025-01-01")),
                Occupancy("b", "tb", period("2025-01-01")),
                Occupancy("c", "tc", period("2025-01-01")),
            ),
            costs=(CostItem("c", "Müll", cents(100), AllocationKey.AREA),),
        )
    )
    assert [(line.tenancy_id, int(line.amount)) for line in result.lines] == [
        ("ta", 33),
        ("tb", 33),
        ("tc", 33),
        (None, 1),
    ]
    assert result.lines[-1].weight == Decimal(0)


def test_credit_and_zero_denominator_keep_the_owner_residual() -> None:
    result = calculate_nk_statement(
        NkInput(
            billing_period=period("2025-01-01", "2025-01-02"),
            units=(UnitBasis("a", 100),),
            occupancies=(Occupancy("a", None, period("2025-01-01")),),
            costs=(CostItem("credit", "Gutschrift", cents(-7_400), AllocationKey.AREA),),
        )
    )
    assert [(line.tenancy_id, int(line.amount)) for line in result.lines] == [(None, -7_400)]
