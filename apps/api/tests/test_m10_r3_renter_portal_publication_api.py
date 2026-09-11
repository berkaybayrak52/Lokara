"""M10-R3 RED API contract for owner publication and renter retrieval."""

import json
import os
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from lokara_api import create_app
from lokara_api.deps import renter_session_for_path
from lokara_api.settings import ApiSettings
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
from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

_DB_PACKAGE_DIR = Path(__file__).resolve().parents[3] / "packages" / "db"


@dataclass(frozen=True)
class _Ids:
    account_a: str
    account_b: str
    owner_a: str
    owner_b: str
    employee_a: str
    adviser_a: str
    renter_person: str
    unlinked_person: str
    membership_owner_a: str
    membership_owner_b: str
    membership_employee_a: str
    membership_adviser_a: str
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
    statement_a_blocked: str
    statement_a_other: str
    statement_b: str
    archive_a: str
    archive_a_correction: str
    archive_a_cover: str
    archive_a_owner: str
    archive_a_blocked: str
    archive_a_other: str
    archive_b: str
    uvi_run_a: str
    uvi_artifact_a: str
    uvi_artifact_a_blocked: str
    annual_artifact_a: str


@dataclass(frozen=True)
class _Setup:
    client: TestClient
    owner: Engine
    ids: _Ids


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


def _link_renter(owner: Engine, ids: _Ids) -> None:
    raw = f"{ids.account_a}.m10-r3-{new_id()}"
    code_id = new_id()
    now = datetime.now(UTC)
    with owner.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO renter_activation_code "
                "(id, account_id, renter_id, tenancy_id, code_hash, expires_at, "
                "issued_by_membership_id, issued_at) VALUES "
                "(:id, :account, :renter, :tenancy, :digest, :expires, :membership, :now)"
            ),
            {
                "id": code_id,
                "account": ids.account_a,
                "renter": ids.renter_a,
                "tenancy": ids.tenancy_a,
                "digest": sha256(raw.encode()).hexdigest(),
                "expires": now + timedelta(hours=1),
                "membership": ids.membership_owner_a,
                "now": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO renter_activation_redemption "
                "(id, account_id, activation_code_id, renter_id, tenancy_id, person_id, "
                "redeemed_at) VALUES (:id, :account, :code, :renter, :tenancy, :person, :now)"
            ),
            {
                "id": new_id(),
                "account": ids.account_a,
                "code": code_id,
                "renter": ids.renter_a,
                "tenancy": ids.tenancy_a,
                "person": ids.renter_person,
                "now": now,
            },
        )
        connection.execute(
            text("UPDATE renter SET person_id = :person WHERE id = :renter"),
            {"person": ids.renter_person, "renter": ids.renter_a},
        )


