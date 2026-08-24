"""Red U4b persistence contract for authoritative U5 calculation inputs."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from lokara_db import DbSettings, create_db_engine, new_id
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Connection,
    Engine,
    ForeignKeyConstraint,
    Numeric,
    UniqueConstraint,
    inspect,
    text,
)
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.sql.schema import Table

_DB_DIR = Path(__file__).resolve().parent.parent


def _migration() -> Path:
    revisions = list((_DB_DIR / "alembic" / "versions").glob("0023_*.py"))
    assert len(revisions) == 1, "migration 0023 is the missing U4b implementation"
    return revisions[0]


def _models() -> tuple[type[Any], type[Any], type[Any], type[Any]]:
    from lokara_db import models

    degree_day = getattr(models, "UviMonthlyDegreeDay", None)
    configuration = getattr(models, "BuildingUviConfiguration", None)
    building_evidence = getattr(models, "UviBuildingMonthlyEvidence", None)
    evidence_source = getattr(models, "UviBuildingMonthlyEvidenceSource", None)
    assert degree_day is not None, "U4b UviMonthlyDegreeDay model is missing"
    assert configuration is not None, "U4b BuildingUviConfiguration model is missing"
    assert building_evidence is not None, "U4b UviBuildingMonthlyEvidence model is missing"
    assert evidence_source is not None, "U4b UviBuildingMonthlyEvidenceSource model is missing"
    return degree_day, configuration, building_evidence, evidence_source


def _table(model: type[Any]) -> Table:
    table = inspect(model).local_table
    assert isinstance(table, Table)
    return table


def _check_text(table: Table) -> str:
    return " ".join(
        constraint.sqltext.text
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    )


def _has_fk(table: Table, local: tuple[str, ...], remote_table: str) -> bool:
    return any(
        isinstance(constraint, ForeignKeyConstraint)
        and tuple(element.parent.name for element in constraint.elements) == local
        and {element.column.table.name for element in constraint.elements} == {remote_table}
        and "account_id" in {element.parent.name for element in constraint.elements}
        and "account_id" in {element.column.name for element in constraint.elements}
        for constraint in table.constraints
    )


def _has_unique(table: Table, columns: tuple[str, ...]) -> bool:
    return any(
        isinstance(constraint, UniqueConstraint)
        and tuple(column.name for column in constraint.columns) == columns
        for constraint in table.constraints
    )


def test_u4b_migration_0023_is_new_history() -> None:
    """U4b-DB-01: prerequisites add 0023 after U4; 0022 is never amended."""
    source = _migration().read_text()
    assert 'revision = "0023"' in source
    assert 'down_revision = "0022"' in source


def test_u4b_0023_allows_only_the_complete_optional_uvi_run_snapshots() -> None:
    """U5-DB-00: 0023, not historical 0022, enables raw Block C plus Block D archives."""
    from lokara_db import Base

    run = Base.metadata.tables["uvi_run"]
    for column in (
        "heizspiegel_vintage",
        "station_assignment_id",
        "station_id",
        "station_distance_km",
    ):
        assert run.columns[column].nullable is True
    checks = _check_text(run)
    assert "station_assignment_id IS NULL" in checks
    assert "station_id IS NULL" in checks
    assert "station_distance_km IS NULL" in checks
    assert "station_assignment_id IS NOT NULL" in checks
    assert "station_id IS NOT NULL" in checks
    assert "station_distance_km IS NOT NULL" in checks

    source = _migration().read_text()
    for column in (
        "heizspiegel_vintage",
        "station_assignment_id",
        "station_id",
        "station_distance_km",
    ):
        assert f'op.alter_column("uvi_run", "{column}", nullable=True)' in source
    assert "uvi_run_station_snapshot_all_or_none" in source


def test_u4b_models_are_account_scoped_immutable_records() -> None:
    """U4b-DB-02: both prerequisite records are insert-only tenant data."""
    for model in _models():
        table = _table(model)
        assert {"id", "account_id", "created_at"} <= set(table.columns.keys())
        assert table.columns["account_id"].nullable is False
        assert {"updated_at", "deleted_at", "is_current"}.isdisjoint(table.columns.keys())


def test_u4b_monthly_degree_day_binds_exact_assignment_and_source() -> None:
    """U4b-DB-03: the selected station/month and exact Kd remain reproducible."""
    degree_day, _, _, _ = _models()
    table = _table(degree_day)
    assert {
        "station_assignment_id",
        "station_id",
        "month",
        "monthly_degree_days",
        "valid_day_count",
        "source_file",
        "source_id",
        "provenance",
        "rechtsstand",
        "verification_status",
        "monthly_annual_share",
        "supersedes_degree_day_id",
    } <= set(table.columns.keys())
    assert _has_fk(
        table,
        ("station_assignment_id", "account_id", "station_id", "month"),
        "uvi_station_assignment",
    )
    for column in ("monthly_degree_days", "monthly_annual_share"):
        assert isinstance(table.columns[column].type, Numeric)
        assert table.columns[column].type.python_type is Decimal
    assert table.columns["monthly_annual_share"].nullable
    assert _has_fk(
        table,
        (
            "supersedes_degree_day_id",
            "account_id",
            "station_assignment_id",
            "station_id",
            "month",
        ),
        "uvi_monthly_degree_day",
    )
    checks = _check_text(table)
    assert "valid_day_count" in checks and "25" in checks
    assert "monthly_degree_days" in checks
    assert "monthly_annual_share" in checks and "1" in checks
    assert "id <> supersedes_degree_day_id" in checks


def test_u4b_building_configuration_is_temporal_and_source_backed() -> None:
    """U4b-DB-04: U2 energy/configuration facts are versioned, never inferred."""
    _, configuration, _, _ = _models()
    table = _table(configuration)
    assert {
        "building_id",
        "energy_source",
        "energy_reference",
        "explicit_hkv_allocator",
        "calorific_factor",
        "valid_from",
        "valid_to",
        "source_id",
        "rechtsstand",
        "verification_status",
        "supersedes_configuration_id",
    } <= set(table.columns.keys())
    assert _has_fk(table, ("building_id", "account_id"), "building")
    assert _has_fk(
        table,
        ("supersedes_configuration_id", "account_id", "building_id"),
        "building_uvi_configuration",
    )
    assert isinstance(table.columns["calorific_factor"].type, Numeric)
    assert table.columns["calorific_factor"].type.python_type is Decimal
    assert table.columns["calorific_factor"].nullable
    checks = _check_text(table)
    assert "valid_from" in checks and "valid_to" in checks
    assert "calorific_factor" in checks and "> 0" in checks
    assert "id <> supersedes_configuration_id" in checks
    for identifier in ("Erdgas", "Heizoel", "Fernwaerme", "Waermepumpe", "Holzpellets"):
        assert identifier in checks


def test_u5_source_identity_pairs_are_persisted_and_archived_from_the_stored_rows() -> None:
    """U5-BOUNDARY-04: configuration and building evidence retain source type plus id."""
    _, configuration, evidence, _ = _models()
    for model in (configuration, evidence):
        table = _table(model)
        assert {"source_type", "source_id"} <= set(table.columns.keys())
        assert table.columns["source_type"].nullable is False
        assert table.columns["source_id"].nullable is False

    router_source = (_DB_DIR.parents[1] / "apps/api/src/lokara_api/routers/uvi_runs.py").read_text()
    for stored_identity in (
        "configuration.source_type",
        "configuration.source_id",
        "building_evidence.source_type",
        "building_evidence.source_id",
    ):
        assert stored_identity in router_source


def test_u4b_building_month_evidence_binds_main_meter_and_correction_context() -> None:
    """U4b-DB-05: building heat/HKV evidence has no fabricated unit or tenancy."""
    _, _, evidence, _ = _models()
    table = _table(evidence)
    assert {
        "building_id",
        "main_meter_id",
        "month",
        "measured_building_heat_kwh_x1000",
        "building_hkv_movement_x1000",
        "source_id",
        "raw_evidence",
        "supersedes_evidence_id",
    } <= set(table.columns.keys())
    assert {"unit_id", "tenancy_id"}.isdisjoint(table.columns.keys())
    assert _has_fk(table, ("building_id", "account_id"), "building")
    assert _has_fk(table, ("main_meter_id", "account_id", "building_id"), "meter")
    assert _has_fk(
        table,
        ("supersedes_evidence_id", "account_id", "building_id", "month"),
        "uvi_building_monthly_evidence",
    )
    assert isinstance(table.columns["measured_building_heat_kwh_x1000"].type, BigInteger)
    checks = _check_text(table)
    assert "measured_building_heat_kwh_x1000" in checks
    assert "building_hkv_movement_x1000" in checks
    assert "raw_evidence" in checks
    assert "id <> supersedes_evidence_id" in checks
    assert _has_unique(table, ("id", "account_id", "building_id", "month"))
    assert _has_unique(table, ("id", "account_id", "main_meter_id"))


def test_u4b_building_evidence_source_links_real_readings_to_the_selected_meter() -> None:
    """U4b-DB-06: source links bind both parent sides through the same meter."""
    from lokara_db.models import MeterReading

    _, _, _, evidence_source = _models()
    table = _table(evidence_source)
    assert {
        "id",
        "account_id",
        "building_monthly_evidence_id",
        "main_meter_id",
        "meter_reading_id",
        "created_at",
    } <= set(table.columns.keys())
    assert _has_fk(
        table,
        ("building_monthly_evidence_id", "account_id", "main_meter_id"),
        "uvi_building_monthly_evidence",
    )
    assert _has_fk(
        table,
        ("meter_reading_id", "account_id", "main_meter_id"),
        "meter_reading",
    )
    assert _has_unique(
        table,
        ("account_id", "building_monthly_evidence_id", "meter_reading_id"),
    )
    assert _has_unique(_table(MeterReading), ("id", "account_id", "meter_id"))


def test_u4b_migration_installs_rls_append_only_and_correction_guards() -> None:
    """U4b-DB-06: migration text contains each database-enforced invariant."""
    normalized = " ".join(_migration().read_text().lower().split())
    for table_name in (
        "uvi_monthly_degree_day",
        "building_uvi_configuration",
        "uvi_building_monthly_evidence",
        "uvi_building_monthly_evidence_source",
    ):
        assert f"create_table( {table_name!r}" in normalized or table_name in normalized
        assert f"alter table {table_name} enable row level security" in normalized
        assert f"alter table {table_name} force row level security" in normalized
        assert f"on {table_name}" in normalized and "with check" in normalized
        assert table_name in normalized and "append-only" in normalized
    for correction_column in (
        "supersedes_degree_day_id",
        "supersedes_configuration_id",
        "supersedes_evidence_id",
    ):
        assert correction_column in normalized
    assert "direct_successor" in normalized
    assert "create constraint trigger" in normalized
    assert "deferrable initially deferred" in normalized
    assert "building_monthly_evidence_source" in normalized
    for eligibility_marker in ("unit_id", "kind", "measurement_unit", "heat", "kwh"):
        assert eligibility_marker in normalized


@pytest.fixture(scope="module")
def owner() -> Iterator[Engine]:
    if not list((_DB_DIR / "alembic" / "versions").glob("0023_*.py")):
        pytest.skip("migration 0023 is the missing U4b implementation")
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


@contextmanager
def _graph(owner: Engine) -> Iterator[tuple[Connection, dict[str, str]]]:
    ids = {
        name: new_id()
        for name in (
            "account_a",
            "account_b",
            "building",
            "other_building",
            "unit",
            "assignment",
            "main_meter",
            "replacement_main_meter",
            "unit_heat_meter",
            "building_water_meter",
            "building_heat_cubic_meter",
            "raw_reading",
            "replacement_raw_reading",
            "unit_heat_reading",
            "building_water_reading",
            "building_heat_cubic_reading",
        )
    }
    connection = owner.connect()
    transaction = connection.begin()
    try:
        connection.execute(
            text(
                "INSERT INTO account (id, name, shape, plan) VALUES"
                " (:account_a, 'U4b A', 'SOLO', 'TRIAL'),"
                " (:account_b, 'U4b B', 'SOLO', 'TRIAL')"
            ),
            ids,
        )
        connection.execute(
            text(
                "INSERT INTO building (id, account_id, name, street, postal_code, city)"
                " VALUES (:building, :account_a, 'Haus', 'Weg 1', '10115', 'Berlin'),"
                " (:other_building, :account_a, 'Haus 2', 'Weg 2', '20095', 'Hamburg')"
            ),
            ids,
        )
        connection.execute(
            text(
                "INSERT INTO unit (id, account_id, building_id, label, area_sqm_x100)"
                " VALUES (:unit, :account_a, :building, 'Wohnung', 8000)"
            ),
            ids,
        )
        connection.execute(
            text(
                "INSERT INTO meter"
                " (id, account_id, building_id, unit_id, kind, measurement_unit, serial,"
                " calibration_valid_until, valuation_factor_x1000) VALUES"
                " (:main_meter, :account_a, :building, NULL, 'HEAT', 'KWH', 'U4B-MAIN',"
                " '2029-12-31', 1000),"
                " (:replacement_main_meter, :account_a, :building, NULL, 'HEAT', 'KWH',"
                " 'U4B-MAIN-2', '2029-12-31', 1000),"
                " (:unit_heat_meter, :account_a, :building, :unit, 'HEAT', 'KWH',"
                " 'U4B-UNIT', '2029-12-31', 1000),"
                " (:building_water_meter, :account_a, :building, NULL, 'COLD_WATER',"
                " 'CUBIC_METRE', 'U4B-WATER', '2029-12-31', NULL),"
                " (:building_heat_cubic_meter, :account_a, :building, NULL, 'HEAT',"
                " 'CUBIC_METRE', 'U4B-HEAT-M3', '2029-12-31', 1000)"
            ),
            ids,
        )
        connection.execute(
            text(
                "INSERT INTO meter_reading"
                " (id, account_id, meter_id, read_at, value_x1000, reason, source) VALUES"
                " (:raw_reading, :account_a, :main_meter, '2025-01-01', 100000,"
                " 'PERIODIC', 'MANUAL'),"
                " (:replacement_raw_reading, :account_a, :replacement_main_meter,"
                " '2025-01-01', 100000, 'PERIODIC', 'MANUAL'),"
                " (:unit_heat_reading, :account_a, :unit_heat_meter, '2025-01-01', 100000,"
                " 'PERIODIC', 'MANUAL'),"
                " (:building_water_reading, :account_a, :building_water_meter, '2025-01-01',"
                " 100000, 'PERIODIC', 'MANUAL'),"
                " (:building_heat_cubic_reading, :account_a, :building_heat_cubic_meter,"
                " '2025-01-01', 100000, 'PERIODIC', 'MANUAL')"
            ),
            ids,
        )
        connection.execute(
            text(
                "INSERT INTO uvi_station_assignment"
                " (id, account_id, postal_code, month, station_id, distance_km,"
                " source_type, source_id) VALUES"
                " (:assignment, :account_a, '10115', '2025-01-01', '001', 12.345,"
                " 'DWD_MONTHLY', 'monthly-source-202501:001')"
            ),
            ids,
        )
        yield connection, ids
    finally:
        transaction.rollback()
        connection.close()


def test_u4b_records_reject_real_cross_account_writes(owner: Engine) -> None:
    """U4b-DB-06: B's app context cannot stamp either new row with account A."""
    with _graph(owner) as (connection, ids):
        connection.execute(text("SET LOCAL ROLE lokara_app"))
        connection.execute(
            text("SELECT set_config('app.account_id', :account_b, true)"),
            ids,
        )
        inserts = (
            text(
                "INSERT INTO uvi_monthly_degree_day"
                " (id, account_id, station_assignment_id, station_id, month,"
                " monthly_degree_days, valid_day_count, source_file, source_id, provenance,"
                " rechtsstand, verification_status, monthly_annual_share,"
                " supersedes_degree_day_id) VALUES"
                " (:id, :account_a, :assignment, '001', '2025-01-01', 590.25, 31,"
                " 'monthly-source-202501', 'DWD:001:202501',"
                " '{\"source\":\"DWD\"}'::jsonb, '08/2026',"
                " 'verify-before-production', NULL, NULL)"
            ),
            text(
                "INSERT INTO building_uvi_configuration"
                " (id, account_id, building_id, energy_source, energy_reference,"
                " explicit_hkv_allocator, calorific_factor, valid_from, valid_to, source_type,"
                " source_id,"
                " rechtsstand, verification_status, supersedes_configuration_id) VALUES"
                " (:id, :account_a, :building, 'Erdgas', 'HO', false, NULL, '2026-01-01',"
                " NULL, 'UVI_CONFIGURATION', 'caller-source', '08/2026',"
                " 'verify-before-production', NULL)"
            ),
            text(
                "INSERT INTO uvi_building_monthly_evidence"
                " (id, account_id, building_id, main_meter_id, month,"
                " measured_building_heat_kwh_x1000, building_hkv_movement_x1000, source_type,"
                " source_id,"
                " raw_evidence, supersedes_evidence_id) VALUES"
                " (:id, :account_a, :building, :main_meter, '2025-01-01', 100000, NULL,"
                " 'UVI_BUILDING_EVIDENCE', 'main-meter:202501',"
                ' \'{"reading_ids":["source"]}\'::jsonb, NULL)'
            ),
            text(
                "INSERT INTO uvi_building_monthly_evidence_source"
                " (id, account_id, building_monthly_evidence_id, main_meter_id,"
                " meter_reading_id) VALUES"
                " (:id, :account_a, :evidence, :main_meter, :raw_reading)"
            ),
        )
        for statement in inserts:
            savepoint = connection.begin_nested()
            try:
                with pytest.raises(DBAPIError) as refused:
                    connection.execute(
                        statement,
                        {**ids, "id": new_id(), "evidence": new_id()},
                    )
            finally:
                savepoint.rollback()
            assert getattr(refused.value.orig, "sqlstate", None) == "42501"


