"""Account-scoped persistence bridge for the pure bank-matching engine.

The engine decides and calculates.  This module locks the database rows, translates
the engine result into immutable evidence and maintains the receivable projection.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime

from lokara_db import (
    BankTransaction,
    IbanHistory,
    MatchConfirmation,
    MatchProposal,
    PaymentAllocation,
    PaymentLedgerEntry,
    Receivable,
    Renter,
    RenterMatchingProfile,
    new_id,
)
from lokara_matching_engine import (
    Allocation,
    BankTransactionInput,
    Decision,
    IbanOwnership,
    ReceivableInput,
    RenterProfileInput,
    SettlementResult,
    TieBreakUnspecifiedError,
    normalize_comparison_text,
    normalize_iban,
    propose,
    reverse,
    settle,
    should_learn_iban,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

type JsonObject = dict[str, object]

_DB_DECISION = {
    Decision.AUTO_MATCH: "AUTO_MATCH",
    Decision.NEEDS_REVIEW: "NEEDS_REVIEW",
    Decision.UNMATCHED: "UNMATCHED",
    Decision.DEDUPED: "DEDUPED",
}
_API_DECISION = {value: key.value for key, value in _DB_DECISION.items()}
_DB_OUTCOME = {
    "confirmed": "CONFIRMED",
    "rejected": "REJECTED",
    "duplicate": "DUPLICATE",
}


class MatchingNotFoundError(LookupError):
    """A resource inside the already-authorized account does not exist."""


class MatchingConflictError(ValueError):
    """The requested money operation cannot be completed without guessing."""


def _normalize_profile_text(value: str) -> str:
    # User-entered German names use the established ASCII search spelling so
    # "MÜLLER-Schmidt" and a bank purpose containing "Mueller" share a form.
    folded = value.casefold().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    return normalize_comparison_text(folded)


def upsert_matching_profile(
    session: Session, renter_id: str, surname: str, payment_code: str | None
) -> JsonObject:
    renter = session.get(Renter, renter_id)
    if renter is None:
        raise MatchingNotFoundError("Mieter nicht gefunden")
    normalized_surname = _normalize_profile_text(surname)
    if not normalized_surname:
        raise MatchingConflictError("Der Nachname darf nicht leer sein.")
    normalized_code = normalize_comparison_text(payment_code) if payment_code is not None else None
    if normalized_code == "":
        normalized_code = None
    profile = session.scalar(
        select(RenterMatchingProfile).where(RenterMatchingProfile.renter_id == renter_id)
    )
    if profile is None:
        profile = RenterMatchingProfile(
            id=new_id(),
            account_id=renter.account_id,
            renter_id=renter_id,
            payment_code=normalized_code,
            normalized_surname=normalized_surname,
        )
        session.add(profile)
    else:
        profile.payment_code = normalized_code
        profile.normalized_surname = normalized_surname
    session.flush()
    return {
        "id": profile.id,
        "renter_id": profile.renter_id,
        "normalized_surname": profile.normalized_surname,
        "payment_code": profile.payment_code,
    }


def _transaction_input(row: BankTransaction) -> BankTransactionInput:
    return BankTransactionInput(
        account_id=row.account_id,
        bank_account_id=row.bank_account_id,
        provider_transaction_id=row.provider_transaction_id,
        amount_cents=row.amount_cents,
        bank_booking_date=row.bank_booking_date,
        finapi_booking_date=row.finapi_booking_date,
        value_date=row.value_date,
        counterpart_iban=row.counterpart_iban,
        counterpart_name=row.counterpart_name,
        purpose=row.purpose,
        end_to_end_reference=row.end_to_end_reference,
        counterpart_mandate_reference=row.counterpart_mandate_reference,
        bank_transaction_code=row.bank_transaction_code,
        provider_type=row.provider_type,
        is_potential_duplicate=row.is_potential_duplicate,
    )


def _receivable_input(row: Receivable) -> ReceivableInput:
    # An NK-Nachzahlung is principal, but deliberately not a rent/advance component.
    # The pure split contract still needs a vector summing to the expected principal;
    # the first bucket is the neutral persistence bucket and never feeds NK advances.
    components = (
        (row.expected_cents, 0, 0, 0)
        if row.category == "nk_nachzahlung"
        else (
            row.base_rent_cents,
            row.nk_advance_cents,
            row.heating_advance_cents,
            row.garage_cents,
        )
    )
    return ReceivableInput(
        id=row.id,
        account_id=row.account_id,
        renter_id=row.renter_id,
        tenancy_id=row.tenancy_id,
        source_type=row.source_type,
        source_id=row.source_id,
        period=row.period,
        due_date=row.due_date,
        expected_cents=row.expected_cents,
        open_cents=row.open_cents,
        status=row.status,
        category=row.category,
        principal_components=components,
        open_costs_cents=row.open_costs_cents,
        open_interest_cents=row.open_interest_cents,
        open_principal_cents=row.open_principal_cents,
    )


def _persisted_principal_components(
    receivable: Receivable, components: tuple[int, ...]
) -> tuple[int, int, int, int]:
    """Keep the engine's neutral Nachzahlung bucket out of named rent components."""
    if receivable.category == "nk_nachzahlung":
        return (0, 0, 0, 0)
    if len(components) != 4:
        raise MatchingConflictError(
            "Die Hauptforderungsanteile sind unvollständig. Die Zahlung wurde nicht gebucht."
        )
    return (components[0], components[1], components[2], components[3])


