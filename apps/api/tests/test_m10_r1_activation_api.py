"""M10-R1 HTTP contract: owner issuance and authenticated spend-once redemption."""

import logging
import os
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from secrets import token_urlsafe
from typing import Any, Protocol

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from lokara_api import create_app
from lokara_api.settings import ApiSettings
from lokara_db import (
    Account,
    Building,
    DbSettings,
    Membership,
    Person,
    Renter,
    Role,
    Tenancy,
    TenancyParty,
    Unit,
    create_db_engine,
    new_id,
)
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session

_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "db"
_COPY_03 = (
    "Die Aktivierung war nicht möglich. Bitte prüfen Sie den Code oder wenden Sie sich an Ihre "
    "Vermieterin oder Ihren Vermieter."
)


@dataclass(frozen=True)
class _Ids:
    account_a: str
    account_b: str
    owner_a: str
    employee_a: str
    owner_b: str
    membership_owner_a: str
    membership_owner_b: str
    building_a: str
    building_b: str
    unit_a: str
    unit_b: str
    tenancy_a: str
    tenancy_a_other: str
    tenancy_b: str
    renter_a: str
    renter_a_other: str
    renter_b: str
    caller_1: str
    caller_2: str


class _Response(Protocol):
    status_code: int

    def json(self) -> Any: ...


@pytest.fixture(scope="module")
def setup() -> Iterator[tuple[TestClient, Engine, _Ids]]:
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
    with owner.connect() as connection:
        tables = set(
            connection.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                    "AND tablename IN ('renter_activation_code', 'renter_activation_redemption')"
                )
            ).scalars()
        )
        expected = {"renter_activation_code", "renter_activation_redemption"}
    if tables != expected:
        pytest.fail(f"M10-R1 activation tables are not implemented: missing {expected - tables}")

    ids = _Ids(*(new_id() for _ in range(19)))
    with Session(owner) as session, session.begin():
        session.add_all(
            [
                Account(id=ids.account_a, name="M10 Konto A"),
                Account(id=ids.account_b, name="M10 Konto B"),
                Person(id=ids.owner_a, email=f"{ids.owner_a}@example.test"),
                Person(id=ids.employee_a, email=f"{ids.employee_a}@example.test"),
                Person(id=ids.owner_b, email=f"{ids.owner_b}@example.test"),
                Person(id=ids.caller_1, email=f"{ids.caller_1}@example.test"),
                Person(id=ids.caller_2, email=f"{ids.caller_2}@example.test"),
            ]
        )
        session.add_all(
            [
                Membership(
                    id=ids.membership_owner_a,
                    person_id=ids.owner_a,
                    account_id=ids.account_a,
                    role=Role.OWNER,
                    accepted_at=datetime(2026, 9, 11, tzinfo=UTC),
                ),
                Membership(
                    person_id=ids.employee_a,
                    account_id=ids.account_a,
                    role=Role.EMPLOYEE,
                    accepted_at=datetime(2026, 9, 11, tzinfo=UTC),
                ),
                Membership(
                    id=ids.membership_owner_b,
                    person_id=ids.owner_b,
                    account_id=ids.account_b,
                    role=Role.OWNER,
                    accepted_at=datetime(2026, 9, 11, tzinfo=UTC),
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
                    label="WE A",
                    area_sqm_x100=5_000,
                ),
                Unit(
                    id=ids.unit_b,
                    account_id=ids.account_b,
                    building_id=ids.building_b,
                    label="WE B",
                    area_sqm_x100=5_000,
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
                    valid_from=date(2026, 1, 1),
                    valid_to=None,
                    base_rent_cents=80_000,
                ),
                Tenancy(
                    id=ids.tenancy_a_other,
                    account_id=ids.account_a,
                    unit_id=ids.unit_a,
                    valid_from=date(2025, 1, 1),
                    valid_to=date(2026, 1, 1),
                    base_rent_cents=70_000,
                ),
                Tenancy(
                    id=ids.tenancy_b,
                    account_id=ids.account_b,
                    unit_id=ids.unit_b,
                    valid_from=date(2026, 1, 1),
                    valid_to=None,
                    base_rent_cents=90_000,
                ),
            ]
        )
    with Session(owner) as session, session.begin():
        session.add_all(
            [
                TenancyParty(
                    account_id=ids.account_a,
                    tenancy_id=ids.tenancy_a,
                    renter_id=ids.renter_a,
                ),
                TenancyParty(
                    account_id=ids.account_a,
                    tenancy_id=ids.tenancy_a_other,
                    renter_id=ids.renter_a_other,
                ),
                TenancyParty(
                    account_id=ids.account_b,
                    tenancy_id=ids.tenancy_b,
                    renter_id=ids.renter_b,
                ),
            ]
        )
    client = TestClient(create_app())
    yield client, owner, ids
    client.close()
    owner.dispose()


