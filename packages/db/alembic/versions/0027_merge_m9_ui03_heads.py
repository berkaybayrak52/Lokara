"""Merge the M9 and UI-03 migration heads."""

from collections.abc import Sequence

revision = "0027"
down_revision = ("0025", "0026")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