def _active_ibans(
    session: Session, account_id: str
) -> tuple[dict[str, tuple[str, ...]], dict[str, set[str]]]:
    by_renter: dict[str, list[str]] = defaultdict(list)
    owners: dict[str, set[str]] = defaultdict(set)
    rows = session.scalars(
        select(IbanHistory).where(
            IbanHistory.account_id == account_id, IbanHistory.valid_to.is_(None)
        )
    ).all()
    for row in rows:
        iban = normalize_iban(row.normalized_iban)
        by_renter[row.renter_id].append(iban)
        owners[iban].add(row.renter_id)
    return (
        {renter_id: tuple(sorted(set(ibans))) for renter_id, ibans in by_renter.items()},
        owners,
    )


def _candidates(
    session: Session, transaction: BankTransaction
) -> tuple[list[tuple[ReceivableInput, RenterProfileInput, IbanOwnership]], dict[str, Receivable]]:
    rows = session.execute(
        select(Receivable, RenterMatchingProfile)
        .join(
            RenterMatchingProfile,
            (RenterMatchingProfile.renter_id == Receivable.renter_id)
            & (RenterMatchingProfile.account_id == Receivable.account_id),
        )
        .where(
            Receivable.account_id == transaction.account_id,
            Receivable.status.in_(("open", "partial")),
        )
        .order_by(Receivable.id)
    ).all()
    by_renter, iban_owners = _active_ibans(session, transaction.account_id)
    transaction_iban = normalize_iban(transaction.counterpart_iban)
    candidates: list[tuple[ReceivableInput, RenterProfileInput, IbanOwnership]] = []
    stored: dict[str, Receivable] = {}
    for receivable, profile in rows:
        known_ibans = by_renter.get(profile.renter_id, ())
        owners = iban_owners.get(transaction_iban, set()) if transaction_iban else set()
        if profile.renter_id not in owners:
            ownership = IbanOwnership.UNKNOWN
        elif len(owners) == 1:
            ownership = IbanOwnership.UNIQUE
        else:
            ownership = IbanOwnership.SHARED
        candidates.append(
            (
                _receivable_input(receivable),
                RenterProfileInput(
                    account_id=profile.account_id,
                    renter_id=profile.renter_id,
                    payment_code=profile.payment_code,
                    normalized_surname=profile.normalized_surname,
                    known_ibans=known_ibans,
                ),
                ownership,
            )
        )
        stored[receivable.id] = receivable
    return candidates, stored


