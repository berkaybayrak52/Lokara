"""M6-C3-0 invariant repair — the fixtures that must be red before migration 0020 exists.

The boundary audit of the M6-C2 slice found that `docs/02` § 6 claims invariants that
migration `0019` did not actually deliver, and that two constraints `0019` *did* create
contradict the matching engine's own fixture-verified output. Each test below carries its
repair id (`M6C3R-R01` … `M6C3R-R17`) in its docstring and is red for exactly one reason:
the constraint is missing, or the existing constraint is the wrong one.

`R01`–`R11` are red against `0019` and green once `0020` lands. `R13`–`R17` are the second
audit re-run of 23.08.2026 and are red against **`0020` as written** — H1 (a reversal's own
proposal shadows the reversed entry's renter), H2 (every trigger is neutralised by a
`pg_temp` shadow table, because no function sets `search_path` and `lokara_app` holds TEMP)
and M3-a (a learned IBAN carries no transaction provenance). `docs/02` § 6, "Open on `0020`",
records all six findings of that re-run; `R12`, `R18`–`R21` live in
`scripts/tests/test_rls_coverage_matcher.py` and `packages/db/tests/test_rls_isolation.py`.

Three rules govern how this module touches the database, because `payment_ledger_entry`,
`payment_allocation`, `bank_transaction`, `match_proposal`, `match_confirmation` and
`iban_history` all refuse DELETE (`0017`/`0019`) and therefore cannot be torn down:

1. Exactly one module-scoped graph is committed, under ids generated per run.
2. Every assertion runs inside a transaction that is rolled back unconditionally, so an
   insert accepted before the repair leaves nothing behind and a rerun cannot pass because the
   row it wanted to write is already there.
3. Nothing is written to the demo account.

`docs/15` § 5.3 and § 3.3, `packages/matching-engine/.../settlement.py` and `reversal.py`
are the sources for the shapes asserted here; the engine, not prose, decides what a
reversal allocation looks like.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import NamedTuple

import pytest
from alembic import command
from alembic.config import Config
from lokara_db import (
    Account,
    BankAccount,
    BankTransaction,
    Building,
    DbSettings,
    IbanHistory,
    MatchConfirmation,
    MatchProposal,
    PaymentAllocation,
    PaymentLedgerEntry,
    Person,
    Receivable,
    Renter,
    Tenancy,
    TenancyParty,
    Unit,
    create_db_engine,
    new_id,
)
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session

_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent

# Distinct IBANs per concern, so a unique-index collision can never masquerade as the
# invariant under test.
_IBAN_ACCOUNT = "DE02120300000000202051"
_IBAN_LEARNED = "DE02500105170137075030"
_IBAN_WRONG_RENTER = "DE02100500000054540402"
_IBAN_UNCONFIRMED = "DE02300209000106531065"
_IBAN_SHARED = "DE02200505501015871393"
_IBAN_REPLACED = "DE02701500000000594937"
_IBAN_NO_PROVENANCE = "DE02100100100006820101"
_IBAN_FOREIGN_TX = "DE02760100850002250803"


def _owner_engine() -> Engine:
    """The migration-role engine, with the schema guaranteed current.

    Same arrangement as the isolation suite (which owns its own copy): the tests apply
    the app role and `alembic upgrade head` themselves, so a plain `pytest` run needs
    only the docker-compose Postgres.
    """
    settings = DbSettings()
    owner = create_db_engine(settings.direct_url)
    with owner.connect() as conn:
        conn.execute(text((_DB_PACKAGE_DIR / "scripts" / "init-app-role.sql").read_text()))
        conn.commit()
    command.upgrade(Config(str(_DB_PACKAGE_DIR / "alembic.ini")), "head")
    return owner


@pytest.fixture(scope="module")
def owner() -> Iterator[Engine]:
    try:
        engine = _owner_engine()
    except OperationalError as exc:  # DB not running
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")
    yield engine
    engine.dispose()


class _Graph(NamedTuple):
    """One committed M6-C3 graph: two renters on one tenancy, one settled payment,
    its reversal, and one unallocated payment with head-room to write into."""

    account_id: str
    person_id: str
    building_id: str
    unit_id: str
    tenancy_id: str
    renter_one: str
    renter_two: str
    party_one: str
    party_two: str
    bank_account_id: str
    tx_payment: str
    tx_return: str
    tx_spare: str
    receivable_one: str
    receivable_two: str
    proposal_id: str
    proposal_spare: str
    confirmation_id: str
    entry_payment: str
    entry_reversal: str
    entry_spare: str
    allocation_id: str


@pytest.fixture(scope="module")
def graph(owner: Engine) -> _Graph:
    """Committed once per run and never torn down — every table below refuses DELETE.

    Renter one pays 1.080,00 €, which is reversed (`docs/15` F06). Renter two is a
    co-party of the same tenancy with an open 600,00 € debt, and is the "other renter"
    every C1/C2 fixture points at. `entry_spare` is a 600,00 € payment with no
    allocation yet, so a cross-renter allocation can be attempted without the
    per-entry cap refusing it for an unrelated reason.
    """
    ids = _Graph(*(new_id() for _ in range(22)))
    with Session(owner) as session, session.begin():
        session.add_all(
            [
                Account(id=ids.account_id, name=f"M6C3 Repair {ids.account_id[:8]}"),
                Person(id=ids.person_id, email=f"m6c3-{ids.person_id}@example.test"),
            ]
        )
        session.flush()
        session.add(
            Building(
                id=ids.building_id,
                account_id=ids.account_id,
                name="Haus M6C3",
                street="Musterstraße 3",
                postal_code="10115",
                city="Berlin",
            )
        )
        session.flush()
        session.add(
            Unit(
                id=ids.unit_id,
                account_id=ids.account_id,
                building_id=ids.building_id,
                label="WE 1",
                area_sqm_x100=7_500,
            )
        )
        session.add_all(
            [
                Renter(id=ids.renter_one, account_id=ids.account_id, legal_name="Anna Beispiel"),
                Renter(id=ids.renter_two, account_id=ids.account_id, legal_name="Bernd Beispiel"),
            ]
        )
        session.flush()
        session.add(
            Tenancy(
                id=ids.tenancy_id,
                account_id=ids.account_id,
                unit_id=ids.unit_id,
                valid_from=date(2025, 1, 1),
                valid_to=None,
                base_rent_cents=85_000,
            )
        )
        session.flush()
        # Both renters are parties to the tenancy, so `enforce_receivable_tenancy_party`
        # (migration 0019) is satisfied for both debts and cannot be the reason a
        # cross-renter fixture is refused.
        session.add_all(
            [
                TenancyParty(
                    id=ids.party_one,
                    account_id=ids.account_id,
                    tenancy_id=ids.tenancy_id,
                    renter_id=ids.renter_one,
                ),
                TenancyParty(
                    id=ids.party_two,
                    account_id=ids.account_id,
                    tenancy_id=ids.tenancy_id,
                    renter_id=ids.renter_two,
                ),
            ]
        )
        session.add(
            BankAccount(
                id=ids.bank_account_id,
                account_id=ids.account_id,
                provider="finapi",
                provider_account_id=f"prov-{ids.bank_account_id}",
                normalized_iban=_IBAN_ACCOUNT,
                display_name="Mietkonto",
            )
        )
        session.flush()
        session.add_all(
            [
                Receivable(
                    id=ids.receivable_one,
                    account_id=ids.account_id,
                    renter_id=ids.renter_one,
                    tenancy_id=ids.tenancy_id,
                    source_type="RECURRING_RENT",
                    source_id=None,
                    period="2025-07",
                    due_date=date(2025, 7, 3),
                    expected_cents=108_000,
                    open_cents=108_000,
                    status="open",
                    category="rent",
                    base_rent_cents=85_000,
                    nk_advance_cents=15_000,
                    heating_advance_cents=8_000,
                    garage_cents=0,
                    open_costs_cents=0,
                    open_interest_cents=0,
                    open_principal_cents=108_000,
                    stored_reference=None,
                ),
                Receivable(
                    id=ids.receivable_two,
                    account_id=ids.account_id,
                    renter_id=ids.renter_two,
                    tenancy_id=ids.tenancy_id,
                    source_type="RECURRING_RENT",
                    source_id=None,
                    period="2025-08",
                    due_date=date(2025, 8, 3),
                    expected_cents=60_000,
                    open_cents=60_000,
                    status="open",
                    category="rent",
                    base_rent_cents=45_000,
                    nk_advance_cents=10_000,
                    heating_advance_cents=5_000,
                    garage_cents=0,
                    open_costs_cents=0,
                    open_interest_cents=0,
                    open_principal_cents=60_000,
                    stored_reference=None,
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                _transaction(ids, ids.tx_payment, 108_000, "E2E-M6C3-1"),
                # docs/15 § 5.3: the return is a *distinct* provider movement, resolved
                # by E2E reference. It is not the original transaction row again.
                _transaction(ids, ids.tx_return, -108_000, "E2E-M6C3-1"),
                _transaction(ids, ids.tx_spare, 60_000, "E2E-M6C3-2"),
            ]
        )
        session.flush()
        session.add(
            MatchProposal(
                id=ids.proposal_id,
                account_id=ids.account_id,
                bank_transaction_id=ids.tx_payment,
                receivable_id=ids.receivable_one,
                renter_id=ids.renter_one,
                signal_iban=60,
                signal_amount=30,
                signal_code_or_surname=15,
                signal_e2e=0,
                signal_period=5,
                confidence=100,
                decision="AUTO_MATCH",
                convention_version="docs/15 07/2026",
                reason_de="Eindeutige IBAN, exakter Betrag und Periode.",
            )
        )
        session.flush()
        # `enforce_ledger_entry_evidence` (0019) requires an entry's proposal to name the
        # entry's own transaction, so the spare payment needs its own proposal. It names
        # renter one, which is what makes M6C3R-R01 a cross-renter allocation.
        session.add(
            MatchProposal(
                id=ids.proposal_spare,
                account_id=ids.account_id,
                bank_transaction_id=ids.tx_spare,
                receivable_id=ids.receivable_one,
                renter_id=ids.renter_one,
                signal_iban=60,
                signal_amount=0,
                signal_code_or_surname=15,
                signal_e2e=0,
                signal_period=0,
                confidence=75,
                decision="NEEDS_REVIEW",
                convention_version="docs/15 07/2026",
                reason_de="IBAN bekannt, Betrag weicht ab.",
            )
        )
        session.flush()
        session.add_all(
            [
                MatchConfirmation(
                    id=ids.confirmation_id,
                    account_id=ids.account_id,
                    match_proposal_id=ids.proposal_id,
                    outcome="CONFIRMED",
                    confirmed_by=ids.person_id,
                ),
                PaymentLedgerEntry(
                    id=ids.entry_payment,
                    account_id=ids.account_id,
                    bank_transaction_id=ids.tx_payment,
                    match_proposal_id=ids.proposal_id,
                    kind="PAYMENT",
                    amount_cents=108_000,
                    credit_cents=0,
                    ordering_version="§ 366/367 BGB",
                    reverses_entry_id=None,
                ),
                # A PAYMENT with no allocation yet. Nothing forbids that state — it is
                # the row an allocation is written against.
                PaymentLedgerEntry(
                    id=ids.entry_spare,
                    account_id=ids.account_id,
                    bank_transaction_id=ids.tx_spare,
                    match_proposal_id=ids.proposal_spare,
                    kind="PAYMENT",
                    amount_cents=60_000,
                    credit_cents=0,
                    ordering_version="§ 366/367 BGB",
                    reverses_entry_id=None,
                ),
            ]
        )
        session.flush()
        session.add(
            PaymentAllocation(
                id=ids.allocation_id,
                account_id=ids.account_id,
                ledger_entry_id=ids.entry_payment,
                receivable_id=ids.receivable_one,
                costs_cents=0,
                interest_cents=0,
                principal_cents=108_000,
                base_rent_cents=85_000,
                nk_advance_cents=15_000,
                heating_advance_cents=8_000,
                garage_cents=0,
                resulting_status="settled",
            )
        )
        session.flush()
        # Every REVERSAL in the live database carries `match_proposal_id IS NULL`
        # (12/12, boundary audit 23.08.2026), so the entry's renter is only reachable
        # through the entry it reverses. That is what M6C3R-R02 pins.
        session.add(
            PaymentLedgerEntry(
                id=ids.entry_reversal,
                account_id=ids.account_id,
                bank_transaction_id=ids.tx_return,
                match_proposal_id=None,
                kind="REVERSAL",
                amount_cents=-108_000,
                credit_cents=0,
                ordering_version="§ 366/367 BGB",
                reverses_entry_id=ids.entry_payment,
            )
        )
    return ids


def _transaction(ids: _Graph, tx_id: str, amount_cents: int, e2e: str) -> BankTransaction:
    return BankTransaction(
        id=tx_id,
        account_id=ids.account_id,
        bank_account_id=ids.bank_account_id,
        provider_transaction_id=f"prov-tx-{tx_id}",
        amount_cents=amount_cents,
        bank_booking_date=date(2025, 7, 2),
        finapi_booking_date=date(2025, 7, 2),
        value_date=date(2025, 7, 2),
        counterpart_iban=_IBAN_LEARNED,
        counterpart_name="Anna Beispiel",
        purpose="Miete 2025-07",
        end_to_end_reference=e2e,
        counterpart_mandate_reference=None,
        bank_transaction_code="SEPA-CT",
        provider_type="CREDIT" if amount_cents >= 0 else "DEBIT",
        is_potential_duplicate=False,
    )


@contextmanager
def _rolled_back(engine: Engine) -> Iterator[Session]:
    """A session whose transaction is discarded no matter what the assertions did.

    Not a convenience. `payment_ledger_entry`, `payment_allocation`, `bank_transaction`,
    `match_proposal`, `match_confirmation` and `iban_history` refuse DELETE, so any
    insert these fixtures make while the constraint is still missing would be permanent
    — and on the next run its unique index would refuse it, turning a red fixture green
    for a reason that has nothing to do with the invariant.
    """
    session = Session(engine)
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _insert_error(session: Session, *rows: object) -> str | None:
    """Attempt an insert inside a savepoint. Return the database's reason, or None.

    On success the savepoint is released, so the rows stay visible to later assertions
    in the same (still-doomed) transaction. On failure it is rolled back and the session
    stays usable for the next arm.
    """
    savepoint = session.begin_nested()
    try:
        session.add_all(list(rows))
        session.flush()
    except DBAPIError as exc:
        savepoint.rollback()
        session.expunge_all()
        return str(exc.orig) if exc.orig is not None else str(exc)
    savepoint.commit()
    return None


def _allocation(
    ids: _Graph,
    *,
    entry_id: str,
    receivable_id: str,
    costs: int = 0,
    interest: int = 0,
    base_rent: int = 0,
    nk_advance: int = 0,
    heating_advance: int = 0,
    garage: int = 0,
    status: str = "settled",
) -> PaymentAllocation:
    """`principal_cents` is the component sum by construction — `0018`'s
    `ck_payment_allocation_components_sum` is not what any fixture here is testing."""
    return PaymentAllocation(
        id=new_id(),
        account_id=ids.account_id,
        ledger_entry_id=entry_id,
        receivable_id=receivable_id,
        costs_cents=costs,
        interest_cents=interest,
        principal_cents=base_rent + nk_advance + heating_advance + garage,
        base_rent_cents=base_rent,
        nk_advance_cents=nk_advance,
        heating_advance_cents=heating_advance,
        garage_cents=garage,
        resulting_status=status,
    )


def _confirmation_for(
    session: Session, ids: _Graph, *, renter_id: str, receivable_id: str, outcome: str
) -> str:
    """A fresh proposal plus its confirmation, inside the caller's doomed transaction.

    `uq_match_confirmation_proposal` allows one confirmation per proposal, so a second
    confirmed IBAN fact needs a second proposal — and the proposal's renter must be the
    row's renter, or `enforce_match_proposal_renter` refuses it first.
    """
    confirmation_id = new_id()
    proposal_id = new_id()
    session.add(
        MatchProposal(
            id=proposal_id,
            account_id=ids.account_id,
            bank_transaction_id=ids.tx_spare,
            receivable_id=receivable_id,
            renter_id=renter_id,
            signal_iban=0,
            signal_amount=30,
            signal_code_or_surname=15,
            signal_e2e=0,
            signal_period=5,
            confidence=50,
            decision="NEEDS_REVIEW",
            convention_version="docs/15 07/2026",
            reason_de="Kein eindeutiges IBAN-Signal.",
        )
    )
    session.flush()
    session.add(
        MatchConfirmation(
            id=confirmation_id,
            account_id=ids.account_id,
            match_proposal_id=proposal_id,
            outcome=outcome,
            confirmed_by=ids.person_id,
        )
    )
    session.flush()
    return confirmation_id


def _iban_row(
    ids: _Graph,
    *,
    renter_id: str,
    iban: str,
    confirmation_id: str,
    valid_from: date,
    learned_from: str | None,
) -> IbanHistory:
    """`learned_from` must be the transaction the cited confirmation's proposal names.

    M6C3R-R16/R17 make that a rule, so every caller states it: `graph.confirmation_id`
    confirms a proposal on `tx_payment`, and every confirmation `_confirmation_for`
    builds sits on `tx_spare`. Passing the wrong one is the R17 fixture, not a default.
    """
    return IbanHistory(
        id=new_id(),
        account_id=ids.account_id,
        renter_id=renter_id,
        normalized_iban=iban,
        valid_from=valid_from,
        valid_to=None,
        learned_from_transaction_id=learned_from,
        confirmed_match_id=confirmation_id,
        confirmed_by=ids.person_id,
    )


_NEGATIVE_CHECK = "ck_payment_allocation_no_negative_components"


class TestAllocationBelongsToOneRenter:
    """C1 — `docs/15` § 6: "A match never moves money between renters."

    `0019` enforces that a proposal names its receivable's renter, and that a receivable's
    renter is a party to its tenancy. It never checks the allocation itself, which is the
    row that actually moves the money.
    """

    def test_payment_allocation_may_not_settle_another_renters_debt(
        self, owner: Engine, graph: _Graph
    ) -> None:
        """M6C3R-R01: entry renter via `match_proposal_id → match_proposal.renter_id`."""
        with _rolled_back(owner) as session:
            error = _insert_error(
                session,
                _allocation(
                    graph,
                    entry_id=graph.entry_spare,
                    receivable_id=graph.receivable_two,
                    base_rent=45_000,
                    nk_advance=10_000,
                    heating_advance=5_000,
                ),
            )
        assert error is not None, (
            "C1 is missing: renter one's payment was allowed to settle renter two's "
            "debt. The entry's renter is match_proposal.renter_id; the allocation's "
            "renter is receivable.renter_id, and they differ here."
        )

    def test_reversal_allocation_may_not_settle_another_renters_debt(
        self, owner: Engine, graph: _Graph
    ) -> None:
        """M6C3R-R02: a REVERSAL has no proposal, so the renter resolves through
        `reverses_entry_id → original.match_proposal_id → renter_id`."""
        with _rolled_back(owner) as session:
            error = _insert_error(
                session,
                _allocation(
                    graph,
                    entry_id=graph.entry_reversal,
                    receivable_id=graph.receivable_two,
                    base_rent=-45_000,
                    nk_advance=-10_000,
                    heating_advance=-5_000,
                    status="open",
                ),
            )
        assert error is not None, "C1 is missing on the reversal arm"
        assert _NEGATIVE_CHECK not in error, (
            "refused for the wrong reason: 0019's blanket non-negative check rejected "
            "the engine's own reversal shape (reversal.py:112-123 emits negative "
            "components). C1 must be what refuses this row, because it names a "
            "receivable belonging to a renter other than the reversed entry's."
        )

    def test_ledger_entry_without_evidence_may_not_carry_an_allocation(
        self, owner: Engine, graph: _Graph
    ) -> None:
        """M6C3R-R03: fail closed. No proposal and no reversed entry means no renter can
        be resolved, so C1 cannot be evaluated — such an entry allocates nothing."""
        orphan_entry = new_id()
        with _rolled_back(owner) as session:
            # The entry is written on its own first: whether C1 fails closed by refusing
            # the evidence-less entry or by refusing its allocation is the implementer's
            # choice, and this fixture accepts either — what it refuses to accept is the
            # pair going through.
            error = _insert_error(
                session,
                PaymentLedgerEntry(
                    id=orphan_entry,
                    account_id=graph.account_id,
                    bank_transaction_id=graph.tx_spare,
                    match_proposal_id=None,
                    kind="PAYMENT",
                    amount_cents=30_000,
                    credit_cents=0,
                    ordering_version="§ 366/367 BGB",
                    reverses_entry_id=None,
                ),
            )
            if error is None:
                error = _insert_error(
                    session,
                    _allocation(
                        graph,
                        entry_id=orphan_entry,
                        receivable_id=graph.receivable_one,
                        base_rent=30_000,
                    ),
                )
        assert error is not None, (
            "C1 does not fail closed: an entry citing neither a proposal nor an original "
            "entry has no resolvable renter, and was still allowed to allocate money."
        )


class TestLearnedIbanNeedsItsOwnConfirmation:
    """C2 — `docs/15` § 3.3: an IBAN is learned "only after a user confirms a Review
    proposal". `0019` requires *a* confirmation id; it never checks whose, or what the
    confirmation decided."""

    def test_iban_history_may_not_cite_another_renters_confirmation(
        self, owner: Engine, graph: _Graph
    ) -> None:
        """M6C3R-R04: the cited confirmation's proposal names renter one; the row claims
        the IBAN for renter two. That is the +60 unique-IBAN signal, forged."""
        with _rolled_back(owner) as session:
            error = _insert_error(
                session,
                _iban_row(
                    graph,
                    renter_id=graph.renter_two,
                    iban=_IBAN_WRONG_RENTER,
                    confirmation_id=graph.confirmation_id,
                    valid_from=date(2025, 7, 2),
                    learned_from=graph.tx_payment,
                ),
            )
        assert error is not None, (
            "C2 is missing: an IBAN fact was learned for renter two out of a "
            "confirmation that belongs to renter one's proposal."
        )

    def test_iban_history_may_not_cite_an_unconfirmed_outcome(
        self, owner: Engine, graph: _Graph
    ) -> None:
        """M6C3R-R05: outcome REJECTED is not a confirmation. Same renter throughout, so
        only the outcome rule can be what refuses this."""
        with _rolled_back(owner) as session:
            rejected = _confirmation_for(
                session,
                graph,
                renter_id=graph.renter_two,
                receivable_id=graph.receivable_two,
                outcome="REJECTED",
            )
            error = _insert_error(
                session,
                _iban_row(
                    graph,
                    renter_id=graph.renter_two,
                    iban=_IBAN_UNCONFIRMED,
                    confirmation_id=rejected,
                    valid_from=date(2025, 7, 2),
                    # R16/R17: the provenance must be the confirmed proposal's own
                    # transaction, so only the outcome rule can refuse this row.
                    learned_from=graph.tx_spare,
                ),
            )
        assert error is not None, (
            "C2 is missing its outcome arm: a REJECTED review taught Lokara an IBAN. "
            "docs/15 § 3.3 learns an IBAN only after the user *confirms*."
        )


class TestReceivableProjectionAgreesWithItself:
    """C3 — `settlement.py:140` computes `open_after = open_cents - principal`. Only
    principal reduces `open_cents`, so `open_cents` **is** the open principal. A
    three-way sum rule would contradict the engine."""

    def test_open_principal_must_equal_open_cents(self, owner: Engine, graph: _Graph) -> None:
        """M6C3R-R06: `open_principal_cents <> open_cents` is refused; `open_cents >
        expected_cents` is refused; costs and interest are only bounded below.

        `open_costs_cents` and `open_interest_cents` stay unbounded above on purpose: no
        source bounds them, and they arrive from Page 05 (M9). Inventing a ceiling here
        would be inventing a rule.
        """
        with _rolled_back(owner) as session:
            drifted = _insert_error(
                session,
                _receivable(
                    graph,
                    period="2025-09",
                    expected_cents=108_000,
                    open_cents=50_000,
                    open_principal_cents=40_000,
                    status="partial",
                ),
            )
            assert drifted is not None, (
                "C3 is missing: 0019 only asserts open_principal_cents <= open_cents, so "
                "the settlement engine and the arrears guard can read two different open "
                "principals from one row. settlement.py:140 makes them the same number."
            )
            over_expected = _insert_error(
                session,
                _receivable(
                    graph,
                    period="2025-10",
                    expected_cents=60_000,
                    open_cents=70_000,
                    open_principal_cents=70_000,
                    status="partial",
                ),
            )
            assert over_expected is not None, "open_cents may never exceed expected_cents"
            negative_costs = _insert_error(
                session,
                _receivable(
                    graph,
                    period="2025-11",
                    expected_cents=60_000,
                    open_cents=60_000,
                    open_principal_cents=60_000,
                    status="open",
                    open_costs_cents=-1,
                ),
            )
            assert negative_costs is not None, "open_costs_cents may not go negative"
            negative_interest = _insert_error(
                session,
                _receivable(
                    graph,
                    period="2025-12",
                    expected_cents=60_000,
                    open_cents=60_000,
                    open_principal_cents=60_000,
                    status="open",
                    open_interest_cents=-1,
                ),
            )
            assert negative_interest is not None, "open_interest_cents may not go negative"


def _receivable(
    ids: _Graph,
    *,
    period: str,
    expected_cents: int,
    open_cents: int,
    open_principal_cents: int,
    status: str,
    open_costs_cents: int = 0,
    open_interest_cents: int = 0,
    category: str = "rent",
    source_id: str | None = None,
) -> Receivable:
    """A rent receivable for renter one. Components sum to `expected_cents` so
    `ck_receivable_components_sum` is never the constraint under test."""
    rent = expected_cents if category == "rent" else 0
    return Receivable(
        id=new_id(),
        account_id=ids.account_id,
        renter_id=ids.renter_one,
        tenancy_id=ids.tenancy_id,
        source_type="PAGE01_STATEMENT" if source_id is not None else "RECURRING_RENT",
        source_id=source_id,
        period=period,
        due_date=date(2025, 7, 3),
        expected_cents=expected_cents,
        open_cents=open_cents,
        status=status,
        category=category,
        base_rent_cents=rent,
        nk_advance_cents=0,
        heating_advance_cents=0,
        garage_cents=0,
        open_costs_cents=open_costs_cents,
        open_interest_cents=open_interest_cents,
        open_principal_cents=open_principal_cents,
        stored_reference=None,
    )


class TestAllocationSignFollowsItsEntry:
    """C6 — the sign rule `0019` got backwards. `reversal.py:112-123` emits
    `costs_cents=-allocation.costs_cents` and so on, so the blanket non-negative check
    rejects the matching engine's own verified output."""

    def test_reversal_allocation_may_negate_the_original_exactly(
        self, owner: Engine, graph: _Graph
    ) -> None:
        """M6C3R-R07: the compensating allocation is accepted, and the two allocations on
        the receivable net to zero — `docs/15` § 5.3 / F06."""
        with _rolled_back(owner) as session:
            error = _insert_error(
                session,
                _allocation(
                    graph,
                    entry_id=graph.entry_reversal,
                    receivable_id=graph.receivable_one,
                    base_rent=-85_000,
                    nk_advance=-15_000,
                    heating_advance=-8_000,
                    status="open",
                ),
            )
            assert error is None, (
                "0019 refuses the reversal the engine produces: "
                f"{error}. reversal.py:112-123 negates every component, and § 5.3 "
                "requires the ledger to net to zero."
            )
            netted = session.scalar(
                select(
                    func.coalesce(
                        func.sum(
                            PaymentAllocation.costs_cents
                            + PaymentAllocation.interest_cents
                            + PaymentAllocation.principal_cents
                        ),
                        0,
                    )
                ).where(PaymentAllocation.receivable_id == graph.receivable_one)
            )
            assert netted == 0, (
                f"F06: payment plus reversal must net to zero on the receivable, got {netted} cents"
            )

    def test_the_cap_is_signed_and_a_payment_stays_positive(
        self, owner: Engine, graph: _Graph
    ) -> None:
        """M6C3R-R08: PAYMENT components stay >= 0, REVERSAL components stay <= 0, and
        the per-entry cap is signed — `sum <= amount_cents` for a PAYMENT,
        `sum >= amount_cents` for a REVERSAL. `0019` compares against `abs(amount_cents)`,
        which grants a -1.080,00 € reversal a +1.080,00 € budget."""
        with _rolled_back(owner) as session:
            negative_on_payment = _insert_error(
                session,
                _allocation(
                    graph,
                    entry_id=graph.entry_spare,
                    receivable_id=graph.receivable_two,
                    base_rent=-45_000,
                    status="open",
                ),
            )
            assert negative_on_payment is not None, (
                "a PAYMENT may not carry negative components — that is a reversal "
                "wearing a payment's kind"
            )
            positive_on_reversal = _insert_error(
                session,
                _allocation(
                    graph,
                    entry_id=graph.entry_reversal,
                    receivable_id=graph.receivable_one,
                    base_rent=85_000,
                    nk_advance=15_000,
                    heating_advance=8_000,
                ),
            )
            assert positive_on_reversal is not None, (
                "the abs() cap in 0019 let a -1.080,00 € REVERSAL settle +1.080,00 € of "
                "debt. A reversal returns money; its allocations are never positive."
            )
            beyond_the_floor = _insert_error(
                session,
                _allocation(
                    graph,
                    entry_id=graph.entry_reversal,
                    receivable_id=graph.receivable_two,
                    base_rent=-200_000,
                    status="open",
                ),
            )
            assert beyond_the_floor is not None, "a reversal may not give back more than it took"
            assert _NEGATIVE_CHECK not in beyond_the_floor, (
                "refused for the wrong reason: the blanket non-negative check fired, not "
                "the signed cap. Once R07 removes that check, sum(allocations) >= "
                "amount_cents is the only thing standing between a -1.080,00 € reversal "
                "and a -2.000,00 € give-back."
            )


