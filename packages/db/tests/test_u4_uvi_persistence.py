"""Red U4 persistence contract from docs/16 §§ 3, 7.2, 9, 10 and 12.

The fixtures pin durable evidence only.  U5 owns generation, renter documents,
publication routes and email behaviour; none of those belong in migration 0022.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple

import pytest
from alembic import command
from alembic.config import Config
from lokara_db import Base, DbSettings, create_db_engine, new_id
from sqlalchemy import (
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
from sqlalchemy.sql.elements import TextClause
from sqlalchemy.sql.schema import Table

_DB_DIR = Path(__file__).resolve().parent.parent
REQUIRED_TABLES = {
    "monthly_meter_reading",
    "monthly_meter_reading_source",
    "uvi_station_assignment",
    "dwd_climate_factor",
    "uvi_run",
    "uvi_delivery_event",
}


def _table(name: str) -> Table:
    return Base.metadata.tables[name]


def _scoped_fk(table: Table, column: str, parent: str) -> bool:
    return any(
        isinstance(constraint, ForeignKeyConstraint)
        and tuple(element.parent.name for element in constraint.elements) == (column, "account_id")
        and tuple(element.column.table.name for element in constraint.elements) == (parent, parent)
        and tuple(element.column.name for element in constraint.elements) == ("id", "account_id")
        for constraint in table.constraints
    )


def _unique_column_sets(table: Table) -> set[frozenset[str]]:
    return {
        frozenset(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def _check_text(table: Table) -> str:
    return " ".join(
        constraint.sqltext.text
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    )


def test_u4_f01_migration_0022_is_a_new_revision() -> None:
    """U4-F01: U4 adds 0022 after 0021; it never amends merged history."""
    revisions = list((_DB_DIR / "alembic" / "versions").glob("0022_*.py"))
    assert len(revisions) == 1
    source = revisions[0].read_text()
    assert 'revision = "0022"' in source
    assert 'down_revision = "0021"' in source


def test_u4_f02_all_six_account_scoped_records_exist() -> None:
    """U4-F02: durable tables exist for each U4 persistence concern."""
    assert set(Base.metadata.tables) >= REQUIRED_TABLES
    for name in REQUIRED_TABLES:
        table = _table(name)
        assert "account_id" in table.columns
        assert table.columns["account_id"].nullable is False


def test_u4_f03_normalized_monthly_readings_retain_correction_evidence() -> None:
    """U4-F03: normalized months are fixed-point, sourced and superseded by INSERT."""
    monthly = _table("monthly_meter_reading")
    assert {
        "id",
        "account_id",
        "meter_id",
        "tenancy_id",
        "unit_id",
        "month",
        "consumption_x1000",
        "reason",
        "source",
        "interpolation_method",
        "supersedes_reading_id",
        "created_at",
    } <= set(monthly.columns.keys())
    assert monthly.columns["consumption_x1000"].type.python_type is int
    assert _scoped_fk(monthly, "meter_id", "meter")
    assert _scoped_fk(monthly, "tenancy_id", "tenancy")
    assert _scoped_fk(monthly, "unit_id", "unit")
    assert _scoped_fk(monthly, "supersedes_reading_id", "monthly_meter_reading")
    assert {"updated_at", "deleted_at", "is_current", "superseded_at"}.isdisjoint(monthly.columns)


def test_u4_f03b_monthly_sources_are_normalized_account_safe_links() -> None:
    """U4-F03b: raw source identities are durable links, never unchecked JSON ids."""
    monthly = _table("monthly_meter_reading")
    assert "source_reading_ids" not in monthly.columns
    source = _table("monthly_meter_reading_source")
    assert {
        "id",
        "account_id",
        "monthly_meter_reading_id",
        "meter_reading_id",
        "created_at",
    } <= set(source.columns.keys())
    assert _scoped_fk(source, "monthly_meter_reading_id", "monthly_meter_reading")
    assert _scoped_fk(source, "meter_reading_id", "meter_reading")
    assert any(
        {"monthly_meter_reading_id", "meter_reading_id"} <= columns
        for columns in _unique_column_sets(source)
    )


def test_u4_f03c_raw_meter_reading_exposes_scoped_parent_pair() -> None:
    """The source link's composite FK needs meter_reading(id, account_id) to be unique."""
    assert frozenset({"id", "account_id"}) in _unique_column_sets(_table("meter_reading"))