def _confirmation(session: Session, proposal_id: str) -> MatchConfirmation | None:
    return session.scalar(
        select(MatchConfirmation).where(MatchConfirmation.match_proposal_id == proposal_id)
    )


def _ledger_for_proposal(session: Session, proposal_id: str) -> PaymentLedgerEntry | None:
    return session.scalar(
        select(PaymentLedgerEntry).where(PaymentLedgerEntry.match_proposal_id == proposal_id)
    )


def _proposal_result(session: Session, transaction: BankTransaction) -> JsonObject:
    proposals = session.scalars(
        select(MatchProposal)
        .where(MatchProposal.bank_transaction_id == transaction.id)
        .order_by(MatchProposal.rank)
    ).all()
    if not proposals:
        return {
            "transaction_id": transaction.id,
            "decision": None,
            "reason_de": None,
            "candidates": [],
            "confirmation": None,
            "ledger_entry_id": None,
        }
    first = proposals[0]
    confirmation = _confirmation(session, first.id)
    ledger = _ledger_for_proposal(session, first.id)
    return {
        "transaction_id": transaction.id,
        "decision": _API_DECISION[first.decision],
        "reason_de": first.reason_de,
        "candidates": [_candidate_json(row) for row in proposals],
        "confirmation": _confirmation_json(confirmation),
        "ledger_entry_id": ledger.id if ledger is not None else None,
    }


def _candidate_json(row: MatchProposal) -> JsonObject:
    return {
        "proposal_id": row.id,
        "rank": row.rank,
        "receivable_id": row.receivable_id,
        "renter_id": row.renter_id,
        "signals": {
            "iban": row.signal_iban,
            "amount": row.signal_amount,
            "code_or_surname": row.signal_code_or_surname,
            "end_to_end": row.signal_e2e,
            "period": row.signal_period,
        },
        "confidence": row.confidence,
    }


def _confirmation_json(row: MatchConfirmation | None) -> JsonObject | None:
    if row is None:
        return None
    return {
        "outcome": row.outcome.lower(),
        "confirmed_by": row.confirmed_by,
        "confirmed_at": row.confirmed_at.isoformat(),
    }


def _designated_period(transaction: BankTransaction, rows: Sequence[Receivable]) -> str | None:
    purpose = normalize_comparison_text(transaction.purpose)
    if not purpose:
        return None
    designated = {
        row.period
        for row in rows
        if normalize_comparison_text(row.period) in purpose
        or normalize_comparison_text(row.id) in purpose
    }
    if len(designated) > 1:
        raise MatchingConflictError(
            "Der Verwendungszweck bezeichnet mehrere Forderungszeiträume. "
            "Die Zahlung wird nicht automatisch gebucht."
        )
    return next(iter(designated), None)