class TestReversalShape:
    """C5 — `docs/15` § 5.3: the compensating entry reverses the original *exactly*."""

    def test_reversal_amount_and_target_are_constrained(self, owner: Engine, graph: _Graph) -> None:
        """M6C3R-R09: `amount_cents` must be `-original.amount_cents`, and a REVERSAL may
        not reverse a REVERSAL.

        Nothing here asserts anything about `bank_transaction_id`: § 5.3 makes the return
        a *distinct* provider movement resolved by E2E or mandate reference, so requiring
        the two entries to share a transaction id would encode a fixture shortcut as a
        rule.
        """
        with _rolled_back(owner) as session:
            partial_reversal = _insert_error(
                session,
                PaymentLedgerEntry(
                    id=new_id(),
                    account_id=graph.account_id,
                    bank_transaction_id=graph.tx_return,
                    match_proposal_id=None,
                    kind="REVERSAL",
                    amount_cents=-50_000,
                    credit_cents=0,
                    ordering_version="§ 366/367 BGB",
                    reverses_entry_id=graph.entry_spare,
                ),
            )
            assert partial_reversal is not None, (
                "C5 is missing: a -500,00 € reversal of a 600,00 € payment was accepted. "
                "The ledger can no longer net to zero, and the table is append-only, so "
                "nothing corrects it afterwards."
            )
            reversal_of_a_reversal = _insert_error(
                session,
                PaymentLedgerEntry(
                    id=new_id(),
                    account_id=graph.account_id,
                    bank_transaction_id=graph.tx_return,
                    match_proposal_id=None,
                    kind="REVERSAL",
                    amount_cents=-108_000,
                    credit_cents=0,
                    ordering_version="§ 366/367 BGB",
                    reverses_entry_id=graph.entry_reversal,
                ),
            )
            assert reversal_of_a_reversal is not None, (
                "C5 is missing: an entry reversed a REVERSAL. § 5.3 reverses a payment, "
                "and a chain of reversals has no defined restore target."
            )


