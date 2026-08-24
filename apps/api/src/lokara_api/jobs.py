"""M6-C3b: the three scheduled job entrypoints (`docs/15` § 5.6).

Three properties hold for every function here, and each is load-bearing:

* **`now`/`today` are inputs.** Nothing reads the clock. A deadline that depends on
  when the worker happened to wake is not reproducible evidence, and `docs/12` § 3
  states the same rule for guards.
* **One account per run.** Each function takes an explicit `account_id` and runs on
  an already RLS-scoped session. `account` is scoped by its own id, so no
  cross-account enumeration exists — and none is added: `app_bootstrap_contexts`
  stays the only pre-context read (`CLAUDE.md` § 3.3). The caller supplies the ids.
* **Only sync writes.** `expire_bank_consents` and `watch_deadlines` are reports.
  "Cleanup" stops the pull; it never deletes a `bank_transaction`, which is
  append-only under § 147 AO.

The watcher deliberately applies no `docs/12` guard rule, threshold, warning copy or
escalation. W1–W8 and fixtures `12-F01`–`12-F24` belong to the guard-foundation
slice; restating one of them here would create a second, unversioned copy of a legal
rule.

No worker is installed. `StubScheduler` in `lokara_adapters` decides what is due;
this module decides what a due job does (`docs/01` D7).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Final

from lokara_adapters import BankGateway
from lokara_db import BankAccount, BankTransaction, Receivable
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .bank_sync import ConsentExpiredError, import_transactions, require_aware
from .deps import job_account_session
from .matching_service import MatchingConflictError, MatchingNotFoundError, run_match

#: PSD2 RTS Art. 10 (Delegated Regulation (EU) 2018/389, as amended) caps how long
#: an AIS consent may stand before the renter re-authenticates. The authoritative
#: `Rechtsstand-Register.csv` carries **no** consent/PSD2/SCA/AIS row, so this is a
#: Lokara `Konvention`, `verify-before-production`, `Rechtsstand 08/2026`, resting on
#: an unverified primary source. Nothing defaults an expiry from it: the pull reads
#: only the stored `consent_expires_at`, and this value is a ceiling check alone.
AIS_CONSENT_MAX_DAYS: Final = 180

_SETTLED = "settled"


@dataclass(frozen=True)
class JobRefusal:
    """One transaction the matching service refused, and why.

    A refusal is evidence, not a failure to hide: `docs/15` § 5.2's missing
    tie-break and § 5.3's unresolvable return both surface here rather than being
    resolved by an invented rule.
    """

    bank_transaction_id: str
    reason: str


@dataclass(frozen=True)
class BankAccountSyncResult:
    """What one bank account's sync did.

    `skipped_reason` is `None`, `consent_missing` or `consent_expired`; a skipped
    account pulled nothing at all, so every count below it is zero.
    """

    bank_account_id: str
    skipped_reason: str | None
    imported: int
    skipped_as_duplicate: int
    auto_matched: int
    needs_review: int
    unmatched: int
    deduped: int
    reversed_payments: int
    settled: int
    refused: tuple[JobRefusal, ...]


@dataclass(frozen=True)
class SyncResult:
    account_id: str
    bank_accounts: tuple[BankAccountSyncResult, ...]


@dataclass(frozen=True)
class ConsentFinding:
    """`state` is `missing`, `expired` or `exceeds_max_window`.

    The third is a ceiling check against the flagged 180-day convention: a provider
    that hands back a longer validity than PSD2 permits is reported, never trimmed.
    """

    bank_account_id: str
    display_name: str
    state: str
    expires_at: datetime | None


@dataclass(frozen=True)
class OverdueReceivable:
    """A fact, not a warning. No § 543 stage, threshold or German copy is applied."""

    receivable_id: str
    renter_id: str
    period: str
    due_date: date
    days_overdue: int
    open_cents: int


@dataclass(frozen=True)
class DeadlineWatchResult:
    account_id: str
    overdue_receivables: tuple[OverdueReceivable, ...]
    consent_findings: tuple[ConsentFinding, ...]


def _bank_accounts(session: Session, account_id: str) -> Sequence[BankAccount]:
    # RLS already scopes this; the explicit predicate is the app-logic half that
    # CLAUDE.md rule 3 requires independently of the database backstop.
    return session.scalars(
        select(BankAccount).where(BankAccount.account_id == account_id).order_by(BankAccount.id)
    ).all()


@dataclass(frozen=True)
class _ImportPhase:
    """What one bank account's pull produced, before anything is matched."""

    skipped_reason: str | None
    imported: int
    skipped_as_duplicate: int
    transaction_ids: tuple[str, ...]


