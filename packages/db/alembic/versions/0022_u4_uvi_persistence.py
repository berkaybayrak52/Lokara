"""U4 immutable UVI readings, source snapshots, runs and delivery evidence."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0022"
down_revision = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "monthly_meter_reading",
    "monthly_meter_reading_source",
    "uvi_station_assignment",
    "dwd_climate_factor",
    "uvi_run",
    "uvi_delivery_event",
)

_SEARCH_PATH = "pg_catalog, public, pg_temp"


def _scoped_fk(table: str, column: str, parent: str) -> None:
    op.create_foreign_key(
        f"{table}_{column}_fkey",
        table,
        parent,
        [column, "account_id"],
        ["id", "account_id"],
        match="SIMPLE",
    )


def _table(name: str, *columns: sa.Column[object], constraints: tuple[object, ...] = ()) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        *columns,
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("id", "account_id", name=f"uq_{name}_id_account"),
        *constraints,
    )


def upgrade() -> None:
    _table(
        "monthly_meter_reading",
        sa.Column("meter_id", sa.String(), nullable=False),
        sa.Column("tenancy_id", sa.String(), nullable=False),
        sa.Column("unit_id", sa.String(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("consumption_x1000", sa.BigInteger(), nullable=False),
        sa.Column(
            "reason",
            postgresql.ENUM(name="reading_reason", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "source",
            postgresql.ENUM(name="reading_source", create_type=False),
            nullable=False,
        ),
        sa.Column("interpolation_method", sa.String(), nullable=False),
        sa.Column("supersedes_reading_id", sa.String(), nullable=True),
        constraints=(
            sa.CheckConstraint(
                "consumption_x1000 >= 0", name="ck_monthly_meter_reading_non_negative"
            ),
            sa.CheckConstraint(
                "id <> supersedes_reading_id",
                name="ck_monthly_meter_reading_not_self_superseding",
            ),
            sa.CheckConstraint(
                "(reason = 'CORRECTION'::reading_reason) = (supersedes_reading_id IS NOT NULL)",
                name="ck_monthly_meter_reading_correction_predecessor",
            ),
            sa.CheckConstraint(
                "EXTRACT(DAY FROM month) = 1", name="ck_monthly_meter_reading_month_start"
            ),
        ),
    )
    _scoped_fk("monthly_meter_reading", "meter_id", "meter")
    _scoped_fk("monthly_meter_reading", "tenancy_id", "tenancy")
    _scoped_fk("monthly_meter_reading", "unit_id", "unit")
    _scoped_fk("monthly_meter_reading", "supersedes_reading_id", "monthly_meter_reading")
    op.create_unique_constraint(
        "uq_monthly_meter_reading_direct_successor",
        "monthly_meter_reading",
        ["account_id", "supersedes_reading_id"],
    )
    op.create_index(
        "ix_monthly_meter_reading_meter_month",
        "monthly_meter_reading",
        ["meter_id", "month"],
    )
    op.create_index(
        "ix_monthly_meter_reading_tenancy_month",
        "monthly_meter_reading",
        ["tenancy_id", "month"],
    )

    op.create_unique_constraint(
        "uq_meter_reading_id_account",
        "meter_reading",
        ["id", "account_id"],
    )
    _table(
        "monthly_meter_reading_source",
        sa.Column("monthly_meter_reading_id", sa.String(), nullable=False),
        sa.Column("meter_reading_id", sa.String(), nullable=False),
        constraints=(
            sa.UniqueConstraint(
                "account_id",
                "monthly_meter_reading_id",
                "meter_reading_id",
                name="uq_monthly_meter_reading_source_identity",
            ),
        ),
    )
    _scoped_fk(
        "monthly_meter_reading_source",
        "monthly_meter_reading_id",
        "monthly_meter_reading",
    )
    _scoped_fk("monthly_meter_reading_source", "meter_reading_id", "meter_reading")
    op.create_index(
        "ix_monthly_meter_reading_source_monthly",
        "monthly_meter_reading_source",
        ["monthly_meter_reading_id"],
    )
    op.create_index(
        "ix_monthly_meter_reading_source_raw",
        "monthly_meter_reading_source",
        ["meter_reading_id"],
    )

    _table(
        "uvi_station_assignment",
        sa.Column("postal_code", sa.String(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("station_id", sa.String(), nullable=False),
        sa.Column("distance_km", sa.Numeric(9, 3), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        constraints=(
            sa.UniqueConstraint(
                "account_id",
                "postal_code",
                "month",
                name="uq_uvi_station_assignment_postal_month",
            ),
            sa.CheckConstraint(
                "postal_code ~ '^[0-9]{5}$'", name="ck_uvi_station_assignment_postal_code"
            ),
            sa.CheckConstraint(
                "EXTRACT(DAY FROM month) = 1", name="ck_uvi_station_assignment_month_start"
            ),
            sa.CheckConstraint("distance_km >= 0", name="ck_uvi_station_assignment_distance_km"),
        ),
    )
    op.create_index(
        "ix_uvi_station_assignment_lookup",
        "uvi_station_assignment",
        ["account_id", "postal_code", "month"],
    )

    _table(
        "dwd_climate_factor",
        sa.Column("postal_code", sa.String(), nullable=False),
        sa.Column("period_from", sa.Date(), nullable=False),
        sa.Column("period_to", sa.Date(), nullable=False),
        sa.Column("factor", sa.Numeric(6, 4), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        constraints=(
            sa.UniqueConstraint(
                "account_id",
                "postal_code",
                "period_from",
                "period_to",
                name="uq_dwd_climate_factor_identity",
            ),
            sa.CheckConstraint(
                "postal_code ~ '^[0-9]{5}$'", name="ck_dwd_climate_factor_postal_code"
            ),
            sa.CheckConstraint(
                "period_to >= period_from", name="ck_dwd_climate_factor_period_ordered"
            ),
            sa.CheckConstraint(
                "factor >= 0.40 AND factor <= 1.80", name="ck_dwd_climate_factor_range"
            ),
        ),
    )
    op.create_index(
        "ix_dwd_climate_factor_lookup",
        "dwd_climate_factor",
        ["account_id", "postal_code", "period_from", "period_to"],
    )

    _table(
        "uvi_run",
        sa.Column("tenancy_id", sa.String(), nullable=False),
        sa.Column("unit_id", sa.String(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("inputs", postgresql.JSONB(), nullable=False),
        sa.Column("results", postgresql.JSONB(), nullable=False),
        sa.Column("heizspiegel_vintage", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("station_assignment_id", sa.String(), nullable=False),
        sa.Column("station_id", sa.String(), nullable=False),
        sa.Column("station_distance_km", sa.Numeric(9, 3), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        constraints=(
            sa.CheckConstraint("EXTRACT(DAY FROM month) = 1", name="ck_uvi_run_month_start"),
            sa.CheckConstraint("station_distance_km >= 0", name="ck_uvi_run_station_distance_km"),
            sa.CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_uvi_run_sha256"),
            sa.CheckConstraint(
                "jsonb_typeof(inputs) = 'object' AND inputs <> '{}'::jsonb",
                name="ck_uvi_run_inputs_nonempty_object",
            ),
            sa.CheckConstraint(
                "jsonb_typeof(results) = 'object' AND results <> '{}'::jsonb",
                name="ck_uvi_run_results_nonempty_object",
            ),
            sa.CheckConstraint(
                "btrim(heizspiegel_vintage, E' \\t\\n\\r') <> ''",
                name="ck_uvi_run_heizspiegel_vintage_nonblank",
            ),
            sa.CheckConstraint(
                "btrim(source_type, E' \\t\\n\\r') <> ''",
                name="ck_uvi_run_source_type_nonblank",
            ),
            sa.CheckConstraint(
                "btrim(source_id, E' \\t\\n\\r') <> ''",
                name="ck_uvi_run_source_id_nonblank",
            ),
        ),
    )
    _scoped_fk("uvi_run", "tenancy_id", "tenancy")
    _scoped_fk("uvi_run", "unit_id", "unit")
    _scoped_fk("uvi_run", "station_assignment_id", "uvi_station_assignment")
    op.create_index("ix_uvi_run_tenancy_month", "uvi_run", ["tenancy_id", "month"])
    op.create_index("ix_uvi_run_unit_month", "uvi_run", ["unit_id", "month"])

    _table(
        "uvi_delivery_event",
        sa.Column("uvi_run_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        constraints=(
            sa.CheckConstraint(
                "status IN ('GENERATED', 'PUBLISHED', 'EMAILED', 'FAILED')",
                name="ck_uvi_delivery_event_status",
            ),
        ),
    )
    _scoped_fk("uvi_delivery_event", "uvi_run_id", "uvi_run")
    op.create_index(
        "ix_uvi_delivery_event_run",
        "uvi_delivery_event",
        ["uvi_run_id", "occurred_at"],
    )

    for table in _TABLES:
        op.create_index(f"ix_{table}_account", table, ["account_id"])
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_isolation ON public.{table} "
            "USING (account_id = current_setting('app.account_id', true)) "
            "WITH CHECK (account_id = current_setting('app.account_id', true))"
        )

    op.execute(f"""
        CREATE FUNCTION public.enforce_monthly_meter_reading_scope_u4() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          PERFORM 1
            FROM public.meter AS meter
            JOIN public.unit AS unit
              ON unit.id = NEW.unit_id
             AND unit.account_id = NEW.account_id
            JOIN public.tenancy AS tenancy
              ON tenancy.id = NEW.tenancy_id
             AND tenancy.account_id = NEW.account_id
           WHERE meter.id = NEW.meter_id
             AND meter.account_id = NEW.account_id
             AND meter.unit_id = NEW.unit_id
             AND meter.building_id = unit.building_id
             AND tenancy.unit_id = NEW.unit_id
             AND tenancy.valid_from < (NEW.month + INTERVAL '1 month')
             AND (tenancy.valid_to IS NULL OR tenancy.valid_to > NEW.month);
          IF NOT FOUND THEN
            RAISE EXCEPTION
              'monthly meter, tenancy and unit must be coherent for the represented month'
              USING ERRCODE = '23514';
          END IF;

          IF NEW.supersedes_reading_id IS NOT NULL THEN
            PERFORM 1
              FROM public.monthly_meter_reading AS predecessor
             WHERE predecessor.id = NEW.supersedes_reading_id
               AND predecessor.account_id = NEW.account_id
               AND predecessor.meter_id = NEW.meter_id
               AND predecessor.tenancy_id = NEW.tenancy_id
               AND predecessor.unit_id = NEW.unit_id
               AND predecessor.month = NEW.month;
            IF NOT FOUND THEN
              RAISE EXCEPTION 'monthly correction predecessor context must match exactly'
                USING ERRCODE = '23514';
            END IF;
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER monthly_meter_reading_scope_guard "
        "AFTER INSERT ON public.monthly_meter_reading FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_monthly_meter_reading_scope_u4()"
    )

    op.execute(f"""
        CREATE FUNCTION public.enforce_monthly_meter_reading_source_u4() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          PERFORM 1
            FROM public.monthly_meter_reading AS monthly
            JOIN public.meter_reading AS raw
              ON raw.id = NEW.meter_reading_id
             AND raw.account_id = NEW.account_id
           WHERE monthly.id = NEW.monthly_meter_reading_id
             AND monthly.account_id = NEW.account_id
             AND raw.meter_id = monthly.meter_id;
          IF NOT FOUND THEN
            RAISE EXCEPTION
              'monthly source reading must belong to the normalized parent meter'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER monthly_meter_reading_source_relation_guard "
        "AFTER INSERT ON public.monthly_meter_reading_source FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_monthly_meter_reading_source_u4()"
    )

    op.execute(f"""
        CREATE FUNCTION public.enforce_monthly_meter_reading_has_source_u4() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1
              FROM public.monthly_meter_reading_source AS source
             WHERE source.monthly_meter_reading_id = NEW.id
               AND source.account_id = NEW.account_id
          ) THEN
            RAISE EXCEPTION 'monthly meter reading requires at least one raw source reading'
              USING ERRCODE = '23514';
          END IF;
          RETURN NULL;
        END; $$
    """)
    op.execute(
        "CREATE CONSTRAINT TRIGGER monthly_meter_reading_source_required "
        "AFTER INSERT ON public.monthly_meter_reading DEFERRABLE INITIALLY DEFERRED "
        "FOR EACH ROW EXECUTE FUNCTION public.enforce_monthly_meter_reading_has_source_u4()"
    )

    op.execute(f"""
        CREATE FUNCTION public.enforce_uvi_run_scope_u4() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          PERFORM 1
            FROM public.tenancy AS tenancy
            JOIN public.unit AS unit
              ON unit.id = NEW.unit_id
             AND unit.account_id = NEW.account_id
            JOIN public.building AS building
              ON building.id = unit.building_id
             AND building.account_id = NEW.account_id
            JOIN public.uvi_station_assignment AS assignment
              ON assignment.id = NEW.station_assignment_id
             AND assignment.account_id = NEW.account_id
           WHERE tenancy.id = NEW.tenancy_id
             AND tenancy.account_id = NEW.account_id
             AND tenancy.unit_id = NEW.unit_id
             AND tenancy.valid_from < (NEW.month + INTERVAL '1 month')
             AND (tenancy.valid_to IS NULL OR tenancy.valid_to > NEW.month)
             AND assignment.month = NEW.month
             AND assignment.postal_code = building.postal_code
             AND assignment.station_id = NEW.station_id
             AND assignment.distance_km = NEW.station_distance_km;
          IF NOT FOUND THEN
            RAISE EXCEPTION
              'UVI run tenancy, unit_id and station assignment snapshot are inconsistent'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    # AFTER is load-bearing: RLS WITH CHECK rejects a cross-account INSERT before
    # either relationship or hash validation can mask the isolation error.
    op.execute(
        "CREATE TRIGGER uvi_run_scope_guard AFTER INSERT ON public.uvi_run "
        "FOR EACH ROW EXECUTE FUNCTION public.enforce_uvi_run_scope_u4()"
    )

    op.execute(f"""
        CREATE FUNCTION public.enforce_uvi_run_hash_u4() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        DECLARE expected_sha256 text;
        BEGIN
          expected_sha256 := encode(
            digest(
              convert_to(
                (to_jsonb(NEW) - ARRAY['id', 'account_id', 'created_at', 'sha256'])::text,
                'UTF8'
              ),
              'sha256'
            ),
            'hex'
          );
          IF NEW.sha256 IS DISTINCT FROM expected_sha256 THEN
            RAISE EXCEPTION 'UVI run SHA-256 does not match canonical evidence payload'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER uvi_run_hash_guard AFTER INSERT ON public.uvi_run "
        "FOR EACH ROW EXECUTE FUNCTION public.enforce_uvi_run_hash_u4()"
    )

    op.execute(f"""
        CREATE FUNCTION public.prevent_uvi_evidence_rewrite_u4() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          RAISE EXCEPTION 'UVI evidence is append-only' USING ERRCODE = '23514';
        END; $$
    """)
    op.execute(f"""
        CREATE FUNCTION public.prevent_linked_meter_reading_rewrite_u4() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          IF EXISTS (
            SELECT 1
              FROM public.monthly_meter_reading_source AS source
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
    op.execute(
        "CREATE TRIGGER meter_reading_append_only BEFORE UPDATE OR DELETE "
        "ON public.meter_reading FOR EACH ROW "
        "EXECUTE FUNCTION public.prevent_linked_meter_reading_rewrite_u4()"
    )
    for table in _TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE "
            f"ON public.{table} FOR EACH ROW "
            "EXECUTE FUNCTION public.prevent_uvi_evidence_rewrite_u4()"
        )


def downgrade() -> None:
    raise RuntimeError("U4 UVI evidence is intentionally not downgraded")
