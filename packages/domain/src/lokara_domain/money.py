"""Money primitives.

All money in Lokara is integer cents. Floats never touch money; intermediate
math uses decimal.Decimal exclusively.
"""

from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal
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


def distribute_cents_half_up(
    total: Cents, weights: Sequence[Decimal | int], *, residual_index: int
) -> list[Cents]:
    """R1/R5/K9 allocation: every share is `round_half_up` of its own exact
    quota, computed once at assignment; the party at ``residual_index`` receives
    the ``Verteilungsrest`` — ``total - Σ(other shares)`` — instead of its own
    rounded quota.

    That party is the **owner bucket** (K9): a leftover cent may not be handed
    to whichever renter happens to have the largest fraction, because nothing on
    a statement can explain that transfer between tenants; the owner row can be
    explained in one line. Its share may therefore be ±1 ct off its own quota
    and **may be negative** (`01b-F01` verbrauchHz: -1 ct) — that is R5 working,
    not a defect.

    ``sum(shares) == total`` holds by construction, exactly as for the
    largest-remainder :func:`distribute_cents`, which stays for its own callers.

    K9 is a house convention (`Konvention`, verify before production), not a
    norm — no output may present it as one. Spec:
    `docs/03-nk-heating-engines.md` → "Seite 01b … (1) Rounding".
    """
    if len(weights) == 0:
        raise ValueError("distribute_cents_half_up requires at least one weight")
    if not 0 <= residual_index < len(weights):
        raise ValueError(
            f"distribute_cents_half_up residual_index {residual_index} is out of range "
            f"for {len(weights)} weights"
        )
    decimal_weights = [w if isinstance(w, Decimal) else Decimal(w) for w in weights]
    if any(not w.is_finite() or w < 0 for w in decimal_weights):
        raise ValueError("distribute_cents_half_up weights must be finite and >= 0")
    weight_sum = sum(decimal_weights, Decimal(0))
    if weight_sum == 0:
        raise ValueError("distribute_cents_half_up requires a positive weight sum")

    shares = [
        Cents(0)
        if index == residual_index
        # R1: rounded once, at the moment the share is assigned — and R2: from
        # the recomputed exact quotient, never from a rounded factor.
        else Cents(
            int((Decimal(total) * w / weight_sum).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        )
        for index, w in enumerate(decimal_weights)
    ]
    shares[residual_index] = Cents(int(total) - sum(shares))

    assert sum(shares) == total  # the residual is inside the sum, never an exception to it
    return shares
