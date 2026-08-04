"""Zähler: meter + meter_reading (create-only) + heating_cost_entry.

meter_reading is append-only by contract, not by trigger: a correction is a new
row with reason=CORRECTION and a later recorded_at, which supersedes the earlier
value for the same read_at. Nothing in the app issues UPDATE or DELETE on it.

All three tables get the same FORCEd RLS backstop as every tenant table.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("meter", "meter_reading", "heating_cost_entry")

_METER_KIND = sa.Enum("HEAT", "WARM_WATER", "COLD_WATER", name="meter_kind")
_MEASUREMENT_UNIT = sa.Enum("KWH", "CUBIC_METRE", "HKV_UNITS", name="measurement_unit")
_READING_REASON = sa.Enum(
    "PERIODIC",
    "INTERIM",
    "TENANT_CHANGE",
    "DEVICE_CHANGE",
    "CORRECTION",
    name="reading_reason",
)
_READING_SOURCE = sa.Enum("MANUAL", "MDL", "RADIO", name="reading_source")


def _timestamp(name: str) -> sa.Column[sa.types.DateTime]:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


def upgrade() -> None:
    op.create_table(
        "meter",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("building_id", sa.String(), sa.ForeignKey("building.id"), nullable=False),
        # NULL = building-level Hauptzähler (measures the whole system).
        sa.Column("unit_id", sa.String(), sa.ForeignKey("unit.id"), nullable=True),
        sa.Column("kind", _METER_KIND, nullable=False),
        sa.Column("measurement_unit", _MEASUREMENT_UNIT, nullable=False),
        sa.Column("serial", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=True),
        # Eichfrist; NULL = not eichpflichtig (Heizkostenverteiler).
        sa.Column("calibration_valid_until", sa.Date(), nullable=True),
        _timestamp("created_at"),
        sa.UniqueConstraint("building_id", "serial"),
    )
    op.create_index("ix_meter_account", "meter", ["account_id"])
    op.create_index("ix_meter_building", "meter", ["building_id"])
    op.create_index("ix_meter_unit", "meter", ["unit_id"])

    op.create_table(
        "meter_reading",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("meter_id", sa.String(), sa.ForeignKey("meter.id"), nullable=False),
        sa.Column("read_at", sa.Date(), nullable=False),
        # Register value × 1000 — fixed point, never a float.
        sa.Column("value_x1000", sa.BigInteger(), nullable=False),
        sa.Column("reason", _READING_REASON, nullable=False),
        sa.Column("source", _READING_SOURCE, nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        # Ordering axis for supersession: latest recorded_at per read_at wins.
        _timestamp("recorded_at"),
    )
    op.create_index("ix_meter_reading_account", "meter_reading", ["account_id"])
    op.create_index("ix_meter_reading_meter", "meter_reading", ["meter_id"])

    op.create_table(
        "heating_cost_entry",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("building_id", sa.String(), sa.ForeignKey("building.id"), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("period_from", sa.Date(), nullable=False),
        sa.Column("period_to", sa.Date(), nullable=False),  # exclusive
        # Off the fuel invoice (mandatory since 2023); NULL when not stated.
        sa.Column("co2_kg_x1000", sa.BigInteger(), nullable=True),
        sa.Column("co2_cost_cents", sa.Integer(), nullable=True),
        _timestamp("created_at"),
    )
    op.create_index("ix_heating_cost_account", "heating_cost_entry", ["account_id"])
    op.create_index("ix_heating_cost_building", "heating_cost_entry", ["building_id"])

    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_isolation ON {table}
            USING (account_id = current_setting('app.account_id', true))
            WITH CHECK (account_id = current_setting('app.account_id', true))
            """
        )


def downgrade() -> None:
    op.drop_table("heating_cost_entry")
    op.drop_table("meter_reading")
    op.drop_table("meter")
    bind = op.get_bind()
    for enum_type in (_READING_SOURCE, _READING_REASON, _MEASUREMENT_UNIT, _METER_KIND):
        enum_type.drop(bind, checkfirst=True)