def test_u4b_configuration_supersedes_open_row_by_insert_without_branching(owner: Engine) -> None:
    """U4b-DB-07: an open predecessor gains one later same-building successor."""
    with _graph(owner) as (connection, ids):
        insert = text(
            "INSERT INTO building_uvi_configuration"
            " (id, account_id, building_id, energy_source, energy_reference,"
            " explicit_hkv_allocator, calorific_factor, valid_from, valid_to, source_type,"
            " source_id,"
            " rechtsstand, verification_status, supersedes_configuration_id) VALUES"
            " (:id, :account_a, :building_id, 'Erdgas', 'HO', false, NULL, :valid_from,"
            " :valid_to, 'UVI_CONFIGURATION', :source_id, '08/2026',"
            " 'verify-before-production', :supersedes)"
        )
        root = new_id()
        connection.execute(
            insert,
            {
                **ids,
                "id": root,
                "building_id": ids["building"],
                "valid_from": date(2026, 1, 1),
                "valid_to": None,
                "source_id": "source-1",
                "supersedes": None,
            },
        )
        for rejected in (
            {
                **ids,
                "id": new_id(),
                "building_id": ids["building"],
                "valid_from": date(2026, 4, 1),
                "valid_to": None,
                "source_id": "second-root",
                "supersedes": None,
            },
            {
                **ids,
                "id": (self_id := new_id()),
                "building_id": ids["building"],
                "valid_from": date(2026, 4, 1),
                "valid_to": None,
                "source_id": "self-reference",
                "supersedes": self_id,
            },
        ):
            savepoint = connection.begin_nested()
            try:
                with pytest.raises(DBAPIError):
                    connection.execute(insert, rejected)
            finally:
                savepoint.rollback()
        successor = {
            **ids,
            "id": new_id(),
            "building_id": ids["building"],
            "valid_from": date(2026, 7, 1),
            "valid_to": None,
            "source_id": "source-2",
            "supersedes": root,
        }
        connection.execute(insert, successor)
        for changes in (
            {"id": new_id(), "source_id": "branch"},
            {
                "id": new_id(),
                "building_id": ids["other_building"],
                "source_id": "foreign-building",
            },
        ):
            savepoint = connection.begin_nested()
            try:
                with pytest.raises(DBAPIError):
                    connection.execute(insert, {**successor, **changes})
            finally:
                savepoint.rollback()