class TestActiveIbanUniquenessIsPerRenter:
    """C8 — `docs/15` § 3.3 `F07`: "If two active renters share it, each receives the
    ambiguous signal and the result is Review." `0019`'s
    `uq_iban_history_active (account_id, normalized_iban)` makes that state impossible,
    so the ambiguity the scoring rule exists to handle can never be reached."""

    def test_two_renters_may_share_one_active_iban_but_one_renter_may_not(
        self, owner: Engine, graph: _Graph
    ) -> None:
        """M6C3R-R10: the F07 state must exist; the replacement guarantee still holds
        per renter."""
        with _rolled_back(owner) as session:
            second = _confirmation_for(
                session,
                graph,
                renter_id=graph.renter_two,
                receivable_id=graph.receivable_two,
                outcome="CONFIRMED",
            )
            shared = _insert_error(
                session,
                _iban_row(
                    graph,
                    renter_id=graph.renter_one,
                    iban=_IBAN_SHARED,
                    confirmation_id=graph.confirmation_id,
                    valid_from=date(2025, 7, 2),
                    learned_from=graph.tx_payment,
                ),
                _iban_row(
                    graph,
                    renter_id=graph.renter_two,
                    iban=_IBAN_SHARED,
                    confirmation_id=second,
                    valid_from=date(2025, 7, 3),
                    learned_from=graph.tx_spare,
                ),
            )
            assert shared is None, (
                "0019 forbids the F07 state docs/15 § 3.3 requires to exist: two active "
                "renters on one IBAN, each scored ambiguous and routed to Review. "
                f"Refused with: {shared}"
            )
            third = _confirmation_for(
                session,
                graph,
                renter_id=graph.renter_one,
                receivable_id=graph.receivable_one,
                outcome="CONFIRMED",
            )
            duplicated = _insert_error(
                session,
                _iban_row(
                    graph,
                    renter_id=graph.renter_one,
                    iban=_IBAN_REPLACED,
                    confirmation_id=graph.confirmation_id,
                    valid_from=date(2025, 7, 2),
                    learned_from=graph.tx_payment,
                ),
                _iban_row(
                    graph,
                    renter_id=graph.renter_one,
                    iban=_IBAN_REPLACED,
                    confirmation_id=third,
                    valid_from=date(2025, 7, 3),
                    learned_from=graph.tx_spare,
                ),
            )
            assert duplicated is not None, (
                "one renter held the same IBAN active twice: history is versioned "
                "(CLAUDE.md § 6), so the predecessor's valid_to must be closed first."
            )


