"""RED M10-I2 persistence contract from docs/14 § 4.7.

The fixtures pin migration 0045 and mapped metadata before implementation.
They do not prescribe the M10-I3 API or M10-I4 renderer.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import runpy
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from investment_engine import (
    InvestmentInput,
    InvestmentResult,
    InvestmentRuleBundle,
    calculate_investment_snapshot,
)
from lokara_db import Base, DbSettings, create_db_engine, new_id
from sqlalchemy import (
    CheckConstraint,
    Connection,
    Engine,
    ForeignKeyConstraint,
    UniqueConstraint,
    text,
)
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.sql.elements import TextClause
from sqlalchemy.sql.schema import Table

_DB_DIR = Path(__file__).resolve().parent.parent
TABLES = (
    "investment_layout_version",
    "investment_input_snapshot",
    "investment_result_snapshot",
)
CANONICAL_VERSION = "postgres-jsonb-text-v1"

PUBLIC_INPUT_KEYS = {
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
}
RULE_KEYS = {
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
}
RESULT_KEYS = {
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
}


def _migration_path() -> Path:
    migrations = tuple((_DB_DIR / "alembic" / "versions").glob("0045_*.py"))
    assert len(migrations) == 1, "RED M10-I2: migration 0045 is missing"
    return migrations[0]


def _migration_source() -> str:
    return _migration_path().read_text()


def _table(name: str) -> Table:
    assert name in Base.metadata.tables, f"RED M10-I2: {name} model is missing"
    return Base.metadata.tables[name]


def _unique_sets(table: Table) -> set[frozenset[str]]:
    return {
        frozenset(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def _has_fk(table: Table, local: tuple[str, ...], remote: tuple[str, ...]) -> bool:
    return any(
        isinstance(constraint, ForeignKeyConstraint)
        and tuple(constraint.column_keys) == local
        and tuple(
            f"{element.column.table.name}.{element.column.name}" for element in constraint.elements
        )
        == remote
        for constraint in table.constraints
    )


def test_m10_i2_migration_0045_has_exact_revision_and_tables() -> None:
    path = _migration_path()
    source = path.read_text()
    assert 'revision = "0045"' in source
    assert 'down_revision = "0044"' in source
    for table in TABLES:
        assert f'"{table}"' in source


def test_m10_i2_models_expose_exact_three_record_boundaries() -> None:
    db = importlib.import_module("lokara_db")
    expected = {
        "InvestmentLayoutVersion": "investment_layout_version",
        "InvestmentInputSnapshot": "investment_input_snapshot",
        "InvestmentResultSnapshot": "investment_result_snapshot",
    }
    for model_name, table_name in expected.items():
        model = getattr(db, model_name, None)
        assert model is not None, f"RED M10-I2: {model_name} is missing"
        assert model.__tablename__ == table_name
    assert set(Base.metadata.tables) >= set(TABLES)


def test_m10_i2_layout_version_shape_is_exact_and_append_versioned() -> None:
    table = _table("investment_layout_version")
    assert set(table.columns.keys()) == {
        "id",
        "account_id",
        "layout_key",
        "version",
        "layout_snapshot",
        "supersedes_layout_version_id",
        "created_at",
    }
    for name in ("account_id", "layout_key", "version", "layout_snapshot", "created_at"):
        assert not table.columns[name].nullable
    assert table.columns["supersedes_layout_version_id"].nullable
    assert table.columns["version"].type.python_type is int
    assert table.columns["layout_snapshot"].type.python_type is dict
    assert table.columns["layout_snapshot"].server_default is None
    assert frozenset({"id", "account_id", "layout_key"}) in _unique_sets(table)
    assert frozenset({"account_id", "layout_key", "version"}) in _unique_sets(table)
    assert _has_fk(
        table,
        ("supersedes_layout_version_id", "account_id", "layout_key"),
        (
            "investment_layout_version.id",
            "investment_layout_version.account_id",
            "investment_layout_version.layout_key",
        ),
    )


def test_m10_i2_input_snapshot_shape_freezes_exact_reproduction_inputs() -> None:
    table = _table("investment_input_snapshot")
    assert set(table.columns.keys()) == {
        "id",
        "account_id",
        "case_key",
        "version",
        "input_snapshot",
        "rule_snapshot",
        "financing_provenance_snapshot",
        "afa_provenance_snapshot",
        "layout_version_id",
        "canonical_payload_version",
        "canonical_payload_bytes",
        "sha256",
        "supersedes_input_snapshot_id",
        "frozen_at",
    }
    assert "building_id" not in table.columns
    assert table.columns["layout_version_id"].nullable
    assert table.columns["supersedes_input_snapshot_id"].nullable
    for name in (
        "account_id",
        "case_key",
        "version",
        "input_snapshot",
        "rule_snapshot",
        "financing_provenance_snapshot",
        "afa_provenance_snapshot",
        "canonical_payload_version",
        "canonical_payload_bytes",
        "sha256",
        "frozen_at",
    ):
        assert not table.columns[name].nullable
    for name in (
        "input_snapshot",
        "rule_snapshot",
        "financing_provenance_snapshot",
        "afa_provenance_snapshot",
    ):
        assert table.columns[name].type.python_type is dict
        assert table.columns[name].server_default is None
    assert table.columns["canonical_payload_bytes"].type.python_type is bytes
    assert frozenset({"id", "account_id", "case_key"}) in _unique_sets(table)
    assert frozenset({"account_id", "case_key", "version"}) in _unique_sets(table)


def test_m10_i2_result_is_one_to_one_with_frozen_input_and_keeps_canonical_bytes() -> None:
    table = _table("investment_result_snapshot")
    assert set(table.columns.keys()) == {
        "id",
        "account_id",
        "input_snapshot_id",
        "engine_version",
        "result_snapshot",
        "canonical_payload_version",
        "canonical_result_bytes",
        "sha256",
        "calculated_at",
    }
    assert all(not column.nullable for column in table.columns)
    assert table.columns["result_snapshot"].type.python_type is dict
    assert table.columns["result_snapshot"].server_default is None
    assert table.columns["canonical_result_bytes"].type.python_type is bytes
    assert frozenset({"id", "account_id"}) in _unique_sets(table)
    assert frozenset({"input_snapshot_id", "account_id"}) in _unique_sets(table)


def test_m10_i2_every_relationship_preserves_account_and_correction_stream() -> None:
    snapshot = _table("investment_input_snapshot")
    result = _table("investment_result_snapshot")
    assert _has_fk(
        snapshot,
        ("supersedes_input_snapshot_id", "account_id", "case_key"),
        (
            "investment_input_snapshot.id",
            "investment_input_snapshot.account_id",
            "investment_input_snapshot.case_key",
        ),
    )
    assert _has_fk(
        snapshot,
        ("layout_version_id", "account_id"),
        ("investment_layout_version.id", "investment_layout_version.account_id"),
    )
    assert _has_fk(
        result,
        ("input_snapshot_id", "account_id"),
        ("investment_input_snapshot.id", "investment_input_snapshot.account_id"),
    )


def test_m10_i2_canonical_json_bytes_and_sha256_are_database_verified() -> None:
    normalized = " ".join(_migration_source().lower().split())
    assert "postgres-jsonb-text-v1" in normalized
    assert "jsonb_build_object" in normalized
    for key in (
        "afa_provenance",
        "financing_provenance",
        "input",
        "layout_version_id",
        "rules",
    ):
        assert f"'{key}'" in normalized
    assert "convert_to" in normalized and "'utf8'" in normalized
    assert "result_snapshot::text" in normalized
    assert "digest(" in normalized and "'sha256'" in normalized
    assert "canonical_payload_bytes" in normalized
    assert "canonical_result_bytes" in normalized
    assert "investment_input_snapshot_hash_guard" in normalized
    assert "investment_result_snapshot_hash_guard" in normalized


def test_m10_i2_persisted_input_and_rule_key_allowlists_are_exact() -> None:
    migration = runpy.run_path(str(_migration_path()))
    assert set(migration["_INPUT_KEYS"]) == PUBLIC_INPUT_KEYS
    assert set(migration["_RULE_KEYS"]) == RULE_KEYS
    assert set(InvestmentResult.__dataclass_fields__) == RESULT_KEYS


def test_m10_i2_json_provenance_missing_values_and_lifecycle_are_guarded() -> None:
    normalized = " ".join(_migration_source().lower().split())
    for column in (
        "layout_snapshot",
        "input_snapshot",
        "rule_snapshot",
        "financing_provenance_snapshot",
        "afa_provenance_snapshot",
        "result_snapshot",
    ):
        assert f"jsonb_typeof({column}) = 'object'" in normalized
    for column in (
        "layout_snapshot",
        "rule_snapshot",
        "financing_provenance_snapshot",
        "afa_provenance_snapshot",
        "result_snapshot",
    ):
        assert f"{column} <> '{{}}'::jsonb" in normalized
    assert "financing_provenance_snapshot ->> 'source'" in normalized
    assert "in ('annahme', 'indikativ', 'angebot')" in normalized
    assert "record_version" in normalized
    assert "assumption" in normalized
    assert "version = 1" in normalized and "version > 1" in normalized
    assert "prevent_investment_rewrite_m10" in normalized
    for table in TABLES:
        assert f"{table}_append_only" in normalized


def test_m10_i2_all_tables_force_rls_with_account_insert_checks() -> None:
    normalized = " ".join(_migration_source().lower().split())
    for table in TABLES:
        assert f"alter table public.{table} enable row level security" in normalized
        assert f"alter table public.{table} force row level security" in normalized
        assert f"create policy {table}_owner_select" in normalized
        assert f"create policy {table}_owner_insert" in normalized
        assert "with check (account_id = current_setting('app.account_id', true)" in normalized
    assert "current_setting('app.tenancy_id', true)" in normalized


def test_m10_i2_correction_roots_successors_and_immediate_versions_are_unique() -> None:
    source = _migration_source()
    for index_name in (
        "uq_investment_layout_version_root",
        "uq_investment_layout_version_successor",
        "uq_investment_input_snapshot_root",
        "uq_investment_input_snapshot_successor",
    ):
        assert index_name in source
    normalized = " ".join(source.lower().split())
    assert "enforce_investment_layout_version_chain_m10" in normalized
    assert "enforce_investment_input_snapshot_chain_m10" in normalized
    assert "predecessor.version = new.version - 1" in normalized


def _check_names(table: Table) -> set[str]:
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint) and isinstance(constraint.name, str)
    }


EXPECTED_CHECKS = {
    "investment_layout_version": {
        "ck_investment_layout_version_positive",
        "ck_investment_layout_version_key_nonblank",
        "ck_investment_layout_version_snapshot_object",
        "ck_investment_layout_version_root",
        "ck_investment_layout_version_not_self",
    },
    "investment_input_snapshot": {
        "ck_investment_input_snapshot_positive",
        "ck_investment_input_snapshot_case_key_nonblank",
        "ck_investment_input_snapshot_input_object",
        "ck_investment_input_snapshot_public_keys",
        "ck_investment_input_snapshot_nested_shapes",
        "ck_investment_input_snapshot_public_value_types",
        "ck_investment_input_snapshot_afa_reference_values",
        "ck_investment_input_snapshot_bank_header_values",
        "ck_investment_input_snapshot_renter_names_values",
        "ck_investment_input_snapshot_rule_object",
        "ck_investment_input_snapshot_rule_shape",
        "ck_investment_input_snapshot_rule_types",
        "ck_investment_input_snapshot_rule_values",
        "ck_investment_input_snapshot_financing_provenance_object",
        "ck_investment_input_snapshot_financing_provenance",
        "ck_investment_input_snapshot_afa_provenance_object",
        "ck_investment_input_snapshot_afa_provenance",
        "ck_investment_input_snapshot_canonical_version",
        "ck_investment_input_snapshot_canonical_bytes_nonempty",
        "ck_investment_input_snapshot_sha256",
        "ck_investment_input_snapshot_root",
        "ck_investment_input_snapshot_not_self",
    },
    "investment_result_snapshot": {
        "ck_investment_result_snapshot_engine_version_nonblank",
        "ck_investment_result_snapshot_object",
        "ck_investment_result_snapshot_replay_provenance",
        "ck_investment_result_snapshot_complete_shape",
        "ck_investment_result_snapshot_variant_shape",
        "ck_investment_result_snapshot_canonical_version",
        "ck_investment_result_snapshot_canonical_bytes_nonempty",
        "ck_investment_result_snapshot_sha256",
    },
}


def test_m10_i2_orm_check_metadata_exactly_matches_the_migration_contract() -> None:
    """Mapped metadata must expose every CHECK that migration 0045 enforces."""
    source = _migration_source()
    migration_names = set(
        re.findall(
            r'name="(ck_investment_(?:layout_version|input_snapshot|result_snapshot)_[^"]+)"',
            source,
        )
    )
    for table_name, expected in EXPECTED_CHECKS.items():
        prefix = f"ck_{table_name}_"
        migration_table_checks = {name for name in migration_names if name.startswith(prefix)}
        assert _check_names(_table(table_name)) == migration_table_checks
        assert migration_table_checks == expected


@pytest.fixture(scope="module")
def upgraded_owner() -> Iterator[Engine]:
    """Apply the current migration chain; live probes are mandatory in CI."""
    try:
        engine = create_db_engine(DbSettings().direct_url)
        with engine.connect() as connection:
            connection.execute(text((_DB_DIR / "scripts" / "init-app-role.sql").read_text()))
            connection.commit()
    except OperationalError as exc:
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")
    command.upgrade(Config(str(_DB_DIR / "alembic.ini")), "head")
    yield engine
    engine.dispose()


def _valid_facts() -> dict[str, object]:
    return {
        "purchase_price_cents": 30_000_000,
        "acquisition_costs_cents": 3_000_000,
        "monthly_actual_rent_cents": 150_000,
        "vacancy_bp": 500,
        "administration_cents": 50_000,
        "maintenance_cents": 70_000,
        "reserve_cents": 40_000,
        "vacancy_risk_cents": 20_000,
        "equity_cents": 10_000_000,
        "loan_cents": 23_000_000,
        "interest_bp": 350,
        "initial_repayment_bp": 200,
        "marginal_tax_bp": 4_200,
        "building_share_bp": 7_500,
        "afa_rate_bp": 200,
        "analysis_period_months": 12,
        "financing_provenance": "annahme",
        "bank_header": {
            "address": "Musterweg 1, Berlin",
            "property_type": "Wohnhaus",
            "year_built": 1995,
            "area_sqm_x100": 12_000,
            "unit_count": 2,
            "creator": "Eigentümer",
            "export_date": "2026-09-12",
            "layout_version": "bank-view-v1",
        },
    }


def _valid_rules() -> dict[str, object]:
    return asdict(
        InvestmentRuleBundle(
            default_building_share_bp=7_500,
            default_afa_rate_bp=200,
            default_marginal_tax_bp=4_200,
            interest_sensitivity_offsets_bp=(-100, -50, 0, 50, 100),
            repayment_sensitivity_steps_bp=(100, 200, 300, 400),
            dscr_amber_hundredths=100,
            dscr_green_hundredths=120,
            cashflow_amber_cents=0,
            cashflow_green_cents=5_000,
            source_evidence=("Page 07",),
            rechtsstand="07/2026",
            production_blocked=True,
        )
    )


def _result_for(facts: Mapping[str, object], rules: Mapping[str, object]) -> dict[str, object]:
    tuple_rules = dict(rules)
    for key in (
        "interest_sensitivity_offsets_bp",
        "repayment_sensitivity_steps_bp",
        "source_evidence",
    ):
        tuple_rules[key] = tuple(tuple_rules[key])  # type: ignore[arg-type]
    return asdict(
        calculate_investment_snapshot(
            InvestmentInput(facts=facts),
            InvestmentRuleBundle(**tuple_rules),  # type: ignore[arg-type]
        )
    )


def _canonical_input_bytes(
    connection: Connection,
    *,
    facts: Mapping[str, object],
    rules: Mapping[str, object],
    financing: Mapping[str, object],
    afa: Mapping[str, object],
    layout_id: str | None,
) -> bytes:
    value = connection.scalar(
        text(
            "SELECT convert_to(jsonb_build_object("
            "'afa_provenance', CAST(:afa AS jsonb), "
            "'financing_provenance', CAST(:financing AS jsonb), "
            "'input', CAST(:facts AS jsonb), "
            "'layout_version_id', CAST(:layout_id AS text), "
            "'rules', CAST(:rules AS jsonb))::text, 'UTF8')"
        ),
        {
            "afa": json.dumps(afa),
            "financing": json.dumps(financing),
            "facts": json.dumps(facts),
            "layout_id": layout_id,
            "rules": json.dumps(rules),
        },
    )
    assert isinstance(value, bytes)
    return value


def _canonical_result_bytes(connection: Connection, result: Mapping[str, object]) -> bytes:
    value = connection.scalar(
        text("SELECT convert_to(CAST(:result AS jsonb)::text, 'UTF8')"),
        {"result": json.dumps(result)},
    )
    assert isinstance(value, bytes)
    return value


def _input_values(
    connection: Connection,
    account_id: str,
    layout_id: str,
    *,
    facts: Mapping[str, object] | None = None,
    rules: Mapping[str, object] | None = None,
    financing: Mapping[str, object] | None = None,
    afa: Mapping[str, object] | None = None,
    case_key: str | None = None,
    version: int = 1,
    supersedes: str | None = None,
) -> dict[str, object]:
    stored_facts = dict(_valid_facts() if facts is None else facts)
    stored_rules = dict(_valid_rules() if rules is None else rules)
    stored_financing = dict(
        {"source": "annahme", "record_version": "finance-v1"} if financing is None else financing
    )
    result = _result_for(_valid_facts(), _valid_rules())
    raw_afa = result["afa_provenance"] if afa is None else afa
    assert isinstance(raw_afa, Mapping)
    stored_afa = dict(raw_afa)
    canonical = _canonical_input_bytes(
        connection,
        facts=stored_facts,
        rules=stored_rules,
        financing=stored_financing,
        afa=stored_afa,
        layout_id=layout_id,
    )
    return {
        "id": new_id(),
        "account": account_id,
        "case_key": case_key or new_id(),
        "version": version,
        "facts": json.dumps(stored_facts),
        "rules": json.dumps(stored_rules),
        "financing": json.dumps(stored_financing),
        "afa": json.dumps(stored_afa),
        "layout": layout_id,
        "canonical_version": CANONICAL_VERSION,
        "canonical": canonical,
        "sha256": sha256(canonical).hexdigest(),
        "supersedes": supersedes,
        "frozen_at": datetime(2026, 9, 12, tzinfo=UTC),
    }


_INPUT_INSERT = text(
    "INSERT INTO investment_input_snapshot "
    "(id, account_id, case_key, version, input_snapshot, rule_snapshot, "
    "financing_provenance_snapshot, afa_provenance_snapshot, layout_version_id, "
    "canonical_payload_version, canonical_payload_bytes, sha256, "
    "supersedes_input_snapshot_id, frozen_at) VALUES "
    "(:id, :account, :case_key, :version, CAST(:facts AS jsonb), CAST(:rules AS jsonb), "
    "CAST(:financing AS jsonb), CAST(:afa AS jsonb), :layout, :canonical_version, "
    ":canonical, :sha256, :supersedes, :frozen_at)"
)


@contextmanager
def _investment_graph(engine: Engine) -> Iterator[tuple[Connection, str, str]]:
    """One valid account and layout; every probe row is rolled back."""
    account_id, layout_id = new_id(), new_id()
    connection = engine.connect()
    transaction = connection.begin()
    try:
        connection.execute(
            text(
                "INSERT INTO account (id, name, shape, plan) "
                "VALUES (:account, 'M10-I2 audit', 'SOLO', 'TRIAL')"
            ),
            {"account": account_id},
        )
        connection.execute(
            text(
                "INSERT INTO investment_layout_version "
                "(id, account_id, layout_key, version, layout_snapshot, "
                "supersedes_layout_version_id) VALUES "
                "(:id, :account, 'bank-pdf', 1, '{\"layout\": \"bank-view-v1\"}'::jsonb, NULL)"
            ),
            {"id": layout_id, "account": account_id},
        )
        yield connection, account_id, layout_id
    finally:
        transaction.rollback()
        connection.close()


def _expect_rejected(
    connection: Connection, statement: TextClause, values: Mapping[str, object]
) -> None:
    savepoint = connection.begin_nested()
    try:
        with pytest.raises(DBAPIError) as refused:
            connection.execute(statement, values)
    finally:
        savepoint.rollback()
    assert getattr(refused.value.orig, "sqlstate", None) != "42P01"


@pytest.mark.parametrize(
    ("field", "invalid"),
    (
        ("loan_cents", "23000000"),
        ("interest_bp", 350.5),
        ("administration_cents", -1),
        ("vacancy_bp", 10_001),
        ("building_share_bp", -1),
        ("marginal_tax_bp", 10_000),
        ("analysis_period_months", -1),
        ("financing_provenance", "unbelegt"),
        ("renter_names", ["Mieter", 7]),
        ("fabricated_input", 1),
    ),
)
def test_m10_i2_live_rejects_invalid_public_input_values(
    upgraded_owner: Engine, field: str, invalid: object
) -> None:
    with _investment_graph(upgraded_owner) as (connection, account_id, layout_id):
        facts = _valid_facts()
        facts[field] = invalid
        values = _input_values(connection, account_id, layout_id, facts=facts)
        _expect_rejected(connection, _INPUT_INSERT, values)


@pytest.mark.parametrize(
    "changes",
    (
        {"annual_full_afa_cents": 400_000},
        {"annual_full_afa_cents": 400_000, "afa_record_version": "  "},
        {"afa_reference": {"afa_basis_cents": 20_000_000}},
        {
            "afa_reference": {
                "annual_full_afa_cents": 400_000,
                "source": "Page 03",
                "record_version": 3,
            }
        },
        {"afa_reference": {"afa_basis_cents": -1, "source": "P3", "record_version": "v1"}},
        {"afa_reference": {"unexpected": "fabricated"}},
        {"bank_header": {"year_built": 0}},
        {"bank_header": {"area_sqm_x100": 1.5}},
        {"bank_header": {"export_date": ""}},
        {"bank_header": {"unexpected": "fabricated"}},
    ),
)
def test_m10_i2_live_rejects_malformed_nested_public_input(
    upgraded_owner: Engine, changes: Mapping[str, object]
) -> None:
    with _investment_graph(upgraded_owner) as (connection, account_id, layout_id):
        facts = _valid_facts()
        facts.update(changes)
        values = _input_values(connection, account_id, layout_id, facts=facts)
        _expect_rejected(connection, _INPUT_INSERT, values)


@pytest.mark.parametrize(
    ("field", "invalid"),
    (
        ("default_building_share_bp", 10_001),
        ("default_afa_rate_bp", -1),
        ("default_marginal_tax_bp", "4200"),
        ("interest_sensitivity_offsets_bp", [-100, 0, 100]),
        ("interest_sensitivity_offsets_bp", [-100, 0, 0, 50, 100]),
        ("interest_sensitivity_offsets_bp", [-100, 50, 0, 100, 150]),
        ("repayment_sensitivity_steps_bp", [0, 100, 200, 300]),
        ("repayment_sensitivity_steps_bp", [100, 300, 200, 400]),
        ("repayment_sensitivity_steps_bp", [100, 200, 300, 400.5]),
        ("dscr_amber_hundredths", -1),
        ("dscr_green_hundredths", 99),
        ("cashflow_green_cents", -1),
        ("source_evidence", []),
        ("source_evidence", ["Page 07", "  "]),
        ("rechtsstand", "\t"),
        ("production_blocked", "true"),
    ),
)
def test_m10_i2_live_rejects_invalid_rule_bundle(
    upgraded_owner: Engine, field: str, invalid: object
) -> None:
    with _investment_graph(upgraded_owner) as (connection, account_id, layout_id):
        rules = _valid_rules()
        rules[field] = invalid
        values = _input_values(connection, account_id, layout_id, rules=rules)
        _expect_rejected(connection, _INPUT_INSERT, values)


@pytest.mark.parametrize("case", ("missing", "extra"))
def test_m10_i2_live_requires_the_exact_rule_bundle_keys(upgraded_owner: Engine, case: str) -> None:
    with _investment_graph(upgraded_owner) as (connection, account_id, layout_id):
        rules = _valid_rules()
        if case == "missing":
            rules.pop("default_afa_rate_bp")
        else:
            rules["fabricated_rule"] = 1
        values = _input_values(connection, account_id, layout_id, rules=rules)
        _expect_rejected(connection, _INPUT_INSERT, values)


@pytest.mark.parametrize(
    ("field", "invalid"),
    (
        ("financing", {"record_version": "v1"}),
        ("financing", {"source": "annahme"}),
        ("financing", {"source": "annahme", "record_version": 1}),
        ("afa", {"record_version": "v1", "assumption": False}),
        ("afa", {"source": "wizard", "assumption": False}),
        ("afa", {"source": "wizard", "record_version": "v1"}),
        ("afa", {"source": " ", "record_version": "v1", "assumption": False}),
    ),
)
def test_m10_i2_live_requires_complete_typed_provenance(
    upgraded_owner: Engine, field: str, invalid: Mapping[str, object]
) -> None:
    with _investment_graph(upgraded_owner) as (connection, account_id, layout_id):
        kwargs = {field: invalid}
        values = _input_values(connection, account_id, layout_id, **kwargs)  # type: ignore[arg-type]
        _expect_rejected(connection, _INPUT_INSERT, values)


def _result_values(
    connection: Connection,
    account_id: str,
    input_id: str,
    result: Mapping[str, object],
) -> dict[str, object]:
    canonical = _canonical_result_bytes(connection, result)
    return {
        "id": new_id(),
        "account": account_id,
        "input": input_id,
        "engine_version": "investment-engine-v1",
        "result": json.dumps(result),
        "canonical_version": CANONICAL_VERSION,
        "canonical": canonical,
        "sha256": sha256(canonical).hexdigest(),
        "calculated_at": datetime(2026, 9, 12, tzinfo=UTC),
    }


_RESULT_INSERT = text(
    "INSERT INTO investment_result_snapshot "
    "(id, account_id, input_snapshot_id, engine_version, result_snapshot, "
    "canonical_payload_version, canonical_result_bytes, sha256, calculated_at) VALUES "
    "(:id, :account, :input, :engine_version, CAST(:result AS jsonb), "
    ":canonical_version, :canonical, :sha256, :calculated_at)"
)


@pytest.mark.parametrize("missing_key", sorted(RESULT_KEYS))
def test_m10_i2_live_rejects_every_incomplete_result_mapping(
    upgraded_owner: Engine, missing_key: str
) -> None:
    with _investment_graph(upgraded_owner) as (connection, account_id, layout_id):
        input_values = _input_values(connection, account_id, layout_id)
        connection.execute(_INPUT_INSERT, input_values)
        result = _result_for(_valid_facts(), _valid_rules())
        result.pop(missing_key)
        values = _result_values(connection, account_id, str(input_values["id"]), result)
        _expect_rejected(connection, _RESULT_INSERT, values)


@pytest.mark.parametrize(
    ("field", "invalid"),
    (
        ("outcome", "fabricated"),
        ("calculated_values", []),
        ("kpi_slots", []),
        ("source_evidence", ["Page 07", " "]),
        ("applied_conventions", []),
        ("bank_view", []),
        ("interest_sensitivity", {}),
        ("interest_sensitivity", [1]),
        ("repayment_sensitivity", ["fabricated"]),
        ("repayment_axis_meaning", ""),
        ("findings", [4]),
        ("guard", []),
        ("fabricated_result", 1),
    ),
)
def test_m10_i2_live_rejects_wrong_result_field_types(
    upgraded_owner: Engine, field: str, invalid: object
) -> None:
    with _investment_graph(upgraded_owner) as (connection, account_id, layout_id):
        input_values = _input_values(connection, account_id, layout_id)
        connection.execute(_INPUT_INSERT, input_values)
        result = _result_for(_valid_facts(), _valid_rules())
        result[field] = invalid
        values = _result_values(connection, account_id, str(input_values["id"]), result)
        _expect_rejected(connection, _RESULT_INSERT, values)


@pytest.mark.parametrize(
    "case",
    ("calculated_with_guard", "hard_block_with_values", "hard_block_without_guard"),
)
def test_m10_i2_live_rejects_result_variant_fabrication(upgraded_owner: Engine, case: str) -> None:
    with _investment_graph(upgraded_owner) as (connection, account_id, layout_id):
        input_values = _input_values(connection, account_id, layout_id)
        connection.execute(_INPUT_INSERT, input_values)
        if case == "calculated_with_guard":
            result = _result_for(_valid_facts(), _valid_rules())
            result["guard"] = {
                "first_interest_cents": 1,
                "first_repayment_cents": 0,
                "guard_text": "fabricated",
            }
        else:
            blocked_facts = _valid_facts()
            blocked_facts["fixed_monthly_annuity_cents"] = 1
            result = _result_for(blocked_facts, _valid_rules())
            if case == "hard_block_with_values":
                result["calculated_values"] = {"fabricated_numeric_result": 1}
            else:
                result["guard"] = {}
        values = _result_values(connection, account_id, str(input_values["id"]), result)
        _expect_rejected(connection, _RESULT_INSERT, values)


def test_m10_i2_live_persists_unmodified_f09_hard_block_with_financing_provenance(
    upgraded_owner: Engine,
) -> None:
    """The genuine F09 guard happens after financing provenance has been resolved."""
    f09_facts = {
        "loan_cents": 34_000_000,
        "interest_bp": 390,
        "fixed_monthly_annuity_cents": 100_000,
        "financing_provenance": "annahme",
    }
    with _investment_graph(upgraded_owner) as (connection, account_id, layout_id):
        input_values = _input_values(connection, account_id, layout_id, facts=f09_facts)
        connection.execute(_INPUT_INSERT, input_values)
        result = _result_for(f09_facts, _valid_rules())
        assert result["outcome"] == "hard_block"
        assert result["financing_provenance"] == {
            "source": "annahme",
            "badge": "Finanzierung: Annahme",
        }
        assert result["calculated_values"] == {}
        assert result["kpi_slots"] == {}
        assert result["afa_provenance"] == {}
        assert result["tax_provenance"] == {}
        assert result["bank_view"] == {}
        assert result["interest_sensitivity"] == ()
        assert result["repayment_sensitivity"] == ()
        guard = result["guard"]
        assert isinstance(guard, Mapping)
        first_repayment = guard["first_repayment_cents"]
        assert isinstance(first_repayment, int)
        assert first_repayment <= 0
        values = _result_values(connection, account_id, str(input_values["id"]), result)
        connection.execute(_RESULT_INSERT, values)


def test_m10_i2_live_replays_valid_snapshot_byte_for_byte(upgraded_owner: Engine) -> None:
    with _investment_graph(upgraded_owner) as (connection, account_id, layout_id):
        input_values = _input_values(connection, account_id, layout_id)
        connection.execute(_INPUT_INSERT, input_values)
        result = _result_for(_valid_facts(), _valid_rules())
        result_values = _result_values(connection, account_id, str(input_values["id"]), result)
        connection.execute(_RESULT_INSERT, result_values)
        stored = connection.execute(
            text(
                "SELECT input_snapshot, rule_snapshot, canonical_payload_bytes "
                "FROM investment_input_snapshot WHERE id = :id"
            ),
            {"id": input_values["id"]},
        ).one()
        replay = _result_for(stored.input_snapshot, stored.rule_snapshot)
        replay_bytes = _canonical_result_bytes(connection, replay)
        assert replay_bytes == result_values["canonical"]
        assert sha256(replay_bytes).hexdigest() == result_values["sha256"]
        assert stored.canonical_payload_bytes == input_values["canonical"]


@pytest.mark.parametrize(
    ("record", "corruption"),
    (
        ("input", "bytes"),
        ("input", "hash"),
        ("result", "bytes"),
        ("result", "hash"),
    ),
)
def test_m10_i2_live_rejects_corrupt_canonical_evidence(
    upgraded_owner: Engine, record: str, corruption: str
) -> None:
    with _investment_graph(upgraded_owner) as (connection, account_id, layout_id):
        input_values = _input_values(connection, account_id, layout_id)
        if record == "input":
            input_values["canonical" if corruption == "bytes" else "sha256"] = (
                b"corrupt" if corruption == "bytes" else "f" * 64
            )
            _expect_rejected(connection, _INPUT_INSERT, input_values)
            return
        connection.execute(_INPUT_INSERT, input_values)
        result = _result_for(_valid_facts(), _valid_rules())
        result_values = _result_values(connection, account_id, str(input_values["id"]), result)
        result_values["canonical" if corruption == "bytes" else "sha256"] = (
            b"corrupt" if corruption == "bytes" else "f" * 64
        )
        _expect_rejected(connection, _RESULT_INSERT, result_values)


@pytest.mark.parametrize("table", TABLES)
@pytest.mark.parametrize("verb", ("UPDATE", "DELETE"))
def test_m10_i2_live_refuses_every_update_and_delete(
    upgraded_owner: Engine, table: str, verb: str
) -> None:
    with _investment_graph(upgraded_owner) as (connection, account_id, layout_id):
        input_values = _input_values(connection, account_id, layout_id)
        connection.execute(_INPUT_INSERT, input_values)
        result = _result_for(_valid_facts(), _valid_rules())
        result_values = _result_values(connection, account_id, str(input_values["id"]), result)
        connection.execute(_RESULT_INSERT, result_values)
        ids = {
            "investment_layout_version": layout_id,
            "investment_input_snapshot": input_values["id"],
            "investment_result_snapshot": result_values["id"],
        }
        statement = (
            text(f"UPDATE {table} SET account_id = account_id WHERE id = :id")
            if verb == "UPDATE"
            else text(f"DELETE FROM {table} WHERE id = :id")
        )
        _expect_rejected(connection, statement, {"id": ids[table]})


@pytest.mark.parametrize("case", ("skipped", "mismatched", "forked"))
def test_m10_i2_live_refuses_invalid_input_predecessor_chains(
    upgraded_owner: Engine, case: str
) -> None:
    with _investment_graph(upgraded_owner) as (connection, account_id, layout_id):
        root = _input_values(connection, account_id, layout_id, case_key="case-a")
        connection.execute(_INPUT_INSERT, root)
        if case == "forked":
            first = _input_values(
                connection,
                account_id,
                layout_id,
                case_key="case-a",
                version=2,
                supersedes=str(root["id"]),
            )
            connection.execute(_INPUT_INSERT, first)
            candidate = _input_values(
                connection,
                account_id,
                layout_id,
                case_key="case-a",
                version=3,
                supersedes=str(root["id"]),
            )
        else:
            candidate = _input_values(
                connection,
                account_id,
                layout_id,
                case_key="case-b" if case == "mismatched" else "case-a",
                version=2 if case == "mismatched" else 3,
                supersedes=str(root["id"]),
            )
        _expect_rejected(connection, _INPUT_INSERT, candidate)


@pytest.mark.parametrize("case", ("skipped", "mismatched", "forked"))
def test_m10_i2_live_refuses_invalid_layout_predecessor_chains(
    upgraded_owner: Engine, case: str
) -> None:
    with _investment_graph(upgraded_owner) as (connection, account_id, layout_id):
        statement = text(
            "INSERT INTO investment_layout_version "
            "(id, account_id, layout_key, version, layout_snapshot, "
            "supersedes_layout_version_id) VALUES "
            '(:id, :account, :layout_key, :version, \'{"layout": "v2"}\'::jsonb, '
            ":supersedes)"
        )
        if case == "forked":
            connection.execute(
                statement,
                {
                    "id": new_id(),
                    "account": account_id,
                    "layout_key": "bank-pdf",
                    "version": 2,
                    "supersedes": layout_id,
                },
            )
        candidate = {
            "id": new_id(),
            "account": account_id,
            "layout_key": "other-layout" if case == "mismatched" else "bank-pdf",
            "version": 2 if case in {"mismatched", "forked"} else 3,
            "supersedes": layout_id,
        }
        _expect_rejected(connection, statement, candidate)
