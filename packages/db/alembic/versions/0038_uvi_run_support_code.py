"""Store the renter-facing support code on each immutable UVI run."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("uvi_run", sa.Column("support_code", sa.String(32), nullable=True))
    op.create_unique_constraint(
        "uq_uvi_run_support_code", "uvi_run", ["account_id", "support_code"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_uvi_run_support_code", "uvi_run", type_="unique")
    op.drop_column("uvi_run", "support_code")
