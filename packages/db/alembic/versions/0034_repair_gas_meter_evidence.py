"""Repair legacy gas factors and freeze interpreted meter history."""

from collections.abc import Sequence

from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SEARCH_PATH = "pg_catalog, public"


def upgrade() -> None:
    op.drop_constraint(
        "ck_building_uvi_configuration_conversion_components",
        "building_uvi_configuration",
        type_="check",
    )

    # Preserve every existing configuration row. The final constraint admits
    # bounded legacy factors while restricting new paired supplier evidence.
    op.create_check_constraint(
        condition=(
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
            "calorific_factor > 0 AND condition_number > 0 AND "
            "energy_source = 'Erdgas' AND energy_reference = 'HO' AND "
            "source_type = 'SUPPLIER_INVOICE' AND rechtsstand = '08/2026' AND "
            "verification_status = 'verify-before-production')"
        ),
        table_name="building_uvi_configuration",
        constraint_name="ck_building_uvi_configuration_conversion_components",
    )

    op.execute(f"""
        CREATE FUNCTION public.prevent_read_meter_rewrite_0034() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            IF EXISTS (
              SELECT 1 FROM public.meter_reading AS reading
               WHERE reading.meter_id = OLD.id
                 AND reading.account_id = OLD.account_id
            ) THEN
              RAISE EXCEPTION 'meter reading history is append-only'
                USING ERRCODE = '23514';
            END IF;
            RETURN OLD;
          END IF;

          IF (
            NEW.id IS DISTINCT FROM OLD.id
            OR NEW.account_id IS DISTINCT FROM OLD.account_id
            OR NEW.building_id IS DISTINCT FROM OLD.building_id
            OR NEW.unit_id IS DISTINCT FROM OLD.unit_id
            OR NEW.device_type IS DISTINCT FROM OLD.device_type
            OR NEW.kind IS DISTINCT FROM OLD.kind
            OR NEW.measurement_unit IS DISTINCT FROM OLD.measurement_unit
            OR NEW.serial IS DISTINCT FROM OLD.serial
            OR NEW.installed_on IS DISTINCT FROM OLD.installed_on
            OR NEW.valuation_factor_x1000 IS DISTINCT FROM OLD.valuation_factor_x1000
          ) AND EXISTS (
            SELECT 1 FROM public.meter_reading AS reading
             WHERE reading.meter_id = OLD.id
               AND reading.account_id = OLD.account_id
          ) THEN
            RAISE EXCEPTION 'meter reading history is append-only'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER meter_reading_history_append_only "
        "BEFORE UPDATE OR DELETE ON public.meter FOR EACH ROW "
        "EXECUTE FUNCTION public.prevent_read_meter_rewrite_0034()"
    )


def downgrade() -> None:
    raise RuntimeError(
        "0034 preserves legacy gas evidence and interpreted meter history; "
        "downgrade is intentionally refused"
    )