def _settle_payment(
    session: Session, transaction: BankTransaction, proposal: MatchProposal
) -> PaymentLedgerEntry:
    existing = _ledger_for_proposal(session, proposal.id)
    if existing is not None:
        return existing
    if proposal.renter_id is None:
        raise MatchingConflictError("Der Vorschlag enthält keinen Mieter für die Buchung.")
    receivables = session.scalars(
        select(Receivable)
        .where(
            Receivable.renter_id == proposal.renter_id,
            Receivable.account_id == transaction.account_id,
            Receivable.status.in_(("open", "partial")),
        )
        .order_by(Receivable.due_date, Receivable.id)
        .with_for_update()
    ).all()
    try:
        result = settle(
            _transaction_input(transaction),
            [_receivable_input(row) for row in receivables],
            designated_period=_designated_period(transaction, receivables),
        )
    except TieBreakUnspecifiedError as exc:
        raise MatchingConflictError(
            "Die Cent-Verteilung ist wegen eines Gleichstands nicht eindeutig. "
            "Die Zahlung wurde nicht gebucht."
        ) from exc
    entry = PaymentLedgerEntry(
        id=new_id(),
        account_id=transaction.account_id,
        bank_transaction_id=transaction.id,
        match_proposal_id=proposal.id,
        kind="PAYMENT",
        amount_cents=transaction.amount_cents,
        credit_cents=result.credit_cents,
        ordering_version="docs/15 § 366/367 BGB, Rechtsstand 07/2026",
        reverses_entry_id=None,
    )
    session.add(entry)
    session.flush()
    by_id = {row.id: row for row in receivables}
    for allocation in result.allocations:
        row = by_id[allocation.receivable_id]
        components = _persisted_principal_components(row, allocation.principal_components)
        session.add(
            PaymentAllocation(
                id=new_id(),
                account_id=transaction.account_id,
                ledger_entry_id=entry.id,
                receivable_id=row.id,
                costs_cents=allocation.costs_cents,
                interest_cents=allocation.interest_cents,
                principal_cents=allocation.principal_cents,
                base_rent_cents=components[0],
                nk_advance_cents=components[1],
                heating_advance_cents=components[2],
                garage_cents=components[3],
                resulting_status=allocation.status,
                before_open_costs_cents=allocation.open_costs_cents_before,
                before_open_interest_cents=allocation.open_interest_cents_before,
                before_open_principal_cents=row.open_principal_cents,
                before_open_cents=allocation.open_cents_before,
                before_status=allocation.status_before,
                after_open_costs_cents=allocation.open_costs_cents,
                after_open_interest_cents=allocation.open_interest_cents,
                after_open_principal_cents=allocation.open_cents,
                after_open_cents=allocation.open_cents,
                after_status=allocation.status,
            )
        )
        row.open_costs_cents = allocation.open_costs_cents
        row.open_interest_cents = allocation.open_interest_cents
        row.open_principal_cents = allocation.open_cents
        row.open_cents = allocation.open_cents
        row.status = allocation.status
    session.flush()
    return entry


def _complete_snapshot(row: PaymentAllocation) -> bool:
    return all(
        value is not None
        for value in (
            row.before_open_costs_cents,
            row.before_open_interest_cents,
            row.before_open_principal_cents,
            row.before_open_cents,
            row.before_status,
            row.after_open_costs_cents,
            row.after_open_interest_cents,
            row.after_open_principal_cents,
            row.after_open_cents,
            row.after_status,
        )
    )


def _resolve_original_payment(
    session: Session, returned: BankTransaction
) -> tuple[PaymentLedgerEntry, BankTransaction]:
    rows = [
        (entry, transaction)
        for entry, transaction in session.execute(
            select(PaymentLedgerEntry, BankTransaction)
            .join(BankTransaction, BankTransaction.id == PaymentLedgerEntry.bank_transaction_id)
            .where(
                PaymentLedgerEntry.account_id == returned.account_id,
                PaymentLedgerEntry.kind == "PAYMENT",
            )
            .order_by(PaymentLedgerEntry.created_at, PaymentLedgerEntry.id)
        )
    ]

    def unique_or_conflict(
        matches: list[tuple[PaymentLedgerEntry, BankTransaction]], label: str
    ) -> tuple[PaymentLedgerEntry, BankTransaction] | None:
        if len(matches) > 1:
            raise MatchingConflictError(
                f"Die Rückzahlung ist über {label} nicht eindeutig. Es wurde nichts geändert."
            )
        return matches[0] if matches else None

    if returned.end_to_end_reference is not None:
        found = unique_or_conflict(
            [row for row in rows if row[1].end_to_end_reference == returned.end_to_end_reference],
            "die End-to-End-Referenz",
        )
        if found is not None:
            return found
    if returned.counterpart_mandate_reference is not None:
        found = unique_or_conflict(
            [
                row
                for row in rows
                if row[1].counterpart_mandate_reference == returned.counterpart_mandate_reference
            ],
            "die Mandatsreferenz",
        )
        if found is not None:
            return found
    iban = normalize_iban(returned.counterpart_iban)
    fallback = [
        row
        for row in rows
        if iban
        and normalize_iban(row[1].counterpart_iban) == iban
        and row[1].amount_cents == -returned.amount_cents
        and row[1].bank_booking_date == returned.bank_booking_date
        and row[1].value_date == returned.value_date
    ]
    found = unique_or_conflict(fallback, "IBAN, Betrag und Datum")
    if found is None:
        raise MatchingConflictError(
            "Zur Rückzahlung wurde keine eindeutig passende ursprüngliche Zahlung gefunden."
        )
    return found