@pytest.fixture(scope="module")
def setup() -> Iterator[_Setup]:
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
    ids = _Ids(*(new_id() for _ in range(39)))
    now = datetime(2026, 9, 11, 12, 0, tzinfo=UTC)
    with Session(owner) as session, session.begin():
        session.add_all(
            [
                Account(id=ids.account_a, name="M10-R3 API A"),
                Account(id=ids.account_b, name="M10-R3 API B"),
                Person(id=ids.owner_a, email=f"{ids.owner_a}@example.test"),
                Person(id=ids.owner_b, email=f"{ids.owner_b}@example.test"),
                Person(id=ids.employee_a, email=f"{ids.employee_a}@example.test"),
                Person(id=ids.adviser_a, email=f"{ids.adviser_a}@example.test"),
                Person(id=ids.renter_person, email=f"{ids.renter_person}@example.test"),
                Person(id=ids.unlinked_person, email=f"{ids.unlinked_person}@example.test"),
                Membership(
                    id=ids.membership_owner_a,
                    person_id=ids.owner_a,
                    account_id=ids.account_a,
                    role=Role.OWNER,
                    accepted_at=now,
                ),
                Membership(
                    id=ids.membership_owner_b,
                    person_id=ids.owner_b,
                    account_id=ids.account_b,
                    role=Role.OWNER,
                    accepted_at=now,
                ),
                Membership(
                    id=ids.membership_employee_a,
                    person_id=ids.employee_a,
                    account_id=ids.account_a,
                    role=Role.EMPLOYEE,
                    accepted_at=now,
                ),
                Membership(
                    id=ids.membership_adviser_a,
                    person_id=ids.adviser_a,
                    account_id=ids.account_a,
                    role=Role.TAX_ADVISOR,
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
                Renter(id=ids.renter_a_other, account_id=ids.account_a, legal_name="Mieter A2"),
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
            ]
        )
        statements: tuple[
            tuple[str, str, str, date, int, dict[str, list[str]], str | None], ...
        ] = (
            (
                ids.statement_a,
                ids.account_a,
                ids.building_a,
                date(2025, 1, 1),
                1,
                {"production_blockers": []},
                None,
            ),
            (
                ids.statement_a_correction,
                ids.account_a,
                ids.building_a,
                date(2025, 1, 1),
                2,
                {"production_blockers": []},
                ids.statement_a,
            ),
            (
                ids.statement_a_blocked,
                ids.account_a,
                ids.building_a,
                date(2023, 1, 1),
                1,
                {"production_blockers": ["verify-before-production"]},
                None,
            ),
            (
                ids.statement_a_other,
                ids.account_a,
                ids.building_a,
                date(2024, 1, 1),
                1,
                {"production_blockers": []},
                None,
            ),
            (
                ids.statement_b,
                ids.account_b,
                ids.building_b,
                date(2025, 1, 1),
                1,
                {"production_blockers": []},
                None,
            ),
        )
        for (
            statement_id,
            account_id,
            building_id,
            period_start,
            version,
            snapshot,
            supersedes,
        ) in statements:
            session.add(
                Statement(
                    id=statement_id,
                    account_id=account_id,
                    building_id=building_id,
                    period_start=period_start,
                    period_end=date(period_start.year, 12, 31),
                    version=version,
                    status=StatementStatus.FINALIZED,
                    total_cents=10_000,
                    content_hash=sha256(statement_id.encode()).hexdigest(),
                    finalized_snapshot=snapshot,
                    finalized_at=now,
                    supersedes_statement_id=supersedes,
                )
            )
    with Session(owner) as session, session.begin():
        archives = (
            (
                ids.archive_a,
                ids.account_a,
                ids.statement_a,
                "TENANT",
                ids.tenancy_a,
                "TENANT_STATEMENT",
                b"statement-a",
                "statement-a.pdf",
            ),
            (
                ids.archive_a_correction,
                ids.account_a,
                ids.statement_a_correction,
                "TENANT",
                ids.tenancy_a,
                "TENANT_STATEMENT",
                b"statement-a-v2",
                "statement-a-v2.pdf",
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
                ids.archive_a_owner,
                ids.account_a,
                ids.statement_a,
                "OWNER",
                None,
                "OWNER_OVERVIEW",
                b"owner-a",
                "owner-a.pdf",
            ),
            (
                ids.archive_a_blocked,
                ids.account_a,
                ids.statement_a_blocked,
                "TENANT",
                ids.tenancy_a,
                "TENANT_STATEMENT",
                b"blocked-a",
                "blocked-a.pdf",
            ),
            (
                ids.archive_a_other,
                ids.account_a,
                ids.statement_a_other,
                "TENANT",
                ids.tenancy_a_other,
                "TENANT_STATEMENT",
                b"statement-a2",
                "statement-a2.pdf",
            ),
            (
                ids.archive_b,
                ids.account_b,
                ids.statement_b,
                "TENANT",
                ids.tenancy_b,
                "TENANT_STATEMENT",
                b"statement-b",
                "statement-b.pdf",
            ),
        )
        for (
            archive_id,
            account_id,
            statement_id,
            audience,
            tenancy_id,
            document_type,
            content,
            filename,
        ) in archives:
            session.add(
                StatementArchive(
                    id=archive_id,
                    account_id=account_id,
                    statement_id=statement_id,
                    audience=audience,
                    tenancy_id=tenancy_id,
                    document_type=document_type,
                    content_bytes=content,
                    sha256=sha256(content).hexdigest(),
                    mime_type="application/pdf",
                    filename=filename,
                )
            )
    with Session(owner) as session, session.begin():
        payload: dict[str, object] = {
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
                sha256=_canonical_uvi_hash(session, payload),
                **payload,
            )
        )
        session.flush()
        for artifact_id, kind, statement_archive_id, blockers, content in (
            (ids.uvi_artifact_a, "UVI", None, [], b"uvi-a"),
            (ids.uvi_artifact_a_blocked, "UVI", None, ["verify-before-production"], b"uvi-blocked"),
            (ids.annual_artifact_a, "ANNUAL_STATEMENT", ids.archive_a_cover, [], b"cover-a"),
        ):
            session.add(
                RenterDeliveryArtifact(
                    id=artifact_id,
                    account_id=ids.account_a,
                    building_id=ids.building_a,
                    unit_id=ids.unit_a,
                    tenancy_id=ids.tenancy_a,
                    renter_id=ids.renter_a,
                    artifact_kind=kind,
                    occurrence_key=f"m10-r3:{artifact_id}",
                    statement_archive_id=statement_archive_id,
                    uvi_run_id=ids.uvi_run_a if kind == "UVI" else None,
                    content_bytes=content,
                    sha256=sha256(content).hexdigest(),
                    mime_type="application/pdf",
                    filename=f"{artifact_id}.pdf",
                    production_blockers_snapshot=blockers,
                    generated_at=now,
                )
            )
    _link_renter(owner, ids)
    client = TestClient(create_app())
    try:
        yield _Setup(client=client, owner=owner, ids=ids)
    finally:
        client.close()
        owner.dispose()


