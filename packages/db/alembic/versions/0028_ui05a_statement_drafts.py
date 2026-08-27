"""UI-05A resumable, account-scoped statement drafts."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0028"
down_revision = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "statement_document_archive",
        sa.Column("document_type", sa.String(), server_default="TENANT_STATEMENT", nullable=False),
    )
    op.drop_constraint(
        "uq_statement_archive_audience", "statement_document_archive", type_="unique"
    )
    op.create_unique_constraint(
        "uq_statement_archive_document_type",
        "statement_document_archive",
        ["statement_id", "audience", "tenancy_id", "document_type"],
    )
    op.create_check_constraint(
        "ck_statement_archive_document_type",
        "statement_document_archive",
        "document_type IN ('OWNER_OVERVIEW', 'COVER_LETTER', 'TENANT_STATEMENT')",
    )
    op.create_table(
        "statement_draft",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("building_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(), server_default="DRAFT", nullable=False),
        sa.Column("current_step", sa.Integer(), server_default="1", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "selected_unit_ids",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "overrides",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("final_statement_id", sa.String(), nullable=True),
        sa.Column("correction_of_statement_id", sa.String(), nullable=True),
        sa.Column("correction_reason", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["building_id", "account_id"],
            ["building.id", "building.account_id"],
            name="statement_draft_building_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["final_statement_id", "account_id"],
            ["statement.id", "statement.account_id"],
            name="statement_draft_final_statement_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["correction_of_statement_id", "account_id"],
            ["statement.id", "statement.account_id"],
            name="statement_draft_correction_of_statement_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_statement_draft_id_account"),
        sa.CheckConstraint("period_end >= period_start", name="ck_statement_draft_period_ordered"),
        sa.CheckConstraint("current_step BETWEEN 1 AND 6", name="ck_statement_draft_step"),
        sa.CheckConstraint("version >= 1", name="ck_statement_draft_version"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'REVIEW_REQUIRED', 'READY', 'FINALIZED', 'CANCELLED')",
            name="ck_statement_draft_status",
        ),
    )
    op.create_index("ix_statement_draft_account", "statement_draft", ["account_id"])
    op.create_index("ix_statement_draft_building", "statement_draft", ["building_id", "updated_at"])
    op.execute(
        "ALTER TABLE statement_draft ENABLE ROW LEVEL SECURITY; "
        "ALTER TABLE statement_draft FORCE ROW LEVEL SECURITY; "
        "CREATE POLICY statement_draft_isolation ON statement_draft "
        "USING (account_id = current_setting('app.account_id', true)) "
        "WITH CHECK (account_id = current_setting('app.account_id', true))"
    )


def downgrade() -> None:
    op.drop_table("statement_draft")
    op.drop_constraint(
        "ck_statement_archive_document_type", "statement_document_archive", type_="check"
    )
    op.drop_constraint(
        "uq_statement_archive_document_type", "statement_document_archive", type_="unique"
    )
    op.create_unique_constraint(
        "uq_statement_archive_audience",
        "statement_document_archive",
        ["statement_id", "audience", "tenancy_id"],
    )
    op.drop_column("statement_document_archive", "document_type")