class TestOneNachzahlungPerTenancyPeriod:
    """C9 — the Page 01 handoff guard in `payments.py:203-221` is a bare SELECT followed
    by an INSERT. Two concurrent requests both pass it and both insert."""

    def test_a_second_nachzahlung_for_one_tenancy_period_is_refused(
        self, owner: Engine, graph: _Graph
    ) -> None:
        """M6C3R-R11: a correction statement is a new statement id, so
        `uq_receivable_source (account_id, source_type, source_id, tenancy_id)` does not
        cover this — the two rows carry different `source_id`s on purpose."""
        with _rolled_back(owner) as session:
            error = _insert_error(
                session,
                _receivable(
                    graph,
                    period="2024",
                    expected_cents=24_500,
                    open_cents=24_500,
                    open_principal_cents=24_500,
                    status="open",
                    category="nk_nachzahlung",
                    source_id=new_id(),
                ),
                _receivable(
                    graph,
                    period="2024",
                    expected_cents=24_500,
                    open_cents=24_500,
                    open_principal_cents=24_500,
                    status="open",
                    category="nk_nachzahlung",
                    source_id=new_id(),
                ),
            )
        assert error is not None, (
            "C9 is missing: one tenancy was billed the same period's Nachzahlung twice. "
            "payments.py guards this with a SELECT-then-INSERT, which two concurrent "
            "requests both pass — and the renter's debt doubles."
        )


