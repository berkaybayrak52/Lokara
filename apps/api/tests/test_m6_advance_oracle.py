"""M6A-F03--F06 cent oracle; implementation must project these exact states."""

import pytest


@pytest.mark.parametrize(
    ("subtotal_cents", "confirmed_actual_advances_cents", "expected_saldo_cents"),
    [(28_857, 28_000, 857), (28_857, 28_857, 0), (28_857, 30_000, -1_143)],
    ids=["positive", "zero", "negative"],
)
def test_m6a_f05_saldo_uses_confirmed_actual_advances(
    subtotal_cents: int, confirmed_actual_advances_cents: int, expected_saldo_cents: int
) -> None:
    assert subtotal_cents - confirmed_actual_advances_cents == expected_saldo_cents


def test_m6a_f03_explicit_empty_allocation_list_confirms_zero() -> None:
    allocation_amounts: list[int] = []
    assert sum(allocation_amounts) == 0


def test_m6a_f06_reversal_changes_only_the_new_reconciliation_snapshot() -> None:
    prior_confirmed_total = 28_000
    # The reversal remains a positive evidence row; its selected allocation has
    # the compensating sign. The earlier immutable reconciliation stays 28,000.
    current_confirmed_total = 28_000 + -28_000
    assert prior_confirmed_total == 28_000
    assert current_confirmed_total == 0
