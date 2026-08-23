"""Executable contract for the confirmed-Messdienstleister migration.

Same harness and the same reason as `test_migration_0007.py`: most of what can
go wrong in a migration is *sequence*, and a wrong sequence still runs green
against an empty database. RLS statements against a table that does not exist
yet, a column typed by an enum Postgres has never heard of, a child table whose
parent is created after it — every one of those is a green `upgrade()` here and
a failed deployment on a real database.

Two invariants beyond 0007's:

* **Both scoped foreign keys carry `account_id`.** `mdl_statement` and
  `mdl_statement_position` are tenant tables, and Postgres checks referential
  integrity with RLS bypassed — so only the composite pair makes a
  cross-account edge unrepresentable (`CLAUDE.md` § 3.3, and the rule
  `scripts/check_fk_isolation.py` enforces).
* **The versioning UNIQUE is append-only.** `(building_id, period_from,
  period_to, version)`, *including* `version`, is what lets a correction insert
  `version + 1` instead of UPDATEing the confirmed row. Drop `version` from that
  tuple and the only way to correct a statement becomes an overwrite, which is
  exactly what `CLAUDE.md` § 3.2 forbids for a legally relevant record.

The enum is asserted differently from 0007 on purpose. 0007 calls
`.create(bind, checkfirst=True)` explicitly because it adds a column to an
existing table; 0008 uses the type inside `create_table`, where SQLAlchemy emits
the `CREATE TYPE` itself as part of the table's DDL. That is only a correct
migration if the emitted order is type-then-table, so this file renders the
recorded `create_table` and asserts against the SQL, rather than trusting the
mechanism.
"""

from collections.abc import Callable
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any

import sqlalchemy as sa


class RecordingOperations:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def __getattr__(self, name: str) -> Any:
        def record(*args: Any, **kwargs: Any) -> None:
            self.calls.append((name, args, kwargs))

        return record


class RecordingEnum(sa.Enum):
    """A stand-in for `_MDL_BRANCH` that records its own CREATE/DROP TYPE.

    `downgrade()` calls `_MDL_BRANCH.drop(op.get_bind(), checkfirst=True)`, and
    under `RecordingOperations` every attribute is a recorder returning None —
    so the bind is None and the real `sa.Enum.drop` would fail on it. Recording
    into the same call list keeps the type's lifecycle visible in sequence with
    the `op.*` calls.

    It stays a real `sa.Enum` subclass because the migration hands it to
    `sa.Column(...)` as a column type, which would reject a non-type double
    before any ordering could be observed.
    """

    def __init__(
        self,
        calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]],
        original: sa.Enum,
    ) -> None:
        super().__init__(*original.enums, name=original.name)
        self.calls = calls

    def create(self, bind: Any = None, checkfirst: bool = False) -> None:
        self.calls.append(("enum_create", (self.name,), {"checkfirst": checkfirst}))

    def drop(self, bind: Any = None, checkfirst: bool = False) -> None:
        self.calls.append(("enum_drop", (self.name,), {"checkfirst": checkfirst}))