def _token(person_id: str) -> dict[str, str]:
    now = int(time.time())
    encoded = jwt.encode(
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
    return {"Authorization": f"Bearer {encoded}"}


def _owner_path(ids: _Ids, *, account: str | None = None) -> str:
    return (
        f"/a/{account or ids.account_a}/tenancies/{ids.tenancy_a}/renters/"
        f"{ids.renter_a}/activation-codes"
    )


def _redeem_path(tenancy_id: str) -> str:
    return f"/renter/{tenancy_id}/activation"


def _raw_code(account_id: str) -> str:
    """A non-secret account locator plus 256 random secret bits."""
    return f"{account_id}.{token_urlsafe(32)}"


def _insert_code(
    owner: Engine,
    ids: _Ids,
    raw: str,
    *,
    account_id: str | None = None,
    tenancy_id: str | None = None,
    renter_id: str | None = None,
    membership_id: str | None = None,
    expires_at: datetime | None = None,
) -> str:
    code_id = new_id()
    expected_account = account_id or ids.account_a
    locator, separator, secret = raw.partition(".")
    assert separator == "." and locator == expected_account and len(secret) >= 43
    with owner.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO renter_activation_code "
                "(id, account_id, renter_id, tenancy_id, code_hash, expires_at, "
                "issued_by_membership_id, issued_at) "
                "VALUES (:id, :account, :renter, :tenancy, :hash, :expires, :membership, :issued)"
            ),
            {
                "id": code_id,
                "account": expected_account,
                "renter": renter_id or ids.renter_a,
                "tenancy": tenancy_id or ids.tenancy_a,
                "hash": sha256(raw.encode()).hexdigest(),
                "expires": expires_at or datetime.now(UTC) + timedelta(hours=1),
                "membership": membership_id or ids.membership_owner_a,
                "issued": datetime.now(UTC),
            },
        )
    return code_id


def _state(owner: Engine, renter_id: str, code_id: str | None) -> tuple[str | None, int]:
    with owner.connect() as connection:
        person_id = connection.scalar(
            text("SELECT person_id FROM renter WHERE id = :id"), {"id": renter_id}
        )
        spent = 0
        if code_id is not None:
            spent = int(
                connection.scalar(
                    text(
                        "SELECT count(*) FROM renter_activation_redemption "
                        "WHERE activation_code_id = :id"
                    ),
                    {"id": code_id},
                )
                or 0
            )
    return person_id, spent


def _insert_redemption(
    owner: Engine,
    ids: _Ids,
    *,
    code_id: str,
    renter_id: str,
    tenancy_id: str,
    person_id: str,
) -> None:
    with owner.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO renter_activation_redemption "
                "(id, account_id, activation_code_id, renter_id, tenancy_id, person_id, "
                "redeemed_at) VALUES "
                "(:id, :account, :code, :renter, :tenancy, :person, :redeemed)"
            ),
            {
                "id": new_id(),
                "account": ids.account_a,
                "code": code_id,
                "renter": renter_id,
                "tenancy": tenancy_id,
                "person": person_id,
                "redeemed": datetime.now(UTC),
            },
        )


def _attempt_rows(
    owner: Engine, raw: str, *, account_id: str
) -> list[tuple[str, str | None, str, str, str]]:
    with owner.connect() as connection:
        return [
            (row.id, row.activation_code_id, row.requested_tenancy_id, row.subject_id, row.outcome)
            for row in connection.execute(
                text(
                    "SELECT id, activation_code_id, requested_tenancy_id, subject_id, outcome "
                    "FROM renter_activation_attempt WHERE account_id = :account "
                    "AND code_digest = :digest ORDER BY attempted_at"
                ),
                {"account": account_id, "digest": sha256(raw.encode()).hexdigest()},
            )
        ]


