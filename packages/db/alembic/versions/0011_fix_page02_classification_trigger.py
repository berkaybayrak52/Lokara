"""Make confirmed Page-02 classifications fully append-only.

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS confirmed_cost_classification_append_only "
        "ON confirmed_cost_classification"
    )
    op.execute(
        "CREATE TRIGGER confirmed_cost_classification_append_only "
        "BEFORE UPDATE OR DELETE ON confirmed_cost_classification FOR EACH ROW "
        "EXECUTE FUNCTION prevent_confirmed_cost_classification_rewrite()"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER confirmed_cost_classification_append_only ON confirmed_cost_classification"
    )
    op.execute(
        "CREATE TRIGGER confirmed_cost_classification_append_only "
        "BEFORE UPDATE ON confirmed_cost_classification FOR EACH ROW "
        "EXECUTE FUNCTION prevent_confirmed_cost_classification_rewrite()"
    )
