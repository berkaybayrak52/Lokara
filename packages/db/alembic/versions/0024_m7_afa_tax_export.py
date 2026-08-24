"""M7 immutable AfA and tax-export persistence."""
# ruff: noqa: E501

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0024"
down_revision = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

M7_TAX_TABLES = (
    "afa_record_version",
    "tax_event",
    "tax_adviser_profile_version",
    "tax_mapping_version",
    "tax_export_readiness_attempt",
    "tax_export_archive",
    "tax_export_artifact",
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


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_unit_tax_event_context", "unit", ["id", "account_id", "building_id"]
    )
    op.create_table(
        "afa_record_version",
        *_identity_columns(),
        sa.Column("building_id", sa.String(), nullable=False),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("result_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("rule_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("rechtsstand", sa.String(), nullable=False),
        sa.Column("production_blocked", sa.Boolean(), nullable=False),
        sa.Column("supersedes_afa_record_version_id", sa.String(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["building_id", "account_id"],
            ["building.id", "building.account_id"],
            name="afa_record_version_building_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_afa_record_version_id", "account_id", "building_id", "tax_year"],
            [
                "afa_record_version.id",
                "afa_record_version.account_id",
                "afa_record_version.building_id",
                "afa_record_version.tax_year",
            ],
            name="afa_record_version_supersedes_afa_record_version_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_afa_record_version_id_account"),
        sa.UniqueConstraint(
            "id",
            "account_id",
            "building_id",
            "tax_year",
            name="uq_afa_record_version_correction_context",
        ),
        sa.UniqueConstraint(
            "account_id", "building_id", "tax_year", "version", name="uq_afa_record_version"
        ),
        sa.UniqueConstraint(
            "account_id",
            "supersedes_afa_record_version_id",
            name="uq_afa_record_version_direct_successor",
        ),
        sa.CheckConstraint("version > 0", name="ck_afa_record_version_positive"),
        sa.CheckConstraint(
            "id <> supersedes_afa_record_version_id", name="ck_afa_record_version_not_self"
        ),
    )

    op.create_table(
        "tax_event",
        *_identity_columns(),
        sa.Column("building_id", sa.String(), nullable=False),
        sa.Column("unit_id", sa.String(), nullable=True),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("direction", sa.String(), nullable=False),
        sa.Column("receipt_reference", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source_payment_allocation_id", sa.String(), nullable=True),
        sa.Column("source_component", sa.String(), nullable=False),
        sa.Column("supersedes_tax_event_id", sa.String(), nullable=True),
        sa.Column("source_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["building_id", "account_id"],
            ["building.id", "building.account_id"],
            name="tax_event_building_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id", "account_id", "building_id"],
            ["unit.id", "unit.account_id", "unit.building_id"],
            name="tax_event_unit_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["source_payment_allocation_id", "account_id"],
            ["payment_allocation.id", "payment_allocation.account_id"],
            name="tax_event_source_payment_allocation_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_tax_event_id", "account_id", "building_id", "source_component"],
            [
                "tax_event.id",
                "tax_event.account_id",
                "tax_event.building_id",
                "tax_event.source_component",
            ],
            name="tax_event_supersedes_tax_event_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_tax_event_id_account"),
        sa.UniqueConstraint(
            "id",
            "account_id",
            "building_id",
            "source_component",
            name="uq_tax_event_correction_context",
        ),
        sa.UniqueConstraint(
            "account_id", "supersedes_tax_event_id", name="uq_tax_event_direct_successor"
        ),
        sa.CheckConstraint("amount_cents >= 0", name="ck_tax_event_amount_non_negative"),
        sa.CheckConstraint("direction IN ('einnahme', 'ausgabe')", name="ck_tax_event_direction"),
        sa.CheckConstraint(
            "source IN ('finapi', 'manuell', 'rechnung')", name="ck_tax_event_source"
        ),
        sa.CheckConstraint("version > 0", name="ck_tax_event_version_positive"),
        sa.CheckConstraint(
            "source_component IN ('manual', 'costs', 'interest', 'principal', "
            "'base_rent', 'nk_advance', 'heating_advance', 'garage')",
            name="ck_tax_event_source_component",
        ),
        sa.CheckConstraint("id <> supersedes_tax_event_id", name="ck_tax_event_not_self"),
    )
    op.create_index(
        "uq_tax_event_payment_allocation_component",
        "tax_event",
        ["account_id", "source_payment_allocation_id", "source_component"],
        unique=True,
        postgresql_where=sa.text(
            "supersedes_tax_event_id IS NULL AND source_payment_allocation_id IS NOT NULL"
        ),
    )

    op.create_table(
        "tax_adviser_profile_version",
        *_identity_columns(),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("profile_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("production_blocked", sa.Boolean(), nullable=False),
        sa.Column("supersedes_profile_version_id", sa.String(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["supersedes_profile_version_id", "account_id"],
            ["tax_adviser_profile_version.id", "tax_adviser_profile_version.account_id"],
            name="tax_adviser_profile_version_supersedes_profile_version_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_tax_adviser_profile_version_id_account"),
        sa.UniqueConstraint("account_id", "version", name="uq_tax_adviser_profile_version"),
        sa.UniqueConstraint(
            "account_id",
            "supersedes_profile_version_id",
            name="uq_tax_adviser_profile_direct_successor",
        ),
        sa.CheckConstraint("version > 0", name="ck_tax_adviser_profile_version_positive"),
        sa.CheckConstraint(
            "id <> supersedes_profile_version_id", name="ck_tax_adviser_profile_not_self"
        ),
    )

    op.create_table(
        "tax_mapping_version",
        *_identity_columns(),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("mapping_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("source_version", sa.String(), nullable=False),
        sa.Column("rechtsstand", sa.String(), nullable=False),
        sa.Column("production_blocked", sa.Boolean(), nullable=False),
        sa.Column("supersedes_mapping_version_id", sa.String(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["supersedes_mapping_version_id", "account_id", "tax_year"],
            [
                "tax_mapping_version.id",
                "tax_mapping_version.account_id",
                "tax_mapping_version.tax_year",
            ],
            name="tax_mapping_version_supersedes_mapping_version_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_tax_mapping_version_id_account"),
        sa.UniqueConstraint(
            "id",
            "account_id",
            "tax_year",
            name="uq_tax_mapping_version_correction_context",
        ),
        sa.UniqueConstraint("account_id", "tax_year", "version", name="uq_tax_mapping_version"),
        sa.UniqueConstraint(
            "account_id",
            "supersedes_mapping_version_id",
            name="uq_tax_mapping_direct_successor",
        ),
        sa.CheckConstraint("version > 0", name="ck_tax_mapping_version_positive"),
        sa.CheckConstraint("id <> supersedes_mapping_version_id", name="ck_tax_mapping_not_self"),
    )

    op.create_table(
        "tax_export_readiness_attempt",
        *_identity_columns(),
        sa.Column("building_id", sa.String(), nullable=False),
        sa.Column("afa_record_version_id", sa.String(), nullable=True),
        sa.Column("adviser_profile_version_id", sa.String(), nullable=True),
        sa.Column("mapping_version_id", sa.String(), nullable=False),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("export_kind", sa.String(), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("findings_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("production_blocked", sa.Boolean(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["building_id", "account_id"],
            ["building.id", "building.account_id"],
            name="tax_export_readiness_attempt_building_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["afa_record_version_id", "account_id"],
            ["afa_record_version.id", "afa_record_version.account_id"],
            name="tax_export_readiness_attempt_afa_record_version_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["adviser_profile_version_id", "account_id"],
            ["tax_adviser_profile_version.id", "tax_adviser_profile_version.account_id"],
            name="tax_export_readiness_attempt_adviser_profile_version_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["mapping_version_id", "account_id"],
            ["tax_mapping_version.id", "tax_mapping_version.account_id"],
            name="tax_export_readiness_attempt_mapping_version_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_tax_export_readiness_attempt_id_account"),
        sa.UniqueConstraint(
            "id",
            "account_id",
            "building_id",
            "tax_year",
            "export_kind",
            name="uq_tax_export_readiness_attempt_archive_context",
        ),
        sa.CheckConstraint(
            "export_kind IN ('anlage_v_pdf', 'anlage_v_csv', 'datev_extf')",
            name="ck_tax_export_readiness_kind",
        ),
    )

    op.create_table(
        "tax_export_archive",
        *_identity_columns(),
        sa.Column("readiness_attempt_id", sa.String(), nullable=False),
        sa.Column("building_id", sa.String(), nullable=False),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("export_kind", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("production_blocked", sa.Boolean(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("supersedes_archive_id", sa.String(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["readiness_attempt_id", "account_id", "building_id", "tax_year", "export_kind"],
            [
                "tax_export_readiness_attempt.id",
                "tax_export_readiness_attempt.account_id",
                "tax_export_readiness_attempt.building_id",
                "tax_export_readiness_attempt.tax_year",
                "tax_export_readiness_attempt.export_kind",
            ],
            name="tax_export_archive_readiness_attempt_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_archive_id", "account_id", "building_id", "tax_year", "export_kind"],
            [
                "tax_export_archive.id",
                "tax_export_archive.account_id",
                "tax_export_archive.building_id",
                "tax_export_archive.tax_year",
                "tax_export_archive.export_kind",
            ],
            name="tax_export_archive_supersedes_archive_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_tax_export_archive_id_account"),
        sa.UniqueConstraint(
            "id",
            "account_id",
            "building_id",
            "tax_year",
            "export_kind",
            name="uq_tax_export_archive_correction_context",
        ),
        sa.UniqueConstraint(
            "account_id",
            "building_id",
            "tax_year",
            "export_kind",
            "version",
            name="uq_tax_export_archive_version",
        ),
        sa.UniqueConstraint(
            "account_id", "supersedes_archive_id", name="uq_tax_export_archive_direct_successor"
        ),
        sa.CheckConstraint("version > 0", name="ck_tax_export_archive_version_positive"),
        sa.CheckConstraint("length(sha256) = 64", name="ck_tax_export_archive_sha256"),
        sa.CheckConstraint(
            "export_kind IN ('anlage_v_pdf', 'anlage_v_csv', 'datev_extf')",
            name="ck_tax_export_archive_kind",
        ),
        sa.CheckConstraint("id <> supersedes_archive_id", name="ck_tax_export_archive_not_self"),
    )

    op.create_table(
        "tax_export_artifact",
        *_identity_columns(),
        sa.Column("archive_id", sa.String(), nullable=False),
        sa.Column("artifact_kind", sa.String(), nullable=False),
        sa.Column("content_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("production_blocked", sa.Boolean(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["archive_id", "account_id"],
            ["tax_export_archive.id", "tax_export_archive.account_id"],
            name="tax_export_artifact_archive_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_tax_export_artifact_id_account"),
        sa.UniqueConstraint(
            "account_id", "archive_id", "artifact_kind", name="uq_tax_export_artifact_kind"
        ),
        sa.CheckConstraint("length(sha256) = 64", name="ck_tax_export_artifact_sha256"),
    )

    for table in M7_TAX_TABLES:
        op.create_index(
            f"ix_{table}_account",
            table_name=table,
            columns=["account_id"],
        )

    rls_statements = (
        "ALTER TABLE afa_record_version ENABLE ROW LEVEL SECURITY; ALTER TABLE afa_record_version FORCE ROW LEVEL SECURITY; CREATE POLICY afa_record_version_isolation ON afa_record_version USING (account_id = current_setting('app.account_id', true)) WITH CHECK (account_id = current_setting('app.account_id', true))",
        "ALTER TABLE tax_event ENABLE ROW LEVEL SECURITY; ALTER TABLE tax_event FORCE ROW LEVEL SECURITY; CREATE POLICY tax_event_isolation ON tax_event USING (account_id = current_setting('app.account_id', true)) WITH CHECK (account_id = current_setting('app.account_id', true))",
        "ALTER TABLE tax_adviser_profile_version ENABLE ROW LEVEL SECURITY; ALTER TABLE tax_adviser_profile_version FORCE ROW LEVEL SECURITY; CREATE POLICY tax_adviser_profile_version_isolation ON tax_adviser_profile_version USING (account_id = current_setting('app.account_id', true)) WITH CHECK (account_id = current_setting('app.account_id', true))",
        "ALTER TABLE tax_mapping_version ENABLE ROW LEVEL SECURITY; ALTER TABLE tax_mapping_version FORCE ROW LEVEL SECURITY; CREATE POLICY tax_mapping_version_isolation ON tax_mapping_version USING (account_id = current_setting('app.account_id', true)) WITH CHECK (account_id = current_setting('app.account_id', true))",
        "ALTER TABLE tax_export_readiness_attempt ENABLE ROW LEVEL SECURITY; ALTER TABLE tax_export_readiness_attempt FORCE ROW LEVEL SECURITY; CREATE POLICY tax_export_readiness_attempt_isolation ON tax_export_readiness_attempt USING (account_id = current_setting('app.account_id', true)) WITH CHECK (account_id = current_setting('app.account_id', true))",
        "ALTER TABLE tax_export_archive ENABLE ROW LEVEL SECURITY; ALTER TABLE tax_export_archive FORCE ROW LEVEL SECURITY; CREATE POLICY tax_export_archive_isolation ON tax_export_archive USING (account_id = current_setting('app.account_id', true)) WITH CHECK (account_id = current_setting('app.account_id', true))",
        "ALTER TABLE tax_export_artifact ENABLE ROW LEVEL SECURITY; ALTER TABLE tax_export_artifact FORCE ROW LEVEL SECURITY; CREATE POLICY tax_export_artifact_isolation ON tax_export_artifact USING (account_id = current_setting('app.account_id', true)) WITH CHECK (account_id = current_setting('app.account_id', true))",
    )
    for statement in rls_statements:
        op.execute(statement)

    op.execute(f"""
        CREATE FUNCTION public.enforce_tax_event_correction_stream_m7() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          IF NEW.supersedes_tax_event_id IS NOT NULL AND NOT EXISTS (
            SELECT 1
              FROM public.tax_event AS predecessor
             WHERE predecessor.id = NEW.supersedes_tax_event_id
               AND predecessor.account_id = NEW.account_id
               AND predecessor.building_id = NEW.building_id
               AND predecessor.source_component = NEW.source_component
               AND predecessor.source_payment_allocation_id IS NOT DISTINCT FROM
                   NEW.source_payment_allocation_id
          ) THEN
            RAISE EXCEPTION 'tax event correction must preserve its source stream'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER tax_event_correction_stream "
        "BEFORE INSERT ON tax_event FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_tax_event_correction_stream_m7()"
    )

    op.execute(f"""
        CREATE FUNCTION public.prevent_tax_record_rewrite_m7() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          RAISE EXCEPTION 'tax records are append-only' USING ERRCODE = '23514';
        END; $$
    """)
    trigger_statements = (
        "CREATE TRIGGER afa_record_version_append_only BEFORE UPDATE OR DELETE ON afa_record_version FOR EACH ROW EXECUTE FUNCTION public.prevent_tax_record_rewrite_m7()",
        "CREATE TRIGGER tax_event_append_only BEFORE UPDATE OR DELETE ON tax_event FOR EACH ROW EXECUTE FUNCTION public.prevent_tax_record_rewrite_m7()",
        "CREATE TRIGGER tax_adviser_profile_version_append_only BEFORE UPDATE OR DELETE ON tax_adviser_profile_version FOR EACH ROW EXECUTE FUNCTION public.prevent_tax_record_rewrite_m7()",
        "CREATE TRIGGER tax_mapping_version_append_only BEFORE UPDATE OR DELETE ON tax_mapping_version FOR EACH ROW EXECUTE FUNCTION public.prevent_tax_record_rewrite_m7()",
        "CREATE TRIGGER tax_export_readiness_attempt_append_only BEFORE UPDATE OR DELETE ON tax_export_readiness_attempt FOR EACH ROW EXECUTE FUNCTION public.prevent_tax_record_rewrite_m7()",
        "CREATE TRIGGER tax_export_archive_append_only BEFORE UPDATE OR DELETE ON tax_export_archive FOR EACH ROW EXECUTE FUNCTION public.prevent_tax_record_rewrite_m7()",
        "CREATE TRIGGER tax_export_artifact_append_only BEFORE UPDATE OR DELETE ON tax_export_artifact FOR EACH ROW EXECUTE FUNCTION public.prevent_tax_record_rewrite_m7()",
    )
    for statement in trigger_statements:
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tax_event_correction_stream ON tax_event")
    for table in reversed(M7_TAX_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}")
        op.drop_table(table)
    op.execute("DROP FUNCTION IF EXISTS public.prevent_tax_record_rewrite_m7()")
    op.execute("DROP FUNCTION IF EXISTS public.enforce_tax_event_correction_stream_m7()")
    op.drop_constraint("uq_unit_tax_event_context", "unit", type_="unique")
