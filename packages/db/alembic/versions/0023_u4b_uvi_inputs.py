"""U4b durable normalized inputs for UVI generation."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0023"
down_revision = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "uvi_monthly_degree_day",
    "building_uvi_configuration",
    "uvi_building_monthly_evidence",
    "uvi_building_monthly_evidence_source",
)
_SEARCH_PATH = "pg_catalog, public, pg_temp"


def upgrade() -> None:
    op.drop_constraint("ck_uvi_run_heizspiegel_vintage_nonblank", "uvi_run", type_="check")
    op.alter_column("uvi_run", "heizspiegel_vintage", nullable=True)
    op.alter_column("uvi_run", "station_assignment_id", nullable=True)
    op.alter_column("uvi_run", "station_id", nullable=True)
    op.alter_column("uvi_run", "station_distance_km", nullable=True)
    op.create_check_constraint(
        "ck_uvi_run_heizspiegel_vintage_nonblank",
        "uvi_run",
        "heizspiegel_vintage IS NULL OR btrim(heizspiegel_vintage, E' \\t\\n\\r') <> ''",
    )
    op.create_check_constraint(
        "uvi_run_station_snapshot_all_or_none",
        "uvi_run",
        "((station_assignment_id IS NULL AND station_id IS NULL "
        "AND station_distance_km IS NULL) OR "
        "(station_assignment_id IS NOT NULL AND station_id IS NOT NULL "
        "AND station_distance_km IS NOT NULL))",
    )
    op.execute(f"""
        CREATE OR REPLACE FUNCTION public.enforce_uvi_run_scope_u4() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        DECLARE building_postal_code text;
        BEGIN
          SELECT building.postal_code INTO building_postal_code
            FROM public.tenancy AS tenancy
            JOIN public.unit AS unit
              ON unit.id = NEW.unit_id
             AND unit.account_id = NEW.account_id
            JOIN public.building AS building
              ON building.id = unit.building_id
             AND building.account_id = NEW.account_id
           WHERE tenancy.id = NEW.tenancy_id
             AND tenancy.account_id = NEW.account_id
             AND tenancy.unit_id = NEW.unit_id
             AND tenancy.valid_from < (NEW.month + INTERVAL '1 month')
             AND (tenancy.valid_to IS NULL OR tenancy.valid_to > NEW.month);
          IF building_postal_code IS NULL THEN
            RAISE EXCEPTION 'UVI run tenancy and unit_id are inconsistent'
              USING ERRCODE = '23514';
          END IF;
          IF NEW.station_assignment_id IS NOT NULL THEN
            PERFORM 1 FROM public.uvi_station_assignment AS assignment
             WHERE assignment.id = NEW.station_assignment_id
               AND assignment.account_id = NEW.account_id
               AND assignment.month = NEW.month
               AND assignment.postal_code = building_postal_code
               AND assignment.station_id = NEW.station_id
               AND assignment.distance_km = NEW.station_distance_km;
            IF NOT FOUND THEN
              RAISE EXCEPTION 'UVI run station assignment snapshot is inconsistent'
                USING ERRCODE = '23514';
            END IF;
          END IF;
          RETURN NEW;
        END; $$
    """)

    op.create_unique_constraint(
        "uq_uvi_station_assignment_exact_month",
        "uvi_station_assignment",
        ["id", "account_id", "station_id", "month"],
    )
    op.create_unique_constraint(
        "uq_meter_id_account_building", "meter", ["id", "account_id", "building_id"]
    )
    op.create_unique_constraint(
        "uq_meter_reading_id_account_meter",
        "meter_reading",
        ["id", "account_id", "meter_id"],
    )

    op.create_table(
        "uvi_monthly_degree_day",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("station_assignment_id", sa.String(), nullable=False),
        sa.Column("station_id", sa.String(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("monthly_degree_days", sa.Numeric(10, 3), nullable=False),
        sa.Column("valid_day_count", sa.Integer(), nullable=False),
        sa.Column("source_file", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(), nullable=False),
        sa.Column("rechtsstand", sa.String(), nullable=False),
        sa.Column("verification_status", sa.String(), nullable=False),
        sa.Column("monthly_annual_share", sa.Numeric(8, 7), nullable=True),
        sa.Column("supersedes_degree_day_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["station_assignment_id", "account_id", "station_id", "month"],
            [
                "uvi_station_assignment.id",
                "uvi_station_assignment.account_id",
                "uvi_station_assignment.station_id",
                "uvi_station_assignment.month",
            ],
            name="uvi_monthly_degree_day_station_assignment_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            [
                "supersedes_degree_day_id",
                "account_id",
                "station_assignment_id",
                "station_id",
                "month",
            ],
            [
                "uvi_monthly_degree_day.id",
                "uvi_monthly_degree_day.account_id",
                "uvi_monthly_degree_day.station_assignment_id",
                "uvi_monthly_degree_day.station_id",
                "uvi_monthly_degree_day.month",
            ],
            name="uvi_monthly_degree_day_supersedes_degree_day_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_uvi_monthly_degree_day_id_account"),
        sa.UniqueConstraint(
            "id",
            "account_id",
            "station_assignment_id",
            "station_id",
            "month",
            name="uq_uvi_monthly_degree_day_correction_context",
        ),
        sa.UniqueConstraint(
            "account_id",
            "station_assignment_id",
            "source_id",
            name="uq_uvi_monthly_degree_day_source",
        ),
        sa.UniqueConstraint(
            "account_id",
            "supersedes_degree_day_id",
            name="uq_uvi_monthly_degree_day_direct_successor",
        ),
        sa.CheckConstraint(
            "EXTRACT(DAY FROM month) = 1", name="ck_uvi_monthly_degree_day_month_start"
        ),
        sa.CheckConstraint(
            "monthly_degree_days NOT IN ('NaN'::numeric, 'Infinity'::numeric, "
            "'-Infinity'::numeric) AND monthly_degree_days >= 0",
            name="ck_uvi_monthly_degree_day_finite_non_negative",
        ),
        sa.CheckConstraint(
            "valid_day_count >= 25 AND valid_day_count <= 31",
            name="ck_uvi_monthly_degree_day_valid_days",
        ),
        sa.CheckConstraint(
            "monthly_annual_share IS NULL OR (monthly_annual_share NOT IN "
            "('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric) AND "
            "monthly_annual_share > 0 AND monthly_annual_share <= 1)",
            name="ck_uvi_monthly_degree_day_annual_share",
        ),
        sa.CheckConstraint(
            "btrim(source_file, E' \\t\\n\\r') <> '' AND "
            "btrim(source_id, E' \\t\\n\\r') <> '' AND "
            "btrim(rechtsstand, E' \\t\\n\\r') <> '' AND "
            "btrim(verification_status, E' \\t\\n\\r') <> ''",
            name="ck_uvi_monthly_degree_day_source_metadata",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(provenance) = 'object' AND provenance <> '{}'::jsonb",
            name="ck_uvi_monthly_degree_day_provenance",
        ),
        sa.CheckConstraint(
            "id <> supersedes_degree_day_id",
            name="ck_uvi_monthly_degree_day_not_self_superseding",
        ),
    )
    op.create_index("ix_uvi_monthly_degree_day_account", "uvi_monthly_degree_day", ["account_id"])
    op.create_index(
        "ix_uvi_monthly_degree_day_lookup",
        "uvi_monthly_degree_day",
        ["account_id", "station_id", "month"],
    )
    op.create_index(
        "uq_uvi_monthly_degree_day_root",
        "uvi_monthly_degree_day",
        ["account_id", "station_assignment_id", "station_id", "month"],
        unique=True,
        postgresql_where=sa.text("supersedes_degree_day_id IS NULL"),
    )

    op.create_table(
        "building_uvi_configuration",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("building_id", sa.String(), nullable=False),
        sa.Column("energy_source", sa.String(), nullable=False),
        sa.Column("energy_reference", sa.String(), nullable=False),
        sa.Column("explicit_hkv_allocator", sa.Boolean(), nullable=False),
        sa.Column("calorific_factor", sa.Numeric(12, 6), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("rechtsstand", sa.String(), nullable=False),
        sa.Column("verification_status", sa.String(), nullable=False),
        sa.Column("supersedes_configuration_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["building_id", "account_id"],
            ["building.id", "building.account_id"],
            name="building_uvi_configuration_building_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_configuration_id", "account_id", "building_id"],
            [
                "building_uvi_configuration.id",
                "building_uvi_configuration.account_id",
                "building_uvi_configuration.building_id",
            ],
            name="building_uvi_configuration_supersedes_configuration_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_building_uvi_configuration_id_account"),
        sa.UniqueConstraint(
            "id",
            "account_id",
            "building_id",
            name="uq_building_uvi_configuration_correction_context",
        ),
        sa.UniqueConstraint(
            "account_id",
            "supersedes_configuration_id",
            name="uq_building_uvi_configuration_direct_successor",
        ),
        sa.CheckConstraint(
            "energy_source IN ('Erdgas', 'Heizoel', 'Fernwaerme', 'Waermepumpe', 'Holzpellets')",
            name="ck_building_uvi_configuration_energy_source",
        ),
        sa.CheckConstraint(
            "energy_reference IN ('HO', 'HU')",
            name="ck_building_uvi_configuration_energy_reference",
        ),
        sa.CheckConstraint(
            "calorific_factor IS NULL OR (calorific_factor NOT IN "
            "('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric) AND "
            "calorific_factor > 0)",
            name="ck_building_uvi_configuration_calorific_factor",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="ck_building_uvi_configuration_period_ordered",
        ),
        sa.CheckConstraint(
            "btrim(source_type, E' \\t\\n\\r') <> '' AND "
            "btrim(source_id, E' \\t\\n\\r') <> '' AND "
            "btrim(rechtsstand, E' \\t\\n\\r') <> '' AND "
            "btrim(verification_status, E' \\t\\n\\r') <> ''",
            name="ck_building_uvi_configuration_source_metadata",
        ),
        sa.CheckConstraint(
            "id <> supersedes_configuration_id",
            name="ck_building_uvi_configuration_not_self_superseding",
        ),
    )
    op.create_index(
        "ix_building_uvi_configuration_account", "building_uvi_configuration", ["account_id"]
    )
    op.create_index(
        "ix_building_uvi_configuration_lookup",
        "building_uvi_configuration",
        ["account_id", "building_id", "valid_from"],
    )
    op.create_index(
        "uq_building_uvi_configuration_root",
        "building_uvi_configuration",
        ["account_id", "building_id"],
        unique=True,
        postgresql_where=sa.text("supersedes_configuration_id IS NULL"),
    )

    op.create_table(
        "uvi_building_monthly_evidence",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("building_id", sa.String(), nullable=False),
        sa.Column("main_meter_id", sa.String(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("measured_building_heat_kwh_x1000", sa.BigInteger(), nullable=True),
        sa.Column("building_hkv_movement_x1000", sa.BigInteger(), nullable=True),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("raw_evidence", postgresql.JSONB(), nullable=False),
        sa.Column("supersedes_evidence_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["building_id", "account_id"],
            ["building.id", "building.account_id"],
            name="uvi_building_monthly_evidence_building_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["main_meter_id", "account_id", "building_id"],
            ["meter.id", "meter.account_id", "meter.building_id"],
            name="uvi_building_monthly_evidence_main_meter_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            [
                "supersedes_evidence_id",
                "account_id",
                "building_id",
                "month",
            ],
            [
                "uvi_building_monthly_evidence.id",
                "uvi_building_monthly_evidence.account_id",
                "uvi_building_monthly_evidence.building_id",
                "uvi_building_monthly_evidence.month",
            ],
            name="uvi_building_monthly_evidence_supersedes_evidence_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_uvi_building_monthly_evidence_id_account"),
        sa.UniqueConstraint(
            "id",
            "account_id",
            "building_id",
            "month",
            name="uq_uvi_building_monthly_evidence_correction_context",
        ),
        sa.UniqueConstraint(
            "id",
            "account_id",
            "main_meter_id",
            name="uq_uvi_building_monthly_evidence_source_context",
        ),
        sa.UniqueConstraint(
            "account_id",
            "supersedes_evidence_id",
            name="uq_uvi_building_monthly_evidence_direct_successor",
        ),
        sa.CheckConstraint(
            "EXTRACT(DAY FROM month) = 1",
            name="ck_uvi_building_monthly_evidence_month_start",
        ),
        sa.CheckConstraint(
            "measured_building_heat_kwh_x1000 IS NOT NULL OR "
            "building_hkv_movement_x1000 IS NOT NULL",
            name="ck_uvi_building_monthly_evidence_has_measurement",
        ),
        sa.CheckConstraint(
            "measured_building_heat_kwh_x1000 IS NULL OR measured_building_heat_kwh_x1000 >= 0",
            name="ck_uvi_building_monthly_evidence_heat_non_negative",
        ),
        sa.CheckConstraint(
            "building_hkv_movement_x1000 IS NULL OR building_hkv_movement_x1000 >= 0",
            name="ck_uvi_building_monthly_evidence_hkv_non_negative",
        ),
        sa.CheckConstraint(
            "btrim(source_type, E' \\t\\n\\r') <> '' AND btrim(source_id, E' \\t\\n\\r') <> ''",
            name="ck_uvi_building_monthly_evidence_source_identity",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(raw_evidence) = 'object' AND raw_evidence <> '{}'::jsonb",
            name="ck_uvi_building_monthly_evidence_raw_evidence",
        ),
        sa.CheckConstraint(
            "id <> supersedes_evidence_id",
            name="ck_uvi_building_monthly_evidence_not_self_superseding",
        ),
    )
    op.create_index(
        "ix_uvi_building_monthly_evidence_account",
        "uvi_building_monthly_evidence",
        ["account_id"],
    )
    op.create_index(
        "ix_uvi_building_monthly_evidence_lookup",
        "uvi_building_monthly_evidence",
        ["account_id", "building_id", "month"],
    )
    op.create_index(
        "uq_uvi_building_monthly_evidence_root",
        "uvi_building_monthly_evidence",
        ["account_id", "building_id", "month"],
        unique=True,
        postgresql_where=sa.text("supersedes_evidence_id IS NULL"),
    )

    op.create_table(
        "uvi_building_monthly_evidence_source",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("building_monthly_evidence_id", sa.String(), nullable=False),
        sa.Column("main_meter_id", sa.String(), nullable=False),
        sa.Column("meter_reading_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["building_monthly_evidence_id", "account_id", "main_meter_id"],
            [
                "uvi_building_monthly_evidence.id",
                "uvi_building_monthly_evidence.account_id",
                "uvi_building_monthly_evidence.main_meter_id",
            ],
            name="uvi_bme_source_evidence_fkey",
            match="SIMPLE",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["meter_reading_id", "account_id", "main_meter_id"],
            ["meter_reading.id", "meter_reading.account_id", "meter_reading.meter_id"],
            name="uvi_bme_source_meter_reading_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint(
            "id",
            "account_id",
            name="uq_uvi_building_monthly_evidence_source_id_account",
        ),
        sa.UniqueConstraint(
            "account_id",
            "building_monthly_evidence_id",
            "meter_reading_id",
            name="uq_uvi_building_monthly_evidence_source_identity",
        ),
    )
    op.create_index(
        "ix_uvi_building_monthly_evidence_source_account",
        "uvi_building_monthly_evidence_source",
        ["account_id"],
    )
    op.create_index(
        "ix_uvi_building_monthly_evidence_source_evidence",
        "uvi_building_monthly_evidence_source",
        ["building_monthly_evidence_id"],
    )

    op.execute("ALTER TABLE uvi_monthly_degree_day ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE uvi_monthly_degree_day FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY uvi_monthly_degree_day_isolation ON uvi_monthly_degree_day "
        "USING (account_id = current_setting('app.account_id', true)) "
        "WITH CHECK (account_id = current_setting('app.account_id', true))"
    )
    op.execute("ALTER TABLE building_uvi_configuration ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE building_uvi_configuration FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY building_uvi_configuration_isolation ON building_uvi_configuration "
        "USING (account_id = current_setting('app.account_id', true)) "
        "WITH CHECK (account_id = current_setting('app.account_id', true))"
    )
    op.execute("ALTER TABLE uvi_building_monthly_evidence ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE uvi_building_monthly_evidence FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY uvi_building_monthly_evidence_isolation "
        "ON uvi_building_monthly_evidence "
        "USING (account_id = current_setting('app.account_id', true)) "
        "WITH CHECK (account_id = current_setting('app.account_id', true))"
    )
    op.execute("ALTER TABLE uvi_building_monthly_evidence_source ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE uvi_building_monthly_evidence_source FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY uvi_building_monthly_evidence_source_isolation "
        "ON uvi_building_monthly_evidence_source "
        "USING (account_id = current_setting('app.account_id', true)) "
        "WITH CHECK (account_id = current_setting('app.account_id', true))"
    )

    op.execute(f"""
        CREATE FUNCTION public.enforce_u4b_configuration_successor() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        DECLARE predecessor_valid_from date;
        BEGIN
          IF NEW.supersedes_configuration_id IS NOT NULL THEN
            SELECT valid_from INTO predecessor_valid_from
              FROM public.building_uvi_configuration
             WHERE id = NEW.supersedes_configuration_id
               AND account_id = NEW.account_id
               AND building_id = NEW.building_id;
            IF predecessor_valid_from IS NULL OR NEW.valid_from <= predecessor_valid_from THEN
              RAISE EXCEPTION 'configuration successor must start after its predecessor'
                USING ERRCODE = '23514';
            END IF;
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER building_uvi_configuration_successor_guard "
        "AFTER INSERT ON building_uvi_configuration FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_u4b_configuration_successor()"
    )

    op.execute(f"""
        CREATE FUNCTION public.enforce_u4b_degree_day_successor() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          IF NEW.supersedes_degree_day_id IS NOT NULL THEN
            PERFORM 1 FROM public.uvi_monthly_degree_day
             WHERE id = NEW.supersedes_degree_day_id
               AND account_id = NEW.account_id
               AND station_assignment_id = NEW.station_assignment_id
               AND station_id = NEW.station_id
               AND month = NEW.month;
            IF NOT FOUND THEN
              RAISE EXCEPTION 'degree-day correction predecessor must already exist'
                USING ERRCODE = '23514';
            END IF;
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER uvi_monthly_degree_day_successor_guard "
        "AFTER INSERT ON uvi_monthly_degree_day FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_u4b_degree_day_successor()"
    )

    op.execute(f"""
        CREATE FUNCTION public.enforce_u4b_building_main_meter() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          PERFORM 1 FROM public.meter
           WHERE id = NEW.main_meter_id
             AND account_id = NEW.account_id
             AND building_id = NEW.building_id
             AND unit_id IS NULL
             AND kind = 'HEAT'
             AND measurement_unit = 'KWH';
          IF NOT FOUND THEN
            RAISE EXCEPTION 'UVI building evidence requires a building-level main meter'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER uvi_building_monthly_evidence_main_meter_guard "
        "AFTER INSERT ON uvi_building_monthly_evidence FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_u4b_building_main_meter()"
    )
    op.execute(f"""
        CREATE FUNCTION public.enforce_u4b_building_evidence_successor() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          IF NEW.supersedes_evidence_id IS NOT NULL THEN
            PERFORM 1 FROM public.uvi_building_monthly_evidence
             WHERE id = NEW.supersedes_evidence_id
               AND account_id = NEW.account_id
               AND building_id = NEW.building_id
               AND month = NEW.month;
            IF NOT FOUND THEN
              RAISE EXCEPTION 'building evidence correction predecessor must already exist'
                USING ERRCODE = '23514';
            END IF;
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER uvi_building_monthly_evidence_successor_guard "
        "AFTER INSERT ON uvi_building_monthly_evidence FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_u4b_building_evidence_successor()"
    )

    op.execute(f"""
        CREATE FUNCTION public.enforce_u4b_building_evidence_has_source() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM public.uvi_building_monthly_evidence_source AS source
             WHERE source.building_monthly_evidence_id = NEW.id
               AND source.account_id = NEW.account_id
               AND source.main_meter_id = NEW.main_meter_id
          ) THEN
            RAISE EXCEPTION 'UVI building evidence requires at least one raw source reading'
              USING ERRCODE = '23514';
          END IF;
          RETURN NULL;
        END; $$
    """)
    op.execute(
        "CREATE CONSTRAINT TRIGGER uvi_building_monthly_evidence_source_required "
        "AFTER INSERT ON uvi_building_monthly_evidence DEFERRABLE INITIALLY DEFERRED "
        "FOR EACH ROW EXECUTE FUNCTION public.enforce_u4b_building_evidence_has_source()"
    )

    op.execute(f"""
        CREATE OR REPLACE FUNCTION public.prevent_linked_meter_reading_rewrite_u4()
        RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM public.monthly_meter_reading_source AS source
             WHERE source.meter_reading_id = OLD.id
               AND source.account_id = OLD.account_id
          ) OR EXISTS (
            SELECT 1 FROM public.uvi_building_monthly_evidence_source AS source
             WHERE source.meter_reading_id = OLD.id
               AND source.account_id = OLD.account_id
          ) THEN
            RAISE EXCEPTION 'linked meter reading evidence is append-only'
              USING ERRCODE = '23514';
          END IF;
          IF TG_OP = 'DELETE' THEN
            RETURN OLD;
          END IF;
          RETURN NEW;
        END; $$
    """)

    op.execute(f"""
        CREATE FUNCTION public.prevent_linked_uvi_main_meter_rewrite_u4b() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          IF (
            NEW.id IS DISTINCT FROM OLD.id
            OR NEW.account_id IS DISTINCT FROM OLD.account_id
            OR NEW.building_id IS DISTINCT FROM OLD.building_id
            OR NEW.unit_id IS DISTINCT FROM OLD.unit_id
            OR NEW.kind IS DISTINCT FROM OLD.kind
            OR NEW.measurement_unit IS DISTINCT FROM OLD.measurement_unit
          ) AND EXISTS (
            SELECT 1 FROM public.uvi_building_monthly_evidence AS evidence
             WHERE evidence.main_meter_id = OLD.id
               AND evidence.account_id = OLD.account_id
          ) THEN
            RAISE EXCEPTION 'linked UVI main-meter evidence is append-only'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER meter_uvi_evidence_identity_append_only "
        "BEFORE UPDATE OF id, account_id, building_id, unit_id, kind, measurement_unit "
        "ON public.meter FOR EACH ROW "
        "EXECUTE FUNCTION public.prevent_linked_uvi_main_meter_rewrite_u4b()"
    )

    op.execute(f"""
        CREATE FUNCTION public.prevent_u4b_uvi_input_rewrite() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          RAISE EXCEPTION 'U4b UVI inputs are append-only' USING ERRCODE = '23514';
        END; $$
    """)
    for table in _TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION public.prevent_u4b_uvi_input_rewrite()"
        )


def downgrade() -> None:
    raise RuntimeError("U4b UVI input evidence is intentionally not downgraded")