def _token(person_id: str) -> dict[str, str]:
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": person_id,
            "iss": ApiSettings().supabase_jwt_issuer,
            "aud": "authenticated",
            "role": "authenticated",
            "iat": now,
            "exp": now + 3600,
        },
        ApiSettings().supabase_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _publication_request(
    ids: _Ids,
    *,
    archive_id: str | None = None,
    artifact_id: str | None = None,
    tenancy_id: str | None = None,
    supersedes_id: str | None = None,
) -> dict[str, object]:
    return {
        "tenancyId": tenancy_id or ids.tenancy_a,
        "statementArchiveId": archive_id,
        "renterDeliveryArtifactId": artifact_id,
        "supersedesPublicationId": supersedes_id,
    }


def _assert_publication_shape(body: dict[str, object], ids: _Ids) -> None:
    assert set(body) == {
        "id",
        "tenancyId",
        "sourceKind",
        "documentType",
        "filename",
        "mimeType",
        "sha256",
        "publishedAt",
        "supersedesPublicationId",
        "downloadUrl",
    }
    assert body["tenancyId"] == ids.tenancy_a
    assert body["mimeType"] == "application/pdf"
    assert body["downloadUrl"] == f"/renter/{ids.tenancy_a}/documents/{body['id']}/download"
    datetime.fromisoformat(str(body["publishedAt"]).replace("Z", "+00:00"))


def _publish_all(setup: _Setup) -> tuple[Any, Any, Any, Any]:
    client, ids = setup.client, setup.ids
    first = client.post(
        f"/a/{ids.account_a}/renter-portal-publications",
        headers=_token(ids.owner_a),
        json=_publication_request(ids, archive_id=ids.archive_a),
    )
    if first.status_code not in {200, 201}:
        return first, first, first, first
    repeated = client.post(
        f"/a/{ids.account_a}/renter-portal-publications",
        headers=_token(ids.owner_a),
        json=_publication_request(ids, archive_id=ids.archive_a),
    )
    correction = client.post(
        f"/a/{ids.account_a}/renter-portal-publications",
        headers=_token(ids.owner_a),
        json=_publication_request(
            ids,
            archive_id=ids.archive_a_correction,
            supersedes_id=str(first.json()["id"]),
        ),
    )
    uvi = client.post(
        f"/a/{ids.account_a}/renter-portal-publications",
        headers=_token(ids.owner_a),
        json=_publication_request(ids, artifact_id=ids.uvi_artifact_a),
    )
    return first, repeated, correction, uvi


