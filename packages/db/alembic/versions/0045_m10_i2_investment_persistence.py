"""Add immutable account-scoped investment snapshots and layout versions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0045"
down_revision = "0044"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SEARCH_PATH = "pg_catalog, public, pg_temp"
_CANONICAL_VERSION = "postgres-jsonb-text-v1"

_INPUT_KEYS = (
    "purchase_price_cents",
    "acquisition_costs_cents",
    "monthly_actual_rent_cents",
    "vacancy_bp",
    "administration_cents",
    "maintenance_cents",
    "reserve_cents",
    "vacancy_risk_cents",
    "equity_cents",
    "loan_cents",
    "interest_bp",
    "initial_repayment_bp",
    "fixed_monthly_annuity_cents",
    "marginal_tax_bp",
    "building_share_bp",
    "afa_rate_bp",
    "annual_full_afa_cents",
    "afa_record_version",
    "analysis_period_months",
    "financing_provenance",
    "afa_reference",
    "bank_header",
    "renter_names",
)

_RULE_KEYS = (
    "default_building_share_bp",
    "default_afa_rate_bp",
    "default_marginal_tax_bp",
    "interest_sensitivity_offsets_bp",
    "repayment_sensitivity_steps_bp",
    "dscr_amber_hundredths",
    "dscr_green_hundredths",
    "cashflow_amber_cents",
    "cashflow_green_cents",
    "source_evidence",
    "rechtsstand",
    "production_blocked",
)

_RESULT_KEYS = (
    "outcome",
    "calculated_values",
    "kpi_slots",
    "source_evidence",
    "rechtsstand",
    "production_blocked",
    "applied_conventions",
    "financing_provenance",
    "afa_provenance",
    "tax_provenance",
    "bank_view",
    "interest_sensitivity",
    "repayment_sensitivity",
    "repayment_axis_meaning",
    "tax_scenario_label",
    "findings",
    "warnings",
    "guard",
)


def _jsonb_key_array(values: tuple[str, ...]) -> str:
    return "ARRAY[" + ", ".join(f"'{value}'" for value in values) + "]"


def _optional_integer(
    column: str,
    key: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> str:
    bounds = []
    if minimum is not None:
        bounds.append(f"({column} ->> '{key}')::numeric >= {minimum}")
    if maximum is not None:
        bounds.append(f"({column} ->> '{key}')::numeric <= {maximum}")
    range_check = " AND ".join(bounds)
    if range_check:
        range_check = f" AND {range_check}"
    return (
        f"(NOT {column} ? '{key}' OR {column} -> '{key}' = 'null'::jsonb OR "
        f"(public.jsonb_is_integer_m10({column} -> '{key}'){range_check}))"
    )


def _optional_nonblank_string(column: str, key: str) -> str:
    return (
        f"(NOT {column} ? '{key}' OR {column} -> '{key}' = 'null'::jsonb OR "
        f"(jsonb_typeof({column} -> '{key}') = 'string' AND "
        f"btrim({column} ->> '{key}', E' \\t\\n\\r') <> ''))"
    )


def _install_json_shape_helpers() -> None:
    op.execute(f"""
        CREATE FUNCTION public.jsonb_is_integer_m10(value jsonb) RETURNS boolean
        LANGUAGE sql IMMUTABLE PARALLEL SAFE SET search_path = {_SEARCH_PATH} AS $$
          SELECT value IS NOT NULL
             AND jsonb_typeof(value) = 'number'
             AND value::text ~ '^-?(0|[1-9][0-9]*)$'
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION public.jsonb_array_is_integer_m10(value jsonb) RETURNS boolean
        LANGUAGE sql IMMUTABLE PARALLEL SAFE SET search_path = {_SEARCH_PATH} AS $$
          SELECT CASE WHEN jsonb_typeof(value) = 'array' THEN NOT EXISTS (
            SELECT 1 FROM jsonb_array_elements(value) AS element
             WHERE NOT public.jsonb_is_integer_m10(element)
          ) ELSE false END
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION public.jsonb_array_is_string_m10(value jsonb) RETURNS boolean
        LANGUAGE sql IMMUTABLE PARALLEL SAFE SET search_path = {_SEARCH_PATH} AS $$
          SELECT CASE WHEN jsonb_typeof(value) = 'array' THEN NOT EXISTS (
            SELECT 1 FROM jsonb_array_elements(value) AS element
             WHERE jsonb_typeof(element) <> 'string'
          ) ELSE false END
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION public.jsonb_array_is_nonblank_string_m10(value jsonb) RETURNS boolean
        LANGUAGE sql IMMUTABLE PARALLEL SAFE SET search_path = {_SEARCH_PATH} AS $$
          SELECT CASE WHEN jsonb_typeof(value) = 'array' THEN NOT EXISTS (
            SELECT 1 FROM jsonb_array_elements(value) AS element
             WHERE jsonb_typeof(element) <> 'string'
                OR btrim(element #>> '{{}}', E' \\t\\n\\r') = ''
          ) ELSE false END
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION public.jsonb_array_is_object_m10(value jsonb) RETURNS boolean
        LANGUAGE sql IMMUTABLE PARALLEL SAFE SET search_path = {_SEARCH_PATH} AS $$
          SELECT CASE WHEN jsonb_typeof(value) = 'array' THEN NOT EXISTS (
            SELECT 1 FROM jsonb_array_elements(value) AS element
             WHERE jsonb_typeof(element) <> 'object'
          ) ELSE false END
        $$
    """)


def upgrade() -> None:
    _install_json_shape_helpers()
    op.create_table(
        "investment_layout_version",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("layout_key", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("layout_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("supersedes_layout_version_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_layout_version_id", "account_id", "layout_key"],
            [
                "investment_layout_version.id",
                "investment_layout_version.account_id",
                "investment_layout_version.layout_key",
            ],
            name="investment_layout_version_supersedes_layout_version_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_investment_layout_version_id_account"),
        sa.UniqueConstraint(
            "id",
            "account_id",
            "layout_key",
            name="uq_investment_layout_version_correction_context",
        ),
        sa.UniqueConstraint(
            "account_id",
            "layout_key",
            "version",
            name="uq_investment_layout_version_stream_version",
        ),
        sa.CheckConstraint("version > 0", name="ck_investment_layout_version_positive"),
        sa.CheckConstraint(
            "btrim(layout_key, E' \\t\\n\\r') <> ''",
            name="ck_investment_layout_version_key_nonblank",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(layout_snapshot) = 'object' AND layout_snapshot <> '{}'::jsonb",
            name="ck_investment_layout_version_snapshot_object",
        ),
        sa.CheckConstraint(
            "((version = 1 AND supersedes_layout_version_id IS NULL) OR "
            "(version > 1 AND supersedes_layout_version_id IS NOT NULL))",
            name="ck_investment_layout_version_root",
        ),
        sa.CheckConstraint(
            "id <> supersedes_layout_version_id",
            name="ck_investment_layout_version_not_self",
        ),
    )
    op.create_index(
        "uq_investment_layout_version_root",
        "investment_layout_version",
        ["account_id", "layout_key"],
        unique=True,
        postgresql_where=sa.text("supersedes_layout_version_id IS NULL"),
    )
    op.create_index(
        "uq_investment_layout_version_successor",
        "investment_layout_version",
        ["account_id", "supersedes_layout_version_id"],
        unique=True,
        postgresql_where=sa.text("supersedes_layout_version_id IS NOT NULL"),
    )
    op.create_index(
        "ix_investment_layout_version_account",
        "investment_layout_version",
        ["account_id"],
    )

    input_keys = _jsonb_key_array(_INPUT_KEYS)
    rule_keys = _jsonb_key_array(_RULE_KEYS)
    public_value_checks = [
        _optional_integer("input_snapshot", key, minimum=0)
        for key in (
            "purchase_price_cents",
            "acquisition_costs_cents",
            "monthly_actual_rent_cents",
            "administration_cents",
            "maintenance_cents",
            "reserve_cents",
            "vacancy_risk_cents",
            "equity_cents",
            "loan_cents",
            "interest_bp",
            "initial_repayment_bp",
            "fixed_monthly_annuity_cents",
            "afa_rate_bp",
            "annual_full_afa_cents",
            "analysis_period_months",
        )
    ]
    public_value_checks.extend(
        (
            _optional_integer("input_snapshot", "vacancy_bp", minimum=0, maximum=10_000),
            _optional_integer("input_snapshot", "building_share_bp", minimum=0, maximum=10_000),
            _optional_integer("input_snapshot", "marginal_tax_bp", minimum=0, maximum=9_999),
            _optional_nonblank_string("input_snapshot", "afa_record_version"),
            "(NOT input_snapshot ? 'financing_provenance' "
            "OR input_snapshot -> 'financing_provenance' = 'null'::jsonb "
            "OR (jsonb_typeof(input_snapshot -> 'financing_provenance') = 'string' "
            "AND input_snapshot ->> 'financing_provenance' "
            "IN ('annahme', 'indikativ', 'angebot')))",
            "(NOT input_snapshot ? 'annual_full_afa_cents' "
            "OR input_snapshot -> 'annual_full_afa_cents' = 'null'::jsonb "
            "OR (input_snapshot ? 'afa_record_version' "
            "AND jsonb_typeof(input_snapshot -> 'afa_record_version') = 'string' "
            "AND btrim(input_snapshot ->> 'afa_record_version', E' \\t\\n\\r') <> ''))",
        )
    )
    afa_reference = "input_snapshot -> 'afa_reference'"
    afa_reference_values = " AND ".join(
        (
            f"({afa_reference}) - ARRAY['afa_basis_cents', 'annual_full_afa_cents', "
            "'source', 'record_version'] = '{}'::jsonb",
            _optional_integer(afa_reference, "afa_basis_cents", minimum=0),
            _optional_integer(afa_reference, "annual_full_afa_cents", minimum=0),
            _optional_nonblank_string(afa_reference, "source"),
            _optional_nonblank_string(afa_reference, "record_version"),
            f"((COALESCE({afa_reference} -> 'afa_basis_cents', 'null'::jsonb) = 'null'::jsonb "
            f"AND COALESCE({afa_reference} -> 'annual_full_afa_cents', 'null'::jsonb) "
            "= 'null'::jsonb) OR "
            f"({afa_reference} ?& ARRAY['source', 'record_version'] "
            f"AND jsonb_typeof({afa_reference} -> 'source') = 'string' "
            f"AND btrim({afa_reference} ->> 'source', E' \\t\\n\\r') <> '' "
            f"AND jsonb_typeof({afa_reference} -> 'record_version') = 'string' "
            f"AND btrim({afa_reference} ->> 'record_version', E' \\t\\n\\r') <> ''))",
        )
    )
    bank_header = "input_snapshot -> 'bank_header'"
    bank_header_values = " AND ".join(
        (
            f"({bank_header}) - ARRAY['address', 'property_type', 'year_built', "
            "'area_sqm_x100', 'unit_count', 'creator', 'export_date', 'layout_version'] "
            "= '{}'::jsonb",
            *(
                _optional_nonblank_string(bank_header, key)
                for key in (
                    "address",
                    "property_type",
                    "creator",
                    "export_date",
                    "layout_version",
                )
            ),
            _optional_integer(bank_header, "year_built", minimum=1),
            _optional_integer(bank_header, "area_sqm_x100", minimum=0),
            _optional_integer(bank_header, "unit_count", minimum=0),
        )
    )
    op.create_table(
        "investment_input_snapshot",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("case_key", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("rule_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("financing_provenance_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("afa_provenance_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("layout_version_id", sa.String(), nullable=True),
        sa.Column("canonical_payload_version", sa.String(), nullable=False),
        sa.Column("canonical_payload_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("supersedes_input_snapshot_id", sa.String(), nullable=True),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["supersedes_input_snapshot_id", "account_id", "case_key"],
            [
                "investment_input_snapshot.id",
                "investment_input_snapshot.account_id",
                "investment_input_snapshot.case_key",
            ],
            name="investment_input_snapshot_supersedes_input_snapshot_id_fkey",
            match="SIMPLE",
        ),
        sa.ForeignKeyConstraint(
            ["layout_version_id", "account_id"],
            ["investment_layout_version.id", "investment_layout_version.account_id"],
            name="investment_input_snapshot_layout_version_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_investment_input_snapshot_id_account"),
        sa.UniqueConstraint(
            "id",
            "account_id",
            "case_key",
            name="uq_investment_input_snapshot_correction_context",
        ),
        sa.UniqueConstraint(
            "account_id",
            "case_key",
            "version",
            name="uq_investment_input_snapshot_stream_version",
        ),
        sa.CheckConstraint("version > 0", name="ck_investment_input_snapshot_positive"),
        sa.CheckConstraint(
            "btrim(case_key, E' \\t\\n\\r') <> ''",
            name="ck_investment_input_snapshot_case_key_nonblank",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(input_snapshot) = 'object'",
            name="ck_investment_input_snapshot_input_object",
        ),
        sa.CheckConstraint(
            f"input_snapshot - {input_keys} = '{{}}'::jsonb",
            name="ck_investment_input_snapshot_public_keys",
        ),
        sa.CheckConstraint(
            "(NOT input_snapshot ? 'afa_reference' "
            "OR input_snapshot -> 'afa_reference' = 'null'::jsonb "
            "OR jsonb_typeof(input_snapshot -> 'afa_reference') = 'object') "
            "AND (NOT input_snapshot ? 'bank_header' "
            "OR input_snapshot -> 'bank_header' = 'null'::jsonb "
            "OR jsonb_typeof(input_snapshot -> 'bank_header') = 'object') "
            "AND (NOT input_snapshot ? 'renter_names' "
            "OR input_snapshot -> 'renter_names' = 'null'::jsonb "
            "OR jsonb_typeof(input_snapshot -> 'renter_names') = 'array')",
            name="ck_investment_input_snapshot_nested_shapes",
        ),
        sa.CheckConstraint(
            " AND ".join(public_value_checks),
            name="ck_investment_input_snapshot_public_value_types",
        ),
        sa.CheckConstraint(
            "(NOT input_snapshot ? 'afa_reference' "
            "OR input_snapshot -> 'afa_reference' = 'null'::jsonb "
            f"OR ({afa_reference_values}))",
            name="ck_investment_input_snapshot_afa_reference_values",
        ),
        sa.CheckConstraint(
            "(NOT input_snapshot ? 'bank_header' "
            "OR input_snapshot -> 'bank_header' = 'null'::jsonb "
            f"OR ({bank_header_values}))",
            name="ck_investment_input_snapshot_bank_header_values",
        ),
        sa.CheckConstraint(
            "(NOT input_snapshot ? 'renter_names' "
            "OR input_snapshot -> 'renter_names' = 'null'::jsonb "
            "OR public.jsonb_array_is_string_m10(input_snapshot -> 'renter_names'))",
            name="ck_investment_input_snapshot_renter_names_values",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(rule_snapshot) = 'object' AND rule_snapshot <> '{}'::jsonb",
            name="ck_investment_input_snapshot_rule_object",
        ),
        sa.CheckConstraint(
            f"rule_snapshot ?& {rule_keys} AND rule_snapshot - {rule_keys} = '{{}}'::jsonb",
            name="ck_investment_input_snapshot_rule_shape",
        ),
        sa.CheckConstraint(
            "public.jsonb_is_integer_m10(rule_snapshot -> 'default_building_share_bp') "
            "AND public.jsonb_is_integer_m10(rule_snapshot -> 'default_afa_rate_bp') "
            "AND public.jsonb_is_integer_m10(rule_snapshot -> 'default_marginal_tax_bp') "
            "AND jsonb_typeof(rule_snapshot -> 'interest_sensitivity_offsets_bp') = 'array' "
            "AND jsonb_typeof(rule_snapshot -> 'repayment_sensitivity_steps_bp') = 'array' "
            "AND public.jsonb_is_integer_m10(rule_snapshot -> 'dscr_amber_hundredths') "
            "AND public.jsonb_is_integer_m10(rule_snapshot -> 'dscr_green_hundredths') "
            "AND public.jsonb_is_integer_m10(rule_snapshot -> 'cashflow_amber_cents') "
            "AND public.jsonb_is_integer_m10(rule_snapshot -> 'cashflow_green_cents') "
            "AND jsonb_typeof(rule_snapshot -> 'source_evidence') = 'array' "
            "AND jsonb_typeof(rule_snapshot -> 'rechtsstand') = 'string' "
            "AND btrim(rule_snapshot ->> 'rechtsstand', E' \\t\\n\\r') <> '' "
            "AND jsonb_typeof(rule_snapshot -> 'production_blocked') = 'boolean'",
            name="ck_investment_input_snapshot_rule_types",
        ),
        sa.CheckConstraint(
            "(rule_snapshot ->> 'default_building_share_bp')::numeric BETWEEN 0 AND 10000 "
            "AND (rule_snapshot ->> 'default_afa_rate_bp')::numeric >= 0 "
            "AND (rule_snapshot ->> 'default_marginal_tax_bp')::numeric BETWEEN 0 AND 9999 "
            "AND public.jsonb_array_is_integer_m10("
            "rule_snapshot -> 'interest_sensitivity_offsets_bp') "
            "AND jsonb_array_length(rule_snapshot -> 'interest_sensitivity_offsets_bp') = 5 "
            "AND (rule_snapshot -> 'interest_sensitivity_offsets_bp' ->> 0)::numeric "
            "<= (rule_snapshot -> 'interest_sensitivity_offsets_bp' ->> 1)::numeric "
            "AND (rule_snapshot -> 'interest_sensitivity_offsets_bp' ->> 1)::numeric "
            "<= (rule_snapshot -> 'interest_sensitivity_offsets_bp' ->> 2)::numeric "
            "AND (rule_snapshot -> 'interest_sensitivity_offsets_bp' ->> 2)::numeric "
            "<= (rule_snapshot -> 'interest_sensitivity_offsets_bp' ->> 3)::numeric "
            "AND (rule_snapshot -> 'interest_sensitivity_offsets_bp' ->> 3)::numeric "
            "<= (rule_snapshot -> 'interest_sensitivity_offsets_bp' ->> 4)::numeric "
            "AND ((CASE WHEN rule_snapshot -> 'interest_sensitivity_offsets_bp' ->> 0 = '0' "
            "THEN 1 ELSE 0 END) + "
            "(CASE WHEN rule_snapshot -> 'interest_sensitivity_offsets_bp' ->> 1 = '0' "
            "THEN 1 ELSE 0 END) + "
            "(CASE WHEN rule_snapshot -> 'interest_sensitivity_offsets_bp' ->> 2 = '0' "
            "THEN 1 ELSE 0 END) + "
            "(CASE WHEN rule_snapshot -> 'interest_sensitivity_offsets_bp' ->> 3 = '0' "
            "THEN 1 ELSE 0 END) + "
            "(CASE WHEN rule_snapshot -> 'interest_sensitivity_offsets_bp' ->> 4 = '0' "
            "THEN 1 ELSE 0 END)) = 1 "
            "AND public.jsonb_array_is_integer_m10("
            "rule_snapshot -> 'repayment_sensitivity_steps_bp') "
            "AND jsonb_array_length(rule_snapshot -> 'repayment_sensitivity_steps_bp') = 4 "
            "AND (rule_snapshot -> 'repayment_sensitivity_steps_bp' ->> 0)::numeric > 0 "
            "AND (rule_snapshot -> 'repayment_sensitivity_steps_bp' ->> 0)::numeric "
            "< (rule_snapshot -> 'repayment_sensitivity_steps_bp' ->> 1)::numeric "
            "AND (rule_snapshot -> 'repayment_sensitivity_steps_bp' ->> 1)::numeric "
            "< (rule_snapshot -> 'repayment_sensitivity_steps_bp' ->> 2)::numeric "
            "AND (rule_snapshot -> 'repayment_sensitivity_steps_bp' ->> 2)::numeric "
            "< (rule_snapshot -> 'repayment_sensitivity_steps_bp' ->> 3)::numeric "
            "AND (rule_snapshot ->> 'dscr_amber_hundredths')::numeric >= 0 "
            "AND (rule_snapshot ->> 'dscr_green_hundredths')::numeric "
            ">= (rule_snapshot ->> 'dscr_amber_hundredths')::numeric "
            "AND (rule_snapshot ->> 'cashflow_green_cents')::numeric "
            ">= (rule_snapshot ->> 'cashflow_amber_cents')::numeric "
            "AND jsonb_array_length(rule_snapshot -> 'source_evidence') > 0 "
            "AND public.jsonb_array_is_nonblank_string_m10(rule_snapshot -> 'source_evidence')",
            name="ck_investment_input_snapshot_rule_values",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(financing_provenance_snapshot) = 'object' "
            "AND financing_provenance_snapshot <> '{}'::jsonb",
            name="ck_investment_input_snapshot_financing_provenance_object",
        ),
        sa.CheckConstraint(
            "financing_provenance_snapshot ?& ARRAY['source', 'record_version'] "
            "AND financing_provenance_snapshot - ARRAY['source', 'record_version'] = '{}'::jsonb "
            "AND jsonb_typeof(financing_provenance_snapshot -> 'source') = 'string' "
            "AND financing_provenance_snapshot ->> 'source' "
            "IN ('annahme', 'indikativ', 'angebot') "
            "AND jsonb_typeof(financing_provenance_snapshot -> 'record_version') = 'string' "
            "AND btrim(financing_provenance_snapshot ->> 'record_version', E' \\t\\n\\r') <> ''",
            name="ck_investment_input_snapshot_financing_provenance",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(afa_provenance_snapshot) = 'object' "
            "AND afa_provenance_snapshot <> '{}'::jsonb",
            name="ck_investment_input_snapshot_afa_provenance_object",
        ),
        sa.CheckConstraint(
            "afa_provenance_snapshot ?& ARRAY['source', 'record_version', 'assumption'] "
            "AND jsonb_typeof(afa_provenance_snapshot -> 'source') = 'string' "
            "AND btrim(afa_provenance_snapshot ->> 'source', E' \\t\\n\\r') <> '' "
            "AND jsonb_typeof(afa_provenance_snapshot -> 'record_version') = 'string' "
            "AND btrim(afa_provenance_snapshot ->> 'record_version', E' \\t\\n\\r') <> '' "
            "AND jsonb_typeof(afa_provenance_snapshot -> 'assumption') = 'boolean'",
            name="ck_investment_input_snapshot_afa_provenance",
        ),
        sa.CheckConstraint(
            f"canonical_payload_version = '{_CANONICAL_VERSION}'",
            name="ck_investment_input_snapshot_canonical_version",
        ),
        sa.CheckConstraint(
            "octet_length(canonical_payload_bytes) > 0",
            name="ck_investment_input_snapshot_canonical_bytes_nonempty",
        ),
        sa.CheckConstraint(
            "sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_investment_input_snapshot_sha256",
        ),
        sa.CheckConstraint(
            "((version = 1 AND supersedes_input_snapshot_id IS NULL) OR "
            "(version > 1 AND supersedes_input_snapshot_id IS NOT NULL))",
            name="ck_investment_input_snapshot_root",
        ),
        sa.CheckConstraint(
            "id <> supersedes_input_snapshot_id",
            name="ck_investment_input_snapshot_not_self",
        ),
    )
    op.create_index(
        "uq_investment_input_snapshot_root",
        "investment_input_snapshot",
        ["account_id", "case_key"],
        unique=True,
        postgresql_where=sa.text("supersedes_input_snapshot_id IS NULL"),
    )
    op.create_index(
        "uq_investment_input_snapshot_successor",
        "investment_input_snapshot",
        ["account_id", "supersedes_input_snapshot_id"],
        unique=True,
        postgresql_where=sa.text("supersedes_input_snapshot_id IS NOT NULL"),
    )
    op.create_index(
        "ix_investment_input_snapshot_account",
        "investment_input_snapshot",
        ["account_id"],
    )

    result_keys = _jsonb_key_array(_RESULT_KEYS)
    op.create_table(
        "investment_result_snapshot",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("input_snapshot_id", sa.String(), nullable=False),
        sa.Column("engine_version", sa.String(), nullable=False),
        sa.Column("result_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("canonical_payload_version", sa.String(), nullable=False),
        sa.Column("canonical_result_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["input_snapshot_id", "account_id"],
            ["investment_input_snapshot.id", "investment_input_snapshot.account_id"],
            name="investment_result_snapshot_input_snapshot_id_fkey",
            match="SIMPLE",
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_investment_result_snapshot_id_account"),
        sa.UniqueConstraint(
            "input_snapshot_id",
            "account_id",
            name="uq_investment_result_snapshot_input",
        ),
        sa.CheckConstraint(
            "btrim(engine_version, E' \\t\\n\\r') <> ''",
            name="ck_investment_result_snapshot_engine_version_nonblank",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(result_snapshot) = 'object' AND result_snapshot <> '{}'::jsonb",
            name="ck_investment_result_snapshot_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(result_snapshot -> 'source_evidence') = 'array' "
            "AND jsonb_array_length(result_snapshot -> 'source_evidence') > 0 "
            "AND jsonb_typeof(result_snapshot -> 'rechtsstand') = 'string' "
            "AND btrim(result_snapshot ->> 'rechtsstand', E' \\t\\n\\r') <> '' "
            "AND jsonb_typeof(result_snapshot -> 'production_blocked') = 'boolean' "
            "AND jsonb_typeof(result_snapshot -> 'financing_provenance') = 'object' "
            "AND result_snapshot -> 'financing_provenance' ?& ARRAY['source', 'badge'] "
            "AND (result_snapshot -> 'financing_provenance') - "
            "ARRAY['source', 'badge'] = '{}'::jsonb "
            "AND result_snapshot -> 'financing_provenance' ->> 'source' "
            "IN ('annahme', 'indikativ', 'angebot') "
            "AND jsonb_typeof(result_snapshot -> 'financing_provenance' -> 'badge') = 'string' "
            "AND btrim(result_snapshot -> 'financing_provenance' ->> 'badge', "
            "E' \\t\\n\\r') <> '' "
            "AND jsonb_typeof(result_snapshot -> 'afa_provenance') = 'object'",
            name="ck_investment_result_snapshot_replay_provenance",
        ),
        sa.CheckConstraint(
            f"result_snapshot ?& {result_keys} "
            f"AND result_snapshot - {result_keys} = '{{}}'::jsonb "
            "AND jsonb_typeof(result_snapshot -> 'outcome') = 'string' "
            "AND result_snapshot ->> 'outcome' IN ('calculated', 'hard_block') "
            "AND jsonb_typeof(result_snapshot -> 'calculated_values') = 'object' "
            "AND jsonb_typeof(result_snapshot -> 'kpi_slots') = 'object' "
            "AND public.jsonb_array_is_nonblank_string_m10(result_snapshot -> 'source_evidence') "
            "AND jsonb_array_length(result_snapshot -> 'source_evidence') > 0 "
            "AND jsonb_typeof(result_snapshot -> 'rechtsstand') = 'string' "
            "AND btrim(result_snapshot ->> 'rechtsstand', E' \\t\\n\\r') <> '' "
            "AND jsonb_typeof(result_snapshot -> 'production_blocked') = 'boolean' "
            "AND public.jsonb_array_is_nonblank_string_m10("
            "result_snapshot -> 'applied_conventions') "
            "AND jsonb_array_length(result_snapshot -> 'applied_conventions') > 0 "
            "AND jsonb_typeof(result_snapshot -> 'financing_provenance') = 'object' "
            "AND jsonb_typeof(result_snapshot -> 'afa_provenance') = 'object' "
            "AND jsonb_typeof(result_snapshot -> 'tax_provenance') = 'object' "
            "AND jsonb_typeof(result_snapshot -> 'bank_view') = 'object' "
            "AND public.jsonb_array_is_object_m10(result_snapshot -> 'interest_sensitivity') "
            "AND public.jsonb_array_is_object_m10(result_snapshot -> 'repayment_sensitivity') "
            "AND jsonb_typeof(result_snapshot -> 'repayment_axis_meaning') = 'string' "
            "AND btrim(result_snapshot ->> 'repayment_axis_meaning', E' \\t\\n\\r') <> '' "
            "AND jsonb_typeof(result_snapshot -> 'tax_scenario_label') = 'string' "
            "AND btrim(result_snapshot ->> 'tax_scenario_label', E' \\t\\n\\r') <> '' "
            "AND public.jsonb_array_is_string_m10(result_snapshot -> 'findings') "
            "AND public.jsonb_array_is_string_m10(result_snapshot -> 'warnings') "
            "AND jsonb_typeof(result_snapshot -> 'guard') = 'object'",
            name="ck_investment_result_snapshot_complete_shape",
        ),
        sa.CheckConstraint(
            "((result_snapshot ->> 'outcome' = 'calculated' "
            "AND result_snapshot -> 'guard' = '{}'::jsonb) OR "
            "(result_snapshot ->> 'outcome' = 'hard_block' "
            "AND result_snapshot -> 'calculated_values' = '{}'::jsonb "
            "AND result_snapshot -> 'kpi_slots' = '{}'::jsonb "
            "AND result_snapshot -> 'financing_provenance' <> '{}'::jsonb "
            "AND result_snapshot -> 'afa_provenance' = '{}'::jsonb "
            "AND result_snapshot -> 'tax_provenance' = '{}'::jsonb "
            "AND result_snapshot -> 'bank_view' = '{}'::jsonb "
            "AND result_snapshot -> 'interest_sensitivity' = '[]'::jsonb "
            "AND result_snapshot -> 'repayment_sensitivity' = '[]'::jsonb "
            "AND result_snapshot -> 'guard' ?& "
            "ARRAY['first_interest_cents', 'first_repayment_cents', 'guard_text'] "
            "AND (result_snapshot -> 'guard') - "
            "ARRAY['first_interest_cents', 'first_repayment_cents', 'guard_text'] = '{}'::jsonb "
            "AND public.jsonb_is_integer_m10("
            "result_snapshot -> 'guard' -> 'first_interest_cents') "
            "AND public.jsonb_is_integer_m10("
            "result_snapshot -> 'guard' -> 'first_repayment_cents') "
            "AND jsonb_typeof(result_snapshot -> 'guard' -> 'guard_text') = 'string' "
            "AND btrim(result_snapshot -> 'guard' ->> 'guard_text', E' \\t\\n\\r') <> ''))",
            name="ck_investment_result_snapshot_variant_shape",
        ),
        sa.CheckConstraint(
            f"canonical_payload_version = '{_CANONICAL_VERSION}'",
            name="ck_investment_result_snapshot_canonical_version",
        ),
        sa.CheckConstraint(
            "octet_length(canonical_result_bytes) > 0",
            name="ck_investment_result_snapshot_canonical_bytes_nonempty",
        ),
        sa.CheckConstraint(
            "sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_investment_result_snapshot_sha256",
        ),
    )
    op.create_index(
        "ix_investment_result_snapshot_account",
        "investment_result_snapshot",
        ["account_id"],
    )

    op.execute(f"""
        CREATE FUNCTION public.enforce_investment_layout_version_chain_m10()
        RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        DECLARE predecessor record;
        BEGIN
          IF NEW.version > 1 THEN
            SELECT prior.version INTO predecessor
              FROM public.investment_layout_version AS prior
             WHERE prior.id = NEW.supersedes_layout_version_id
               AND prior.account_id = NEW.account_id
               AND prior.layout_key = NEW.layout_key;
            IF NOT FOUND OR NOT predecessor.version = NEW.version - 1 THEN
              RAISE EXCEPTION 'layout correction must follow the immediate version'
                USING ERRCODE = '23514';
            END IF;
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER investment_layout_version_chain_guard "
        "AFTER INSERT ON public.investment_layout_version FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_investment_layout_version_chain_m10()"
    )
    op.execute(f"""
        CREATE FUNCTION public.enforce_investment_input_snapshot_chain_m10()
        RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        DECLARE predecessor record;
        BEGIN
          IF NEW.version > 1 THEN
            SELECT prior.version INTO predecessor
              FROM public.investment_input_snapshot AS prior
             WHERE prior.id = NEW.supersedes_input_snapshot_id
               AND prior.account_id = NEW.account_id
               AND prior.case_key = NEW.case_key;
            IF NOT FOUND OR NOT predecessor.version = NEW.version - 1 THEN
              RAISE EXCEPTION 'input correction must follow the immediate version'
                USING ERRCODE = '23514';
            END IF;
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER investment_input_snapshot_chain_guard "
        "AFTER INSERT ON public.investment_input_snapshot FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_investment_input_snapshot_chain_m10()"
    )

    op.execute(f"""
        CREATE FUNCTION public.enforce_investment_input_snapshot_hash_m10()
        RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        DECLARE expected_bytes bytea;
        DECLARE expected_sha256 text;
        BEGIN
          expected_bytes := convert_to(
            jsonb_build_object(
              'afa_provenance', NEW.afa_provenance_snapshot,
              'financing_provenance', NEW.financing_provenance_snapshot,
              'input', NEW.input_snapshot,
              'layout_version_id', NEW.layout_version_id,
              'rules', NEW.rule_snapshot
            )::text,
            'UTF8'
          );
          expected_sha256 := encode(digest(expected_bytes, 'sha256'), 'hex');
          IF NEW.canonical_payload_bytes IS DISTINCT FROM expected_bytes
             OR NEW.sha256 IS DISTINCT FROM expected_sha256 THEN
            RAISE EXCEPTION 'investment input canonical bytes or SHA-256 do not match'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER investment_input_snapshot_hash_guard "
        "AFTER INSERT ON public.investment_input_snapshot FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_investment_input_snapshot_hash_m10()"
    )
    op.execute(f"""
        CREATE FUNCTION public.enforce_investment_result_snapshot_hash_m10()
        RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        DECLARE expected_bytes bytea;
        DECLARE expected_sha256 text;
        BEGIN
          expected_bytes := convert_to(NEW.result_snapshot::text, 'UTF8');
          expected_sha256 := encode(digest(expected_bytes, 'sha256'), 'hex');
          IF NEW.canonical_result_bytes IS DISTINCT FROM expected_bytes
             OR NEW.sha256 IS DISTINCT FROM expected_sha256 THEN
            RAISE EXCEPTION 'investment result canonical bytes or SHA-256 do not match'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER investment_result_snapshot_hash_guard "
        "AFTER INSERT ON public.investment_result_snapshot FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_investment_result_snapshot_hash_m10()"
    )

    op.execute(f"""
        CREATE FUNCTION public.prevent_investment_rewrite_m10()
        RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          RAISE EXCEPTION 'investment persistence is append-only' USING ERRCODE = '23514';
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER investment_layout_version_append_only "
        "BEFORE UPDATE OR DELETE ON public.investment_layout_version FOR EACH ROW "
        "EXECUTE FUNCTION public.prevent_investment_rewrite_m10()"
    )
    op.execute(
        "CREATE TRIGGER investment_input_snapshot_append_only "
        "BEFORE UPDATE OR DELETE ON public.investment_input_snapshot FOR EACH ROW "
        "EXECUTE FUNCTION public.prevent_investment_rewrite_m10()"
    )
    op.execute(
        "CREATE TRIGGER investment_result_snapshot_append_only "
        "BEFORE UPDATE OR DELETE ON public.investment_result_snapshot FOR EACH ROW "
        "EXECUTE FUNCTION public.prevent_investment_rewrite_m10()"
    )

    op.execute("ALTER TABLE public.investment_layout_version ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.investment_layout_version FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY investment_layout_version_owner_select "
        "ON public.investment_layout_version FOR SELECT "
        "USING (account_id = current_setting('app.account_id', true) "
        "AND NULLIF(current_setting('app.tenancy_id', true), '') IS NULL)"
    )
    op.execute(
        "CREATE POLICY investment_layout_version_owner_insert "
        "ON public.investment_layout_version FOR INSERT "
        "WITH CHECK (account_id = current_setting('app.account_id', true) "
        "AND NULLIF(current_setting('app.tenancy_id', true), '') IS NULL)"
    )
    op.execute("ALTER TABLE public.investment_input_snapshot ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.investment_input_snapshot FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY investment_input_snapshot_owner_select "
        "ON public.investment_input_snapshot FOR SELECT "
        "USING (account_id = current_setting('app.account_id', true) "
        "AND NULLIF(current_setting('app.tenancy_id', true), '') IS NULL)"
    )
    op.execute(
        "CREATE POLICY investment_input_snapshot_owner_insert "
        "ON public.investment_input_snapshot FOR INSERT "
        "WITH CHECK (account_id = current_setting('app.account_id', true) "
        "AND NULLIF(current_setting('app.tenancy_id', true), '') IS NULL)"
    )
    op.execute("ALTER TABLE public.investment_result_snapshot ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.investment_result_snapshot FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY investment_result_snapshot_owner_select "
        "ON public.investment_result_snapshot FOR SELECT "
        "USING (account_id = current_setting('app.account_id', true) "
        "AND NULLIF(current_setting('app.tenancy_id', true), '') IS NULL)"
    )
    op.execute(
        "CREATE POLICY investment_result_snapshot_owner_insert "
        "ON public.investment_result_snapshot FOR INSERT "
        "WITH CHECK (account_id = current_setting('app.account_id', true) "
        "AND NULLIF(current_setting('app.tenancy_id', true), '') IS NULL)"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS investment_result_snapshot_append_only "
        "ON public.investment_result_snapshot"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS investment_result_snapshot_hash_guard "
        "ON public.investment_result_snapshot"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS investment_input_snapshot_append_only "
        "ON public.investment_input_snapshot"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS investment_input_snapshot_hash_guard "
        "ON public.investment_input_snapshot"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS investment_input_snapshot_chain_guard "
        "ON public.investment_input_snapshot"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS investment_layout_version_append_only "
        "ON public.investment_layout_version"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS investment_layout_version_chain_guard "
        "ON public.investment_layout_version"
    )
    op.drop_table("investment_result_snapshot")
    op.drop_table("investment_input_snapshot")
    op.drop_table("investment_layout_version")
    op.execute("DROP FUNCTION IF EXISTS public.prevent_investment_rewrite_m10()")
    op.execute("DROP FUNCTION IF EXISTS public.enforce_investment_result_snapshot_hash_m10()")
    op.execute("DROP FUNCTION IF EXISTS public.enforce_investment_input_snapshot_hash_m10()")
    op.execute("DROP FUNCTION IF EXISTS public.enforce_investment_input_snapshot_chain_m10()")
    op.execute("DROP FUNCTION IF EXISTS public.enforce_investment_layout_version_chain_m10()")
    op.execute("DROP FUNCTION IF EXISTS public.jsonb_array_is_object_m10(jsonb)")
    op.execute("DROP FUNCTION IF EXISTS public.jsonb_array_is_nonblank_string_m10(jsonb)")
    op.execute("DROP FUNCTION IF EXISTS public.jsonb_array_is_string_m10(jsonb)")
    op.execute("DROP FUNCTION IF EXISTS public.jsonb_array_is_integer_m10(jsonb)")
    op.execute("DROP FUNCTION IF EXISTS public.jsonb_is_integer_m10(jsonb)")
