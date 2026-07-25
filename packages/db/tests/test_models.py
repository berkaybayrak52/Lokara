"""Structural tests on the mapped metadata — no database required.

These pin the docs/02 invariants at the schema level: every domain table
carries account_id, the uniqueness rules exist, and the RLS table list in
ACCOUNT_SCOPED_TABLES can never silently drift from the models.
"""

from lokara_db import ACCOUNT_SCOPED_TABLES, Base, DbSettings, sqlalchemy_url
from sqlalchemy import UniqueConstraint
from sqlalchemy.sql.schema import Table

EXPECTED_TABLES = {
    "person",
    "account",
    "membership",
    "building_assignment",
    "landlord",
    "renter",
    "building",
    "unit",
    "tenancy",
    "tenancy_party",
    "self_use_period",
    "statement",
    "cost_entry",
    "allocation_key_assignment",
}


def _table(name: str) -> Table:
    return Base.metadata.tables[name]


def _unique_column_sets(table: Table) -> set[frozenset[str]]:
    return {
        frozenset(col.name for col in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


class TestSchemaShape:
    def test_exactly_the_docs02_tables_exist(self) -> None:
        assert set(Base.metadata.tables) == EXPECTED_TABLES

    def test_every_account_scoped_table_carries_account_id(self) -> None:
        for name in ACCOUNT_SCOPED_TABLES:
            table = _table(name)
            assert "account_id" in table.columns, f"{name} is missing account_id"
            assert not table.columns["account_id"].nullable, f"{name}.account_id must be NOT NULL"

    def test_scoped_list_covers_all_domain_tables(self) -> None:
        # person = global identity; account = scoped by its own id;
        # building_assignment = scoped via its membership. Everything else MUST
        # be in ACCOUNT_SCOPED_TABLES — a new domain table cannot dodge RLS.
        exempt = {"person", "account", "building_assignment"}
        assert set(ACCOUNT_SCOPED_TABLES) == EXPECTED_TABLES - exempt

    def test_membership_is_unique_per_person_and_account(self) -> None:
        assert frozenset({"person_id", "account_id"}) in _unique_column_sets(_table("membership"))

    def test_tenancy_party_is_unique_per_tenancy_and_renter(self) -> None:
        assert frozenset({"tenancy_id", "renter_id"}) in _unique_column_sets(
            _table("tenancy_party")
        )

    def test_statement_version_chain_is_unique(self) -> None:
        assert frozenset({"building_id", "period_start", "period_end", "version"}) in (
            _unique_column_sets(_table("statement"))
        )

    def test_money_and_area_columns_are_integers(self) -> None:
        for table_name, column in (
            ("tenancy", "base_rent_cents"),
            ("tenancy", "advance_payment_cents"),
            ("statement", "total_cents"),
            ("unit", "area_sqm_x100"),
            ("self_use_period", "sqm_x100"),
            ("cost_entry", "amount_cents"),
        ):
            assert _table(table_name).columns[column].type.python_type is int

    def test_validity_columns_are_day_granular_dates(self) -> None:
        from datetime import date

        for table_name in ("tenancy", "self_use_period"):
            table = _table(table_name)
            assert table.columns["valid_from"].type.python_type is date
            assert table.columns["valid_to"].type.python_type is date
            assert table.columns["valid_to"].nullable  # NULL = open-ended (half-open period)
        cost = _table("cost_entry")
        assert cost.columns["period_from"].type.python_type is date
        assert cost.columns["period_to"].type.python_type is date

    def test_allocation_key_never_lives_on_the_cost_row(self) -> None:
        """docs/03: keys come from a per-period assignment, so re-keying a cost
        can never destroy entered data. A `key` column on cost_entry would be
        exactly that bug."""
        assert "key" not in _table("cost_entry").columns
        assert "key" in _table("allocation_key_assignment").columns


class TestSettings:
    def test_libpq_url_is_normalized_to_psycopg(self) -> None:
        assert sqlalchemy_url("postgresql://u:p@h:5432/db") == "postgresql+psycopg://u:p@h:5432/db"
        assert sqlalchemy_url("postgresql+psycopg://u@h/db") == "postgresql+psycopg://u@h/db"

    def test_runtime_and_migration_roles_differ(self) -> None:
        # DATABASE_URL must be the non-owner app role — owners bypass RLS.
        settings = DbSettings()
        assert "lokara_app" in settings.database_sqlalchemy_url
        assert "lokara_app" not in settings.direct_sqlalchemy_url
