"""Personenschlüssel: person_count rows + the object's Fiktivbelegung mode.

`person_count` is the Personenzahl as history, not a scalar on the unit: the
count changes inside a billing period, and a current-value column would silently
rewrite an already-issued Abrechnung (docs/02 § 4 temporal rule).

The D0 Fiktivbelegung of a vacant unit is **not** stored here. It is derived per
run from the last ended tenancy of that unit plus `building.fiktivbelegung_mode`
(Page 01 § 4 D0, docs/02 § 5). It is a flagged convention applied at calculation
time, not observed data, so storing it would make it look entered and freeze it
against the pending legal review.

`fiktivbelegung_mode = KEINE` is lawful only with a logged confirmation
(Page 01 E18), so the mode and its waiver note travel under one CHECK.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FIKTIVBELEGUNG_MODE = sa.Enum(
    "LETZTE_BELEGUNG",
    "IMMER_1",
    "KEINE",
    name="fiktivbelegung_mode",
)


def upgrade() -> None:
    op.create_table(
        "person_count",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("tenancy_id", sa.String(), nullable=False),
        # Zero is a real entered count; a negative one is not a Personenzahl.
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        # NULL = still running, half-open like every other temporal row.
        sa.Column("valid_to", sa.Date(), nullable=True),
        # Composite from the start: a single-column FK would be a cross-account
        # hole that check_fk_isolation.py rejects (0004 had to repair 0002/0003).
        sa.ForeignKeyConstraint(
            ["tenancy_id", "account_id"],
            ["tenancy.id", "tenancy.account_id"],
            name="person_count_tenancy_id_fkey",
            match="SIMPLE",
        ),
        sa.CheckConstraint("count >= 0", name="ck_person_count_non_negative"),
    )
    op.create_index("ix_person_count_account", "person_count", ["account_id"])
    op.create_index("ix_person_count_tenancy", "person_count", ["tenancy_id"])

    op.execute("ALTER TABLE person_count ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE person_count FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY person_count_isolation ON person_count
        USING (account_id = current_setting('app.account_id', true))
        WITH CHECK (account_id = current_setting('app.account_id', true))
        """
    )

    _FIKTIVBELEGUNG_MODE.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "building",
        sa.Column(
            "fiktivbelegung_mode",
            _FIKTIVBELEGUNG_MODE,
            nullable=False,
            # Page 01 § 3.5 default. Existing buildings inherit it, which is the
            # documented behaviour rather than a migration convenience.
            server_default="LETZTE_BELEGUNG",
        ),
    )
    op.add_column("building", sa.Column("fiktivbelegung_waiver_note", sa.String(), nullable=True))
    op.create_check_constraint(
        "ck_building_fiktivbelegung_waiver_logged",
        "building",
        "fiktivbelegung_mode <> 'KEINE' OR fiktivbelegung_waiver_note IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_building_fiktivbelegung_waiver_logged", "building", type_="check")
    op.drop_column("building", "fiktivbelegung_waiver_note")
    op.drop_column("building", "fiktivbelegung_mode")
    _FIKTIVBELEGUNG_MODE.drop(op.get_bind(), checkfirst=True)
    # The policy and the RLS flags die with the table.
    op.drop_table("person_count")