def test_u4b_degree_day_and_building_evidence_have_one_correction_head(owner: Engine) -> None:
    """U4b-DB-08: correction INSERTs retain context and cannot branch."""
    with _graph(owner) as (connection, ids):
        degree_insert = text(
            "INSERT INTO uvi_monthly_degree_day"
            " (id, account_id, station_assignment_id, station_id, month,"
            " monthly_degree_days, valid_day_count, source_file, source_id, provenance,"
            " rechtsstand, verification_status, monthly_annual_share,"
            " supersedes_degree_day_id) VALUES"
            " (:id, :account_a, :assignment, '001', '2025-01-01', 590.25, 31,"
            " 'monthly-source-202501', :source_id, '{\"source\":\"DWD\"}'::jsonb,"
            " '08/2026', 'verify-before-production', NULL, :supersedes)"
        )
        evidence_insert = text(
            "INSERT INTO uvi_building_monthly_evidence"
            " (id, account_id, building_id, main_meter_id, month,"
            " measured_building_heat_kwh_x1000, building_hkv_movement_x1000, source_type,"
            " source_id,"
            " raw_evidence, supersedes_evidence_id) VALUES"
            " (:id, :account_a, :building, :main_meter, '2025-01-01', 100000, NULL,"
            " 'UVI_BUILDING_EVIDENCE', :source_id,"
            ' \'{"reading_ids":["source"]}\'::jsonb, :supersedes)'
        )
        for insert in (degree_insert, evidence_insert):
            root = new_id()
            connection.execute(
                insert,
                {
                    **ids,
                    "id": root,
                    "source_id": "source-1",
                    "supersedes": None,
                },
            )
            for rejected in (
                {
                    **ids,
                    "id": new_id(),
                    "source_id": "second-root",
                    "supersedes": None,
                },
                {
                    **ids,
                    "id": (self_id := new_id()),
                    "source_id": "self-reference",
                    "supersedes": self_id,
                },
            ):
                savepoint = connection.begin_nested()
                try:
                    with pytest.raises(DBAPIError):
                        connection.execute(insert, rejected)
                finally:
                    savepoint.rollback()
            successor = {
                **ids,
                "id": new_id(),
                "source_id": "source-2",
                "supersedes": root,
            }
            connection.execute(insert, successor)
            savepoint = connection.begin_nested()
            try:
                with pytest.raises(DBAPIError):
                    connection.execute(insert, {**successor, "id": new_id()})
            finally:
                savepoint.rollback()


