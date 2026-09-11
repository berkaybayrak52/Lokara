"""M10-R3 RED database contract for immutable renter portal publication."""

import ast
import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

import lokara_db
import pytest
from alembic import command
from alembic.config import Config
from lokara_db import (
    Account,
    Building,
    DbSettings,
    Membership,
    Person,
    Renter,
    RenterDeliveryArtifact,
    Role,
    Statement,
    StatementArchive,
    StatementStatus,
    Tenancy,
    TenancyParty,
    Unit,
    UviRun,
    create_db_engine,
    new_id,
)
from sqlalchemy import CheckConstraint, Connection, Engine, ForeignKeyConstraint, Table, text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session

_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent
_MIGRATIONS = _DB_PACKAGE_DIR / "alembic" / "versions"


class _UseSourceDate:
    pass


_USE_SOURCE_DATE = _UseSourceDate()


@dataclass(frozen=True)
class _Ids:
    account_a: str
    account_b: str
    owner_a: str
    owner_b: str
    membership_a: str
    membership_b: str
    building_a: str
    building_b: str
    unit_a: str
    unit_a_other: str
    unit_b: str
    tenancy_a: str
    tenancy_a_other: str
    tenancy_b: str
    renter_a: str
    renter_a_other: str
    renter_b: str
    statement_a: str
    statement_a_correction: str
    statement_a_other: str
    statement_b: str
    archive_a: str
    archive_a_correction: str
    archive_a_cover: str
    archive_a_other: str
    archive_b: str
    uvi_run_a: str
    uvi_artifact_a: str
    uvi_artifact_a_blocked: str


def _canonical_uvi_hash(session: Session, payload: dict[str, object]) -> str:
    value = session.scalar(
        text(
            """SELECT encode(digest(convert_to(jsonb_build_object(
              'tenancy_id', CAST(:tenancy_id AS text), 'unit_id', CAST(:unit_id AS text),
              'month', to_jsonb(CAST(:month AS date)),
              'inputs', CAST(:inputs AS jsonb), 'results', CAST(:results AS jsonb),
              'heizspiegel_vintage', CAST(:heizspiegel_vintage AS text),
              'source_type', CAST(:source_type AS text), 'source_id', CAST(:source_id AS text),
              'station_assignment_id', CAST(:station_assignment_id AS text),
              'station_id', CAST(:station_id AS text),
              'station_distance_km', to_jsonb(CAST(:station_distance_km AS numeric)),
              'support_code', CAST(:support_code AS text)
            )::text, 'UTF8'), 'sha256'), 'hex')"""
        ),
        {
            **payload,
            "inputs": json.dumps(payload["inputs"], separators=(",", ":")),
            "results": json.dumps(payload["results"], separators=(",", ":")),
        },
    )
    assert isinstance(value, str)
    return value


