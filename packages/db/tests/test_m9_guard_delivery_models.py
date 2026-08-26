"""Red M9 persistence contract for guards, delivery and checklists.

These are model- and migration-shape fixtures.  Runtime isolation probes belong
to the boundary audit; this file first makes the durable evidence surface
unambiguous for the model/migration implementer.
"""

from pathlib import Path

from lokara_db import ACCOUNT_SCOPED_TABLES, Base
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.sql.schema import DefaultClause, Table

M9_TABLES = {
    "guard_evaluation",
    "guard_reminder",
    "guard_resolution_event",
    "delivery_schedule_version",
    "renter_delivery_artifact",
    "email_attempt",
    "email_delivery_status_event",
    "recipient_suppression_event",
    "checklist_instance",
    "checklist_item_event",
}

ROOT = Path(__file__).resolve().parents[3]
MIGRATION = ROOT / "packages/db/alembic/versions/0025_m9_guard_delivery.py"


def _table(name: str) -> Table:
    return Base.metadata.tables[name]


def _unique_sets(table: Table) -> set[frozenset[str]]:
    return {
        frozenset(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def _scoped_fk(table: Table, column: str, parent: str) -> bool:
    return any(
        isinstance(constraint, ForeignKeyConstraint)
        and tuple(element.parent.name for element in constraint.elements) == (column, "account_id")
        and tuple(element.column.table.name for element in constraint.elements) == (parent, parent)
        and tuple(element.column.name for element in constraint.elements) == ("id", "account_id")
        for constraint in table.constraints
    )


def test_m9_tables_exist_and_are_account_scoped() -> None:
    assert set(Base.metadata.tables) >= M9_TABLES, "migration 0025 M9 models are missing"
    assert set(ACCOUNT_SCOPED_TABLES) >= M9_TABLES
    for name in M9_TABLES:
        account_id = _table(name).columns["account_id"]
        assert account_id.nullable is False, name


def test_guard_evaluation_freezes_exact_inputs_results_rules_and_occurrence() -> None:
    table = _table("guard_evaluation")
    assert {
        "guard_code",
        "subject_type",
        "subject_id",
        "building_id",
        "tenancy_id",
        "renter_id",
        "occurrence_key",
        "input_snapshot",
        "result_snapshot",
        "rule_snapshot",
        "evaluated_at",
    } <= set(table.columns.keys())
    assert _scoped_fk(table, "building_id", "building")
    assert _scoped_fk(table, "tenancy_id", "tenancy")
    assert _scoped_fk(table, "renter_id", "renter")
    assert frozenset({"account_id", "guard_code", "occurrence_key"}) in _unique_sets(table)


def test_reminders_are_idempotent_and_resolution_is_append_only_evidence() -> None:
    reminder = _table("guard_reminder")
    event = _table("guard_resolution_event")
    assert {
        "guard_evaluation_id",
        "occurrence_key",
        "channel",
        "due_at",
        "idempotency_key",
    } <= set(reminder.columns.keys())
    assert _scoped_fk(reminder, "guard_evaluation_id", "guard_evaluation")
    assert frozenset({"account_id", "idempotency_key"}) in _unique_sets(reminder)
    assert {"guard_evaluation_id", "event_type", "occurred_at", "evidence_reference"} <= set(
        event.columns.keys()
    )
    assert _scoped_fk(event, "guard_evaluation_id", "guard_evaluation")


def test_resolution_events_have_account_scoped_idempotency_keys() -> None:
    event = _table("guard_resolution_event")
    assert "idempotency_key" in event.columns
    assert event.columns["idempotency_key"].nullable is False
    assert frozenset({"account_id", "idempotency_key"}) in _unique_sets(event)

    source = MIGRATION.read_text(encoding="utf-8")
    resolution_table = source[source.index('"guard_resolution_event"') :]
    resolution_table = resolution_table[: resolution_table.index("op.create_table", 1)]
    assert 'sa.Column("idempotency_key", sa.String(), nullable=False)' in resolution_table
    assert '"account_id", "idempotency_key"' in resolution_table


def test_w1_confirmation_is_bound_to_artifact_and_active_owner_membership() -> None:
    event = _table("guard_resolution_event")
    assert {"renter_delivery_artifact_id", "confirmed_by_membership_id"} <= set(
        event.columns.keys()
    )
    assert _scoped_fk(event, "renter_delivery_artifact_id", "renter_delivery_artifact")
    assert _scoped_fk(event, "confirmed_by_membership_id", "membership")

    source = MIGRATION.read_text(encoding="utf-8")
    assert "guard_resolution_event_artifact_evaluation_context_fkey" in source
    assert "guard_resolution_event_owner_confirmation" in source
    assert "membership.role = 'OWNER'" in source
    assert "membership.revoked_at IS NULL" in source


def test_m9_actor_and_w1_triggers_pin_accepted_and_artifact_contracts() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    checklist_trigger = source[
        source.index(
            "CREATE FUNCTION public.enforce_checklist_item_actor_scope_m9()"
        ) : source.index("CREATE TRIGGER checklist_item_event_actor_scope_guard")
    ]
    confirmation_trigger = source[
        source.index(
            "CREATE FUNCTION public.enforce_guard_resolution_owner_confirmation_m9()"
        ) : source.index("CREATE TRIGGER guard_resolution_event_owner_confirmation")
    ]
    missing: list[str] = []
    if "membership.accepted_at IS NOT NULL" not in checklist_trigger:
        missing.append("accepted checklist membership")
    if not all(
        marker in confirmation_trigger for marker in ("artifact.artifact_kind", "ANNUAL_STATEMENT")
    ):
        missing.append("annual-statement artifact kind")
    if not all(
        marker in confirmation_trigger
        for marker in ("event_snapshot", "artifact_id", "renter_delivery_artifact_id")
    ):
        missing.append("snapshot artifact id equals bound artifact column")
    assert not missing, f"migration 0025 trigger contract is incomplete: {missing}"


def test_delivery_schedule_is_versioned_opt_in_and_database_default_off() -> None:
    table = _table("delivery_schedule_version")
    assert {
        "building_id",
        "delivery_kind",
        "version",
        "enabled",
        "supersedes_schedule_version_id",
        "valid_from",
    } <= set(table.columns.keys())
    assert _scoped_fk(table, "building_id", "building")
    assert _scoped_fk(table, "supersedes_schedule_version_id", "delivery_schedule_version")
    assert table.columns["enabled"].nullable is False
    server_default = table.columns["enabled"].server_default
    assert isinstance(server_default, DefaultClause)
    assert str(server_default.arg).lower() in {"false", "0"}
    assert frozenset({"account_id", "building_id", "delivery_kind", "version"}) in _unique_sets(
        table
    )


def test_delivery_artifact_freezes_exact_bytes_hash_and_scoped_context() -> None:
    table = _table("renter_delivery_artifact")
    assert {
        "building_id",
        "tenancy_id",
        "renter_id",
        "artifact_kind",
        "occurrence_key",
        "content_bytes",
        "sha256",
        "mime_type",
        "filename",
    } <= set(table.columns.keys())
    assert _scoped_fk(table, "building_id", "building")
    assert _scoped_fk(table, "tenancy_id", "tenancy")
    assert _scoped_fk(table, "renter_id", "renter")
    assert frozenset({"account_id", "renter_id", "artifact_kind", "occurrence_key"}) in (
        _unique_sets(table)
    )
    assert {"updated_at", "deleted_at", "storage_key"}.isdisjoint(table.columns.keys())


def test_delivery_artifact_binds_one_immutable_source_and_freezes_blockers() -> None:
    table = _table("renter_delivery_artifact")
    assert {
        "statement_archive_id",
        "uvi_run_id",
        "production_blockers_snapshot",
    } <= set(table.columns.keys())
    assert _scoped_fk(table, "statement_archive_id", "statement_document_archive")
    assert _scoped_fk(table, "uvi_run_id", "uvi_run")
    checks = " ".join(
        str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    ).lower()
    assert "statement_archive_id" in checks and "uvi_run_id" in checks
    assert "artifact_kind" in checks
    assert "production_blockers_snapshot" in checks


def test_email_attempt_and_status_events_preserve_one_recipient_and_idempotency() -> None:
    attempt = _table("email_attempt")
    status = _table("email_delivery_status_event")
    assert {
        "renter_delivery_artifact_id",
        "renter_id",
        "normalized_recipient",
        "sender_address",
        "from_name",
        "idempotency_key",
        "provider_message_id",
    } <= set(attempt.columns.keys())
    assert "cc" not in attempt.columns and "bcc" not in attempt.columns
    assert _scoped_fk(attempt, "renter_delivery_artifact_id", "renter_delivery_artifact")
    assert _scoped_fk(attempt, "renter_id", "renter")
    assert frozenset({"account_id", "idempotency_key"}) in _unique_sets(attempt)
    assert {"email_attempt_id", "status", "occurred_at", "provider_reference"} <= set(
        status.columns.keys()
    )
    assert _scoped_fk(status, "email_attempt_id", "email_attempt")


def test_async_negative_status_transactionally_appends_recipient_suppression() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    assert "AFTER INSERT ON email_delivery_status_event" in source
    assert "INSERT INTO recipient_suppression_event" in source
    assert "BOUNCED" in source and "COMPLAINED" in source


def test_suppression_and_checklist_history_are_append_only_and_scoped() -> None:
    suppression = _table("recipient_suppression_event")
    checklist = _table("checklist_instance")
    item = _table("checklist_item_event")
    assert {"normalized_recipient", "reason", "occurred_at", "email_attempt_id"} <= set(
        suppression.columns.keys()
    )
    assert _scoped_fk(suppression, "email_attempt_id", "email_attempt")
    assert {"building_id", "template_id", "template_version", "template_snapshot"} <= set(
        checklist.columns.keys()
    )
    assert _scoped_fk(checklist, "building_id", "building")
    assert {
        "checklist_instance_id",
        "item_id",
        "event_type",
        "occurred_at",
        "actor_membership_id",
    } <= set(item.columns.keys())
    assert _scoped_fk(item, "checklist_instance_id", "checklist_instance")
    assert _scoped_fk(item, "actor_membership_id", "membership")


def test_migration_0025_installs_forced_rls_and_append_only_guards() -> None:
    assert MIGRATION.exists(), "migration 0025 is missing"
    source = MIGRATION.read_text(encoding="utf-8")
    assert 'revision = "0025"' in source
    assert 'down_revision = "0024"' in source
    for name in M9_TABLES:
        assert f"{name} ENABLE ROW LEVEL SECURITY" in source
        assert f"{name} FORCE ROW LEVEL SECURITY" in source
        assert f"{name}_isolation" in source
    assert source.count("WITH CHECK") >= len(M9_TABLES)
    for name in M9_TABLES:
        assert f"{name}_append_only" in source
    assert "append-only" in source.lower()