@pytest.fixture
def app_engine(owner: Engine) -> Iterator[Engine]:
    """A `lokara_app` engine created and disposed per test.

    H2 shadows a table in `pg_temp`, and plpgsql caches a trigger function's query plans
    for the life of the backend. A pool shared with an earlier test could hand back a
    connection whose cached plan already bound `receivable` to `public.receivable`, which
    would hide the defect instead of proving it. One backend per test removes the doubt.

    It depends on `owner` only for ordering: that fixture applies the app role and
    `alembic upgrade head`, and skips the module when Postgres is not running.
    """
    engine = create_db_engine(DbSettings().database_url)
    try:
        yield engine
    finally:
        engine.dispose()


@contextmanager
def _rolled_back_app(engine: Engine, account_id: str) -> Iterator[Session]:
    """`_rolled_back`, but as `lokara_app` inside the graph's RLS context.

    The H2 fixtures must run as the application role, not the migration owner: the
    finding is that `lokara_app` holds TEMP on the database, so the shadow table is
    something the application's own role can create. `set_config(..., true)` is
    transaction-local, and the transaction is discarded either way.
    """
    session = Session(engine)
    try:
        session.execute(
            text("SELECT set_config('app.account_id', :account_id, true)"),
            {"account_id": account_id},
        )
        yield session
    finally:
        session.rollback()
        session.close()