def _assert_public_refusal(response: _Response) -> None:
    assert response.status_code == 400
    assert response.json() == {"detail": _COPY_03}


def _assert_internal_outcome(caplog: pytest.LogCaptureFixture, expected: str, raw: str) -> None:
    assert expected in caplog.text
    assert raw not in caplog.text, "raw activation codes must never enter logs"


def test_openapi_exposes_only_the_two_approved_activation_routes() -> None:
    document = create_app().openapi()
    assert (
        "/a/{account_id}/tenancies/{tenancy_id}/renters/{renter_id}/activation-codes"
        in document["paths"]
    )
    assert "/renter/{tenancy_id}/activation" in document["paths"]
    request_schema = document["paths"]["/renter/{tenancy_id}/activation"]["post"]["requestBody"]
    assert "personId" not in str(request_schema)
    assert "person_id" not in str(request_schema)


def test_owner_only_issuance_returns_raw_once_and_persists_only_its_hash(
    setup: tuple[TestClient, Engine, _Ids],
) -> None:
    client, owner, ids = setup
    response = client.post(_owner_path(ids), headers=_token(ids.owner_a), json={})
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"activationCodeId", "activationCode", "expiresAt"}
    raw = body["activationCode"]
    assert isinstance(raw, str) and len(raw) >= 32
    locator, secret = raw.split(".", 1)
    assert locator == ids.account_a
    assert len(secret) >= 43  # base64url encoding of at least 32 random bytes
    assert datetime.fromisoformat(body["expiresAt"]) > datetime.now(UTC)
    with owner.connect() as connection:
        stored = connection.execute(
            text(
                "SELECT code_hash, row_to_json(c)::text FROM renter_activation_code c "
                "WHERE id = :id"
            ),
            {"id": body["activationCodeId"]},
        ).one()
    assert stored.code_hash == sha256(raw.encode()).hexdigest()
    assert raw not in stored[1]

    for person_id in (ids.employee_a, ids.owner_b):
        refused = client.post(_owner_path(ids), headers=_token(person_id), json={})
        assert refused.status_code == 403


def test_success_links_the_authenticated_person_and_appends_one_spend(
    setup: tuple[TestClient, Engine, _Ids],
) -> None:
    client, owner, ids = setup
    raw = _raw_code(ids.account_a)
    code_id = _insert_code(owner, ids, raw)
    response = client.post(
        _redeem_path(ids.tenancy_a),
        headers=_token(ids.caller_1),
        json={"activationCode": raw},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True, "tenancyId": ids.tenancy_a, "renterId": ids.renter_a}
    assert _state(owner, ids.renter_a, code_id) == (ids.caller_1, 1)

    with pytest.raises(DBAPIError, match="append-only"), owner.begin() as connection:
        connection.execute(
            text(
                "UPDATE renter_activation_redemption SET redeemed_at = now() "
                "WHERE activation_code_id = :id"
            ),
            {"id": code_id},
        )
    with pytest.raises(DBAPIError, match="append-only"), owner.begin() as connection:
        connection.execute(
            text("DELETE FROM renter_activation_redemption WHERE activation_code_id = :id"),
            {"id": code_id},
        )


def test_renter_person_id_cannot_be_filled_outside_activation_redemption(
    setup: tuple[TestClient, Engine, _Ids],
) -> None:
    _, owner, ids = setup
    renter_id = new_id()
    with Session(owner) as session, session.begin():
        session.add(Renter(id=renter_id, account_id=ids.account_a, legal_name="Kein Direktlink"))
    with pytest.raises(DBAPIError, match="activation"), owner.begin() as connection:
        connection.execute(
            text("UPDATE renter SET person_id = :person WHERE id = :renter"),
            {"person": ids.caller_2, "renter": renter_id},
        )


