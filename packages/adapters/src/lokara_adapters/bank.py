"""Bank port — PSD2 account information (AIS), normalized to `docs/15` § 3.1.

Reading a landlord's bank account requires a **licensed AISP**; we never build
that licence ourselves. The port normalizes whatever the provider returns into
``BankTransaction`` before any domain code sees it. `bank_booking_date` is the
tax-relevant **payment date** (cash basis, § 11 EStG) and is also what § 5.1 reads
to order due before not-due receivables — legally load-bearing, not metadata.

This replaces the pre-M6 shape (id, booking date, positive cents, direction).
`docs/15` § 10 recorded why that one could not be the contract: it had no account
or bank-account identity, one date instead of three, no E2E or mandate reference,
no transaction code or provider type, no potential-duplicate flag, and its stub
ignored the `bank_account_id` it was given, so it could prove neither account
isolation nor provider-ID uniqueness.

TODO(provider): the real implementation consumes finAPI/Tink (EU + AVV, listed
sub-processor). Only this module ever imports that SDK.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

# docs/15 § 3.1 gives the counterpart name a maximum of 80 characters, which is
# also the SEPA pain/camt name length — a longer value is already non-conformant
# at the provider. Truncating here keeps a malformed provider row importable
# instead of dropping a real payment; matching normalizes this text anyway, and
# the untruncated value is not a matching signal.
_MAX_COUNTERPART_NAME = 80
_MAX_PURPOSE = 2000

_CENTS_PER_EURO = Decimal(100)


def cents_from_provider_amount(raw: str | Decimal) -> int:
    """A provider amount as signed integer cents, per `docs/15` § 3.1.

    Parsed as `Decimal`, multiplied by 100 and rounded `ROUND_HALF_UP`.
    `BANKMATCH-F10` pins both halves: `1080.00` is 108,000 cents and `1080.005`
    is 108,00**1** — banker's rounding would give 108,000 and be wrong here.

    `float` is refused rather than coerced. It is the single import boundary for
    money in this system, and a `float` that gets past it is a defect that no
    later integer assertion can see: `Decimal(1080.005)` is
    1080.00499999999999545252649113535881042480468750, which rounds *down*.
    """
    if isinstance(raw, float):
        raise TypeError(
            "provider amounts must be str or Decimal, never float — "
            "docs/15 § 3.1 forbids binary-float arithmetic on money"
        )
    return int((Decimal(raw) * _CENTS_PER_EURO).quantize(Decimal(1), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class BankTransaction:
    """`docs/15` § 3.1: the immutable normalized provider movement.

    `amount_cents` is **signed**. A negative amount (or a SEPA return code in
    `bank_transaction_code`) enters the § 5.3 reversal path; a positive amount
    enters scoring; zero is retained for import audit and ignored by matching.
    Sign replaced the old `direction` enum because the sign is what § 5.3 reads.

    `is_potential_duplicate` is *not* the re-import case and must never be
    conflated with it: a potential duplicate is kept and forces Review, while an
    exact re-import of `provider_transaction_id` is deduplicated before scoring
    and produces no second row. Identity is
    `(account_id, bank_account_id, provider_transaction_id)` — never the provider
    id alone, since providers do not allocate ids globally.
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


def _capped(value: str | None, limit: int) -> str | None:
    return value if value is None else value[:limit]


def normalize_transaction(
    *,
    account_id: str,
    bank_account_id: str,
    provider_transaction_id: str,
    amount: str | Decimal,
    bank_booking_date: date,
    finapi_booking_date: date,
    value_date: date,
    counterpart_iban: str | None = None,
    counterpart_name: str | None = None,
    purpose: str | None = None,
    end_to_end_reference: str | None = None,
    counterpart_mandate_reference: str | None = None,
    bank_transaction_code: str | None = None,
    provider_type: str | None = None,
    is_potential_duplicate: bool = False,
) -> BankTransaction:
    """The one place a provider payload becomes a `BankTransaction`.

    Keyword-only: the § 3.1 record has fifteen fields, seven of them nullable
    strings, and positional construction would silently swap an IBAN for a
    mandate reference.
    """
    return BankTransaction(
        account_id=account_id,
        bank_account_id=bank_account_id,
        provider_transaction_id=provider_transaction_id,
        amount_cents=cents_from_provider_amount(amount),
        bank_booking_date=bank_booking_date,
        finapi_booking_date=finapi_booking_date,
        value_date=value_date,
        counterpart_iban=counterpart_iban,
        counterpart_name=_capped(counterpart_name, _MAX_COUNTERPART_NAME),
        purpose=_capped(purpose, _MAX_PURPOSE),
        end_to_end_reference=end_to_end_reference,
        counterpart_mandate_reference=counterpart_mandate_reference,
        bank_transaction_code=bank_transaction_code,
        provider_type=provider_type,
        is_potential_duplicate=is_potential_duplicate,
    )


