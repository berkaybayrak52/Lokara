"""Add tenancy-bound renter activation codes and spend-once evidence."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0041"
down_revision = "0040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "renter_activation_code",
    "renter_activation_redemption",
    "renter_activation_attempt",
)
_SEARCH_PATH = "pg_catalog, public, pg_temp"


def upgrade() -> None:
    op.create_table(
        "renter_activation_code",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("renter_id", sa.String(), nullable=False),
        sa.Column("tenancy_id", sa.String(), nullable=False),
        sa.Column("code_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("issued_by_membership_id", sa.String(), nullable=False),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["renter_id", "account_id"],
            ["renter.id", "renter.account_id"],
            name="renter_activation_code_renter_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["tenancy_id", "account_id"],
            ["tenancy.id", "tenancy.account_id"],
            name="renter_activation_code_tenancy_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["issued_by_membership_id", "account_id"],
            ["membership.id", "membership.account_id"],
            name="renter_activation_code_issued_by_membership_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["tenancy_id", "renter_id", "account_id"],
            [
                "tenancy_party.tenancy_id",
                "tenancy_party.renter_id",
                "tenancy_party.account_id",
            ],
            name="renter_activation_code_tenancy_party_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_renter_activation_code_id_account"),
        sa.UniqueConstraint(
            "id",
            "account_id",
            "renter_id",
            "tenancy_id",
            name="uq_renter_activation_code_redemption_context",
        ),
        sa.UniqueConstraint(
            "account_id", "code_hash", name="uq_renter_activation_code_account_hash"
        ),
        sa.CheckConstraint("code_hash ~ '^[0-9a-f]{64}$'", name="ck_renter_activation_code_sha256"),
    )
    op.create_index("ix_renter_activation_code_account", "renter_activation_code", ["account_id"])
    op.create_index(
        "ix_renter_activation_code_target",
        "renter_activation_code",
        ["account_id", "tenancy_id", "renter_id"],
    )

    op.create_table(
        "renter_activation_redemption",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("activation_code_id", sa.String(), nullable=False),
        sa.Column("renter_id", sa.String(), nullable=False),
        sa.Column("tenancy_id", sa.String(), nullable=False),
        sa.Column("person_id", sa.String(), sa.ForeignKey("person.id"), nullable=False),
        sa.Column(
            "redeemed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["activation_code_id", "account_id", "renter_id", "tenancy_id"],
            [
                "renter_activation_code.id",
                "renter_activation_code.account_id",
                "renter_activation_code.renter_id",
                "renter_activation_code.tenancy_id",
            ],
            name="renter_activation_redemption_activation_code_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["renter_id", "account_id"],
            ["renter.id", "renter.account_id"],
            name="renter_activation_redemption_renter_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["tenancy_id", "account_id"],
            ["tenancy.id", "tenancy.account_id"],
            name="renter_activation_redemption_tenancy_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_renter_activation_redemption_id_account"),
        sa.UniqueConstraint(
            "activation_code_id", name="uq_renter_activation_redemption_activation_code"
        ),
    )
    op.create_index(
        "ix_renter_activation_redemption_account",
        "renter_activation_redemption",
        ["account_id"],
    )
    op.create_index(
        "ix_renter_activation_redemption_target",
        "renter_activation_redemption",
        ["account_id", "tenancy_id", "renter_id"],
    )

    op.create_table(
        "renter_activation_attempt",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("activation_code_id", sa.String(), nullable=True),
        sa.Column("requested_tenancy_id", sa.String(), nullable=False),
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("code_digest", sa.String(), nullable=False),
        sa.Column(
            "attempted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["activation_code_id", "account_id"],
            ["renter_activation_code.id", "renter_activation_code.account_id"],
            name="renter_activation_attempt_activation_code_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_renter_activation_attempt_id_account"),
        sa.CheckConstraint(
            "outcome IN ('ACTIVATION_CODE_SPENT', 'ACTIVATION_CODE_EXPIRED', "
            "'ACTIVATION_TENANCY_MISMATCH', 'ACTIVATION_ACCOUNT_MISMATCH', "
            "'RENTER_ALREADY_LINKED', 'ACTIVATION_PERSON_UNKNOWN', "
            "'ACTIVATION_CODE_UNKNOWN')",
            name="ck_renter_activation_attempt_outcome",
        ),
        sa.CheckConstraint(
            "code_digest ~ '^[0-9a-f]{64}$'",
            name="ck_renter_activation_attempt_sha256",
        ),
    )
    op.create_index(
        "ix_renter_activation_attempt_account",
        "renter_activation_attempt",
        ["account_id"],
    )

    for table in _TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_isolation ON public.{table} "
            "USING (account_id = current_setting('app.account_id', true)) "
            "WITH CHECK (account_id = current_setting('app.account_id', true))"
        )

    op.execute(f"""
        CREATE FUNCTION public.enforce_renter_activation_code_issuer_m10()
        RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          IF current_user = 'lokara_app'
             AND NEW.account_id IS DISTINCT FROM current_setting('app.account_id', true) THEN
            RETURN NEW;
          END IF;
          PERFORM 1
            FROM public.membership AS membership
           WHERE membership.id = NEW.issued_by_membership_id
             AND membership.account_id = NEW.account_id
             AND membership.role = 'OWNER'::public.role
             AND membership.accepted_at IS NOT NULL
             AND membership.revoked_at IS NULL;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'activation codes require an active owner issuer'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER renter_activation_code_owner_issuer "
        "BEFORE INSERT ON public.renter_activation_code FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_renter_activation_code_issuer_m10()"
    )

    op.execute(f"""
        CREATE FUNCTION public.enforce_renter_activation_redemption_m10()
        RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          IF current_user = 'lokara_app'
             AND NEW.account_id IS DISTINCT FROM current_setting('app.account_id', true) THEN
            RETURN NEW;
          END IF;
          PERFORM 1
            FROM public.renter AS renter
           WHERE renter.id = NEW.renter_id
             AND renter.account_id = NEW.account_id
             AND renter.person_id IS NULL;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'activation redemption requires an unlinked renter'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER renter_activation_redemption_guard "
        "BEFORE INSERT ON public.renter_activation_redemption FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_renter_activation_redemption_m10()"
    )

    op.execute(f"""
        CREATE FUNCTION public.enforce_renter_person_activation_m10()
        RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          IF TG_OP = 'INSERT' THEN
            IF NEW.person_id IS NOT NULL THEN
              RAISE EXCEPTION 'renter person link requires activation redemption'
                USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
          END IF;

          IF NEW.person_id IS NOT DISTINCT FROM OLD.person_id THEN
            RETURN NEW;
          END IF;
          IF OLD.person_id IS NOT NULL THEN
            RAISE EXCEPTION 'renter person link is immutable after activation'
              USING ERRCODE = '23514';
          END IF;
          IF NEW.person_id IS NULL OR NOT EXISTS (
            SELECT 1
              FROM public.renter_activation_redemption AS redemption
             WHERE redemption.account_id = NEW.account_id
               AND redemption.renter_id = NEW.id
               AND redemption.person_id = NEW.person_id
          ) THEN
            RAISE EXCEPTION 'renter person link requires matching activation redemption'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER renter_person_activation_guard "
        "BEFORE INSERT OR UPDATE OF person_id ON public.renter FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_renter_person_activation_m10()"
    )

    op.execute(f"""
        CREATE FUNCTION public.prevent_renter_activation_rewrite_m10()
        RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          RAISE EXCEPTION 'activation evidence is append-only'
            USING ERRCODE = '23514';
        END; $$
    """)
    for table in _TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON public.{table} "
            "FOR EACH ROW EXECUTE FUNCTION public.prevent_renter_activation_rewrite_m10()"
        )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS renter_person_activation_guard ON public.renter")
    for table in reversed(_TABLES):
        # ``IF EXISTS`` also supports a bounded local refresh when an uncommitted
        # revision was already applied before another table was added to it.
        op.execute(f"DROP TABLE IF EXISTS public.{table}")
    op.execute("DROP FUNCTION IF EXISTS public.prevent_renter_activation_rewrite_m10()")
    op.execute("DROP FUNCTION IF EXISTS public.enforce_renter_person_activation_m10()")
    op.execute("DROP FUNCTION IF EXISTS public.enforce_renter_activation_redemption_m10()")
    op.execute("DROP FUNCTION IF EXISTS public.enforce_renter_activation_code_issuer_m10()")