def test_m10_act_f01_spent_is_uniform_and_does_not_mutate(
    setup: tuple[TestClient, Engine, _Ids], caplog: pytest.LogCaptureFixture
) -> None:
    client, owner, ids = setup
    raw = _raw_code(ids.account_a)
    # Use the second renter so this test is independent of the positive fixture.
    code_id = _insert_code(
        owner, ids, raw, tenancy_id=ids.tenancy_a_other, renter_id=ids.renter_a_other
    )
    first = client.post(
        _redeem_path(ids.tenancy_a_other),
        headers=_token(ids.caller_2),
        json={"activationCode": raw},
    )
    assert first.status_code == 200
    before = _state(owner, ids.renter_a_other, code_id)
    caplog.set_level(logging.INFO)
    response = client.post(
        _redeem_path(ids.tenancy_a_other),
        headers=_token(ids.caller_1),
        json={"activationCode": raw},
    )
    _assert_public_refusal(response)
    _assert_internal_outcome(caplog, "ACTIVATION_CODE_SPENT", raw)
    assert _state(owner, ids.renter_a_other, code_id) == before
    attempts = _attempt_rows(owner, raw, account_id=ids.account_a)
    assert [(row[1], row[2], row[3], row[4]) for row in attempts] == [
        (code_id, ids.tenancy_a_other, ids.caller_1, "ACTIVATION_CODE_SPENT")
    ]


def test_m10_act_f02_expiry_boundary_is_now_greater_than_or_equal(
    setup: tuple[TestClient, Engine, _Ids], caplog: pytest.LogCaptureFixture
) -> None:
    client, owner, ids = setup
    raw = _raw_code(ids.account_a)
    code_id = _insert_code(owner, ids, raw, expires_at=datetime.now(UTC))
    before = _state(owner, ids.renter_a, code_id)
    caplog.set_level(logging.INFO)
    response = client.post(
        _redeem_path(ids.tenancy_a),
        headers=_token(ids.caller_2),
        json={"activationCode": raw},
    )
    _assert_public_refusal(response)
    _assert_internal_outcome(caplog, "ACTIVATION_CODE_EXPIRED", raw)
    assert _state(owner, ids.renter_a, code_id) == before
    attempts = _attempt_rows(owner, raw, account_id=ids.account_a)
    assert [(row[1], row[2], row[3], row[4]) for row in attempts] == [
        (code_id, ids.tenancy_a, ids.caller_2, "ACTIVATION_CODE_EXPIRED")
    ]
    attempt_id = attempts[0][0]
    with pytest.raises(DBAPIError, match="append-only"), owner.begin() as connection:
        connection.execute(
            text("UPDATE renter_activation_attempt SET outcome = 'CHANGED' WHERE id = :id"),
            {"id": attempt_id},
        )
    with pytest.raises(DBAPIError, match="append-only"), owner.begin() as connection:
        connection.execute(
            text("DELETE FROM renter_activation_attempt WHERE id = :id"),
            {"id": attempt_id},
        )


def test_m10_act_f03_wrong_tenancy_is_uniform_and_does_not_mutate(
    setup: tuple[TestClient, Engine, _Ids], caplog: pytest.LogCaptureFixture
) -> None:
    client, owner, ids = setup
    raw = _raw_code(ids.account_a)
    code_id = _insert_code(owner, ids, raw)
    before = _state(owner, ids.renter_a, code_id)
    caplog.set_level(logging.INFO)
    response = client.post(
        _redeem_path(ids.tenancy_a_other),
        headers=_token(ids.caller_2),
        json={"activationCode": raw},
    )
    _assert_public_refusal(response)
    _assert_internal_outcome(caplog, "ACTIVATION_TENANCY_MISMATCH", raw)
    assert _state(owner, ids.renter_a, code_id) == before
    attempts = _attempt_rows(owner, raw, account_id=ids.account_a)
    assert [(row[1], row[2], row[3], row[4]) for row in attempts] == [
        (code_id, ids.tenancy_a_other, ids.caller_2, "ACTIVATION_TENANCY_MISMATCH")
    ]


def test_m10_act_f04_foreign_account_locator_is_uniform_and_does_not_mutate(
    setup: tuple[TestClient, Engine, _Ids], caplog: pytest.LogCaptureFixture
) -> None:
    client, owner, ids = setup
    raw = _raw_code(ids.account_b)
    code_id = _insert_code(
        owner,
        ids,
        raw,
        account_id=ids.account_b,
        tenancy_id=ids.tenancy_b,
        renter_id=ids.renter_b,
        membership_id=ids.membership_owner_b,
    )
    before = _state(owner, ids.renter_b, code_id)
    caplog.set_level(logging.INFO)
    response = client.post(
        _redeem_path(ids.tenancy_a),
        headers=_token(ids.caller_2),
        json={"activationCode": raw},
    )
    _assert_public_refusal(response)
    # Forced RLS must not perform a second/global lookup just to distinguish this
    # case. The safe live outcome is the same as an unknown code.
    _assert_internal_outcome(caplog, "ACTIVATION_CODE_UNKNOWN", raw)
    assert _state(owner, ids.renter_b, code_id) == before
    attempts = _attempt_rows(owner, raw, account_id=ids.account_b)
    assert [(row[1], row[2], row[3], row[4]) for row in attempts] == [
        (None, ids.tenancy_a, ids.caller_2, "ACTIVATION_CODE_UNKNOWN")
    ]