def _reverse_payment(session: Session, returned: BankTransaction) -> JsonObject:
    existing = session.scalar(
        select(PaymentLedgerEntry).where(
            PaymentLedgerEntry.bank_transaction_id == returned.id,
            PaymentLedgerEntry.kind == "REVERSAL",
        )
    )
    if existing is not None:
        return {
            "transaction_id": returned.id,
            "event": "payment_returned",
            "ledger_entry_id": existing.id,
        }
    original_entry, original_transaction = _resolve_original_payment(session, returned)
    already_reversed = session.scalar(
        select(PaymentLedgerEntry.id).where(
            PaymentLedgerEntry.reverses_entry_id == original_entry.id
        )
    )
    if already_reversed is not None:
        raise MatchingConflictError("Diese Zahlung wurde bereits zurückgebucht.")
    allocations = session.scalars(
        select(PaymentAllocation)
        .where(PaymentAllocation.ledger_entry_id == original_entry.id)
        .order_by(PaymentAllocation.id)
    ).all()
    if not allocations or any(not _complete_snapshot(row) for row in allocations):
        raise MatchingConflictError(
            "Die ursprüngliche Zahlung hat keine vollständigen Projektionsnachweise. "
            "Sie kann nicht automatisch zurückgebucht werden."
        )
    receivable_ids = [row.receivable_id for row in allocations]
    receivables = session.scalars(
        select(Receivable)
        .where(Receivable.id.in_(receivable_ids))
        .order_by(Receivable.id)
        .with_for_update()
    ).all()
    by_id = {row.id: row for row in receivables}
    if len(by_id) != len(set(receivable_ids)):
        raise MatchingConflictError("Eine ursprüngliche Forderung wurde nicht gefunden.")
    engine_allocations: list[Allocation] = []
    for stored in allocations:
        receivable = by_id[stored.receivable_id]
        if (
            receivable.open_costs_cents != stored.after_open_costs_cents
            or receivable.open_interest_cents != stored.after_open_interest_cents
            or receivable.open_principal_cents != stored.after_open_principal_cents
            or receivable.open_cents != stored.after_open_cents
            or receivable.status != stored.after_status
        ):
            raise MatchingConflictError(
                "Spätere Buchungen haben den Forderungsstand verändert. "
                "Die Rückzahlung kann nicht sicher automatisch gebucht werden."
            )
        assert stored.before_open_cents is not None
        assert stored.before_open_costs_cents is not None
        assert stored.before_open_interest_cents is not None
        assert stored.before_status is not None
        assert stored.after_open_cents is not None
        assert stored.after_open_costs_cents is not None
        assert stored.after_open_interest_cents is not None
        assert stored.after_status is not None
        engine_allocations.append(
            Allocation(
                receivable_id=receivable.id,
                renter_id=receivable.renter_id,
                account_id=receivable.account_id,
                expected_cents=receivable.expected_cents,
                costs_cents=stored.costs_cents,
                interest_cents=stored.interest_cents,
                principal_cents=stored.principal_cents,
                principal_components=(
                    stored.base_rent_cents,
                    stored.nk_advance_cents,
                    stored.heating_advance_cents,
                    stored.garage_cents,
                ),
                open_cents=stored.after_open_cents,
                open_costs_cents=stored.after_open_costs_cents,
                open_interest_cents=stored.after_open_interest_cents,
                status=stored.after_status,
                open_cents_before=stored.before_open_cents,
                open_costs_cents_before=stored.before_open_costs_cents,
                open_interest_cents_before=stored.before_open_interest_cents,
                status_before=stored.before_status,
            )
        )
    try:
        result = reverse(
            _transaction_input(returned),
            _transaction_input(original_transaction),
            [SettlementResult(tuple(engine_allocations), original_entry.credit_cents)],
        )
    except ValueError as exc:
        raise MatchingConflictError(
            "Die Rückzahlung stimmt nicht vollständig mit der ursprünglichen Zahlung überein."
        ) from exc
    entry = PaymentLedgerEntry(
        id=new_id(),
        account_id=returned.account_id,
        bank_transaction_id=returned.id,
        match_proposal_id=None,
        kind="REVERSAL",
        amount_cents=returned.amount_cents,
        credit_cents=0,
        ordering_version="docs/15 § 5.3, Rechtsstand 07/2026",
        reverses_entry_id=original_entry.id,
    )
    session.add(entry)
    session.flush()
    stored_by_receivable = {row.receivable_id: row for row in allocations}
    restored_by_receivable = {row.receivable_id: row for row in result.restored_receivables}
    for compensation in result.compensating_entries:
        stored = stored_by_receivable[compensation.receivable_id]
        restored = restored_by_receivable[compensation.receivable_id]
        receivable = by_id[compensation.receivable_id]
        components = _persisted_principal_components(receivable, compensation.principal_components)
        session.add(
            PaymentAllocation(
                id=new_id(),
                account_id=returned.account_id,
                ledger_entry_id=entry.id,
                receivable_id=receivable.id,
                costs_cents=compensation.costs_cents,
                interest_cents=compensation.interest_cents,
                principal_cents=compensation.principal_cents,
                base_rent_cents=components[0],
                nk_advance_cents=components[1],
                heating_advance_cents=components[2],
                garage_cents=components[3],
                resulting_status=restored.status,
                before_open_costs_cents=stored.after_open_costs_cents,
                before_open_interest_cents=stored.after_open_interest_cents,
                before_open_principal_cents=stored.after_open_principal_cents,
                before_open_cents=stored.after_open_cents,
                before_status=stored.after_status,
                after_open_costs_cents=stored.before_open_costs_cents,
                after_open_interest_cents=stored.before_open_interest_cents,
                after_open_principal_cents=stored.before_open_principal_cents,
                after_open_cents=stored.before_open_cents,
                after_status=stored.before_status,
            )
        )
        receivable.open_costs_cents = restored.open_costs_cents
        receivable.open_interest_cents = restored.open_interest_cents
        receivable.open_principal_cents = restored.open_cents
        receivable.open_cents = restored.open_cents
        receivable.status = restored.status
    session.flush()
    return {
        "transaction_id": returned.id,
        "event": result.guard_signal,
        "ledger_entry_id": entry.id,
    }


