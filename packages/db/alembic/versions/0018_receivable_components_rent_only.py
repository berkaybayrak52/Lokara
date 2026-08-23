"""Limit the receivable component-sum check to rent, where the components exist."""

from collections.abc import Sequence

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 0017 required base_rent + nk_advance + heating_advance + garage = expected_cents
# for every receivable, following docs/15 § 3.2's "the nominal components sum to
# expected_cents". That reading is right for a `rent` receivable and wrong for the
# other category the same section defines.
#
# An `nk_nachzahlung` is the settled Saldo of a finalized Page 01 statement. It has
# no rent, no garage and — decisively — no advance: § 5.2 says the paid NK-advance
# component feeds the annual actual-advance total Page 01 consumes. Parking a
# Nachzahlung in `nk_advance_cents` to satisfy an arithmetic check would feed the
# next statement an advance that was never paid as one, double-counting it. The
# figure would be internally consistent and wrong, which is the class of defect a
# green test suite cannot see.
#
# docs/15 gives no component split for `nk_nachzahlung` (`F12` states only the
# 24,500 cents), so none is invented here: the four components are zero and the
# check no longer claims otherwise.
_OLD = "base_rent_cents + nk_advance_cents + heating_advance_cents + garage_cents = expected_cents"
_NEW = f"category <> 'rent' OR ({_OLD})"


def upgrade() -> None:
    op.drop_constraint("ck_receivable_components_sum", "receivable", type_="check")
    op.create_check_constraint("ck_receivable_components_sum", "receivable", _NEW)


def downgrade() -> None:
    op.drop_constraint("ck_receivable_components_sum", "receivable", type_="check")
    op.create_check_constraint("ck_receivable_components_sum", "receivable", _OLD)
