"""Database acceptance fixtures for M6-C3a migration 0021.

These fixtures own only the persistence contract transcribed in ``docs/15`` §§ 5.4–5.5.
They prove proposal rank, projection snapshots, confirmed/Auto booking evidence and deferred
ledger reconciliation. Every probe is rolled back because the affected evidence tables are
append-only.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import NamedTuple

import pytest
from alembic import command
from alembic.config import Config
from lokara_db import DbSettings, account_scoped_session, create_db_engine, new_id
from sqlalchemy import Connection, DateTime, Engine, inspect, text
from sqlalchemy.exc import DBAPIError, OperationalError

_DB_DIR = Path(__file__).resolve().parent.parent
_SNAPSHOT_COLUMNS = {
    f"{side}_{field}"
    for side in ("before", "after")
    for field in (
        "open_costs_cents",
        "open_interest_cents",
        "open_principal_cents",
        "open_cents",
        "status",
    )
}


def test_migration_0021_exists_without_touching_a_database() -> None:
    """Non-DB red proof: implementation must add a new revision, never amend 0020."""
    revisions = list((_DB_DIR / "alembic" / "versions").glob("0021_*.py"))
    assert len(revisions) == 1
    source = revisions[0].read_text()
    assert 'revision = "0021"' in source
    assert 'down_revision = "0020"' in source


def test_0021_validates_every_backfilled_run_before_installing_future_triggers() -> None:
    """A future-only trigger cannot repair or validate evidence already in the table.

    The migration must stop on a malformed legacy group after its deterministic rank
    backfill and before installing the INSERT triggers.  The one-off block is named so
    review can prove that it raises rather than silently normalizing differing evidence.
    """
    migration = next((_DB_DIR / "alembic" / "versions").glob("0021_*.py"))
    source = migration.read_text()
    marker = "$legacy_proposal_validation$"
    assert source.count(marker) == 2
    validation = source.split(marker)[1]
    normalized = " ".join(validation.lower().split())

    assert "from public.match_proposal" in normalized
    assert "group by account_id, bank_transaction_id" in normalized
    for malformed in (
        "min(rank) <> 1",
        "max(rank) <> count(*)",
        "count(distinct rank) <> count(*)",
        "count(distinct decision) <> 1",
        "count(distinct reason_de) <> 1",
        "count(distinct convention_version) <> 1",
    ):
        assert malformed in normalized
    assert "raise exception" in normalized
    assert "errcode = '23514'" in normalized
    assert "update public.match_proposal" not in normalized

    backfill = source.index("UPDATE public.match_proposal AS proposal")
    legacy_validation = source.index(f"DO {marker}")
    run_seal = source.index("CREATE FUNCTION public.seal_match_proposal_run_m6c3a")
    future_consistency = source.index("CREATE FUNCTION public.validate_match_proposal_run_m6c3a")
    assert backfill < legacy_validation < run_seal < future_consistency


@pytest.fixture(scope="module")
def owner() -> Iterator[Engine]:
    try:
        engine = create_db_engine(DbSettings().direct_url)
        with engine.connect() as connection:
            connection.execute(text((_DB_DIR / "scripts" / "init-app-role.sql").read_text()))
            connection.commit()
    except OperationalError as exc:
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")
    command.upgrade(Config(str(_DB_DIR / "alembic.ini")), "head")
    yield engine
    engine.dispose()


class Graph(NamedTuple):
    account: str
    foreign_account: str
    person: str
    bank_account: str
    renter: str
    building: str
    unit: str
    tenancy: str
    receivable: str
    tx_auto: str
    tx_review: str
    tx_spare: str
    proposal_auto: str
    proposal_review: str
    confirmation_review: str


@pytest.fixture(scope="module")
def graph(owner: Engine) -> Graph:
    ids = Graph(*(new_id() for _ in range(15)))
    has_rank = "rank" in {column["name"] for column in inspect(owner).get_columns("match_proposal")}
    rank_column = ", rank" if has_rank else ""
    rank_value = ", 1" if has_rank else ""
    with owner.begin() as connection:
        params = {
            "a": ids.account,
            "b": ids.foreign_account,
            "p": ids.person,
            "email": f"{ids.person}@example.test",
            "building": ids.building,
            "unit": ids.unit,
            "renter": ids.renter,
            "tenancy": ids.tenancy,
            "party": new_id(),
            "bank": ids.bank_account,
            "provider": f"provider-{ids.bank_account}",
            "receivable": ids.receivable,
        }
        statements = (
            "INSERT INTO account (id, name, shape, plan)"
            " VALUES (:a, 'M6C3a', 'SOLO', 'TRIAL'),"
            " (:b, 'M6C3a foreign', 'SOLO', 'TRIAL')",
            "INSERT INTO person (id, email) VALUES (:p, :email)",
            "INSERT INTO building (id, account_id, name, street, postal_code, city)"
            " VALUES (:building, :a, 'Haus', 'Weg 1', '10115', 'Berlin')",
            "INSERT INTO unit (id, account_id, building_id, label, area_sqm_x100)"
            " VALUES (:unit, :a, :building, 'WE 1', 5000)",
            "INSERT INTO renter (id, account_id, legal_name) VALUES (:renter, :a, 'Anna')",
            "INSERT INTO tenancy"
            " (id, account_id, unit_id, valid_from, valid_to, base_rent_cents)"
            " VALUES (:tenancy, :a, :unit, '2025-01-01', NULL, 85000)",
            "INSERT INTO tenancy_party (id, account_id, tenancy_id, renter_id)"
            " VALUES (:party, :a, :tenancy, :renter)",
            "INSERT INTO bank_account"
            " (id, account_id, provider, provider_account_id, normalized_iban, display_name)"
            " VALUES (:bank, :a, 'finapi', :provider, 'DE02120300000000202051', 'Mietkonto')",
            "INSERT INTO receivable"
            " (id, account_id, renter_id, tenancy_id, source_type, source_id, period, due_date,"
            " expected_cents, open_cents, status, category, base_rent_cents, nk_advance_cents,"
            " heating_advance_cents, garage_cents, open_costs_cents, open_interest_cents,"
            " open_principal_cents, stored_reference)"
            " VALUES (:receivable, :a, :renter, :tenancy, 'RECURRING_RENT', NULL, '2026-07',"
            " '2026-07-03', 108000, 108000, 'open', 'rent', 85000, 15000, 8000, 0, 0, 0,"
            " 108000, NULL)",
        )
        for statement in statements:
            connection.execute(text(statement), params)
        for tx, amount in ((ids.tx_auto, 108_000), (ids.tx_review, 108_000), (ids.tx_spare, 1)):
            connection.execute(
                text(
                    "INSERT INTO bank_transaction"
                    " (id, account_id, bank_account_id, provider_transaction_id, amount_cents,"
                    " bank_booking_date, finapi_booking_date, value_date, is_potential_duplicate)"
                    " VALUES (:id, :a, :bank, :provider, :amount, '2026-07-05', '2026-07-05',"
                    " '2026-07-05', false)"
                ),
                {
                    "id": tx,
                    "a": ids.account,
                    "bank": ids.bank_account,
                    "provider": tx,
                    "amount": amount,
                },
            )
        proposal_sql = (
            "INSERT INTO match_proposal"
            " (id, account_id, bank_transaction_id, receivable_id, renter_id, signal_iban,"
            " signal_amount, signal_code_or_surname, signal_e2e, signal_period, confidence,"
            f" decision, convention_version, reason_de{rank_column})"
            " VALUES (:id, :a, :tx, :receivable, :renter, :iban, 30, 0, 0, 5, :confidence,"
            f" :decision, 'docs/15 07/2026', :reason{rank_value})"
        )
        connection.execute(
            text(proposal_sql),
            {
                "id": ids.proposal_auto,
                "a": ids.account,
                "tx": ids.tx_auto,
                "receivable": ids.receivable,
                "renter": ids.renter,
                "iban": 60,
                "confidence": 95,
                "decision": "AUTO_MATCH",
                "reason": "Eindeutige IBAN.",
            },
        )
        connection.execute(
            text(proposal_sql),
            {
                "id": ids.proposal_review,
                "a": ids.account,
                "tx": ids.tx_review,
                "receivable": ids.receivable,
                "renter": ids.renter,
                "iban": 0,
                "confidence": 40,
                "decision": "NEEDS_REVIEW",
                "reason": "Bestätigung erforderlich.",
            },
        )
        connection.execute(
            text(
                "INSERT INTO match_confirmation"
                " (id, account_id, match_proposal_id, outcome, confirmed_by)"
                " VALUES (:id, :a, :proposal, 'CONFIRMED', :person)"
            ),
            {
                "id": ids.confirmation_review,
                "a": ids.account,
                "proposal": ids.proposal_review,
                "person": ids.person,
            },
        )
    return ids


@contextmanager
def rolled_back(engine: Engine) -> Iterator[Connection]:
    connection = engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        transaction.rollback()
        connection.close()


def _ledger_insert(
    connection: Connection,
    graph: Graph,
    *,
    transaction_id: str,
    proposal_id: str | None,
    amount: int,
    credit: int,
    kind: str = "PAYMENT",
    reverses: str | None = None,
) -> str:
    entry_id = new_id()
    connection.execute(
        text(
            "INSERT INTO payment_ledger_entry"
            " (id, account_id, bank_transaction_id, match_proposal_id, kind, amount_cents,"
            " credit_cents, ordering_version, reverses_entry_id)"
            " VALUES (:id, :a, :tx, :proposal, :kind, :amount, :credit, '§ 366/367 BGB', :reverses)"
        ),
        {
            "id": entry_id,
            "a": graph.account,
            "tx": transaction_id,
            "proposal": proposal_id,
            "kind": kind,
            "amount": amount,
            "credit": credit,
            "reverses": reverses,
        },
    )
    return entry_id


def _transaction_row(connection: Connection, graph: Graph, amount: int = 1) -> str:
    transaction_id = new_id()
    connection.execute(
        text(
            "INSERT INTO bank_transaction"
            " (id, account_id, bank_account_id, provider_transaction_id, amount_cents,"
            " bank_booking_date, finapi_booking_date, value_date, is_potential_duplicate)"
            " VALUES (:id, :a, :bank, :id, :amount, '2026-07-05', '2026-07-05',"
            " '2026-07-05', false)"
        ),
        {"id": transaction_id, "a": graph.account, "bank": graph.bank_account, "amount": amount},
    )
    return transaction_id


def _proposal_row(
    connection: Connection,
    graph: Graph,
    transaction_id: str,
    *,
    rank: int,
    decision: str = "NEEDS_REVIEW",
    reason: str = "Einheitlicher Vorschlagslauf.",
    version: str = "docs/15 07/2026",
    receivable_id: str | None = None,
) -> str:
    proposal_id = new_id()
    connection.execute(
        text(
            "INSERT INTO match_proposal"
            " (id, account_id, bank_transaction_id, receivable_id, renter_id, rank,"
            " signal_iban, signal_amount, signal_code_or_surname, signal_e2e, signal_period,"
            " confidence, decision, convention_version, reason_de)"
            " VALUES (:id, :a, :tx, :receivable, :renter, :rank, 0, 30, 10, 0, 0, 40,"
            " :decision, :version, :reason)"
        ),
        {
            "id": proposal_id,
            "a": graph.account,
            "tx": transaction_id,
            "receivable": receivable_id or graph.receivable,
            "renter": graph.renter,
            "rank": rank,
            "decision": decision,
            "version": version,
            "reason": reason,
        },
    )
    return proposal_id


def _two_candidate_batch(
    connection: Connection,
    graph: Graph,
    transaction_id: str,
    *,
    ranks: tuple[int, int] = (1, 2),
    decisions: tuple[str, str] = ("NEEDS_REVIEW", "NEEDS_REVIEW"),
    reasons: tuple[str, str] = ("Ein Lauf.", "Ein Lauf."),
    versions: tuple[str, str] = ("docs/15 07/2026", "docs/15 07/2026"),
) -> tuple[str, str]:
    first, second = new_id(), new_id()
    connection.execute(
        text(
            "INSERT INTO match_proposal"
            " (id, account_id, bank_transaction_id, receivable_id, renter_id, rank,"
            " signal_iban, signal_amount, signal_code_or_surname, signal_e2e, signal_period,"
            " confidence, decision, convention_version, reason_de) VALUES"
            " (:p1, :a, :tx, :receivable, :renter, :r1, 0, 30, 10, 0, 0, 40, :d1, :v1, :why1),"
            " (:p2, :a, :tx, :receivable, :renter, :r2, 0, 30, 10, 0, 0, 40, :d2, :v2, :why2)"
        ),
        {
            "p1": first,
            "p2": second,
            "a": graph.account,
            "tx": transaction_id,
            "receivable": graph.receivable,
            "renter": graph.renter,
            "r1": ranks[0],
            "r2": ranks[1],
            "d1": decisions[0],
            "d2": decisions[1],
            "v1": versions[0],
            "v2": versions[1],
            "why1": reasons[0],
            "why2": reasons[1],
        },
    )
    return first, second


def test_0021_is_head_and_metadata_has_rank_and_snapshots(owner: Engine) -> None:
    with owner.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0021"
    proposal_columns = {
        column["name"]: column for column in inspect(owner).get_columns("match_proposal")
    }
    assert proposal_columns["rank"]["nullable"] is False
    allocation_columns = {
        column["name"]: column for column in inspect(owner).get_columns("payment_allocation")
    }
    assert allocation_columns.keys() >= _SNAPSHOT_COLUMNS
    # Migration compatibility is explicit: an old allocation has no snapshot evidence.
    assert all(allocation_columns[name]["nullable"] for name in _SNAPSHOT_COLUMNS)


def test_rank_is_unique_per_transaction_and_existing_rows_are_backfilled(
    owner: Engine, graph: Graph
) -> None:
    with owner.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT rank FROM match_proposal WHERE id = :id"), {"id": graph.proposal_auto}
            )
            == 1
        )
        indexes = inspect(connection).get_indexes("match_proposal")
        assert any(
            index["unique"] and set(index["column_names"]) == {"bank_transaction_id", "rank"}
            for index in indexes
        )
    with rolled_back(owner) as connection, pytest.raises(DBAPIError):
        connection.execute(
            text(
                "INSERT INTO match_proposal"
                " (id, account_id, bank_transaction_id, receivable_id, renter_id, rank,"
                " signal_iban, signal_amount, signal_code_or_surname, signal_e2e, signal_period,"
                " confidence, decision, convention_version, reason_de)"
                " SELECT :id, account_id, bank_transaction_id, receivable_id, renter_id, rank,"
                " signal_iban, signal_amount, signal_code_or_surname, signal_e2e, signal_period,"
                " confidence, decision, convention_version, reason_de FROM match_proposal"
                " WHERE id = :source"
            ),
            {"id": new_id(), "source": graph.proposal_auto},
        )


def test_rank_two_cannot_be_confirmed(owner: Engine, graph: Graph) -> None:
    with rolled_back(owner) as connection:
        transaction_id = _transaction_row(connection, graph)
        _, lower = _two_candidate_batch(connection, graph, transaction_id)
        with pytest.raises(DBAPIError):
            connection.execute(
                text(
                    "INSERT INTO match_confirmation"
                    " (id, account_id, match_proposal_id, outcome, confirmed_by)"
                    " VALUES (:id, :a, :proposal, 'CONFIRMED', :person)"
                ),
                {"id": new_id(), "a": graph.account, "proposal": lower, "person": graph.person},
            )


def test_rank_two_auto_proposal_cannot_evidence_a_payment(owner: Engine, graph: Graph) -> None:
    with rolled_back(owner) as connection:
        transaction_id = _transaction_row(connection, graph)
        _, lower = _two_candidate_batch(
            connection,
            graph,
            transaction_id,
            decisions=("AUTO_MATCH", "AUTO_MATCH"),
        )
        with pytest.raises(DBAPIError):
            _ledger_insert(
                connection,
                graph,
                transaction_id=transaction_id,
                proposal_id=lower,
                amount=1,
                credit=1,
            )


def test_proposal_run_is_sealed_after_its_initial_insert(owner: Engine, graph: Graph) -> None:
    with rolled_back(owner) as connection, pytest.raises(DBAPIError):
        _proposal_row(connection, graph, graph.tx_auto, rank=2, decision="AUTO_MATCH")


def test_initial_proposal_batch_is_contiguous_and_internally_consistent(
    owner: Engine, graph: Graph
) -> None:
    with rolled_back(owner) as connection:
        transaction_id = _transaction_row(connection, graph)
        _two_candidate_batch(
            connection,
            graph,
            transaction_id,
            ranks=(1, 3),
            decisions=("NEEDS_REVIEW", "UNMATCHED"),
            reasons=("Ein Lauf.", "Abweichender Grund."),
            versions=("docs/15 07/2026", "abweichende-version"),
        )
        with pytest.raises(DBAPIError):
            connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_iban_history_uses_timezone_aware_datetime_metadata(owner: Engine) -> None:
    columns = {column["name"]: column for column in inspect(owner).get_columns("iban_history")}
    for name in ("valid_from", "valid_to"):
        assert isinstance(columns[name]["type"], DateTime)
        assert getattr(columns[name]["type"], "timezone", False) is True


def _nk_payment(connection: Connection, graph: Graph) -> tuple[str, str]:
    receivable_id = new_id()
    amount = 24_500
    connection.execute(
        text(
            "INSERT INTO receivable"
            " (id, account_id, renter_id, tenancy_id, source_type, source_id, period, due_date,"
            " expected_cents, open_cents, status, category, base_rent_cents, nk_advance_cents,"
            " heating_advance_cents, garage_cents, open_costs_cents, open_interest_cents,"
            " open_principal_cents, stored_reference)"
            " VALUES (:id, :a, :renter, :tenancy, 'PAGE01_STATEMENT', :source, :period,"
            " '2026-07-05', :amount, :amount, 'open', 'nk_nachzahlung', 0, 0, 0, 0, 0, 0,"
            " :amount, NULL)"
        ),
        {
            "id": receivable_id,
            "a": graph.account,
            "renter": graph.renter,
            "tenancy": graph.tenancy,
            "source": new_id(),
            "period": f"fixture-{new_id()}",
            "amount": amount,
        },
    )
    transaction_id = _transaction_row(connection, graph, amount)
    proposal_id = _proposal_row(
        connection,
        graph,
        transaction_id,
        rank=1,
        decision="AUTO_MATCH",
        receivable_id=receivable_id,
    )
    entry_id = _ledger_insert(
        connection,
        graph,
        transaction_id=transaction_id,
        proposal_id=proposal_id,
        amount=amount,
        credit=0,
    )
    return receivable_id, entry_id


def _allocation_row(
    connection: Connection,
    graph: Graph,
    *,
    entry_id: str,
    receivable_id: str,
    principal: int,
    base_rent: int,
) -> None:
    connection.execute(
        text(
            "INSERT INTO payment_allocation"
            " (id, account_id, ledger_entry_id, receivable_id, costs_cents, interest_cents,"
            " principal_cents, base_rent_cents, nk_advance_cents, heating_advance_cents,"
            " garage_cents, resulting_status)"
            " VALUES (:id, :a, :entry, :receivable, 0, 0, :principal, :base, 0, 0, 0, 'settled')"
        ),
        {
            "id": new_id(),
            "a": graph.account,
            "entry": entry_id,
            "receivable": receivable_id,
            "principal": principal,
            "base": base_rent,
        },
    )


def test_nachzahlung_allocation_uses_no_rent_or_advance_component(
    owner: Engine, graph: Graph
) -> None:
    with rolled_back(owner) as connection:
        receivable_id, entry_id = _nk_payment(connection, graph)
        _allocation_row(
            connection,
            graph,
            entry_id=entry_id,
            receivable_id=receivable_id,
            principal=24_500,
            base_rent=0,
        )
        connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_nachzahlung_allocation_refuses_a_named_rent_component(owner: Engine, graph: Graph) -> None:
    with rolled_back(owner) as connection:
        receivable_id, entry_id = _nk_payment(connection, graph)
        with pytest.raises(DBAPIError):
            _allocation_row(
                connection,
                graph,
                entry_id=entry_id,
                receivable_id=receivable_id,
                principal=24_500,
                base_rent=24_500,
            )


def test_rent_allocation_refuses_missing_component_classification(
    owner: Engine, graph: Graph
) -> None:
    with rolled_back(owner) as connection:
        transaction_id = _transaction_row(connection, graph, 1)
        proposal_id = _proposal_row(
            connection, graph, transaction_id, rank=1, decision="AUTO_MATCH"
        )
        entry_id = _ledger_insert(
            connection,
            graph,
            transaction_id=transaction_id,
            proposal_id=proposal_id,
            amount=1,
            credit=0,
        )
        with pytest.raises(DBAPIError):
            _allocation_row(
                connection,
                graph,
                entry_id=entry_id,
                receivable_id=graph.receivable,
                principal=1,
                base_rent=0,
            )


@pytest.mark.parametrize(
    "decision,outcome,allowed",
    [
        ("AUTO_MATCH", None, True),
        ("NEEDS_REVIEW", "CONFIRMED", True),
        ("NEEDS_REVIEW", None, False),
        ("NEEDS_REVIEW", "REJECTED", False),
        ("NEEDS_REVIEW", "DUPLICATE", False),
        ("UNMATCHED", None, False),
    ],
)
def test_payment_requires_auto_or_confirmed_review_evidence(
    owner: Engine, graph: Graph, decision: str, outcome: str | None, allowed: bool
) -> None:
    with rolled_back(owner) as connection:
        tx = new_id()
        proposal = new_id()
        params = {
            "tx": tx,
            "a": graph.account,
            "bank": graph.bank_account,
            "proposal": proposal,
            "decision": decision,
        }
        connection.execute(
            text(
                "INSERT INTO bank_transaction"
                " (id, account_id, bank_account_id, provider_transaction_id, amount_cents,"
                " bank_booking_date, finapi_booking_date, value_date, is_potential_duplicate)"
                " VALUES (:tx, :a, :bank, :tx, 1, '2026-07-05', '2026-07-05', '2026-07-05', false)"
            ),
            params,
        )
        connection.execute(
            text(
                " INSERT INTO match_proposal"
                " (id, account_id, bank_transaction_id, receivable_id, renter_id, rank,"
                " signal_iban,"
                " signal_amount, signal_code_or_surname, signal_e2e, signal_period, confidence,"
                " decision, convention_version, reason_de)"
                " VALUES (:proposal, :a, :tx, NULL, NULL, 1, 0, 0, 0, 0, 0, 0, :decision,"
                " 'docs/15 07/2026', 'Evidenz')"
            ),
            params,
        )
        if outcome is not None:
            connection.execute(
                text(
                    "INSERT INTO match_confirmation"
                    " (id, account_id, match_proposal_id, outcome, confirmed_by)"
                    " VALUES (:id, :a, :proposal, :outcome, :person)"
                ),
                {
                    "id": new_id(),
                    "a": graph.account,
                    "proposal": proposal,
                    "outcome": outcome,
                    "person": graph.person,
                },
            )
        if allowed:
            _ledger_insert(
                connection, graph, transaction_id=tx, proposal_id=proposal, amount=1, credit=1
            )
            connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        else:
            with pytest.raises(DBAPIError):
                _ledger_insert(
                    connection, graph, transaction_id=tx, proposal_id=proposal, amount=1, credit=1
                )


def test_credit_and_allocation_reconcile_at_deferred_constraint_time(
    owner: Engine, graph: Graph
) -> None:
    with rolled_back(owner) as connection:
        entry = _ledger_insert(
            connection,
            graph,
            transaction_id=graph.tx_auto,
            proposal_id=graph.proposal_auto,
            amount=108_000,
            credit=0,
        )
        # No allocation means the correct credit is the full payment, not zero.
        with pytest.raises(DBAPIError):
            connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        assert entry


def test_reversal_credit_is_zero_and_projection_snapshot_pair_is_complete_or_legacy_null(
    owner: Engine,
) -> None:
    checks = {
        constraint["name"]
        for constraint in inspect(owner).get_check_constraints("payment_ledger_entry")
        if isinstance(constraint["name"], str)
    }
    assert any("credit" in name and "reversal" in name for name in checks)
    with owner.connect() as connection:
        partial_pairs = connection.scalar(
            text(
                "SELECT count(*) FROM payment_allocation WHERE"
                " (before_open_cents IS NULL) <> (after_open_cents IS NULL)"
            )
        )
        assert partial_pairs == 0


def test_evidence_trigger_is_after_and_all_new_functions_are_hardened(owner: Engine) -> None:
    with owner.connect() as connection:
        timing = connection.execute(
            text(
                "SELECT t.tgtype, p.proconfig, pg_get_functiondef(p.oid)"
                " FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid"
                " WHERE t.tgrelid = 'public.payment_ledger_entry'::regclass"
                " AND t.tgname = 'payment_ledger_evidence'"
            )
        ).one()
        # PostgreSQL tgtype bit 2 is BEFORE. It must be absent so RLS WITH CHECK speaks first.
        assert timing.tgtype & 2 == 0
        assert "search_path=pg_catalog, public, pg_temp" in "".join(timing.proconfig or [])
        assert isinstance(timing.pg_get_functiondef, str)
        assert "public.match_proposal" in timing.pg_get_functiondef
        functions = connection.execute(
            text(
                "SELECT p.proconfig, pg_get_functiondef(p.oid) AS body FROM pg_proc p"
                " WHERE p.pronamespace = 'public'::regnamespace"
                " AND p.proname LIKE '%m6c3a%'"
            )
        ).all()
        assert functions
        assert all(
            "search_path=pg_catalog, public, pg_temp" in "".join(row.proconfig or [])
            for row in functions
        )


def test_foreign_account_write_reaches_rls_before_evidence_trigger(
    owner: Engine, graph: Graph
) -> None:
    app = create_db_engine(DbSettings().database_url)
    try:
        with (
            pytest.raises(DBAPIError) as exc_info,
            account_scoped_session(app, graph.foreign_account) as session,
        ):
            session.execute(
                text(
                    "INSERT INTO payment_ledger_entry"
                    " (id, account_id, bank_transaction_id, match_proposal_id, kind,"
                    " amount_cents, credit_cents, ordering_version, reverses_entry_id)"
                    " VALUES (:id, :a, :tx, :proposal, 'PAYMENT', 108000, 108000,"
                    " '§ 366/367 BGB', NULL)"
                ),
                {
                    "id": new_id(),
                    "a": graph.account,
                    "tx": graph.tx_auto,
                    "proposal": graph.proposal_auto,
                },
            )
        assert "row-level security policy" in str(exc_info.value).lower()
    finally:
        app.dispose()