def test_u4b_evidence_chain_is_per_building_month_and_can_replace_main_meter(
    owner: Engine,
) -> None:
    """U4b-DB-09: a correction may replace the meter; a second root may not."""
    with _graph(owner) as (connection, ids):
        evidence_insert = text(
            "INSERT INTO uvi_building_monthly_evidence"
            " (id, account_id, building_id, main_meter_id, month,"
            " measured_building_heat_kwh_x1000, building_hkv_movement_x1000, source_type,"
            " source_id,"
            " raw_evidence, supersedes_evidence_id) VALUES"
            " (:id, :account_a, :building, :meter, '2025-01-01', 100000, NULL,"
            " 'UVI_BUILDING_EVIDENCE', :source_id,"
            ' \'{"reading_ids":["source"]}\'::jsonb, :supersedes)'
        )
        source_insert = text(
            "INSERT INTO uvi_building_monthly_evidence_source"
            " (id, account_id, building_monthly_evidence_id, main_meter_id,"
            " meter_reading_id) VALUES"
            " (:source_link, :account_a, :evidence, :meter, :reading)"
        )
        root = new_id()
        connection.execute(
            evidence_insert,
            {
                **ids,
                "id": root,
                "meter": ids["main_meter"],
                "source_id": "root",
                "supersedes": None,
            },
        )
        connection.execute(
            source_insert,
            {
                **ids,
                "source_link": new_id(),
                "evidence": root,
                "meter": ids["main_meter"],
                "reading": ids["raw_reading"],
            },
        )
        savepoint = connection.begin_nested()
        try:
            with pytest.raises(DBAPIError):
                connection.execute(
                    evidence_insert,
                    {
                        **ids,
                        "id": new_id(),
                        "meter": ids["replacement_main_meter"],
                        "source_id": "competing-root",
                        "supersedes": None,
                    },
                )
        finally:
            savepoint.rollback()

        replacement = new_id()
        connection.execute(
            evidence_insert,
            {
                **ids,
                "id": replacement,
                "meter": ids["replacement_main_meter"],
                "source_id": "replacement",
                "supersedes": root,
            },
        )
        connection.execute(
            source_insert,
            {
                **ids,
                "source_link": new_id(),
                "evidence": replacement,
                "meter": ids["replacement_main_meter"],
                "reading": ids["replacement_raw_reading"],
            },
        )
        connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_u4b_evidence_requires_a_real_source_link_at_transaction_boundary(
    owner: Engine,
) -> None:
    """U4b-DB-10: a deferred constraint permits parent+links but rejects a bare parent."""
    with _graph(owner) as (connection, ids):
        insert = text(
            "INSERT INTO uvi_building_monthly_evidence"
            " (id, account_id, building_id, main_meter_id, month,"
            " measured_building_heat_kwh_x1000, building_hkv_movement_x1000, source_type,"
            " source_id,"
            " raw_evidence, supersedes_evidence_id) VALUES"
            " (:id, :account_a, :building, :main_meter, '2025-01-01', 100000, NULL,"
            " 'UVI_BUILDING_EVIDENCE', 'source',"
            ' \'{"reading_ids":["source"]}\'::jsonb, NULL)'
        )
        savepoint = connection.begin_nested()
        try:
            connection.execute(insert, {**ids, "id": new_id()})
            with pytest.raises(DBAPIError):
                connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        finally:
            savepoint.rollback()
        connection.execute(text("SET CONSTRAINTS ALL DEFERRED"))

        wrong_reading_savepoint = connection.begin_nested()
        try:
            evidence_id = new_id()
            connection.execute(insert, {**ids, "id": evidence_id})
            with pytest.raises(DBAPIError):
                connection.execute(
                    text(
                        "INSERT INTO uvi_building_monthly_evidence_source"
                        " (id, account_id, building_monthly_evidence_id, main_meter_id,"
                        " meter_reading_id) VALUES"
                        " (:id, :account_a, :evidence, :main_meter, :replacement_raw_reading)"
                    ),
                    {**ids, "id": new_id(), "evidence": evidence_id},
                )
        finally:
            wrong_reading_savepoint.rollback()


