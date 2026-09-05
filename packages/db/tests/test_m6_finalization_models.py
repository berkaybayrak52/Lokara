"""Red M6-B archive/finalization persistence contract from docs/02 and docs/08.

These are schema-level fixtures.  They deliberately do not prescribe a service
implementation; the migration/model implementer must supply the append-only,
account-scoped records before an API or PDF implementation can pass them.
"""

from lokara_db import Base
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.sql.schema import Table

REQUIRED_TABLES = {
    "statement_document_archive",
    "statement_settlement",
    "tenancy_delivery_address",
    "owner_payment_credit_instruction",
}


def _table(name: str) -> Table:
    return Base.metadata.tables[name]


def _scoped_fk(table: Table, column: str, parent: str) -> bool:
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


def test_m6b_records_exist_before_finalization_can_be_exposed() -> None:
    """M6B-F02--F04/F10/F16--F19: no archive without its durable records."""
    assert set(Base.metadata.tables) >= REQUIRED_TABLES


def test_m6b_finalized_statement_has_immutable_snapshot_and_scoped_predecessor() -> None:
    """M6B-IMM/CORR: final versions retain their exact inputs and correction chain."""
    statement = _table("statement")
    assert {"finalized_snapshot", "finalized_at", "supersedes_statement_id"} <= set(
        statement.columns.keys()
    )
    assert statement.columns["finalized_snapshot"].nullable is False
    assert statement.columns["finalized_at"].nullable is True
    assert _scoped_fk(statement, "supersedes_statement_id", "statement")


def test_m6b_archive_stores_downloadable_immutable_bytes_and_hash() -> None:
    """M6B-IMM: a download is an archive byte stream, never a recomputation."""
    archive = _table("statement_document_archive")
    assert {
        "id",
        "account_id",
        "statement_id",
        "audience",
        "tenancy_id",
        "document_type",
        "content_bytes",
        "sha256",
        "mime_type",
        "filename",
        "created_at",
    } <= set(archive.columns.keys())
    assert _scoped_fk(archive, "statement_id", "statement")
    assert _scoped_fk(archive, "tenancy_id", "tenancy")
    assert archive.columns["content_bytes"].nullable is False
    assert archive.columns["sha256"].nullable is False
    assert archive.columns["tenancy_id"].nullable is True
    assert {"updated_at", "deleted_at", "storage_key"}.isdisjoint(archive.columns)
    checks = [
        constraint.sqltext.text
        for constraint in archive.constraints
        if isinstance(constraint, CheckConstraint)
    ]
    assert any("sha256" in check for check in checks)


def test_m6b_archive_uniqueness_keeps_one_owner_and_one_tenant_document() -> None:
    """M6B-F16/F17: no duplicate document type per audience/tenancy and version."""
    archive = _table("statement_document_archive")
    unique_sets = _unique_column_sets(archive)
    assert frozenset({"statement_id", "audience", "tenancy_id", "document_type"}) in unique_sets
    # A nullable tenancy cannot make the owner row unique on PostgreSQL by
    # itself.  The implementation must add a partial unique owner index.
    assert any(
        index.unique
        and {"statement_id", "audience"} <= {column.name for column in index.columns}
        and index.dialect_options["postgresql"].get("where") is not None
        for index in archive.indexes
    )


def test_m6b_settlement_has_only_positive_obligations_and_scoped_links() -> None:
    """M6B-F02--F04/F18--F19: zero has no row; positive/negative have one obligation."""
    settlement = _table("statement_settlement")
    assert {
        "id",
        "account_id",
        "statement_id",
        "tenancy_id",
        "kind",
        "amount_cents",
        "origin_saldo_cents",
        "late_positive_exception_reason",
        "created_at",
    } <= set(settlement.columns.keys())
    assert _scoped_fk(settlement, "statement_id", "statement")
    assert _scoped_fk(settlement, "tenancy_id", "tenancy")
    assert frozenset({"statement_id", "tenancy_id"}) in _unique_column_sets(settlement)
    checks = [
        constraint.sqltext.text
        for constraint in settlement.constraints
        if isinstance(constraint, CheckConstraint)
    ]
    assert any("amount_cents" in check and "> 0" in check for check in checks)


def test_m6b_versioned_address_and_instruction_rows_are_append_only() -> None:
    """M6B-IMM: later delivery/payment-copy versions cannot rewrite a snapshot."""
    address = _table("tenancy_delivery_address")
    instruction = _table("owner_payment_credit_instruction")
    assert {
        "id",
        "account_id",
        "tenancy_id",
        "version",
        "addressee",
        "street",
        "postal_code",
        "city",
        "country",
        "created_at",
    } <= set(address.columns.keys())
    assert {"id", "account_id", "version", "instruction_text", "created_at"} <= set(
        instruction.columns.keys()
    )
    assert _scoped_fk(address, "tenancy_id", "tenancy")
    assert frozenset({"tenancy_id", "version"}) in _unique_column_sets(address)
    assert frozenset({"account_id", "version"}) in _unique_column_sets(instruction)
    for table in (address, instruction):
        assert {"updated_at", "deleted_at", "is_current", "superseded_at"}.isdisjoint(table.columns)
