"""Add the approved gas-volume meter and split gas conversion components."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL does not allow a newly added enum value to be used before the
    # transaction that added it commits. Keep this one DDL step in autocommit.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE meter_device_type ADD VALUE IF NOT EXISTS 'GAS_METER'")

    op.drop_constraint("ck_meter_device_type_facts", "meter", type_="check")
    op.create_check_constraint(
        "ck_meter_device_type_facts",
        "meter",
        "(device_type = 'HEAT_METER' AND kind = 'HEAT' AND measurement_unit = 'KWH') OR "
        "(device_type = 'HEAT_COST_ALLOCATOR' AND kind = 'HEAT' AND measurement_unit = 'HKV_UNITS') OR "  # noqa: E501
        "(device_type = 'WARM_WATER_METER' AND kind = 'WARM_WATER' AND measurement_unit = 'CUBIC_METRE') OR "  # noqa: E501
        "(device_type = 'COLD_WATER_METER' AND kind = 'COLD_WATER' AND measurement_unit = 'CUBIC_METRE') OR "  # noqa: E501
        "(device_type = 'GAS_METER' AND kind = 'HEAT' AND measurement_unit = 'CUBIC_METRE')",
    )

    op.add_column(
        "building_uvi_configuration",
        sa.Column("condition_number", sa.Numeric(12, 6), nullable=True),
    )
    # Historical rows retain their complete combined factor with no inferred
    # condition number. New split evidence may supply both positive components.
    op.create_check_constraint(
        "ck_building_uvi_configuration_conversion_components",
        "building_uvi_configuration",
        "(calorific_factor IS NULL AND condition_number IS NULL) OR "
        "(calorific_factor IS NOT NULL AND condition_number IS NULL AND "
        "calorific_factor NOT IN "
        "('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric) AND "
        "calorific_factor > 0) OR "
        "(calorific_factor IS NOT NULL AND condition_number IS NOT NULL AND "
        "calorific_factor NOT IN "
        "('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric) AND "
        "condition_number NOT IN "
        "('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric) AND "
        "calorific_factor > 0 AND condition_number > 0)",
    )


def downgrade() -> None:
    # Removing the enum member must never delete or silently remap a meter.
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM meter WHERE device_type = 'GAS_METER') THEN "
        "RAISE EXCEPTION 'cannot downgrade 0033 while GAS_METER rows exist' "
        "USING ERRCODE = '23514'; "
        "END IF; END $$"
    )

    op.drop_constraint("ck_meter_device_type_facts", "meter", type_="check")
    op.execute("ALTER TABLE meter ALTER COLUMN device_type TYPE text USING device_type::text")
    op.execute("DROP TYPE meter_device_type")
    op.execute(
        "CREATE TYPE meter_device_type AS ENUM "
        "('HEAT_METER', 'HEAT_COST_ALLOCATOR', 'WARM_WATER_METER', 'COLD_WATER_METER')"
    )
    op.execute(
        "ALTER TABLE meter ALTER COLUMN device_type TYPE meter_device_type "
        "USING device_type::meter_device_type"
    )
    op.create_check_constraint(
        "ck_meter_device_type_facts",
        "meter",
        "(device_type = 'HEAT_METER' AND kind = 'HEAT' AND measurement_unit = 'KWH') OR "
        "(device_type = 'HEAT_COST_ALLOCATOR' AND kind = 'HEAT' AND measurement_unit = 'HKV_UNITS') OR "  # noqa: E501
        "(device_type = 'WARM_WATER_METER' AND kind = 'WARM_WATER' AND measurement_unit = 'CUBIC_METRE') OR "  # noqa: E501
        "(device_type = 'COLD_WATER_METER' AND kind = 'COLD_WATER' AND measurement_unit = 'CUBIC_METRE')",  # noqa: E501
    )

    op.drop_constraint(
        "ck_building_uvi_configuration_conversion_components",
        "building_uvi_configuration",
        type_="check",
    )
    # Migration 0023 stored the combined factor. Fold the split components
    # together before returning to that schema.
    op.execute(
        "UPDATE building_uvi_configuration "
        "SET calorific_factor = calorific_factor * condition_number "
        "WHERE calorific_factor IS NOT NULL AND condition_number IS NOT NULL"
    )
    op.drop_column("building_uvi_configuration", "condition_number")