def run_match(session: Session, transaction_id: str) -> JsonObject:
    transaction = session.scalar(
        select(BankTransaction).where(BankTransaction.id == transaction_id).with_for_update()
    )
    if transaction is None:
        raise MatchingNotFoundError("Banktransaktion nicht gefunden")
    if transaction.amount_cents < 0:
        return _reverse_payment(session, transaction)
    if transaction.amount_cents == 0:
        return _proposal_result(session, transaction)
    existing = session.scalar(
        select(MatchProposal.id).where(MatchProposal.bank_transaction_id == transaction.id)
    )
    if existing is not None:
        return _proposal_result(session, transaction)
    candidates, _ = _candidates(session, transaction)
    engine_result = propose(_transaction_input(transaction), candidates)
    ranked = engine_result.ranked_candidates
    if ranked:
        for rank, candidate in enumerate(ranked, start=1):
            session.add(
                MatchProposal(
                    id=new_id(),
                    account_id=transaction.account_id,
                    bank_transaction_id=transaction.id,
                    receivable_id=candidate.receivable_id,
                    renter_id=candidate.renter_id,
                    rank=rank,
                    signal_iban=candidate.signals[0],
                    signal_amount=candidate.signals[1],
                    signal_code_or_surname=candidate.signals[2],
                    signal_e2e=candidate.signals[3],
                    signal_period=candidate.signals[4],
                    confidence=candidate.confidence,
                    decision=_DB_DECISION[engine_result.decision],
                    convention_version=engine_result.convention_version,
                    reason_de=engine_result.reason,
                )
            )
    else:
        session.add(
            MatchProposal(
                id=new_id(),
                account_id=transaction.account_id,
                bank_transaction_id=transaction.id,
                receivable_id=None,
                renter_id=None,
                rank=1,
                signal_iban=0,
                signal_amount=0,
                signal_code_or_surname=0,
                signal_e2e=0,
                signal_period=0,
                confidence=0,
                decision=_DB_DECISION[engine_result.decision],
                convention_version=engine_result.convention_version,
                reason_de=engine_result.reason,
            )
        )
    session.flush()
    first = session.scalar(
        select(MatchProposal).where(
            MatchProposal.bank_transaction_id == transaction.id,
            MatchProposal.rank == 1,
        )
    )
    assert first is not None
    if engine_result.decision is Decision.AUTO_MATCH:
        _settle_payment(session, transaction, first)
    return _proposal_result(session, transaction)


