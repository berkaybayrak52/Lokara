"""Confirmed Messdienstleister statements and their per-renter positions.

`docs/03` H7: validate and pass through; never recompute MDL amounts. So the
positions are stored exactly as the document delivered them, and the only check
is the control sum against the confirmed total.

Append-only and versioned (`CLAUDE.md` § 3.2): a correction inserts
`version + 1` for the same building period, which is what the UNIQUE constraint
below permits and what an UPDATE would destroy.

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("mdl_statement", "mdl_statement_position")

_MDL_BRANCH = sa.Enum("NET", "GROSS", name="mdl_branch")


def upgrade() -> None:
    op.create_table(
        "mdl_statement",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("building_id", sa.String(), nullable=False),
        sa.Column("branch", _MDL_BRANCH, nullable=False),
        sa.Column("period_from", sa.Date(), nullable=False),
        sa.Column("period_to", sa.Date(), nullable=False),
        sa.Column("confirmed_total_cents", sa.Integer(), nullable=False),
        sa.Column("owner_position_cents", sa.Integer(), nullable=False),
        # GROSS only; a NET document was already reduced by the landlord share.
        sa.Column("co2_kg_x1000", sa.BigInteger(), nullable=True),
        sa.Column("co2_cost_cents", sa.Integer(), nullable=True),
        sa.Column("heated_area_sqm_x100", sa.Integer(), nullable=True),
        sa.Column(
            "co2_evidence_present", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("source_ref", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "confirmed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["building_id", "account_id"],
            ["building.id", "building.account_id"],
            name="mdl_statement_building_id_fkey",
            match="SIMPLE",
        ),
        # Referenceable as a parent by mdl_statement_position's composite FK.
        sa.UniqueConstraint("id", "account_id", name="uq_mdl_statement_id_account"),
        sa.UniqueConstraint(
            "building_id",
            "period_from",
            "period_to",
            "version",
            name="uq_mdl_statement_building_period_version",
        ),
        sa.CheckConstraint(
            "confirmed_total_cents >= 0", name="ck_mdl_statement_total_non_negative"
        ),
        sa.CheckConstraint("owner_position_cents >= 0", name="ck_mdl_statement_owner_non_negative"),
        sa.CheckConstraint("version >= 1", name="ck_mdl_statement_version_positive"),
        sa.CheckConstraint("period_to > period_from", name="ck_mdl_statement_period_ordered"),
    )
    op.create_index("ix_mdl_statement_account", "mdl_statement", ["account_id"])
    op.create_index("ix_mdl_statement_building", "mdl_statement", ["building_id"])

    op.create_table(
        "mdl_statement_position",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("mdl_statement_id", sa.String(), nullable=False),
        sa.Column("tenancy_id", sa.String(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["mdl_statement_id", "account_id"],
            ["mdl_statement.id", "mdl_statement.account_id"],
            name="mdl_statement_position_mdl_statement_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["tenancy_id", "account_id"],
            ["tenancy.id", "tenancy.account_id"],
            name="mdl_statement_position_tenancy_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint(
            "mdl_statement_id", "tenancy_id", name="uq_mdl_position_statement_tenancy"
        ),
        sa.CheckConstraint("amount_cents >= 0", name="ck_mdl_position_non_negative"),
    )
    op.create_index("ix_mdl_position_account", "mdl_statement_position", ["account_id"])
    op.create_index("ix_mdl_position_statement", "mdl_statement_position", ["mdl_statement_id"])
    op.create_index("ix_mdl_position_tenancy", "mdl_statement_position", ["tenancy_id"])

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
    op.drop_table("mdl_statement_position")
    op.drop_table("mdl_statement")
    _MDL_BRANCH.drop(op.get_bind(), checkfirst=True)
