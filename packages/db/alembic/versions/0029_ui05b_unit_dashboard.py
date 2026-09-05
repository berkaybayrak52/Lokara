"""UI-05B temporal unit and tenancy dashboard facts."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0029"
down_revision = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _enable_rls(table: str) -> None:
    op.execute(
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY; "
        f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY; "
        f"CREATE POLICY {table}_isolation ON {table} "
        "USING (account_id = current_setting('app.account_id', true)) "
        "WITH CHECK (account_id = current_setting('app.account_id', true))"
    )


def _account_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "unit_profile_version",
        *_account_columns(),
        sa.Column("unit_id", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("usage_type", sa.String(), nullable=False),
        sa.Column("rooms_x100", sa.Integer(), nullable=True),
        sa.Column(
            "amenities",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("amenity_note", sa.String(), nullable=True),
        sa.Column("evidence_ref", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["unit_id", "account_id"],
            ["unit.id", "unit.account_id"],
            name="unit_profile_version_unit_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_unit_profile_version_id_account"),
        sa.UniqueConstraint("unit_id", "version", name="uq_unit_profile_version_unit_version"),
        sa.CheckConstraint("version >= 1", name="ck_unit_profile_version_version"),
        sa.CheckConstraint(
            "usage_type IN ('RESIDENTIAL', 'COMMERCIAL', 'OTHER')",
            name="ck_unit_profile_version_usage_type",
        ),
        sa.CheckConstraint(
            "rooms_x100 IS NULL OR rooms_x100 >= 0",
            name="ck_unit_profile_version_rooms_non_negative",
        ),
    )
    op.create_index("ix_unit_profile_version_account", "unit_profile_version", ["account_id"])
    op.create_index(
        "ix_unit_profile_version_unit",
        "unit_profile_version",
        ["unit_id", "effective_from"],
    )

    op.create_table(
        "tenancy_contract_version",
        *_account_columns(),
        sa.Column("tenancy_id", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("contract_type", sa.String(), nullable=False),
        sa.Column("evidence_ref", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenancy_id", "account_id"],
            ["tenancy.id", "tenancy.account_id"],
            name="tenancy_contract_version_tenancy_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_tenancy_contract_version_id_account"),
        sa.UniqueConstraint(
            "tenancy_id", "version", name="uq_tenancy_contract_version_tenancy_version"
        ),
        sa.CheckConstraint("version >= 1", name="ck_tenancy_contract_version_version"),
        sa.CheckConstraint(
            "contract_type IN ('RESIDENTIAL_OPEN_ENDED', 'RESIDENTIAL_FIXED_TERM', "
            "'COMMERCIAL_OPEN_ENDED', 'COMMERCIAL_FIXED_TERM', 'OTHER')",
            name="ck_tenancy_contract_version_contract_type",
        ),
    )
    op.create_index(
        "ix_tenancy_contract_version_account", "tenancy_contract_version", ["account_id"]
    )
    op.create_index(
        "ix_tenancy_contract_version_tenancy",
        "tenancy_contract_version",
        ["tenancy_id", "effective_from"],
    )

    op.create_table(
        "tenancy_contract_position",
        *_account_columns(),
        sa.Column("tenancy_id", sa.String(), nullable=False),
        sa.Column("position_type", sa.String(), nullable=False),
        sa.Column("inclusion_type", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("monthly_amount_cents", sa.Integer(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("evidence_ref", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenancy_id", "account_id"],
            ["tenancy.id", "tenancy.account_id"],
            name="tenancy_contract_position_tenancy_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_tenancy_contract_position_id_account"),
        sa.CheckConstraint(
            "position_type IN ('GARAGE', 'PARKING')",
            name="ck_tenancy_contract_position_type",
        ),
        sa.CheckConstraint(
            "inclusion_type IN ('INCLUDED', 'SEPARATE')",
            name="ck_tenancy_contract_position_inclusion",
        ),
        sa.CheckConstraint(
            "monthly_amount_cents IS NULL OR monthly_amount_cents >= 0",
            name="ck_tenancy_contract_position_amount",
        ),
        sa.CheckConstraint(
            "inclusion_type = 'INCLUDED' OR monthly_amount_cents IS NOT NULL",
            name="ck_tenancy_contract_position_separate_amount",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="ck_tenancy_contract_position_period",
        ),
    )
    op.create_index(
        "ix_tenancy_contract_position_account",
        "tenancy_contract_position",
        ["account_id"],
    )
    op.create_index(
        "ix_tenancy_contract_position_tenancy",
        "tenancy_contract_position",
        ["tenancy_id", "valid_from"],
    )

    op.create_table(
        "tenancy_rent_change",
        *_account_columns(),
        sa.Column("tenancy_id", sa.String(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("new_base_rent_cents", sa.Integer(), nullable=False),
        sa.Column("evidence_ref", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenancy_id", "account_id"],
            ["tenancy.id", "tenancy.account_id"],
            name="tenancy_rent_change_tenancy_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_tenancy_rent_change_id_account"),
        sa.UniqueConstraint(
            "tenancy_id", "effective_from", name="uq_tenancy_rent_change_effective"
        ),
        sa.CheckConstraint("new_base_rent_cents >= 0", name="ck_tenancy_rent_change_non_negative"),
    )
    op.create_index("ix_tenancy_rent_change_account", "tenancy_rent_change", ["account_id"])
    op.create_index(
        "ix_tenancy_rent_change_tenancy",
        "tenancy_rent_change",
        ["tenancy_id", "effective_from"],
    )

    for table in (
        "unit_profile_version",
        "tenancy_contract_version",
        "tenancy_contract_position",
        "tenancy_rent_change",
    ):
        _enable_rls(table)

    op.execute(
        "CREATE FUNCTION prevent_ui05b_rewrite() RETURNS trigger AS $$ "
        "BEGIN RAISE EXCEPTION 'UI-05B temporal rows are append-only'; END; "
        "$$ LANGUAGE plpgsql"
    )
    for table in (
        "unit_profile_version",
        "tenancy_contract_version",
        "tenancy_contract_position",
        "tenancy_rent_change",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_append_only "
            f"BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION prevent_ui05b_rewrite()"
        )


def downgrade() -> None:
    for table in (
        "tenancy_rent_change",
        "tenancy_contract_position",
        "tenancy_contract_version",
        "unit_profile_version",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_append_only ON {table}")
        op.drop_table(table)
    op.execute("DROP FUNCTION prevent_ui05b_rewrite()")
