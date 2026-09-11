"""Add immutable source-derived display periods to renter publications."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0044"
down_revision = "0043"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SEARCH_PATH = "pg_catalog, public, pg_temp"

_DISPLAY_PERIOD_CHECK = (
    "((source_kind = 'STATEMENT_ARCHIVE' "
    "AND period_start IS NOT NULL AND period_end IS NOT NULL "
    "AND period_start <= period_end AND document_month IS NULL) OR "
    "(source_kind = 'UVI_ARTIFACT' "
    "AND period_start IS NULL AND period_end IS NULL "
    "AND document_month IS NOT NULL AND EXTRACT(DAY FROM document_month) = 1))"
)


def _install_source_guard(*, verify_display_period: bool) -> None:
    statement_display_guard = ""
    uvi_join = ""
    uvi_display_guard = ""
    if verify_display_period:
        statement_display_guard = (
            "AND NEW.period_start = statement.period_start "
            "AND NEW.period_end = statement.period_end "
            "AND NEW.document_month IS NULL"
        )
        uvi_join = (
            "JOIN public.uvi_run AS uvi_run "
            "ON uvi_run.id = artifact.uvi_run_id "
            "AND uvi_run.account_id = artifact.account_id "
            "AND uvi_run.tenancy_id = artifact.tenancy_id "
            "AND uvi_run.unit_id = artifact.unit_id"
        )
        uvi_display_guard = (
            "AND NEW.period_start IS NULL "
            "AND NEW.period_end IS NULL "
            "AND NEW.document_month = uvi_run.month"
        )

    op.execute(f"""
        CREATE OR REPLACE FUNCTION public.enforce_renter_portal_publication_source_m10()
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
               AND json_array_length(statement.finalized_snapshot -> 'production_blockers') = 0
               {statement_display_guard};
            IF NOT FOUND THEN
              RAISE EXCEPTION 'statement archive is not eligible for renter portal publication'
                USING ERRCODE = '23514';
            END IF;
          ELSIF NEW.source_kind = 'UVI_ARTIFACT' THEN
            PERFORM 1
              FROM public.renter_delivery_artifact AS artifact
              {uvi_join}
             WHERE artifact.id = NEW.renter_delivery_artifact_id
               AND artifact.account_id = NEW.account_id
               AND artifact.tenancy_id = NEW.tenancy_id
               AND artifact.artifact_kind = 'UVI'
               AND artifact.uvi_run_id IS NOT NULL
               AND jsonb_typeof(artifact.production_blockers_snapshot) = 'array'
               AND jsonb_array_length(artifact.production_blockers_snapshot) = 0
               {uvi_display_guard};
            IF NOT FOUND THEN
              RAISE EXCEPTION 'UVI artifact is not eligible for renter portal publication'
                USING ERRCODE = '23514';
            END IF;
          END IF;
          RETURN NEW;
        END; $$
    """)


def upgrade() -> None:
    op.add_column("renter_portal_publication", sa.Column("period_start", sa.Date(), nullable=True))
    op.add_column("renter_portal_publication", sa.Column("period_end", sa.Date(), nullable=True))
    op.add_column(
        "renter_portal_publication", sa.Column("document_month", sa.Date(), nullable=True)
    )

    # The table is append-only at runtime. Temporarily remove only its rewrite
    # trigger so existing immutable rows can receive source-derived metadata.
    op.execute(
        "DROP TRIGGER renter_portal_publication_append_only ON public.renter_portal_publication"
    )
    op.execute("""
        UPDATE public.renter_portal_publication AS publication
           SET period_start = statement.period_start,
               period_end = statement.period_end
          FROM public.statement_document_archive AS archive
          JOIN public.statement AS statement
            ON statement.id = archive.statement_id
           AND statement.account_id = archive.account_id
         WHERE publication.source_kind = 'STATEMENT_ARCHIVE'
           AND publication.statement_archive_id = archive.id
           AND publication.account_id = archive.account_id
           AND publication.tenancy_id = archive.tenancy_id
    """)
    op.execute("""
        UPDATE public.renter_portal_publication AS publication
           SET document_month = uvi_run.month
          FROM public.renter_delivery_artifact AS artifact
          JOIN public.uvi_run AS uvi_run
            ON uvi_run.id = artifact.uvi_run_id
           AND uvi_run.account_id = artifact.account_id
           AND uvi_run.tenancy_id = artifact.tenancy_id
           AND uvi_run.unit_id = artifact.unit_id
         WHERE publication.source_kind = 'UVI_ARTIFACT'
           AND publication.renter_delivery_artifact_id = artifact.id
           AND publication.account_id = artifact.account_id
           AND publication.tenancy_id = artifact.tenancy_id
    """)

    op.create_check_constraint(
        "ck_renter_portal_publication_display_period",
        "renter_portal_publication",
        _DISPLAY_PERIOD_CHECK,
    )
    _install_source_guard(verify_display_period=True)
    op.execute(
        "CREATE TRIGGER renter_portal_publication_append_only "
        "BEFORE UPDATE OR DELETE ON public.renter_portal_publication FOR EACH ROW "
        "EXECUTE FUNCTION public.prevent_renter_portal_publication_rewrite_m10()"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER renter_portal_publication_append_only ON public.renter_portal_publication"
    )
    _install_source_guard(verify_display_period=False)
    op.drop_constraint(
        "ck_renter_portal_publication_display_period",
        "renter_portal_publication",
        type_="check",
    )
    op.drop_column("renter_portal_publication", "document_month")
    op.drop_column("renter_portal_publication", "period_end")
    op.drop_column("renter_portal_publication", "period_start")
    op.execute(
        "CREATE TRIGGER renter_portal_publication_append_only "
        "BEFORE UPDATE OR DELETE ON public.renter_portal_publication FOR EACH ROW "
        "EXECUTE FUNCTION public.prevent_renter_portal_publication_rewrite_m10()"
    )