def test_u4_f04_station_assignment_is_exact_and_never_recomputed() -> None:
    """U4-F04: one immutable PLZ/month assignment retains station and distance."""
    assignment = _table("uvi_station_assignment")
    assert {
        "id",
        "account_id",
        "postal_code",
        "month",
        "station_id",
        "distance_km",
        "source_type",
        "source_id",
        "created_at",
    } <= set(assignment.columns.keys())
    assert isinstance(assignment.columns["distance_km"].type, Numeric)
    assert assignment.columns["distance_km"].type.python_type is Decimal
    assert frozenset({"account_id", "postal_code", "month"}) in _unique_column_sets(assignment)
    checks = _check_text(assignment)
    assert "postal_code" in checks and "distance_km" in checks
    assert {"updated_at", "deleted_at", "recomputed_at"}.isdisjoint(assignment.columns)


def test_u4_f05_climate_factor_retries_are_idempotent_and_keep_old_periods() -> None:
    """U4-F05: the annual source identity is PLZ plus exact rolling period."""
    factor = _table("dwd_climate_factor")
    assert {
        "id",
        "account_id",
        "postal_code",
        "period_from",
        "period_to",
        "factor",
        "source_type",
        "source_id",
        "published_at",
        "created_at",
    } <= set(factor.columns.keys())
    assert isinstance(factor.columns["factor"].type, Numeric)
    assert factor.columns["factor"].type.python_type is Decimal
    assert frozenset({"account_id", "postal_code", "period_from", "period_to"}) in (
        _unique_column_sets(factor)
    )
    checks = _check_text(factor)
    assert "factor" in checks and "0.40" in checks and "1.80" in checks
    assert "period_from" in checks and "period_to" in checks
    assert {"updated_at", "deleted_at", "is_latest"}.isdisjoint(factor.columns)


def test_u4_f06_run_archives_inputs_results_identity_and_resolved_sources() -> None:
    """U4-F06: a UVI is reproducible from its immutable archive, never live rows."""
    run = _table("uvi_run")
    assert {
        "id",
        "account_id",
        "tenancy_id",
        "unit_id",
        "month",
        "inputs",
        "results",
        "heizspiegel_vintage",
        "source_type",
        "source_id",
        "station_assignment_id",
        "station_id",
        "station_distance_km",
        "sha256",
        "created_at",
    } <= set(run.columns.keys())
    assert _scoped_fk(run, "tenancy_id", "tenancy")
    assert _scoped_fk(run, "unit_id", "unit")
    assert _scoped_fk(run, "station_assignment_id", "uvi_station_assignment")
    assert isinstance(run.columns["station_distance_km"].type, Numeric)
    assert run.columns["inputs"].nullable is False
    assert run.columns["results"].nullable is False
    checks = _check_text(run)
    assert "sha256" in checks
    assert {"updated_at", "deleted_at", "status"}.isdisjoint(run.columns)


def test_u4_f07_delivery_retries_append_new_evidence_rows() -> None:
    """U4-F07: GENERATED/PUBLISHED/EMAILED/FAILED are events, never run state."""
    event = _table("uvi_delivery_event")
    assert {
        "id",
        "account_id",
        "uvi_run_id",
        "status",
        "occurred_at",
        "created_at",
    } <= set(event.columns.keys())
    assert _scoped_fk(event, "uvi_run_id", "uvi_run")
    checks = _check_text(event)
    for status in ("GENERATED", "PUBLISHED", "EMAILED", "FAILED"):
        assert status in checks
    assert not any("status" in columns for columns in _unique_column_sets(event))
    assert {"updated_at", "deleted_at", "retry_count"}.isdisjoint(event.columns)


@pytest.fixture(scope="module")
def upgraded_owner() -> Iterator[Engine]:
    """Migration-level checks skip locally without Postgres and are mandatory in CI."""
    if not list((_DB_DIR / "alembic" / "versions").glob("0022_*.py")):
        pytest.skip("migration 0022 is the missing U4 implementation")
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


def test_u4_live_database_reached_current_head_after_0022(upgraded_owner: Engine) -> None:
    """U4 runs on a schema at least as new as 0022; the repository head is 0024."""
    with upgraded_owner.connect() as connection:
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    assert revision == "0024"
    assert int(revision) >= 22


def test_u4_f08_all_six_records_are_database_append_only(upgraded_owner: Engine) -> None:
    """U4-F08: UPDATE and DELETE are refused by a trigger on every evidence table."""
    inspector = inspect(upgraded_owner)
    assert set(inspector.get_table_names()) >= REQUIRED_TABLES
    with upgraded_owner.connect() as connection:
        for table_name in REQUIRED_TABLES:
            trigger_defs = connection.scalars(
                text(
                    "SELECT pg_get_triggerdef(t.oid) FROM pg_trigger t"
                    " WHERE t.tgrelid = to_regclass(:table_name) AND NOT t.tgisinternal"
                ),
                {"table_name": f"public.{table_name}"},
            ).all()
            normalized = " ".join(trigger_defs).upper()
            assert "UPDATE" in normalized, table_name
            assert "DELETE" in normalized, table_name