def decide_match(session: Session, transaction_id: str, outcome: str, actor_id: str) -> JsonObject:
    transaction = session.scalar(
        select(BankTransaction).where(BankTransaction.id == transaction_id).with_for_update()
    )
    if transaction is None:
        raise MatchingNotFoundError("Banktransaktion nicht gefunden")
    proposal = session.scalar(
        select(MatchProposal).where(
            MatchProposal.bank_transaction_id == transaction.id,
            MatchProposal.rank == 1,
        )
    )
    if proposal is None:
        raise MatchingNotFoundError("Matching-Vorschlag nicht gefunden")
    if proposal.decision != "NEEDS_REVIEW":
        raise MatchingConflictError("Dieser Matching-Vorschlag benötigt keine Entscheidung.")
    requested = _DB_OUTCOME[outcome]
    existing = _confirmation(session, proposal.id)
    if existing is not None:
        if existing.outcome != requested:
            raise MatchingConflictError(
                "Für diesen Vorschlag besteht bereits eine andere Entscheidung."
            )
        existing_ledger = _ledger_for_proposal(session, proposal.id)
        return {
            "transaction_id": transaction.id,
            "outcome": outcome,
            "selected_rank": proposal.rank if outcome == "confirmed" else None,
            "ledger_entry_id": existing_ledger.id if existing_ledger is not None else None,
        }
    confirmed_at = datetime.now(UTC)
    confirmation = MatchConfirmation(
        id=new_id(),
        account_id=transaction.account_id,
        match_proposal_id=proposal.id,
        outcome=requested,
        confirmed_by=actor_id,
        confirmed_at=confirmed_at,
    )
    session.add(confirmation)
    session.flush()
    ledger: PaymentLedgerEntry | None = None
    if outcome == "confirmed":
        ledger = _settle_payment(session, transaction, proposal)
        if should_learn_iban(_transaction_input(transaction), match_confirmed=True):
            iban = normalize_iban(transaction.counterpart_iban)
            active = session.scalar(
                select(IbanHistory.id).where(
                    IbanHistory.renter_id == proposal.renter_id,
                    IbanHistory.normalized_iban == iban,
                    IbanHistory.valid_to.is_(None),
                )
            )
            if active is None:
                assert proposal.renter_id is not None
                session.add(
                    IbanHistory(
                        id=new_id(),
                        account_id=transaction.account_id,
                        renter_id=proposal.renter_id,
                        normalized_iban=iban,
                        valid_from=confirmed_at,
                        valid_to=None,
                        learned_from_transaction_id=transaction.id,
                        confirmed_match_id=confirmation.id,
                        confirmed_by=actor_id,
                        confirmed_at=confirmed_at,
                    )
                )
    session.flush()
    return {
        "transaction_id": transaction.id,
        "outcome": outcome,
        "selected_rank": proposal.rank if outcome == "confirmed" else None,
        "ledger_entry_id": ledger.id if ledger is not None else None,
    }


