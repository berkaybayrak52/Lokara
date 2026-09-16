"""RED M10-I3 entitlement persistence contract from docs/14 § 4.8.

Fixture coverage: M10-INV-F01 and M10-INV-F02. The tests pin migration 0046,
the mapped boundary, append-only correction chain and account RLS before source
implementation exists.
"""

from __future__ import annotations

import importlib
import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from lokara_db import Base, DbSettings, account_scoped_session, create_db_engine, new_id
from sqlalchemy import (
    Connection,
    Engine,
    ForeignKeyConstraint,
    UniqueConstraint,
    select,
    text,
)
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.sql.elements import TextClause
from sqlalchemy.sql.schema import Table

_DB_DIR = Path(__file__).resolve().parent.parent
TABLE = "investment_entitlement_event"


def _migration_path() -> Path:
    migrations = tuple((_DB_DIR / "alembic" / "versions").glob("0046_*.py"))
    assert len(migrations) == 1, "RED M10-I3: migration 0046 is missing"
    return migrations[0]


def _migration_source() -> str:
    return _migration_path().read_text()


def _table() -> Table:
    assert TABLE in Base.metadata.tables, "RED M10-I3: entitlement model is missing"
    return Base.metadata.tables[TABLE]


def _unique_sets(table: Table) -> set[frozenset[str]]:
    return {
        frozenset(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def _has_fk(table: Table, local: tuple[str, ...], remote: tuple[str, ...]) -> bool:
    return any(
        isinstance(constraint, ForeignKeyConstraint)
        and tuple(constraint.column_keys) == local
        and tuple(
            f"{element.column.table.name}.{element.column.name}" for element in constraint.elements
        )
        == remote
        for constraint in table.constraints
    )


def test_m10_inv_f01_migration_and_model_have_exact_entitlement_shape() -> None:
    path = _migration_path()
    source = path.read_text()
    assert 'revision = "0046"' in source
    assert 'down_revision = "0045"' in source
    assert f'"{TABLE}"' in source

    db = importlib.import_module("lokara_db")
    model = getattr(db, "InvestmentEntitlementEvent", None)
    assert model is not None, "RED M10-I3: InvestmentEntitlementEvent is missing"
    assert model.__tablename__ == TABLE

    table = _table()
    assert set(table.columns.keys()) == {
        "id",
        "account_id",
        "entitlement_key",
        "version",
        "enabled",
        "supersedes_entitlement_event_id",
        "recorded_by_membership_id",
        "recorded_at",
    }
    for name in (
        "account_id",
        "entitlement_key",
        "version",
        "enabled",
        "recorded_by_membership_id",
        "recorded_at",
    ):
        assert not table.columns[name].nullable
    assert table.columns["supersedes_entitlement_event_id"].nullable
    assert table.columns["recorded_at"].server_default is not None
    assert frozenset({"id", "account_id", "entitlement_key"}) in _unique_sets(table)
    assert frozenset({"account_id", "entitlement_key", "version"}) in _unique_sets(table)
    assert _has_fk(
        table,
        ("supersedes_entitlement_event_id", "account_id", "entitlement_key"),
        (
            "investment_entitlement_event.id",
            "investment_entitlement_event.account_id",
            "investment_entitlement_event.entitlement_key",
        ),
    )
    assert _has_fk(
        table,
        ("recorded_by_membership_id", "account_id"),
        ("membership.id", "membership.account_id"),
    )


def test_m10_inv_f01_migration_enforces_key_chain_immutability_and_rls() -> None:
    normalized = " ".join(_migration_source().lower().split())
    assert "entitlement_key = 'investment'" in normalized
    assert "version > 0" in normalized
    assert "version = 1" in normalized and "version > 1" in normalized
    assert "predecessor.version = new.version - 1" in normalized
    for index in (
        "uq_investment_entitlement_event_root",
        "uq_investment_entitlement_event_successor",
    ):
        assert index in normalized
    assert "prevent_investment_entitlement_rewrite_m10" in normalized
    assert "before update or delete" in normalized
    assert f"alter table public.{TABLE} enable row level security" in normalized
    assert f"alter table public.{TABLE} force row level security" in normalized
    assert f"create policy {TABLE}_owner_select" in normalized
    assert f"create policy {TABLE}_owner_insert" in normalized
    assert "with check (account_id = current_setting('app.account_id', true)" in normalized
    assert "current_setting('app.tenancy_id', true)" in normalized


@pytest.fixture(scope="module")
def engines() -> Iterator[tuple[Engine, Engine]]:
    """Current owner/app engines; DB-backed probes are mandatory in CI."""
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
    app = create_db_engine(settings.database_url)
    yield owner, app
    app.dispose()
    owner.dispose()


_EVENT_INSERT = text(
    "INSERT INTO investment_entitlement_event "
    "(id, account_id, entitlement_key, version, enabled, "
    "supersedes_entitlement_event_id, recorded_by_membership_id) VALUES "
    "(:id, :account, :key, :version, :enabled, :supersedes, :membership)"
)


def _event_values(
    account_id: str,
    membership_id: str,
    *,
    version: int = 1,
    enabled: bool = True,
    supersedes: str | None = None,
    entitlement_key: str = "INVESTMENT",
) -> dict[str, object]:
    return {
        "id": new_id(),
        "account": account_id,
        "key": entitlement_key,
        "version": version,
        "enabled": enabled,
        "supersedes": supersedes,
        "membership": membership_id,
    }


@contextmanager
def _owner_graph(engine: Engine) -> Iterator[tuple[Connection, str, str, str, str]]:
    account_a, account_b = new_id(), new_id()
    person_a, person_b = new_id(), new_id()
    membership_a, membership_b = new_id(), new_id()
    connection = engine.connect()
    transaction = connection.begin()
    try:
        connection.execute(
            text(
                "INSERT INTO account (id, name, shape, plan) VALUES "
                "(:a, 'M10-I3 A', 'SOLO', 'TRIAL'), (:b, 'M10-I3 B', 'SOLO', 'TRIAL')"
            ),
            {"a": account_a, "b": account_b},
        )
        connection.execute(
            text("INSERT INTO person (id, email) VALUES (:a, :email_a), (:b, :email_b)"),
            {
                "a": person_a,
                "b": person_b,
                "email_a": f"{person_a}@example.test",
                "email_b": f"{person_b}@example.test",
            },
        )
        connection.execute(
            text(
                "INSERT INTO membership "
                "(id, person_id, account_id, role, accepted_at, revoked_at) VALUES "
                "(:ma, :pa, :aa, 'OWNER', :accepted, NULL), "
                "(:mb, :pb, :ab, 'OWNER', :accepted, NULL)"
            ),
            {
                "ma": membership_a,
                "pa": person_a,
                "aa": account_a,
                "mb": membership_b,
                "pb": person_b,
                "ab": account_b,
                "accepted": datetime(2026, 9, 16, tzinfo=UTC),
            },
        )
        yield connection, account_a, account_b, membership_a, membership_b
    finally:
        transaction.rollback()
        connection.close()


def _expect_rejected(
    connection: Connection, statement: TextClause, values: Mapping[str, object]
) -> None:
    savepoint = connection.begin_nested()
    try:
        with pytest.raises(DBAPIError) as refused:
            connection.execute(statement, values)
    finally:
        savepoint.rollback()
    assert getattr(refused.value.orig, "sqlstate", None) != "42P01"


def test_m10_inv_f02_live_appends_enable_disable_with_server_time(
    engines: tuple[Engine, Engine],
) -> None:
    owner, _app = engines
    with _owner_graph(owner) as (connection, account_a, _account_b, member_a, _member_b):
        root = _event_values(account_a, member_a)
        connection.execute(_EVENT_INSERT, root)
        disabled = _event_values(
            account_a,
            member_a,
            version=2,
            enabled=False,
            supersedes=str(root["id"]),
        )
        connection.execute(_EVENT_INSERT, disabled)
        rows = connection.execute(
            text(
                "SELECT entitlement_key, version, enabled, supersedes_entitlement_event_id, "
                "recorded_by_membership_id, recorded_at FROM investment_entitlement_event "
                "WHERE account_id = :account ORDER BY version"
            ),
            {"account": account_a},
        ).all()
        assert [(row.entitlement_key, row.version, row.enabled) for row in rows] == [
            ("INVESTMENT", 1, True),
            ("INVESTMENT", 2, False),
        ]
        assert rows[0].supersedes_entitlement_event_id is None
        assert rows[1].supersedes_entitlement_event_id == root["id"]
        assert all(row.recorded_by_membership_id == member_a for row in rows)
        assert all(row.recorded_at is not None for row in rows)


@pytest.mark.parametrize("case", ("bad_key", "skipped", "forked", "foreign_author"))
def test_m10_inv_f02_live_refuses_invalid_entitlement_streams(
    engines: tuple[Engine, Engine], case: str
) -> None:
    owner, _app = engines
    with _owner_graph(owner) as (connection, account_a, _account_b, member_a, member_b):
        root = _event_values(account_a, member_a)
        connection.execute(_EVENT_INSERT, root)
        if case == "forked":
            connection.execute(
                _EVENT_INSERT,
                _event_values(account_a, member_a, version=2, supersedes=str(root["id"])),
            )
        candidate = _event_values(
            account_a,
            member_b if case == "foreign_author" else member_a,
            entitlement_key="BILLING" if case == "bad_key" else "INVESTMENT",
            version=3 if case == "skipped" else 2,
            supersedes=str(root["id"]),
        )
        _expect_rejected(connection, _EVENT_INSERT, candidate)


@pytest.mark.parametrize("verb", ("UPDATE", "DELETE"))
def test_m10_inv_f01_live_rejects_entitlement_rewrites(
    engines: tuple[Engine, Engine], verb: str
) -> None:
    owner, _app = engines
    with _owner_graph(owner) as (connection, account_a, _account_b, member_a, _member_b):
        root = _event_values(account_a, member_a)
        connection.execute(_EVENT_INSERT, root)
        statement = (
            text("UPDATE investment_entitlement_event SET enabled = false WHERE id = :id")
            if verb == "UPDATE"
            else text("DELETE FROM investment_entitlement_event WHERE id = :id")
        )
        _expect_rejected(connection, statement, {"id": root["id"]})


def test_m10_inv_f01_live_rls_scopes_reads_writes_and_refuses_renter_context(
    engines: tuple[Engine, Engine],
) -> None:
    owner, app = engines
    account_a, account_b = new_id(), new_id()
    person_a, person_b = new_id(), new_id()
    membership_a, membership_b = new_id(), new_id()
    with owner.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO account (id, name, shape, plan) VALUES "
                "(:a, 'M10-I3 RLS A', 'SOLO', 'TRIAL'), "
                "(:b, 'M10-I3 RLS B', 'SOLO', 'TRIAL')"
            ),
            {"a": account_a, "b": account_b},
        )
        connection.execute(
            text("INSERT INTO person (id, email) VALUES (:a, :ea), (:b, :eb)"),
            {
                "a": person_a,
                "b": person_b,
                "ea": f"{person_a}@example.test",
                "eb": f"{person_b}@example.test",
            },
        )
        connection.execute(
            text(
                "INSERT INTO membership "
                "(id, person_id, account_id, role, accepted_at, revoked_at) VALUES "
                "(:ma, :pa, :aa, 'OWNER', :accepted, NULL), "
                "(:mb, :pb, :ab, 'OWNER', :accepted, NULL)"
            ),
            {
                "ma": membership_a,
                "pa": person_a,
                "aa": account_a,
                "mb": membership_b,
                "pb": person_b,
                "ab": account_b,
                "accepted": datetime(2026, 9, 16, tzinfo=UTC),
            },
        )

    event = _event_values(account_a, membership_a)
    with account_scoped_session(app, account_a) as session:
        session.execute(_EVENT_INSERT, event)
        assert (
            session.scalar(select(_table().c.id).where(_table().c.id == event["id"])) == event["id"]
        )

    with account_scoped_session(app, account_b) as session:
        assert session.scalar(select(_table().c.id).where(_table().c.id == event["id"])) is None
        savepoint = session.begin_nested()
        try:
            with pytest.raises(DBAPIError):
                session.execute(
                    _EVENT_INSERT,
                    _event_values(account_a, membership_a),
                )
        finally:
            savepoint.rollback()

    with account_scoped_session(app, account_a) as session:
        session.execute(
            text("SELECT set_config('app.tenancy_id', :id, true)"),
            {"id": new_id()},
        )
        assert session.scalar(select(_table().c.id).where(_table().c.id == event["id"])) is None
        savepoint = session.begin_nested()
        try:
            with pytest.raises(DBAPIError):
                session.execute(_EVENT_INSERT, _event_values(account_a, membership_a))
        finally:
            savepoint.rollback()
