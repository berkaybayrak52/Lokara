"""UI-07 append-only transaction classification events."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bank_transaction_classification_event",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("bank_transaction_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("actor_person_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["bank_transaction_id", "account_id"],
            ["bank_transaction.id", "bank_transaction.account_id"],
            name="bank_transaction_classification_event_bank_transaction_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint(
            "id", "account_id", name="uq_bank_transaction_classification_event_id_account"
        ),
        sa.CheckConstraint(
            "action IN ('IGNORED', 'RESTORED')",
            name="ck_bank_transaction_classification_action",
        ),
    )
    op.create_index(
        "ix_bank_transaction_classification_account",
        "bank_transaction_classification_event",
        ["account_id"],
    )
    op.create_index(
        "ix_bank_transaction_classification_transaction",
        "bank_transaction_classification_event",
        ["bank_transaction_id", "created_at"],
    )
    op.execute(
        "ALTER TABLE bank_transaction_classification_event ENABLE ROW LEVEL SECURITY; "
        "ALTER TABLE bank_transaction_classification_event FORCE ROW LEVEL SECURITY; "
        "CREATE POLICY bank_transaction_classification_event_isolation "
        "ON bank_transaction_classification_event "
        "USING (account_id = current_setting('app.account_id', true)) "
        "WITH CHECK (account_id = current_setting('app.account_id', true))"
    )
    op.execute(
        "CREATE FUNCTION prevent_payment_classification_rewrite() RETURNS trigger AS $$ "
        "BEGIN RAISE EXCEPTION 'payment classification events are append-only'; END; "
        "$$ LANGUAGE plpgsql"
    )
    op.execute(
        "CREATE TRIGGER trg_bank_transaction_classification_event_append_only "
        "BEFORE UPDATE OR DELETE ON bank_transaction_classification_event "
        "FOR EACH ROW EXECUTE FUNCTION prevent_payment_classification_rewrite()"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_bank_transaction_classification_event_append_only "
        "ON bank_transaction_classification_event"
    )
    op.drop_table("bank_transaction_classification_event")
    op.execute("DROP FUNCTION prevent_payment_classification_rewrite()")