@pytest.fixture(scope="module")
def setup() -> Iterator[tuple[Engine, Engine, _Ids]]:
    settings = DbSettings()
    try:
        owner = create_db_engine(settings.direct_url)
        with owner.connect() as connection:
            connection.execute(
                text((_DB_PACKAGE_DIR / "scripts" / "init-app-role.sql").read_text())
            )
            connection.commit()
    except OperationalError as exc:
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")
    command.upgrade(Config(str(_DB_PACKAGE_DIR / "alembic.ini")), "head")
    app = create_db_engine(settings.database_url)
    ids = _Ids(*(new_id() for _ in range(29)))
    now = datetime(2026, 9, 11, 12, 0, tzinfo=UTC)
    with Session(owner) as session, session.begin():
        session.add_all(
            [
                Account(id=ids.account_a, name="M10-R3 A"),
                Account(id=ids.account_b, name="M10-R3 B"),
                Person(id=ids.owner_a, email=f"{ids.owner_a}@example.test"),
                Person(id=ids.owner_b, email=f"{ids.owner_b}@example.test"),
                Membership(
                    id=ids.membership_a,
                    person_id=ids.owner_a,
                    account_id=ids.account_a,
                    role=Role.OWNER,
                    accepted_at=now,
                ),
                Membership(
                    id=ids.membership_b,
                    person_id=ids.owner_b,
                    account_id=ids.account_b,
                    role=Role.OWNER,
                    accepted_at=now,
                ),
                Building(
                    id=ids.building_a,
                    account_id=ids.account_a,
                    name="Haus A",
                    street="A-Weg 1",
                    postal_code="10115",
                    city="Berlin",
                ),
                Building(
                    id=ids.building_b,
                    account_id=ids.account_b,
                    name="Haus B",
                    street="B-Weg 1",
                    postal_code="20095",
                    city="Hamburg",
                ),
                Renter(id=ids.renter_a, account_id=ids.account_a, legal_name="Mieter A"),
                Renter(
                    id=ids.renter_a_other,
                    account_id=ids.account_a,
                    legal_name="Mieter A2",
                ),
                Renter(id=ids.renter_b, account_id=ids.account_b, legal_name="Mieter B"),
            ]
        )
    with Session(owner) as session, session.begin():
        session.add_all(
            [
                Unit(
                    id=ids.unit_a,
                    account_id=ids.account_a,
                    building_id=ids.building_a,
                    label="A1",
                    area_sqm_x100=5_000,
                ),
                Unit(
                    id=ids.unit_a_other,
                    account_id=ids.account_a,
                    building_id=ids.building_a,
                    label="A2",
                    area_sqm_x100=4_000,
                ),
                Unit(
                    id=ids.unit_b,
                    account_id=ids.account_b,
                    building_id=ids.building_b,
                    label="B1",
                    area_sqm_x100=6_000,
                ),
            ]
        )
    with Session(owner) as session, session.begin():
        session.add_all(
            [
                Tenancy(
                    id=ids.tenancy_a,
                    account_id=ids.account_a,
                    unit_id=ids.unit_a,
                    valid_from=date(2025, 1, 1),
                    valid_to=None,
                    base_rent_cents=80_000,
                ),
                Tenancy(
                    id=ids.tenancy_a_other,
                    account_id=ids.account_a,
                    unit_id=ids.unit_a_other,
                    valid_from=date(2025, 1, 1),
                    valid_to=None,
                    base_rent_cents=70_000,
                ),
                Tenancy(
                    id=ids.tenancy_b,
                    account_id=ids.account_b,
                    unit_id=ids.unit_b,
                    valid_from=date(2025, 1, 1),
                    valid_to=None,
                    base_rent_cents=90_000,
                ),
            ]
        )
    with Session(owner) as session, session.begin():
        session.add_all(
            [
                TenancyParty(
                    account_id=ids.account_a, tenancy_id=ids.tenancy_a, renter_id=ids.renter_a
                ),
                TenancyParty(
                    account_id=ids.account_a,
                    tenancy_id=ids.tenancy_a_other,
                    renter_id=ids.renter_a_other,
                ),
                TenancyParty(
                    account_id=ids.account_b, tenancy_id=ids.tenancy_b, renter_id=ids.renter_b
                ),
                Statement(
                    id=ids.statement_a,
                    account_id=ids.account_a,
                    building_id=ids.building_a,
                    period_start=date(2025, 1, 1),
                    period_end=date(2025, 12, 31),
                    version=1,
                    status=StatementStatus.FINALIZED,
                    total_cents=10_000,
                    content_hash=sha256(b"statement-a").hexdigest(),
                    finalized_snapshot={"production_blockers": []},
                    finalized_at=now,
                    supersedes_statement_id=None,
                ),
                Statement(
                    id=ids.statement_a_other,
                    account_id=ids.account_a,
                    building_id=ids.building_a,
                    period_start=date(2024, 1, 1),
                    period_end=date(2024, 12, 31),
                    version=1,
                    status=StatementStatus.FINALIZED,
                    total_cents=9_000,
                    content_hash=sha256(b"statement-a-other").hexdigest(),
                    finalized_snapshot={"production_blockers": []},
                    finalized_at=now,
                    supersedes_statement_id=None,
                ),
                Statement(
                    id=ids.statement_a_correction,
                    account_id=ids.account_a,
                    building_id=ids.building_a,
                    period_start=date(2025, 1, 1),
                    period_end=date(2025, 12, 31),
                    version=2,
                    status=StatementStatus.FINALIZED,
                    total_cents=10_100,
                    content_hash=sha256(b"statement-a-correction").hexdigest(),
                    finalized_snapshot={"production_blockers": []},
                    finalized_at=now,
                    supersedes_statement_id=ids.statement_a,
                ),
                Statement(
                    id=ids.statement_b,
                    account_id=ids.account_b,
                    building_id=ids.building_b,
                    period_start=date(2025, 1, 1),
                    period_end=date(2025, 12, 31),
                    version=1,
                    status=StatementStatus.FINALIZED,
                    total_cents=11_000,
                    content_hash=sha256(b"statement-b").hexdigest(),
                    finalized_snapshot={"production_blockers": []},
                    finalized_at=now,
                    supersedes_statement_id=None,
                ),
            ]
        )
    with Session(owner) as session, session.begin():
        archive_rows = (
            (
                ids.archive_a,
                ids.account_a,
                ids.statement_a,
                "TENANT",
                ids.tenancy_a,
                "TENANT_STATEMENT",
                b"tenant-a",
                "tenant-a.pdf",
            ),
            (
                ids.archive_a_correction,
                ids.account_a,
                ids.statement_a_correction,
                "TENANT",
                ids.tenancy_a,
                "TENANT_STATEMENT",
                b"tenant-a-correction",
                "tenant-a-correction.pdf",
            ),
            (
                ids.archive_a_cover,
                ids.account_a,
                ids.statement_a,
                "TENANT",
                ids.tenancy_a,
                "COVER_LETTER",
                b"cover-a",
                "cover-a.pdf",
            ),
            (
                ids.archive_a_other,
                ids.account_a,
                ids.statement_a_other,
                "TENANT",
                ids.tenancy_a_other,
                "TENANT_STATEMENT",
                b"tenant-a2",
                "tenant-a2.pdf",
            ),
            (
                ids.archive_b,
                ids.account_b,
                ids.statement_b,
                "TENANT",
                ids.tenancy_b,
                "TENANT_STATEMENT",
                b"tenant-b",
                "tenant-b.pdf",
            ),
        )
        for (
            archive_id,
            account_id,
            statement_id,
            audience,
            tenancy_id,
            kind,
            content,
            filename,
        ) in archive_rows:
            session.add(
                StatementArchive(
                    id=archive_id,
                    account_id=account_id,
                    statement_id=statement_id,
                    audience=audience,
                    tenancy_id=tenancy_id,
                    document_type=kind,
                    content_bytes=content,
                    sha256=sha256(content).hexdigest(),
                    mime_type="application/pdf",
                    filename=filename,
                )
            )
    with Session(owner) as session, session.begin():
        uvi_payload: dict[str, object] = {
            "tenancy_id": ids.tenancy_a,
            "unit_id": ids.unit_a,
            "month": date(2026, 8, 1),
            "inputs": {"fixture": "M10-R3"},
            "results": {"document": {"fixture": "M10-R3"}},
            "heizspiegel_vintage": None,
            "source_type": "TEST",
            "source_id": "M10-R3",
            "station_assignment_id": None,
            "station_id": None,
            "station_distance_km": None,
            "support_code": None,
        }
        session.add(
            UviRun(
                id=ids.uvi_run_a,
                account_id=ids.account_a,
                sha256=_canonical_uvi_hash(session, uvi_payload),
                **uvi_payload,
            )
        )
        session.flush()
        for artifact_id, blockers, content in (
            (ids.uvi_artifact_a, [], b"uvi-a"),
            (ids.uvi_artifact_a_blocked, ["verify-before-production"], b"uvi-blocked"),
        ):
            session.add(
                RenterDeliveryArtifact(
                    id=artifact_id,
                    account_id=ids.account_a,
                    building_id=ids.building_a,
                    unit_id=ids.unit_a,
                    tenancy_id=ids.tenancy_a,
                    renter_id=ids.renter_a,
                    artifact_kind="UVI",
                    occurrence_key=f"m10-r3:{artifact_id}",
                    statement_archive_id=None,
                    uvi_run_id=ids.uvi_run_a,
                    content_bytes=content,
                    sha256=sha256(content).hexdigest(),
                    mime_type="application/pdf",
                    filename=f"{artifact_id}.pdf",
                    production_blockers_snapshot=blockers,
                    generated_at=now,
                )
            )
    try:
        yield owner, app, ids
    finally:
        app.dispose()
        owner.dispose()