def test_u4b_evidence_rejects_non_main_or_non_kwh_heat_meters(owner: Engine) -> None:
    """U4b-DB-11: only a building-level HEAT/KWH meter can support evidence."""
    with _graph(owner) as (connection, ids):
        insert = text(
            "INSERT INTO uvi_building_monthly_evidence"
            " (id, account_id, building_id, main_meter_id, month,"
            " measured_building_heat_kwh_x1000, building_hkv_movement_x1000, source_type,"
            " source_id,"
            " raw_evidence, supersedes_evidence_id) VALUES"
            " (:id, :account_a, :building, :meter, '2025-01-01', 100000, NULL,"
            " 'UVI_BUILDING_EVIDENCE', 'invalid-meter',"
            ' \'{"reading_ids":["source"]}\'::jsonb, NULL)'
        )
        invalid_meters = (
            (ids["unit_heat_meter"], ids["unit_heat_reading"]),
            (ids["building_water_meter"], ids["building_water_reading"]),
            (ids["building_heat_cubic_meter"], ids["building_heat_cubic_reading"]),
        )
        for meter_id, reading_id in invalid_meters:
            savepoint = connection.begin_nested()
            try:
                with pytest.raises(DBAPIError):
                    evidence_id = new_id()
                    connection.execute(
                        insert,
                        {**ids, "id": evidence_id, "meter": meter_id},
                    )
                    connection.execute(
                        text(
                            "INSERT INTO uvi_building_monthly_evidence_source"
                            " (id, account_id, building_monthly_evidence_id, main_meter_id,"
                            " meter_reading_id) VALUES"
                            " (:id, :account_a, :evidence, :meter, :reading)"
                        ),
                        {
                            **ids,
                            "id": new_id(),
                            "evidence": evidence_id,
                            "meter": meter_id,
                            "reading": reading_id,
                        },
                    )
                    connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            finally:
                savepoint.rollback()
            connection.execute(text("SET CONSTRAINTS ALL DEFERRED"))


