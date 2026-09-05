"""UI-08 meter lifecycle, calibration facts and heating source workflow."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0032"
down_revision = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

METER_DEVICE_TYPE = postgresql.ENUM(
    "HEAT_METER",
    "HEAT_COST_ALLOCATOR",
    "WARM_WATER_METER",
    "COLD_WATER_METER",
    name="meter_device_type",
    create_type=False,
)
REMOTE_READABILITY = postgresql.ENUM(
    "REMOTE_READABLE",
    "NOT_REMOTE_READABLE",
    "UNKNOWN",
    name="remote_readability",
    create_type=False,
)
CALIBRATION_DATA_STATE = postgresql.ENUM(
    "DATA_AVAILABLE",
    "MISSING_DATA",
    "NOT_APPLICABLE",
    "REVIEW_REQUIRED",
    name="calibration_data_state",
    create_type=False,
)
METER_LIFECYCLE_EVENT_TYPE = postgresql.ENUM(
    "INSTALLED",
    "REMOVED",
    "REPLACED",
    "VOID",
    name="meter_lifecycle_event_type",
    create_type=False,
)
HEATING_BILLING_MODE = postgresql.ENUM(
    "LOKARA",
    "EXTERNAL_PROVIDER",
    name="heating_billing_mode",
    create_type=False,
)
EXTERNAL_HEATING_STATUS = postgresql.ENUM(
    "BEAUFTRAGT",
    "DATEN_UEBERMITTELT",
    "ABRECHNUNG_ERHALTEN",
    "GEPRUEFT",
    "UEBERNOMMEN",
    name="external_heating_status",
    create_type=False,
)
HEATING_COST_CATEGORY = postgresql.ENUM(
    "FUEL_OR_HEAT_SUPPLY",
    "OPERATING_ELECTRICITY",
    "MAINTENANCE",
    "METERING_SERVICE",
    "OTHER_ALLOWED",
    name="heating_cost_category",
    create_type=False,
)


def _enable_rls(table: str) -> None:
    op.execute(
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY; "
        f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY; "
        f"CREATE POLICY {table}_isolation ON {table} "
        "USING (account_id = current_setting('app.account_id', true)) "
        "WITH CHECK (account_id = current_setting('app.account_id', true))"
    )


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (
        METER_DEVICE_TYPE,
        REMOTE_READABILITY,
        CALIBRATION_DATA_STATE,
        METER_LIFECYCLE_EVENT_TYPE,
        HEATING_BILLING_MODE,
        EXTERNAL_HEATING_STATUS,
        HEATING_COST_CATEGORY,
    ):
        enum_type.create(bind, checkfirst=True)

    op.add_column("meter", sa.Column("device_type", METER_DEVICE_TYPE, nullable=True))
    op.add_column("meter", sa.Column("location", sa.String(), nullable=True))
    op.add_column("meter", sa.Column("manufacturer", sa.String(), nullable=True))
    op.add_column("meter", sa.Column("model", sa.String(), nullable=True))
    op.add_column("meter", sa.Column("installed_on", sa.Date(), nullable=True))
    op.add_column(
        "meter",
        sa.Column(
            "remote_readability",
            REMOTE_READABILITY,
            nullable=False,
            server_default="UNKNOWN",
        ),
    )
    op.add_column(
        "meter", sa.Column("calibration_data_state", CALIBRATION_DATA_STATE, nullable=True)
    )
    op.add_column("meter", sa.Column("calibration_date", sa.Date(), nullable=True))
    op.add_column("meter", sa.Column("calibration_evidence_ref", sa.String(), nullable=True))
    op.execute(
        "UPDATE meter SET device_type = CASE "
        "WHEN kind = 'HEAT' AND measurement_unit = 'KWH' THEN 'HEAT_METER'::meter_device_type "
        "WHEN kind = 'HEAT' AND measurement_unit = 'HKV_UNITS' "
        "THEN 'HEAT_COST_ALLOCATOR'::meter_device_type "
        "WHEN kind = 'WARM_WATER' THEN 'WARM_WATER_METER'::meter_device_type "
        "ELSE 'COLD_WATER_METER'::meter_device_type END, "
        "installed_on = CASE "
        "WHEN account_id = 'acc_demo_lokara' AND id LIKE 'met_demo_%' "
        "THEN DATE '2021-01-01' "
        "ELSE COALESCE((SELECT min(mr.read_at) FROM meter_reading mr "
        "WHERE mr.meter_id = meter.id), created_at::date) END, "
        "calibration_data_state = CASE "
        "WHEN kind = 'HEAT' AND measurement_unit = 'HKV_UNITS' "
        "THEN 'NOT_APPLICABLE'::calibration_data_state "
        "WHEN calibration_valid_until IS NOT NULL THEN 'REVIEW_REQUIRED'::calibration_data_state "
        "ELSE 'MISSING_DATA'::calibration_data_state END"
    )
    op.alter_column("meter", "device_type", nullable=False)
    op.alter_column("meter", "installed_on", nullable=False)
    op.alter_column("meter", "calibration_data_state", nullable=False)
    op.create_check_constraint(
        "ck_meter_device_type_facts",
        "meter",
        "(device_type = 'HEAT_METER' AND kind = 'HEAT' AND measurement_unit = 'KWH') OR "
        "(device_type = 'HEAT_COST_ALLOCATOR' AND kind = 'HEAT' "
        "AND measurement_unit = 'HKV_UNITS') OR "
        "(device_type = 'WARM_WATER_METER' AND kind = 'WARM_WATER' "
        "AND measurement_unit = 'CUBIC_METRE') OR "
        "(device_type = 'COLD_WATER_METER' AND kind = 'COLD_WATER' "
        "AND measurement_unit = 'CUBIC_METRE')",
    )
    op.create_check_constraint(
        "ck_meter_calibration_facts",
        "meter",
        "(calibration_data_state = 'DATA_AVAILABLE' AND calibration_date IS NOT NULL "
        "AND calibration_evidence_ref IS NOT NULL) OR "
        "(calibration_data_state <> 'DATA_AVAILABLE' AND calibration_date IS NULL "
        "AND calibration_evidence_ref IS NULL)",
    )

    op.create_table(
        "meter_lifecycle_event",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("building_id", sa.String(), nullable=False),
        sa.Column("meter_id", sa.String(), nullable=False),
        sa.Column("event_type", METER_LIFECYCLE_EVENT_TYPE, nullable=False),
        sa.Column("effective_on", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("related_meter_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["building_id", "account_id"],
            ["building.id", "building.account_id"],
            name="meter_lifecycle_event_building_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["meter_id", "account_id", "building_id"],
            ["meter.id", "meter.account_id", "meter.building_id"],
            name="meter_lifecycle_event_meter_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["related_meter_id", "account_id", "building_id"],
            ["meter.id", "meter.account_id", "meter.building_id"],
            name="meter_lifecycle_event_related_meter_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_meter_lifecycle_event_id_account"),
        sa.CheckConstraint(
            "(event_type = 'INSTALLED' AND reason IS NULL) OR "
            "(event_type <> 'INSTALLED' AND btrim(reason) <> '')",
            name="ck_meter_lifecycle_reason",
        ),
        sa.CheckConstraint(
            "(event_type = 'REPLACED' AND related_meter_id IS NOT NULL) OR "
            "event_type <> 'REPLACED'",
            name="ck_meter_lifecycle_replacement_link",
        ),
        sa.CheckConstraint(
            "related_meter_id IS NULL OR related_meter_id <> meter_id",
            name="ck_meter_lifecycle_not_self_related",
        ),
    )
    op.create_index("ix_meter_lifecycle_event_account", "meter_lifecycle_event", ["account_id"])
    op.create_index(
        "ix_meter_lifecycle_event_meter",
        "meter_lifecycle_event",
        ["meter_id", "effective_on"],
    )
    op.create_index("ix_meter_lifecycle_event_building", "meter_lifecycle_event", ["building_id"])
    op.execute(
        "INSERT INTO meter_lifecycle_event "
        "(id, account_id, building_id, meter_id, event_type, effective_on, reason, created_at) "
        "SELECT 'mle_' || md5(id || '-installed'), account_id, building_id, id, "
        "'INSTALLED'::meter_lifecycle_event_type, installed_on, NULL, created_at FROM meter"
    )
    _enable_rls("meter_lifecycle_event")

    op.add_column("meter_reading", sa.Column("supersedes_reading_id", sa.String(), nullable=True))
    op.add_column("meter_reading", sa.Column("confirmation_note", sa.String(), nullable=True))
    op.create_foreign_key(
        "meter_reading_supersedes_reading_id_fkey",
        "meter_reading",
        "meter_reading",
        ["supersedes_reading_id", "account_id", "meter_id"],
        ["id", "account_id", "meter_id"],
        match="SIMPLE",
    )
    op.create_unique_constraint(
        "uq_meter_reading_direct_successor", "meter_reading", ["supersedes_reading_id"]
    )
    op.create_check_constraint(
        "ck_meter_reading_correction_link",
        "meter_reading",
        "supersedes_reading_id IS NULL OR "
        "(reason = 'CORRECTION' AND btrim(confirmation_note) <> '')",
    )

    op.add_column(
        "heating_cost_entry",
        sa.Column(
            "category",
            HEATING_COST_CATEGORY,
            nullable=False,
            server_default="OTHER_ALLOWED",
        ),
    )
    op.add_column("heating_cost_entry", sa.Column("source_ref", sa.String(), nullable=True))
    op.add_column(
        "heating_cost_entry", sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("heating_cost_entry", sa.Column("void_reason", sa.String(), nullable=True))
    op.create_check_constraint(
        "ck_heating_cost_void_reason",
        "heating_cost_entry",
        "(voided_at IS NULL AND void_reason IS NULL) OR "
        "(voided_at IS NOT NULL AND btrim(void_reason) <> '')",
    )

    op.create_table(
        "heating_billing_mode_version",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("building_id", sa.String(), nullable=False),
        sa.Column("period_from", sa.Date(), nullable=False),
        sa.Column("period_to", sa.Date(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("mode", HEATING_BILLING_MODE, nullable=False),
        sa.Column("provider_name", sa.String(), nullable=True),
        sa.Column("provider_reference", sa.String(), nullable=True),
        sa.Column("external_status", EXTERNAL_HEATING_STATUS, nullable=True),
        sa.Column("mdl_statement_id", sa.String(), nullable=True),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["building_id", "account_id"],
            ["building.id", "building.account_id"],
            name="heating_billing_mode_version_building_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["mdl_statement_id", "account_id"],
            ["mdl_statement.id", "mdl_statement.account_id"],
            name="heating_billing_mode_version_mdl_statement_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_heating_billing_mode_version_id_account"),
        sa.UniqueConstraint(
            "building_id",
            "period_from",
            "period_to",
            "version",
            name="uq_heating_billing_mode_period_version",
        ),
        sa.CheckConstraint("period_to > period_from", name="ck_heating_billing_mode_period"),
        sa.CheckConstraint("version >= 1", name="ck_heating_billing_mode_version"),
        sa.CheckConstraint(
            "(mode = 'LOKARA' AND provider_name IS NULL AND external_status IS NULL "
            "AND mdl_statement_id IS NULL) OR "
            "(mode = 'EXTERNAL_PROVIDER' AND btrim(provider_name) <> '' "
            "AND external_status IS NOT NULL)",
            name="ck_heating_billing_mode_shape",
        ),
        sa.CheckConstraint(
            "external_status <> 'UEBERNOMMEN' OR mdl_statement_id IS NOT NULL",
            name="ck_heating_billing_mode_adopted_statement",
        ),
    )
    op.create_index(
        "ix_heating_billing_mode_account", "heating_billing_mode_version", ["account_id"]
    )
    op.create_index(
        "ix_heating_billing_mode_building_period",
        "heating_billing_mode_version",
        ["building_id", "period_from", "period_to"],
    )
    _enable_rls("heating_billing_mode_version")

    op.execute(
        "CREATE FUNCTION prevent_ui08_append_only_rewrite() RETURNS trigger AS $$ "
        "BEGIN RAISE EXCEPTION 'UI-08 evidence is append-only'; END; "
        "$$ LANGUAGE plpgsql"
    )
    for table in ("meter_lifecycle_event", "heating_billing_mode_version"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION prevent_ui08_append_only_rewrite()"
        )
    op.execute("DROP TRIGGER IF EXISTS meter_reading_append_only ON meter_reading")
    op.execute(
        "CREATE TRIGGER meter_reading_append_only BEFORE UPDATE OR DELETE ON meter_reading "
        "FOR EACH ROW EXECUTE FUNCTION prevent_ui08_append_only_rewrite()"
    )
    op.execute(
        "CREATE FUNCTION validate_ui08_heating_mode_statement() RETURNS trigger AS $$ "
        "BEGIN IF NEW.mdl_statement_id IS NOT NULL AND NOT EXISTS ("
        "SELECT 1 FROM mdl_statement s WHERE s.id = NEW.mdl_statement_id "
        "AND s.account_id = NEW.account_id AND s.building_id = NEW.building_id "
        "AND s.period_from = NEW.period_from AND s.period_to = NEW.period_to) THEN "
        "RAISE EXCEPTION 'MDL statement does not match heating mode context'; END IF; "
        "RETURN NEW; END; $$ LANGUAGE plpgsql"
    )
    op.execute(
        "CREATE TRIGGER heating_billing_mode_statement_guard BEFORE INSERT "
        "ON heating_billing_mode_version FOR EACH ROW "
        "EXECUTE FUNCTION validate_ui08_heating_mode_statement()"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS heating_billing_mode_statement_guard "
        "ON heating_billing_mode_version"
    )
    op.execute("DROP FUNCTION IF EXISTS validate_ui08_heating_mode_statement()")
    op.execute("DROP TRIGGER IF EXISTS meter_reading_append_only ON meter_reading")
    for table in ("heating_billing_mode_version", "meter_lifecycle_event"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_append_only ON {table}")
    op.execute("DROP FUNCTION IF EXISTS prevent_ui08_append_only_rewrite()")
    op.execute(
        "CREATE TRIGGER meter_reading_append_only BEFORE UPDATE OR DELETE ON meter_reading "
        "FOR EACH ROW EXECUTE FUNCTION prevent_linked_meter_reading_rewrite_u4()"
    )
    op.drop_table("heating_billing_mode_version")
    op.drop_constraint("ck_heating_cost_void_reason", "heating_cost_entry", type_="check")
    for column in ("void_reason", "voided_at", "source_ref", "category"):
        op.drop_column("heating_cost_entry", column)
    op.drop_constraint("ck_meter_reading_correction_link", "meter_reading", type_="check")
    op.drop_constraint("uq_meter_reading_direct_successor", "meter_reading", type_="unique")
    op.drop_constraint(
        "meter_reading_supersedes_reading_id_fkey", "meter_reading", type_="foreignkey"
    )
    op.drop_column("meter_reading", "confirmation_note")
    op.drop_column("meter_reading", "supersedes_reading_id")
    op.drop_table("meter_lifecycle_event")
    op.drop_constraint("ck_meter_calibration_facts", "meter", type_="check")
    op.drop_constraint("ck_meter_device_type_facts", "meter", type_="check")
    op.drop_column("meter", "location", if_exists=True)
    for column in (
        "calibration_evidence_ref",
        "calibration_date",
        "calibration_data_state",
        "remote_readability",
        "installed_on",
        "model",
        "manufacturer",
        "device_type",
    ):
        op.drop_column("meter", column)
    bind = op.get_bind()
    for enum_type in reversed(
        (
            METER_DEVICE_TYPE,
            REMOTE_READABILITY,
            CALIBRATION_DATA_STATE,
            METER_LIFECYCLE_EVENT_TYPE,
            HEATING_BILLING_MODE,
            EXTERNAL_HEATING_STATUS,
            HEATING_COST_CATEGORY,
        )
    ):
        enum_type.drop(bind, checkfirst=True)