def test_m10_pub_f02_f03_f05_owner_publication_is_exact_idempotent_copy(
    setup: _Setup,
) -> None:
    ids = setup.ids
    first_response, repeated_response, correction_response, uvi_response = _publish_all(setup)
    assert first_response.status_code == 201, (
        "M10-R3 owner publication endpoint is not implemented",
        first_response.status_code,
        first_response.text,
    )
    assert repeated_response.status_code == 200
    assert repeated_response.json() == first_response.json()
    assert correction_response.status_code == 201
    assert uvi_response.status_code == 201
    statement = first_response.json()
    correction = correction_response.json()
    uvi = uvi_response.json()
    _assert_publication_shape(statement, ids)
    assert statement["sourceKind"] == "STATEMENT_ARCHIVE"
    assert statement["documentType"] == "TENANT_STATEMENT"
    assert statement["filename"] == "statement-a.pdf"
    assert statement["sha256"] == sha256(b"statement-a").hexdigest()
    assert statement["supersedesPublicationId"] is None
    _assert_publication_shape(correction, ids)
    assert correction["supersedesPublicationId"] == statement["id"]
    _assert_publication_shape(uvi, ids)
    assert uvi["sourceKind"] == "UVI_ARTIFACT"
    assert uvi["documentType"] == "UVI"
    assert uvi["sha256"] == sha256(b"uvi-a").hexdigest()
    with setup.owner.connect() as connection:
        row = connection.execute(
            text(
                "SELECT content_bytes, sha256, mime_type, filename FROM renter_portal_publication "
                "WHERE id = :id"
            ),
            {"id": statement["id"]},
        ).one()
        assert tuple(row) == (
            b"statement-a",
            sha256(b"statement-a").hexdigest(),
            "application/pdf",
            "statement-a.pdf",
        )
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM uvi_delivery_event "
                    "WHERE uvi_run_id = :run AND status = 'PUBLISHED'"
                ),
                {"run": ids.uvi_run_a},
            )
            == 1
        )


@pytest.mark.parametrize(
    ("person", "account"),
    (
        ("employee_a", "account_a"),
        ("adviser_a", "account_a"),
        ("renter_person", "account_a"),
        ("owner_b", "account_a"),
    ),
)
def test_m10_pub_f05_only_exact_account_owner_can_publish(
    setup: _Setup, person: str, account: str
) -> None:
    ids = setup.ids
    response = setup.client.post(
        f"/a/{getattr(ids, account)}/renter-portal-publications",
        headers=_token(getattr(ids, person)),
        json=_publication_request(ids, archive_id=ids.archive_a_cover),
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("payload", "expected_status"),
    (
        ({}, 422),
        ({"archive": "archive_a", "artifact": "uvi_artifact_a"}, 422),
        ({"archive": "archive_a_owner"}, 422),
        ({"archive": "archive_a_blocked"}, 422),
        ({"archive": "archive_a_other"}, 404),
        ({"archive": "archive_b"}, 404),
        ({"artifact": "uvi_artifact_a_blocked"}, 422),
        ({"artifact": "annual_artifact_a"}, 422),
    ),
)
def test_m10_pub_f03_ineligible_or_foreign_sources_are_refused_without_evidence(
    setup: _Setup, payload: dict[str, str], expected_status: int
) -> None:
    ids = setup.ids
    with setup.owner.connect() as connection:
        before = connection.scalar(
            text(
                "SELECT count(*) FROM uvi_delivery_event "
                "WHERE uvi_run_id = :run AND status = 'PUBLISHED'"
            ),
            {"run": ids.uvi_run_a},
        )
    request = _publication_request(
        ids,
        archive_id=getattr(ids, payload["archive"]) if "archive" in payload else None,
        artifact_id=getattr(ids, payload["artifact"]) if "artifact" in payload else None,
    )
    response = setup.client.post(
        f"/a/{ids.account_a}/renter-portal-publications",
        headers=_token(ids.owner_a),
        json=request,
    )
    assert response.status_code == expected_status
    with setup.owner.connect() as connection:
        after = connection.scalar(
            text(
                "SELECT count(*) FROM uvi_delivery_event "
                "WHERE uvi_run_id = :run AND status = 'PUBLISHED'"
            ),
            {"run": ids.uvi_run_a},
        )
    assert after == before


