"""Temporal core + identity three-layer + RLS backstop (docs/02, MIGRATION-PLAN Appendix B).

Revision ID: 0001
Revises:
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ENUMS = {
    "account_shape": ("SOLO", "HAUSVERWALTUNG"),
    "plan": ("TRIAL", "SOLO_S", "SOLO_M", "SOLO_L", "TEAM", "PRO", "ENTERPRISE"),
    "role": ("OWNER", "EMPLOYEE", "TAX_ADVISOR"),  # no RENTER by design (docs/02)
    "statement_status": ("DRAFT", "FINALIZED", "SUPERSEDED"),
    "self_use_kind": ("OWNER_OCCUPIED", "FREE_OF_CHARGE"),
    # No column uses allocation_key yet — the per-period AllocationKeyAssignment
    # table arrives with the M3 plumbing. The type ships now so the enum is
    # versioned alongside the rest of the schema (parity with the Prisma M0).
    "allocation_key": ("AREA", "PERSONS", "CONSUMPTION", "UNITS", "DIRECT", "MEA"),
}

# Tables whose rows are scoped by their own account_id column.
_ACCOUNT_ID_TABLES = (
    "membership",
    "landlord",
    "renter",
    "building",
    "unit",
    "tenancy",
    "tenancy_party",
    "self_use_period",
    "statement",
)


def _enum(name: str) -> postgresql.ENUM:
    # create_type=False: types are created once, explicitly, at the top of upgrade().
    return postgresql.ENUM(*_ENUMS[name], name=name, create_type=False)


def _timestamp(name: str) -> sa.Column[object]:
    return sa.Column(
        name, sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )


def upgrade() -> None:
    bind = op.get_bind()
    for name, values in _ENUMS.items():
        postgresql.ENUM(*values, name=name).create(bind)

    # ── Identity ──────────────────────────────────────────────────────────────
    op.create_table(
        "person",  # global (Supabase Auth maps onto it) — deliberately NOT under RLS
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=True),
        _timestamp("created_at"),
    )
    op.create_table(
        "account",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("shape", _enum("account_shape"), nullable=False),
        sa.Column("plan", _enum("plan"), nullable=False),
        _timestamp("created_at"),
    )
    op.create_table(
        "membership",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("person_id", sa.String(), sa.ForeignKey("person.id"), nullable=False),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("role", _enum("role"), nullable=False),
        _timestamp("invited_at"),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("person_id", "account_id"),
    )
    op.create_index("ix_membership_account", "membership", ["account_id"])

    op.create_table(
        "landlord",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("legal_name", sa.String(), nullable=False),
        sa.Column("address", sa.String(), nullable=False),
    )
    op.create_index("ix_landlord_account", "landlord", ["account_id"])

    op.create_table(
        "renter",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("legal_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("person_id", sa.String(), sa.ForeignKey("person.id"), nullable=True),
    )
    op.create_index("ix_renter_account", "renter", ["account_id"])
    op.create_index("ix_renter_person", "renter", ["person_id"])

    # ── Temporal core ─────────────────────────────────────────────────────────
    op.create_table(
        "building",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("landlord_id", sa.String(), sa.ForeignKey("landlord.id"), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("street", sa.String(), nullable=False),
        sa.Column("postal_code", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=False),
        _timestamp("created_at"),
    )
    op.create_index("ix_building_account", "building", ["account_id"])

    op.create_table(
        "building_assignment",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "membership_id",
            sa.String(),
            sa.ForeignKey("membership.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("building_id", sa.String(), sa.ForeignKey("building.id"), nullable=False),
        sa.UniqueConstraint("membership_id", "building_id"),
    )

    op.create_table(
        "unit",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("building_id", sa.String(), sa.ForeignKey("building.id"), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("area_sqm_x100", sa.Integer(), nullable=False),
        _timestamp("created_at"),
    )
    op.create_index("ix_unit_account", "unit", ["account_id"])
    op.create_index("ix_unit_building", "unit", ["building_id"])

    op.create_table(
        "tenancy",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("unit_id", sa.String(), sa.ForeignKey("unit.id"), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),  # NULL = still running
        sa.Column("base_rent_cents", sa.Integer(), nullable=False),
        sa.Column("advance_payment_cents", sa.Integer(), nullable=False),
        _timestamp("created_at"),
    )
    op.create_index("ix_tenancy_account", "tenancy", ["account_id"])
    op.create_index("ix_tenancy_unit", "tenancy", ["unit_id"])

    op.create_table(
        "tenancy_party",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("tenancy_id", sa.String(), sa.ForeignKey("tenancy.id"), nullable=False),
        sa.Column("renter_id", sa.String(), sa.ForeignKey("renter.id"), nullable=False),
        sa.UniqueConstraint("tenancy_id", "renter_id"),
    )
    op.create_index("ix_tenancy_party_account", "tenancy_party", ["account_id"])

    op.create_table(
        "self_use_period",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("unit_id", sa.String(), sa.ForeignKey("unit.id"), nullable=False),
        sa.Column("sqm_x100", sa.Integer(), nullable=False),
        sa.Column("kind", _enum("self_use_kind"), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
    )
    op.create_index("ix_self_use_account", "self_use_period", ["account_id"])
    op.create_index("ix_self_use_unit", "self_use_period", ["unit_id"])

    op.create_table(
        "statement",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("building_id", sa.String(), sa.ForeignKey("building.id"), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", _enum("statement_status"), nullable=False),
        sa.Column("total_cents", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=True),
        _timestamp("created_at"),
        sa.UniqueConstraint("building_id", "period_start", "period_end", "version"),
    )
    op.create_index("ix_statement_account", "statement", ["account_id"])

    # ── Row-Level Security backstop (CLAUDE.md rule 3 / Appendix B) ───────────
    # The API sets `app.account_id` per transaction (set_config(..., true)).
    # current_setting(..., true) returns NULL when unset → matches nothing →
    # deny by default. FORCE binds the table owner too; runtime traffic uses
    # the non-owner `lokara_app` role because superusers always bypass RLS.
    for table in ("account", "building_assignment", *_ACCOUNT_ID_TABLES):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # The account row itself is scoped by its own id; all others by account_id.
    op.execute(
        """
        CREATE POLICY account_isolation ON account
        USING (id = current_setting('app.account_id', true))
        WITH CHECK (id = current_setting('app.account_id', true))
        """
    )
    for table in _ACCOUNT_ID_TABLES:
        op.execute(
            f"""
            CREATE POLICY {table}_isolation ON {table}
            USING (account_id = current_setting('app.account_id', true))
            WITH CHECK (account_id = current_setting('app.account_id', true))
            """
        )
    # building_assignment carries no account_id → scope via its membership.
    op.execute(
        """
        CREATE POLICY building_assignment_isolation ON building_assignment
        USING (EXISTS (SELECT 1 FROM membership m
                       WHERE m.id = building_assignment.membership_id
                         AND m.account_id = current_setting('app.account_id', true)))
        WITH CHECK (EXISTS (SELECT 1 FROM membership m
                            WHERE m.id = building_assignment.membership_id
                              AND m.account_id = current_setting('app.account_id', true)))
        """
    )


def downgrade() -> None:
    for table in (
        "statement",
        "self_use_period",
        "tenancy_party",
        "tenancy",
        "unit",
        "building_assignment",
        "building",
        "renter",
        "landlord",
        "membership",
        "account",
        "person",
    ):
        op.drop_table(table)  # policies drop with their tables
    bind = op.get_bind()
    for name, values in _ENUMS.items():
        postgresql.ENUM(*values, name=name).drop(bind)
