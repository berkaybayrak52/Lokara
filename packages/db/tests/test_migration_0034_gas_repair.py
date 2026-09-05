"""PostgreSQL acceptance proof for the bounded legacy gas-factor repair."""

from __future__ import annotations

import os
import re
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from lokara_db import DbSettings, new_id
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import NullPool

_DB_DIR = Path(__file__).resolve().parent.parent
_SAFE_DATABASE_NAME = re.compile(r"[a-z0-9_]+")


def _database_url(owner_url: URL, database: str) -> URL:
    return owner_url.set(database=database)


def _skip_if_postgres_is_unavailable(exc: OperationalError) -> None:
    if os.environ.get("LOKARA_REQUIRE_DB"):
        raise exc
    pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")


def test_0034_clears_the_synthetic_condition_number_from_matching_legacy_gas_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GAS-MIGRATION-01: source metadata cannot reinterpret one legacy combined factor."""
    owner_url = make_url(DbSettings().direct_sqlalchemy_url)
    database_name = f"lokara_migration_0034_{uuid4().hex}"
    assert _SAFE_DATABASE_NAME.fullmatch(database_name)

    maintenance = create_engine(
        _database_url(owner_url, "postgres"),
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )
    test_engine: Engine | None = None
    database_created = False
    try:
        try:
            with maintenance.connect() as connection:
                connection.exec_driver_sql(f'CREATE DATABASE "{database_name}"')
            database_created = True
        except OperationalError as exc:
            _skip_if_postgres_is_unavailable(exc)

        test_url = _database_url(owner_url, database_name)
        monkeypatch.setenv("DIRECT_URL", test_url.render_as_string(hide_password=False))
        alembic = Config(str(_DB_DIR / "alembic.ini"))
        command.upgrade(alembic, "0032")

        test_engine = create_engine(test_url, poolclass=NullPool)
        account_id = new_id()
        building_id = new_id()
        configuration_id = new_id()
        legacy_factor = Decimal("10.123456")
        source_id = f"legacy-gas-invoice-{configuration_id}"
        with test_engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO account (id, name, shape, plan) "
                    "VALUES (:account, '0034 gas repair', 'SOLO', 'TRIAL')"
                ),
                {"account": account_id},
            )
            connection.execute(
                text(
                    "INSERT INTO building "
                    "(id, account_id, name, street, postal_code, city) "
                    "VALUES (:building, :account, '0034 Haus', 'Testweg 34', '10115', 'Berlin')"
                ),
                {"account": account_id, "building": building_id},
            )
            connection.execute(
                text(
                    "INSERT INTO building_uvi_configuration "
                    "(id, account_id, building_id, energy_source, energy_reference, "
                    "explicit_hkv_allocator, calorific_factor, valid_from, valid_to, source_type, "
                    "source_id, rechtsstand, verification_status, supersedes_configuration_id) "
                    "VALUES (:configuration, :account, :building, 'Erdgas', 'HO', false, "
                    ":factor, '2026-08-01', NULL, 'SUPPLIER_INVOICE', :source_id, '08/2026', "
                    "'verify-before-production', NULL)"
                ),
                {
                    "account": account_id,
                    "building": building_id,
                    "configuration": configuration_id,
                    "factor": legacy_factor,
                    "source_id": source_id,
                },
            )

        command.upgrade(alembic, "0034")

        with test_engine.connect() as connection:
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
            repaired = connection.execute(
                text(
                    "SELECT calorific_factor, condition_number, energy_source, energy_reference, "
                    "source_type, source_id, rechtsstand, verification_status "
                    "FROM building_uvi_configuration WHERE id = :configuration"
                ),
                {"configuration": configuration_id},
            ).one()

        assert revision == "0034"
        assert repaired.calorific_factor == legacy_factor
        assert repaired.condition_number is None
        assert repaired.energy_source == "Erdgas"
        assert repaired.energy_reference == "HO"
        assert repaired.source_type == "SUPPLIER_INVOICE"
        assert repaired.source_id == source_id
        assert repaired.rechtsstand == "08/2026"
        assert repaired.verification_status == "verify-before-production"
    finally:
        if test_engine is not None:
            test_engine.dispose()
        if database_created:
            with maintenance.connect() as connection:
                connection.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname = :database AND pid <> pg_backend_pid()"
                    ),
                    {"database": database_name},
                )
                connection.exec_driver_sql(f'DROP DATABASE "{database_name}"')
        maintenance.dispose()
