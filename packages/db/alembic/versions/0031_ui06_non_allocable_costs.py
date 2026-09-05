"""UI-06 permits documented costs without an allocation key."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "confirmed_cost_classification",
        "allocation_key_assignment_id",
        existing_type=sa.Text(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "confirmed_cost_classification",
        "allocation_key_assignment_id",
        existing_type=sa.Text(),
        nullable=False,
    )
