"""Executable contract for the Personenschlüssel / Fiktivbelegung migration.

Ordering is the point here. Three of the four invariants below are statements
about *sequence*, and every one of them is a migration that runs green against an
empty database and fails against a real one: RLS applied to a table that does not
exist yet, a column typed by an enum Postgres has never heard of, a CHECK over
columns added afterwards. The composite foreign key is the fourth, and it is the
cross-account hole `scripts/check_fk_isolation.py` exists to refuse.
"""

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
    """A stand-in for `_FIKTIVBELEGUNG_MODE` that records its own `CREATE TYPE`.

    The migration calls `_FIKTIVBELEGUNG_MODE.create(op.get_bind(), ...)`, and
    under `RecordingOperations` every attribute is a recorder that returns None —
    so `op.get_bind()` is None and the real `sa.Enum.create` would fail on it.
    Recording into the *same* call list instead keeps the enum's creation visible
    in sequence with the `op.*` calls, which is the only way to assert that the
    type exists before the column that is typed by it.

    It stays a real `sa.Enum` subclass because the migration hands it to
    `sa.Column(...)` as the column type, and a non-type double would be rejected
    there before the ordering could ever be observed.
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
    path = Path(__file__).parents[1] / "alembic/versions/0007_person_counts_and_fiktivbelegung.py"
    spec = spec_from_file_location("migration_0007", path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def _recorded(monkeypatch: Any) -> tuple[ModuleType, RecordingOperations]:
    migration = _load()
    operations = RecordingOperations()
    monkeypatch.setattr(migration, "op", operations)
    monkeypatch.setattr(
        migration,
        "_FIKTIVBELEGUNG_MODE",
        RecordingEnum(operations.calls, migration._FIKTIVBELEGUNG_MODE),
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


def test_it_follows_0006(monkeypatch: Any) -> None:
    migration, _ = _recorded(monkeypatch)

    assert migration.revision == "0007"
    assert migration.down_revision == "0006"


def test_person_count_tenancy_link_is_composite(monkeypatch: Any) -> None:
    """A bare `tenancy_id -> tenancy.id` FK is the cross-account hole.

    Postgres checks referential integrity with RLS bypassed, so a `person_count`
    row that stamps its own `account_id` correctly — and therefore passes
    `WITH CHECK` — could still point at a tenancy owned by another account. Only
    the pair `(tenancy_id, account_id) -> (tenancy.id, tenancy.account_id)` makes
    that edge unrepresentable, which is what `scripts/check_fk_isolation.py`
    demands of every new foreign key.
    """
    _, operations = _recorded(monkeypatch)

    _, args, _ = operations.calls[_index_of(operations, "create_table", "person_count")]
    constraints = [arg for arg in args if isinstance(arg, sa.ForeignKeyConstraint)]
    (tenancy_fk,) = [c for c in constraints if c.name == "person_count_tenancy_id_fkey"]

    assert tenancy_fk.column_keys == ["tenancy_id", "account_id"]
    assert [element.target_fullname for element in tenancy_fk.elements] == [
        "tenancy.id",
        "tenancy.account_id",
    ]
    # SIMPLE, not FULL: account_id is NOT NULL, and MATCH FULL would demand
    # all-or-nothing across the pair (see `_scoped_fk` in models.py).
    assert tenancy_fk.match == "SIMPLE"


def test_rls_is_enabled_forced_and_policied_after_the_table_exists(monkeypatch: Any) -> None:
    """ENABLE alone lets the table owner bypass every policy, and all three
    statements are `ALTER`/`CREATE POLICY` against a table that has to be there
    already — so the order is not cosmetic."""
    _, operations = _recorded(monkeypatch)

    table = _index_of(operations, "create_table", "person_count")
    enable = _execute_index(operations, "ALTER TABLE person_count ENABLE ROW LEVEL SECURITY")
    force = _execute_index(operations, "ALTER TABLE person_count FORCE ROW LEVEL SECURITY")
    policy = _execute_index(operations, "CREATE POLICY person_count_isolation ON person_count")

    assert table < enable < policy
    assert table < force < policy


def test_enum_type_is_created_before_the_column_that_uses_it(monkeypatch: Any) -> None:
    """`add_column` with an unmade enum type fails on Postgres, which is the whole
    reason the migration calls `.create(..., checkfirst=True)` explicitly instead
    of leaving it to the column's own DDL."""
    _, operations = _recorded(monkeypatch)

    created = _index_of(operations, "enum_create", "fiktivbelegung_mode")
    mode_column = next(
        index
        for index, (name, args, _) in enumerate(operations.calls)
        if name == "add_column" and args[0] == "building" and args[1].name == "fiktivbelegung_mode"
    )

    assert created < mode_column
    assert operations.calls[created][2] == {"checkfirst": True}


def test_waiver_check_comes_after_both_building_columns(monkeypatch: Any) -> None:
    """The CHECK names `fiktivbelegung_mode` and `fiktivbelegung_waiver_note`
    (Page 01 E18: `keine` is lawful only with a logged confirmation), so it cannot
    be created before either column exists."""
    _, operations = _recorded(monkeypatch)

    added = [
        index
        for index, (name, args, _) in enumerate(operations.calls)
        if name == "add_column"
        and args[0] == "building"
        and args[1].name in {"fiktivbelegung_mode", "fiktivbelegung_waiver_note"}
    ]
    check = _index_of(
        operations, "create_check_constraint", "ck_building_fiktivbelegung_waiver_logged"
    )

    assert len(added) == 2
    assert max(added) < check
