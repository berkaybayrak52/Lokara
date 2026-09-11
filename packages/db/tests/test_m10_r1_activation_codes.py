"""M10-R1 database contract for renter activation codes.

These tests intentionally precede migration 0041 and its mapped models.  They use
catalogue queries so the red state says "the M10 tables/migration are absent"
instead of failing during Python import.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from lokara_db import DbSettings, create_db_engine
from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError

_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent
_MIGRATION = _DB_PACKAGE_DIR / "alembic" / "versions" / "0041_renter_activation_codes.py"
_TABLES = {
    "renter_activation_code",
    "renter_activation_redemption",
    "renter_activation_attempt",
}


@pytest.fixture(scope="module")
def owner_engine() -> Iterator[Engine]:
    settings = DbSettings()
    try:
        engine = create_db_engine(settings.direct_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError as exc:
        if __import__("os").environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")
    command.upgrade(Config(str(_DB_PACKAGE_DIR / "alembic.ini")), "head")
    yield engine
    engine.dispose()


def test_migration_0041_follows_the_consolidated_0040_head() -> None:
    assert _MIGRATION.exists(), "M10-R1 migration 0041 is not implemented"
    source = _MIGRATION.read_text(encoding="utf-8")
    assert 'revision = "0041"' in source
    assert 'down_revision = "0040"' in source


def test_activation_tables_are_account_scoped_and_forced_rls(owner_engine: Engine) -> None:
    with owner_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity, "
                "EXISTS (SELECT 1 FROM pg_policy p "
                "WHERE p.polrelid = c.oid AND p.polwithcheck IS NOT NULL) "
                "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'public' AND c.relname = ANY(:tables)"
            ),
            {"tables": sorted(_TABLES)},
        ).all()
    found = {name: (enabled, forced, with_check) for name, enabled, forced, with_check in rows}
    assert set(found) == _TABLES, f"M10-R1 tables missing: {_TABLES - set(found)}"
    assert all(value == (True, True, True) for value in found.values())


def test_activation_schema_contains_only_hashed_secret_and_complete_evidence(
    owner_engine: Engine,
) -> None:
    with owner_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = ANY(:tables)"
            ),
            {"tables": sorted(_TABLES)},
        ).all()
    columns: dict[str, set[str]] = {table: set() for table in _TABLES}
    for table, column in rows:
        columns[table].add(column)

    assert {
        "id",
        "account_id",
        "renter_id",
        "tenancy_id",
        "code_hash",
        "expires_at",
        "issued_by_membership_id",
        "issued_at",
    } <= columns["renter_activation_code"]
    assert not ({"code", "raw_code", "activation_code"} & columns["renter_activation_code"])
    assert {
        "id",
        "account_id",
        "activation_code_id",
        "renter_id",
        "tenancy_id",
        "person_id",
        "redeemed_at",
    } <= columns["renter_activation_redemption"]
    assert {
        "id",
        "account_id",
        "activation_code_id",
        "requested_tenancy_id",
        "subject_id",
        "outcome",
        "code_digest",
        "attempted_at",
    } <= columns["renter_activation_attempt"]


def test_every_account_scoped_activation_edge_is_composite(owner_engine: Engine) -> None:
    """Each scoped parent link carries account_id; person remains global by design."""
    with owner_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT child.relname, parent.relname, "
                "array_agg(child_col.attname ORDER BY key_col.ord), "
                "array_agg(parent_col.attname ORDER BY key_col.ord) "
                "FROM pg_constraint con "
                "JOIN pg_class child ON child.oid = con.conrelid "
                "JOIN pg_class parent ON parent.oid = con.confrelid "
                "JOIN LATERAL unnest(con.conkey, con.confkey) WITH ORDINALITY "
                "AS key_col(child_num, parent_num, ord) ON true "
                "JOIN pg_attribute child_col ON child_col.attrelid = child.oid "
                "AND child_col.attnum = key_col.child_num "
                "JOIN pg_attribute parent_col ON parent_col.attrelid = parent.oid "
                "AND parent_col.attnum = key_col.parent_num "
                "WHERE con.contype = 'f' AND child.relname = ANY(:tables) "
                "GROUP BY child.relname, parent.relname"
            ),
            {"tables": sorted(_TABLES)},
        ).all()

    scoped_parents = {
        "renter",
        "tenancy",
        "tenancy_party",
        "membership",
        "renter_activation_code",
    }
    seen: set[tuple[str, str]] = set()
    for child, parent, child_columns, parent_columns in rows:
        if parent not in scoped_parents:
            continue
        seen.add((child, parent))
        assert "account_id" in child_columns
        assert "account_id" in parent_columns

    assert {
        ("renter_activation_code", "renter"),
        ("renter_activation_code", "tenancy"),
        ("renter_activation_code", "tenancy_party"),
        ("renter_activation_code", "membership"),
        ("renter_activation_redemption", "renter_activation_code"),
        ("renter_activation_redemption", "renter"),
        ("renter_activation_redemption", "tenancy"),
        ("renter_activation_attempt", "renter_activation_code"),
    } <= seen


def test_attempt_code_fk_is_optional_composite_and_requested_tenancy_is_opaque(
    owner_engine: Engine,
) -> None:
    with owner_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT parent.relname, "
                "array_agg(child_col.attname ORDER BY key_col.ord), "
                "array_agg(parent_col.attname ORDER BY key_col.ord) "
                "FROM pg_constraint con "
                "JOIN pg_class child ON child.oid = con.conrelid "
                "JOIN pg_class parent ON parent.oid = con.confrelid "
                "JOIN LATERAL unnest(con.conkey, con.confkey) WITH ORDINALITY "
                "AS key_col(child_num, parent_num, ord) ON true "
                "JOIN pg_attribute child_col ON child_col.attrelid = child.oid "
                "AND child_col.attnum = key_col.child_num "
                "JOIN pg_attribute parent_col ON parent_col.attrelid = parent.oid "
                "AND parent_col.attnum = key_col.parent_num "
                "WHERE con.contype = 'f' AND child.relname = 'renter_activation_attempt' "
                "GROUP BY con.oid, parent.relname"
            )
        ).all()
        nullable = connection.scalar(
            text(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'renter_activation_attempt' "
                "AND column_name = 'activation_code_id'"
            )
        )
    assert (
        "renter_activation_code",
        ["activation_code_id", "account_id"],
        ["id", "account_id"],
    ) in rows
    assert nullable == "YES"
    assert all(
        not (parent == "tenancy" and "requested_tenancy_id" in child_columns)
        for parent, child_columns, _parent_columns in rows
    )


def test_redemption_person_id_references_the_global_person(owner_engine: Engine) -> None:
    with owner_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT array_agg(child_col.attname ORDER BY key_col.ord), "
                "array_agg(parent_col.attname ORDER BY key_col.ord) "
                "FROM pg_constraint con "
                "JOIN pg_class child ON child.oid = con.conrelid "
                "JOIN pg_class parent ON parent.oid = con.confrelid "
                "JOIN LATERAL unnest(con.conkey, con.confkey) WITH ORDINALITY "
                "AS key_col(child_num, parent_num, ord) ON true "
                "JOIN pg_attribute child_col ON child_col.attrelid = child.oid "
                "AND child_col.attnum = key_col.child_num "
                "JOIN pg_attribute parent_col ON parent_col.attrelid = parent.oid "
                "AND parent_col.attnum = key_col.parent_num "
                "WHERE con.contype = 'f' "
                "AND child.relname = 'renter_activation_redemption' "
                "AND parent.relname = 'person' GROUP BY con.oid"
            )
        ).all()
    assert (["person_id"], ["id"]) in rows


def test_one_database_spend_row_per_activation_code(owner_engine: Engine) -> None:
    with owner_engine.connect() as connection:
        unique_sets = (
            connection.execute(
                text(
                    "SELECT array_agg(a.attname ORDER BY k.ord) "
                    "FROM pg_constraint c "
                    "JOIN LATERAL unnest(c.conkey) WITH ORDINALITY k(attnum, ord) ON true "
                    "JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum "
                    "WHERE c.conrelid = 'renter_activation_redemption'::regclass "
                    "AND c.contype IN ('u', 'p') GROUP BY c.oid"
                )
            )
            .scalars()
            .all()
        )
    assert any(columns == ["activation_code_id"] for columns in unique_sets), (
        "single use must be a database uniqueness invariant"
    )


def test_code_hash_is_unique_inside_its_rls_account(owner_engine: Engine) -> None:
    with owner_engine.connect() as connection:
        unique_sets = (
            connection.execute(
                text(
                    "SELECT array_agg(a.attname ORDER BY k.ord) "
                    "FROM pg_constraint c "
                    "JOIN LATERAL unnest(c.conkey) WITH ORDINALITY k(attnum, ord) ON true "
                    "JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum "
                    "WHERE c.conrelid = 'renter_activation_code'::regclass "
                    "AND c.contype IN ('u', 'p') GROUP BY c.oid"
                )
            )
            .scalars()
            .all()
        )
    assert any(set(columns) == {"account_id", "code_hash"} for columns in unique_sets)
