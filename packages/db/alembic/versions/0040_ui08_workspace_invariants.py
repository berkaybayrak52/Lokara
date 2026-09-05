"""Enforce UI-08 immutable evidence and complete lifecycle metadata."""

from collections.abc import Sequence

from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_meter_lifecycle_reason",
        "meter_lifecycle_event",
        type_="check",
    )
    op.create_check_constraint(
        "ck_meter_lifecycle_reason",
        "meter_lifecycle_event",
        "(event_type = 'INSTALLED' AND reason IS NULL) OR "
        "(event_type <> 'INSTALLED' AND reason IS NOT NULL AND btrim(reason) <> '')",
    )

    op.drop_constraint(
        "ck_meter_reading_correction_link",
        "meter_reading",
        type_="check",
    )
    op.create_check_constraint(
        "ck_meter_reading_correction_link",
        "meter_reading",
        "supersedes_reading_id IS NULL OR "
        "(reason = 'CORRECTION' AND confirmation_note IS NOT NULL "
        "AND btrim(confirmation_note) <> '')",
    )

    op.drop_constraint(
        "ck_heating_cost_void_reason",
        "heating_cost_entry",
        type_="check",
    )
    op.create_check_constraint(
        "ck_heating_cost_void_reason",
        "heating_cost_entry",
        "(voided_at IS NULL AND void_reason IS NULL) OR "
        "(voided_at IS NOT NULL AND void_reason IS NOT NULL AND btrim(void_reason) <> '')",
    )

    op.drop_constraint(
        "ck_heating_billing_mode_shape",
        "heating_billing_mode_version",
        type_="check",
    )
    op.create_check_constraint(
        "ck_heating_billing_mode_shape",
        "heating_billing_mode_version",
        "(mode = 'LOKARA' AND provider_name IS NULL AND provider_reference IS NULL "
        "AND external_status IS NULL AND mdl_statement_id IS NULL) OR "
        "(mode = 'EXTERNAL_PROVIDER' AND provider_name IS NOT NULL "
        "AND btrim(provider_name) <> '' AND external_status IS NOT NULL)",
    )

    op.execute(
        "CREATE FUNCTION enforce_heating_cost_entry_immutability_ui08() RETURNS trigger AS $$ "
        "BEGIN "
        "IF TG_OP = 'DELETE' THEN "
        "RAISE EXCEPTION 'heating cost evidence is append-only' USING ERRCODE = '23514'; "
        "END IF; "
        "IF OLD.voided_at IS NULL AND OLD.void_reason IS NULL "
        "AND NEW.voided_at IS NOT NULL AND NEW.void_reason IS NOT NULL "
        "AND btrim(NEW.void_reason) <> '' "
        "AND (to_jsonb(NEW) - 'voided_at' - 'void_reason') "
        "IS NOT DISTINCT FROM (to_jsonb(OLD) - 'voided_at' - 'void_reason') THEN "
        "RETURN NEW; "
        "END IF; "
        "RAISE EXCEPTION 'heating cost evidence is append-only except for its first void' "
        "USING ERRCODE = '23514'; "
        "END; $$ LANGUAGE plpgsql"
    )
    op.execute(
        "CREATE TRIGGER heating_cost_entry_immutable_except_void "
        "BEFORE UPDATE OR DELETE ON heating_cost_entry FOR EACH ROW "
        "EXECUTE FUNCTION enforce_heating_cost_entry_immutability_ui08()"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS heating_cost_entry_immutable_except_void ON heating_cost_entry"
    )
    op.execute("DROP FUNCTION IF EXISTS enforce_heating_cost_entry_immutability_ui08()")

    op.drop_constraint(
        "ck_heating_billing_mode_shape",
        "heating_billing_mode_version",
        type_="check",
    )
    op.create_check_constraint(
        "ck_heating_billing_mode_shape",
        "heating_billing_mode_version",
        "(mode = 'LOKARA' AND provider_name IS NULL AND external_status IS NULL "
        "AND mdl_statement_id IS NULL) OR "
        "(mode = 'EXTERNAL_PROVIDER' AND btrim(provider_name) <> '' "
        "AND external_status IS NOT NULL)",
    )

    op.drop_constraint(
        "ck_heating_cost_void_reason",
        "heating_cost_entry",
        type_="check",
    )
    op.create_check_constraint(
        "ck_heating_cost_void_reason",
        "heating_cost_entry",
        "(voided_at IS NULL AND void_reason IS NULL) OR "
        "(voided_at IS NOT NULL AND btrim(void_reason) <> '')",
    )

    op.drop_constraint(
        "ck_meter_reading_correction_link",
        "meter_reading",
        type_="check",
    )
    op.create_check_constraint(
        "ck_meter_reading_correction_link",
        "meter_reading",
        "supersedes_reading_id IS NULL OR "
        "(reason = 'CORRECTION' AND btrim(confirmation_note) <> '')",
    )

    op.drop_constraint(
        "ck_meter_lifecycle_reason",
        "meter_lifecycle_event",
        type_="check",
    )
    op.create_check_constraint(
        "ck_meter_lifecycle_reason",
        "meter_lifecycle_event",
        "(event_type = 'INSTALLED' AND reason IS NULL) OR "
        "(event_type <> 'INSTALLED' AND btrim(reason) <> '')",
    )