def _payment_entry(
    session: Session, ids: _Graph, *, renter_id: str, receivable_id: str, cents: int
) -> str:
    """A committed-into-the-doomed-transaction PAYMENT: transaction, proposal, entry.

    `enforce_ledger_entry_evidence` requires an entry's proposal to name the entry's own
    transaction, and `enforce_match_proposal_renter` requires the proposal to name its
    receivable's renter, so all three rows are built together.
    """
    tx_id, proposal_id, entry_id = new_id(), new_id(), new_id()
    session.add(_transaction(ids, tx_id, cents, f"E2E-{tx_id[:8]}"))
    session.flush()
    session.add(
        MatchProposal(
            id=proposal_id,
            account_id=ids.account_id,
            bank_transaction_id=tx_id,
            receivable_id=receivable_id,
            renter_id=renter_id,
            signal_iban=60,
            signal_amount=30,
            signal_code_or_surname=0,
            signal_e2e=0,
            signal_period=0,
            confidence=90,
            decision="AUTO_MATCH",
            convention_version="docs/15 07/2026",
            reason_de="Eindeutige IBAN und exakter Betrag.",
        )
    )
    session.flush()
    session.add(
        PaymentLedgerEntry(
            id=entry_id,
            account_id=ids.account_id,
            bank_transaction_id=tx_id,
            match_proposal_id=proposal_id,
            kind="PAYMENT",
            amount_cents=cents,
            credit_cents=0,
            ordering_version="§ 366/367 BGB",
            reverses_entry_id=None,
        )
    )
    session.flush()
    return entry_id


def _reversal_entry_with_own_proposal(
    session: Session,
    ids: _Graph,
    *,
    reverses: str,
    cents: int,
    proposal_renter: str,
    proposal_receivable: str,
) -> str:
    """The § 5.3 return: a *distinct* provider movement that carries its own proposal.

    `ck_payment_ledger_reversal_shape` requires `reverses_entry_id` on a REVERSAL and
    says nothing about `match_proposal_id`, and § 5.3 makes the return a separate
    movement resolved by E2E or mandate reference — so a proposal of its own is a legal
    shape, not an abuse. `proposal_renter` is what H1 lets shadow the real one.
    """
    tx_id, proposal_id, entry_id = new_id(), new_id(), new_id()
    session.add(_transaction(ids, tx_id, -cents, f"E2E-{tx_id[:8]}"))
    session.flush()
    session.add(
        MatchProposal(
            id=proposal_id,
            account_id=ids.account_id,
            bank_transaction_id=tx_id,
            receivable_id=proposal_receivable,
            renter_id=proposal_renter,
            signal_iban=60,
            signal_amount=30,
            signal_code_or_surname=0,
            signal_e2e=0,
            signal_period=0,
            confidence=90,
            decision="AUTO_MATCH",
            convention_version="docs/15 07/2026",
            reason_de="Rücklastschrift, IBAN eindeutig.",
        )
    )
    session.flush()
    session.add(
        PaymentLedgerEntry(
            id=entry_id,
            account_id=ids.account_id,
            bank_transaction_id=tx_id,
            match_proposal_id=proposal_id,
            kind="REVERSAL",
            amount_cents=-cents,
            credit_cents=0,
            ordering_version="§ 366/367 BGB",
            reverses_entry_id=reverses,
        )
    )
    session.flush()
    return entry_id