def test_m10_pub_f06_renter_list_is_exact_ordered_and_preserves_superseded_versions(
    setup: _Setup,
) -> None:
    ids = setup.ids
    first_response, _, correction_response, uvi_response = _publish_all(setup)
    assert first_response.status_code == 200
    assert correction_response.status_code == 200
    assert uvi_response.status_code == 200
    published = (first_response.json(), correction_response.json(), uvi_response.json())
    response = setup.client.get(
        f"/renter/{ids.tenancy_a}/documents",
        headers=_token(ids.renter_person),
    )
    assert response.status_code == 200
    assert set(response.json()) == {"documents"}
    documents = response.json()["documents"]
    assert {row["id"] for row in documents} == {
        published[0]["id"],
        published[1]["id"],
        published[2]["id"],
    }
    assert documents == sorted(documents, key=lambda row: (row["publishedAt"], row["id"]))
    for row in documents:
        _assert_publication_shape(row, ids)


@pytest.mark.parametrize("target", ("same_account_other", "cross_account", "unlinked"))
def test_m10_pub_f06_other_tenancies_and_unlinked_callers_are_undiscoverable(
    setup: _Setup, target: str
) -> None:
    ids = setup.ids
    tenancy_id = ids.tenancy_a
    person_id = ids.renter_person
    if target == "same_account_other":
        tenancy_id = ids.tenancy_a_other
    elif target == "cross_account":
        tenancy_id = ids.tenancy_b
    else:
        person_id = ids.unlinked_person
    response = setup.client.get(
        f"/renter/{tenancy_id}/documents",
        headers=_token(person_id),
    )
    assert response.status_code == 404


def test_m10_pub_f07_download_returns_verified_publication_bytes_only(
    setup: _Setup,
) -> None:
    ids = setup.ids
    first_response, _, _, _ = _publish_all(setup)
    assert first_response.status_code == 200
    publication_id = first_response.json()["id"]
    response = setup.client.get(
        f"/renter/{ids.tenancy_a}/documents/{publication_id}/download",
        headers=_token(ids.renter_person),
    )
    assert response.status_code == 200
    assert response.content == b"statement-a"
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["x-content-sha256"] == sha256(b"statement-a").hexdigest()
    assert response.headers["content-disposition"] == 'attachment; filename="statement-a.pdf"'

    foreign = setup.client.get(
        f"/renter/{ids.tenancy_a_other}/documents/{publication_id}/download",
        headers=_token(ids.renter_person),
    )
    assert foreign.status_code == 404
    unpublished = setup.client.get(
        f"/renter/{ids.tenancy_a}/documents/{ids.archive_a_cover}/download",
        headers=_token(ids.renter_person),
    )
    assert unpublished.status_code == 404


def test_m10_pub_f07_digest_mismatch_is_409_and_probe_is_rolled_back(setup: _Setup) -> None:
    ids = setup.ids
    publication_id = new_id()
    with setup.owner.connect() as connection:
        transaction = connection.begin()
        try:
            assert connection.scalar(
                text("SELECT to_regclass('public.renter_portal_publication')")
            ), "M10-R3 migration 0043 has not created renter_portal_publication"
            connection.execute(
                text(
                    "INSERT INTO renter_portal_publication "
                    "(id, account_id, tenancy_id, source_kind, statement_archive_id, "
                    "renter_delivery_artifact_id, document_type, content_bytes, sha256, mime_type, "
                    "filename, published_by_membership_id, published_at, "
                    "supersedes_publication_id) "
                    "VALUES (:id, :account, :tenancy, 'STATEMENT_ARCHIVE', :archive, NULL, "
                    "'COVER_LETTER', :content, :digest, 'application/pdf', 'corrupt.pdf', "
                    ":membership, :now, NULL)"
                ),
                {
                    "id": publication_id,
                    "account": ids.account_a,
                    "tenancy": ids.tenancy_a,
                    "archive": ids.archive_a_cover,
                    "content": b"corrupt-bytes",
                    "digest": sha256(b"cover-a").hexdigest(),
                    "membership": ids.membership_owner_a,
                    "now": datetime.now(UTC),
                },
            )

            def same_transaction_renter_session() -> Iterator[Session]:
                with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                    yield session

            app = cast(FastAPI, setup.client.app)
            app.dependency_overrides[renter_session_for_path] = same_transaction_renter_session
            response = setup.client.get(
                f"/renter/{ids.tenancy_a}/documents/{publication_id}/download",
                headers=_token(ids.renter_person),
            )
            assert response.status_code == 409
            assert response.content != b"corrupt-bytes"
        finally:
            app.dependency_overrides.pop(renter_session_for_path, None)
            transaction.rollback()