def test_u4_f09_tenancy_and_unit_on_a_run_must_name_the_same_lease(
    upgraded_owner: Engine,
) -> None:
    """U4-F09: migration 0022 installs a same-unit tenancy guard, not only account FKs."""
    with upgraded_owner.connect() as connection:
        definitions = connection.scalars(
            text(
                "SELECT pg_get_triggerdef(t.oid) || ' ' || pg_get_functiondef(t.tgfoid)"
                " FROM pg_trigger t WHERE t.tgrelid = 'public.uvi_run'::regclass"
                " AND NOT t.tgisinternal"
            )
        ).all()
    normalized = " ".join(definitions).lower()
    assert "tenancy" in normalized and "unit_id" in normalized


class U4Graph(NamedTuple):
    account: str
    building: str
    other_building: str
    unit: str
    peer_unit: str
    other_building_unit: str
    tenancy: str
    split_tenancy: str
    expired_tenancy: str
    peer_tenancy: str
    meter: str
    replacement_meter: str
    peer_meter: str
    other_building_meter: str
    assignment: str
    august_assignment: str
    other_postal_assignment: str
    raw_reading: str
    replacement_raw_reading: str
    foreign_account: str
    foreign_building: str
    foreign_unit: str
    foreign_meter: str
    foreign_raw_reading: str


@contextmanager
def u4_graph(engine: Engine) -> Iterator[tuple[Connection, U4Graph]]:
    """One same-account U4 graph; every row is rolled back after each probe."""
    ids = U4Graph(*(new_id() for _ in range(24)))
    connection = engine.connect()
    transaction = connection.begin()
    try:
        params = ids._asdict()
        connection.execute(
            text(
                "INSERT INTO account (id, name, shape, plan)"
                " VALUES (:account, 'U4 audit', 'SOLO', 'TRIAL'),"
                " (:foreign_account, 'U4 foreign', 'SOLO', 'TRIAL')"
            ),
            params,
        )
        connection.execute(
            text(
                "INSERT INTO building (id, account_id, name, street, postal_code, city) VALUES"
                " (:building, :account, 'Haus', 'Weg 1', '10115', 'Berlin'),"
                " (:other_building, :account, 'Haus 2', 'Weg 2', '20095', 'Hamburg'),"
                " (:foreign_building, :foreign_account, 'Fremd', 'Weg 3', '50667', 'Köln')"
            ),
            params,
        )
        connection.execute(
            text(
                "INSERT INTO unit (id, account_id, building_id, label, area_sqm_x100) VALUES"
                " (:unit, :account, :building, 'WE 1', 5000),"
                " (:peer_unit, :account, :building, 'WE 2', 6000),"
                " (:other_building_unit, :account, :other_building, 'WE 3', 7000),"
                " (:foreign_unit, :foreign_account, :foreign_building, 'WE F', 4000)"
            ),
            params,
        )
        connection.execute(
            text(
                "INSERT INTO tenancy"
                " (id, account_id, unit_id, valid_from, valid_to, base_rent_cents) VALUES"
                " (:tenancy, :account, :unit, '2026-01-15', '2026-12-15', 80000),"
                " (:split_tenancy, :account, :unit, '2026-07-15', NULL, 81000),"
                " (:expired_tenancy, :account, :unit, '2025-01-01', '2026-01-01', 79000),"
                " (:peer_tenancy, :account, :peer_unit, '2026-01-01', NULL, 82000)"
            ),
            params,
        )
        connection.execute(
            text(
                "INSERT INTO meter"
                " (id, account_id, building_id, unit_id, kind, measurement_unit, serial,"
                " calibration_valid_until, valuation_factor_x1000) VALUES"
                " (:meter, :account, :building, :unit, 'HEAT', 'KWH', 'U4-A',"
                " '2029-12-31', 1000),"
                " (:replacement_meter, :account, :building, :unit, 'HEAT', 'KWH', 'U4-B',"
                " '2029-12-31', 1000),"
                " (:peer_meter, :account, :building, :peer_unit, 'HEAT', 'KWH', 'U4-C',"
                " '2029-12-31', 1000),"
                " (:other_building_meter, :account, :other_building, :other_building_unit,"
                " 'HEAT', 'KWH', 'U4-D', '2029-12-31', 1000),"
                " (:foreign_meter, :foreign_account, :foreign_building, :foreign_unit,"
                " 'HEAT', 'KWH', 'U4-F', '2029-12-31', 1000)"
            ),
            params,
        )
        connection.execute(
            text(
                "INSERT INTO meter_reading"
                " (id, account_id, meter_id, read_at, value_x1000, reason, source) VALUES"
                " (:raw_reading, :account, :meter, '2026-07-01', 100000, 'PERIODIC', 'MANUAL'),"
                " (:replacement_raw_reading, :account, :replacement_meter, '2026-07-01',"
                " 200000, 'DEVICE_CHANGE', 'MANUAL'),"
                " (:foreign_raw_reading, :foreign_account, :foreign_meter, '2026-07-01',"
                " 300000, 'PERIODIC', 'MANUAL')"
            ),
            params,
        )
        connection.execute(
            text(
                "INSERT INTO uvi_station_assignment"
                " (id, account_id, postal_code, month, station_id, distance_km,"
                " source_type, source_id) VALUES"
                " (:assignment, :account, '10115', '2026-07-01', '00433', 12.345,"
                " 'DWD_MONTHLY', '2026-07:00433'),"
                " (:august_assignment, :account, '10115', '2026-08-01', '00433', 12.345,"
                " 'DWD_MONTHLY', '2026-08:00433'),"
                " (:other_postal_assignment, :account, '20095', '2026-07-01', '01975', 7.500,"
                " 'DWD_MONTHLY', '2026-07:01975')"
            ),
            params,
        )
        yield connection, ids
    finally:
        transaction.rollback()
        connection.close()


