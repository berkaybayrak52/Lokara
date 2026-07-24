"""RLS isolation tests against a live Postgres — the Phase B gate.

The whole ballgame (MIGRATION-PLAN B.3): a session carrying account B's RLS
context must NOT see account A's rows, as the non-owner `lokara_app` role.

The suite is self-sufficient: it applies scripts/init-app-role.sql and
`alembic upgrade head` itself, so a plain `pytest` run only needs the
docker-compose Postgres (locally) or the CI service container.

Skips when Postgres is unreachable — unless LOKARA_REQUIRE_DB is set (CI sets
it, so the gate can never silently vanish there). Seeding runs as the local
superuser, which bypasses RLS even though the policies are FORCEd.
TODO(supabase): on Supabase the migration role is a non-superuser owner, so
FORCE binds it too — admin/seed flows there must set a context.
"""

import os
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from lokara_db import (
    Account,
    Building,
    BuildingAssignment,
    DbSettings,
    Membership,
    Person,
    Renter,
    Role,
    Statement,
    StatementStatus,
    account_scoped_session,
    create_db_engine,
    new_id,
)
from sqlalchemy import CursorResult, Engine, select, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent


def _upgraded_engines() -> tuple[Engine, Engine]:
    """(owner engine, app engine) with role + schema guaranteed current."""
    settings = DbSettings()
    owner = create_db_engine(settings.direct_url)
    with owner.connect() as conn:
        conn.execute(text((_DB_PACKAGE_DIR / "scripts" / "init-app-role.sql").read_text()))
        conn.commit()
    command.upgrade(Config(str(_DB_PACKAGE_DIR / "alembic.ini")), "head")
    return owner, create_db_engine(settings.database_url)


@pytest.fixture(scope="module")
def engines() -> Iterator[tuple[Engine, Engine]]:
    try:
        owner, app = _upgraded_engines()
    except OperationalError as exc:  # DB not running
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")
    yield owner, app
    app.dispose()
    owner.dispose()


class _Seed:
    """Two accounts: A owns a person/membership/building/assignment/renter/statement;
    B is empty. Unique ids per run so reruns never collide."""

    def __init__(self) -> None:
        self.account_a = new_id()
        self.account_b = new_id()
        self.building_a = new_id()
        self.renter_a = new_id()
        self.statement_a = new_id()
        self.person_a = new_id()
        self.membership_a = new_id()
        self.assignment_a = new_id()


@pytest.fixture(scope="module")
def seed(engines: tuple[Engine, Engine]) -> Iterator[_Seed]:
    owner, _ = engines
    ids = _Seed()
    with Session(owner) as session, session.begin():
        session.add(Account(id=ids.account_a, name="Konto A"))
        session.add(Account(id=ids.account_b, name="Konto B"))
        session.add(Person(id=ids.person_a, email=f"owner-{ids.person_a}@example.test"))
        session.add(
            Membership(
                id=ids.membership_a,
                person_id=ids.person_a,
                account_id=ids.account_a,
                role=Role.OWNER,
            )
        )
        session.add(
            Building(
                id=ids.building_a,
                account_id=ids.account_a,
                name="Haus A",
                street="Musterstraße 1",
                postal_code="10115",
                city="Berlin",
            )
        )
        session.add(
            BuildingAssignment(
                id=ids.assignment_a,
                membership_id=ids.membership_a,
                building_id=ids.building_a,
            )
        )
        session.add(Renter(id=ids.renter_a, account_id=ids.account_a, legal_name="Mieter A"))
        session.add(
            Statement(
                id=ids.statement_a,
                account_id=ids.account_a,
                building_id=ids.building_a,
                period_start=date(2025, 1, 1),
                period_end=date(2025, 12, 31),
                version=1,
                status=StatementStatus.DRAFT,
                total_cents=120000,
            )
        )
    yield ids
    with Session(owner) as session, session.begin():
        for model, row_id in (
            (Statement, ids.statement_a),
            (BuildingAssignment, ids.assignment_a),
            (Renter, ids.renter_a),
            (Building, ids.building_a),
            (Membership, ids.membership_a),
            (Person, ids.person_a),
            (Account, ids.account_a),
            (Account, ids.account_b),
        ):
            obj = session.get(model, row_id)
            if obj is not None:
                session.delete(obj)


class TestRuntimeRole:
    def test_app_role_cannot_bypass_rls(self, engines: tuple[Engine, Engine]) -> None:
        """If DATABASE_URL ever points at an owner/superuser, RLS silently stops
        applying — fail loudly here instead."""
        _, app = engines
        with Session(app) as session:
            row = session.execute(
                text(
                    "SELECT current_user, rolsuper, rolbypassrls "
                    "FROM pg_roles WHERE rolname = current_user"
                )
            ).one()
        assert row.current_user == "lokara_app"
        assert not row.rolsuper
        assert not row.rolbypassrls


class TestCrossAccountIsolation:
    def test_cross_account_read_is_blocked(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """THE Phase B gate: account B's context must not see account A's rows."""
        _, app = engines
        with account_scoped_session(app, seed.account_b) as session:
            assert session.scalars(select(Building)).all() == []
            assert session.scalars(select(Renter)).all() == []
            assert session.scalars(select(Statement)).all() == []
            assert session.scalars(select(Membership)).all() == []
            assert session.scalars(select(BuildingAssignment)).all() == []
            assert session.scalars(select(Account.id)).all() == [seed.account_b]

    def test_own_context_sees_own_rows(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """Non-vacuous control: the same query with A's context finds A's rows —
        so the empty results above are RLS at work, not an empty database."""
        _, app = engines
        with account_scoped_session(app, seed.account_a) as session:
            assert session.scalars(select(Building.id)).all() == [seed.building_a]
            assert session.scalars(select(Renter.id)).all() == [seed.renter_a]
            assert session.scalars(select(Statement.id)).all() == [seed.statement_a]
            assert session.scalars(select(BuildingAssignment.id)).all() == [seed.assignment_a]
            assert session.scalars(select(Account.id)).all() == [seed.account_a]

    def test_missing_context_denies_by_default(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """No app.account_id set → current_setting returns NULL → zero rows."""
        _, app = engines
        with Session(app) as session:
            assert session.scalars(select(Building)).all() == []
            assert session.scalars(select(Account)).all() == []

    def test_cross_account_write_is_rejected(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """WITH CHECK: B's context cannot insert a row claiming account A."""
        _, app = engines
        with (
            pytest.raises(ProgrammingError, match="row-level security"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                Building(
                    account_id=seed.account_a,
                    name="Eingeschleust",
                    street="Leak-Allee 1",
                    postal_code="00000",
                    city="Nirgendwo",
                )
            )
            session.flush()

    def test_cross_account_update_cannot_reach_foreign_rows(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """UPDATE under B's context simply cannot see A's row — 0 rows touched,
        and A's data is unchanged afterwards."""
        _, app = engines
        with account_scoped_session(app, seed.account_b) as session:
            result: CursorResult[Any] = session.connection().execute(
                text("UPDATE building SET name = 'gekapert' WHERE id = :bid"),
                {"bid": seed.building_a},
            )
            assert result.rowcount == 0
        with account_scoped_session(app, seed.account_a) as session:
            building = session.get(Building, seed.building_a)
            assert building is not None and building.name == "Haus A"
