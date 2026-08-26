"""M9 immutable guards, opt-in delivery, email and checklist evidence."""
# ruff: noqa: E501

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0025"
down_revision = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Creation order, and its exact reverse is the drop order. `guard_resolution_event`
# carries the W1 foreign key to `renter_delivery_artifact`, so the artifact table is
# created first; nothing in the artifact table points back at a guard table.
M9_TABLES = (
    "guard_evaluation",
    "guard_reminder",
    "delivery_schedule_version",
    "renter_delivery_artifact",
    "guard_resolution_" + "event",
    "email_attempt",
    "email_delivery_status_event",
    "recipient_suppression_event",
    "checklist_instance",
    "checklist_item_event",
)

_SEARCH_PATH = "pg_catalog, public, pg_temp"


def _identity_columns() -> tuple[sa.Column[object], ...]:
    return (
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
    )


def _audit_columns() -> tuple[sa.Column[object], ...]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def _scoped_fk(child: str, column: str, parent: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column, "account_id"],
        [f"{parent}.id", f"{parent}.account_id"],
        name=f"{child}_{column}_fkey",
        match="SIMPLE",
    )


def _scoped_identity(table: str) -> sa.UniqueConstraint:
    return sa.UniqueConstraint("id", "account_id", name=f"uq_{table}_id_account")


