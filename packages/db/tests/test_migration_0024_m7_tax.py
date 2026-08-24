"""RED M7-C contract for immutable, account-scoped tax persistence."""

from __future__ import annotations

import ast
import importlib
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

MIGRATION = (
    Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0024_m7_afa_tax_export.py"
)

TABLES = (
    "afa_record_version",
    "tax_event",
    "tax_adviser_profile_version",
    "tax_mapping_version",
    "tax_export_readiness_attempt",
    "tax_export_archive",
    "tax_export_artifact",
)


def _migration() -> ModuleType:
    if not MIGRATION.exists():
        pytest.fail("RED M7-C: migration 0024_m7_afa_tax_export.py is missing", pytrace=False)
    spec = importlib.util.spec_from_file_location("m7_migration_0024", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _source() -> str:
    _migration()
    return MIGRATION.read_text(encoding="utf-8")


def _migration_calls(attribute: str) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(ast.parse(_source()))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == attribute
    ]


def _literal(value: ast.AST) -> Any:
    return ast.literal_eval(value)


def test_migration_0024_declares_exact_seven_record_groups() -> None:
    module = _migration()
    assert module.revision == "0024"
    assert module.down_revision == "0023"
    assert tuple(module.M7_TAX_TABLES) == TABLES
    source = _source()
    for table in TABLES:
        assert f'"{table}"' in source
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in source
        assert f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY" in source
        assert f"CREATE POLICY {table}_isolation" in source
        assert "WITH CHECK (account_id = current_setting('app.account_id', true))" in source


def test_models_expose_nullable_events_and_immutable_version_edges() -> None:
    db = importlib.import_module("lokara_db")
    expected = {
        "AfaRecordVersion": "afa_record_version",
        "TaxEvent": "tax_event",
        "TaxAdviserProfileVersion": "tax_adviser_profile_version",
        "TaxMappingVersion": "tax_mapping_version",
        "TaxExportReadinessAttempt": "tax_export_readiness_attempt",
        "TaxExportArchive": "tax_export_archive",
        "TaxExportArtifact": "tax_export_artifact",
    }
    for model_name, table_name in expected.items():
        model = getattr(db, model_name, None)
        assert model is not None, f"RED M7-C: {model_name} model is missing"
        assert model.__tablename__ == table_name
        assert "account_id" in model.__table__.columns

    event = db.TaxEvent.__table__.columns
    assert event["payment_date"].nullable
    assert event["category"].nullable
    assert not event["amount_cents"].nullable
    assert "supersedes_tax_event_id" in event
    assert "source_payment_allocation_id" in event