def test_m10_act_f05_already_linked_keeps_link_and_code_unspent(
    setup: tuple[TestClient, Engine, _Ids], caplog: pytest.LogCaptureFixture
) -> None:
    client, owner, ids = setup
    raw = _raw_code(ids.account_a)
    renter_id = new_id()
    tenancy_id = new_id()
    with Session(owner) as session, session.begin():
        session.add(
            Renter(
                id=renter_id,
                account_id=ids.account_a,
                legal_name="Bereits verknüpft",
            )
        )
        session.add(
            Tenancy(
                id=tenancy_id,
                account_id=ids.account_a,
                unit_id=ids.unit_a,
                valid_from=date(2028, 1, 1),
                valid_to=None,
                base_rent_cents=80_000,
            )
        )
    with Session(owner) as session, session.begin():
        session.add(
            TenancyParty(
                account_id=ids.account_a,
                tenancy_id=tenancy_id,
                renter_id=renter_id,
            )
        )
    evidence_raw = _raw_code(ids.account_a)
    evidence_code_id = _insert_code(
        owner,
        ids,
        evidence_raw,
        tenancy_id=tenancy_id,
        renter_id=renter_id,
    )
    _insert_redemption(
        owner,
        ids,
        code_id=evidence_code_id,
        renter_id=renter_id,
        tenancy_id=tenancy_id,
        person_id=ids.caller_1,
    )
    with owner.begin() as connection:
        connection.execute(
            text("UPDATE renter SET person_id = :person WHERE id = :renter"),
            {"person": ids.caller_1, "renter": renter_id},
        )
    code_id = _insert_code(owner, ids, raw, tenancy_id=tenancy_id, renter_id=renter_id)
    before = _state(owner, renter_id, code_id)
    caplog.set_level(logging.INFO)
    response = client.post(
        _redeem_path(tenancy_id),
        headers=_token(ids.caller_1),
        json={"activationCode": raw},
    )
    _assert_public_refusal(response)
    _assert_internal_outcome(caplog, "RENTER_ALREADY_LINKED", raw)
    assert _state(owner, renter_id, code_id) == before
    attempts = _attempt_rows(owner, raw, account_id=ids.account_a)
    assert [(row[1], row[2], row[3], row[4]) for row in attempts] == [
        (code_id, tenancy_id, ids.caller_1, "RENTER_ALREADY_LINKED")
    ]


def test_m10_act_f06_unknown_person_is_uniform_and_does_not_mutate(
    setup: tuple[TestClient, Engine, _Ids], caplog: pytest.LogCaptureFixture
) -> None:
    client, owner, ids = setup
    raw = _raw_code(ids.account_a)
    code_id = _insert_code(owner, ids, raw)
    before = _state(owner, ids.renter_a, code_id)
    unknown_person_id = new_id()
    caplog.set_level(logging.INFO)
    response = client.post(
        _redeem_path(ids.tenancy_a),
        headers=_token(unknown_person_id),
        json={"activationCode": raw},
    )
    _assert_public_refusal(response)
    _assert_internal_outcome(caplog, "ACTIVATION_PERSON_UNKNOWN", raw)
    assert _state(owner, ids.renter_a, code_id) == before
    attempts = _attempt_rows(owner, raw, account_id=ids.account_a)
    assert [(row[1], row[2], row[3], row[4]) for row in attempts] == [
        (code_id, ids.tenancy_a, unknown_person_id, "ACTIVATION_PERSON_UNKNOWN")
    ]