def _monthly_values(ids: U4Graph, **changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "id": new_id(),
        "account": ids.account,
        "meter": ids.meter,
        "tenancy": ids.tenancy,
        "unit": ids.unit,
        "month": date(2026, 7, 1),
        "consumption": 1000,
        "reason": "PERIODIC",
        "source": "MANUAL",
        "interpolation_method": "LINEAR_ELAPSED_DAYS",
        "supersedes": None,
    }
    values.update(changes)
    return values


_MONTHLY_INSERT = text(
    "INSERT INTO monthly_meter_reading"
    " (id, account_id, meter_id, tenancy_id, unit_id, month, consumption_x1000,"
    " reason, source, interpolation_method, supersedes_reading_id)"
    " VALUES (:id, :account, :meter, :tenancy, :unit, :month, :consumption, :reason,"
    " :source, :interpolation_method, :supersedes)"
)

_MONTHLY_SOURCE_INSERT = text(
    "INSERT INTO monthly_meter_reading_source"
    " (id, account_id, monthly_meter_reading_id, meter_reading_id)"
    " VALUES (:id, :account, :monthly, :raw)"
)


def _source_values(ids: U4Graph, monthly_id: object, **changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "id": new_id(),
        "account": ids.account,
        "monthly": monthly_id,
        "raw": ids.raw_reading,
    }
    values.update(changes)
    return values


def _expect_rejected(
    connection: Connection, statement: TextClause, params: Mapping[str, object]
) -> None:
    savepoint = connection.begin_nested()
    try:
        with pytest.raises(DBAPIError) as refused:
            connection.execute(statement, params)
    finally:
        savepoint.rollback()
    _assert_intended_guard(refused.value)


def _assert_intended_guard(refused: DBAPIError) -> None:
    assert getattr(refused.orig, "sqlstate", None) != "42P01", "missing table is not a guard"
    message = str(refused).lower()
    assert not (
        "source_reading_ids" in message and ("not-null" in message or "not null" in message)
    ), "the retired JSON column must not mask the intended invariant"


def _expect_deferred_source_rejected(
    connection: Connection, monthly_values: Mapping[str, object]
) -> None:
    savepoint = connection.begin_nested()
    try:
        with pytest.raises(DBAPIError) as refused:
            connection.execute(_MONTHLY_INSERT, monthly_values)
            connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    finally:
        savepoint.rollback()
    _assert_intended_guard(refused.value)


@pytest.mark.parametrize(
    "meter_field",
    ("peer_meter", "other_building_meter"),
    ids=("wrong_unit", "wrong_building"),
)
def test_u4_audit_f01_monthly_reading_rejects_wrong_unit_and_building_links(
    upgraded_owner: Engine, meter_field: str
) -> None:
    """A normalized renter month cannot cite another unit's or building's meter."""
    with u4_graph(upgraded_owner) as (connection, ids):
        _expect_rejected(
            connection, _MONTHLY_INSERT, _monthly_values(ids, meter=getattr(ids, meter_field))
        )


def test_u4_audit_f02_monthly_reading_requires_tenancy_overlap(
    upgraded_owner: Engine,
) -> None:
    """A tenancy wholly outside the represented calendar month is invalid."""
    with u4_graph(upgraded_owner) as (connection, ids):
        _expect_rejected(
            connection,
            _MONTHLY_INSERT,
            _monthly_values(ids, tenancy=ids.expired_tenancy),
        )


