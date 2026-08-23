"""Pure bank-matching engine — `docs/15-bank-matching.md`.

Deterministic scoring, decision, settlement and reversal over integer cents.
Matching identity is a Lokara convention: a high confidence proposes, it never
books.  The statutory §§ 362/366/367 ordering in settlement is independent of
the scoring conventions in §4 and is never reordered by a score.

The public surface is populated by the M6-C1 implementation slice.

Layout, and the boundary each module owns:

- `inputs` — the normalized § 3 records, the text/IBAN normalization of § 4, and
  `parse_provider_amount_to_cents`, the single decimal-to-cent boundary in the system;
- `scoring` — the five § 4 signals and the capped confidence, all `Konvention`;
- `decision` — the § 4 decision *order* (dedupe, duplicate flag, unique IBAN, shared
  IBAN, threshold) and the money-free stored `Proposal`;
- `settlement` — §§ 362/366/367 BGB allocation, overpayment and renter credit;
- `split` — the § 5.2 Largest-Remainder component split;
- `reversal` — the § 5.3 append-only compensating entries;
- `errors` — the one place the engine refuses instead of guessing.

Two properties this package will not trade away.  It imports nothing but the standard
library, so no clock, no file, no vendor SDK and no rules store can reach a legal number
(`CLAUDE.md` § 3.1; the caller resolves values and passes them in).  And where the
authoritative source is silent about a rule that would move renter money — the § 5.2
tie-break between equal fractional remainders — it raises `TieBreakUnspecifiedError`
rather than inventing a convention (`CLAUDE.md` § 4).

Nothing here is legally approved.  Every weight, threshold and Auto-Match rule is a
`verify-before-production` convention at Rechtsstand 07/2026 (`docs/15` § 2).
"""

from .decision import (
    CONVENTION_VERSION,
    Candidate,
    Decision,
    Proposal,
    ProviderIdentity,
    propose,
    should_learn_iban,
)
from .errors import MatchingEngineError, TieBreakUnspecifiedError
from .inputs import (
    CATEGORY_NK_NACHZAHLUNG,
    CATEGORY_RENT,
    STATUS_OPEN,
    STATUS_PARTIAL,
    STATUS_SETTLED,
    BankTransactionInput,
    IbanOwnership,
    ReceivableInput,
    RenterProfileInput,
    normalize_comparison_text,
    normalize_iban,
    parse_provider_amount_to_cents,
)
from .reversal import (
    GUARD_PAYMENT_RETURNED,
    RESOLUTION_END_TO_END_REFERENCE,
    RESOLUTION_IBAN_AMOUNT_DATE,
    RESOLUTION_MANDATE_REFERENCE,
    CompensatingEntry,
    RestoredReceivable,
    ReversalResult,
    reverse,
)
from .scoring import (
    CONFIDENCE_CAP,
    REVIEW_FLOOR,
    CandidateScore,
    score_candidate,
)
from .settlement import Allocation, SettlementResult, settle
from .split import split_principal

__all__ = [
    "CATEGORY_NK_NACHZAHLUNG",
    "CATEGORY_RENT",
    "CONFIDENCE_CAP",
    "CONVENTION_VERSION",
    "GUARD_PAYMENT_RETURNED",
    "RESOLUTION_END_TO_END_REFERENCE",
    "RESOLUTION_IBAN_AMOUNT_DATE",
    "RESOLUTION_MANDATE_REFERENCE",
    "REVIEW_FLOOR",
    "STATUS_OPEN",
    "STATUS_PARTIAL",
    "STATUS_SETTLED",
    "Allocation",
    "BankTransactionInput",
    "Candidate",
    "CandidateScore",
    "CompensatingEntry",
    "Decision",
    "IbanOwnership",
    "MatchingEngineError",
    "Proposal",
    "ProviderIdentity",
    "ReceivableInput",
    "RenterProfileInput",
    "RestoredReceivable",
    "ReversalResult",
    "SettlementResult",
    "TieBreakUnspecifiedError",
    "normalize_comparison_text",
    "normalize_iban",
    "parse_provider_amount_to_cents",
    "propose",
    "reverse",
    "score_candidate",
    "settle",
    "should_learn_iban",
    "split_principal",
]
