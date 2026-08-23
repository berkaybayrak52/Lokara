"""Principal-component split — `docs/15` § 5.2, CSV row 173.

A full principal payment copies the nominal components.  A partial principal payment `P`
is spread proportionally and the cent remainder is reconciled by Largest Remainder:

```text
raw_component = nominal_component * P / expected_cents
component_paid = whole-cent proportional share
reconcile the cent remainder by Largest Remainder
```

`BANKMATCH-F11`: 100,000 paid against 108,000 expected over (85,000, 15,000, 8,000)
yields (78,704, 13,889, 7,407) and needs no further redistribution.  The paid NK-advance
component feeds the annual actual-advance total Page 01 consumes, so a cent lost here is
a cent wrong on next year's statement — the reconciled parts sum *exactly* to `P`, and
that is asserted, not hoped for.

All arithmetic is integer.  The proportional share is `nominal * paid // expected` and
the fractional remainder is the exact integer modulus over the common denominator
`expected_cents`, so no `Decimal` rounding mode and certainly no `float` is involved.

This module is also where the engine refuses.  See `errors.TieBreakUnspecifiedError`.
"""

from __future__ import annotations

from collections.abc import Sequence

from .errors import TieBreakUnspecifiedError


def split_principal(
    nominal_components: Sequence[int],
    paid_principal_cents: int,
    expected_cents: int,
) -> tuple[int, ...]:
    """Spread `paid_principal_cents` over `nominal_components` (`docs/15` § 5.2).

    `docs/15` § 3.2 requires the nominal components to sum to `expected_cents`; that is
    enforced here because it is exactly what makes `sum(result) == paid_principal_cents`
    an identity rather than a hope.

    Raises:
        TieBreakUnspecifiedError: two components have the same fractional remainder and
            the cent could go to either.  No authoritative source states which one wins,
            so the engine stops instead of inventing a distribution convention.
        ValueError: the inputs are not a valid § 3.2 component vector.
    """
    nominal = tuple(nominal_components)
    if any(component < 0 for component in nominal):
        raise ValueError(f"principal components must be non-negative: {nominal!r}")
    if paid_principal_cents < 0:
        raise ValueError(f"paid principal must be non-negative: {paid_principal_cents!r}")
    if expected_cents <= 0:
        raise ValueError(f"expected_cents must be positive: {expected_cents!r}")
    if sum(nominal) != expected_cents:
        raise ValueError(
            "docs/15 section 3.2: the nominal components must sum to expected_cents "
            f"({sum(nominal)} != {expected_cents})"
        )
    if paid_principal_cents > expected_cents:
        raise ValueError(
            "a principal split never exceeds the nominal debt; an overpayment moves to "
            f"the next receivable under docs/15 section 5.1 ({paid_principal_cents} > "
            f"{expected_cents})"
        )

    if paid_principal_cents == 0:
        return tuple(0 for _ in nominal)
    if paid_principal_cents == expected_cents:
        # "A full principal payment copies nominal components" (`docs/15` § 5.2).
        return nominal

    scaled = tuple(component * paid_principal_cents for component in nominal)
    whole = tuple(value // expected_cents for value in scaled)
    remainders = tuple(value % expected_cents for value in scaled)
    cents_to_distribute = paid_principal_cents - sum(whole)
    if cents_to_distribute == 0:
        return whole

    order = sorted(range(len(nominal)), key=lambda index: remainders[index], reverse=True)
    boundary = order[cents_to_distribute - 1]
    contender = order[cents_to_distribute]
    if remainders[boundary] == remainders[contender]:
        raise TieBreakUnspecifiedError(
            "Largest Remainder tie: components "
            f"{boundary} and {contender} share the fractional remainder "
            f"{remainders[boundary]}/{expected_cents} and only "
            f"{cents_to_distribute} cent(s) remain to distribute. docs/15 section 5.2: "
            "'Page 08 does not specify the tie-break between equal fractional "
            "remainders; that missing deterministic convention must be added to the "
            "authoritative source before a future implementation claims the unexercised "
            "tie branch.' Refusing rather than inventing an order for renter money "
            f"(nominal={nominal!r}, paid={paid_principal_cents}, "
            f"expected={expected_cents})."
        )

    winners = frozenset(order[:cents_to_distribute])
    reconciled = tuple(value + (1 if index in winners else 0) for index, value in enumerate(whole))
    if sum(reconciled) != paid_principal_cents:  # pragma: no cover - guards the identity
        raise ValueError(
            "the reconciled components must sum exactly to the paid principal "
            f"({sum(reconciled)} != {paid_principal_cents}); a cent lost here is a cent "
            "wrong on the Page 01 actual-advance total"
        )
    return reconciled
