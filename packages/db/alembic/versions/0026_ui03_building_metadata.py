"""UI-03 building metadata and optional map coordinates."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "building",
        sa.Column("building_type", sa.String(), server_default="WOHNHAUS", nullable=False),
    )
    op.add_column(
        "building",
        sa.Column("is_residential", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "building",
        sa.Column("country", sa.String(), server_default="Deutschland", nullable=False),
    )
    op.add_column("building", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("building", sa.Column("longitude", sa.Float(), nullable=True))
    op.create_check_constraint(
        "ck_building_type",
        "building",
        "building_type IN ('WOHN_UND_GESCHAEFTSHAUS', 'WOHNHAUS', "
        "'GEWERBEIMMOBILIE', 'EINFAMILIENHAUS')",
    )
    op.create_check_constraint(
        "ck_building_latitude_range",
        "building",
        "latitude BETWEEN -90 AND 90",
    )
    op.create_check_constraint(
        "ck_building_longitude_range",
        "building",
        "longitude BETWEEN -180 AND 180",
    )


def downgrade() -> None:
    op.drop_constraint("ck_building_longitude_range", "building", type_="check")
    op.drop_constraint("ck_building_latitude_range", "building", type_="check")
    op.drop_constraint("ck_building_type", "building", type_="check")
    op.drop_column("building", "longitude")
    op.drop_column("building", "latitude")
    op.drop_column("building", "country")
    op.drop_column("building", "is_residential")
    op.drop_column("building", "building_type")