class BankGateway(Protocol):
    """Port: list booked transactions of one connected bank account."""

    def list_transactions(
        self, bank_account_id: str, window_from: date, window_to: date
    ) -> tuple[BankTransaction, ...]:
        """Transactions booked in the half-open window ``[window_from, window_to)``,
        for that bank account only."""
        ...


_DEMO_ACCOUNT_ID = "demo-account"
_DEMO_BANK_ACCOUNT_ID = "bank_acc_demo"

# Matches the seeded demo scenario (packages/db seed: base rent + NK advance per
# renter) plus the €1,200.00 garbage invoice of the canonical fixture as a debit —
# now a negative amount rather than a CREDIT/DEBIT flag.
_FIXTURE_TRANSACTIONS: tuple[BankTransaction, ...] = (
    normalize_transaction(
        account_id=_DEMO_ACCOUNT_ID,
        bank_account_id=_DEMO_BANK_ACCOUNT_ID,
        provider_transaction_id="tx_stub_001",
        amount="1170.00",  # Anna Beispiel: 950,00 € Miete + 220,00 € NK-Vorauszahlung
        bank_booking_date=date(2025, 1, 3),
        finapi_booking_date=date(2025, 1, 3),
        value_date=date(2025, 1, 3),
        counterpart_iban="DE02120300000000202051",
        counterpart_name="Anna Beispiel",
        purpose="Miete + NK Wohnung A Januar 2025",
        end_to_end_reference="E2E-STUB-001",
        bank_transaction_code="SEPA-CT",
        provider_type="CREDIT",
    ),
    normalize_transaction(
        account_id=_DEMO_ACCOUNT_ID,
        bank_account_id=_DEMO_BANK_ACCOUNT_ID,
        provider_transaction_id="tx_stub_002",
        amount="830.00",  # Bernd Muster: 680,00 € + 150,00 €
        bank_booking_date=date(2025, 1, 5),
        finapi_booking_date=date(2025, 1, 5),
        value_date=date(2025, 1, 5),
        counterpart_iban="DE02500105170137075030",
        counterpart_name="Bernd Muster",
        purpose="Miete Wohnung B 01/2025",
        bank_transaction_code="SEPA-CT",
        provider_type="CREDIT",
    ),
    normalize_transaction(
        account_id=_DEMO_ACCOUNT_ID,
        bank_account_id=_DEMO_BANK_ACCOUNT_ID,
        provider_transaction_id="tx_stub_003",
        amount="630.00",  # Clara Vorlage: 520,00 € + 110,00 €
        bank_booking_date=date(2025, 1, 5),
        finapi_booking_date=date(2025, 1, 5),
        value_date=date(2025, 1, 5),
        counterpart_iban="DE02100500000054540402",
        counterpart_name="Clara Vorlage",
        purpose="Miete Wohnung C Januar 2025",
        bank_transaction_code="SEPA-CT",
        provider_type="CREDIT",
    ),
    normalize_transaction(
        account_id=_DEMO_ACCOUNT_ID,
        bank_account_id=_DEMO_BANK_ACCOUNT_ID,
        provider_transaction_id="tx_stub_004",
        amount="-1200.00",  # the canonical €1,200.00 garbage cost, paid out
        bank_booking_date=date(2025, 12, 18),
        finapi_booking_date=date(2025, 12, 18),
        value_date=date(2025, 12, 18),
        counterpart_iban="DE02300209000106531065",
        counterpart_name="Stadtreinigung Frankfurt GmbH",
        purpose="Müllabfuhr Musterstraße 12 Jahresrechnung 2025",
        bank_transaction_code="SEPA-CT",
        provider_type="DEBIT",
    ),
)


class StubBankGateway:
    """Fixture stub for dev, tests, and the pitch demo — no network, no licence.

    Unlike its predecessor it **honours `bank_account_id`**. `docs/15` § 10 named
    the ignored argument as the reason the old stub could prove neither account
    isolation nor provider-ID uniqueness, and a stub that answers every id with
    the same rows cannot fail the test that matters.

    TODO(provider): swap for the AISP-backed adapter.
    """

    def list_transactions(
        self, bank_account_id: str, window_from: date, window_to: date
    ) -> tuple[BankTransaction, ...]:
        return tuple(
            t
            for t in _FIXTURE_TRANSACTIONS
            if t.bank_account_id == bank_account_id
            and window_from <= t.bank_booking_date < window_to
        )