def _require_table(connection: Connection) -> None:
    assert connection.scalar(text("SELECT to_regclass('public.renter_portal_publication')")), (
        "M10-R3 migration 0043 has not created renter_portal_publication"
    )


def _insert_publication(
    connection: Connection,
    ids: _Ids,
    *,
    publication_id: str,
    tenancy_id: str | None = None,
    archive_id: str | None = None,
    artifact_id: str | None = None,
    document_type: str = "TENANT_STATEMENT",
    supersedes_id: str | None = None,
    account_id: str | None = None,
    membership_id: str | None = None,
    period_start: date | _UseSourceDate | None = _USE_SOURCE_DATE,
    period_end: date | _UseSourceDate | None = _USE_SOURCE_DATE,
    document_month: date | _UseSourceDate | None = _USE_SOURCE_DATE,
) -> None:
    account = account_id or ids.account_a
    tenancy = tenancy_id or ids.tenancy_a
    source_kind = "UVI_ARTIFACT" if artifact_id else "STATEMENT_ARCHIVE"
    if artifact_id:
        source_content = b"uvi-a"
        source_filename = f"{artifact_id}.pdf"
    elif archive_id == ids.archive_a_cover:
        source_content = b"cover-a"
        source_filename = "cover-a.pdf"
    elif archive_id == ids.archive_a_correction:
        source_content = b"tenant-a-correction"
        source_filename = "tenant-a-correction.pdf"
    elif archive_id == ids.archive_a_other:
        source_content = b"tenant-a2"
        source_filename = "tenant-a2.pdf"
    elif archive_id == ids.archive_b:
        source_content = b"tenant-b"
        source_filename = "tenant-b.pdf"
    else:
        source_content = b"tenant-a"
        source_filename = "tenant-a.pdf"
    source_period_start = (
        date(2024, 1, 1) if archive_id == ids.archive_a_other else date(2025, 1, 1)
    )
    source_period_end = (
        date(2024, 12, 31) if archive_id == ids.archive_a_other else date(2025, 12, 31)
    )
    resolved_period_start = (
        (None if artifact_id else source_period_start)
        if isinstance(period_start, _UseSourceDate)
        else period_start
    )
    resolved_period_end = (
        (None if artifact_id else source_period_end)
        if isinstance(period_end, _UseSourceDate)
        else period_end
    )
    resolved_document_month = (
        (date(2026, 8, 1) if artifact_id else None)
        if isinstance(document_month, _UseSourceDate)
        else document_month
    )
    has_display_columns = bool(
        connection.scalar(
            text(
                "SELECT count(*) = 3 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'renter_portal_publication' "
                "AND column_name IN ('period_start', 'period_end', 'document_month')"
            )
        )
    )
    display_columns = ", period_start, period_end, document_month" if has_display_columns else ""
    display_values = ", :period_start, :period_end, :document_month" if has_display_columns else ""
    connection.execute(
        text(
            "INSERT INTO renter_portal_publication "
            "(id, account_id, tenancy_id, source_kind, statement_archive_id, "
            "renter_delivery_artifact_id, document_type, content_bytes, sha256, mime_type, "
            "filename, published_by_membership_id, published_at, supersedes_publication_id"
            f"{display_columns}) "
            "VALUES (:id, :account, :tenancy, :source_kind, :archive, :artifact, :document_type, "
            ":content, :digest, 'application/pdf', :filename, :membership, "
            f":published_at, :supersedes{display_values})"
        ),
        {
            "id": publication_id,
            "account": account,
            "tenancy": tenancy,
            "source_kind": source_kind,
            "archive": archive_id,
            "artifact": artifact_id,
            "document_type": document_type,
            "content": source_content,
            "digest": sha256(source_content).hexdigest(),
            "filename": source_filename,
            "membership": membership_id or ids.membership_a,
            "published_at": datetime(2026, 9, 11, 13, 0, tzinfo=UTC),
            "supersedes": supersedes_id,
            "period_start": resolved_period_start,
            "period_end": resolved_period_end,
            "document_month": resolved_document_month,
        },
    )