def test_u4_audit_f02b_monthly_reading_permits_tenant_and_device_splits(
    upgraded_owner: Engine,
) -> None:
    """A partial-month tenancy and a replacement meter in the same unit remain representable."""
    with u4_graph(upgraded_owner) as (connection, ids):
        tenant_change = _monthly_values(ids, tenancy=ids.split_tenancy, reason="TENANT_CHANGE")
        device_change = _monthly_values(
            ids,
            meter=ids.replacement_meter,
            reason="DEVICE_CHANGE",
        )
        connection.execute(_MONTHLY_INSERT, tenant_change)
        connection.execute(_MONTHLY_INSERT, device_change)
        connection.execute(
            _MONTHLY_SOURCE_INSERT,
            _source_values(ids, tenant_change["id"]),
        )
        connection.execute(
            _MONTHLY_SOURCE_INSERT,
            _source_values(
                ids,
                device_change["id"],
                raw=ids.replacement_raw_reading,
            ),
        )
        connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_u4_audit_f03a_correction_rejects_self_supersession(
    upgraded_owner: Engine,
) -> None:
    """A correction cannot cite itself as its predecessor."""
    with u4_graph(upgraded_owner) as (connection, ids):
        self_id = new_id()
        _expect_rejected(
            connection,
            _MONTHLY_INSERT,
            _monthly_values(ids, id=self_id, reason="CORRECTION", supersedes=self_id),
        )


@pytest.mark.parametrize(
    "case",
    ("meter", "tenancy", "unit", "month"),
    ids=("meter", "tenancy", "unit", "month"),
)
def test_u4_audit_f03b_correction_predecessor_context_must_match(
    upgraded_owner: Engine,
    case: str,
) -> None:
    """A correction preserves its predecessor's meter, tenancy, unit and month."""
    with u4_graph(upgraded_owner) as (connection, ids):
        predecessor = _monthly_values(ids)
        connection.execute(_MONTHLY_INSERT, predecessor)
        changes_by_case: dict[str, dict[str, object]] = {
            "meter": {"meter": ids.replacement_meter},
            "tenancy": {"tenancy": ids.split_tenancy},
            "unit": {
                "meter": ids.peer_meter,
                "tenancy": ids.peer_tenancy,
                "unit": ids.peer_unit,
            },
            "month": {"month": date(2026, 8, 1)},
        }
        _expect_rejected(
            connection,
            _MONTHLY_INSERT,
            _monthly_values(
                ids,
                reason="CORRECTION",
                supersedes=predecessor["id"],
                **changes_by_case[case],
            ),
        )


def test_u4_audit_f03c_correction_rejects_second_direct_successor(
    upgraded_owner: Engine,
) -> None:
    """A predecessor has at most one direct correction successor."""
    with u4_graph(upgraded_owner) as (connection, ids):
        predecessor = _monthly_values(ids)
        connection.execute(_MONTHLY_INSERT, predecessor)
        first_successor = _monthly_values(
            ids,
            reason="CORRECTION",
            supersedes=predecessor["id"],
        )
        connection.execute(_MONTHLY_INSERT, first_successor)
        _expect_rejected(
            connection,
            _MONTHLY_INSERT,
            _monthly_values(ids, reason="CORRECTION", supersedes=predecessor["id"]),
        )


@pytest.mark.parametrize(
    ("reason", "uses_predecessor"),
    (("PERIODIC", True), ("CORRECTION", False)),
    ids=("non_correction_with_predecessor", "correction_without_predecessor"),
)
def test_u4_audit_f03d_correction_reason_matches_predecessor_presence(
    upgraded_owner: Engine, reason: str, uses_predecessor: bool
) -> None:
    """CORRECTION is required exactly when supersedes_reading_id is present."""
    with u4_graph(upgraded_owner) as (connection, ids):
        predecessor = _monthly_values(ids)
        connection.execute(_MONTHLY_INSERT, predecessor)
        _expect_rejected(
            connection,
            _MONTHLY_INSERT,
            _monthly_values(
                ids,
                reason=reason,
                supersedes=predecessor["id"] if uses_predecessor else None,
            ),
        )


def test_u4_audit_f04_correction_fk_is_immediate_and_successor_is_unique() -> None:
    """Immediate predecessor FK plus one-successor uniqueness makes longer cycles impossible."""
    monthly = _table("monthly_meter_reading")
    predecessor_fk = next(
        constraint
        for constraint in monthly.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        and {column.name for column in constraint.columns}
        == {"supersedes_reading_id", "account_id"}
    )
    assert predecessor_fk.deferrable is not True
    assert any(
        "supersedes_reading_id" in columns and columns <= {"account_id", "supersedes_reading_id"}
        for columns in _unique_column_sets(monthly)
    )