def test_u4b_records_are_append_only_in_the_database(owner: Engine) -> None:
    """U4b-DB-09: corrections append; no prerequisite row is rewritten."""
    with _graph(owner) as (connection, ids):
        degree_day_id = new_id()
        configuration_id = new_id()
        building_evidence_id = new_id()
        building_evidence_source_id = new_id()
        connection.execute(
            text(
                "INSERT INTO uvi_monthly_degree_day"
                " (id, account_id, station_assignment_id, station_id, month,"
                " monthly_degree_days, valid_day_count, source_file, source_id, provenance,"
                " rechtsstand, verification_status, monthly_annual_share,"
                " supersedes_degree_day_id) VALUES"
                " (:id, :account_a, :assignment, '001', '2025-01-01', 590.25, 31,"
                " 'monthly-source-202501', 'DWD:001:202501',"
                " '{\"source\":\"DWD\"}'::jsonb, '08/2026',"
                " 'verify-before-production', NULL, NULL)"
            ),
            {**ids, "id": degree_day_id},
        )
        connection.execute(
            text(
                "INSERT INTO building_uvi_configuration"
                " (id, account_id, building_id, energy_source, energy_reference,"
                " explicit_hkv_allocator, calorific_factor, valid_from, valid_to, source_type,"
                " source_id,"
                " rechtsstand, verification_status, supersedes_configuration_id) VALUES"
                " (:id, :account_a, :building, 'Erdgas', 'HO', false, NULL, '2026-01-01',"
                " NULL, 'UVI_CONFIGURATION', 'caller-source', '08/2026',"
                " 'verify-before-production', NULL)"
            ),
            {**ids, "id": configuration_id},
        )
        connection.execute(
            text(
                "INSERT INTO uvi_building_monthly_evidence"
                " (id, account_id, building_id, main_meter_id, month,"
                " measured_building_heat_kwh_x1000, building_hkv_movement_x1000, source_type,"
                " source_id,"
                " raw_evidence, supersedes_evidence_id) VALUES"
                " (:id, :account_a, :building, :main_meter, '2025-01-01', 100000, NULL,"
                " 'UVI_BUILDING_EVIDENCE', 'main-meter:202501',"
                ' \'{"reading_ids":["source"]}\'::jsonb, NULL)'
            ),
            {**ids, "id": building_evidence_id},
        )
        connection.execute(
            text(
                "INSERT INTO uvi_building_monthly_evidence_source"
                " (id, account_id, building_monthly_evidence_id, main_meter_id,"
                " meter_reading_id) VALUES"
                " (:id, :account_a, :evidence, :main_meter, :raw_reading)"
            ),
            {**ids, "id": building_evidence_source_id, "evidence": building_evidence_id},
        )
        for statement, row_id in (
            (
                "UPDATE uvi_monthly_degree_day SET valid_day_count = 30 WHERE id = :id",
                degree_day_id,
            ),
            ("DELETE FROM uvi_monthly_degree_day WHERE id = :id", degree_day_id),
            (
                "UPDATE building_uvi_configuration SET source_id = 'changed' WHERE id = :id",
                configuration_id,
            ),
            ("DELETE FROM building_uvi_configuration WHERE id = :id", configuration_id),
            (
                "UPDATE uvi_building_monthly_evidence SET source_id = 'changed' WHERE id = :id",
                building_evidence_id,
            ),
            ("DELETE FROM uvi_building_monthly_evidence WHERE id = :id", building_evidence_id),
            (
                "UPDATE uvi_building_monthly_evidence_source"
                " SET meter_reading_id = meter_reading_id WHERE id = :id",
                building_evidence_source_id,
            ),
            (
                "DELETE FROM uvi_building_monthly_evidence_source WHERE id = :id",
                building_evidence_source_id,
            ),
        ):
            savepoint = connection.begin_nested()
            try:
                with pytest.raises(DBAPIError, match="append-only"):
                    connection.execute(text(statement), {"id": row_id})
            finally:
                savepoint.rollback()


def test_u4b_linked_raw_reading_is_append_only_without_a_monthly_source_link(
    owner: Engine,
) -> None:
    """U4b-DB-12: the building evidence link alone freezes its MeterReading."""
    with _graph(owner) as (connection, ids):
        evidence_id = new_id()
        connection.execute(
            text(
                "INSERT INTO uvi_building_monthly_evidence"
                " (id, account_id, building_id, main_meter_id, month,"
                " measured_building_heat_kwh_x1000, building_hkv_movement_x1000, source_type,"
                " source_id,"
                " raw_evidence, supersedes_evidence_id) VALUES"
                " (:id, :account_a, :building, :main_meter, '2025-01-01', 100000, NULL,"
                " 'UVI_BUILDING_EVIDENCE', 'source',"
                ' \'{"reading_ids":["source"]}\'::jsonb, NULL)'
            ),
            {**ids, "id": evidence_id},
        )
        connection.execute(
            text(
                "INSERT INTO uvi_building_monthly_evidence_source"
                " (id, account_id, building_monthly_evidence_id, main_meter_id,"
                " meter_reading_id) VALUES"
                " (:id, :account_a, :evidence, :main_meter, :raw_reading)"
            ),
            {**ids, "id": new_id(), "evidence": evidence_id},
        )
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM monthly_meter_reading_source"
                    " WHERE meter_reading_id = :raw_reading"
                ),
                ids,
            )
            == 0
        )
        connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        for statement in (
            "UPDATE meter_reading SET value_x1000 = value_x1000 + 1 WHERE id = :raw_reading",
            "DELETE FROM meter_reading WHERE id = :raw_reading",
        ):
            savepoint = connection.begin_nested()
            try:
                with pytest.raises(DBAPIError, match="append-only"):
                    connection.execute(text(statement), ids)
            finally:
                savepoint.rollback()