def _load() -> ModuleType:
    path = Path(__file__).parents[1] / "alembic/versions/0008_confirmed_mdl_statements.py"
    spec = spec_from_file_location("migration_0008", path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def _recorded(
    monkeypatch: Any, *, record_enum: bool = False
) -> tuple[ModuleType, RecordingOperations]:
    """Run `upgrade()` against a recorder.

    `record_enum` swaps in `RecordingEnum`, which suppresses the real
    `CREATE TYPE` — useful for the lifecycle assertions, useless for the DDL
    ordering one, which needs the genuine type to render itself.
    """
    migration = _load()
    operations = RecordingOperations()
    monkeypatch.setattr(migration, "op", operations)
    if record_enum:
        monkeypatch.setattr(
            migration, "_MDL_BRANCH", RecordingEnum(operations.calls, migration._MDL_BRANCH)
        )
    migration.upgrade()
    return migration, operations


def _index_of(operations: RecordingOperations, name: str, first_arg: Any) -> int:
    return next(
        index
        for index, (call_name, args, _) in enumerate(operations.calls)
        if call_name == name and args and args[0] == first_arg
    )


def _execute_index(operations: RecordingOperations, needle: str) -> int:
    return next(
        index
        for index, (call_name, args, _) in enumerate(operations.calls)
        if call_name == "execute" and needle in args[0]
    )


# The parents the two new tables point at. Stubbed rather than imported from
# `models.py`: this file is a contract for the *migration*, and resolving its
# foreign keys against the ORM would let a model change paper over a migration
# that no longer matches it.
_STUB_PARENTS: dict[str, Callable[[sa.MetaData], sa.Table]] = {
    "account": lambda md: sa.Table("account", md, sa.Column("id", sa.String(), primary_key=True)),
    "building": lambda md: sa.Table(
        "building",
        md,
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.UniqueConstraint("id", "account_id"),
    ),
    "tenancy": lambda md: sa.Table(
        "tenancy",
        md,
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.UniqueConstraint("id", "account_id"),
    ),
    "mdl_statement": lambda md: sa.Table(
        "mdl_statement",
        md,
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.UniqueConstraint("id", "account_id"),
    ),
}


def _table(operations: RecordingOperations, name: str) -> sa.Table:
    """The recorded `create_table` call, rebuilt as the Table it describes."""
    _, args, kwargs = operations.calls[_index_of(operations, "create_table", name)]
    metadata = sa.MetaData()
    for parent, build in _STUB_PARENTS.items():
        if parent != name:
            build(metadata)
    return sa.Table(str(args[0]), metadata, *args[1:], **kwargs)


def _rendered_ddl(operations: RecordingOperations, name: str) -> list[str]:
    table = _table(operations, name)
    statements: list[str] = []

    def dump(sql: Any, *args: Any, **kwargs: Any) -> None:
        statements.append(str(sql.compile(dialect=engine.dialect)).strip())

    engine = sa.create_mock_engine("postgresql://", dump)
    table.create(engine, checkfirst=False)
    return statements


def _fk(table: sa.Table, name: str) -> sa.ForeignKeyConstraint:
    (constraint,) = [c for c in table.foreign_key_constraints if c.name == name]
    return constraint


def _unique(table: sa.Table, name: str) -> sa.UniqueConstraint:
    (constraint,) = [
        c for c in table.constraints if isinstance(c, sa.UniqueConstraint) and c.name == name
    ]
    return constraint


def test_it_follows_0007(monkeypatch: Any) -> None:
    migration, _ = _recorded(monkeypatch)

    assert migration.revision == "0008"
    assert migration.down_revision == "0007"


def test_the_building_link_is_composite(monkeypatch: Any) -> None:
    """A bare `building_id -> building.id` FK would be the cross-account hole.

    An `mdl_statement` row that stamps its own `account_id` correctly passes the
    RLS `WITH CHECK` and could still hang a confirmed third-party statement off
    another account's building — and this is money that goes onto a real Mieter's
    Abrechnung. Only the pair
    `(building_id, account_id) -> (building.id, building.account_id)` makes that
    edge unrepresentable, which is what `scripts/check_fk_isolation.py` demands.
    """
    _, operations = _recorded(monkeypatch)

    building_fk = _fk(_table(operations, "mdl_statement"), "mdl_statement_building_id_fkey")

    assert building_fk.column_keys == ["building_id", "account_id"]
    assert [element.target_fullname for element in building_fk.elements] == [
        "building.id",
        "building.account_id",
    ]
    # SIMPLE, not FULL: account_id is NOT NULL, and MATCH FULL would demand
    # all-or-nothing across the pair (see `_scoped_fk` in models.py).
    assert building_fk.match == "SIMPLE"


def test_both_position_parents_are_composite(monkeypatch: Any) -> None:
    """A position carries one renter's amount, so both of its parents matter.

    `tenancy_id` names *whose* amount it is and `mdl_statement_id` names which
    confirmed document it came from. A single-column FK on either one lets a row
    that satisfies `WITH CHECK` still reach across accounts — a foreign renter's
    figure on this account's statement, or this account's figure attached to a
    foreign document.
    """
    _, operations = _recorded(monkeypatch)

    positions = _table(operations, "mdl_statement_position")
    statement_fk = _fk(positions, "mdl_statement_position_mdl_statement_id_fkey")
    tenancy_fk = _fk(positions, "mdl_statement_position_tenancy_id_fkey")

    assert statement_fk.column_keys == ["mdl_statement_id", "account_id"]
    assert [element.target_fullname for element in statement_fk.elements] == [
        "mdl_statement.id",
        "mdl_statement.account_id",
    ]
    assert statement_fk.match == "SIMPLE"

    assert tenancy_fk.column_keys == ["tenancy_id", "account_id"]
    assert [element.target_fullname for element in tenancy_fk.elements] == [
        "tenancy.id",
        "tenancy.account_id",
    ]
    assert tenancy_fk.match == "SIMPLE"


def test_the_parent_is_unique_on_the_pair_the_child_references(monkeypatch: Any) -> None:
    """`uq_mdl_statement_id_account` is load-bearing, not decoration.

    Postgres refuses a foreign key whose referenced columns carry no unique
    index. Without this constraint the composite FK asserted above cannot be
    created at all, and the only migration that still applies is one with a
    single-column — i.e. cross-account-permissive — link.
    """
    _, operations = _recorded(monkeypatch)

    pair = _unique(_table(operations, "mdl_statement"), "uq_mdl_statement_id_account")

    assert list(pair.columns.keys()) == ["id", "account_id"]


def test_a_correction_can_only_be_a_new_version(monkeypatch: Any) -> None:
    """`version` inside the UNIQUE tuple is what makes the table append-only.

    `CLAUDE.md` § 3.2: a legally relevant record is never overwritten. With
    `version` in the key, a corrected Messdienstleister document inserts
    `version + 1` for the same building period and the superseded confirmation
    stays readable. Without it, the same period could hold only one row and a
    correction would have to be an UPDATE — destroying the evidence that the
    earlier figures were once confirmed and sent.
    """
    _, operations = _recorded(monkeypatch)

    statements = _table(operations, "mdl_statement")
    versioning = _unique(statements, "uq_mdl_statement_building_period_version")
    positions = _unique(
        _table(operations, "mdl_statement_position"), "uq_mdl_position_statement_tenancy"
    )

    assert list(versioning.columns.keys()) == [
        "building_id",
        "period_from",
        "period_to",
        "version",
    ]
    # And one amount per renter per confirmed document, so a double-booked
    # position cannot inflate the control sum that `01b-F29` checks.
    assert list(positions.columns.keys()) == ["mdl_statement_id", "tenancy_id"]


def test_rls_is_enabled_forced_and_policied_after_each_table_exists(monkeypatch: Any) -> None:
    """ENABLE alone lets the table owner bypass every policy, and all three
    statements are `ALTER`/`CREATE POLICY` against a table that has to exist
    already — so the order is not cosmetic. Asserted per table because the loop
    in the migration runs after both `create_table` calls and a future edit
    could easily move one of them."""
    _, operations = _recorded(monkeypatch)

    for table in ("mdl_statement", "mdl_statement_position"):
        created = _index_of(operations, "create_table", table)
        enable = _execute_index(operations, f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        force = _execute_index(operations, f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        policy = _execute_index(operations, f"CREATE POLICY {table}_isolation ON {table}")

        assert created < enable < policy, table
        assert created < force < policy, table


def test_the_policy_scopes_reads_and_writes_by_account(monkeypatch: Any) -> None:
    """USING without WITH CHECK reads correctly and lets a foreign row be
    *written* — the half of isolation that only an INSERT test would ever
    reveal."""
    _, operations = _recorded(monkeypatch)

    for table in ("mdl_statement", "mdl_statement_position"):
        _, args, _ = operations.calls[
            _execute_index(operations, f"CREATE POLICY {table}_isolation ON {table}")
        ]
        policy = " ".join(str(args[0]).split())

        assert "USING (account_id = current_setting('app.account_id', true))" in policy
        assert "WITH CHECK (account_id = current_setting('app.account_id', true))" in policy


def test_the_enum_type_is_created_before_the_column_that_uses_it(monkeypatch: Any) -> None:
    """`branch mdl_branch` against an unmade type fails on Postgres.

    Unlike 0007, this migration never calls `_MDL_BRANCH.create(...)`: the type
    is used inside `create_table`, where SQLAlchemy emits its `CREATE TYPE` as
    part of the table's own DDL. That is correct only because the emitted order
    is type-then-table, so the assertion is made against the rendered SQL rather
    than against the mechanism.
    """
    _, operations = _recorded(monkeypatch)

    ddl = _rendered_ddl(operations, "mdl_statement")
    create_type = next(i for i, sql in enumerate(ddl) if sql.startswith("CREATE TYPE mdl_branch"))
    create_table = next(
        i for i, sql in enumerate(ddl) if sql.startswith("CREATE TABLE mdl_statement")
    )

    assert create_type < create_table
    assert "AS ENUM ('NET', 'GROSS')" in ddl[create_type]
    # The two branches are different arithmetic, not a display flag (docs/03 H7).
    assert "branch mdl_branch NOT NULL" in ddl[create_table]


def test_upgrade_leaves_the_type_to_the_table_and_downgrade_takes_it_back(
    monkeypatch: Any,
) -> None:
    """The asymmetry between the two directions is deliberate, and it is a trap.

    `upgrade()` never touches `_MDL_BRANCH`: the type rides in on the table's
    own DDL (asserted above). `downgrade()` must touch it, because `drop_table`
    takes a *name* — there is no Table object carrying the type, so nothing
    would drop it. An orphaned `mdl_branch` then makes the next `upgrade()` fail
    on `CREATE TYPE`, and a down/up cycle is exactly what a developer does after
    an aborted deployment.

    Unlike 0007, no `checkfirst=True` is asserted on the way up: Alembic
    dispatches `before_create` with `checkfirst=False`, so the `CREATE TYPE` is
    unconditional. Claiming idempotency here would be asserting something the
    migration does not do.
    """
    migration, operations = _recorded(monkeypatch, record_enum=True)

    assert not [call for call in operations.calls if call[0] == "enum_create"]

    migration.downgrade()
    dropped = _index_of(operations, "enum_drop", "mdl_branch")

    # checkfirst on the way down: a partially applied 0008 may have no type.
    assert operations.calls[dropped][2] == {"checkfirst": True}


def test_downgrade_drops_the_child_then_the_parent_then_the_type(monkeypatch: Any) -> None:
    """`drop_table` by name takes no type with it, so the enum needs its own
    drop — and the position table has to go before the statement it references."""
    migration = _load()
    operations = RecordingOperations()
    monkeypatch.setattr(migration, "op", operations)
    monkeypatch.setattr(
        migration, "_MDL_BRANCH", RecordingEnum(operations.calls, migration._MDL_BRANCH)
    )
    migration.downgrade()

    positions = _index_of(operations, "drop_table", "mdl_statement_position")
    statements = _index_of(operations, "drop_table", "mdl_statement")
    dropped_type = _index_of(operations, "enum_drop", "mdl_branch")

    assert positions < statements < dropped_type
    assert operations.calls[dropped_type][2] == {"checkfirst": True}