def test_u4_audit_f05_monthly_reason_and_source_use_existing_database_enums(
    upgraded_owner: Engine,
) -> None:
    """ORM and migration retain the existing reading_reason/reading_source types."""
    mapped = _table("monthly_meter_reading")
    live = {
        column["name"]: column
        for column in inspect(upgraded_owner).get_columns("monthly_meter_reading")
    }
    assert getattr(mapped.columns["reason"].type, "name", None) == "reading_reason"
    assert getattr(mapped.columns["source"].type, "name", None) == "reading_source"
    assert getattr(live["reason"]["type"], "name", None) == "reading_reason"
    assert getattr(live["source"]["type"], "name", None) == "reading_source"
    with u4_graph(upgraded_owner) as (connection, ids):
        _expect_rejected(connection, _MONTHLY_INSERT, _monthly_values(ids, reason="NOT_A_REASON"))
        _expect_rejected(connection, _MONTHLY_INSERT, _monthly_values(ids, source="NOT_A_SOURCE"))


def test_u4_audit_f10_source_table_has_rls_with_check_and_deferred_parent_guard(
    upgraded_owner: Engine,
) -> None:
    """The sixth table is isolated and its parent completeness guard is initially deferred."""
    with upgraded_owner.connect() as connection:
        row = connection.execute(
            text(
                "SELECT c.relrowsecurity, c.relforcerowsecurity,"
                " EXISTS (SELECT 1 FROM pg_policy p"
                " WHERE p.polrelid = c.oid AND p.polwithcheck IS NOT NULL) AS with_check"
                " FROM pg_class c WHERE c.oid = 'public.monthly_meter_reading_source'::regclass"
            )
        ).one()
        deferred = connection.scalar(
            text(
                "SELECT bool_or(t.tgdeferrable AND t.tginitdeferred) FROM pg_trigger t"
                " WHERE t.tgrelid = 'public.monthly_meter_reading'::regclass"
                " AND NOT t.tgisinternal"
            )
        )
    assert row.relrowsecurity and row.relforcerowsecurity and row.with_check
    assert deferred is True


def test_u4_audit_f11_monthly_requires_source_by_transaction_end(
    upgraded_owner: Engine,
) -> None:
    """A parent may be inserted first but cannot end its transaction with zero source links."""
    with u4_graph(upgraded_owner) as (connection, ids):
        _expect_deferred_source_rejected(connection, _monthly_values(ids))


def test_u4_audit_f11b_complete_parent_and_source_are_allowed(upgraded_owner: Engine) -> None:
    """The normal parent-then-link write order satisfies the deferred invariant."""
    with u4_graph(upgraded_owner) as (connection, ids):
        monthly = _monthly_values(ids)
        connection.execute(_MONTHLY_INSERT, monthly)
        connection.execute(
            _MONTHLY_SOURCE_INSERT,
            _source_values(ids, monthly["id"]),
        )
        connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        count = connection.scalar(
            text(
                "SELECT count(*) FROM monthly_meter_reading_source"
                " WHERE monthly_meter_reading_id = :monthly"
            ),
            {"monthly": monthly["id"]},
        )
        assert count == 1


@pytest.mark.parametrize(
    "raw_case",
    ("nonexistent", "foreign_account", "other_meter"),
)
def test_u4_audit_f12_source_link_rejects_invalid_raw_reading(
    upgraded_owner: Engine, raw_case: str
) -> None:
    """A source must exist in-account and belong to the normalized parent's meter."""
    with u4_graph(upgraded_owner) as (connection, ids):
        monthly = _monthly_values(ids)
        connection.execute(_MONTHLY_INSERT, monthly)
        raw_by_case = {
            "nonexistent": new_id(),
            "foreign_account": ids.foreign_raw_reading,
            "other_meter": ids.replacement_raw_reading,
        }
        _expect_rejected(
            connection,
            _MONTHLY_SOURCE_INSERT,
            _source_values(ids, monthly["id"], raw=raw_by_case[raw_case]),
        )


def test_u4_audit_f13_source_link_rejects_duplicate(upgraded_owner: Engine) -> None:
    """One raw reading cannot be cited twice by the same normalized month."""
    with u4_graph(upgraded_owner) as (connection, ids):
        monthly = _monthly_values(ids)
        connection.execute(_MONTHLY_INSERT, monthly)
        connection.execute(
            _MONTHLY_SOURCE_INSERT,
            _source_values(ids, monthly["id"]),
        )
        _expect_rejected(
            connection,
            _MONTHLY_SOURCE_INSERT,
            _source_values(ids, monthly["id"]),
        )


def test_u4_audit_f14_raw_meter_reading_has_named_append_only_trigger(
    upgraded_owner: Engine,
) -> None:
    """Linked raw evidence has a named BEFORE UPDATE OR DELETE database guard."""
    with upgraded_owner.connect() as connection:
        triggers = connection.execute(
            text(
                "SELECT t.tgname, pg_get_triggerdef(t.oid) AS definition"
                " FROM pg_trigger t"
                " WHERE t.tgrelid = 'public.meter_reading'::regclass"
                " AND NOT t.tgisinternal"
            )
        ).all()
    assert any(
        row.tgname == "meter_reading_append_only"
        and "BEFORE" in row.definition
        and "UPDATE" in row.definition
        and "DELETE" in row.definition
        for row in triggers
    )


