"""Candidate signals and confidence — `docs/15` § 4, CSV row 172.

Every weight here is a Lokara *convention*, flagged `verify-before-production`
(Rechtsstand 07/2026).  None of it is law.  The four checked BGB rows apply only after
the payment has been assigned, and `docs/15` § 2 is explicit that these numbers must
never be presented as legal support for a score or an Auto-Match.

The signal vector is a fixed 5-tuple in the order
`(iban, amount, code_or_surname, e2e, period)` so that a stored proposal can be replayed
component by component years later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .inputs import (
    BankTransactionInput,
    IbanOwnership,
    ReceivableInput,
    RenterProfileInput,
    normalize_comparison_text,
    normalize_iban,
)

#: `docs/15` § 4 signal table / CSV row 172.  Konvention, `verify-before-production`.
WEIGHT_UNIQUE_IBAN: Final = 60
WEIGHT_AMBIGUOUS_IBAN: Final = 20
WEIGHT_EXACT_AMOUNT: Final = 30
WEIGHT_PAYMENT_CODE: Final = 15
WEIGHT_END_TO_END_REFERENCE: Final = 15
WEIGHT_SURNAME: Final = 10
WEIGHT_PERIOD: Final = 5

#: `docs/15` § 4: "Confidence is `min(100, sum(signals))`".
CONFIDENCE_CAP: Final = 100

#: `docs/15` § 2 last paragraph and § 4 step 5.  CSV row 171's "Auto = 40-79" is
#: shorthand, not a general threshold: the floor below only separates Review from
#: Unmatched *for candidates that are not Auto-eligible*.
REVIEW_FLOOR: Final = 40

#: Index of each component inside `CandidateScore.signals`.
IBAN_SIGNAL: Final = 0
AMOUNT_SIGNAL: Final = 1
CODE_OR_SURNAME_SIGNAL: Final = 2
END_TO_END_SIGNAL: Final = 3
PERIOD_SIGNAL: Final = 4


@dataclass(frozen=True, slots=True)
class CandidateScore:
    """One scored `(transaction, renter, receivable)` candidate (`docs/15` § 4).

    It carries no money.  A score proposes; it never books (`docs/15` § 0).
    """

    receivable_id: str
    renter_id: str
    account_id: str
    iban_ownership: IbanOwnership
    signals: tuple[int, ...]
    confidence: int

    @property
    def has_unique_known_iban(self) -> bool:
        """The only Auto-Match key there is (`docs/15` § 4 step 3, CSV row 181)."""
        return self.signals[IBAN_SIGNAL] == WEIGHT_UNIQUE_IBAN


def _iban_signal(
    transaction: BankTransactionInput,
    profile: RenterProfileInput,
    ownership: IbanOwnership,
) -> int:
    """60 for a *known* IBAN unique to one renter, 20 when shared, otherwise 0.

    "Known" is taken literally: the transaction's IBAN must appear among this renter's
    active history rows (`docs/15` § 3.3).  A null counterpart IBAN scores nothing, which
    is what makes `BANKMATCH-F09` land on 45 rather than 105.
    """
    counterpart = normalize_iban(transaction.counterpart_iban)
    if not counterpart:
        return 0
    if counterpart not in {normalize_iban(known) for known in profile.known_ibans}:
        return 0
    if ownership is IbanOwnership.UNIQUE:
        return WEIGHT_UNIQUE_IBAN
    if ownership is IbanOwnership.SHARED:
        return WEIGHT_AMBIGUOUS_IBAN
    return 0


def _code_or_surname_signal(purpose: str, profile: RenterProfileInput) -> int:
    """15 for the payment code, else 10 for the surname — "take 15 or 10, not both".

    `BANKMATCH-F09` puts *both* in the purpose and still scores 45.  Mutual exclusivity
    is the entire point of that fixture.
    """
    if not purpose:
        return 0
    code = normalize_comparison_text(profile.payment_code)
    if code and code in purpose:
        return WEIGHT_PAYMENT_CODE
    surname = normalize_comparison_text(profile.normalized_surname)
    if surname and surname in purpose:
        return WEIGHT_SURNAME
    return 0


def _end_to_end_signal(transaction: BankTransactionInput, profile: RenterProfileInput) -> int:
    """15 when the E2E or mandate reference matches the renter's stored reference.

    `docs/15` § 4 names "stored reference" but § 3.3 gives the renter profile exactly one
    stored, renter-identifying reference: `payment_code`.  That is what is compared here.
    No Page 08 fixture exercises this signal, so nothing in the oracle pins the reading —
    it is flagged in the slice report as a judgment call for review, and it is deliberately
    the narrowest option (the profile's own field) rather than an invented reference table.
    """
    stored = normalize_comparison_text(profile.payment_code)
    if not stored:
        return 0
    references = (transaction.end_to_end_reference, transaction.counterpart_mandate_reference)
    for reference in references:
        normalized = normalize_comparison_text(reference)
        if normalized and stored in normalized:
            return WEIGHT_END_TO_END_REFERENCE
    return 0


def _period_signal(purpose: str, receivable: ReceivableInput) -> int:
    """5 when the purpose contains this receivable's own period token.

    The token is the normalized `docs/15` § 3.2 period (`YYYY-MM`, or the statement
    period for an NK-Nachzahlung).  `docs/15` does not state which other spellings — a
    German month name, "Juli 26" — count as the token, so none is accepted here and no
    fixture depends on one.
    """
    token = normalize_comparison_text(receivable.period)
    if token and purpose and token in purpose:
        return WEIGHT_PERIOD
    return 0


def score_candidate(
    transaction: BankTransactionInput,
    receivable: ReceivableInput,
    profile: RenterProfileInput,
    iban_ownership: IbanOwnership,
) -> CandidateScore:
    """Score one account-scoped candidate (`docs/15` § 4).

    There is no amount tolerance (CSV row 169): `amount_cents == open_cents` or nothing.
    Confidence is capped at 100 and the raw signal vector is preserved alongside it, so a
    stored proposal stays auditable after the convention version changes.
    """
    purpose = normalize_comparison_text(transaction.purpose)
    signals = (
        _iban_signal(transaction, profile, iban_ownership),
        WEIGHT_EXACT_AMOUNT if transaction.amount_cents == receivable.open_cents else 0,
        _code_or_surname_signal(purpose, profile),
        _end_to_end_signal(transaction, profile),
        _period_signal(purpose, receivable),
    )
    return CandidateScore(
        receivable_id=receivable.id,
        renter_id=receivable.renter_id,
        account_id=receivable.account_id,
        iban_ownership=iban_ownership,
        signals=signals,
        confidence=min(CONFIDENCE_CAP, sum(signals)),
    )