def test_u4b_referenced_main_meter_keeps_its_evidence_identity_and_eligibility(
    owner: Engine,
) -> None:
    """U4b-DB-13: six identity/eligibility fields freeze while evidence refers to a meter."""
    with _graph(owner) as (connection, ids):
        evidence_id = new_id()
        connection.execute(
            text(
                "INSERT INTO uvi_building_monthly_evidence"
                " (id, account_id, building_id, main_meter_id, month,"
                " measured_building_heat_kwh_x1000, building_hkv_movement_x1000, source_type,"
                " source_id,"
                " raw_evidence, supersedes_evidence_id) VALUES"
                " (:id, :account_a, :building, :main_meter, '2025-01-01', 100000, NULL,"
                " 'UVI_BUILDING_EVIDENCE', 'source',"
                ' \'{"reading_ids":["source"]}\'::jsonb, NULL)'
            ),
            {**ids, "id": evidence_id},
        )
        connection.execute(
            text(
                "INSERT INTO uvi_building_monthly_evidence_source"
                " (id, account_id, building_monthly_evidence_id, main_meter_id,"
                " meter_reading_id) VALUES"
                " (:id, :account_a, :evidence, :main_meter, :raw_reading)"
            ),
            {**ids, "id": new_id(), "evidence": evidence_id},
        )
        connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        changes = (
            "unit_id = :unit",
            "kind = 'COLD_WATER'",
            "measurement_unit = 'CUBIC_METRE'",
            "account_id = :account_b",
            "building_id = :other_building",
            "id = :replacement_main_meter",
        )
        for assignment in changes:
            savepoint = connection.begin_nested()
            try:
                with pytest.raises(DBAPIError, match="append-only"):
                    connection.execute(
                        text(f"UPDATE meter SET {assignment} WHERE id = :main_meter"),
                        ids,
                    )
            finally:
                savepoint.rollback()


def test_u4b_rejects_blank_or_empty_source_metadata(owner: Engine) -> None:
    """U4b-DB-10: blank identity/stamps and empty provenance are not evidence."""
    with _graph(owner) as (connection, ids):
        degree_template = (
            "INSERT INTO uvi_monthly_degree_day"
            " (id, account_id, station_assignment_id, station_id, month,"
            " monthly_degree_days, valid_day_count, source_file, source_id, provenance,"
            " rechtsstand, verification_status, monthly_annual_share,"
            " supersedes_degree_day_id) VALUES"
            " (:id, :account_a, :assignment, '001', '2025-01-01', 590.25, 31,"
            " {source_file}, {source_id}, {provenance}, {rechtsstand}, {verification},"
            " NULL, NULL)"
        )
        configuration_template = (
            "INSERT INTO building_uvi_configuration"
            " (id, account_id, building_id, energy_source, energy_reference,"
            " explicit_hkv_allocator, calorific_factor, valid_from, valid_to, source_type,"
            " source_id,"
            " rechtsstand, verification_status, supersedes_configuration_id) VALUES"
            " (:id, :account_a, :building, 'Erdgas', 'HO', false, NULL, '2026-01-01',"
            " NULL, 'UVI_CONFIGURATION', {source_id}, {rechtsstand}, {verification}, NULL)"
        )
        cases = (
            degree_template.format(
                source_file="''",
                source_id="'DWD:001:202501'",
                provenance='\'{"source":"DWD"}\'::jsonb',
                rechtsstand="'08/2026'",
                verification="'verify-before-production'",
            ),
            degree_template.format(
                source_file="'monthly-source-202501'",
                source_id="''",
                provenance='\'{"source":"DWD"}\'::jsonb',
                rechtsstand="'08/2026'",
                verification="'verify-before-production'",
            ),
            degree_template.format(
                source_file="'monthly-source-202501'",
                source_id="'DWD:001:202501'",
                provenance="'{}'::jsonb",
                rechtsstand="'08/2026'",
                verification="'verify-before-production'",
            ),
            degree_template.format(
                source_file="'monthly-source-202501'",
                source_id="'DWD:001:202501'",
                provenance='\'{"source":"DWD"}\'::jsonb',
                rechtsstand="''",
                verification="'verify-before-production'",
            ),
            degree_template.format(
                source_file="'monthly-source-202501'",
                source_id="'DWD:001:202501'",
                provenance='\'{"source":"DWD"}\'::jsonb',
                rechtsstand="'08/2026'",
                verification="''",
            ),
            configuration_template.format(
                source_id="''",
                rechtsstand="'08/2026'",
                verification="'verify-before-production'",
            ),
            configuration_template.format(
                source_id="'source'",
                rechtsstand="''",
                verification="'verify-before-production'",
            ),
            configuration_template.format(
                source_id="'source'",
                rechtsstand="'08/2026'",
                verification="''",
            ),
            "INSERT INTO uvi_building_monthly_evidence"
            " (id, account_id, building_id, main_meter_id, month,"
            " measured_building_heat_kwh_x1000, building_hkv_movement_x1000, source_type,"
            " source_id,"
            " raw_evidence, supersedes_evidence_id) VALUES"
            " (:id, :account_a, :building, :main_meter, '2025-01-01', 100000, NULL,"
            " 'UVI_BUILDING_EVIDENCE', '',"
            ' \'{"reading_ids":["source"]}\'::jsonb, NULL)',
            "INSERT INTO uvi_building_monthly_evidence"
            " (id, account_id, building_id, main_meter_id, month,"
            " measured_building_heat_kwh_x1000, building_hkv_movement_x1000, source_type,"
            " source_id,"
            " raw_evidence, supersedes_evidence_id) VALUES"
            " (:id, :account_a, :building, :main_meter, '2025-01-01', 100000, NULL,"
            " 'UVI_BUILDING_EVIDENCE', 'source',"
            " '{}'::jsonb, NULL)",
        )
        for statement in cases:
            savepoint = connection.begin_nested()
            try:
                with pytest.raises(DBAPIError):
                    connection.execute(text(statement), {**ids, "id": new_id()})
            finally:
                savepoint.rollback()


