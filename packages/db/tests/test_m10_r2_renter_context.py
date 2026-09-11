"""M10-R2 RED database contract for tenancy-scoped renter sessions and RLS."""

import ast
import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import lokara_db
import pytest
from alembic import command
from alembic.config import Config
from lokara_db import (
    Account,
    Building,
    DbSettings,
    Membership,
    Person,
    Renter,
    Role,
    Tenancy,
    TenancyParty,
    Unit,
    create_db_engine,
    new_id,
)
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session

_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent
_MIGRATIONS = _DB_PACKAGE_DIR / "alembic" / "versions"
_BOOTSTRAP_TABLES = {"person", "membership", "account", "renter", "tenancy_party", "tenancy"}


@dataclass(frozen=True)
class _Ids:
    account: str
    owner_person: str
    owner_membership: str
    renter_person: str
    unlinked_person: str
    building: str
    unit: str
    tenancy: str
    other_tenancy: str
    renter: str
    other_renter: str


@pytest.fixture(scope="module")
def setup() -> Iterator[tuple[Engine, Engine, _Ids]]:
    settings = DbSettings()
    try:
        owner = create_db_engine(settings.direct_url)
        with owner.connect() as connection:
            connection.execute(
                text((_DB_PACKAGE_DIR / "scripts" / "init-app-role.sql").read_text())
            )
            connection.commit()
    except OperationalError as exc:
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")
    command.upgrade(Config(str(_DB_PACKAGE_DIR / "alembic.ini")), "head")
    app = create_db_engine(settings.database_url)

    ids = _Ids(*(new_id() for _ in range(11)))
    with Session(owner) as session, session.begin():
        session.add_all(
            [
                Account(id=ids.account, name="M10-R2 RLS Konto"),
                Person(id=ids.owner_person, email=f"{ids.owner_person}@example.test"),
                Person(id=ids.renter_person, email=f"{ids.renter_person}@example.test"),
                Person(id=ids.unlinked_person, email=f"{ids.unlinked_person}@example.test"),
                Membership(
                    id=ids.owner_membership,
                    person_id=ids.owner_person,
                    account_id=ids.account,
                    role=Role.OWNER,
                    accepted_at=datetime(2026, 9, 11, tzinfo=UTC),
                ),
                Building(
                    id=ids.building,
                    account_id=ids.account,
                    name="RLS Haus",
                    street="Grenzweg 1",
                    postal_code="10115",
                    city="Berlin",
                ),
                Renter(id=ids.renter, account_id=ids.account, legal_name="RLS Mieter"),
                Renter(
                    id=ids.other_renter,
                    account_id=ids.account,
                    legal_name="Andere Mietpartei",
                ),
            ]
        )
    with Session(owner) as session, session.begin():
        session.add(
            Unit(
                id=ids.unit,
                account_id=ids.account,
                building_id=ids.building,
                label="RLS Wohnung",
                area_sqm_x100=5_400,
            )
        )
    with Session(owner) as session, session.begin():
        session.add_all(
            [
                Tenancy(
                    id=ids.tenancy,
                    account_id=ids.account,
                    unit_id=ids.unit,
                    valid_from=date(2025, 1, 1),
                    valid_to=None,
                    base_rent_cents=80_000,
                ),
                Tenancy(
                    id=ids.other_tenancy,
                    account_id=ids.account,
                    unit_id=ids.unit,
                    valid_from=date(2023, 1, 1),
                    valid_to=date(2024, 12, 31),
                    base_rent_cents=70_000,
                ),
            ]
        )
    with Session(owner) as session, session.begin():
        session.add_all(
            [
                TenancyParty(
                    account_id=ids.account,
                    tenancy_id=ids.tenancy,
                    renter_id=ids.renter,
                ),
                TenancyParty(
                    account_id=ids.account,
                    tenancy_id=ids.other_tenancy,
                    renter_id=ids.other_renter,
                ),
            ]
        )

    raw = f"{ids.account}.m10-r2-{new_id()}"
    code_id = new_id()
    now = datetime.now(UTC)
    with owner.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO renter_activation_code "
                "(id, account_id, renter_id, tenancy_id, code_hash, expires_at, "
                "issued_by_membership_id, issued_at) VALUES "
                "(:id, :account, :renter, :tenancy, :digest, :expires, :membership, :now)"
            ),
            {
                "id": code_id,
                "account": ids.account,
                "renter": ids.renter,
                "tenancy": ids.tenancy,
                "digest": sha256(raw.encode()).hexdigest(),
                "expires": now + timedelta(hours=1),
                "membership": ids.owner_membership,
                "now": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO renter_activation_redemption "
                "(id, account_id, activation_code_id, renter_id, tenancy_id, person_id, "
                "redeemed_at) VALUES "
                "(:id, :account, :code, :renter, :tenancy, :person, :now)"
            ),
            {
                "id": new_id(),
                "account": ids.account,
                "code": code_id,
                "renter": ids.renter,
                "tenancy": ids.tenancy,
                "person": ids.renter_person,
                "now": now,
            },
        )
        connection.execute(
            text("UPDATE renter SET person_id = :person WHERE id = :renter"),
            {"person": ids.renter_person, "renter": ids.renter},
        )

    try:
        yield owner, app, ids
    finally:
        app.dispose()
        owner.dispose()


