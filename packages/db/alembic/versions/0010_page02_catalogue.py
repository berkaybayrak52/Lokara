# ruff: noqa: E501
"""Persist Page-02 agreements and human cost classifications.

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def _rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {table}_isolation ON {table} USING (account_id = current_setting('app.account_id', true)) WITH CHECK (account_id = current_setting('app.account_id', true))"
    )


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_allocation_key_assignment_id_account",
        "allocation_key_assignment",
        ["id", "account_id"],
    )
    op.create_table(
        "operating_cost_agreement",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("account_id", sa.Text(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("tenancy_id", sa.Text(), nullable=False),
        sa.Column("allocation_agreed", sa.Boolean(), nullable=False),
        sa.Column("mehrbelastung_clause", sa.Boolean(), nullable=False),
        sa.Column("named_other_costs", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("contractual_keys", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date()),
        sa.Column("revises_id", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenancy_id", "account_id"],
            ["tenancy.id", "tenancy.account_id"],
            name="operating_cost_agreement_tenancy_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["revises_id", "account_id"],
            ["operating_cost_agreement.id", "operating_cost_agreement.account_id"],
            name="operating_cost_agreement_revises_id_fkey",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_operating_cost_agreement_id_account"),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="ck_operating_cost_agreement_period_ordered",
        ),
    )
    op.create_index(
        "ix_operating_cost_agreement_account", "operating_cost_agreement", ["account_id"]
    )
    op.create_index(
        "ix_operating_cost_agreement_tenancy", "operating_cost_agreement", ["tenancy_id"]
    )
    op.create_table(
        "confirmed_cost_classification",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("account_id", sa.Text(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("cost_entry_id", sa.Text(), nullable=False),
        sa.Column("allocation_key_assignment_id", sa.Text(), nullable=False),
        sa.Column("catalogue_id", sa.Text(), nullable=False),
        sa.Column("rule_rechtsstand", sa.Text(), nullable=False),
        sa.Column("source_amount_cents", sa.Integer(), nullable=False),
        sa.Column("allocable_cents", sa.Integer(), nullable=False),
        sa.Column("non_allocable_cents", sa.Integer(), nullable=False),
        sa.Column("labour_cents", sa.Integer()),
        sa.Column(
            "key",
            postgresql.ENUM(
                "AREA",
                "PERSONS",
                "CONSUMPTION",
                "UNITS",
                "DIRECT",
                "MEA",
                name="allocation_key",
                create_type=False,
            ),
        ),
        sa.Column("key_source", sa.Text()),
        sa.Column("findings", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("special_rule_evidence", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("production_blocked", sa.Boolean(), nullable=False),
        sa.Column(
            "confirmed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["cost_entry_id", "account_id"],
            ["cost_entry.id", "cost_entry.account_id"],
            name="confirmed_cost_classification_cost_entry_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["allocation_key_assignment_id", "account_id"],
            ["allocation_key_assignment.id", "allocation_key_assignment.account_id"],
            name="confirmed_cost_classification_assignment_id_fkey",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_confirmed_cost_classification_id_account"),
        sa.CheckConstraint(
            "source_amount_cents = allocable_cents + non_allocable_cents",
            name="ck_cost_classification_reconciles",
        ),
        sa.CheckConstraint(
            "labour_cents IS NULL OR (labour_cents >= 0 AND labour_cents <= allocable_cents)",
            name="ck_cost_classification_labour_valid",
        ),
    )
    op.create_index(
        "ix_cost_classification_account", "confirmed_cost_classification", ["account_id"]
    )
    op.create_index(
        "ix_cost_classification_cost", "confirmed_cost_classification", ["cost_entry_id"]
    )
    for table in ("operating_cost_agreement", "confirmed_cost_classification"):
        _rls(table)
    op.execute("""
        CREATE FUNCTION prevent_confirmed_cost_classification_rewrite() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'confirmed cost classifications are append-only' USING ERRCODE = '23514'; END; $$
    """)
    op.execute(
        "CREATE TRIGGER confirmed_cost_classification_append_only "
        "BEFORE UPDATE OR DELETE ON confirmed_cost_classification FOR EACH ROW "
        "EXECUTE FUNCTION prevent_confirmed_cost_classification_rewrite()"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER confirmed_cost_classification_append_only ON confirmed_cost_classification"
    )
    op.execute("DROP FUNCTION prevent_confirmed_cost_classification_rewrite()")
    for table in ("confirmed_cost_classification", "operating_cost_agreement"):
        op.execute(f"DROP POLICY {table}_isolation ON {table}")
    op.drop_table("confirmed_cost_classification")
    op.drop_table("operating_cost_agreement")
    op.drop_constraint(
        "uq_allocation_key_assignment_id_account",
        "allocation_key_assignment",
        type_="unique",
    )
