"""Persist the PLZ centroid dataset identity on station assignments."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "uvi_station_assignment",
        sa.Column("centroid_dataset_identity", sa.String(), nullable=True),
    )
    op.add_column(
        "uvi_station_assignment",
        sa.Column("centroid_dataset_version", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("uvi_station_assignment", "centroid_dataset_version")
    op.drop_column("uvi_station_assignment", "centroid_dataset_identity")