def test_materialized_tax_event_corrections_use_root_only_component_uniqueness() -> None:
    """A correction may retain its M6 stream; only a second root is a duplicate."""
    db = importlib.import_module("lokara_db")
    table = db.TaxEvent.__table__
    assert "source_component" in table.columns
    assert not table.columns["source_component"].nullable
    unique_columns = {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    component_identity = (
        "account_id",
        "source_payment_allocation_id",
        "source_component",
    )
    assert component_identity not in unique_columns
    assert ("account_id", "source_payment_allocation_id") not in unique_columns

    root_indexes = [
        index
        for index in table.indexes
        if index.unique and tuple(column.name for column in index.columns) == component_identity
    ]
    assert len(root_indexes) == 1
    root_predicate = str(root_indexes[0].dialect_options["postgresql"]["where"])
    normalized_predicate = " ".join(root_predicate.lower().split())
    assert "supersedes_tax_event_id is null" in normalized_predicate
    assert "source_payment_allocation_id is not null" in normalized_predicate

    source_component_columns = [
        call
        for call in _migration_calls("Column")
        if call.args and _literal(call.args[0]) == "source_component"
    ]
    assert len(source_component_columns) == 1
    nullable = next(
        keyword.value
        for keyword in source_component_columns[0].keywords
        if keyword.arg == "nullable"
    )
    assert _literal(nullable) is False
    unconditional_unique_components = {
        tuple(_literal(arg) for arg in call.args)
        for call in _migration_calls("UniqueConstraint")
        if all(isinstance(arg, ast.Constant) for arg in call.args)
    }
    assert component_identity not in unconditional_unique_components

    migration_root_indexes: list[tuple[ast.Call, str]] = []
    for call in _migration_calls("create_index"):
        if len(call.args) < 3:
            continue
        if (
            _literal(call.args[1]) != "tax_event"
            or tuple(_literal(call.args[2])) != component_identity
        ):
            continue
        keywords = {keyword.arg: keyword.value for keyword in call.keywords}
        if _literal(keywords["unique"]) is not True:
            continue
        predicate_call = keywords.get("postgresql_where")
        if not isinstance(predicate_call, ast.Call) or not predicate_call.args:
            continue
        migration_root_indexes.append((call, str(_literal(predicate_call.args[0]))))
    assert len(migration_root_indexes) == 1
    migration_predicate = " ".join(migration_root_indexes[0][1].lower().split())
    assert "supersedes_tax_event_id is null" in migration_predicate
    assert "source_payment_allocation_id is not null" in migration_predicate


def test_supersession_edges_preserve_their_logical_version_context() -> None:
    db = importlib.import_module("lokara_db")
    expected = (
        (
            db.AfaRecordVersion.__table__,
            (
                "supersedes_afa_record_version_id",
                "account_id",
                "building_id",
                "tax_year",
            ),
            ("id", "account_id", "building_id", "tax_year"),
        ),
        (
            db.TaxMappingVersion.__table__,
            ("supersedes_mapping_version_id", "account_id", "tax_year"),
            ("id", "account_id", "tax_year"),
        ),
        (
            db.TaxExportArchive.__table__,
            (
                "supersedes_archive_id",
                "account_id",
                "building_id",
                "tax_year",
                "export_kind",
            ),
            ("id", "account_id", "building_id", "tax_year", "export_kind"),
        ),
    )
    for table, local_columns, remote_columns in expected:
        matching_fks = [
            constraint
            for constraint in table.foreign_key_constraints
            if tuple(constraint.column_keys) == local_columns
            and tuple(element.column.name for element in constraint.elements) == remote_columns
        ]
        assert matching_fks, (
            f"{table.name} supersession must keep its building/year or readiness stream"
        )
        unique_columns = {
            tuple(constraint.columns.keys())
            for constraint in table.constraints
            if constraint.__class__.__name__ == "UniqueConstraint"
        }
        assert remote_columns in unique_columns

    migration_foreign_keys: set[tuple[tuple[str, ...], tuple[str, ...]]] = {
        (tuple(_literal(call.args[0])), tuple(_literal(call.args[1])))
        for call in _migration_calls("ForeignKeyConstraint")
        if len(call.args) >= 2
    }
    for migration_local, migration_remote in (
        (
            ["supersedes_afa_record_version_id", "account_id", "building_id", "tax_year"],
            [
                "afa_record_version.id",
                "afa_record_version.account_id",
                "afa_record_version.building_id",
                "afa_record_version.tax_year",
            ],
        ),
        (
            ["supersedes_mapping_version_id", "account_id", "tax_year"],
            [
                "tax_mapping_version.id",
                "tax_mapping_version.account_id",
                "tax_mapping_version.tax_year",
            ],
        ),
        (
            ["supersedes_archive_id", "account_id", "building_id", "tax_year", "export_kind"],
            [
                "tax_export_archive.id",
                "tax_export_archive.account_id",
                "tax_export_archive.building_id",
                "tax_export_archive.tax_year",
                "tax_export_archive.export_kind",
            ],
        ),
    ):
        assert (tuple(migration_local), tuple(migration_remote)) in migration_foreign_keys


def test_tax_event_correction_preserves_building_and_source_stream() -> None:
    db = importlib.import_module("lokara_db")
    table = db.TaxEvent.__table__
    local_columns = (
        "supersedes_tax_event_id",
        "account_id",
        "building_id",
        "source_component",
    )
    remote_columns = ("id", "account_id", "building_id", "source_component")
    assert any(
        tuple(constraint.column_keys) == local_columns
        and tuple(element.column.name for element in constraint.elements) == remote_columns
        for constraint in table.foreign_key_constraints
    )
    unique_columns = {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert remote_columns in unique_columns

    migration_foreign_keys: set[tuple[tuple[str, ...], tuple[str, ...]]] = {
        (tuple(_literal(call.args[0])), tuple(_literal(call.args[1])))
        for call in _migration_calls("ForeignKeyConstraint")
        if len(call.args) >= 2
    }
    assert (
        local_columns,
        (
            "tax_event.id",
            "tax_event.account_id",
            "tax_event.building_id",
            "tax_event.source_component",
        ),
    ) in migration_foreign_keys
    # The allocation link is nullable for manual events, so equality across that
    # part of the source stream needs a null-safe correction guard.
    normalized_source = " ".join(_source().split())
    assert "source_payment_allocation_id IS NOT DISTINCT FROM" in normalized_source


def test_composite_fks_idempotent_materialization_and_append_only_bytes_are_enforced() -> None:
    source = _source()
    for table in TABLES:
        assert f"{table}_append_only" in source
    assert "BEFORE UPDATE OR DELETE" in source
    assert "tax records are append-only" in source

    # One accepted M6 allocation can materialize each stable component at most once.
    assert "uq_tax_event_payment_allocation_component" in source
    assert "source_payment_allocation_id" in source
    assert "source_component" in source
    # Corrections append a same-account successor; they never rewrite the original.
    assert "supersedes_tax_event_id" in source
    assert "uq_tax_event_direct_successor" in source
    # Archives and artifacts freeze exact bytes and their digest.
    assert "content_bytes" in source
    assert "sha256" in source
    assert "tax_export_artifact_append_only" in source
    # Account-scoped edges use composite constraints, never id-only foreign keys.
    assert source.count("sa.ForeignKeyConstraint(") >= 7
    assert source.count('"account_id"') >= len(TABLES)


def test_rls_with_check_contract_refuses_cross_account_writes() -> None:
    """Static RED guard; the later boundary audit supplies the rolled-back live probe."""

    source = _source()
    for table in TABLES:
        assert f"CREATE POLICY {table}_isolation" in source
        assert "USING (account_id = current_setting('app.account_id', true))" in source
        assert "WITH CHECK (account_id = current_setting('app.account_id', true))" in source
