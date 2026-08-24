"""The one AIS pull: consent precondition, provider-ID dedupe, normalized insert.

`docs/15` § 3.1 has exactly one rule for a re-import — the same
`provider_transaction_id` on the same bank account is the movement already
processed, so it creates no second row — and exactly one identity,
`(account_id, bank_account_id, provider_transaction_id)`. That rule lived inside
the owner endpoint until M6-C3b needed it from a scheduled job too. It is here so
both callers share one truth rather than two loops that can drift.

`is_potential_duplicate` is not this rule and is never merged with it: it keeps
its transaction and forces Review.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from lokara_adapters import BankGateway
from lokara_db import BankAccount, BankTransaction, new_id
from sqlalchemy import select
from sqlalchemy.orm import Session


class BankAccountNotFoundError(LookupError):
    """The named bank account does not exist in this account's scope."""


class ConsentExpiredError(ValueError):
    """No valid PSD2 consent stands, so no pull may happen.

    `reason` is `consent_missing` or `consent_expired`. A missing expiry is refused
    rather than assumed: `docs/15` § 5.6 keeps the 180-day window a flagged
    convention, and defaulting one here would make that convention Lokara's answer
    on the exact edge — a bank pull — where it is legally load-bearing.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class ImportOutcome:
    """What one pull did. `imported_transaction_ids` is what the caller may match."""

    imported: int
    skipped_as_duplicate: int
    imported_transaction_ids: tuple[str, ...]


def require_aware(value: datetime, field: str) -> None:
    """Refuse a naive timestamp. Every stored timestamp here is `TIMESTAMPTZ`, so a
    naive one can only have come from a caller's local clock."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware — a naive datetime has no instant")


def import_transactions(
    session: Session,
    *,
    account_id: str,
    bank_account_id: str,
    window_from: date,
    window_to: date,
    gateway: BankGateway,
    now: datetime,
) -> ImportOutcome:
    """Pull `[window_from, window_to)` for one bank account into storage.

    The session must already carry its RLS account context; `account_id` scopes the
    same rows in application logic, which `CLAUDE.md` rule 3 requires independently.
    """
    require_aware(now, "now")
    bank_account = session.scalar(
        select(BankAccount).where(
            BankAccount.id == bank_account_id,
            BankAccount.account_id == account_id,
        )
    )
    if bank_account is None:
        raise BankAccountNotFoundError(bank_account_id)
    if bank_account.consent_expires_at is None:
        raise ConsentExpiredError("consent_missing")
    if bank_account.consent_expires_at <= now:
        raise ConsentExpiredError("consent_expired")

    known = set(
        session.scalars(
            select(BankTransaction.provider_transaction_id).where(
                # Both halves, not one: RLS scopes this already, but the dedupe set
                # is what decides whether a movement is skipped or booked twice, and
                # CLAUDE.md rule 3 wants that decision scoped in app logic too.
                BankTransaction.account_id == account_id,
                BankTransaction.bank_account_id == bank_account_id,
            )
        ).all()
    )

    imported: list[str] = []
    skipped = 0
    for normalized in gateway.list_transactions(bank_account_id, window_from, window_to):
        if normalized.provider_transaction_id in known:
            skipped += 1
            continue
        transaction_id = new_id()
        session.add(
            BankTransaction(
                id=transaction_id,
                account_id=account_id,
                bank_account_id=bank_account_id,
                provider_transaction_id=normalized.provider_transaction_id,
                amount_cents=normalized.amount_cents,
                bank_booking_date=normalized.bank_booking_date,
                finapi_booking_date=normalized.finapi_booking_date,
                value_date=normalized.value_date,
                counterpart_iban=normalized.counterpart_iban,
                counterpart_name=normalized.counterpart_name,
                purpose=normalized.purpose,
                end_to_end_reference=normalized.end_to_end_reference,
                counterpart_mandate_reference=normalized.counterpart_mandate_reference,
                bank_transaction_code=normalized.bank_transaction_code,
                provider_type=normalized.provider_type,
                is_potential_duplicate=normalized.is_potential_duplicate,
            )
        )
        known.add(normalized.provider_transaction_id)
        imported.append(transaction_id)
    session.flush()
    return ImportOutcome(
        imported=len(imported),
        skipped_as_duplicate=skipped,
        imported_transaction_ids=tuple(imported),
    )
