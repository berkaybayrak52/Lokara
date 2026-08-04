"""Kosten erfassen: cost_entry + append-only allocation_key_assignment.

The allocation key is deliberately NOT a column on cost_entry — re-keying a
cost INSERTs a new assignment row (latest wins), so no entered data is ever
touched. Both tables get the same FORCEd RLS backstop as every tenant table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("cost_entry", "allocation_key_assignment")


def _timestamp(name: str) -> sa.Column[sa.types.DateTime]:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


def upgrade() -> None:
    op.create_table(
        "cost_entry",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("building_id", sa.String(), sa.ForeignKey("building.id"), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("period_from", sa.Date(), nullable=False),
        sa.Column("period_to", sa.Date(), nullable=False),  # exclusive
        _timestamp("created_at"),
    )
    op.create_index("ix_cost_entry_account", "cost_entry", ["account_id"])
    op.create_index("ix_cost_entry_building", "cost_entry", ["building_id"])

    op.create_table(
        "allocation_key_assignment",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("cost_entry_id", sa.String(), sa.ForeignKey("cost_entry.id"), nullable=False),
        sa.Column(
            "key",
            postgresql.ENUM(name="allocation_key", create_type=False),  # shipped in 0001
            nullable=False,
        ),
        sa.Column("direct_unit_id", sa.String(), sa.ForeignKey("unit.id"), nullable=True),
        sa.Column("direct_tenancy_id", sa.String(), sa.ForeignKey("tenancy.id"), nullable=True),
        _timestamp("created_at"),
    )
    op.create_index("ix_aka_account", "allocation_key_assignment", ["account_id"])
    op.create_index("ix_aka_cost_entry", "allocation_key_assignment", ["cost_entry_id"])

    # Same RLS backstop as 0001: FORCE + USING/WITH CHECK on account_id.
    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_isolation ON {table}
            USING (account_id = current_setting('app.account_id', true))
            WITH CHECK (account_id = current_setting('app.account_id', true))
            """
        )


def downgrade() -> None:
    op.drop_table("allocation_key_assignment")
    op.drop_table("cost_entry")
