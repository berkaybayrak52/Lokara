"""Red contract for the sole pre-account-context database read.

The specification is ``docs/02-data-model.md`` → "The bootstrap contexts read".
The implementation is intentionally absent when this fixture is written: migration 0006
must add one bounded ``SECURITY DEFINER`` function, ``app_bootstrap_contexts(text)``.
"""

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from lokara_db import (
    Account,
    AccountShape,
    DbSettings,
    Membership,
    Person,
    Role,
    create_db_engine,
    new_id,
)
from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent

APP_ROLE = "lokara_app"
BOOTSTRAP_ROLE = "lokara_bootstrap"
BOOTSTRAP_FUNCTION = "app_bootstrap_contexts"
READABLE_TABLES = frozenset({"person", "membership", "account"})


def _upgraded_engines() -> tuple[Engine, Engine]:
    settings = DbSettings()
    owner = create_db_engine(settings.direct_url)
    with owner.connect() as connection:
        connection.execute(text((_DB_PACKAGE_DIR / "scripts" / "init-app-role.sql").read_text()))
        connection.commit()
    command.upgrade(Config(str(_DB_PACKAGE_DIR / "alembic.ini")), "head")
    return owner, create_db_engine(settings.database_url)


@pytest.fixture(scope="module")
def engines() -> Iterator[tuple[Engine, Engine]]:
    try:
        owner, app = _upgraded_engines()
    except OperationalError as exc:
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")
    yield owner, app
    app.dispose()
    owner.dispose()


class _Seed:
    def __init__(self) -> None:
        self.account_one = new_id()
        self.account_two = new_id()
        self.other_account = new_id()
        self.switcher = new_id()
        self.unmembered = new_id()
        self.revoked = new_id()
        self.colleague = new_id()
        self.unknown = new_id()
        self.memberships = [new_id() for _ in range(4)]


@pytest.fixture(scope="module")
def seed(engines: tuple[Engine, Engine]) -> Iterator[_Seed]:
    owner, _ = engines
    ids = _Seed()
    with Session(owner) as session, session.begin():
        session.add(Account(id=ids.account_one, name="Hausverwaltung Nord"))
        session.add(
            Account(
                id=ids.account_two,
                name="Immobilien Süd",
                shape=AccountShape.HAUSVERWALTUNG,
            )
        )
        session.add(Account(id=ids.other_account, name="Fremdkonto"))
        for person_id in (ids.switcher, ids.unmembered, ids.revoked, ids.colleague):
            session.add(Person(id=person_id, email=f"{person_id}@example.test"))
        session.add_all(
            [
                Membership(
                    id=ids.memberships[0],
                    person_id=ids.switcher,
                    account_id=ids.account_one,
                    role=Role.OWNER,
                ),
                Membership(
                    id=ids.memberships[1],
                    person_id=ids.switcher,
                    account_id=ids.account_two,
                    role=Role.EMPLOYEE,
                ),
                Membership(
                    id=ids.memberships[2],
                    person_id=ids.colleague,
                    account_id=ids.other_account,
                    role=Role.TAX_ADVISOR,
                ),
                Membership(
                    id=ids.memberships[3],
                    person_id=ids.revoked,
                    account_id=ids.other_account,
                    role=Role.EMPLOYEE,
                    revoked_at=datetime(2026, 1, 31, 12, 0, tzinfo=UTC),
                ),
            ]
        )
    yield ids
    with Session(owner) as session, session.begin():
        for membership_id in ids.memberships:
            membership_row = session.get(Membership, membership_id)
            if membership_row is not None:
                session.delete(membership_row)
    with Session(owner) as session, session.begin():
        for person_id in (ids.switcher, ids.unmembered, ids.revoked, ids.colleague):
            person_row = session.get(Person, person_id)
            if person_row is not None:
                session.delete(person_row)
        for account_id in (ids.account_one, ids.account_two, ids.other_account):
            account_row = session.get(Account, account_id)
            if account_row is not None:
                session.delete(account_row)


def _contexts(
    app: Engine, person_id: str
) -> list[tuple[str, str, str | None, str | None, str | None, str | None]]:
    """Call the function as lokara_app with no app.account_id set."""
    with Session(app) as session:
        rows = session.execute(
            text(f"SELECT * FROM {BOOTSTRAP_FUNCTION}(:person_id)"),
            {"person_id": person_id},
        ).all()
    return [
        (
            str(row.person_id),
            str(row.email),
            row.account_id,
            row.account_name,
            row.account_shape,
            row.membership_role,
        )
        for row in rows
    ]