@pytest.mark.parametrize("case", ["malformed", "nonexistent", "foreign", "same-account"])
def test_m10_act_f07_unknown_code_has_no_format_or_existence_oracle(
    setup: tuple[TestClient, Engine, _Ids],
    caplog: pytest.LogCaptureFixture,
    case: str,
) -> None:
    client, owner, ids = setup
    if case == "malformed":
        raw = "malformed-activation-code"
        account_id = None
    elif case == "nonexistent":
        raw = _raw_code(new_id())
        account_id = None
    elif case == "foreign":
        raw = _raw_code(ids.account_b)
        account_id = ids.account_b
    else:
        raw = _raw_code(ids.account_a)
        account_id = ids.account_a
    with owner.connect() as connection:
        before = int(connection.scalar(text("SELECT count(*) FROM renter_activation_redemption")))
    caplog.set_level(logging.INFO)
    response = client.post(
        _redeem_path(ids.tenancy_a),
        headers=_token(ids.caller_2),
        json={"activationCode": raw},
    )
    _assert_public_refusal(response)
    _assert_internal_outcome(caplog, "ACTIVATION_CODE_UNKNOWN", raw)
    with owner.connect() as connection:
        after = int(connection.scalar(text("SELECT count(*) FROM renter_activation_redemption")))
    assert after == before
    if account_id is None:
        with owner.connect() as connection:
            count = int(
                connection.scalar(
                    text(
                        "SELECT count(*) FROM renter_activation_attempt WHERE code_digest = :digest"
                    ),
                    {"digest": sha256(raw.encode()).hexdigest()},
                )
            )
        assert count == 0
    else:
        attempts = _attempt_rows(owner, raw, account_id=account_id)
        assert [(row[1], row[2], row[3], row[4]) for row in attempts] == [
            (None, ids.tenancy_a, ids.caller_2, "ACTIVATION_CODE_UNKNOWN")
        ]


@pytest.mark.parametrize(
    ("body", "secret_marker"),
    [
        ({}, None),
        ({"activationCode": None}, None),
        ({"activationCode": 918273645546372819}, "918273645546372819"),
        ({"activationCode": ["shape-secret-list-583102"]}, "shape-secret-list-583102"),
        (
            {"activationCode": {"raw": "shape-secret-object-947201"}},
            "shape-secret-object-947201",
        ),
    ],
    ids=["missing", "null", "numeric", "list", "object"],
)
def test_invalid_activation_code_shapes_use_the_uniform_timed_refusal_path(
    setup: tuple[TestClient, Engine, _Ids],
    caplog: pytest.LogCaptureFixture,
    body: dict[str, object],
    secret_marker: str | None,
) -> None:
    client, _owner, ids = setup
    caplog.set_level(logging.INFO)
    started = time.monotonic()
    response = client.post(
        _redeem_path(ids.tenancy_a),
        headers=_token(ids.caller_2),
        json=body,
    )
    elapsed = time.monotonic() - started
    _assert_public_refusal(response)
    assert elapsed >= 0.018
    assert "ACTIVATION_CODE_UNKNOWN" in caplog.text
    if secret_marker is not None:
        assert secret_marker not in caplog.text


def test_concurrent_redemption_has_one_winner_and_one_spend(
    setup: tuple[TestClient, Engine, _Ids],
) -> None:
    _, owner, ids = setup
    raw = _raw_code(ids.account_a)
    # A new party avoids depending on earlier refusal fixtures.
    renter_id = new_id()
    tenancy_id = new_id()
    with Session(owner) as session, session.begin():
        session.add(Renter(id=renter_id, account_id=ids.account_a, legal_name="Parallel Mieter"))
        session.add(
            Tenancy(
                id=tenancy_id,
                account_id=ids.account_a,
                unit_id=ids.unit_a,
                valid_from=date(2027, 1, 1),
                valid_to=None,
                base_rent_cents=80_000,
            )
        )
    with Session(owner) as session, session.begin():
        session.add(
            TenancyParty(account_id=ids.account_a, tenancy_id=tenancy_id, renter_id=renter_id)
        )
    code_id = _insert_code(owner, ids, raw, tenancy_id=tenancy_id, renter_id=renter_id)

    def redeem(person_id: str) -> tuple[int, dict[str, object]]:
        with TestClient(create_app()) as client:
            response = client.post(
                _redeem_path(tenancy_id),
                headers=_token(person_id),
                json={"activationCode": raw},
            )
            return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(redeem, [ids.caller_1, ids.caller_2]))
    assert sorted(status for status, _ in results) == [200, 400]
    linked_person, spend_count = _state(owner, renter_id, code_id)
    assert linked_person in {ids.caller_1, ids.caller_2}
    assert spend_count == 1
