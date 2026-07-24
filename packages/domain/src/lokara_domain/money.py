"""Money primitives.

All money in Lokara is integer cents. Floats never touch money; intermediate
math uses decimal.Decimal exclusively.
"""

from collections.abc import Sequence
from decimal import Decimal
from typing import NewType

Cents = NewType("Cents", int)

ZERO_CENTS = Cents(0)


class NonIntegerCentsError(ValueError):
    def __init__(self, value: object) -> None:
        super().__init__(f"Money must be integer cents, got: {value!r}")


def cents(value: int) -> Cents:
    """Validates that a value is a plain integer cent amount (bools rejected)."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise NonIntegerCentsError(value)
    return Cents(value)


def add_cents(*values: Cents) -> Cents:
    return Cents(sum(values))


def format_eur(value: Cents) -> str:
    """Formats integer cents as a German amount string, e.g. 120000 -> "1.200,00 €".

    Deterministic manual formatting (no locale dependency); non-breaking space
    before the euro sign, as German convention requires.
    """
    sign = "-" if value < 0 else ""
    euros, rest = divmod(abs(int(value)), 100)
    grouped = f"{euros:,}".replace(",", ".")
    return f"{sign}{grouped},{rest:02d} €"


def distribute_cents(total: Cents, weights: Sequence[Decimal | int]) -> list[Cents]:
    """Largest-remainder allocation: splits ``total`` cents proportionally to
    ``weights`` so the parts always reconcile to ``total`` exactly.

    Deterministic: quotas are computed with Decimal (no float drift); leftover
    cents go to the largest fractional remainders, ties broken by lowest index.
    """
    if len(weights) == 0:
        raise ValueError("distribute_cents requires at least one weight")
    decimal_weights = [w if isinstance(w, Decimal) else Decimal(w) for w in weights]
    if any(not w.is_finite() or w < 0 for w in decimal_weights):
        raise ValueError("distribute_cents weights must be finite and >= 0")
    weight_sum = sum(decimal_weights, Decimal(0))
    if weight_sum == 0:
        raise ValueError("distribute_cents requires a positive weight sum")

    quotas = [Decimal(total) * w / weight_sum for w in decimal_weights]
    floors = [int(q // 1) for q in quotas]
    remainder = int(total) - sum(floors)

    # Rank by fractional remainder descending; ties broken by lowest index.
    by_remainder = sorted(
        range(len(quotas)), key=lambda i: (quotas[i] - (quotas[i] // 1), -i), reverse=True
    )
    for i in by_remainder[:remainder]:
        floors[i] += 1

    result = [Cents(f) for f in floors]
    assert sum(result) == total  # reconciliation is the whole game — never ship without it
    return result