def _nonblank(*columns: str) -> str:
    return " AND ".join(f"btrim({column}, E' \\t\\n\\r') <> ''" for column in columns)


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_tenancy_delivery_context", "tenancy", ["id", "account_id", "unit_id"]
    )
    op.create_unique_constraint(
        "uq_tenancy_party_delivery_context",
        "tenancy_party",
        ["tenancy_id", "renter_id", "account_id"],
    )
    op.create_unique_constraint(
        "uq_statement_archive_delivery_context",
        "statement_document_archive",
        ["id", "account_id", "tenancy_id"],
    )
    op.create_unique_constraint(
        "uq_uvi_run_delivery_context",
        "uvi_run",
        ["id", "account_id", "tenancy_id", "unit_id"],
    )
    op.create_table(
        "guard_evaluation",
        *_identity_columns(),
        sa.Column("guard_code", sa.String(), nullable=False),
        sa.Column("subject_type", sa.String(), nullable=False),
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column("building_id", sa.String(), nullable=False),
        sa.Column("unit_id", sa.String(), nullable=True),
        sa.Column("tenancy_id", sa.String(), nullable=True),
        sa.Column("renter_id", sa.String(), nullable=True),
        sa.Column("occurrence_key", sa.String(), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("result_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("rule_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        *_audit_columns(),
        _scoped_fk("guard_evaluation", "building_id", "building"),
        sa.ForeignKeyConstraint(
            ["unit_id", "account_id", "building_id"],
            ["unit.id", "unit.account_id", "unit.building_id"],
            name="guard_evaluation_unit_context_fkey",
            match="SIMPLE",
        ),
        _scoped_fk("guard_evaluation", "tenancy_id", "tenancy"),
        _scoped_fk("guard_evaluation", "renter_id", "renter"),
        sa.ForeignKeyConstraint(
            ["tenancy_id", "account_id", "unit_id"],
            ["tenancy.id", "tenancy.account_id", "tenancy.unit_id"],
            name="guard_evaluation_tenancy_context_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["tenancy_id", "renter_id", "account_id"],
            ["tenancy_party.tenancy_id", "tenancy_party.renter_id", "tenancy_party.account_id"],
            name="guard_evaluation_tenancy_party_context_fkey",
            match="SIMPLE",
        ),
        _scoped_identity("guard_evaluation"),
        sa.UniqueConstraint(
            "id",
            "account_id",
            "occurrence_key",
            name="uq_guard_evaluation_reminder_context",
        ),
        sa.UniqueConstraint(
            "account_id", "guard_code", "occurrence_key", name="uq_guard_evaluation_occurrence"
        ),
        sa.CheckConstraint(
            _nonblank("guard_code", "subject_type", "subject_id", "occurrence_key"),
            name="ck_guard_evaluation_identity_nonblank",
        ),
        sa.CheckConstraint(
            "((unit_id IS NULL AND tenancy_id IS NULL AND renter_id IS NULL) OR "
            "(unit_id IS NOT NULL AND tenancy_id IS NOT NULL AND renter_id IS NOT NULL))",
            name="ck_guard_evaluation_renter_context_complete",
        ),
    )
    op.create_index(
        "ix_guard_evaluation_building",
        "guard_evaluation",
        ["account_id", "building_id", "evaluated_at"],
    )

    op.create_table(
        "guard_reminder",
        *_identity_columns(),
        sa.Column("guard_evaluation_id", sa.String(), nullable=False),
        sa.Column("occurrence_key", sa.String(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("payload_snapshot", postgresql.JSONB(), nullable=False),
        *_audit_columns(),
        _scoped_fk("guard_reminder", "guard_evaluation_id", "guard_evaluation"),
        sa.ForeignKeyConstraint(
            ["guard_evaluation_id", "account_id", "occurrence_key"],
            [
                "guard_evaluation.id",
                "guard_evaluation.account_id",
                "guard_evaluation.occurrence_key",
            ],
            name="guard_reminder_evaluation_occurrence_fkey",
            match="SIMPLE",
        ),
        _scoped_identity("guard_reminder"),
        sa.UniqueConstraint("account_id", "idempotency_key", name="uq_guard_reminder_idempotency"),
        sa.CheckConstraint(
            "channel IN ('EMAIL', 'IN_APP', 'PUSH')", name="ck_guard_reminder_channel"
        ),
        sa.CheckConstraint(
            _nonblank("occurrence_key", "idempotency_key"),
            name="ck_guard_reminder_identity_nonblank",
        ),
    )
    op.create_index("ix_guard_reminder_due", "guard_reminder", ["account_id", "due_at"])

    op.create_table(
        "delivery_schedule_version",
        *_identity_columns(),
        sa.Column("building_id", sa.String(), nullable=False),
        sa.Column("delivery_kind", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("supersedes_schedule_version_id", sa.String(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("schedule_snapshot", postgresql.JSONB(), nullable=False),
        *_audit_columns(),
        _scoped_fk("delivery_schedule_version", "building_id", "building"),
        _scoped_fk(
            "delivery_schedule_version",
            "supersedes_schedule_version_id",
            "delivery_schedule_version",
        ),
        _scoped_identity("delivery_schedule_version"),
        sa.UniqueConstraint(
            "id",
            "account_id",
            "building_id",
            "delivery_kind",
            name="uq_delivery_schedule_correction_context",
        ),
        sa.ForeignKeyConstraint(
            [
                "supersedes_schedule_version_id",
                "account_id",
                "building_id",
                "delivery_kind",
            ],
            [
                "delivery_schedule_version.id",
                "delivery_schedule_version.account_id",
                "delivery_schedule_version.building_id",
                "delivery_schedule_version.delivery_kind",
            ],
            name="delivery_schedule_supersedes_context_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint(
            "account_id",
            "building_id",
            "delivery_kind",
            "version",
            name="uq_delivery_schedule_version",
        ),
        sa.UniqueConstraint(
            "account_id",
            "supersedes_schedule_version_id",
            name="uq_delivery_schedule_direct_successor",
        ),
        sa.CheckConstraint("version > 0", name="ck_delivery_schedule_version_positive"),
        sa.CheckConstraint(
            "delivery_kind IN ('ANNUAL_STATEMENT', 'UVI')",
            name="ck_delivery_schedule_kind",
        ),
        sa.CheckConstraint(
            "id <> supersedes_schedule_version_id", name="ck_delivery_schedule_not_self"
        ),
    )
    op.create_index(
        "ix_delivery_schedule_building",
        "delivery_schedule_version",
        ["account_id", "building_id", "valid_from"],
    )

    op.create_table(
        "renter_delivery_artifact",
        *_identity_columns(),
        sa.Column("building_id", sa.String(), nullable=False),
        sa.Column("unit_id", sa.String(), nullable=False),
        sa.Column("tenancy_id", sa.String(), nullable=False),
        sa.Column("renter_id", sa.String(), nullable=False),
        sa.Column("artifact_kind", sa.String(), nullable=False),
        sa.Column("occurrence_key", sa.String(), nullable=False),
        sa.Column("statement_archive_id", sa.String(), nullable=True),
        sa.Column("uvi_run_id", sa.String(), nullable=True),
        sa.Column("content_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("production_blockers_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        *_audit_columns(),
        _scoped_fk("renter_delivery_artifact", "building_id", "building"),
        sa.ForeignKeyConstraint(
            ["unit_id", "account_id", "building_id"],
            ["unit.id", "unit.account_id", "unit.building_id"],
            name="renter_delivery_artifact_unit_context_fkey",
            match="SIMPLE",
        ),
        _scoped_fk("renter_delivery_artifact", "tenancy_id", "tenancy"),
        _scoped_fk("renter_delivery_artifact", "renter_id", "renter"),
        sa.ForeignKeyConstraint(
            ["tenancy_id", "account_id", "unit_id"],
            ["tenancy.id", "tenancy.account_id", "tenancy.unit_id"],
            name="renter_delivery_artifact_tenancy_context_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["tenancy_id", "renter_id", "account_id"],
            ["tenancy_party.tenancy_id", "tenancy_party.renter_id", "tenancy_party.account_id"],
            name="renter_delivery_artifact_tenancy_party_context_fkey",
            match="SIMPLE",
        ),
        _scoped_fk(
            "renter_delivery_artifact",
            "statement_archive_id",
            "statement_document_archive",
        ),
        _scoped_fk("renter_delivery_artifact", "uvi_run_id", "uvi_run"),
        sa.ForeignKeyConstraint(
            ["statement_archive_id", "account_id", "tenancy_id"],
            [
                "statement_document_archive.id",
                "statement_document_archive.account_id",
                "statement_document_archive.tenancy_id",
            ],
            name="renter_delivery_artifact_statement_context_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["uvi_run_id", "account_id", "tenancy_id", "unit_id"],
            ["uvi_run.id", "uvi_run.account_id", "uvi_run.tenancy_id", "uvi_run.unit_id"],
            name="renter_delivery_artifact_uvi_context_fkey",
            match="SIMPLE",
        ),
        _scoped_identity("renter_delivery_artifact"),
        sa.UniqueConstraint(
            "id",
            "account_id",
            "renter_id",
            name="uq_renter_delivery_artifact_email_context",
        ),
        sa.UniqueConstraint(
            "account_id",
            "renter_id",
            "artifact_kind",
            "occurrence_key",
            name="uq_renter_delivery_artifact_occurrence",
        ),
        sa.CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_renter_delivery_artifact_sha256"),
        sa.CheckConstraint(
            "octet_length(content_bytes) > 0", name="ck_renter_delivery_artifact_nonempty"
        ),
        sa.CheckConstraint(
            "((artifact_kind = 'ANNUAL_STATEMENT' AND statement_archive_id IS NOT NULL "
            "AND uvi_run_id IS NULL) OR "
            "(artifact_kind = 'UVI' AND statement_archive_id IS NULL "
            "AND uvi_run_id IS NOT NULL))",
            name="ck_renter_delivery_artifact_source_kind",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(production_blockers_snapshot) = 'array'",
            name="ck_renter_delivery_artifact_blockers_array",
        ),
        sa.CheckConstraint(
            _nonblank("artifact_kind", "occurrence_key", "mime_type", "filename"),
            name="ck_renter_delivery_artifact_metadata_nonblank",
        ),
    )
    op.create_index(
        "ix_renter_delivery_artifact_renter",
        "renter_delivery_artifact",
        ["account_id", "renter_id"],
    )

    op.create_table(
        "guard_resolution_event",
        *_identity_columns(),
        sa.Column("guard_evaluation_id", sa.String(), nullable=False),
        sa.Column("renter_delivery_artifact_id", sa.String(), nullable=True),
        sa.Column("confirmed_by_membership_id", sa.String(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_reference", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("event_snapshot", postgresql.JSONB(), nullable=False),
        *_audit_columns(),
        _scoped_fk("guard_resolution_event", "guard_evaluation_id", "guard_evaluation"),
        _scoped_fk(
            "guard_resolution_event",
            "renter_delivery_artifact_id",
            "renter_delivery_artifact",
        ),
        _scoped_fk(
            "guard_resolution_event",
            "confirmed_by_membership_id",
            "membership",
        ),
        _scoped_identity("guard_resolution_event"),
        sa.UniqueConstraint(
            "account_id", "idempotency_key", name="uq_guard_resolution_event_idempotency"
        ),
        sa.CheckConstraint(
            _nonblank("event_type", "evidence_reference", "idempotency_key"),
            name="ck_guard_resolution_event_evidence_nonblank",
        ),
        sa.CheckConstraint(
            "event_type NOT IN ('statement_sent', 'statement_sent_correction', "
            "'statement_delivery_evidence_late', "
            "'statement_delivery_evidence_late_correction') OR "
            "(renter_delivery_artifact_id IS NOT NULL AND "
            "confirmed_by_membership_id IS NOT NULL)",
            name="ck_guard_resolution_event_w1_confirmation_bindings",
        ),
    )
    op.create_index(
        "ix_guard_resolution_event_evaluation",
        "guard_resolution_event",
        ["account_id", "guard_evaluation_id", "occurred_at"],
    )

    op.create_table(
        "email_attempt",
        *_identity_columns(),
        sa.Column("renter_delivery_artifact_id", sa.String(), nullable=False),
        sa.Column("renter_id", sa.String(), nullable=False),
        sa.Column("normalized_recipient", sa.String(), nullable=False),
        sa.Column("sender_address", sa.String(), nullable=False),
        sa.Column("from_name", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("provider_message_id", sa.String(), nullable=True),
        sa.Column("message_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        *_audit_columns(),
        _scoped_fk("email_attempt", "renter_delivery_artifact_id", "renter_delivery_artifact"),
        _scoped_fk("email_attempt", "renter_id", "renter"),
        sa.ForeignKeyConstraint(
            ["renter_delivery_artifact_id", "account_id", "renter_id"],
            [
                "renter_delivery_artifact.id",
                "renter_delivery_artifact.account_id",
                "renter_delivery_artifact.renter_id",
            ],
            name="email_attempt_artifact_renter_context_fkey",
            match="SIMPLE",
        ),
        _scoped_identity("email_attempt"),
        sa.UniqueConstraint(
            "id",
            "account_id",
            "normalized_recipient",
            name="uq_email_attempt_suppression_context",
        ),
        sa.UniqueConstraint("account_id", "idempotency_key", name="uq_email_attempt_idempotency"),
        sa.CheckConstraint(
            "normalized_recipient = lower(btrim(normalized_recipient)) AND "
            "normalized_recipient LIKE '%@%'",
            name="ck_email_attempt_normalized_recipient",
        ),
        sa.CheckConstraint(
            "sender_address = lower(btrim(sender_address)) AND sender_address LIKE '%@lokara.de'",
            name="ck_email_attempt_lokara_sender",
        ),
        sa.CheckConstraint(
            _nonblank("from_name", "idempotency_key"),
            name="ck_email_attempt_identity_nonblank",
        ),
    )
    op.create_index(
        "ix_email_attempt_recipient",
        "email_attempt",
        ["account_id", "normalized_recipient"],
    )

    op.create_table(
        "email_delivery_status_event",
        *_identity_columns(),
        sa.Column("email_attempt_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_reference", sa.String(), nullable=True),
        sa.Column("event_snapshot", postgresql.JSONB(), nullable=False),
        *_audit_columns(),
        _scoped_fk("email_delivery_status_event", "email_attempt_id", "email_attempt"),
        _scoped_identity("email_delivery_status_event"),
        sa.CheckConstraint(
            "status IN ('QUEUED', 'DELIVERED', 'BOUNCED', 'COMPLAINED', 'FAILED')",
            name="ck_email_delivery_status_event_status",
        ),
        sa.CheckConstraint(
            "NOT (event_snapshot ? 'email_attempt_id') OR "
            "COALESCE(event_snapshot ->> 'email_attempt_id' = email_attempt_id, FALSE)",
            name="ck_email_delivery_status_event_attempt_snapshot",
        ),
    )
    op.create_index(
        "ix_email_delivery_status_event_attempt",
        "email_delivery_status_event",
        ["account_id", "email_attempt_id", "occurred_at"],
    )

    op.create_table(
        "recipient_suppression_event",
        *_identity_columns(),
        sa.Column("normalized_recipient", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("email_attempt_id", sa.String(), nullable=False),
        sa.Column("provider_reference", sa.String(), nullable=True),
        *_audit_columns(),
        _scoped_fk("recipient_suppression_event", "email_attempt_id", "email_attempt"),
        sa.ForeignKeyConstraint(
            ["email_attempt_id", "account_id", "normalized_recipient"],
            ["email_attempt.id", "email_attempt.account_id", "email_attempt.normalized_recipient"],
            name="recipient_suppression_attempt_recipient_fkey",
            match="SIMPLE",
        ),
        _scoped_identity("recipient_suppression_event"),
        sa.UniqueConstraint(
            "account_id",
            "normalized_recipient",
            "reason",
            "email_attempt_id",
            name="uq_recipient_suppression_event",
        ),
        sa.CheckConstraint(
            "reason IN ('BOUNCED', 'COMPLAINED')",
            name="ck_recipient_suppression_event_reason",
        ),
        sa.CheckConstraint(
            "normalized_recipient = lower(btrim(normalized_recipient)) AND "
            "normalized_recipient LIKE '%@%'",
            name="ck_recipient_suppression_normalized_recipient",
        ),
    )
    op.create_index(
        "ix_recipient_suppression_recipient",
        "recipient_suppression_event",
        ["account_id", "normalized_recipient", "occurred_at"],
    )

    op.create_table(
        "checklist_instance",
        *_identity_columns(),
        sa.Column("building_id", sa.String(), nullable=False),
        sa.Column("template_id", sa.String(), nullable=False),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("template_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("occurrence_key", sa.String(), nullable=False),
        *_audit_columns(),
        _scoped_fk("checklist_instance", "building_id", "building"),
        _scoped_identity("checklist_instance"),
        sa.UniqueConstraint(
            "account_id",
            "building_id",
            "template_id",
            "template_version",
            "occurrence_key",
            name="uq_checklist_instance_occurrence",
        ),
        sa.CheckConstraint("template_version > 0", name="ck_checklist_template_version_positive"),
        sa.CheckConstraint(
            _nonblank("template_id", "occurrence_key"),
            name="ck_checklist_instance_identity_nonblank",
        ),
    )
    op.create_index(
        "ix_checklist_instance_building",
        "checklist_instance",
        ["account_id", "building_id"],
    )

    op.create_table(
        "checklist_item_event",
        *_identity_columns(),
        sa.Column("checklist_instance_id", sa.String(), nullable=False),
        sa.Column("item_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_membership_id", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("event_snapshot", postgresql.JSONB(), nullable=False),
        *_audit_columns(),
        _scoped_fk("checklist_item_event", "checklist_instance_id", "checklist_instance"),
        _scoped_fk("checklist_item_event", "actor_membership_id", "membership"),
        _scoped_identity("checklist_item_event"),
        sa.UniqueConstraint(
            "account_id", "idempotency_key", name="uq_checklist_item_event_idempotency"
        ),
        sa.CheckConstraint(
            _nonblank("item_id", "event_type", "idempotency_key"),
            name="ck_checklist_item_event_identity_nonblank",
        ),
    )
    op.create_index(
        "ix_checklist_item_event_instance",
        "checklist_item_event",
        ["account_id", "checklist_instance_id", "occurred_at"],
    )

    for table in M9_TABLES:
        op.create_index(f"ix_{table}_account", table, ["account_id"])

    rls_statements = (
        "ALTER TABLE guard_evaluation ENABLE ROW LEVEL SECURITY; ALTER TABLE guard_evaluation FORCE ROW LEVEL SECURITY; CREATE POLICY guard_evaluation_isolation ON guard_evaluation USING (account_id = current_setting('app.account_id', true)) WITH CHECK (account_id = current_setting('app.account_id', true))",
        "ALTER TABLE guard_reminder ENABLE ROW LEVEL SECURITY; ALTER TABLE guard_reminder FORCE ROW LEVEL SECURITY; CREATE POLICY guard_reminder_isolation ON guard_reminder USING (account_id = current_setting('app.account_id', true)) WITH CHECK (account_id = current_setting('app.account_id', true))",
        "ALTER TABLE guard_resolution_event ENABLE ROW LEVEL SECURITY; ALTER TABLE guard_resolution_event FORCE ROW LEVEL SECURITY; CREATE POLICY guard_resolution_event_isolation ON guard_resolution_event USING (account_id = current_setting('app.account_id', true)) WITH CHECK (account_id = current_setting('app.account_id', true))",
        "ALTER TABLE delivery_schedule_version ENABLE ROW LEVEL SECURITY; ALTER TABLE delivery_schedule_version FORCE ROW LEVEL SECURITY; CREATE POLICY delivery_schedule_version_isolation ON delivery_schedule_version USING (account_id = current_setting('app.account_id', true)) WITH CHECK (account_id = current_setting('app.account_id', true))",
        "ALTER TABLE renter_delivery_artifact ENABLE ROW LEVEL SECURITY; ALTER TABLE renter_delivery_artifact FORCE ROW LEVEL SECURITY; CREATE POLICY renter_delivery_artifact_isolation ON renter_delivery_artifact USING (account_id = current_setting('app.account_id', true)) WITH CHECK (account_id = current_setting('app.account_id', true))",
        "ALTER TABLE email_attempt ENABLE ROW LEVEL SECURITY; ALTER TABLE email_attempt FORCE ROW LEVEL SECURITY; CREATE POLICY email_attempt_isolation ON email_attempt USING (account_id = current_setting('app.account_id', true)) WITH CHECK (account_id = current_setting('app.account_id', true))",
        "ALTER TABLE email_delivery_status_event ENABLE ROW LEVEL SECURITY; ALTER TABLE email_delivery_status_event FORCE ROW LEVEL SECURITY; CREATE POLICY email_delivery_status_event_isolation ON email_delivery_status_event USING (account_id = current_setting('app.account_id', true)) WITH CHECK (account_id = current_setting('app.account_id', true))",
        "ALTER TABLE recipient_suppression_event ENABLE ROW LEVEL SECURITY; ALTER TABLE recipient_suppression_event FORCE ROW LEVEL SECURITY; CREATE POLICY recipient_suppression_event_isolation ON recipient_suppression_event USING (account_id = current_setting('app.account_id', true)) WITH CHECK (account_id = current_setting('app.account_id', true))",
        "ALTER TABLE checklist_instance ENABLE ROW LEVEL SECURITY; ALTER TABLE checklist_instance FORCE ROW LEVEL SECURITY; CREATE POLICY checklist_instance_isolation ON checklist_instance USING (account_id = current_setting('app.account_id', true)) WITH CHECK (account_id = current_setting('app.account_id', true))",
        "ALTER TABLE checklist_item_event ENABLE ROW LEVEL SECURITY; ALTER TABLE checklist_item_event FORCE ROW LEVEL SECURITY; CREATE POLICY checklist_item_event_isolation ON checklist_item_event USING (account_id = current_setting('app.account_id', true)) WITH CHECK (account_id = current_setting('app.account_id', true))",
    )
    for statement in rls_statements:
        op.execute(statement)

    op.execute(f"""
        CREATE FUNCTION public.enforce_guard_resolution_owner_confirmation_m9()
        RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          IF NEW.event_type IN (
            'statement_sent',
            'statement_sent_correction',
            'statement_delivery_evidence_late',
            'statement_delivery_evidence_late_correction'
          ) THEN
            PERFORM 1
              FROM public.guard_evaluation AS evaluation
              JOIN public.renter_delivery_artifact AS artifact
                ON artifact.id = NEW.renter_delivery_artifact_id
               AND artifact.account_id = NEW.account_id
               AND artifact.artifact_kind = 'ANNUAL_STATEMENT'
               AND artifact.building_id = evaluation.building_id
               AND artifact.unit_id IS NOT DISTINCT FROM evaluation.unit_id
               AND artifact.tenancy_id IS NOT DISTINCT FROM evaluation.tenancy_id
               AND artifact.renter_id IS NOT DISTINCT FROM evaluation.renter_id
               AND artifact.occurrence_key = evaluation.occurrence_key
              JOIN public.membership AS membership
                ON membership.id = NEW.confirmed_by_membership_id
               AND membership.account_id = NEW.account_id
             WHERE evaluation.id = NEW.guard_evaluation_id
               AND evaluation.account_id = NEW.account_id
               AND evaluation.guard_code = 'W1'
               AND NEW.event_snapshot ->> 'artifact_id'
                   = NEW.renter_delivery_artifact_id
               AND membership.role = 'OWNER'
               AND membership.accepted_at IS NOT NULL
               AND membership.revoked_at IS NULL;
            IF NOT FOUND THEN
              RAISE EXCEPTION
                'W1 delivery confirmation requires the matching artifact and an active owner'
                USING ERRCODE = '23514',
                      CONSTRAINT = 'guard_resolution_event_artifact_evaluation_context_fkey';
            END IF;
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER guard_resolution_event_owner_confirmation "
        "AFTER INSERT ON public.guard_resolution_event FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_guard_resolution_owner_confirmation_m9()"
    )

    op.execute(f"""
        CREATE FUNCTION public.append_recipient_suppression_from_status_m9()
        RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          IF NEW.status IN ('BOUNCED', 'COMPLAINED') THEN
            INSERT INTO recipient_suppression_event (
              id,
              account_id,
              normalized_recipient,
              reason,
              occurred_at,
              email_attempt_id,
              provider_reference
            )
            SELECT
              'status-' || NEW.id,
              NEW.account_id,
              attempt.normalized_recipient,
              NEW.status,
              NEW.occurred_at,
              NEW.email_attempt_id,
              NEW.provider_reference
              FROM public.email_attempt AS attempt
             WHERE attempt.id = NEW.email_attempt_id
               AND attempt.account_id = NEW.account_id
            ON CONFLICT ON CONSTRAINT uq_recipient_suppression_event DO NOTHING;
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER email_delivery_status_event_suppression "
        "AFTER INSERT ON email_delivery_status_event FOR EACH ROW "
        "EXECUTE FUNCTION public.append_recipient_suppression_from_status_m9()"
    )

    op.execute(f"""
        CREATE FUNCTION public.deduplicate_recipient_suppression_m9() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          PERFORM 1
            FROM public.recipient_suppression_event AS existing
           WHERE existing.account_id = NEW.account_id
             AND existing.normalized_recipient = NEW.normalized_recipient
             AND existing.reason = NEW.reason
             AND existing.email_attempt_id = NEW.email_attempt_id;
          IF FOUND THEN
            RETURN NULL;
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER recipient_suppression_event_idempotency "
        "BEFORE INSERT ON recipient_suppression_event FOR EACH ROW "
        "EXECUTE FUNCTION public.deduplicate_recipient_suppression_m9()"
    )

    op.execute(f"""
        CREATE FUNCTION public.enforce_checklist_item_actor_scope_m9() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          PERFORM 1
            FROM public.membership AS membership
            JOIN public.checklist_instance AS checklist
              ON checklist.id = NEW.checklist_instance_id
             AND checklist.account_id = NEW.account_id
           WHERE membership.id = NEW.actor_membership_id
             AND membership.account_id = NEW.account_id
             AND membership.accepted_at IS NOT NULL
             AND membership.revoked_at IS NULL
             AND (
               membership.role = 'OWNER'::public.role
               OR (
                 membership.role = 'EMPLOYEE'::public.role
                 AND EXISTS (
                   SELECT 1
                     FROM public.building_assignment AS assignment
                    WHERE assignment.membership_id = membership.id
                      AND assignment.account_id = NEW.account_id
                      AND assignment.building_id = checklist.building_id
                 )
               )
             );
          IF NOT FOUND THEN
            RAISE EXCEPTION
              'checklist item actor must be an owner or an employee assigned to the building'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER checklist_item_event_actor_scope_guard "
        "AFTER INSERT ON public.checklist_item_event FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_checklist_item_actor_scope_m9()"
    )

    op.execute(f"""
        CREATE FUNCTION public.prevent_m9_evidence_rewrite() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          RAISE EXCEPTION 'M9 guard and delivery evidence is append-only'
            USING ERRCODE = '23514';
        END; $$
    """)
    trigger_statements = (
        "CREATE TRIGGER guard_evaluation_append_only BEFORE UPDATE OR DELETE ON guard_evaluation FOR EACH ROW EXECUTE FUNCTION public.prevent_m9_evidence_rewrite()",
        "CREATE TRIGGER guard_reminder_append_only BEFORE UPDATE OR DELETE ON guard_reminder FOR EACH ROW EXECUTE FUNCTION public.prevent_m9_evidence_rewrite()",
        "CREATE TRIGGER guard_resolution_event_append_only BEFORE UPDATE OR DELETE ON guard_resolution_event FOR EACH ROW EXECUTE FUNCTION public.prevent_m9_evidence_rewrite()",
        "CREATE TRIGGER delivery_schedule_version_append_only BEFORE UPDATE OR DELETE ON delivery_schedule_version FOR EACH ROW EXECUTE FUNCTION public.prevent_m9_evidence_rewrite()",
        "CREATE TRIGGER renter_delivery_artifact_append_only BEFORE UPDATE OR DELETE ON renter_delivery_artifact FOR EACH ROW EXECUTE FUNCTION public.prevent_m9_evidence_rewrite()",
        "CREATE TRIGGER email_attempt_append_only BEFORE UPDATE OR DELETE ON email_attempt FOR EACH ROW EXECUTE FUNCTION public.prevent_m9_evidence_rewrite()",
        "CREATE TRIGGER email_delivery_status_event_append_only BEFORE UPDATE OR DELETE ON email_delivery_status_event FOR EACH ROW EXECUTE FUNCTION public.prevent_m9_evidence_rewrite()",
        "CREATE TRIGGER recipient_suppression_event_append_only BEFORE UPDATE OR DELETE ON recipient_suppression_event FOR EACH ROW EXECUTE FUNCTION public.prevent_m9_evidence_rewrite()",
        "CREATE TRIGGER checklist_instance_append_only BEFORE UPDATE OR DELETE ON checklist_instance FOR EACH ROW EXECUTE FUNCTION public.prevent_m9_evidence_rewrite()",
        "CREATE TRIGGER checklist_item_event_append_only BEFORE UPDATE OR DELETE ON checklist_item_event FOR EACH ROW EXECUTE FUNCTION public.prevent_m9_evidence_rewrite()",
    )
    for statement in trigger_statements:
        op.execute(statement)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS guard_resolution_event_owner_confirmation ON guard_resolution_event"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS email_delivery_status_event_suppression "
        "ON email_delivery_status_event"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS recipient_suppression_event_idempotency "
        "ON recipient_suppression_event"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS checklist_item_event_actor_scope_guard ON checklist_item_event"
    )
    for table in reversed(M9_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}")
        op.drop_table(table)
    op.execute("DROP FUNCTION IF EXISTS public.enforce_checklist_item_actor_scope_m9()")
    op.execute("DROP FUNCTION IF EXISTS public.deduplicate_recipient_suppression_m9()")
    op.execute("DROP FUNCTION IF EXISTS public.append_recipient_suppression_from_status_m9()")
    op.execute("DROP FUNCTION IF EXISTS public.enforce_guard_resolution_owner_confirmation_m9()")
    op.execute("DROP FUNCTION IF EXISTS public.prevent_m9_evidence_rewrite()")
    op.drop_constraint("uq_tenancy_party_delivery_context", "tenancy_party", type_="unique")
    op.drop_constraint("uq_uvi_run_delivery_context", "uvi_run", type_="unique")
    op.drop_constraint(
        "uq_statement_archive_delivery_context",
        "statement_document_archive",
        type_="unique",
    )
    op.drop_constraint("uq_tenancy_delivery_context", "tenancy", type_="unique")
