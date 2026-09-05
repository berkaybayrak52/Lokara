"""Add the building-effective warm-water hot temperature for § 9 conversion."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "building_uvi_configuration",
        sa.Column("warm_water_hot_temp_c", sa.Numeric(8, 3), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("building_uvi_configuration", "warm_water_hot_temp_c")