@pytest.mark.parametrize(
    "statement",
    (
        "UPDATE meter_reading SET value_x1000 = value_x1000 + 1 WHERE id = :raw",
        "DELETE FROM meter_reading WHERE id = :raw",
    ),
    ids=("update", "delete"),
)
def test_u4_audit_f15_linked_raw_meter_reading_cannot_be_rewritten(
    upgraded_owner: Engine, statement: str
) -> None:
    """Both mutations are refused by the append-only trigger, not only by the source FK."""
    with u4_graph(upgraded_owner) as (connection, ids):
        monthly = _monthly_values(ids)
        connection.execute(_MONTHLY_INSERT, monthly)
        connection.execute(
            _MONTHLY_SOURCE_INSERT,
            _source_values(ids, monthly["id"]),
        )
        connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

        savepoint = connection.begin_nested()
        try:
            with pytest.raises(DBAPIError) as refused:
                connection.execute(text(statement), {"raw": ids.raw_reading})
        finally:
            savepoint.rollback()
        assert "append-only" in str(refused.value).lower()


def _uvi_values(ids: U4Graph, **changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "id": new_id(),
        "account": ids.account,
        "tenancy": ids.tenancy,
        "unit": ids.unit,
        "month": date(2026, 7, 1),
        "inputs": json.dumps({"current_kwh": "100"}),
        "results": json.dumps({"block_a_kwh": "100"}),
        "heizspiegel_vintage": "2025",
        "source_type": "METER_SERIES",
        "source_id": "meter-series:2026-07",
        "assignment": ids.assignment,
        "station_id": "00433",
        "distance": Decimal("12.345"),
        "sha256": "0" * 64,
    }
    values.update(changes)
    return values


_UVI_INSERT = text(
    "INSERT INTO uvi_run"
    " (id, account_id, tenancy_id, unit_id, month, inputs, results, heizspiegel_vintage,"
    " source_type, source_id, station_assignment_id, station_id, station_distance_km, sha256)"
    " VALUES (:id, :account, :tenancy, :unit, :month, CAST(:inputs AS jsonb),"
    " CAST(:results AS jsonb), :heizspiegel_vintage, :source_type, :source_id,"
    " :assignment, :station_id, :distance, :sha256)"
)


def _canonical_uvi_hash(connection: Connection, values: Mapping[str, object]) -> str:
    """SHA-256 of PostgreSQL's canonical jsonb text for every immutable evidence field."""
    result = connection.scalar(
        text(
            "SELECT encode(digest(convert_to(jsonb_build_object("
            " 'tenancy_id', CAST(:tenancy AS text), 'unit_id', CAST(:unit AS text),"
            " 'month', CAST(:month AS date),"
            " 'inputs', CAST(:inputs AS jsonb), 'results', CAST(:results AS jsonb),"
            " 'heizspiegel_vintage', CAST(:heizspiegel_vintage AS text),"
            " 'source_type', CAST(:source_type AS text),"
            " 'source_id', CAST(:source_id AS text),"
            " 'station_assignment_id', CAST(:assignment AS text),"
            " 'station_id', CAST(:station_id AS text),"
            " 'station_distance_km', CAST(:distance AS numeric(9,3))"
            ")::text, 'UTF8'), 'sha256'), 'hex')"
        ),
        values,
    )
    assert isinstance(result, str)
    return result


def test_u5_block_d_raw_weather_run_allows_null_optional_source_snapshots(
    upgraded_owner: Engine,
) -> None:
    """U5-DB-PREREQ: Block D/raw Block C needs neither D2 vintage nor station snapshot."""
    with u4_graph(upgraded_owner) as (connection, ids):
        values = _uvi_values(
            ids,
            inputs=json.dumps({"target_unit_id": ids.unit, "weather_mode": "raw"}),
            results=json.dumps({"block_c": "raw", "block_d": "ready"}),
            heizspiegel_vintage=None,
            assignment=None,
            station_id=None,
            distance=None,
        )
        values["sha256"] = _canonical_uvi_hash(connection, values)
        connection.execute(_UVI_INSERT, values)
        archived = connection.execute(
            text(
                "SELECT tenancy_id, unit_id, heizspiegel_vintage, station_assignment_id,"
                " station_id, station_distance_km, sha256 FROM uvi_run WHERE id = :id"
            ),
            {"id": values["id"]},
        ).one()
        assert archived.tenancy_id == ids.tenancy
        assert archived.unit_id == ids.unit
        assert archived.heizspiegel_vintage is None
        assert (
            archived.station_assignment_id,
            archived.station_id,
            archived.station_distance_km,
        ) == (None, None, None)
        assert archived.sha256 == values["sha256"]