class TestAReversalsOwnProposalDoesNotChooseTheRenter:
    """H1 — the boundary audit re-run of 23.08.2026, against `0020:155-168`.

    `enforce_payment_allocation_renter` resolves the entry's renter with
    `IF entry_proposal IS NOT NULL … ELSIF original_entry IS NOT NULL`, so the two
    sources are alternatives. `ck_payment_ledger_reversal_shape` (`models.py:1772`)
    requires a REVERSAL to carry `reverses_entry_id` but never forbids it from *also*
    carrying `match_proposal_id`, and `docs/15` § 5.3 makes the return a distinct
    provider movement that legitimately has a proposal of its own. The `IF` branch
    therefore wins and the reversed payment's renter is never consulted — which is
    exactly the money movement `docs/15` § 6 forbids: "a match never moves money
    between renters".

    The repair is the resolution rule, not a ban: forbidding `match_proposal_id` on a
    REVERSAL would make the § 5.3 shape unrepresentable. When both are present the
    reversed entry's renter decides, or the two must agree.
    """

    def test_a_reversal_may_not_repoint_its_allocation_through_its_own_proposal(
        self, owner: Engine, graph: _Graph
    ) -> None:
        """M6C3R-R13: renter one pays, the payment bounces, and the return's own
        proposal names renter two.

        Pre-repair behaviour: **accepted**. The allocation settled renter two's debt out of
        renter one's returned money, and `payment_allocation` is append-only, so nothing
        corrects it afterwards.

        Arms 1 and 2 are controls that pass today; they are asserted here so a repair
        cannot reach the H1 case by loosening what already works.
        """
        with _rolled_back(owner) as session:
            # Control (R01's shape): a plain PAYMENT of renter one may not settle
            # renter two's debt. The proposal branch is consulted and it is correct.
            plain_payment = _insert_error(
                session,
                _allocation(
                    graph,
                    entry_id=graph.entry_spare,
                    receivable_id=graph.receivable_two,
                    base_rent=45_000,
                    nk_advance=10_000,
                    heating_advance=5_000,
                ),
            )
            assert plain_payment is not None, (
                "control regressed: a PAYMENT whose proposal names renter one settled "
                "renter two's debt"
            )
            # Control (R02's shape): a REVERSAL with no proposal of its own resolves
            # through `reverses_entry_id`, and that branch is correct too.
            reversal_without_proposal = _insert_error(
                session,
                _allocation(
                    graph,
                    entry_id=graph.entry_reversal,
                    receivable_id=graph.receivable_two,
                    base_rent=-45_000,
                    nk_advance=-10_000,
                    heating_advance=-5_000,
                    status="open",
                ),
            )
            assert reversal_without_proposal is not None, (
                "control regressed: a REVERSAL with `match_proposal_id IS NULL` resolved "
                "its renter through the reversed entry and must still refuse renter two"
            )
            # Control the repair must not break: renter two's own payment, returned,
            # with a proposal of its own. § 5.3's normal shape — it stays accepted.
            renter_two_payment = _payment_entry(
                session,
                graph,
                renter_id=graph.renter_two,
                receivable_id=graph.receivable_two,
                cents=30_000,
            )
            honest_return = _reversal_entry_with_own_proposal(
                session,
                graph,
                reverses=renter_two_payment,
                cents=30_000,
                proposal_renter=graph.renter_two,
                proposal_receivable=graph.receivable_two,
            )
            agreeing = _insert_error(
                session,
                _allocation(
                    graph,
                    entry_id=honest_return,
                    receivable_id=graph.receivable_two,
                    base_rent=-30_000,
                    status="open",
                ),
            )
            assert agreeing is None, (
                "a return that carries its own proposal is docs/15 § 5.3's ordinary "
                f"shape and both sources name renter two here; refused with: {agreeing}"
            )
            # H1. `entry_spare` is renter one's 600,00 € payment. The return names
            # renter two in its own proposal and renter one through `reverses_entry_id`.
            shadowing_return = _reversal_entry_with_own_proposal(
                session,
                graph,
                reverses=graph.entry_spare,
                cents=60_000,
                proposal_renter=graph.renter_two,
                proposal_receivable=graph.receivable_two,
            )
            error = _insert_error(
                session,
                _allocation(
                    graph,
                    entry_id=shadowing_return,
                    receivable_id=graph.receivable_two,
                    base_rent=-45_000,
                    nk_advance=-10_000,
                    heating_advance=-5_000,
                    status="open",
                ),
            )
        assert error is not None, (
            "H1: the reversal's own proposal shadowed the reversed payment's renter. "
            "0020:155-168 takes the `IF entry_proposal IS NOT NULL` branch and never "
            "reaches `ELSIF original_entry IS NOT NULL`, so renter one's returned money "
            "was credited against renter two's debt. docs/15 § 6."
        )


