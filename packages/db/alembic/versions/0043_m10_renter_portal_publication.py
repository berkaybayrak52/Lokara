"""Add immutable, tenancy-scoped renter portal publications."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0043"
down_revision = "0042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SEARCH_PATH = "pg_catalog, public, pg_temp"


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_renter_delivery_artifact_publication_context",
        "renter_delivery_artifact",
        ["id", "account_id", "tenancy_id"],
    )
    op.create_index(
        "uq_uvi_delivery_event_published_once",
        "uvi_delivery_event",
        ["account_id", "uvi_run_id"],
        unique=True,
        postgresql_where=sa.text("status = 'PUBLISHED'"),
    )

    op.create_table(
        "renter_portal_publication",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("tenancy_id", sa.String(), nullable=False),
        sa.Column("source_kind", sa.String(), nullable=False),
        sa.Column("statement_archive_id", sa.String(), nullable=True),
        sa.Column("renter_delivery_artifact_id", sa.String(), nullable=True),
        sa.Column("document_type", sa.String(), nullable=False),
        sa.Column("content_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("published_by_membership_id", sa.String(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_publication_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenancy_id", "account_id"],
            ["tenancy.id", "tenancy.account_id"],
            name="renter_portal_publication_tenancy_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["statement_archive_id", "account_id", "tenancy_id"],
            [
                "statement_document_archive.id",
                "statement_document_archive.account_id",
                "statement_document_archive.tenancy_id",
            ],
            name="renter_portal_publication_statement_archive_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["renter_delivery_artifact_id", "account_id", "tenancy_id"],
            [
                "renter_delivery_artifact.id",
                "renter_delivery_artifact.account_id",
                "renter_delivery_artifact.tenancy_id",
            ],
            name="renter_portal_publication_renter_delivery_artifact_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["published_by_membership_id", "account_id"],
            ["membership.id", "membership.account_id"],
            name="renter_portal_publication_published_by_membership_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_publication_id", "account_id", "tenancy_id", "document_type"],
            [
                "renter_portal_publication.id",
                "renter_portal_publication.account_id",
                "renter_portal_publication.tenancy_id",
                "renter_portal_publication.document_type",
            ],
            name="renter_portal_publication_supersedes_publication_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint(
            "id",
            "account_id",
            "tenancy_id",
            "document_type",
            name="uq_renter_portal_publication_supersession_context",
        ),
        sa.CheckConstraint(
            "source_kind IN ('STATEMENT_ARCHIVE', 'UVI_ARTIFACT')",
            name="ck_renter_portal_publication_source_kind",
        ),
        sa.CheckConstraint(
            "document_type IN ('COVER_LETTER', 'TENANT_STATEMENT', 'UVI')",
            name="ck_renter_portal_publication_document_type",
        ),
        sa.CheckConstraint(
            "((source_kind = 'STATEMENT_ARCHIVE' AND statement_archive_id IS NOT NULL "
            "AND renter_delivery_artifact_id IS NULL "
            "AND document_type IN ('COVER_LETTER', 'TENANT_STATEMENT')) OR "
            "(source_kind = 'UVI_ARTIFACT' AND statement_archive_id IS NULL "
            "AND renter_delivery_artifact_id IS NOT NULL AND document_type = 'UVI'))",
            name="ck_renter_portal_publication_source_document",
        ),
        sa.CheckConstraint(
            "octet_length(content_bytes) > 0",
            name="ck_renter_portal_publication_content_nonempty",
        ),
        sa.CheckConstraint(
            "sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_renter_portal_publication_sha256",
        ),
        sa.CheckConstraint(
            "btrim(mime_type, E' \\t\\n\\r') <> '' AND btrim(filename, E' \\t\\n\\r') <> ''",
            name="ck_renter_portal_publication_metadata_nonblank",
        ),
        sa.CheckConstraint(
            "id <> supersedes_publication_id",
            name="ck_renter_portal_publication_not_self_superseding",
        ),
    )
    op.create_index(
        "uq_renter_portal_publication_statement_source",
        "renter_portal_publication",
        ["account_id", "statement_archive_id"],
        unique=True,
        postgresql_where=sa.text("statement_archive_id IS NOT NULL"),
    )
    op.create_index(
        "uq_renter_portal_publication_uvi_source",
        "renter_portal_publication",
        ["account_id", "renter_delivery_artifact_id"],
        unique=True,
        postgresql_where=sa.text("renter_delivery_artifact_id IS NOT NULL"),
    )
    op.create_index(
        "ix_renter_portal_publication_account",
        "renter_portal_publication",
        ["account_id"],
    )
    op.create_index(
        "ix_renter_portal_publication_tenancy",
        "renter_portal_publication",
        ["account_id", "tenancy_id", "published_at"],
    )

    op.execute("ALTER TABLE public.renter_portal_publication ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.renter_portal_publication FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY renter_portal_publication_owner_select "
        "ON public.renter_portal_publication FOR SELECT "
        "USING (account_id = current_setting('app.account_id', true) "
        "AND NULLIF(current_setting('app.tenancy_id', true), '') IS NULL)"
    )
    op.execute(
        "CREATE POLICY renter_portal_publication_owner_insert "
        "ON public.renter_portal_publication FOR INSERT "
        "WITH CHECK (account_id = current_setting('app.account_id', true) "
        "AND NULLIF(current_setting('app.tenancy_id', true), '') IS NULL)"
    )
    op.execute(
        "CREATE POLICY renter_portal_publication_renter_select "
        "ON public.renter_portal_publication FOR SELECT TO lokara_app "
        "USING (account_id = current_setting('app.account_id', true) "
        "AND tenancy_id = current_setting('app.tenancy_id', true) "
        "AND NULLIF(current_setting('app.tenancy_id', true), '') IS NOT NULL)"
    )

    op.execute(f"""
        CREATE FUNCTION public.enforce_renter_portal_publication_source_m10()
        RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          PERFORM 1
            FROM public.membership AS publisher
           WHERE publisher.id = NEW.published_by_membership_id
             AND publisher.account_id = NEW.account_id
             AND publisher.role = 'OWNER'::public.role
             AND publisher.accepted_at IS NOT NULL
             AND publisher.revoked_at IS NULL;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'renter portal publication requires an active owner publisher'
              USING ERRCODE = '23514';
          END IF;

          IF NEW.source_kind = 'STATEMENT_ARCHIVE' THEN
            PERFORM 1
              FROM public.statement_document_archive AS archive
              JOIN public.statement AS statement
                ON statement.id = archive.statement_id
               AND statement.account_id = archive.account_id
             WHERE archive.id = NEW.statement_archive_id
               AND archive.account_id = NEW.account_id
               AND archive.tenancy_id = NEW.tenancy_id
               AND archive.audience = 'TENANT'
               AND archive.document_type = NEW.document_type
               AND archive.document_type IN ('COVER_LETTER', 'TENANT_STATEMENT')
               AND statement.finalized_at IS NOT NULL
               AND statement.status IN ('FINALIZED'::public.statement_status,
                                        'SUPERSEDED'::public.statement_status)
               AND json_typeof(statement.finalized_snapshot -> 'production_blockers') = 'array'
               AND json_array_length(statement.finalized_snapshot -> 'production_blockers') = 0;
            IF NOT FOUND THEN
              RAISE EXCEPTION 'statement archive is not eligible for renter portal publication'
                USING ERRCODE = '23514';
            END IF;
          ELSIF NEW.source_kind = 'UVI_ARTIFACT' THEN
            PERFORM 1
              FROM public.renter_delivery_artifact AS artifact
             WHERE artifact.id = NEW.renter_delivery_artifact_id
               AND artifact.account_id = NEW.account_id
               AND artifact.tenancy_id = NEW.tenancy_id
               AND artifact.artifact_kind = 'UVI'
               AND artifact.uvi_run_id IS NOT NULL
               AND jsonb_typeof(artifact.production_blockers_snapshot) = 'array'
               AND jsonb_array_length(artifact.production_blockers_snapshot) = 0;
            IF NOT FOUND THEN
              RAISE EXCEPTION 'UVI artifact is not eligible for renter portal publication'
                USING ERRCODE = '23514';
            END IF;
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER renter_portal_publication_source_guard "
        "AFTER INSERT ON public.renter_portal_publication FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_renter_portal_publication_source_m10()"
    )

    op.execute(f"""
        CREATE FUNCTION public.prevent_renter_portal_publication_rewrite_m10()
        RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          RAISE EXCEPTION 'renter portal publications are append-only'
            USING ERRCODE = '23514';
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER renter_portal_publication_append_only "
        "BEFORE UPDATE OR DELETE ON public.renter_portal_publication FOR EACH ROW "
        "EXECUTE FUNCTION public.prevent_renter_portal_publication_rewrite_m10()"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS renter_portal_publication_append_only "
        "ON public.renter_portal_publication"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS renter_portal_publication_source_guard "
        "ON public.renter_portal_publication"
    )
    op.drop_table("renter_portal_publication")
    op.execute("DROP FUNCTION IF EXISTS public.prevent_renter_portal_publication_rewrite_m10()")
    op.execute("DROP FUNCTION IF EXISTS public.enforce_renter_portal_publication_source_m10()")
    op.drop_index("uq_uvi_delivery_event_published_once", table_name="uvi_delivery_event")
    op.drop_constraint(
        "uq_renter_delivery_artifact_publication_context",
        "renter_delivery_artifact",
        type_="unique",
    )