def _set_context(connection: Connection, account_id: str, tenancy_id: str | None) -> None:
    connection.execute(
        text("SELECT set_config('app.account_id', :value, true)"), {"value": account_id}
    )
    connection.execute(
        text("SELECT set_config('app.tenancy_id', :value, true)"),
        {"value": tenancy_id or ""},
    )


def test_m10_pub_f01_migration_and_model_pin_exact_schema() -> None:
    migrations = sorted(_MIGRATIONS.glob("0043_*.py"))
    assert len(migrations) == 1, "M10-R3 migration 0043 is not implemented"
    tree = ast.parse(migrations[0].read_text())
    assignments = {
        node.targets[0].id: node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Constant)
    }
    assert assignments["revision"] == "0043"
    assert assignments["down_revision"] == "0042"
    model = getattr(lokara_db, "RenterPortalPublication", None)
    assert model is not None, "RenterPortalPublication model is not implemented"
    table = cast(Table, model.__table__)
    assert set(table.columns.keys()) == {
        "id",
        "account_id",
        "tenancy_id",
        "source_kind",
        "statement_archive_id",
        "renter_delivery_artifact_id",
        "document_type",
        "content_bytes",
        "sha256",
        "mime_type",
        "filename",
        "published_by_membership_id",
        "published_at",
        "supersedes_publication_id",
        "period_start",
        "period_end",
        "document_month",
        "created_at",
    }
    foreign_keys = {
        (tuple(fk.column_keys), tuple(element.target_fullname for element in fk.elements))
        for fk in table.constraints
        if isinstance(fk, ForeignKeyConstraint)
    }
    assert (
        ("statement_archive_id", "account_id", "tenancy_id"),
        (
            "statement_document_archive.id",
            "statement_document_archive.account_id",
            "statement_document_archive.tenancy_id",
        ),
    ) in foreign_keys
    assert (
        ("renter_delivery_artifact_id", "account_id", "tenancy_id"),
        (
            "renter_delivery_artifact.id",
            "renter_delivery_artifact.account_id",
            "renter_delivery_artifact.tenancy_id",
        ),
    ) in foreign_keys
    assert (
        ("published_by_membership_id", "account_id"),
        ("membership.id", "membership.account_id"),
    ) in foreign_keys
    assert (
        ("supersedes_publication_id", "account_id", "tenancy_id", "document_type"),
        (
            "renter_portal_publication.id",
            "renter_portal_publication.account_id",
            "renter_portal_publication.tenancy_id",
            "renter_portal_publication.document_type",
        ),
    ) in foreign_keys
    checks = " ".join(
        str(constraint.sqltext).lower()
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    )
    for marker in (
        "statement_archive",
        "uvi_artifact",
        "cover_letter",
        "tenant_statement",
        "period_start",
        "period_end",
        "document_month",
        "octet_length",
        "sha256",
        "supersedes_publication_id",
    ):
        assert marker in checks
    assert "ck_renter_portal_publication_display_period" in {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert {
        "uq_renter_portal_publication_statement_source",
        "uq_renter_portal_publication_uvi_source",
    } <= {index.name for index in table.indexes}
    uvi_delivery_event_table = cast(Table, lokara_db.UviDeliveryEvent.__table__)
    assert "uq_uvi_delivery_event_published_once" in {
        index.name for index in uvi_delivery_event_table.indexes
    }


def test_m10_pub_f08_migration_pins_safe_source_backfill_before_constraint() -> None:
    migrations = sorted(_MIGRATIONS.glob("0044_*.py"))
    assert len(migrations) == 1, "M10-R4 display metadata migration 0044 is not implemented"
    migration_source = migrations[0].read_text()
    tree = ast.parse(migration_source)
    assignments = {
        node.targets[0].id: node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Constant)
    }
    assert migrations[0].name == "0044_m10_renter_publication_display_period.py"
    assert assignments["revision"] == "0044"
    assert assignments["down_revision"] == "0043"

    upgrade_source = migration_source.split("def downgrade", maxsplit=1)[0].lower()
    for marker in (
        "period_start",
        "period_end",
        "document_month",
        "update public.renter_portal_publication",
        "statement_document_archive",
        "set period_start = statement.period_start",
        "period_end = statement.period_end",
        "renter_delivery_artifact",
        "set document_month = uvi_run.month",
        "ck_renter_portal_publication_display_period",
        "enforce_renter_portal_publication_source_m10",
    ):
        assert marker in upgrade_source
    last_source_backfill = max(
        upgrade_source.index("set period_start = statement.period_start"),
        upgrade_source.index("set document_month = uvi_run.month"),
    )
    constraint_position = upgrade_source.index("ck_renter_portal_publication_display_period")
    assert last_source_backfill < constraint_position
    assert "coalesce" not in upgrade_source, "0044 must not invent fallback display dates"