@dataclass
class _Tally:
    auto_matched: int = 0
    needs_review: int = 0
    unmatched: int = 0
    deduped: int = 0
    reversed_payments: int = 0
    settled: int = 0
    refused: list[JobRefusal] = field(default_factory=list)


# Migration 0021 makes the three reconciliation constraints DEFERRABLE INITIALLY
# DEFERRED, because a settlement inserts its ledger entry before its allocations and
# is only consistent once both are in. Under C3a that was harmless: one request was
# one `run_match` was one transaction, so the check ran at the same COMMIT. A job
# matches many transactions in one transaction, and a deferred violation would
# surface at the outer COMMIT and abort every import and settlement in the run.
# Forcing the check inside each SAVEPOINT puts the failure back where the run can
# bound it. Exactly these three constraints are deferrable, so `ALL` names them and
# nothing else, and the reset restores their declared state for the next transaction.
_ALL_IMMEDIATE = text("SET CONSTRAINTS ALL IMMEDIATE")
_ALL_DEFERRED = text("SET CONSTRAINTS ALL DEFERRED")


def _match_one(session: Session, transaction: BankTransaction, tally: _Tally) -> None:
    """Match one transaction inside its own SAVEPOINT, and count what happened."""
    savepoint = session.begin_nested()
    try:
        result = run_match(session, transaction.id)
        session.execute(_ALL_IMMEDIATE)
        session.execute(_ALL_DEFERRED)
    except (MatchingConflictError, MatchingNotFoundError, IntegrityError) as error:
        savepoint.rollback()
        tally.refused.append(JobRefusal(bank_transaction_id=transaction.id, reason=str(error)))
        return
    savepoint.commit()

    decision = result.get("decision")
    if decision == "auto_match":
        tally.auto_matched += 1
    elif decision == "needs_review":
        tally.needs_review += 1
    elif decision == "unmatched":
        tally.unmatched += 1
    elif decision == "deduped":
        tally.deduped += 1
    if result.get("event") is not None:
        tally.reversed_payments += 1
    if result.get("ledger_entry_id") is not None:
        tally.settled += 1


def _import_phase(
    session: Session,
    *,
    account_id: str,
    bank_account_id: str,
    window_from: date,
    window_to: date,
    gateway: BankGateway,
    now: datetime,
) -> _ImportPhase:
    try:
        outcome = import_transactions(
            session,
            account_id=account_id,
            bank_account_id=bank_account_id,
            window_from=window_from,
            window_to=window_to,
            gateway=gateway,
            now=now,
        )
    except ConsentExpiredError as error:
        return _ImportPhase(
            skipped_reason=error.reason,
            imported=0,
            skipped_as_duplicate=0,
            transaction_ids=(),
        )
    return _ImportPhase(
        skipped_reason=None,
        imported=outcome.imported,
        skipped_as_duplicate=outcome.skipped_as_duplicate,
        transaction_ids=outcome.imported_transaction_ids,
    )


