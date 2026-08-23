"""Decision channel and the stored proposal — `docs/15` § 4, CSV rows 171, 178-179, 181.

The decision order in `docs/15` § 4 is an *order*, not a set of independent tests, and
the fixtures exist to pin it:

1. an exact provider-ID re-import is deduplicated — before channel selection, before any
   scoring (`BANKMATCH-F03`);
2. `isPotentialDuplicate` then forces Review, *even with a unique known IBAN*, and the
   transaction is kept, never silently discarded (`docs/15` § 3.1);
3. exactly one renter carrying the unique-IBAN signal produces Auto-Match;
4. a shared IBAN never Auto-Matches — not even at 65 (`BANKMATCH-F07`);
5. without Auto eligibility, confidence >= 40 is Review and below 40 is Unmatched.

Auto-Match is therefore **not** a score threshold.  CSV row 171's "Auto = 40-79" is
shorthand and `docs/15` § 2 says so explicitly: a unique known IBAN Auto-Matches at only
60 (`BANKMATCH-F04`, `-F11`), while a shared IBAN stays in Review above the same floor.

A `Proposal` carries no money at all.  Settlement lives in `settlement.py` and happens
only after an Auto-Match or an explicit user confirmation.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from .inputs import (
    BankTransactionInput,
    IbanOwnership,
    ReceivableInput,
    RenterProfileInput,
    normalize_iban,
)
from .scoring import (
    AMOUNT_SIGNAL,
    CODE_OR_SURNAME_SIGNAL,
    END_TO_END_SIGNAL,
    REVIEW_FLOOR,
    CandidateScore,
    score_candidate,
)

#: The convention set a stored proposal was decided under (`docs/15` § 4: the proposal
#: records "applicable convention version").  Every weight and threshold behind it is
#: `verify-before-production`; a green replay proves determinism, not legal approval.
CONVENTION_VERSION: Final = "docs/15 bank-matching conventions, Rechtsstand 07/2026"

#: One account-scoped candidate as the caller supplies it (`docs/15` §§ 3.3, 4).
Candidate = tuple[ReceivableInput, RenterProfileInput, IbanOwnership]

#: `docs/15` § 3.1 exact re-import identity.
ProviderIdentity = tuple[str, str, str]


class Decision(StrEnum):
    """The four channels a normalized transaction can end in (`docs/15` § 4)."""

    #: Exactly one renter with a unique known IBAN, and no duplicate flag.
    AUTO_MATCH = "auto_match"
    #: A human decides.  No amount is settled before that confirmation.
    NEEDS_REVIEW = "needs_review"
    #: Too little evidence.  Nothing is proposed and nothing is settled.
    UNMATCHED = "unmatched"
    #: An already-processed movement, recognised by its `(account_id, bank_account_id,
    #: provider_transaction_id)` triple.  Distinct from `NEEDS_REVIEW`: a dedupe creates
    #: no second normalized transaction and no second ledger entry (`docs/15` § 3.1).
    DEDUPED = "deduped"


@dataclass(frozen=True, slots=True)
class Proposal:
    """The stored, replayable outcome of § 4 — identity, evidence, channel, reason.

    Deliberately money-free.  `docs/15` § 4 step 6: "No amount is settled before
    confirmation", so a proposal exposes no allocation, credit or amount field that a
    caller could mistake for a booking.
    """

    account_id: str
    bank_account_id: str
    provider_transaction_id: str
    decision: Decision
    reason: str
    ranked_candidates: tuple[CandidateScore, ...]
    convention_version: str = CONVENTION_VERSION


def _ranking_key(score: CandidateScore) -> tuple[int, int, int, int, str]:
    """`docs/15` § 4 step 6: rank by amount, then code/surname and E2E evidence.

    Confidence and finally the receivable ID close the key so the order is total and
    reproducible — no set iteration and no caller-supplied input order may leak into a
    stored ranking.
    """
    return (
        -score.signals[AMOUNT_SIGNAL],
        -score.signals[CODE_OR_SURNAME_SIGNAL],
        -score.signals[END_TO_END_SIGNAL],
        -score.confidence,
        score.receivable_id,
    )


def _in_account(
    transaction: BankTransactionInput, candidates: Iterable[Candidate]
) -> list[Candidate]:
    """Drop everything outside the transaction's account *before* any score exists.

    `docs/15` §§ 4 and 6: candidates are only receivables of renters in the transaction's
    `account_id`, and candidate selection is restricted to one account "before any score
    is calculated".  A leaked foreign candidate would not merely show up in a list — its
    unique-IBAN signal would turn an Unmatched transaction into an Auto-Match across the
    isolation boundary.
    """
    return [
        (receivable, profile, ownership)
        for receivable, profile, ownership in candidates
        if receivable.account_id == transaction.account_id
        and profile.account_id == transaction.account_id
        and receivable.renter_id == profile.renter_id
    ]


def _proposal(
    transaction: BankTransactionInput,
    decision: Decision,
    reason: str,
    ranked: tuple[CandidateScore, ...],
) -> Proposal:
    return Proposal(
        account_id=transaction.account_id,
        bank_account_id=transaction.bank_account_id,
        provider_transaction_id=transaction.provider_transaction_id,
        decision=decision,
        reason=reason,
        ranked_candidates=ranked,
    )


def propose(
    transaction: BankTransactionInput,
    candidates: Sequence[Candidate],
    *,
    already_imported_provider_ids: frozenset[ProviderIdentity] = frozenset(),
) -> Proposal:
    """Run the `docs/15` § 4 decision order and return the stored proposal."""
    if transaction.provider_identity in already_imported_provider_ids:
        # Step 1, and it precedes step 2: an exact re-import that happens to carry
        # `isPotentialDuplicate` is still deduplicated, not reviewed.  Nothing is scored.
        return _proposal(
            transaction,
            Decision.DEDUPED,
            "Bereits importierte Provider-Transaktion (Konto, Bankkonto, Provider-ID): "
            "dedupliziert vor Kanalwahl und Scoring. Es entsteht keine zweite "
            "normalisierte Transaktion und keine zweite Buchung "
            "(docs/15 Abschnitt 4, Schritt 1).",
            (),
        )

    scoped = _in_account(transaction, candidates)
    ranked = tuple(
        sorted(
            (
                score_candidate(transaction, receivable, profile, ownership)
                for receivable, profile, ownership in scoped
            ),
            key=_ranking_key,
        )
    )

    if transaction.is_potential_duplicate:
        # Step 2 beats step 3: a unique known IBAN does not rescue it.  The transaction
        # is kept and reviewed, never silently discarded (`docs/15` § 3.1, CSV row 178).
        return _proposal(
            transaction,
            Decision.NEEDS_REVIEW,
            "Der Anbieter meldet eine mögliche Doublette: Prüfung erforderlich, auch bei "
            "eindeutig bekannter IBAN. Die Transaktion bleibt erhalten "
            "(docs/15 Abschnitt 4, Schritt 2).",
            ranked,
        )

    unique_iban_renters = sorted(
        {score.renter_id for score in ranked if score.has_unique_known_iban}
    )
    if len(unique_iban_renters) == 1:
        # Step 3.  The amount affects allocation, not identity: F04 and F11 Auto-Match at
        # 60 with no amount signal at all.
        return _proposal(
            transaction,
            Decision.AUTO_MATCH,
            "Auto-Match: genau ein Mieter mit eindeutig bekannter IBAN. Der Betrag "
            "steuert die Verteilung auf die Forderungen, nicht die Identität "
            "(docs/15 Abschnitt 4, Schritt 3).",
            ranked,
        )

    if not ranked:
        return _proposal(
            transaction,
            Decision.UNMATCHED,
            "Keine offene Forderung dieses Kontos kommt als Kandidat in Frage "
            "(docs/15 Abschnitt 4).",
            (),
        )

    top = ranked[0]
    if top.confidence >= REVIEW_FLOOR:
        # Steps 4 and 5.  A shared IBAN stays in Review however high the number goes.
        demotion = (
            "die IBAN gehört mehreren Mietern dieses Kontos"
            if any(score.iban_ownership is IbanOwnership.SHARED for score in ranked)
            else "keine eindeutig bekannte IBAN"
        )
        return _proposal(
            transaction,
            Decision.NEEDS_REVIEW,
            f"Kein Auto-Match, {demotion}. Konfidenz {top.confidence} >= {REVIEW_FLOOR}: "
            "Prüfung erforderlich (docs/15 Abschnitt 4, Schritte 4 und 5). Bis zur "
            "Bestätigung wird kein Betrag zugeordnet.",
            ranked,
        )

    return _proposal(
        transaction,
        Decision.UNMATCHED,
        f"Kein Auto-Match und Konfidenz {top.confidence} < {REVIEW_FLOOR}: nicht "
        "zugeordnet (docs/15 Abschnitt 4, Schritt 5).",
        ranked,
    )


def should_learn_iban(transaction: BankTransactionInput, match_confirmed: bool) -> bool:
    """Learn a counterpart IBAN only after a confirmed match (`docs/15` § 3.3, row 179).

    Null is never learned (`BANKMATCH-F09`), and an unconfirmed Review proposal learns
    nothing either.  On `True` the caller appends a *new* `IbanHistory` row with its own
    `valid_from`, `learned_from_transaction_id` and confirmation actor; nothing is
    overwritten (`CLAUDE.md` § 3.2).
    """
    if not match_confirmed:
        return False
    return bool(normalize_iban(transaction.counterpart_iban))
