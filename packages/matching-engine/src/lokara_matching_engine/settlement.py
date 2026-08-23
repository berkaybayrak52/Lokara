"""Settlement — `docs/15` § 5.1, §§ 362/366/367 BGB, CSV rows 169-170, 174-176.

Scoring and settlement are separate systems that happen to run one after the other.
`docs/15` § 5.1, last line: *"The statutory order in this section is independent from the
scoring conventions in § 4.  A high confidence never changes § 366/§ 367 ordering."*
Nothing in this module reads a confidence, a signal or a decision.

Order, and it is not negotiable:

1. a purpose designation naming a period or receivable wins (§ 366 Abs. 1 BGB, row 176);
2. otherwise Page 08 FIFO — receivables due at `bank_booking_date` before not-due ones,
   then older `due_date` first (§ 366 Abs. 2 BGB, row 174);
3. within one debt, costs, then interest, then principal (§ 367 BGB, row 170);
4. an exact payment settles (§ 362 BGB, row 175), a partial payment leaves `partial`, and
   an overpayment repeats the order across further receivables until any final remainder
   becomes renter credit.

`docs/15` § 9: V1 does not pay renter credit out.  There is deliberately no payout field
on `SettlementResult`, and a designation naming a period with no receivable does not
invent one — the amount becomes credit (`BANKMATCH-F08`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from .inputs import (
    STATUS_PARTIAL,
    STATUS_SETTLED,
    BankTransactionInput,
    ReceivableInput,
)
from .split import split_principal


@dataclass(frozen=True, slots=True)
class Allocation:
    """One immutable payment-ledger allocation against one debt (`docs/15` §§ 5.1-5.3).

    Both the pre-payment and the post-payment projection are recorded.  The ledger is
    append-only: a reversal appends compensating entries and restores the projection from
    the `*_before` fields, it never edits or deletes this row (`docs/15` § 5.3).
    """

    receivable_id: str
    renter_id: str
    account_id: str
    expected_cents: int
    costs_cents: int
    interest_cents: int
    principal_cents: int
    principal_components: tuple[int, ...]
    open_cents: int
    open_costs_cents: int
    open_interest_cents: int
    status: str
    open_cents_before: int
    open_costs_cents_before: int
    open_interest_cents_before: int
    status_before: str

    @property
    def assigned_cents(self) -> int:
        """Everything this allocation applied to the debt (§ 367 order, all three tiers)."""
        return self.costs_cents + self.interest_cents + self.principal_cents


@dataclass(frozen=True, slots=True)
class SettlementResult:
    """The allocations of one confirmed or Auto-Matched transaction, plus the remainder.

    `assigned + credit == amount` holds by construction.  There is no payout field:
    `docs/15` § 9 excludes paying renter credit out in V1.
    """

    allocations: tuple[Allocation, ...]
    credit_cents: int

    @property
    def assigned_cents(self) -> int:
        return sum(allocation.assigned_cents for allocation in self.allocations)


def _fifo_key(receivable: ReceivableInput, reference: date) -> tuple[int, date, str]:
    """Page 08 FIFO: due before not-due, then older `due_date` first.

    `reference` is the transaction's `bank_booking_date` — *not* `finapi_booking_date`
    (`docs/15` § 3.1).  The two differ in the fixtures precisely so an implementation that
    reads the provider's own booking date is caught.  The receivable ID closes the key so
    two debts due on the same day always order the same way.
    """
    return (0 if receivable.due_date <= reference else 1, receivable.due_date, receivable.id)


def _ordered_receivables(
    transaction: BankTransactionInput,
    receivables: Sequence[ReceivableInput],
    designated_period: str | None,
) -> list[ReceivableInput]:
    """§ 366 Abs. 1 before § 366 Abs. 2: the debtor's designation, then FIFO.

    Cross-account receivables are dropped first: a match never moves money between
    accounts, and never between renters (`docs/15` § 6).

    A designation naming a period for which no receivable exists selects nothing; the
    remaining debts still follow FIFO and any leftover becomes credit (`docs/15` § 3.2:
    the credit arises "after other valid allocation").
    """
    in_account = [
        receivable for receivable in receivables if receivable.account_id == transaction.account_id
    ]
    reference = transaction.bank_booking_date
    designated = [
        receivable
        for receivable in in_account
        if designated_period is not None and receivable.period == designated_period
    ]
    designated_ids = {receivable.id for receivable in designated}
    rest = [receivable for receivable in in_account if receivable.id not in designated_ids]
    return sorted(designated, key=lambda row: _fifo_key(row, reference)) + sorted(
        rest, key=lambda row: _fifo_key(row, reference)
    )


def _allocate(receivable: ReceivableInput, available_cents: int) -> Allocation | None:
    """Apply cents to one debt in the § 367 order: costs, then interest, then principal."""
    remaining = available_cents
    costs = min(remaining, max(receivable.open_costs_cents, 0))
    remaining -= costs
    interest = min(remaining, max(receivable.open_interest_cents, 0))
    remaining -= interest
    principal = min(remaining, max(receivable.open_principal_cents, 0))
    if costs + interest + principal == 0:
        return None

    open_costs_after = receivable.open_costs_cents - costs
    open_interest_after = receivable.open_interest_cents - interest
    open_after = receivable.open_cents - principal
    fully_paid = open_after == 0 and open_costs_after == 0 and open_interest_after == 0
    return Allocation(
        receivable_id=receivable.id,
        renter_id=receivable.renter_id,
        account_id=receivable.account_id,
        expected_cents=receivable.expected_cents,
        costs_cents=costs,
        interest_cents=interest,
        principal_cents=principal,
        principal_components=split_principal(
            receivable.principal_components, principal, receivable.expected_cents
        ),
        open_cents=open_after,
        open_costs_cents=open_costs_after,
        open_interest_cents=open_interest_after,
        # § 362 BGB fulfils the debt only when nothing is left open in any § 367 tier.
        status=STATUS_SETTLED if fully_paid else STATUS_PARTIAL,
        open_cents_before=receivable.open_cents,
        open_costs_cents_before=receivable.open_costs_cents,
        open_interest_cents_before=receivable.open_interest_cents,
        status_before=receivable.status,
    )


def settle(
    transaction: BankTransactionInput,
    receivables: Sequence[ReceivableInput],
    *,
    designated_period: str | None = None,
) -> SettlementResult:
    """Allocate one positive transaction over the renter's debts (`docs/15` § 5.1).

    Call this only after an Auto-Match or an explicit user confirmation.  A negative
    amount belongs on the reversal path (`reverse`); a zero amount is retained for import
    audit and allocates nothing (`docs/15` § 3.1).
    """
    if transaction.amount_cents < 0:
        raise ValueError(
            "a negative amount is a return and belongs on the reversal path of "
            f"docs/15 section 5.3, not in settle(): {transaction.amount_cents}"
        )

    allocations: list[Allocation] = []
    remaining = transaction.amount_cents
    for receivable in _ordered_receivables(transaction, receivables, designated_period):
        if remaining == 0:
            break
        allocation = _allocate(receivable, remaining)
        if allocation is None:
            continue
        allocations.append(allocation)
        remaining -= allocation.assigned_cents

    # "any final remainder becomes renter credit.  It is not paid out by Lokara."
    return SettlementResult(allocations=tuple(allocations), credit_cents=remaining)