def list_proposals(session: Session) -> JsonObject:
    rows = session.scalars(
        select(MatchProposal).order_by(
            MatchProposal.created_at.desc(), MatchProposal.bank_transaction_id, MatchProposal.rank
        )
    ).all()
    grouped: dict[str, list[MatchProposal]] = defaultdict(list)
    order: list[str] = []
    for row in rows:
        if row.bank_transaction_id not in grouped:
            order.append(row.bank_transaction_id)
        grouped[row.bank_transaction_id].append(row)
    transactions: list[JsonObject] = []
    for transaction_id in order:
        proposals = sorted(grouped[transaction_id], key=lambda row: row.rank)
        first = proposals[0]
        confirmation = _confirmation(session, first.id)
        ledger = _ledger_for_proposal(session, first.id)
        transactions.append(
            {
                "transaction_id": transaction_id,
                "decision": _API_DECISION[first.decision],
                "reason_de": first.reason_de,
                "candidates": [_candidate_json(row) for row in proposals],
                "confirmation": _confirmation_json(confirmation),
                "ledger_entry_id": ledger.id if ledger is not None else None,
                "created_at": first.created_at.isoformat(),
            }
        )
    return {"transactions": transactions}


def _allocation_json(row: PaymentAllocation) -> JsonObject:
    return {
        "id": row.id,
        "receivable_id": row.receivable_id,
        "costs_cents": row.costs_cents,
        "interest_cents": row.interest_cents,
        "principal_cents": row.principal_cents,
        "components": {
            "base_rent_cents": row.base_rent_cents,
            "nk_advance_cents": row.nk_advance_cents,
            "heating_advance_cents": row.heating_advance_cents,
            "garage_cents": row.garage_cents,
        },
        "resulting_status": row.resulting_status,
        "before": {
            "open_costs_cents": row.before_open_costs_cents,
            "open_interest_cents": row.before_open_interest_cents,
            "open_principal_cents": row.before_open_principal_cents,
            "open_cents": row.before_open_cents,
            "status": row.before_status,
        },
        "after": {
            "open_costs_cents": row.after_open_costs_cents,
            "open_interest_cents": row.after_open_interest_cents,
            "open_principal_cents": row.after_open_principal_cents,
            "open_cents": row.after_open_cents,
            "status": row.after_status,
        },
    }


def list_ledger(session: Session) -> JsonObject:
    entries = session.scalars(
        select(PaymentLedgerEntry).order_by(
            PaymentLedgerEntry.created_at.desc(), PaymentLedgerEntry.id.desc()
        )
    ).all()
    result: list[JsonObject] = []
    for entry in entries:
        allocations = session.scalars(
            select(PaymentAllocation)
            .where(PaymentAllocation.ledger_entry_id == entry.id)
            .order_by(PaymentAllocation.id)
        ).all()
        result.append(
            {
                "id": entry.id,
                "bank_transaction_id": entry.bank_transaction_id,
                "match_proposal_id": entry.match_proposal_id,
                "kind": entry.kind.lower(),
                "amount_cents": entry.amount_cents,
                "credit_cents": entry.credit_cents,
                "ordering_version": entry.ordering_version,
                "reverses_entry_id": entry.reverses_entry_id,
                "created_at": entry.created_at.isoformat(),
                "allocations": [_allocation_json(row) for row in allocations],
            }
        )
    return {"entries": result}


__all__ = [
    "MatchingConflictError",
    "MatchingNotFoundError",
    "decide_match",
    "list_ledger",
    "list_proposals",
    "run_match",
    "upsert_matching_profile",
]