def test_m10_pub_f08_conditional_shape_and_source_dates_are_database_enforced(
    setup: tuple[Engine, Engine, _Ids],
) -> None:
    owner, _, ids = setup
    with owner.connect() as connection:
        transaction = connection.begin()
        try:
            columns = {
                str(value)
                for value in connection.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = 'public' "
                        "AND table_name = 'renter_portal_publication'"
                    )
                ).scalars()
            }
            assert {"period_start", "period_end", "document_month"} <= columns, (
                "M10-R4 publication display metadata columns are not implemented"
            )
            constraint = connection.scalar(
                text(
                    "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conrelid = 'public.renter_portal_publication'::regclass "
                    "AND conname = 'ck_renter_portal_publication_display_period'"
                )
            )
            assert constraint is not None
            normalized_constraint = str(constraint).lower()
            for marker in (
                "period_start",
                "period_end",
                "document_month",
                "source_kind",
                "statement_archive",
                "uvi_artifact",
            ):
                assert marker in normalized_constraint

            statement_publication = new_id()
            _insert_publication(
                connection,
                ids,
                publication_id=statement_publication,
                archive_id=ids.archive_a,
            )
            assert tuple(
                connection.execute(
                    text(
                        "SELECT period_start, period_end, document_month "
                        "FROM renter_portal_publication WHERE id = :id"
                    ),
                    {"id": statement_publication},
                ).one()
            ) == (date(2025, 1, 1), date(2025, 12, 31), None)

            uvi_nested = connection.begin_nested()
            uvi_publication = new_id()
            _insert_publication(
                connection,
                ids,
                publication_id=uvi_publication,
                artifact_id=ids.uvi_artifact_a,
                document_type="UVI",
            )
            assert tuple(
                connection.execute(
                    text(
                        "SELECT period_start, period_end, document_month "
                        "FROM renter_portal_publication WHERE id = :id"
                    ),
                    {"id": uvi_publication},
                ).one()
            ) == (None, None, date(2026, 8, 1))
            uvi_nested.rollback()

            cases: tuple[dict[str, Any], ...] = (
                {
                    "archive_id": ids.archive_a_cover,
                    "document_type": "COVER_LETTER",
                    "period_start": date(2024, 1, 1),
                    "period_end": date(2024, 12, 31),
                },
                {
                    "archive_id": ids.archive_a_cover,
                    "document_type": "COVER_LETTER",
                    "period_start": date(2025, 12, 31),
                    "period_end": date(2025, 1, 1),
                },
                {
                    "archive_id": ids.archive_a_cover,
                    "document_type": "COVER_LETTER",
                    "document_month": date(2026, 8, 1),
                },
                {
                    "artifact_id": ids.uvi_artifact_a,
                    "document_type": "UVI",
                    "document_month": date(2026, 7, 1),
                },
                {
                    "artifact_id": ids.uvi_artifact_a,
                    "document_type": "UVI",
                    "document_month": date(2026, 8, 2),
                },
                {
                    "artifact_id": ids.uvi_artifact_a,
                    "document_type": "UVI",
                    "period_start": date(2026, 8, 1),
                    "period_end": date(2026, 8, 31),
                },
            )
            for case in cases:
                nested = connection.begin_nested()
                with pytest.raises(DBAPIError):
                    _insert_publication(
                        connection,
                        ids,
                        publication_id=new_id(),
                        **case,
                    )
                nested.rollback()
        finally:
            transaction.rollback()


