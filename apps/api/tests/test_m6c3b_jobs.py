"""Acceptance surface for the M6-C3b scheduled jobs (`docs/15` § 5.6).

The pure engine already proves Page 08 and C3a already proves persistence. These
tests prove that running the same contract *on a schedule* changes nothing about
it: one account per run, consent before any pull, an idempotent import, an
``AUTO_MATCH`` that settles exactly once, a ``NEEDS_REVIEW`` that still moves zero
cents, a bounded refusal, and two read-only jobs that write nothing at all.

Every expected decision and cent comes from the single approved oracle in
``packages/rules-store/tests/berkay_15_golden.py``; none is copied here.

The graph is built here rather than imported from ``test_m6c3a_matching_service``:
a job suite that shares the C3a scenario would inherit its thirteen movements and
could no longer say which run produced which row. The gateway is a test-local
``BankGateway`` implementation, not ``StubBankGateway`` — the stub answers with
fixed demo rows for one hard-coded bank account and could prove neither the
consent gate nor account isolation.

All job assertions run through ``account_scoped_session`` (the RLS ``lokara_app``
role). The owner engine seeds and is never used to assert isolation.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Final

import pytest
from alembic import command
from alembic.config import Config
from lokara_adapters import BankGateway
from lokara_adapters import BankTransaction as NormalizedTransaction
from lokara_api.jobs import (
    AIS_CONSENT_MAX_DAYS,
    BankAccountSyncResult,
    DeadlineWatchResult,
    SyncResult,
    expire_bank_consents,
    run_for_accounts,
    sync_bank_transactions,
    watch_deadlines,
)
from lokara_db import (
    Account,
    BankAccount,
    BankTransaction,
    Building,
    DbSettings,
    IbanHistory,
    MatchConfirmation,
    MatchProposal,
    Membership,
    PaymentAllocation,
    PaymentLedgerEntry,
    Person,
    Receivable,
    Renter,
    RenterMatchingProfile,
    Role,
    Tenancy,
    TenancyParty,
    Unit,
    account_scoped_session,
    create_db_engine,
    new_id,
)
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

_ROOT = Path(__file__).resolve().parents[3]
_ORACLE_DIR = _ROOT / "packages" / "rules-store" / "tests"
if str(_ORACLE_DIR) not in sys.path:
    sys.path.insert(0, str(_ORACLE_DIR))
from berkay_15_golden import PAGE_08_GOLDENS  # noqa: E402

_DB_DIR = _ROOT / "packages" / "db"

# `docs/15` § 5.6: time is an input, never the clock.
NOW: Final = datetime(2026, 8, 24, 6, 0, tzinfo=UTC)
TODAY: Final = date(2026, 8, 24)
WINDOW_FROM: Final = date(2026, 7, 1)
WINDOW_TO: Final = date(2026, 9, 1)
OVERDUE_DAYS: Final = 30
AUTO_IBAN: Final = "DE02120300000000202051"
UNKNOWN_IBAN: Final = "DE02500105170137075030"
FIFO_IBAN: Final = "DE89370400440532013000"
# The five append-only tables of `docs/15` § 6, plus the three a read-only job could
# quietly mutate without changing any of them: an UPDATE to `receivable.status` or
# `bank_account.consent_expires_at` and an INSERT into `iban_history` all leave the
# append-only counts untouched.
COUNTED_TABLES: Final = (
    "bank_transaction",
    "match_proposal",
    "match_confirmation",
    "payment_ledger_entry",
    "payment_allocation",
    "iban_history",
    "receivable",
    "bank_account",
)
#: Row versions the read-only jobs must not bump. `xmin` changes on any UPDATE,
#: including one that writes the same value back, which a count can never see.
VERSIONED_TABLES: Final = ("bank_account", "receivable")


def _integer(case_id: str, key: str) -> int:
    value = PAGE_08_GOLDENS[case_id][key]
    assert isinstance(value, int)
    return value


def _string(case_id: str, key: str) -> str:
    value = PAGE_08_GOLDENS[case_id][key]
    assert isinstance(value, str)
    return value


def _integers(case_id: str, key: str) -> tuple[int, ...]:
    value = PAGE_08_GOLDENS[case_id][key]
    assert isinstance(value, tuple)
    assert all(isinstance(item, int) for item in value)
    return tuple(int(item) for item in value)


class Graph:
    """Ids of the two-account scenario, so tests never guess a row."""

    def __init__(self) -> None:
        self.account_a = new_id()
        self.account_b = new_id()
        self.owner_a = new_id()
        self.owner_b = new_id()
        # Account A holds four bank accounts: three consent states, plus a second
        # consenting one whose id deliberately sorts *after* `bank_ok` while its
        # transaction was booked *earlier*. Ordering the merged run by
        # `bank_account_id` instead of by booking date is then visible in the
        # allocations, not merely suspected.
        self.bank_ok, self.bank_fifo = sorted((new_id(), new_id()))
        self.bank_missing = new_id()
        self.bank_expired = new_id()
        self.bank_b = new_id()
        self.auto_renter = new_id()
        self.review_renter = new_id()
        self.overdue_renter = new_id()
        self.fifo_renter = new_id()
        self.b_renter = new_id()
        self.auto_receivable = new_id()
        self.review_receivable = new_id()
        self.overdue_receivable = new_id()
        self.fifo_old_receivable = new_id()
        self.fifo_new_receivable = new_id()
        self.b_receivable = new_id()


class RecordingGateway:
    """Test-local `BankGateway`. It records every pull so a refused pull is provable."""

    def __init__(self, rows: dict[str, tuple[NormalizedTransaction, ...]]) -> None:
        self._rows = rows
        self.calls: list[str] = []

    def list_transactions(
        self, bank_account_id: str, window_from: date, window_to: date
    ) -> tuple[NormalizedTransaction, ...]:
        self.calls.append(bank_account_id)
        return tuple(
            row
            for row in self._rows.get(bank_account_id, ())
            if window_from <= row.bank_booking_date < window_to
        )


def _normalized(
    *,
    account_id: str,
    bank_account_id: str,
    provider_transaction_id: str,
    amount_cents: int,
    booking_date: date,
    counterpart_iban: str | None,
    counterpart_name: str | None,
    purpose: str | None,
    end_to_end_reference: str | None,
) -> NormalizedTransaction:
    return NormalizedTransaction(
        account_id=account_id,
        bank_account_id=bank_account_id,
        provider_transaction_id=provider_transaction_id,
        amount_cents=amount_cents,
        bank_booking_date=booking_date,
        finapi_booking_date=booking_date,
        value_date=booking_date,
        counterpart_iban=counterpart_iban,
        counterpart_name=counterpart_name,
        purpose=purpose,
        end_to_end_reference=end_to_end_reference,
        counterpart_mandate_reference=None,
        bank_transaction_code="RETURN" if amount_cents < 0 else "SEPA-CT",
        provider_type="DEBIT" if amount_cents < 0 else "CREDIT",
        is_potential_duplicate=False,
    )


def _gateway_rows(graph: Graph) -> dict[str, tuple[NormalizedTransaction, ...]]:
    """The provider window. Two of these bank accounts must never be pulled."""
    auto_amount = _integer("BANKMATCH-F01", "amount")
    review_amount = _integer("BANKMATCH-F02", "amount")
    reversal_amount = _integer("BANKMATCH-F06", "reversal_amount")
    return {
        graph.bank_ok: (
            _normalized(
                account_id=graph.account_a,
                bank_account_id=graph.bank_ok,
                provider_transaction_id="c3b-auto",
                amount_cents=auto_amount,
                booking_date=date(2026, 7, 5),
                counterpart_iban=AUTO_IBAN,
                counterpart_name="Automann",
                purpose="Miete 2026-07",
                end_to_end_reference="E2E-C3B-AUTO",
            ),
            _normalized(
                account_id=graph.account_a,
                bank_account_id=graph.bank_ok,
                provider_transaction_id="c3b-review",
                amount_cents=review_amount,
                booking_date=date(2026, 7, 6),
                counterpart_iban=UNKNOWN_IBAN,
                counterpart_name="Pruefmann",
                # `docs/15` § 4 reads the surname out of the *purpose*, not the
                # counterpart name, so F02's 10-point signal needs it here.
                purpose="Zahlung Pruefmann",
                end_to_end_reference="E2E-C3B-REVIEW",
            ),
            # A return that names an original which does not exist: the § 5.3
            # reversal path must refuse it. It is booked last so the refusal
            # cannot be mistaken for an aborted run.
            # The later half of the FIFO pair, on the bank account whose id sorts
            # first. F01 supplies the amount; the unique IBAN makes it Auto.
            _normalized(
                account_id=graph.account_a,
                bank_account_id=graph.bank_ok,
                provider_transaction_id="c3b-fifo-late",
                amount_cents=auto_amount,
                booking_date=date(2026, 7, 4),
                counterpart_iban=FIFO_IBAN,
                counterpart_name="Fifomann",
                purpose=None,
                end_to_end_reference="E2E-C3B-FIFO-LATE",
            ),
            _normalized(
                account_id=graph.account_a,
                bank_account_id=graph.bank_ok,
                provider_transaction_id="c3b-refused",
                amount_cents=reversal_amount,
                booking_date=date(2026, 7, 7),
                counterpart_iban=AUTO_IBAN,
                counterpart_name="Automann",
                purpose=None,
                end_to_end_reference="E2E-C3B-NO-SUCH-ORIGINAL",
            ),
        ),
        # Booked two days before the `bank_ok` payment above, on an id that sorts
        # after it: F11's partial payment for the same renter.
        graph.bank_fifo: (
            _normalized(
                account_id=graph.account_a,
                bank_account_id=graph.bank_fifo,
                provider_transaction_id="c3b-fifo-early",
                amount_cents=_integer("BANKMATCH-F11", "payment"),
                booking_date=date(2026, 7, 2),
                counterpart_iban=FIFO_IBAN,
                counterpart_name="Fifomann",
                purpose=None,
                end_to_end_reference="E2E-C3B-FIFO-EARLY",
            ),
        ),
        graph.bank_missing: (
            _normalized(
                account_id=graph.account_a,
                bank_account_id=graph.bank_missing,
                provider_transaction_id="c3b-no-consent",
                amount_cents=_integer("BANKMATCH-F01", "amount"),
                booking_date=date(2026, 7, 8),
                counterpart_iban=AUTO_IBAN,
                counterpart_name="Automann",
                purpose=None,
                end_to_end_reference="E2E-C3B-NO-CONSENT",
            ),
        ),
        graph.bank_expired: (
            _normalized(
                account_id=graph.account_a,
                bank_account_id=graph.bank_expired,
                provider_transaction_id="c3b-expired-consent",
                amount_cents=_integer("BANKMATCH-F01", "amount"),
                booking_date=date(2026, 7, 9),
                counterpart_iban=AUTO_IBAN,
                counterpart_name="Automann",
                purpose=None,
                end_to_end_reference="E2E-C3B-EXPIRED",
            ),
        ),
        graph.bank_b: (
            _normalized(
                account_id=graph.account_b,
                bank_account_id=graph.bank_b,
                provider_transaction_id="c3b-foreign",
                amount_cents=_integer("BANKMATCH-F01", "amount"),
                booking_date=date(2026, 7, 10),
                counterpart_iban=AUTO_IBAN,
                counterpart_name="Fremdmann",
                purpose="Miete 2026-07",
                end_to_end_reference="E2E-C3B-FOREIGN",
            ),
        ),
    }


def _seed_renter(
    session: Session,
    *,
    account_id: str,
    renter_id: str,
    receivable_id: str,
    surname: str,
    period: str,
    due_date: date,
    expected_cents: int,
    open_cents: int,
    status: str,
    components: tuple[int, int, int],
    with_profile: bool = True,
) -> str:
    building_id, unit_id, tenancy_id = new_id(), new_id(), new_id()
    session.add(
        Building(
            id=building_id,
            account_id=account_id,
            name=f"Haus {surname}",
            street="Testweg 1",
            postal_code="10115",
            city="Berlin",
        )
    )
    session.add(Renter(id=renter_id, account_id=account_id, legal_name=surname))
    session.flush()
    session.add(
        Unit(
            id=unit_id,
            account_id=account_id,
            building_id=building_id,
            label=surname,
            area_sqm_x100=5000,
        )
    )
    session.flush()
    session.add(
        Tenancy(
            id=tenancy_id,
            account_id=account_id,
            unit_id=unit_id,
            valid_from=date(2025, 1, 1),
            valid_to=None,
            base_rent_cents=components[0],
        )
    )
    session.flush()
    session.add(
        TenancyParty(id=new_id(), account_id=account_id, tenancy_id=tenancy_id, renter_id=renter_id)
    )
    session.flush()
    if with_profile:
        session.add(
            RenterMatchingProfile(
                id=new_id(),
                account_id=account_id,
                renter_id=renter_id,
                payment_code=None,
                normalized_surname=surname.lower(),
            )
        )
    _add_receivable(
        session,
        account_id=account_id,
        renter_id=renter_id,
        tenancy_id=tenancy_id,
        receivable_id=receivable_id,
        period=period,
        due_date=due_date,
        expected_cents=expected_cents,
        open_cents=open_cents,
        status=status,
        components=components,
    )
    return tenancy_id


def _add_receivable(
    session: Session,
    *,
    account_id: str,
    renter_id: str,
    tenancy_id: str,
    receivable_id: str,
    period: str,
    due_date: date,
    expected_cents: int,
    open_cents: int,
    status: str,
    components: tuple[int, int, int],
) -> None:
    session.add(
        Receivable(
            id=receivable_id,
            account_id=account_id,
            renter_id=renter_id,
            tenancy_id=tenancy_id,
            source_type="RECURRING_RENT",
            source_id=None,
            period=period,
            due_date=due_date,
            expected_cents=expected_cents,
            open_cents=open_cents,
            status=status,
            category="rent",
            base_rent_cents=components[0],
            nk_advance_cents=components[1],
            heating_advance_cents=components[2],
            garage_cents=0,
            open_costs_cents=0,
            open_interest_cents=0,
            open_principal_cents=open_cents,
            stored_reference=None,
        )
    )
    session.flush()


def _learn_iban(
    session: Session,
    *,
    graph: Graph,
    account_id: str,
    owner_id: str,
    renter_id: str,
    receivable_id: str,
    bank_account_id: str,
    iban: str,
) -> None:
    """Page 08 derives a known IBAN only from active, confirmed history.

    Migration 0020 ties the row to a `CONFIRMED` proposal for that renter, so the
    evidence is built on a *different* prior movement. Never preload a proposal on
    a transaction whose immutable run a test is about.
    """
    learned_tx, proposal_id, confirmation_id = new_id(), new_id(), new_id()
    session.add(
        BankTransaction(
            id=learned_tx,
            account_id=account_id,
            bank_account_id=bank_account_id,
            provider_transaction_id=f"learned-{learned_tx}",
            amount_cents=1,
            bank_booking_date=date(2026, 1, 1),
            finapi_booking_date=date(2026, 1, 1),
            value_date=date(2026, 1, 1),
            counterpart_iban=iban,
            counterpart_name=None,
            purpose=None,
            end_to_end_reference=None,
            counterpart_mandate_reference=None,
            bank_transaction_code="SEPA-CT",
            provider_type="CREDIT",
            is_potential_duplicate=False,
        )
    )
    session.flush()
    session.add(
        MatchProposal(
            id=proposal_id,
            account_id=account_id,
            bank_transaction_id=learned_tx,
            receivable_id=receivable_id,
            renter_id=renter_id,
            rank=1,
            signal_iban=0,
            signal_amount=0,
            signal_code_or_surname=10,
            signal_e2e=0,
            signal_period=0,
            confidence=10,
            decision="NEEDS_REVIEW",
            convention_version="docs/15 07/2026",
            reason_de="Frühere ausdrückliche Bestätigung.",
        )
    )
    session.flush()
    session.add(
        MatchConfirmation(
            id=confirmation_id,
            account_id=account_id,
            match_proposal_id=proposal_id,
            outcome="CONFIRMED",
            confirmed_by=owner_id,
        )
    )
    session.flush()
    session.add(
        IbanHistory(
            id=new_id(),
            account_id=account_id,
            renter_id=renter_id,
            normalized_iban=iban,
            valid_from=datetime(2026, 1, 1, tzinfo=UTC),
            valid_to=None,
            learned_from_transaction_id=learned_tx,
            confirmed_match_id=confirmation_id,
            confirmed_by=owner_id,
        )
    )
    session.flush()
    assert graph.auto_renter  # the graph owns every id this helper was given


@pytest.fixture(scope="module")
def live() -> Iterator[tuple[Graph, Engine]]:
    settings = DbSettings()
    try:
        owner = create_db_engine(settings.direct_url)
        with owner.connect() as connection:
            connection.execute(text((_DB_DIR / "scripts" / "init-app-role.sql").read_text()))
            connection.commit()
    except OperationalError as exc:
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")
    command.upgrade(Config(str(_DB_DIR / "alembic.ini")), "head")

    graph = Graph()
    nominal = _integers("BANKMATCH-F11", "nominal_components")
    auto_amount = _integer("BANKMATCH-F01", "amount")
    with Session(owner) as session, session.begin():
        session.add_all(
            [
                Account(id=graph.account_a, name="M6-C3b A"),
                Account(id=graph.account_b, name="M6-C3b B"),
                Person(id=graph.owner_a, email=f"{graph.owner_a}@example.test"),
                Person(id=graph.owner_b, email=f"{graph.owner_b}@example.test"),
            ]
        )
        session.flush()
        session.add_all(
            [
                Membership(
                    id=new_id(),
                    person_id=graph.owner_a,
                    account_id=graph.account_a,
                    role=Role.OWNER,
                ),
                Membership(
                    id=new_id(),
                    person_id=graph.owner_b,
                    account_id=graph.account_b,
                    role=Role.OWNER,
                ),
                BankAccount(
                    id=graph.bank_ok,
                    account_id=graph.account_a,
                    provider="finapi",
                    provider_account_id=f"provider-{graph.bank_ok}",
                    normalized_iban="DE02100500000054540402",
                    display_name="Mietkonto",
                    consent_expires_at=NOW + timedelta(days=60),
                ),
                BankAccount(
                    id=graph.bank_fifo,
                    account_id=graph.account_a,
                    provider="finapi",
                    provider_account_id=f"provider-{graph.bank_fifo}",
                    normalized_iban="DE02600501010002034304",
                    display_name="Zweitkonto",
                    consent_expires_at=NOW + timedelta(days=60),
                ),
                BankAccount(
                    id=graph.bank_missing,
                    account_id=graph.account_a,
                    provider="finapi",
                    provider_account_id=f"provider-{graph.bank_missing}",
                    normalized_iban="DE02300209000106531065",
                    display_name="Konto ohne Zustimmung",
                    consent_expires_at=None,
                ),
                BankAccount(
                    id=graph.bank_expired,
                    account_id=graph.account_a,
                    provider="finapi",
                    provider_account_id=f"provider-{graph.bank_expired}",
                    normalized_iban="DE02200505501015871393",
                    display_name="Konto mit abgelaufener Zustimmung",
                    consent_expires_at=NOW - timedelta(days=1),
                ),
                BankAccount(
                    id=graph.bank_b,
                    account_id=graph.account_b,
                    provider="finapi",
                    provider_account_id=f"provider-{graph.bank_b}",
                    normalized_iban="DE02701500000000594937",
                    display_name="Fremdkonto",
                    consent_expires_at=NOW + timedelta(days=60),
                ),
            ]
        )
        session.flush()

        # Account A — the Auto renter: exact amount, designated period, known IBAN.
        _seed_renter(
            session,
            account_id=graph.account_a,
            renter_id=graph.auto_renter,
            receivable_id=graph.auto_receivable,
            surname="Automann",
            period="2026-07",
            due_date=date(2026, 7, 3),
            expected_cents=auto_amount,
            open_cents=auto_amount,
            status="open",
            components=(nominal[0], nominal[1], nominal[2]),
        )
        _learn_iban(
            session,
            graph=graph,
            account_id=graph.account_a,
            owner_id=graph.owner_a,
            renter_id=graph.auto_renter,
            receivable_id=graph.auto_receivable,
            bank_account_id=graph.bank_ok,
            iban=AUTO_IBAN,
        )
        # The Review renter: exact amount and surname only, no known IBAN, and a
        # period that cannot match, so its confidence is the F02 value exactly.
        _seed_renter(
            session,
            account_id=graph.account_a,
            renter_id=graph.review_renter,
            receivable_id=graph.review_receivable,
            surname="Pruefmann",
            period="2026-09",
            due_date=date(2026, 9, 3),
            expected_cents=_integer("BANKMATCH-F02", "amount"),
            open_cents=_integer("BANKMATCH-F02", "amount"),
            status="open",
            components=(nominal[0], nominal[1], nominal[2]),
        )
        # The Overdue renter has no matching profile, so it is never a candidate and
        # only the watcher ever sees it. F11 supplies its partial-payment shape.
        _seed_renter(
            session,
            account_id=graph.account_a,
            renter_id=graph.overdue_renter,
            receivable_id=graph.overdue_receivable,
            surname="Saeumig",
            period="2026-06",
            due_date=TODAY - timedelta(days=OVERDUE_DAYS),
            expected_cents=_integer("BANKMATCH-F11", "expected"),
            open_cents=_integer("BANKMATCH-F11", "open_after"),
            status=_string("BANKMATCH-F11", "status_after"),
            components=(nominal[0], nominal[1], nominal[2]),
            with_profile=False,
        )
        # The FIFO renter owes two months and is paid twice, once per bank account.
        # `docs/15` § 5.1 settles a renter's debts due-first across *all* of their
        # payments, so which receivable each payment lands on is the observable
        # difference between merging the run by booking date and looping per bank
        # account. F11 supplies both the partial payment and its component split.
        fifo_tenancy = _seed_renter(
            session,
            account_id=graph.account_a,
            renter_id=graph.fifo_renter,
            receivable_id=graph.fifo_old_receivable,
            surname="Fifomann",
            period="2026-05",
            due_date=date(2026, 5, 3),
            expected_cents=_integer("BANKMATCH-F11", "expected"),
            open_cents=_integer("BANKMATCH-F11", "expected"),
            status="open",
            components=(nominal[0], nominal[1], nominal[2]),
        )
        _add_receivable(
            session,
            account_id=graph.account_a,
            renter_id=graph.fifo_renter,
            tenancy_id=fifo_tenancy,
            receivable_id=graph.fifo_new_receivable,
            period="2026-06",
            due_date=date(2026, 6, 3),
            expected_cents=_integer("BANKMATCH-F11", "expected"),
            open_cents=_integer("BANKMATCH-F11", "expected"),
            status="open",
            components=(nominal[0], nominal[1], nominal[2]),
        )
        _learn_iban(
            session,
            graph=graph,
            account_id=graph.account_a,
            owner_id=graph.owner_a,
            renter_id=graph.fifo_renter,
            receivable_id=graph.fifo_old_receivable,
            bank_account_id=graph.bank_fifo,
            iban=FIFO_IBAN,
        )
        # Account B, identical in shape. Nothing about it may appear in an A run.
        _seed_renter(
            session,
            account_id=graph.account_b,
            renter_id=graph.b_renter,
            receivable_id=graph.b_receivable,
            surname="Fremdmann",
            period="2026-07",
            due_date=date(2026, 7, 3),
            expected_cents=auto_amount,
            open_cents=auto_amount,
            status="open",
            components=(nominal[0], nominal[1], nominal[2]),
        )
    yield graph, create_db_engine(settings.database_url)


def _row_versions(engine: Engine, account_id: str) -> dict[str, str]:
    """`table:id -> xmin`. Any UPDATE bumps `xmin`, even one writing the same value."""
    with account_scoped_session(engine, account_id) as session:
        return {
            f"{table}:{row_id}": version
            for table in VERSIONED_TABLES
            for row_id, version in session.execute(
                text(f"SELECT id, xmin::text FROM {table}")
            ).all()
        }


def _counts(engine: Engine, account_id: str) -> dict[str, int]:
    with account_scoped_session(engine, account_id) as session:
        return {
            table: int(session.scalar(text(f"SELECT count(*) FROM {table}")) or 0)
            for table in COUNTED_TABLES
        }


def _run_sync(engine: Engine, graph: Graph, account_id: str) -> tuple[SyncResult, RecordingGateway]:
    gateway: BankGateway = RecordingGateway(_gateway_rows(graph))
    with account_scoped_session(engine, account_id) as session:
        result = sync_bank_transactions(
            session,
            account_id=account_id,
            window_from=WINDOW_FROM,
            window_to=WINDOW_TO,
            gateway=gateway,
            now=NOW,
        )
    assert isinstance(gateway, RecordingGateway)
    return result, gateway


@pytest.fixture(scope="module")
def first_sync(live: tuple[Graph, Engine]) -> tuple[SyncResult, RecordingGateway]:
    graph, engine = live
    return _run_sync(engine, graph, graph.account_a)


def _for_bank(result: SyncResult, bank_account_id: str) -> BankAccountSyncResult:
    accounts = result.bank_accounts
    matching = [item for item in accounts if item.bank_account_id == bank_account_id]
    assert len(matching) == 1, f"expected exactly one result for {bank_account_id}"
    return matching[0]


def test_sync_reports_only_the_account_it_was_given(
    live: tuple[Graph, Engine], first_sync: tuple[SyncResult, RecordingGateway]
) -> None:
    """CLAUDE.md § 3.3 and `docs/15` § 5.6: one account per run."""
    graph, engine = live
    result, gateway = first_sync

    assert result.account_id == graph.account_a
    reported = [item.bank_account_id for item in result.bank_accounts]
    assert graph.bank_b not in reported
    assert sorted(reported) == reported, "bank_accounts must be sorted by bank_account_id"
    assert set(reported) == {
        graph.bank_ok,
        graph.bank_fifo,
        graph.bank_missing,
        graph.bank_expired,
    }
    assert graph.bank_b not in gateway.calls

    with account_scoped_session(engine, graph.account_b) as session:
        assert session.scalar(select(func.count()).select_from(BankTransaction)) == 0
        assert session.scalar(select(func.count()).select_from(MatchProposal)) == 0
        assert session.scalar(select(func.count()).select_from(PaymentLedgerEntry)) == 0
        foreign = session.get(Receivable, graph.b_receivable)
        assert foreign is not None
        assert foreign.status == "open"
        assert foreign.open_cents == _integer("BANKMATCH-F01", "amount")


def test_consent_gates_the_pull(
    live: tuple[Graph, Engine], first_sync: tuple[SyncResult, RecordingGateway]
) -> None:
    """`docs/15` § 5.6: no live consent, no pull — and no import either."""
    graph, engine = live
    _, gateway = first_sync

    missing = _for_bank(first_sync[0], graph.bank_missing)
    assert missing.skipped_reason == "consent_missing"
    assert missing.imported == 0

    expired = _for_bank(first_sync[0], graph.bank_expired)
    assert expired.skipped_reason == "consent_expired"
    assert expired.imported == 0

    granted = _for_bank(first_sync[0], graph.bank_ok)
    assert granted.skipped_reason is None
    assert granted.imported == 4

    second = _for_bank(first_sync[0], graph.bank_fifo)
    assert second.skipped_reason is None
    assert second.imported == 1

    # The refusal is the pull itself, not a filter applied afterwards: only the two
    # consenting accounts were ever asked, in `bank_account_id` order.
    assert gateway.calls == [graph.bank_ok, graph.bank_fifo]

    with account_scoped_session(engine, graph.account_a) as session:
        stored = set(
            session.scalars(
                select(BankTransaction.provider_transaction_id).where(
                    BankTransaction.bank_account_id.in_([graph.bank_missing, graph.bank_expired])
                )
            ).all()
        )
    assert stored == set()


def test_second_sync_imports_nothing_and_books_nothing(
    live: tuple[Graph, Engine], first_sync: tuple[SyncResult, RecordingGateway]
) -> None:
    """`docs/15` § 3.1: an exact re-import is skipped, never re-scored."""
    graph, engine = live
    before = _counts(engine, graph.account_a)

    result, _ = _run_sync(engine, graph, graph.account_a)
    granted = _for_bank(result, graph.bank_ok)

    assert granted.imported == 0
    assert granted.skipped_as_duplicate == 4
    second = _for_bank(result, graph.bank_fifo)
    assert second.imported == 0
    assert second.skipped_as_duplicate == 1
    assert _counts(engine, graph.account_a) == before


def test_auto_match_settles_exactly_once(
    live: tuple[Graph, Engine], first_sync: tuple[SyncResult, RecordingGateway]
) -> None:
    """`docs/15` § 5.6: an `AUTO_MATCH` settles on a schedule, on the § 5 terms."""
    graph, engine = live
    granted = _for_bank(first_sync[0], graph.bank_ok)

    # `bank_ok` carries two Auto movements: this one and the later half of the FIFO
    # pair, which `test_merged_run_settles_fifo_by_booking_date` owns.
    assert granted.auto_matched == 2
    assert granted.needs_review == 1
    assert granted.deduped == 0
    assert granted.reversed_payments == 0

    with account_scoped_session(engine, graph.account_a) as session:
        transaction = session.scalar(
            select(BankTransaction).where(
                BankTransaction.provider_transaction_id == "c3b-auto",
                BankTransaction.bank_account_id == graph.bank_ok,
            )
        )
        assert transaction is not None
        proposals = session.scalars(
            select(MatchProposal)
            .where(MatchProposal.bank_transaction_id == transaction.id)
            .order_by(MatchProposal.rank)
        ).all()
        assert proposals[0].decision == "AUTO_MATCH"
        assert proposals[0].renter_id == graph.auto_renter
        assert proposals[0].confidence == _integer("BANKMATCH-F01", "confidence")
        assert (
            proposals[0].signal_iban,
            proposals[0].signal_amount,
            proposals[0].signal_code_or_surname,
            proposals[0].signal_e2e,
            proposals[0].signal_period,
        ) == _integers("BANKMATCH-F01", "signals")

        entries = session.scalars(
            select(PaymentLedgerEntry).where(
                PaymentLedgerEntry.bank_transaction_id == transaction.id
            )
        ).all()
        assert len(entries) == 1
        assert entries[0].amount_cents == _integer("BANKMATCH-F01", "amount")
        assert granted.settled == 2

        allocations = session.scalars(
            select(PaymentAllocation).where(PaymentAllocation.ledger_entry_id == entries[0].id)
        ).all()
        assigned = sum(
            row.costs_cents + row.interest_cents + row.principal_cents for row in allocations
        )
        assert assigned == _integer("BANKMATCH-F01", "assigned")

        settled = session.get(Receivable, graph.auto_receivable)
        assert settled is not None
        assert settled.open_cents == _integer("BANKMATCH-F01", "open_after")
        assert settled.status == _string("BANKMATCH-F01", "status_after")

    # A repeat run books nothing more against the same movement.
    _run_sync(engine, graph, graph.account_a)
    with account_scoped_session(engine, graph.account_a) as session:
        repeated = session.scalar(
            select(func.count())
            .select_from(PaymentLedgerEntry)
            .join(
                BankTransaction,
                BankTransaction.id == PaymentLedgerEntry.bank_transaction_id,
            )
            .where(
                PaymentLedgerEntry.kind == "PAYMENT",
                BankTransaction.provider_transaction_id == "c3b-auto",
            )
        )
        assert repeated == 1


def test_needs_review_moves_no_money(
    live: tuple[Graph, Engine], first_sync: tuple[SyncResult, RecordingGateway]
) -> None:
    """`docs/15` § 5.4: a schedule never stands in for the user decision."""
    graph, engine = live

    with account_scoped_session(engine, graph.account_a) as session:
        transaction = session.scalar(
            select(BankTransaction).where(
                BankTransaction.provider_transaction_id == "c3b-review",
                BankTransaction.bank_account_id == graph.bank_ok,
            )
        )
        assert transaction is not None
        proposals = session.scalars(
            select(MatchProposal)
            .where(MatchProposal.bank_transaction_id == transaction.id)
            .order_by(MatchProposal.rank)
        ).all()
        assert proposals[0].decision == "NEEDS_REVIEW"
        assert proposals[0].renter_id == graph.review_renter
        assert proposals[0].confidence == _integer("BANKMATCH-F02", "confidence")
        assert (
            session.scalar(
                select(func.count())
                .select_from(PaymentLedgerEntry)
                .where(PaymentLedgerEntry.bank_transaction_id == transaction.id)
            )
            == 0
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(MatchConfirmation)
                .where(MatchConfirmation.match_proposal_id == proposals[0].id)
            )
            == 0
        )
        open_review = session.get(Receivable, graph.review_receivable)
        assert open_review is not None
        assert open_review.open_cents == _integer("BANKMATCH-F02", "amount")
        assert open_review.status == "open"


def test_one_refusal_does_not_discard_the_rest_of_the_run(
    live: tuple[Graph, Engine], first_sync: tuple[SyncResult, RecordingGateway]
) -> None:
    """`docs/15` § 5.6: each match runs in its own SAVEPOINT."""
    graph, engine = live
    granted = _for_bank(first_sync[0], graph.bank_ok)

    with account_scoped_session(engine, graph.account_a) as session:
        refused_id = session.scalar(
            select(BankTransaction.id).where(
                BankTransaction.provider_transaction_id == "c3b-refused",
                BankTransaction.bank_account_id == graph.bank_ok,
            )
        )
        assert refused_id is not None, "a refused match keeps its imported evidence"

    refusals = granted.refused
    assert [item.bank_transaction_id for item in refusals] == [refused_id]
    assert refusals[0].reason, "a refusal must say why"
    # The refusal rolled back alone: every other movement kept its outcome.
    assert granted.imported == 4
    assert granted.auto_matched == 2
    assert granted.needs_review == 1

    with account_scoped_session(engine, graph.account_a) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(PaymentLedgerEntry)
                .where(PaymentLedgerEntry.bank_transaction_id == refused_id)
            )
            == 0
        )


def _allocations(
    session: Session, provider_transaction_id: str
) -> tuple[PaymentLedgerEntry, dict[str, PaymentAllocation]]:
    """The one payment booked for a movement, keyed by the receivable it settled."""
    entries = session.scalars(
        select(PaymentLedgerEntry)
        .join(BankTransaction, BankTransaction.id == PaymentLedgerEntry.bank_transaction_id)
        .where(BankTransaction.provider_transaction_id == provider_transaction_id)
    ).all()
    assert len(entries) == 1, f"exactly one ledger entry for {provider_transaction_id}"
    rows = session.scalars(
        select(PaymentAllocation).where(PaymentAllocation.ledger_entry_id == entries[0].id)
    ).all()
    by_receivable = {row.receivable_id: row for row in rows}
    assert len(by_receivable) == len(rows), "one allocation per receivable"
    return entries[0], by_receivable


def _assigned(allocation: PaymentAllocation) -> int:
    return allocation.costs_cents + allocation.interest_cents + allocation.principal_cents


def test_merged_run_settles_fifo_by_booking_date(
    live: tuple[Graph, Engine], first_sync: tuple[SyncResult, RecordingGateway]
) -> None:
    """`docs/15` §§ 5.1 and 5.6: one merged order for the whole run.

    Both payments belong to one renter but arrive on two bank accounts. The earlier
    booking sits on `bank_fifo`, whose id sorts *after* `bank_ok`. Matching each bank
    account to completion in turn would therefore process the later payment first and
    settle the May debt with it, leaving the earlier payment on June. Ordering the
    merged list by `(bank_booking_date, provider_transaction_id)` puts F11's partial
    payment on May instead. The allocations below are the difference, so the rule is
    pinned by a fixture rather than by a comment.
    """
    graph, engine = live
    paid = _integers("BANKMATCH-F11", "paid_components")
    partial = _integer("BANKMATCH-F11", "payment")
    remainder = _integer("BANKMATCH-F11", "open_after")

    assert graph.bank_ok < graph.bank_fifo, "the later payment must sit on the lower id"
    assert _for_bank(first_sync[0], graph.bank_fifo).auto_matched == 1

    with account_scoped_session(engine, graph.account_a) as session:
        early_entry, early = _allocations(session, "c3b-fifo-early")
        late_entry, late = _allocations(session, "c3b-fifo-late")

        assert early_entry.amount_cents == partial
        assert list(early) == [graph.fifo_old_receivable], (
            "the payment booked first settles the oldest debt, not the one the "
            "lower bank_account_id happened to carry"
        )
        may = early[graph.fifo_old_receivable]
        assert _assigned(may) == partial
        assert (may.base_rent_cents, may.nk_advance_cents, may.heating_advance_cents) == paid
        assert may.resulting_status == _string("BANKMATCH-F11", "status_after")

        assert late_entry.amount_cents == _integer("BANKMATCH-F01", "amount")
        assert set(late) == {graph.fifo_old_receivable, graph.fifo_new_receivable}
        may_rest = late[graph.fifo_old_receivable]
        assert _assigned(may_rest) == remainder
        assert may_rest.resulting_status == "settled"
        june = late[graph.fifo_new_receivable]
        assert _assigned(june) == partial
        assert (june.base_rent_cents, june.nk_advance_cents, june.heating_advance_cents) == paid
        assert june.resulting_status == _string("BANKMATCH-F11", "status_after")

        # sum(shares) == input_total: the second payment is fully assigned.
        assert _assigned(may_rest) + _assigned(june) == late_entry.amount_cents

        older = session.get(Receivable, graph.fifo_old_receivable)
        newer = session.get(Receivable, graph.fifo_new_receivable)
        assert older is not None and newer is not None
        assert (older.open_cents, older.status) == (0, "settled")
        assert (newer.open_cents, newer.status) == (
            remainder,
            _string("BANKMATCH-F11", "status_after"),
        )


def test_read_only_jobs_write_nothing(
    live: tuple[Graph, Engine], first_sync: tuple[SyncResult, RecordingGateway]
) -> None:
    """`docs/15` § 5.6: cleanup stops the pull; § 147 AO keeps every row.

    Row counts alone cannot carry this claim. An UPDATE to `receivable.status`,
    `receivable.open_cents` or `bank_account.consent_expires_at` leaves every count
    identical, so the counts are backed here by two checks that see a write: the
    session must hold nothing pending after either job, and no `xmin` of the rows
    these jobs actually read may move.
    """
    graph, engine = live
    before = _counts(engine, graph.account_a)
    before_versions = _row_versions(engine, graph.account_a)
    assert before_versions, "the xmin snapshot must not be silently empty"

    with account_scoped_session(engine, graph.account_a) as session:
        findings = expire_bank_consents(session, account_id=graph.account_a, now=NOW)
        # Nothing is queued for INSERT, UPDATE or DELETE — not even a write that a
        # later flush would have carried out on the caller's behalf.
        assert list(session.new) == []
        assert list(session.dirty) == []
        assert list(session.deleted) == []

        watch = watch_deadlines(session, account_id=graph.account_a, today=TODAY, now=NOW)
        assert list(session.new) == []
        assert list(session.dirty) == []
        assert list(session.deleted) == []

    assert _counts(engine, graph.account_a) == before
    # `xmin` moves on any UPDATE, including one that rewrites the same value.
    assert _row_versions(engine, graph.account_a) == before_versions
    assert watch.account_id == graph.account_a

    states = {item.bank_account_id: item.state for item in findings}
    assert states[graph.bank_missing] == "missing"
    assert states[graph.bank_expired] == "expired"
    # A stored expiry inside the ceiling is not a finding. The ceiling itself is a
    # Lokara Konvention (docs/15 § 1), never a default the job writes anywhere.
    assert graph.bank_ok not in states
    assert AIS_CONSENT_MAX_DAYS == 180
    with account_scoped_session(engine, graph.account_a) as session:
        untouched = session.get(BankAccount, graph.bank_expired)
        assert untouched is not None
        assert untouched.consent_expires_at is not None


def test_watcher_reports_overdue_facts_only(
    live: tuple[Graph, Engine], first_sync: tuple[SyncResult, RecordingGateway]
) -> None:
    """`docs/15` § 5.6: facts, with no docs/12 guard rule applied."""
    graph, engine = live
    with account_scoped_session(engine, graph.account_a) as session:
        watch = watch_deadlines(session, account_id=graph.account_a, today=TODAY, now=NOW)

    overdue = watch.overdue_receivables
    # The FIFO renter's June debt is only partly paid, so it is overdue too, and it
    # sorts first on `due_date`.
    assert [item.receivable_id for item in overdue] == [
        graph.fifo_new_receivable,
        graph.overdue_receivable,
    ]
    assert [(item.due_date, item.receivable_id) for item in overdue] == sorted(
        (item.due_date, item.receivable_id) for item in overdue
    )
    row = overdue[1]
    assert row.renter_id == graph.overdue_renter
    assert row.period == "2026-06"
    assert row.due_date == TODAY - timedelta(days=OVERDUE_DAYS)
    assert row.days_overdue == OVERDUE_DAYS
    assert row.open_cents == _integer("BANKMATCH-F11", "open_after")

    reported = {item.receivable_id for item in overdue}
    assert graph.auto_receivable not in reported, "a settled receivable is not overdue"
    assert graph.fifo_old_receivable not in reported, "a settled receivable is not overdue"
    assert graph.review_receivable not in reported, "a not-yet-due receivable is not overdue"


def test_run_for_accounts_runs_one_context_per_account(live: tuple[Graph, Engine]) -> None:
    """`docs/15` § 5.6: one `account_scoped_session` per id, in the order given."""
    graph, engine = live
    seen: list[str] = []

    def job(session: Session, account_id: str) -> DeadlineWatchResult:
        seen.append(str(session.scalar(text("SELECT current_setting('app.account_id', true)"))))
        return watch_deadlines(session, account_id=account_id, today=TODAY, now=NOW)

    order = [graph.account_a, graph.account_b]
    results = run_for_accounts(engine, order, job)

    assert [item.account_id for item in results] == order
    assert seen == order, "each job ran under its own RLS account context"
    # Account B sees only its own facts: its unpaid July rent, and no consent
    # finding, because its one bank account has a live stored expiry.
    assert [item.receivable_id for item in results[1].overdue_receivables] == [graph.b_receivable]
    assert [item.bank_account_id for item in results[1].consent_findings] == []
    a_reported = {item.receivable_id for item in results[0].overdue_receivables}
    assert graph.b_receivable not in a_reported
