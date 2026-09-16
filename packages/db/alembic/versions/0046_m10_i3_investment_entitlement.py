"""Add the immutable account-scoped investment entitlement stream."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0046"
down_revision = "0045"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SEARCH_PATH = "pg_catalog, public, pg_temp"


def upgrade() -> None:
    op.create_table(
        "investment_entitlement_event",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("entitlement_key", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("supersedes_entitlement_event_id", sa.String(), nullable=True),
        sa.Column("recorded_by_membership_id", sa.String(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_entitlement_event_id", "account_id", "entitlement_key"],
            [
                "investment_entitlement_event.id",
                "investment_entitlement_event.account_id",
                "investment_entitlement_event.entitlement_key",
            ],
            name="investment_entitlement_event_supersedes_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_membership_id", "account_id"],
            ["membership.id", "membership.account_id"],
            name="investment_entitlement_event_recorded_by_membership_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint(
            "id",
            "account_id",
            "entitlement_key",
            name="uq_investment_entitlement_event_correction_context",
        ),
        sa.UniqueConstraint(
            "account_id",
            "entitlement_key",
            "version",
            name="uq_investment_entitlement_event_stream_version",
        ),
        sa.CheckConstraint(
            "entitlement_key = 'INVESTMENT'",
            name="ck_investment_entitlement_event_key",
        ),
        sa.CheckConstraint("version > 0", name="ck_investment_entitlement_event_positive"),
        sa.CheckConstraint(
            "((version = 1 AND supersedes_entitlement_event_id IS NULL) OR "
            "(version > 1 AND supersedes_entitlement_event_id IS NOT NULL))",
            name="ck_investment_entitlement_event_root",
        ),
        sa.CheckConstraint(
            "id <> supersedes_entitlement_event_id",
            name="ck_investment_entitlement_event_not_self",
        ),
    )
    op.create_index(
        "uq_investment_entitlement_event_root",
        "investment_entitlement_event",
        ["account_id", "entitlement_key"],
        unique=True,
        postgresql_where=sa.text("supersedes_entitlement_event_id IS NULL"),
    )
    op.create_index(
        "uq_investment_entitlement_event_successor",
        "investment_entitlement_event",
        ["account_id", "entitlement_key", "supersedes_entitlement_event_id"],
        unique=True,
        postgresql_where=sa.text("supersedes_entitlement_event_id IS NOT NULL"),
    )
    op.create_index(
        "ix_investment_entitlement_event_account",
        "investment_entitlement_event",
        ["account_id"],
    )

    op.execute(f"""
        CREATE FUNCTION public.enforce_investment_entitlement_chain_m10()
        RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        DECLARE predecessor record;
        BEGIN
          IF NEW.version > 1 THEN
            SELECT prior.version INTO predecessor
              FROM public.investment_entitlement_event AS prior
             WHERE prior.id = NEW.supersedes_entitlement_event_id
               AND prior.account_id = NEW.account_id
               AND prior.entitlement_key = NEW.entitlement_key;
            IF NOT FOUND OR NOT predecessor.version = NEW.version - 1 THEN
              RAISE EXCEPTION 'entitlement event must follow the immediate version'
                USING ERRCODE = '23514';
            END IF;
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER investment_entitlement_event_chain_guard "
        "AFTER INSERT ON public.investment_entitlement_event FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_investment_entitlement_chain_m10()"
    )
    op.execute(f"""
        CREATE FUNCTION public.prevent_investment_entitlement_rewrite_m10()
        RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          RAISE EXCEPTION 'investment entitlement events are append-only'
            USING ERRCODE = '23514';
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER investment_entitlement_event_append_only "
        "BEFORE UPDATE OR DELETE ON public.investment_entitlement_event FOR EACH ROW "
        "EXECUTE FUNCTION public.prevent_investment_entitlement_rewrite_m10()"
    )

    op.execute("ALTER TABLE public.investment_entitlement_event ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.investment_entitlement_event FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY investment_entitlement_event_owner_select "
        "ON public.investment_entitlement_event FOR SELECT "
        "USING (account_id = current_setting('app.account_id', true) "
        "AND NULLIF(current_setting('app.tenancy_id', true), '') IS NULL)"
    )
    op.execute(
        "CREATE POLICY investment_entitlement_event_owner_insert "
        "ON public.investment_entitlement_event FOR INSERT "
        "WITH CHECK (account_id = current_setting('app.account_id', true) "
        "AND NULLIF(current_setting('app.tenancy_id', true), '') IS NULL)"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS investment_entitlement_event_append_only "
        "ON public.investment_entitlement_event"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS investment_entitlement_event_chain_guard "
        "ON public.investment_entitlement_event"
    )
    op.drop_table("investment_entitlement_event")
    op.execute("DROP FUNCTION IF EXISTS public.prevent_investment_entitlement_rewrite_m10()")
    op.execute("DROP FUNCTION IF EXISTS public.enforce_investment_entitlement_chain_m10()")