def _set_renter_context(connection: Connection, ids: _Ids) -> None:
    connection.execute(
        text("SELECT set_config('app.account_id', :account, true)"),
        {"account": ids.account},
    )
    connection.execute(
        text("SELECT set_config('app.tenancy_id', :tenancy, true)"),
        {"tenancy": ids.tenancy},
    )


def test_migration_0042_follows_0041() -> None:
    migrations = sorted(_MIGRATIONS.glob("0042_*.py"))
    assert len(migrations) == 1, "M10-R2 migration 0042 is not implemented"
    tree = ast.parse(migrations[0].read_text())
    assignments = {
        node.targets[0].id: node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Constant)
    }
    assert assignments["revision"] == "0042"
    assert assignments["down_revision"] == "0041"


def test_m10_ctx_f07_single_bootstrap_function_has_exact_least_privilege_and_typed_rows(
    setup: tuple[Engine, Engine, _Ids],
) -> None:
    owner, app, ids = setup
    with owner.connect() as connection:
        definers = connection.execute(
            text(
                "SELECT p.proname, oidvectortypes(p.proargtypes) FROM pg_proc p "
                "JOIN pg_namespace n ON n.oid = p.pronamespace "
                "WHERE n.nspname = 'public' AND p.prosecdef"
            )
        ).all()
        grants = {
            (row.table_name, row.privilege_type)
            for row in connection.execute(
                text(
                    "SELECT table_name, privilege_type "
                    "FROM information_schema.role_table_grants "
                    "WHERE table_schema = 'public' AND grantee = 'lokara_bootstrap'"
                )
            )
        }
    assert [(row.proname, row.oidvectortypes) for row in definers] == [
        ("app_bootstrap_contexts", "text")
    ]
    assert grants == {(table, "SELECT") for table in _BOOTSTRAP_TABLES}

    with app.connect() as connection:
        rows = (
            connection.execute(
                text("SELECT * FROM app_bootstrap_contexts(:person)"),
                {"person": ids.renter_person},
            )
            .mappings()
            .all()
        )
    assert [row["context_kind"] for row in rows] == ["RENTER_TENANCY"]
    assert rows[0]["tenancy_id"] == ids.tenancy
    assert rows[0]["account_id"] == ids.account
    assert rows[0]["membership_role"] is None
    assert rows[0]["account_name"] is None