@pytest.mark.parametrize(
    ("assignment", "station_id", "distance"),
    (
        (None, "00433", Decimal("12.345")),
        (None, None, Decimal("12.345")),
        (None, "00433", None),
        ("assigned", None, None),
        ("assigned", "00433", None),
        ("assigned", None, Decimal("12.345")),
    ),
)
def test_u5_run_rejects_partial_station_snapshot(
    upgraded_owner: Engine,
    assignment: str | None,
    station_id: str | None,
    distance: Decimal | None,
) -> None:
    """The optional station evidence is one atomic identity, never a partial snapshot."""
    with u4_graph(upgraded_owner) as (connection, ids):
        values = _uvi_values(
            ids,
            heizspiegel_vintage=None,
            assignment=ids.assignment if assignment is not None else None,
            station_id=station_id,
            distance=distance,
        )
        values["sha256"] = _canonical_uvi_hash(connection, values)
        _expect_rejected(connection, _UVI_INSERT, values)


@pytest.mark.parametrize(
    "case",
    ("assignment_month", "assignment_postal", "station_id", "station_distance"),
)
def test_u4_audit_f06_run_binds_assignment_month_postal_and_station_snapshot(
    upgraded_owner: Engine, case: str
) -> None:
    """The archived station snapshot must exactly match the assigned unit month and PLZ."""
    with u4_graph(upgraded_owner) as (connection, ids):
        changes_by_case: dict[str, dict[str, object]] = {
            "assignment_month": {"assignment": ids.august_assignment},
            "assignment_postal": {
                "assignment": ids.other_postal_assignment,
                "station_id": "01975",
                "distance": Decimal("7.500"),
            },
            "station_id": {"station_id": "WRONG"},
            "station_distance": {"distance": Decimal("12.346")},
        }
        values = _uvi_values(ids, **changes_by_case[case])
        values["sha256"] = _canonical_uvi_hash(connection, values)
        _expect_rejected(connection, _UVI_INSERT, values)


def test_u4_audit_f07_run_requires_tenancy_overlap(upgraded_owner: Engine) -> None:
    """The named lease must overlap the represented calendar month."""
    with u4_graph(upgraded_owner) as (connection, ids):
        values = _uvi_values(ids, tenancy=ids.expired_tenancy)
        values["sha256"] = _canonical_uvi_hash(connection, values)
        _expect_rejected(connection, _UVI_INSERT, values)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("inputs", json.dumps({})),
        ("inputs", json.dumps([])),
        ("results", json.dumps({})),
        ("results", json.dumps([])),
        ("heizspiegel_vintage", "  "),
        ("source_type", ""),
        ("source_id", "\t"),
    ),
    ids=(
        "inputs_empty_object",
        "inputs_array",
        "results_empty_object",
        "results_array",
        "blank_vintage",
        "blank_source_type",
        "blank_source_id",
    ),
)
def test_u4_audit_f08_run_rejects_empty_objects_and_blank_identity(
    upgraded_owner: Engine, field: str, value: object
) -> None:
    """Inputs/results are non-empty objects and every source identity component is nonblank."""
    with u4_graph(upgraded_owner) as (connection, ids):
        values = _uvi_values(ids, **{field: value})
        values["sha256"] = _canonical_uvi_hash(connection, values)
        _expect_rejected(connection, _UVI_INSERT, values)


def test_u4_audit_f09_sha256_binds_canonical_complete_uvi_payload(upgraded_owner: Engine) -> None:
    """Like 0016's bytes hash, the run hash must equal its canonical stored evidence bytes.

    Canonical U4 bytes are UTF-8 PostgreSQL jsonb text of ``to_jsonb(NEW)`` minus exactly
    id, account_id, created_at and sha256. This combines 0016's digest binding with
    0020's established whole-row ``to_jsonb`` subtraction pattern.
    """
    with u4_graph(upgraded_owner) as (connection, ids):
        baseline = _uvi_values(ids)
        baseline["sha256"] = _canonical_uvi_hash(connection, baseline)
        connection.execute(_UVI_INSERT, baseline)
        tampered = _uvi_values(ids, sha256="f" * 64)
        _expect_rejected(connection, _UVI_INSERT, tampered)

        definitions = connection.scalars(
            text(
                "SELECT pg_get_functiondef(t.tgfoid) FROM pg_trigger t"
                " WHERE t.tgrelid = 'public.uvi_run'::regclass AND NOT t.tgisinternal"
            )
        ).all()
        normalized = " ".join(" ".join(definitions).lower().split())
        assert "digest(" in normalized and "sha256" in normalized
        assert "to_jsonb(new)" in normalized
        for excluded in ("id", "account_id", "created_at", "sha256"):
            assert excluded in normalized