def test_u4b_rejects_postgresql_numeric_nan(owner: Engine) -> None:
    """U4b-DB-11: PostgreSQL Numeric NaN cannot enter any UVI calculation input."""
    with _graph(owner) as (connection, ids):
        statements = (
            "INSERT INTO uvi_monthly_degree_day"
            " (id, account_id, station_assignment_id, station_id, month,"
            " monthly_degree_days, valid_day_count, source_file, source_id, provenance,"
            " rechtsstand, verification_status, monthly_annual_share,"
            " supersedes_degree_day_id) VALUES"
            " (:id, :account_a, :assignment, '001', '2025-01-01', 'NaN'::numeric, 31,"
            " 'monthly-source-202501', 'source', '{\"source\":\"DWD\"}'::jsonb,"
            " '08/2026', 'verify-before-production', NULL, NULL)",
            "INSERT INTO uvi_monthly_degree_day"
            " (id, account_id, station_assignment_id, station_id, month,"
            " monthly_degree_days, valid_day_count, source_file, source_id, provenance,"
            " rechtsstand, verification_status, monthly_annual_share,"
            " supersedes_degree_day_id) VALUES"
            " (:id, :account_a, :assignment, '001', '2025-01-01', 590.25, 31,"
            " 'monthly-source-202501', 'source', '{\"source\":\"DWD\"}'::jsonb,"
            " '08/2026', 'verify-before-production', 'NaN'::numeric, NULL)",
            "INSERT INTO building_uvi_configuration"
            " (id, account_id, building_id, energy_source, energy_reference,"
            " explicit_hkv_allocator, calorific_factor, valid_from, valid_to, source_type,"
            " source_id,"
            " rechtsstand, verification_status, supersedes_configuration_id) VALUES"
            " (:id, :account_a, :building, 'Erdgas', 'HO', false, 'NaN'::numeric,"
            " '2026-01-01', NULL, 'UVI_CONFIGURATION', 'source', '08/2026',"
            " 'verify-before-production', NULL)",
        )
        for statement in statements:
            savepoint = connection.begin_nested()
            try:
                with pytest.raises(DBAPIError):
                    connection.execute(text(statement), {**ids, "id": new_id()})
            finally:
                savepoint.rollback()


def test_u4b_cross_account_reads_are_nonvacuous_and_isolated(owner: Engine) -> None:
    """U4b-DB-12: A sees all three rows; B sees none under lokara_app RLS."""
    with _graph(owner) as (connection, ids):
        inserts = (
            "INSERT INTO uvi_monthly_degree_day"
            " (id, account_id, station_assignment_id, station_id, month,"
            " monthly_degree_days, valid_day_count, source_file, source_id, provenance,"
            " rechtsstand, verification_status, monthly_annual_share,"
            " supersedes_degree_day_id) VALUES"
            " (:degree, :account_a, :assignment, '001', '2025-01-01', 590.25, 31,"
            " 'monthly-source-202501', 'source', '{\"source\":\"DWD\"}'::jsonb,"
            " '08/2026', 'verify-before-production', NULL, NULL)",
            "INSERT INTO building_uvi_configuration"
            " (id, account_id, building_id, energy_source, energy_reference,"
            " explicit_hkv_allocator, calorific_factor, valid_from, valid_to, source_type,"
            " source_id,"
            " rechtsstand, verification_status, supersedes_configuration_id) VALUES"
            " (:configuration, :account_a, :building, 'Erdgas', 'HO', false, NULL,"
            " '2026-01-01', NULL, 'UVI_CONFIGURATION', 'source', '08/2026',"
            " 'verify-before-production', NULL)",
            "INSERT INTO uvi_building_monthly_evidence"
            " (id, account_id, building_id, main_meter_id, month,"
            " measured_building_heat_kwh_x1000, building_hkv_movement_x1000, source_type,"
            " source_id,"
            " raw_evidence, supersedes_evidence_id) VALUES"
            " (:evidence, :account_a, :building, :main_meter, '2025-01-01', 100000, NULL,"
            " 'UVI_BUILDING_EVIDENCE', 'source',"
            ' \'{"reading_ids":["source"]}\'::jsonb, NULL)',
            "INSERT INTO uvi_building_monthly_evidence_source"
            " (id, account_id, building_monthly_evidence_id, main_meter_id, meter_reading_id)"
            " VALUES (:evidence_source, :account_a, :evidence, :main_meter, :raw_reading)",
        )
        row_ids = {
            "degree": new_id(),
            "configuration": new_id(),
            "evidence": new_id(),
            "evidence_source": new_id(),
        }
        for statement in inserts:
            connection.execute(text(statement), {**ids, **row_ids})
        connection.execute(text("SET LOCAL ROLE lokara_app"))
        for account, expected in ((ids["account_a"], 1), (ids["account_b"], 0)):
            connection.execute(
                text("SELECT set_config('app.account_id', :account, true)"),
                {"account": account},
            )
            for table_name in (
                "uvi_monthly_degree_day",
                "building_uvi_configuration",
                "uvi_building_monthly_evidence",
                "uvi_building_monthly_evidence_source",
            ):
                assert connection.scalar(text(f"SELECT count(*) FROM {table_name}")) == expected