def test_m10_ctx_f03_and_f05_rls_reads_exactly_the_context_tenancy_unit_and_building(
    setup: tuple[Engine, Engine, _Ids],
) -> None:
    _, app, ids = setup
    # Rollback-only adversarial probe: there is no endpoint or query-level tenancy filter here.
    with app.connect() as connection:
        transaction = connection.begin()
        try:
            _set_renter_context(connection, ids)
            assert connection.execute(text("SELECT id FROM tenancy")).scalars().all() == [
                ids.tenancy
            ]
            assert connection.execute(text("SELECT id FROM unit")).scalars().all() == [ids.unit]
            assert connection.execute(text("SELECT id FROM building")).scalars().all() == [
                ids.building
            ]
            for hidden in ("person", "renter", "tenancy_party", "statement", "meter"):
                assert connection.scalar(text(f"SELECT count(*) FROM {hidden}")) == 0
        finally:
            transaction.rollback()


def test_m10_ctx_f05_renter_session_derives_and_sets_both_local_contexts(
    setup: tuple[Engine, Engine, _Ids],
) -> None:
    _, app, ids = setup
    helper = getattr(lokara_db, "renter_scoped_session", None)
    assert callable(helper), "renter_scoped_session is not implemented"
    # No account id is accepted here: the helper must derive it from the exact witness.
    with helper(app, ids.renter_person, ids.tenancy) as session:
        assert session.scalar(text("SELECT current_setting('app.account_id', true)")) == ids.account
        assert session.scalar(text("SELECT current_setting('app.tenancy_id', true)")) == ids.tenancy


def test_m10_ctx_f05_catalog_allows_renter_select_on_exactly_three_tables(
    setup: tuple[Engine, Engine, _Ids],
) -> None:
    owner, _, _ = setup
    with owner.connect() as connection:
        policies = connection.execute(
            text(
                "SELECT tablename, policyname, cmd, roles::text, qual FROM pg_policies "
                "WHERE schemaname = 'public' AND qual LIKE '%app.tenancy_id%' "
                "AND qual NOT LIKE '%IS NULL%'"
            )
        ).all()
    assert {
        (policy.tablename, policy.policyname, policy.cmd, policy.roles) for policy in policies
    } == {
        ("tenancy", "tenancy_renter_select", "SELECT", "{lokara_app}"),
        ("unit", "unit_renter_select", "SELECT", "{lokara_app}"),
        ("building", "building_renter_select", "SELECT", "{lokara_app}"),
    }
    assert all("app.account_id" in str(policy.qual) for policy in policies)


def test_m10_ctx_f06_every_renter_context_write_is_refused(
    setup: tuple[Engine, Engine, _Ids],
) -> None:
    _, app, ids = setup
    # The attempted write is evidence only inside this transaction and is always rolled back.
    with app.connect() as connection:
        transaction = connection.begin()
        try:
            _set_renter_context(connection, ids)
            with pytest.raises(DBAPIError):
                connection.execute(
                    text(
                        "INSERT INTO building "
                        "(id, account_id, name, street, postal_code, city) "
                        "VALUES (:id, :account, 'Verboten', 'Sperrweg 1', '10115', 'Berlin')"
                    ),
                    {"id": new_id(), "account": ids.account},
                )
        finally:
            transaction.rollback()


def test_m10_ctx_f06_all_existing_account_policies_stop_at_tenancy_context(
    setup: tuple[Engine, Engine, _Ids],
) -> None:
    owner, _, _ = setup
    with owner.connect() as connection:
        policies = connection.execute(
            text(
                "SELECT tablename, policyname, cmd, qual, with_check FROM pg_policies "
                "WHERE schemaname = 'public' AND 'public' = ANY(roles) "
                "AND policyname LIKE '%\\_isolation' ESCAPE '\\'"
            )
        ).all()
    assert policies
    for policy in policies:
        expressions = [
            str(expression).lower()
            for expression in (policy.qual, policy.with_check)
            if expression is not None
        ]
        assert expressions, f"{policy.tablename}.{policy.policyname} has no write expression"
        has_guard = all(
            "app.tenancy_id" in expression and "is null" in expression for expression in expressions
        )
        assert has_guard, (
            f"{policy.tablename}.{policy.policyname} still grants account access while "
            "app.tenancy_id is set"
        )
