"""Red M6-A persistence contract from docs/02, M6A-F01 through M6A-F07.

This is deliberately metadata-level: it names the rows, immutable links and
isolation edges that the migration/model slice must supply before the API can
honestly expose an advance or a Saldo.  It does not test a proposed service
implementation.
"""

from datetime import date

from lokara_db import Base
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.sql.schema import Table

EXPECTED_M6_TABLES = {
    "advance_payment_period",
    "advance_payment",
    "advance_allocation",
    "advance_reconciliation",
    "advance_reconciliation_allocation",
}


def _table(name: str) -> Table:
    return Base.metadata.tables[name]


def _has_scoped_fk(table: Table, column: str, parent: str) -> bool:
    """The local pair is ``(id column, account_id)`` to the same parent pair."""
    return any(
        isinstance(constraint, ForeignKeyConstraint)
        and tuple(element.parent.name for element in constraint.elements) == (column, "account_id")
        and tuple(element.column.table.name for element in constraint.elements) == (parent, parent)
        and tuple(element.column.name for element in constraint.elements) == ("id", "account_id")
        for constraint in table.constraints
    )


def _unique_column_sets(table: Table) -> set[frozenset[str]]:
    return {
        frozenset(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def test_m6a_f01_scalar_is_replaced_by_backfillable_temporal_schedule() -> None:
    """M6A-F01: schedule has the migration inputs; new tenancy state has no scalar."""
    tenancy = _table("tenancy")
    period = _table("advance_payment_period")

    assert "advance_payment_cents" not in tenancy.columns
    assert {
        "id",
        "account_id",
        "tenancy_id",
        "amount_cents",
        "valid_from",
        "predecessor_id",
        "declaration_ref",
        "created_at",
    } <= set(period.columns.keys())
    assert period.columns["amount_cents"].type.python_type is int
    assert period.columns["valid_from"].type.python_type is date
    assert period.columns["predecessor_id"].nullable


def test_m6a_f02_successor_is_append_only_and_its_end_is_derived() -> None:
    """A successor link replaces a mutable end-date or mutable previous row."""
    period = _table("advance_payment_period")
    assert "valid_to" not in period.columns
    assert {"updated_at", "deleted_at", "superseded_at", "is_current"}.isdisjoint(period.columns)
    assert _has_scoped_fk(period, "tenancy_id", "tenancy")
    assert _has_scoped_fk(period, "predecessor_id", "advance_payment_period")
    assert frozenset({"tenancy_id", "valid_from"}) in _unique_column_sets(period)


def test_m6a_f03_to_f06_accepted_evidence_and_reconciliations_are_immutable() -> None:
    """Positive entries, zero confirmation and correction evidence need separate rows."""
    entry = _table("advance_payment")
    allocation = _table("advance_allocation")
    reconciliation = _table("advance_reconciliation")
    join = _table("advance_reconciliation_allocation")

    assert {
        "account_id",
        "tenancy_id",
        "amount_cents",
        "payment_date",
        "evidence_ref",
        "accepted_at",
        "reversal_of_id",
    } <= set(entry.columns.keys())
    assert {"updated_at", "deleted_at", "accepted"}.isdisjoint(entry.columns.keys())
    assert {
        "account_id",
        "payment_id",
        "tenancy_id",
        "period_start",
        "period_end",
        "amount_cents",
    } <= set(allocation.columns.keys())
    assert {
        "account_id",
        "tenancy_id",
        "period_start",
        "period_end",
        "version",
        "total_cents",
        "supersedes_id",
        "confirmed_at",
    } <= set(reconciliation.columns.keys())
    assert {"account_id", "reconciliation_id", "allocation_id"} <= set(join.columns.keys())
    assert frozenset({"tenancy_id", "period_start", "period_end", "version"}) in (
        _unique_column_sets(reconciliation)
    )
    assert frozenset({"reconciliation_id", "allocation_id"}) in (_unique_column_sets(join))
    # The empty join set is the explicit zero confirmation.  A nullable total
    # would conflate it with missing reconciliation and is forbidden.
    assert reconciliation.columns["total_cents"].type.python_type is int


def test_m6a_f07_every_new_edge_is_account_scoped() -> None:
    """Composite edges are required in addition to RLS for every new record."""
    for name in EXPECTED_M6_TABLES:
        table = _table(name)
        assert "account_id" in table.columns
        assert not table.columns["account_id"].nullable
        assert any(
            isinstance(constraint, ForeignKeyConstraint)
            and tuple(element.parent.name for element in constraint.elements) == ("account_id",)
            and tuple(element.column.table.name for element in constraint.elements) == ("account",)
            and tuple(element.column.name for element in constraint.elements) == ("id",)
            for constraint in table.constraints
        )

    entry = _table("advance_payment")
    allocation = _table("advance_allocation")
    reconciliation = _table("advance_reconciliation")
    join = _table("advance_reconciliation_allocation")
    assert _has_scoped_fk(entry, "tenancy_id", "tenancy")
    assert _has_scoped_fk(allocation, "payment_id", "advance_payment")
    assert _has_scoped_fk(allocation, "tenancy_id", "tenancy")
    assert _has_scoped_fk(reconciliation, "tenancy_id", "tenancy")
    assert _has_scoped_fk(join, "reconciliation_id", "advance_reconciliation")
    assert _has_scoped_fk(join, "allocation_id", "advance_allocation")


def test_m6a_constraints_keep_recorded_amounts_in_integer_cents() -> None:
    """M6A-F03/F06: positive entry/allocation amounts are DB constraints, not UI hints."""
    for table_name in ("advance_payment", "advance_allocation"):
        table = _table(table_name)
        assert table.columns["amount_cents"].type.python_type is int
        checks = [
            constraint.sqltext.text
            for constraint in table.constraints
            if isinstance(constraint, CheckConstraint)
        ]
        assert any("amount_cents" in check and "> 0" in check for check in checks)
