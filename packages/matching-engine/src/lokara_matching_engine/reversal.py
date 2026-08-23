"""Reversal — `docs/15` § 5.3.

A negative amount or a SEPA-return code enters this path.  Three things it deliberately
does *not* do, all of them stated by `docs/15` § 5.3:

- it does not rescore.  A `ReversalResult` carries no candidates, signals, confidence or
  decision, because the original match already happened and is not up for reassessment;
- it does not create a replacement positive payment.  Every compensating entry is <= 0;
- it does not edit or delete the original allocations.  The payment ledger is append-only
  (`CLAUDE.md` § 3.2), so the reversal appends entries that negate the originals exactly
  and restores the receivable *projection* from the values the allocation recorded.

Resolution order is fixed: E2E or mandate reference first, and only then the Page 08
fallback `(IBAN, amount, date)` — within the same account.  `BANKMATCH-F06` hands the
engine a return that matches both ways at once, precisely so that the "only then" is
provable.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from .inputs import BankTransactionInput, normalize_iban
from .settlement import Allocation, SettlementResult

#: `docs/15` § 5.3 resolution channels, most specific first.
RESOLUTION_END_TO_END_REFERENCE: Final = "end_to_end_reference"
RESOLUTION_MANDATE_REFERENCE: Final = "counterpart_mandate_reference"
RESOLUTION_IBAN_AMOUNT_DATE: Final = "iban_amount_date"

#: Handed to the Page 05 guard/Wächter mechanism (`docs/15` § 5.3).
GUARD_PAYMENT_RETURNED: Final = "payment_returned"


@dataclass(frozen=True, slots=True)
class CompensatingEntry:
    """An appended ledger entry that negates one original allocation exactly."""

    receivable_id: str
    renter_id: str
    account_id: str
    amount_cents: int
    costs_cents: int
    interest_cents: int
    principal_cents: int
    principal_components: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class RestoredReceivable:
    """The receivable projection as it stood before the reversed allocation.

    `status` is the *recorded* pre-payment status, not a status re-derived from the
    restored amounts.  Re-deriving it would have to guess whether an earlier partial
    payment existed, and guessing is what this engine does not do.
    """

    receivable_id: str
    open_cents: int
    open_costs_cents: int
    open_interest_cents: int
    status: str


@dataclass(frozen=True, slots=True)
class ReversalResult:
    """The append-only outcome of one return (`docs/15` § 5.3).

    No `decision`, `signals`, `confidence` or `ranked_candidates`: "Do not rescore".
    """

    resolution: str
    compensating_entries: tuple[CompensatingEntry, ...]
    restored_receivables: tuple[RestoredReceivable, ...]
    guard_signal: str = GUARD_PAYMENT_RETURNED


def _resolve(returned: BankTransactionInput, original: BankTransactionInput) -> str:
    """Reference first, Page 08 `(IBAN, amount, date)` fallback "only then"."""
    if (
        returned.end_to_end_reference is not None
        and returned.end_to_end_reference == original.end_to_end_reference
    ):
        return RESOLUTION_END_TO_END_REFERENCE
    if (
        returned.counterpart_mandate_reference is not None
        and returned.counterpart_mandate_reference == original.counterpart_mandate_reference
    ):
        return RESOLUTION_MANDATE_REFERENCE

    counterpart = normalize_iban(returned.counterpart_iban)
    same_iban = bool(counterpart) and counterpart == normalize_iban(original.counterpart_iban)
    same_amount = -returned.amount_cents == original.amount_cents
    # `docs/15` names the fallback triple but not which normalized date it compares, so
    # both dates the provider gives us must agree before the fallback is allowed to fire.
    same_date = (
        returned.bank_booking_date == original.bank_booking_date
        and returned.value_date == original.value_date
    )
    if same_iban and same_amount and same_date:
        return RESOLUTION_IBAN_AMOUNT_DATE

    raise ValueError(
        "the returned movement resolves to no original match: neither the E2E nor the "
        "mandate reference matches, and the docs/15 section 5.3 fallback (IBAN, amount, "
        "date) does not either. Refusing to reverse a payment that was not identified."
    )


def _compensate(allocation: Allocation) -> CompensatingEntry:
    return CompensatingEntry(
        receivable_id=allocation.receivable_id,
        renter_id=allocation.renter_id,
        account_id=allocation.account_id,
        amount_cents=-allocation.assigned_cents,
        costs_cents=-allocation.costs_cents,
        interest_cents=-allocation.interest_cents,
        principal_cents=-allocation.principal_cents,
        principal_components=tuple(-component for component in allocation.principal_components),
    )


def _restore(allocation: Allocation) -> RestoredReceivable:
    return RestoredReceivable(
        receivable_id=allocation.receivable_id,
        open_cents=allocation.open_cents_before,
        open_costs_cents=allocation.open_costs_cents_before,
        open_interest_cents=allocation.open_interest_cents_before,
        status=allocation.status_before,
    )


def reverse(
    returned: BankTransactionInput,
    original: BankTransactionInput,
    original_settlements: Sequence[SettlementResult],
) -> ReversalResult:
    """Reverse the allocations of one original payment (`docs/15` § 5.3).

    Raises:
        ValueError: the return is not negative, crosses an account boundary, or resolves
            to no original match.
    """
    if returned.account_id != original.account_id:
        raise ValueError(
            "docs/15 sections 5.3 and 6: a reversal is resolved within the same account "
            f"({returned.account_id!r} != {original.account_id!r})"
        )
    if returned.amount_cents >= 0:
        raise ValueError(
            "the reversal path expects the signed return amount from docs/15 section "
            f"3.1, which is negative: {returned.amount_cents}"
        )

    resolution = _resolve(returned, original)
    allocations = tuple(
        allocation for settlement in original_settlements for allocation in settlement.allocations
    )
    reversed_total = -sum(allocation.assigned_cents for allocation in allocations)
    if reversed_total != returned.amount_cents:
        raise ValueError(
            "a return reverses the original allocations exactly; it is never partially "
            f"absorbed or topped up ({reversed_total} != {returned.amount_cents})"
        )

    return ReversalResult(
        resolution=resolution,
        compensating_entries=tuple(_compensate(allocation) for allocation in allocations),
        restored_receivables=tuple(_restore(allocation) for allocation in allocations),
        guard_signal=GUARD_PAYMENT_RETURNED,
    )
