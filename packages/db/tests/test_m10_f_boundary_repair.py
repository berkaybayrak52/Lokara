"""RED M10-F database boundary and schema-parity regression contract."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest
from alembic import command
from alembic.config import Config
from lokara_db import DbSettings, create_db_engine, new_id
from lokara_db.models import RenterPortalPublication
from sqlalchemy import Connection, Engine, Table, text
from sqlalchemy.exc import DBAPIError, OperationalError

_DB_DIR = Path(__file__).resolve().parent.parent
_MIGRATION = _DB_DIR / "alembic" / "versions" / "0047_m10_f_boundary_and_schema_parity.py"


@dataclass(frozen=True)
class _CoreIds:
    account: str
    owner_person: str
    owner_membership: str
    renter_person: str
    building: str
    unit: str
    tenancy: str
    renter: str


@pytest.fixture(scope="module")
def owner_engine() -> Iterator[Engine]:
    settings = DbSettings()
    try:
        engine = create_db_engine(settings.direct_url)
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
def _rollback_probe(engine: Engine) -> Iterator[Connection]:
    connection = engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        transaction.rollback()
        connection.close()


def _seed_core(connection: Connection) -> _CoreIds:
    ids = _CoreIds(*(new_id() for _ in range(8)))
    now = datetime(2026, 9, 17, 9, 0, tzinfo=UTC)
    connection.execute(
        text("INSERT INTO account (id, name, shape, plan) VALUES (:id, 'M10-F', 'SOLO', 'TRIAL')"),
        {"id": ids.account},
    )
    connection.execute(
        text(
            "INSERT INTO person (id, email) VALUES (:owner, :owner_email), (:renter, :renter_email)"
        ),
        {
            "owner": ids.owner_person,
            "owner_email": f"{ids.owner_person}@example.test",
            "renter": ids.renter_person,
            "renter_email": f"{ids.renter_person}@example.test",
        },
    )
    connection.execute(
        text(
            "INSERT INTO membership "
            "(id, person_id, account_id, role, accepted_at, revoked_at) "
            "VALUES (:id, :person, :account, 'OWNER', :accepted, NULL)"
        ),
        {
            "id": ids.owner_membership,
            "person": ids.owner_person,
            "account": ids.account,
            "accepted": now,
        },
    )
    connection.execute(
        text(
            "INSERT INTO building (id, account_id, name, street, postal_code, city) "
            "VALUES (:id, :account, 'M10-F Haus', 'Grenzweg 1', '10115', 'Berlin')"
        ),
        {"id": ids.building, "account": ids.account},
    )
    connection.execute(
        text("INSERT INTO renter (id, account_id, legal_name) VALUES (:id, :account, 'Mieter')"),
        {"id": ids.renter, "account": ids.account},
    )
    connection.execute(
        text(
            "INSERT INTO unit (id, account_id, building_id, label, area_sqm_x100) "
            "VALUES (:id, :account, :building, 'A', 5000)"
        ),
        {"id": ids.unit, "account": ids.account, "building": ids.building},
    )
    connection.execute(
        text(
            "INSERT INTO tenancy "
            "(id, account_id, unit_id, valid_from, valid_to, base_rent_cents) "
            "VALUES (:id, :account, :unit, DATE '2025-01-01', NULL, 80000)"
        ),
        {"id": ids.tenancy, "account": ids.account, "unit": ids.unit},
    )
    connection.execute(
        text(
            "INSERT INTO tenancy_party (id, account_id, tenancy_id, renter_id) "
            "VALUES (:id, :account, :tenancy, :renter)"
        ),
        {
            "id": new_id(),
            "account": ids.account,
            "tenancy": ids.tenancy,
            "renter": ids.renter,
        },
    )
    return ids


def _become_app(connection: Connection, account_id: str) -> None:
    connection.execute(text("SET LOCAL ROLE lokara_app"))
    connection.execute(
        text("SELECT set_config('app.account_id', :account, true)"), {"account": account_id}
    )
    connection.execute(text("SELECT set_config('app.tenancy_id', '', true)"))


def _seed_activation_code(
    connection: Connection,
    ids: _CoreIds,
    *,
    expires_at: datetime,
    issued_at: datetime,
) -> str:
    code_id = new_id()
    connection.execute(
        text(
            "INSERT INTO renter_activation_code "
            "(id, account_id, renter_id, tenancy_id, code_hash, expires_at, "
            "issued_by_membership_id, issued_at) VALUES "
            "(:id, :account, :renter, :tenancy, :digest, :expires, :membership, :issued)"
        ),
        {
            "id": code_id,
            "account": ids.account,
            "renter": ids.renter,
            "tenancy": ids.tenancy,
            "digest": sha256(code_id.encode()).hexdigest(),
            "expires": expires_at,
            "membership": ids.owner_membership,
            "issued": issued_at,
        },
    )
    return code_id


def _insert_activation_redemption(
    connection: Connection,
    ids: _CoreIds,
    code_id: str,
    *,
    redeemed_at: datetime,
) -> str:
    redemption_id = new_id()
    connection.execute(
        text(
            "INSERT INTO renter_activation_redemption "
            "(id, account_id, activation_code_id, renter_id, tenancy_id, person_id, "
            "redeemed_at) VALUES "
            "(:id, :account, :code, :renter, :tenancy, :person, :redeemed)"
        ),
        {
            "id": redemption_id,
            "account": ids.account,
            "code": code_id,
            "renter": ids.renter,
            "tenancy": ids.tenancy,
            "person": ids.renter_person,
            "redeemed": redeemed_at,
        },
    )
    return redemption_id


def _seed_statement_archive(
    connection: Connection,
    ids: _CoreIds,
    *,
    version: int = 1,
    predecessor_id: str | None = None,
    status: str = "FINALIZED",
) -> tuple[str, str, bytes, str]:
    statement_id, archive_id = new_id(), new_id()
    content = f"statement-{version}".encode()
    filename = f"statement-{version}.pdf"
    connection.execute(
        text(
            "INSERT INTO statement "
            "(id, account_id, building_id, period_start, period_end, version, status, "
            "total_cents, content_hash, finalized_snapshot, finalized_at, "
            "supersedes_statement_id) VALUES "
            "(:id, :account, :building, DATE '2025-01-01', DATE '2025-12-31', :version, "
            "CAST(:status AS statement_status), 10000, :digest, "
            "CAST(:snapshot AS json), :finalized, :predecessor)"
        ),
        {
            "id": statement_id,
            "account": ids.account,
            "building": ids.building,
            "version": version,
            "status": status,
            "digest": sha256(content).hexdigest(),
            "snapshot": json.dumps({"production_blockers": []}),
            "finalized": datetime(2026, 9, 17, 9, 0, tzinfo=UTC),
            "predecessor": predecessor_id,
        },
    )
    connection.execute(
        text(
            "INSERT INTO statement_document_archive "
            "(id, account_id, statement_id, audience, tenancy_id, document_type, "
            "content_bytes, sha256, mime_type, filename) VALUES "
            "(:id, :account, :statement, 'TENANT', :tenancy, 'TENANT_STATEMENT', "
            ":content, :digest, 'application/pdf', :filename)"
        ),
        {
            "id": archive_id,
            "account": ids.account,
            "statement": statement_id,
            "tenancy": ids.tenancy,
            "content": content,
            "digest": sha256(content).hexdigest(),
            "filename": filename,
        },
    )
    return statement_id, archive_id, content, filename


def _seed_uvi_artifact(connection: Connection, ids: _CoreIds) -> tuple[str, bytes, str]:
    run_id, artifact_id = new_id(), new_id()
    inputs = {"fixture": "M10-F"}
    results = {"document": {"fixture": "M10-F"}}
    digest = connection.scalar(
        text(
            "SELECT encode(digest(convert_to(jsonb_build_object("
            "'tenancy_id', CAST(:tenancy AS text), 'unit_id', CAST(:unit AS text), "
            "'month', to_jsonb(DATE '2026-08-01'), 'inputs', CAST(:inputs AS jsonb), "
            "'results', CAST(:results AS jsonb), 'heizspiegel_vintage', CAST(NULL AS text), "
            "'source_type', CAST('TEST' AS text), 'source_id', CAST('M10-F' AS text), "
            "'station_assignment_id', CAST(NULL AS text), 'station_id', CAST(NULL AS text), "
            "'station_distance_km', to_jsonb(CAST(NULL AS numeric)), "
            "'support_code', CAST(NULL AS text))::text, 'UTF8'), 'sha256'), 'hex')"
        ),
        {
            "tenancy": ids.tenancy,
            "unit": ids.unit,
            "inputs": json.dumps(inputs, separators=(",", ":")),
            "results": json.dumps(results, separators=(",", ":")),
        },
    )
    connection.execute(
        text(
            "INSERT INTO uvi_run "
            "(id, account_id, tenancy_id, unit_id, month, inputs, results, "
            "heizspiegel_vintage, source_type, source_id, station_assignment_id, station_id, "
            "station_distance_km, sha256, support_code) VALUES "
            "(:id, :account, :tenancy, :unit, DATE '2026-08-01', CAST(:inputs AS jsonb), "
            "CAST(:results AS jsonb), NULL, 'TEST', 'M10-F', NULL, NULL, NULL, :digest, NULL)"
        ),
        {
            "id": run_id,
            "account": ids.account,
            "tenancy": ids.tenancy,
            "unit": ids.unit,
            "inputs": json.dumps(inputs),
            "results": json.dumps(results),
            "digest": digest,
        },
    )
    content = b"uvi-m10-f"
    filename = "uvi-m10-f.pdf"
    connection.execute(
        text(
            "INSERT INTO renter_delivery_artifact "
            "(id, account_id, building_id, unit_id, tenancy_id, renter_id, artifact_kind, "
            "occurrence_key, statement_archive_id, uvi_run_id, content_bytes, sha256, "
            "mime_type, filename, production_blockers_snapshot, generated_at) VALUES "
            "(:id, :account, :building, :unit, :tenancy, :renter, 'UVI', :occurrence, NULL, "
            ":run, :content, :digest, 'application/pdf', :filename, '[]'::jsonb, :generated)"
        ),
        {
            "id": artifact_id,
            "account": ids.account,
            "building": ids.building,
            "unit": ids.unit,
            "tenancy": ids.tenancy,
            "renter": ids.renter,
            "occurrence": f"m10-f:{artifact_id}",
            "run": run_id,
            "content": content,
            "digest": sha256(content).hexdigest(),
            "filename": filename,
            "generated": datetime(2026, 9, 17, 9, 0, tzinfo=UTC),
        },
    )
    return artifact_id, content, filename


def _insert_publication(
    connection: Connection,
    ids: _CoreIds,
    *,
    source_kind: str,
    source_id: str,
    content: bytes,
    digest: str,
    mime_type: str,
    filename: str,
    supersedes_id: str | None = None,
) -> str:
    publication_id = new_id()
    is_uvi = source_kind == "UVI_ARTIFACT"
    connection.execute(
        text(
            "INSERT INTO renter_portal_publication "
            "(id, account_id, tenancy_id, source_kind, statement_archive_id, "
            "renter_delivery_artifact_id, document_type, content_bytes, sha256, mime_type, "
            "filename, published_by_membership_id, published_at, supersedes_publication_id, "
            "period_start, period_end, document_month) VALUES "
            "(:id, :account, :tenancy, :kind, :archive, :artifact, :document_type, :content, "
            ":digest, :mime, :filename, :membership, :published, :supersedes, "
            ":period_start, :period_end, :document_month)"
        ),
        {
            "id": publication_id,
            "account": ids.account,
            "tenancy": ids.tenancy,
            "kind": source_kind,
            "archive": None if is_uvi else source_id,
            "artifact": source_id if is_uvi else None,
            "document_type": "UVI" if is_uvi else "TENANT_STATEMENT",
            "content": content,
            "digest": digest,
            "mime": mime_type,
            "filename": filename,
            "membership": ids.owner_membership,
            "published": datetime(2026, 9, 17, 10, 0, tzinfo=UTC),
            "supersedes": supersedes_id,
            "period_start": None if is_uvi else date(2025, 1, 1),
            "period_end": None if is_uvi else date(2025, 12, 31),
            "document_month": date(2026, 8, 1) if is_uvi else None,
        },
    )
    return publication_id


def test_m10_f_0047_migration_is_conditional_and_repairs_all_boundaries() -> None:
    assert _MIGRATION.exists(), "M10-F compatibility migration 0047 is missing"
    normalized = " ".join(_MIGRATION.read_text().lower().split())
    hardened_upgrade = normalized.split("def downgrade", maxsplit=1)[0]
    assert 'revision = "0047"' in normalized
    assert 'down_revision = "0046"' in normalized
    assert "statement_timestamp()" in hardened_upgrade
    assert "transaction_timestamp()" not in hardened_upgrade

    for marker in ("account", "support_code", "information_schema.columns", "drop column"):
        assert marker in normalized
    assert "if exists" in normalized and "if not exists" in normalized

    for marker in (
        "ck_building_type",
        "wohn_und_geschaeftshaus",
        "wohnhaus",
        "gewerbeimmobilie",
        "einfamilienhaus",
        "ck_building_latitude_range",
        "latitude between -90 and 90",
        "ck_building_longitude_range",
        "longitude between -180 and 180",
    ):
        assert marker in normalized
    assert (
        "alter table public.building drop constraint if exists ck_building_type_allowed"
        in normalized
    )

    for marker in (
        "renter_activation_redemption",
        "expires_at",
        "renter_portal_publication",
        "statement_document_archive",
        "renter_delivery_artifact",
        "content_bytes",
        "sha256",
        "mime_type",
        "filename",
        "investment_entitlement_event",
        "recorded_by_membership_id",
        "accepted_at is not null",
        "revoked_at is null",
        "uq_renter_portal_publication_successor",
        "supersedes_publication_id",
    ):
        assert marker in normalized


def test_m10_f_publication_successor_index_is_declared_in_model_metadata() -> None:
    index = next(
        (
            candidate
            for candidate in cast(Table, RenterPortalPublication.__table__).indexes
            if candidate.name == "uq_renter_portal_publication_successor"
        ),
        None,
    )

    assert index is not None
    assert index.unique is True
    assert [column.name for column in index.columns] == [
        "account_id",
        "tenancy_id",
        "document_type",
        "supersedes_publication_id",
    ]
    assert str(index.dialect_options["postgresql"]["where"]) == (
        "supersedes_publication_id IS NOT NULL"
    )


def test_m10_f_expired_activation_cannot_be_redeemed_into_a_person_link(
    owner_engine: Engine,
) -> None:
    with _rollback_probe(owner_engine) as connection:
        ids = _seed_core(connection)
        code_id = new_id()
        connection.execute(
            text(
                "INSERT INTO renter_activation_code "
                "(id, account_id, renter_id, tenancy_id, code_hash, expires_at, "
                "issued_by_membership_id, issued_at) VALUES "
                "(:id, :account, :renter, :tenancy, :digest, :expires, :membership, :issued)"
            ),
            {
                "id": code_id,
                "account": ids.account,
                "renter": ids.renter,
                "tenancy": ids.tenancy,
                "digest": sha256(code_id.encode()).hexdigest(),
                "expires": datetime(2026, 9, 16, 8, 0, tzinfo=UTC),
                "membership": ids.owner_membership,
                "issued": datetime(2026, 9, 15, 8, 0, tzinfo=UTC),
            },
        )
        _become_app(connection, ids.account)
        with pytest.raises(DBAPIError):
            connection.execute(
                text(
                    "INSERT INTO renter_activation_redemption "
                    "(id, account_id, activation_code_id, renter_id, tenancy_id, person_id, "
                    "redeemed_at) VALUES "
                    "(:id, :account, :code, :renter, :tenancy, :person, :redeemed)"
                ),
                {
                    "id": new_id(),
                    "account": ids.account,
                    "code": code_id,
                    "renter": ids.renter,
                    "tenancy": ids.tenancy,
                    "person": ids.renter_person,
                    "redeemed": datetime(2026, 9, 17, 8, 0, tzinfo=UTC),
                },
            )
            connection.execute(
                text("UPDATE renter SET person_id = :person WHERE id = :renter"),
                {"person": ids.renter_person, "renter": ids.renter},
            )


def test_m10_f_backdated_redemption_cannot_bypass_database_expiry(
    owner_engine: Engine,
) -> None:
    with _rollback_probe(owner_engine) as connection:
        ids = _seed_core(connection)
        database_now = connection.scalar(text("SELECT transaction_timestamp()"))
        assert isinstance(database_now, datetime)
        code_id = _seed_activation_code(
            connection,
            ids,
            expires_at=database_now - timedelta(hours=1),
            issued_at=database_now - timedelta(hours=2),
        )
        _become_app(connection, ids.account)
        with pytest.raises(DBAPIError):
            _insert_activation_redemption(
                connection,
                ids,
                code_id,
                redeemed_at=database_now - timedelta(hours=2),
            )


def test_m10_f_activation_expiring_at_database_time_is_rejected(
    owner_engine: Engine,
) -> None:
    with _rollback_probe(owner_engine) as connection:
        ids = _seed_core(connection)
        database_now = connection.scalar(text("SELECT transaction_timestamp()"))
        assert isinstance(database_now, datetime)
        code_id = _seed_activation_code(
            connection,
            ids,
            expires_at=database_now,
            issued_at=database_now - timedelta(hours=1),
        )
        _become_app(connection, ids.account)
        with pytest.raises(DBAPIError):
            _insert_activation_redemption(
                connection,
                ids,
                code_id,
                redeemed_at=database_now - timedelta(seconds=1),
            )


def test_m10_f_accepted_redemption_timestamp_is_per_statement_server_time(
    owner_engine: Engine,
) -> None:
    with _rollback_probe(owner_engine) as connection:
        ids = _seed_core(connection)
        database_now = connection.scalar(text("SELECT transaction_timestamp()"))
        assert isinstance(database_now, datetime)
        code_id = _seed_activation_code(
            connection,
            ids,
            expires_at=database_now + timedelta(hours=1),
            issued_at=database_now - timedelta(hours=1),
        )
        _become_app(connection, ids.account)
        statement_before = connection.scalar(text("SELECT statement_timestamp()"))
        redemption_id = _insert_activation_redemption(
            connection,
            ids,
            code_id,
            redeemed_at=datetime(2000, 1, 1, tzinfo=UTC),
        )
        stored_at = connection.scalar(
            text("SELECT redeemed_at FROM renter_activation_redemption WHERE id = :id"),
            {"id": redemption_id},
        )
        statement_after = connection.scalar(text("SELECT statement_timestamp()"))
        assert isinstance(statement_before, datetime)
        assert isinstance(stored_at, datetime)
        assert isinstance(statement_after, datetime)
        assert statement_before <= stored_at <= statement_after


def test_m10_f_transaction_opened_before_expiry_cannot_redeem_after_expiry(
    owner_engine: Engine,
) -> None:
    with _rollback_probe(owner_engine) as connection:
        ids = _seed_core(connection)
        database_now = connection.scalar(text("SELECT statement_timestamp()"))
        assert isinstance(database_now, datetime)
        expires_at = database_now + timedelta(milliseconds=500)
        code_id = _seed_activation_code(
            connection,
            ids,
            expires_at=expires_at,
            issued_at=database_now - timedelta(hours=1),
        )
        _become_app(connection, ids.account)
        before_delay = connection.scalar(text("SELECT statement_timestamp()"))
        assert isinstance(before_delay, datetime)
        assert before_delay < expires_at
        connection.execute(text("SELECT pg_sleep(0.65)"))
        after_delay = connection.scalar(text("SELECT statement_timestamp()"))
        assert isinstance(after_delay, datetime)
        assert after_delay > expires_at
        with pytest.raises(DBAPIError):
            _insert_activation_redemption(
                connection,
                ids,
                code_id,
                redeemed_at=database_now,
            )


@pytest.mark.parametrize("source_kind", ("STATEMENT_ARCHIVE", "UVI_ARTIFACT"))
@pytest.mark.parametrize(
    "mismatch",
    ("bytes", "sha256", "mime", "filename"),
    ids=("bytes", "sha256", "mime", "filename"),
)
def test_m10_f_publication_payload_must_equal_its_eligible_source(
    owner_engine: Engine, source_kind: str, mismatch: str
) -> None:
    with _rollback_probe(owner_engine) as connection:
        ids = _seed_core(connection)
        if source_kind == "STATEMENT_ARCHIVE":
            _, source_id, source_content, source_filename = _seed_statement_archive(connection, ids)
        else:
            source_id, source_content, source_filename = _seed_uvi_artifact(connection, ids)
        _become_app(connection, ids.account)

        content = b"different bytes" if mismatch == "bytes" else source_content
        digest = "f" * 64 if mismatch == "sha256" else sha256(source_content).hexdigest()
        mime_type = "application/octet-stream" if mismatch == "mime" else "application/pdf"
        filename = "different.pdf" if mismatch == "filename" else source_filename
        with pytest.raises(DBAPIError):
            _insert_publication(
                connection,
                ids,
                source_kind=source_kind,
                source_id=source_id,
                content=content,
                digest=digest,
                mime_type=mime_type,
                filename=filename,
            )


@pytest.mark.parametrize(
    ("role", "accepted", "revoked"),
    (
        ("EMPLOYEE", True, False),
        ("TAX_ADVISOR", True, False),
        ("OWNER", False, False),
        ("OWNER", True, True),
    ),
    ids=("employee", "tax-advisor", "unaccepted-owner", "revoked-owner"),
)
def test_m10_f_entitlement_actor_must_be_an_active_accepted_owner(
    owner_engine: Engine, role: str, accepted: bool, revoked: bool
) -> None:
    with _rollback_probe(owner_engine) as connection:
        ids = _seed_core(connection)
        person_id, membership_id = new_id(), new_id()
        now = datetime(2026, 9, 17, 9, 0, tzinfo=UTC)
        connection.execute(
            text("INSERT INTO person (id, email) VALUES (:id, :email)"),
            {"id": person_id, "email": f"{person_id}@example.test"},
        )
        connection.execute(
            text(
                "INSERT INTO membership "
                "(id, person_id, account_id, role, accepted_at, revoked_at) VALUES "
                "(:id, :person, :account, CAST(:role AS role), :accepted, :revoked)"
            ),
            {
                "id": membership_id,
                "person": person_id,
                "account": ids.account,
                "role": role,
                "accepted": now if accepted else None,
                "revoked": now if revoked else None,
            },
        )
        _become_app(connection, ids.account)
        with pytest.raises(DBAPIError):
            connection.execute(
                text(
                    "INSERT INTO investment_entitlement_event "
                    "(id, account_id, entitlement_key, version, enabled, "
                    "supersedes_entitlement_event_id, recorded_by_membership_id) VALUES "
                    "(:id, :account, 'INVESTMENT', 1, true, NULL, :membership)"
                ),
                {"id": new_id(), "account": ids.account, "membership": membership_id},
            )


def test_m10_f_entitlement_recorded_at_is_per_statement_server_time(
    owner_engine: Engine,
) -> None:
    with _rollback_probe(owner_engine) as connection:
        ids = _seed_core(connection)
        _become_app(connection, ids.account)
        statement_before = connection.scalar(text("SELECT statement_timestamp()"))
        event_id = new_id()
        connection.execute(
            text(
                "INSERT INTO investment_entitlement_event "
                "(id, account_id, entitlement_key, version, enabled, "
                "supersedes_entitlement_event_id, recorded_by_membership_id, recorded_at) "
                "VALUES (:id, :account, 'INVESTMENT', 1, true, NULL, :membership, :forged)"
            ),
            {
                "id": event_id,
                "account": ids.account,
                "membership": ids.owner_membership,
                "forged": datetime(2000, 1, 1, tzinfo=UTC),
            },
        )
        stored_at = connection.scalar(
            text("SELECT recorded_at FROM investment_entitlement_event WHERE id = :id"),
            {"id": event_id},
        )
        statement_after = connection.scalar(text("SELECT statement_timestamp()"))

        assert isinstance(statement_before, datetime)
        assert isinstance(stored_at, datetime)
        assert isinstance(statement_after, datetime)
        assert statement_before <= stored_at <= statement_after


def test_m10_f_publication_predecessor_has_only_one_direct_successor(
    owner_engine: Engine,
) -> None:
    with _rollback_probe(owner_engine) as connection:
        ids = _seed_core(connection)
        statement_1, archive_1, content_1, filename_1 = _seed_statement_archive(connection, ids)
        statement_2, archive_2, content_2, filename_2 = _seed_statement_archive(
            connection,
            ids,
            version=2,
            predecessor_id=statement_1,
            status="SUPERSEDED",
        )
        _, archive_3, content_3, filename_3 = _seed_statement_archive(
            connection,
            ids,
            version=3,
            predecessor_id=statement_2,
        )
        _become_app(connection, ids.account)
        predecessor = _insert_publication(
            connection,
            ids,
            source_kind="STATEMENT_ARCHIVE",
            source_id=archive_1,
            content=content_1,
            digest=sha256(content_1).hexdigest(),
            mime_type="application/pdf",
            filename=filename_1,
        )
        _insert_publication(
            connection,
            ids,
            source_kind="STATEMENT_ARCHIVE",
            source_id=archive_2,
            content=content_2,
            digest=sha256(content_2).hexdigest(),
            mime_type="application/pdf",
            filename=filename_2,
            supersedes_id=predecessor,
        )
        with pytest.raises(DBAPIError):
            _insert_publication(
                connection,
                ids,
                source_kind="STATEMENT_ARCHIVE",
                source_id=archive_3,
                content=content_3,
                digest=sha256(content_3).hexdigest(),
                mime_type="application/pdf",
                filename=filename_3,
                supersedes_id=predecessor,
            )