def sync_bank_transactions(
    session: Session,
    *,
    account_id: str,
    window_from: date,
    window_to: date,
    gateway: BankGateway,
    now: datetime,
) -> SyncResult:
    """Pull every connected bank account of one account, then match what arrived.

    Matching runs here on purpose: `docs/15` § 4 defines `AUTO_MATCH` as the
    automatic channel, so a scheduled sync settles it. `NEEDS_REVIEW` still moves no
    money before a human confirmation, which is the property the whole contract
    rests on.

    Import and matching are two phases, not one loop per bank account. `docs/15`
    § 5.1 settles a renter's receivables FIFO across *all* of their payments, and a
    renter's rent and their garage may arrive on two different accounts — so
    matching one bank account to completion before opening the next would order
    settlement by `bank_account_id` and only then by the date the bank booked.
    """
    require_aware(now, "now")
    phases = {
        bank_account.id: _import_phase(
            session,
            account_id=account_id,
            bank_account_id=bank_account.id,
            window_from=window_from,
            window_to=window_to,
            gateway=gateway,
            now=now,
        )
        for bank_account in _bank_accounts(session, account_id)
    }

    imported_ids = [
        transaction_id for phase in phases.values() for transaction_id in phase.transaction_ids
    ]
    tallies = {bank_account_id: _Tally() for bank_account_id in phases}
    for transaction in session.scalars(
        select(BankTransaction)
        .where(
            BankTransaction.account_id == account_id,
            BankTransaction.id.in_(imported_ids),
        )
        .order_by(BankTransaction.bank_booking_date, BankTransaction.provider_transaction_id)
    ).all():
        _match_one(session, transaction, tallies[transaction.bank_account_id])

    return SyncResult(
        account_id=account_id,
        bank_accounts=tuple(
            BankAccountSyncResult(
                bank_account_id=bank_account_id,
                skipped_reason=phases[bank_account_id].skipped_reason,
                imported=phases[bank_account_id].imported,
                skipped_as_duplicate=phases[bank_account_id].skipped_as_duplicate,
                auto_matched=tallies[bank_account_id].auto_matched,
                needs_review=tallies[bank_account_id].needs_review,
                unmatched=tallies[bank_account_id].unmatched,
                deduped=tallies[bank_account_id].deduped,
                reversed_payments=tallies[bank_account_id].reversed_payments,
                settled=tallies[bank_account_id].settled,
                refused=tuple(tallies[bank_account_id].refused),
            )
            for bank_account_id in sorted(phases)
        ),
    )


def expire_bank_consents(
    session: Session, *, account_id: str, now: datetime
) -> tuple[ConsentFinding, ...]:
    """Report the bank accounts that may no longer be pulled. Writes nothing.

    Reconsent is a landlord action through the provider, so the job's whole job is
    to name the accounts. It deletes no evidence and revokes nothing itself; the
    pull is already blocked by the same stored expiry in `bank_sync`.
    """
    require_aware(now, "now")
    ceiling = now + timedelta(days=AIS_CONSENT_MAX_DAYS)
    findings: list[ConsentFinding] = []
    for bank_account in _bank_accounts(session, account_id):
        expires_at = bank_account.consent_expires_at
        if expires_at is None:
            state = "missing"
        elif expires_at <= now:
            state = "expired"
        elif expires_at > ceiling:
            state = "exceeds_max_window"
        else:
            continue
        findings.append(
            ConsentFinding(
                bank_account_id=bank_account.id,
                display_name=bank_account.display_name,
                state=state,
                expires_at=expires_at,
            )
        )
    return tuple(findings)


def watch_deadlines(
    session: Session, *, account_id: str, today: date, now: datetime
) -> DeadlineWatchResult:
    """Report the M6-owned deadline facts. Writes nothing.

    An overdue receivable is stated as days and cents. It carries no § 543 stage, no
    threshold comparison and no warning text — those are `docs/12` W3, and they ship
    with the guard engine, versioned, not as a copy made here.
    """
    require_aware(now, "now")
    rows = session.scalars(
        select(Receivable)
        .where(
            Receivable.account_id == account_id,
            Receivable.status != _SETTLED,
            Receivable.due_date < today,
        )
        .order_by(Receivable.due_date, Receivable.id)
    ).all()
    return DeadlineWatchResult(
        account_id=account_id,
        overdue_receivables=tuple(
            OverdueReceivable(
                receivable_id=row.id,
                renter_id=row.renter_id,
                period=row.period,
                due_date=row.due_date,
                days_overdue=(today - row.due_date).days,
                open_cents=row.open_cents,
            )
            for row in rows
        ),
        consent_findings=expire_bank_consents(session, account_id=account_id, now=now),
    )


def run_for_accounts[T](
    engine: Engine, account_ids: Sequence[str], job: Callable[[Session, str], T]
) -> tuple[T, ...]:
    """Run one job once per account id, each in its own RLS-scoped transaction.

    The ids come from the caller. A scheduler that wanted to discover them would
    need a second pre-context read, and `CLAUDE.md` § 3.3 allows exactly one —
    `docs/15` § 5.6 records that gap as open rather than closing it here.

    The session comes from `deps.job_account_session` rather than
    `account_scoped_session` directly: `scripts/check_pre_context_reads.py` keeps
    every RLS session boundary in `deps.py`, and a job is not an exception to that.
    """
    results: list[T] = []
    for account_id in account_ids:
        with job_account_session(engine, account_id) as session:
            results.append(job(session, account_id))
    return tuple(results)