class TestTriggerLookupsCannotBeShadowed:
    """H2 — every trigger in `0019`/`0020` is neutralised by a `pg_temp` table.

    All six functions in `0020` (lines 53, 90, 143, 199, 255) and the five in `0019` are
    `LANGUAGE plpgsql` with no `SET search_path`, and every lookup is unqualified:
    `FROM receivable`, `FROM payment_ledger_entry`, `FROM match_proposal`,
    `FROM match_confirmation`, `FROM tenancy_party`. `lokara_app` holds TEMP on the
    database (verified 23.08.2026), and PostgreSQL resolves `pg_temp` before `public`,
    so the application's own role can hand any of these triggers a fabricated parent.

    Everything the M6-C3 slice added rests on those lookups. `CLAUDE.md` § 3.3 makes
    isolation a property of the database, not of the caller's search path.

    Both fixtures create the shadow with `ON COMMIT DROP` inside a transaction that is
    rolled back unconditionally, so nothing survives the test either way.
    """

    def test_a_temp_receivable_may_not_answer_the_renter_lookup(
        self, app_engine: Engine, graph: _Graph
    ) -> None:
        """M6C3R-R14: `enforce_payment_allocation_renter` reads `FROM receivable`.

        The shadow maps renter two's receivable id to renter one, so the cross-renter
        allocation that R01 proves is refused becomes indistinguishable from a correct
        one. Pre-repair behaviour: **accepted**.
        """
        with _rolled_back_app(app_engine, graph.account_id) as session:
            session.execute(
                text(
                    "CREATE TEMP TABLE receivable"
                    " (id text, account_id text, renter_id text) ON COMMIT DROP"
                )
            )
            session.execute(
                text(
                    "INSERT INTO pg_temp.receivable (id, account_id, renter_id)"
                    " VALUES (:id, :account_id, :renter_id)"
                ),
                {
                    "id": graph.receivable_two,
                    "account_id": graph.account_id,
                    "renter_id": graph.renter_one,
                },
            )
            error = _insert_error(
                session,
                _allocation(
                    graph,
                    entry_id=graph.entry_spare,
                    receivable_id=graph.receivable_two,
                    base_rent=45_000,
                    nk_advance=10_000,
                    heating_advance=5_000,
                ),
            )
        assert error is not None, (
            "H2: a temp table named `receivable` answered the trigger's lookup, so "
            "renter one's payment settled renter two's real debt — the composite FK "
            "still points at public.receivable, so the row that lands is the "
            "cross-renter one. Every plpgsql function in 0019/0020 needs "
            "`SET search_path` (and qualified lookups), or lokara_app must lose TEMP."
        )

    def test_a_temp_ledger_entry_may_not_answer_the_cap_lookup(
        self, app_engine: Engine, graph: _Graph
    ) -> None:
        """M6C3R-R15: `enforce_payment_allocation_cap` reads `FROM payment_ledger_entry`.

        The shadow claims the 600,00 € entry carried 100.000,00 €, so an allocation of
        5.000,00 € stays under the cap while the real entry never received the money.
        The composite FK is satisfied by the real row, so what lands is an allocation of
        money that does not exist. Pre-repair behaviour: **accepted**.
        """
        with _rolled_back_app(app_engine, graph.account_id) as session:
            session.execute(
                text(
                    "CREATE TEMP TABLE payment_ledger_entry"
                    " (id text, account_id text, amount_cents bigint, kind text,"
                    "  match_proposal_id text, reverses_entry_id text) ON COMMIT DROP"
                )
            )
            session.execute(
                text(
                    "INSERT INTO pg_temp.payment_ledger_entry"
                    " (id, account_id, amount_cents, kind, match_proposal_id,"
                    "  reverses_entry_id)"
                    " VALUES (:id, :account_id, 10000000, 'PAYMENT', :proposal_id, NULL)"
                ),
                {
                    "id": graph.entry_spare,
                    "account_id": graph.account_id,
                    "proposal_id": graph.proposal_spare,
                },
            )
            error = _insert_error(
                session,
                _allocation(
                    graph,
                    entry_id=graph.entry_spare,
                    receivable_id=graph.receivable_one,
                    base_rent=500_000,
                ),
            )
        assert error is not None, (
            "H2: a temp `payment_ledger_entry` granted a 600,00 € payment a "
            "100.000,00 € budget, and 5.000,00 € was allocated against a debt nobody "
            "paid. The signed cap 0020 repaired is only as strong as the name "
            "resolution behind it."
        )


class TestALearnedIbanNamesTheTransactionItWasLearnedFrom:
    """M3-a — `0020:255-279` checks the renter and the `CONFIRMED` outcome, and never
    ties `learned_from_transaction_id` to the confirmed proposal's `bank_transaction_id`.

    `docs/15` § 3.3 stores `learned_from_transaction_id` beside `confirmed_match_id` on
    `IbanHistory`, and an IBAN "is learned only after a user confirms a Review proposal".
    The transaction named there is the movement that carried the IBAN; a row that names
    a different one, or none, records a provenance that was never reviewed. The column
    is then evidence of nothing, and `iban_history` is append-only.

    **Scope limit, deliberately not tested here:** whether `normalized_iban` equals that
    transaction's `counterpart_iban`. Normalization happens in the adapter
    (`CLAUDE.md` § 6, "use adapters at every external edge"), not in SQL, and no source
    fixes a canonical form the database could compare against. That decision is not
    made, so no fixture asserts it.
    """

    def test_a_learned_iban_may_not_omit_its_transaction(
        self, owner: Engine, graph: _Graph
    ) -> None:
        """M6C3R-R16: `learned_from_transaction_id IS NULL` with a genuine CONFIRMED
        confirmation for the right renter. Pre-repair behaviour: **accepted**."""
        with _rolled_back(owner) as session:
            confirmed = _confirmation_for(
                session,
                graph,
                renter_id=graph.renter_two,
                receivable_id=graph.receivable_two,
                outcome="CONFIRMED",
            )
            error = _insert_error(
                session,
                _iban_row(
                    graph,
                    renter_id=graph.renter_two,
                    iban=_IBAN_NO_PROVENANCE,
                    confirmation_id=confirmed,
                    valid_from=date(2025, 7, 2),
                    learned_from=None,
                ),
            )
        assert error is not None, (
            "M3-a: an IBAN fact was learned with no transaction behind it. docs/15 § 3.3 "
            "learns an IBAN from a confirmed Review of a *movement*; without that link "
            "the column records nothing and the row cannot be corrected later."
        )
        assert "names no transaction" in error, (
            "R16 was refused for a different reason and did not prove the null-provenance arm: "
            f"{error}"
        )

    def test_a_learned_iban_may_not_name_a_foreign_transaction(
        self, owner: Engine, graph: _Graph
    ) -> None:
        """M6C3R-R17: the confirmation is genuine, CONFIRMED and renter one's, but the
        provenance names `tx_spare` while its proposal sits on `tx_payment`.

        Pre-repair behaviour: **accepted** — so the +60 unique-IBAN signal could be sourced
        from a movement the user never reviewed.
        """
        with _rolled_back(owner) as session:
            error = _insert_error(
                session,
                _iban_row(
                    graph,
                    renter_id=graph.renter_one,
                    iban=_IBAN_FOREIGN_TX,
                    confirmation_id=graph.confirmation_id,
                    valid_from=date(2025, 7, 2),
                    learned_from=graph.tx_spare,
                ),
            )
        assert error is not None, (
            "M3-a: `learned_from_transaction_id` named a transaction other than the one "
            "the confirmed proposal is about. The confirmation proves a decision on "
            "tx_payment; this row cites tx_spare as its source."
        )
        assert "other than the one its confirmed proposal decided" in error, (
            f"R17 was refused for a different reason and did not prove foreign provenance: {error}"
        )
