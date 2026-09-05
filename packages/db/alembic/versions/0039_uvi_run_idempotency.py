"""Make UVI generation idempotent and reserve one email claim per run."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0039"
down_revision = "0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_uvi_run_tenancy_month",
        "uvi_run",
        ["account_id", "tenancy_id", "month"],
    )
    op.create_index(
        "uq_uvi_delivery_event_emailed_once",
        "uvi_delivery_event",
        ["account_id", "uvi_run_id"],
        unique=True,
        postgresql_where=sa.text("status = 'EMAILED'"),
    )


def downgrade() -> None:
    op.drop_index("uq_uvi_delivery_event_emailed_once", table_name="uvi_delivery_event")
    op.drop_constraint("uq_uvi_run_tenancy_month", "uvi_run", type_="unique")