class TestBootstrapMechanismShape:
    """Database-catalog invariants: the bypass is bounded outside application code."""

    def test_exactly_one_security_definer_function_exists(
        self, engines: tuple[Engine, Engine]
    ) -> None:
        owner, _ = engines
        with Session(owner) as session:
            functions = session.execute(
                text(
                    "SELECT p.proname, oidvectortypes(p.proargtypes) AS arguments "
                    "FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
                    "WHERE n.nspname = 'public' AND p.prosecdef"
                )
            ).all()
        assert [(row.proname, row.arguments) for row in functions] == [(BOOTSTRAP_FUNCTION, "text")]

    def test_function_is_owned_by_the_bounded_role_and_read_only(
        self, engines: tuple[Engine, Engine]
    ) -> None:
        owner, _ = engines
        with Session(owner) as session:
            function = session.execute(
                text(
                    "SELECT owner.rolname, p.provolatile, p.proconfig "
                    "FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
                    "JOIN pg_roles owner ON owner.oid = p.proowner "
                    "WHERE n.nspname = 'public' AND p.proname = :function"
                ),
                {"function": BOOTSTRAP_FUNCTION},
            ).one_or_none()
        assert function is not None, f"{BOOTSTRAP_FUNCTION}(text) does not exist"
        assert function.rolname == BOOTSTRAP_ROLE
        assert function.provolatile in ("s", "i"), "bootstrap must be STABLE or stricter"
        assert function.proconfig is not None
        assert "search_path=pg_catalog, public" in function.proconfig

    def test_bootstrap_role_is_bounded(self, engines: tuple[Engine, Engine]) -> None:
        owner, _ = engines
        with Session(owner) as session:
            role = session.execute(
                text(
                    "SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolbypassrls "
                    "FROM pg_roles WHERE rolname = :role"
                ),
                {"role": BOOTSTRAP_ROLE},
            ).one_or_none()
        assert role is not None, f"role {BOOTSTRAP_ROLE} does not exist"
        assert tuple(role) == (False, False, False, False, False)

    def test_app_role_does_not_inherit_the_bootstrap_role(
        self, engines: tuple[Engine, Engine]
    ) -> None:
        owner, _ = engines
        with Session(owner) as session:
            inherited = session.scalar(
                text(
                    "SELECT 1 FROM pg_auth_members m "
                    "JOIN pg_roles member ON member.oid = m.member "
                    "JOIN pg_roles granted ON granted.oid = m.roleid "
                    "WHERE member.rolname = :app AND granted.rolname = :bootstrap"
                ),
                {"app": APP_ROLE, "bootstrap": BOOTSTRAP_ROLE},
            )
        assert inherited is None

    def test_bootstrap_role_may_select_three_tables_and_nothing_else(
        self, engines: tuple[Engine, Engine]
    ) -> None:
        owner, _ = engines
        with Session(owner) as session:
            grants = session.execute(
                text(
                    "SELECT c.relname, acl.privilege_type FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "CROSS JOIN LATERAL aclexplode(COALESCE(c.relacl, "
                    "acldefault('r', c.relowner))) acl "
                    "JOIN pg_roles grantee ON grantee.oid = acl.grantee "
                    "WHERE n.nspname = 'public' AND grantee.rolname = :role"
                ),
                {"role": BOOTSTRAP_ROLE},
            ).all()
        assert {(row.relname, row.privilege_type) for row in grants} == {
            (table, "SELECT") for table in READABLE_TABLES
        }

    def test_bootstrap_policies_are_exactly_three_select_policies(
        self, engines: tuple[Engine, Engine]
    ) -> None:
        owner, _ = engines
        with Session(owner) as session:
            policies = session.execute(
                text(
                    "SELECT tablename, cmd, roles FROM pg_policies "
                    "WHERE schemaname = 'public' AND :role = ANY(roles)"
                ),
                {"role": BOOTSTRAP_ROLE},
            ).all()
        assert {row.tablename for row in policies} == set(READABLE_TABLES)
        assert all(row.cmd == "SELECT" for row in policies)
        assert all(list(row.roles) == [BOOTSTRAP_ROLE] for row in policies)

    def test_execute_is_limited_to_the_app_and_function_owner(
        self, engines: tuple[Engine, Engine]
    ) -> None:
        owner, _ = engines
        with Session(owner) as session:
            grantees = set(
                session.scalars(
                    text(
                        "SELECT COALESCE(grantee.rolname, 'PUBLIC') FROM pg_proc p "
                        "JOIN pg_namespace n ON n.oid = p.pronamespace "
                        "CROSS JOIN LATERAL aclexplode(COALESCE(p.proacl, "
                        "acldefault('f', p.proowner))) acl "
                        "LEFT JOIN pg_roles grantee ON grantee.oid = acl.grantee "
                        "WHERE n.nspname = 'public' AND p.proname = :function "
                        "AND acl.privilege_type = 'EXECUTE'"
                    ),
                    {"function": BOOTSTRAP_FUNCTION},
                ).all()
            )
        assert grantees == {APP_ROLE, BOOTSTRAP_ROLE}


class TestBootstrapReadBehaviour:
    def test_live_memberships_across_accounts_are_returned(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        _, app = engines
        rows = _contexts(app, seed.switcher)
        assert rows == [
            (
                seed.switcher,
                f"{seed.switcher}@example.test",
                seed.account_one,
                "Hausverwaltung Nord",
                "SOLO",
                "OWNER",
            ),
            (
                seed.switcher,
                f"{seed.switcher}@example.test",
                seed.account_two,
                "Immobilien Süd",
                "HAUSVERWALTUNG",
                "EMPLOYEE",
            ),
        ]

    def test_unmembered_person_is_distinct_from_unknown_subject(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        _, app = engines
        unmembered = _contexts(app, seed.unmembered)
        assert unmembered == [
            (seed.unmembered, f"{seed.unmembered}@example.test", None, None, None, None)
        ]
        assert _contexts(app, seed.unknown) == []

    def test_revoked_membership_is_not_a_context(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        _, app = engines
        assert _contexts(app, seed.colleague)[0][2:] == (
            seed.other_account,
            "Fremdkonto",
            "SOLO",
            "TAX_ADVISOR",
        )
        assert _contexts(app, seed.revoked) == [
            (seed.revoked, f"{seed.revoked}@example.test", None, None, None, None)
        ]

    def test_call_does_not_open_domain_rows_or_set_account_context(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        _, app = engines
        with Session(app) as session:
            session.execute(
                text(f"SELECT * FROM {BOOTSTRAP_FUNCTION}(:person_id)"),
                {"person_id": seed.switcher},
            ).all()
            domain_rows = session.scalar(text("SELECT count(*) FROM building"))
            context = session.scalar(text("SELECT current_setting('app.account_id', true)"))
        assert domain_rows == 0
        assert not context
