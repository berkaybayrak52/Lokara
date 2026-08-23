"""Normalized, immutable inputs for the bank-matching engine — `docs/15` § 3.

Everything the engine sees has already crossed the adapter boundary: money is integer
cents, dates are `datetime.date`, provider-specific spellings are gone.  The single
float boundary in the whole system is `parse_provider_amount_to_cents`, and it is a
`Decimal` boundary, not a `float` one (`docs/15` § 3.1: *"binary-float arithmetic is
forbidden"*).

Nothing in this module reads a clock, a file or an environment variable.  Every date
that matters — the booking date that decides due-ness, the due dates of the debts — is
passed in by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum

#: `docs/15` § 3.2 receivable states.  Kept as plain strings because the normalized
#: input arrives from a database column, not from this package.
STATUS_OPEN = "open"
STATUS_PARTIAL = "partial"
STATUS_SETTLED = "settled"

#: `docs/15` § 3.2 categories.
CATEGORY_RENT = "rent"
CATEGORY_NK_NACHZAHLUNG = "nk_nachzahlung"

_CENT_EXPONENT = Decimal(1)
_HUNDRED = Decimal(100)


class IbanOwnership(StrEnum):
    """How many active renters in *this* account own the transaction's IBAN.

    Resolved inside the account before any score is calculated (`docs/15` §§ 3.3, 6).
    It is an input, not something the engine derives, because the mapping lives in the
    versioned `IbanHistory` rows that a pure engine may not read.
    """

    #: Exactly one active renter mapping — the only Auto-Match key (`docs/15` § 4 step 3).
    UNIQUE = "unique"
    #: Two or more active renters share it; never Auto-Matches (`docs/15` § 4 step 4).
    SHARED = "shared"
    #: No active mapping in this account — the IBAN is not (yet) known.
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class BankTransactionInput:
    """One normalized provider movement (`docs/15` § 3.1).

    Exact re-import identity is the triple `(account_id, bank_account_id,
    provider_transaction_id)`.  A provider ID is unique only *together with* its account
    and bank-account identity, so the same ID under another account is a different
    movement — that is an account-isolation guarantee (`docs/15` § 6), not a cache key.

    `bank_booking_date`, **not** `finapi_booking_date`, decides whether a receivable is
    due (`docs/15` § 3.1).
    """

    account_id: str
    bank_account_id: str
    provider_transaction_id: str
    amount_cents: int
    bank_booking_date: date
    finapi_booking_date: date
    value_date: date
    counterpart_iban: str | None = None
    counterpart_name: str | None = None
    purpose: str | None = None
    end_to_end_reference: str | None = None
    counterpart_mandate_reference: str | None = None
    bank_transaction_code: str | None = None
    provider_type: str | None = None
    is_potential_duplicate: bool = False

    @property
    def provider_identity(self) -> tuple[str, str, str]:
        """The § 3.1 re-import identity triple, account-scoped by construction."""
        return (self.account_id, self.bank_account_id, self.provider_transaction_id)


@dataclass(frozen=True, slots=True)
class ReceivableInput:
    """One open or partial debt of one renter (`docs/15` § 3.2).

    The source calls its renter field `tenant_id`; Lokara normalizes that to `renter_id`
    (`CLAUDE.md` § 7 — a renter is never a "tenant" in the schema).

    `principal_components` is positional in the § 3.2 order
    `(base_rent, nk_advance, heating_advance, garage)` and sums to `expected_cents`.
    `open_cents` tracks the open *principal*; open costs and interest are separate, as
    § 3.2 spells out ("0 <= open <= expected plus separately open costs/interest").
    """

    id: str
    account_id: str
    renter_id: str
    tenancy_id: str
    source_type: str
    source_id: str | None
    period: str
    due_date: date
    expected_cents: int
    open_cents: int
    status: str
    category: str
    principal_components: tuple[int, ...]
    open_costs_cents: int
    open_interest_cents: int
    open_principal_cents: int


@dataclass(frozen=True, slots=True)
class RenterProfileInput:
    """The matching profile of one renter (`docs/15` § 3.3).

    `known_ibans` is derived by the caller from the *active* `IbanHistory` rows of this
    account.  History is versioned, never overwritten, so the engine receives a snapshot
    and never learns anything itself.
    """

    account_id: str
    renter_id: str
    payment_code: str | None
    normalized_surname: str
    known_ibans: tuple[str, ...]


def normalize_comparison_text(value: str | None) -> str:
    """Lowercase and strip spaces and special characters (`docs/15` § 4).

    Codes are then tested as substrings, which is exactly why the separators have to go:
    a purpose reading ``"KDNR-4711 / Miete"`` must match the stored code ``"KDNR-4711"``.
    """
    if value is None:
        return ""
    return "".join(character for character in value.lower() if character.isalnum())


def normalize_iban(value: str | None) -> str:
    """Uppercase, whitespace-free IBAN form used for every comparison in this engine."""
    if value is None:
        return ""
    return "".join(character for character in value if not character.isspace()).upper()


def parse_provider_amount_to_cents(amount: str | Decimal) -> int:
    """Convert a provider amount to signed integer cents (`docs/15` § 3.1, CSV row 180).

    The provider amount is parsed as `Decimal`, multiplied by 100 and rounded
    `ROUND_HALF_UP` — commercial rounding, decided on the exact decimal value.  This is
    the only place in the system where a decimal string becomes cents; everything
    downstream is integer-only.

    A `float` is refused rather than coerced.  Accepting one would reintroduce binary
    rounding at the one boundary this contract exists to isolate: `float("1080.005")` is
    already `1080.0049999...` before any rounding rule can be applied, which silently
    turns `BANKMATCH-F10`'s 108,001 into 108,000.
    """
    provided = type(amount).__name__
    if not isinstance(amount, str | Decimal):
        raise TypeError(
            "provider amounts are parsed from a decimal string or Decimal, never a "
            f"{provided}: docs/15 section 3.1 forbids binary-float arithmetic"
        )
    try:
        exact = Decimal(amount)
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"not a decimal provider amount: {amount!r}") from error
    if not exact.is_finite():
        raise ValueError(f"not a finite provider amount: {amount!r}")
    return int((exact * _HUNDRED).quantize(_CENT_EXPONENT, rounding=ROUND_HALF_UP))
