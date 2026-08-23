"""Add Page-02 void metadata and classification rule provenance.

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    # 0011 repaired the trigger definition for fresh chains.  Repeat the
    # idempotent replacement here so a database already at 0011 receives the
    # same append-only guard together with the void/provenance additions.
    op.execute(
        "DROP TRIGGER IF EXISTS confirmed_cost_classification_append_only "
        "ON confirmed_cost_classification"
    )
    op.execute(
        "CREATE TRIGGER confirmed_cost_classification_append_only "
        "BEFORE UPDATE OR DELETE ON confirmed_cost_classification FOR EACH ROW "
        "EXECUTE FUNCTION prevent_confirmed_cost_classification_rewrite()"
    )
    op.add_column("cost_entry", sa.Column("voided_at", sa.DateTime(timezone=True)))
    op.add_column("cost_entry", sa.Column("void_reason", sa.Text()))
    op.add_column("cost_entry", sa.Column("replaces_cost_entry_id", sa.Text()))
    op.add_column(
        "cost_entry", sa.Column("new_cost", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.create_foreign_key(
        "cost_entry_replaces_cost_entry_id_fkey",
        "cost_entry",
        "cost_entry",
        ["replaces_cost_entry_id", "account_id"],
        ["id", "account_id"],
    )
    op.add_column(
        "confirmed_cost_classification",
        sa.Column("rule_source", sa.Text(), nullable=False, server_default="BetrKV / Page 02"),
    )


def downgrade() -> None:
    op.drop_column("confirmed_cost_classification", "rule_source")
    op.drop_constraint("cost_entry_replaces_cost_entry_id_fkey", "cost_entry", type_="foreignkey")
    op.drop_column("cost_entry", "new_cost")
    op.drop_column("cost_entry", "replaces_cost_entry_id")
    op.drop_column("cost_entry", "void_reason")
    op.drop_column("cost_entry", "voided_at")
