"""Bank port — PSD2 account information (AIS).

Reading a landlord's bank account requires a **licensed AISP**; we never build
that licence ourselves. The port normalizes whatever the provider returns into
``BankTransaction`` before any domain code sees it. The booking date is the
tax-relevant **payment date** (cash basis, § 11 EStG) — legally load-bearing,
not metadata.

TODO(provider): the real implementation consumes finAPI/Tink (EU + AVV, listed
sub-processor) at M6. Only this module ever imports that SDK.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Protocol

from lokara_domain import Cents, cents


class TransactionDirection(StrEnum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


@dataclass(frozen=True)
class BankTransaction:
    """A normalized booked transaction. Amounts are positive cents; the sign
    lives in ``direction`` so no caller has to guess a provider's convention."""

    id: str
    booking_date: date
    amount: Cents
    direction: TransactionDirection
    counterpart_name: str
    counterpart_iban: str
    purpose: str


class BankGateway(Protocol):
    """Port: list booked transactions of one connected bank account."""

    def list_transactions(
        self, bank_account_id: str, window_from: date, window_to: date
    ) -> tuple[BankTransaction, ...]:
        """Transactions booked in the half-open window ``[window_from, window_to)``."""
        ...


# Matches the seeded demo scenario (packages/db seed: base rent + NK advance per
# renter) plus the €1,200.00 garbage invoice of the canonical fixture as a debit.
_FIXTURE_TRANSACTIONS: tuple[BankTransaction, ...] = (
    BankTransaction(
        id="tx_stub_001",
        booking_date=date(2025, 1, 3),
        amount=cents(117000),  # Anna Beispiel: 950,00 € Miete + 220,00 € NK-Vorauszahlung
        direction=TransactionDirection.CREDIT,
        counterpart_name="Anna Beispiel",
        counterpart_iban="DE02120300000000202051",
        purpose="Miete + NK Wohnung A Januar 2025",
    ),
    BankTransaction(
        id="tx_stub_002",
        booking_date=date(2025, 1, 5),
        amount=cents(83000),  # Bernd Muster: 680,00 € + 150,00 €
        direction=TransactionDirection.CREDIT,
        counterpart_name="Bernd Muster",
        counterpart_iban="DE02500105170137075030",
        purpose="Miete Wohnung B 01/2025",
    ),
    BankTransaction(
        id="tx_stub_003",
        booking_date=date(2025, 1, 5),
        amount=cents(63000),  # Clara Vorlage: 520,00 € + 110,00 €
        direction=TransactionDirection.CREDIT,
        counterpart_name="Clara Vorlage",
        counterpart_iban="DE02100500000054540402",
        purpose="Miete Wohnung C Januar 2025",
    ),
    BankTransaction(
        id="tx_stub_004",
        booking_date=date(2025, 12, 18),
        amount=cents(120000),  # the canonical €1,200.00 garbage cost
        direction=TransactionDirection.DEBIT,
        counterpart_name="Stadtreinigung Frankfurt GmbH",
        counterpart_iban="DE02300209000106531065",
        purpose="Müllabfuhr Musterstraße 12 Jahresrechnung 2025",
    ),
)


class StubBankGateway:
    """Fixture stub for dev, tests, and the pitch demo — no network, no licence.

    TODO(provider): swap for the AISP-backed adapter at M6.
    """

    def list_transactions(
        self, bank_account_id: str, window_from: date, window_to: date
    ) -> tuple[BankTransaction, ...]:
        del bank_account_id  # the stub serves one fixture account
        return tuple(t for t in _FIXTURE_TRANSACTIONS if window_from <= t.booking_date < window_to)
