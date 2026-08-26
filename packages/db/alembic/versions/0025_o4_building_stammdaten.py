"""O4 (Spec 02-objekte): building type, residential flag, country and geo columns."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BUILDING_TYPES = (
    "WOHN_UND_GESCHAEFTSHAUS",
    "WOHNHAUS",
    "GEWERBEIMMOBILIE",
    "EINFAMILIENHAUS",
)
_CHECK_NAME = "ck_building_type_allowed"


def upgrade() -> None:
    # Non-geo columns are NOT NULL with a server_default so existing rows are
    # backfilled and ORM inserts that do not know the columns (e.g. the demo
    # seed) keep succeeding — the DB fills the default.
    op.add_column(
        "building",
        sa.Column(
            "building_type",
            sa.String(),
            nullable=False,
            server_default="WOHNHAUS",
        ),
    )
    op.add_column(
        "building",
        sa.Column(
            "is_residential",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "building",
        sa.Column(
            "country",
            sa.String(),
            nullable=False,
            server_default="Deutschland",
        ),
    )
    # Geo coordinates stay nullable (no default): geocoding is best-effort.
    op.add_column("building", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("building", sa.Column("longitude", sa.Float(), nullable=True))

    # VARCHAR + CHECK instead of a native PG enum, so the value set can grow
    # later without a fragile Alembic enum migration.
    allowed = ", ".join(f"'{value}'" for value in _BUILDING_TYPES)
    op.create_check_constraint(
        _CHECK_NAME,
        "building",
        f"building_type IN ({allowed})",
    )


def downgrade() -> None:
    op.drop_constraint(_CHECK_NAME, "building", type_="check")
    op.drop_column("building", "longitude")
    op.drop_column("building", "latitude")
    op.drop_column("building", "country")
    op.drop_column("building", "is_residential")
    op.drop_column("building", "building_type")