def test_m10_pub_f02_append_only_unique_sources_and_preserved_supersession(
    setup: tuple[Engine, Engine, _Ids],
) -> None:
    owner, _, ids = setup
    with owner.connect() as connection:
        transaction = connection.begin()
        try:
            _require_table(connection)
            first, second = new_id(), new_id()
            _insert_publication(connection, ids, publication_id=first, archive_id=ids.archive_a)
            _insert_publication(
                connection,
                ids,
                publication_id=second,
                archive_id=ids.archive_a_correction,
                supersedes_id=first,
            )
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM renter_portal_publication "
                        "WHERE id IN (:first, :second)"
                    ),
                    {"first": first, "second": second},
                )
                == 2
            )
            for statement, values in (
                (
                    "UPDATE renter_portal_publication SET filename = 'changed.pdf' WHERE id = :id",
                    {"id": first},
                ),
                ("DELETE FROM renter_portal_publication WHERE id = :id", {"id": first}),
            ):
                nested = connection.begin_nested()
                with pytest.raises(DBAPIError):
                    connection.execute(text(statement), values)
                nested.rollback()
            nested = connection.begin_nested()
            with pytest.raises(DBAPIError):
                _insert_publication(
                    connection, ids, publication_id=new_id(), archive_id=ids.archive_a
                )
            nested.rollback()
        finally:
            transaction.rollback()


