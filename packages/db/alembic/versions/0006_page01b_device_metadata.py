"""Page 01b device factor, tenant segments, estimates and provenance.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("meter", sa.Column("valuation_factor_x1000", sa.BigInteger(), nullable=True))
    # Exact 1.000 backfill for every existing heat device.  Water meters stay
    # NULL because they never enter H5 valuation.
    op.execute("UPDATE meter SET valuation_factor_x1000 = 1000 WHERE kind = 'HEAT'")
    op.create_check_constraint(
        "ck_meter_heat_valuation_factor",
        "meter",
        "(kind = 'HEAT' AND valuation_factor_x1000 IS NOT NULL "
        "AND valuation_factor_x1000 > 0) OR "
        "(kind <> 'HEAT' AND valuation_factor_x1000 IS NULL)",
    )

    op.add_column("meter_reading", sa.Column("tenancy_id", sa.String(), nullable=True))
    op.add_column(
        "meter_reading",
        sa.Column("estimated_consumption_x1000", sa.BigInteger(), nullable=True),
    )
    op.add_column("meter_reading", sa.Column("estimation_basis", sa.String(), nullable=True))
    op.add_column("meter_reading", sa.Column("provenance_ref", sa.String(), nullable=True))
    op.create_foreign_key(
        "meter_reading_tenancy_id_fkey",
        "meter_reading",
        "tenancy",
        ["tenancy_id", "account_id"],
        ["id", "account_id"],
        match="SIMPLE",
    )
    op.create_check_constraint(
        "ck_meter_reading_estimate_basis",
        "meter_reading",
        "(estimated_consumption_x1000 IS NULL AND estimation_basis IS NULL) OR "
        "(estimated_consumption_x1000 IS NOT NULL AND estimated_consumption_x1000 >= 0 "
        "AND estimation_basis IS NOT NULL)",
    )
    op.create_index("ix_meter_reading_tenancy", "meter_reading", ["tenancy_id"])


def downgrade() -> None:
    op.drop_index("ix_meter_reading_tenancy", table_name="meter_reading")
    op.drop_constraint("ck_meter_reading_estimate_basis", "meter_reading", type_="check")
    op.drop_constraint("meter_reading_tenancy_id_fkey", "meter_reading", type_="foreignkey")
    op.drop_column("meter_reading", "provenance_ref")
    op.drop_column("meter_reading", "estimation_basis")
    op.drop_column("meter_reading", "estimated_consumption_x1000")
    op.drop_column("meter_reading", "tenancy_id")
    op.drop_constraint("ck_meter_heat_valuation_factor", "meter", type_="check")
    op.drop_column("meter", "valuation_factor_x1000")
