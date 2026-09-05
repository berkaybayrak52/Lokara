"""Add account/landlord contact fields used by the frozen UVI letter header."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0037"
down_revision = "0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("landlord", sa.Column("phone", sa.String(), nullable=True))
    op.add_column("landlord", sa.Column("email", sa.String(), nullable=True))
    op.add_column("landlord", sa.Column("logo", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("landlord", "logo")
    op.drop_column("landlord", "email")
    op.drop_column("landlord", "phone")