def test_m10_pub_f03_composite_source_publisher_and_supersession_refusals_are_rollback_only(
    setup: tuple[Engine, Engine, _Ids],
) -> None:
    owner, _, ids = setup
    cases: tuple[dict[str, Any], ...] = (
        {"archive_id": ids.archive_b},
        {"archive_id": ids.archive_a_other},
        {"archive_id": ids.archive_a, "membership_id": ids.membership_b},
    )
    for case in cases:
        with owner.connect() as connection:
            transaction = connection.begin()
            try:
                _require_table(connection)
                with pytest.raises(DBAPIError):
                    _insert_publication(connection, ids, publication_id=new_id(), **case)
            finally:
                transaction.rollback()

    with owner.connect() as connection:
        transaction = connection.begin()
        try:
            _require_table(connection)
            predecessor = new_id()
            _insert_publication(
                connection, ids, publication_id=predecessor, archive_id=ids.archive_a
            )
            with pytest.raises(DBAPIError):
                _insert_publication(
                    connection,
                    ids,
                    publication_id=new_id(),
                    tenancy_id=ids.tenancy_a_other,
                    archive_id=ids.archive_a_other,
                    supersedes_id=predecessor,
                )
        finally:
            transaction.rollback()


def test_m10_pub_f04_forced_rls_owner_with_check_renter_select_and_write_refusals(
    setup: tuple[Engine, Engine, _Ids],
) -> None:
    owner, app, ids = setup
    with owner.connect() as connection:
        _require_table(connection)
        state = connection.execute(
            text(
                "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                "WHERE oid = 'public.renter_portal_publication'::regclass"
            )
        ).one()
        policies = connection.execute(
            text(
                "SELECT policyname, cmd, roles::text, qual, with_check FROM pg_policies "
                "WHERE schemaname = 'public' AND tablename = 'renter_portal_publication'"
            )
        ).all()
    assert tuple(state) == (True, True)
    assert {(row.policyname, row.cmd, row.roles) for row in policies} == {
        ("renter_portal_publication_owner_select", "SELECT", "{public}"),
        ("renter_portal_publication_owner_insert", "INSERT", "{public}"),
        ("renter_portal_publication_renter_select", "SELECT", "{lokara_app}"),
    }
    owner_insert = next(row for row in policies if row.cmd == "INSERT")
    assert owner_insert.with_check is not None
    assert "app.account_id" in str(owner_insert.with_check)
    assert "app.tenancy_id" in str(owner_insert.with_check)

    with app.connect() as connection:
        transaction = connection.begin()
        try:
            _require_table(connection)
            own, other = new_id(), new_id()
            _set_context(connection, ids.account_a, None)
            _insert_publication(connection, ids, publication_id=own, archive_id=ids.archive_a)
            _insert_publication(
                connection,
                ids,
                publication_id=other,
                tenancy_id=ids.tenancy_a_other,
                archive_id=ids.archive_a_other,
            )
            nested = connection.begin_nested()
            with pytest.raises(DBAPIError):
                _insert_publication(
                    connection,
                    ids,
                    publication_id=new_id(),
                    tenancy_id=ids.tenancy_b,
                    archive_id=ids.archive_b,
                    account_id=ids.account_b,
                    membership_id=ids.membership_b,
                )
            nested.rollback()
            _set_context(connection, ids.account_a, ids.tenancy_a)
            assert connection.execute(
                text("SELECT id FROM renter_portal_publication")
            ).scalars().all() == [own]
            for hidden in (
                "statement_document_archive",
                "renter_delivery_artifact",
                "statement",
                "uvi_run",
                "uvi_delivery_event",
            ):
                assert connection.scalar(text(f"SELECT count(*) FROM {hidden}")) == 0
            nested = connection.begin_nested()
            with pytest.raises(DBAPIError):
                _insert_publication(
                    connection,
                    ids,
                    publication_id=new_id(),
                    archive_id=ids.archive_a_cover,
                    document_type="COVER_LETTER",
                )
            nested.rollback()
        finally:
            transaction.rollback()
