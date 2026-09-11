"""M10-R2 RED API contract for renter contexts and the own-tenancy overview."""

import os
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from pathlib import Path

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
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

_DB_PACKAGE_DIR = Path(__file__).resolve().parents[3] / "packages" / "db"


@dataclass(frozen=True)
class _Ids:
    account_a: str
    account_b: str
    dual_person: str
    unlinked_person: str
    owner_b: str
    owner_membership_a: str
    owner_membership_b: str
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


def _link_renter(
    owner: Engine,
    *,
    account_id: str,
    membership_id: str,
    tenancy_id: str,
    renter_id: str,
    person_id: str,
) -> None:
    code_id = new_id()
    raw = f"{account_id}.m10-r2-{new_id()}"
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
                "account": account_id,
                "renter": renter_id,
                "tenancy": tenancy_id,
                "digest": sha256(raw.encode()).hexdigest(),
                "expires": now + timedelta(hours=1),
                "membership": membership_id,
                "now": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO renter_activation_redemption "
                "(id, account_id, activation_code_id, renter_id, tenancy_id, person_id, "
                "redeemed_at) VALUES "
                "(:id, :account, :code, :renter, :tenancy, :person, :now)"
            ),
            {
                "id": new_id(),
                "account": account_id,
                "code": code_id,
                "renter": renter_id,
                "tenancy": tenancy_id,
                "person": person_id,
                "now": now,
            },
        )
        connection.execute(
            text("UPDATE renter SET person_id = :person WHERE id = :renter"),
            {"person": person_id, "renter": renter_id},
        )


@pytest.fixture(scope="module")
def setup() -> Iterator[tuple[TestClient, _Ids]]:
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

    ids = _Ids(*(new_id() for _ in range(17)))
    with Session(owner) as session, session.begin():
        session.add_all(
            [
                Account(id=ids.account_a, name="M10-R2 Konto A"),
                Account(id=ids.account_b, name="M10-R2 Konto B"),
                Person(id=ids.dual_person, email=f"{ids.dual_person}@example.test"),
                Person(id=ids.unlinked_person, email=f"{ids.unlinked_person}@example.test"),
                Person(id=ids.owner_b, email=f"{ids.owner_b}@example.test"),
                Membership(
                    id=ids.owner_membership_a,
                    person_id=ids.dual_person,
                    account_id=ids.account_a,
                    role=Role.OWNER,
                    accepted_at=datetime(2026, 9, 11, tzinfo=UTC),
                ),
                Membership(
                    id=ids.owner_membership_b,
                    person_id=ids.owner_b,
                    account_id=ids.account_b,
                    role=Role.OWNER,
                    accepted_at=datetime(2026, 9, 11, tzinfo=UTC),
                ),
                Building(
                    id=ids.building_a,
                    account_id=ids.account_a,
                    name="Rosenhof",
                    street="Rosenweg 4",
                    postal_code="50667",
                    city="Köln",
                ),
                Building(
                    id=ids.building_b,
                    account_id=ids.account_b,
                    name="Fremdhaus",
                    street="Fremdweg 9",
                    postal_code="20095",
                    city="Hamburg",
                ),
                Renter(id=ids.renter_a, account_id=ids.account_a, legal_name="Doppelrolle"),
                Renter(
                    id=ids.renter_a_other,
                    account_id=ids.account_a,
                    legal_name="Andere Mietpartei",
                ),
                Renter(id=ids.renter_b, account_id=ids.account_b, legal_name="Fremde Mietpartei"),
            ]
        )
    with Session(owner) as session, session.begin():
        session.add_all(
            [
                Unit(
                    id=ids.unit_a,
                    account_id=ids.account_a,
                    building_id=ids.building_a,
                    label="Wohnung 3 links",
                    area_sqm_x100=6_200,
                ),
                Unit(
                    id=ids.unit_b,
                    account_id=ids.account_b,
                    building_id=ids.building_b,
                    label="Wohnung B",
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
                    valid_from=date(2024, 3, 1),
                    valid_to=None,
                    base_rent_cents=91_000,
                ),
                Tenancy(
                    id=ids.tenancy_a_other,
                    account_id=ids.account_a,
                    unit_id=ids.unit_a,
                    valid_from=date(2022, 1, 1),
                    valid_to=date(2024, 2, 29),
                    base_rent_cents=71_000,
                ),
                Tenancy(
                    id=ids.tenancy_b,
                    account_id=ids.account_b,
                    unit_id=ids.unit_b,
                    valid_from=date(2025, 1, 1),
                    valid_to=None,
                    base_rent_cents=81_000,
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
    _link_renter(
        owner,
        account_id=ids.account_a,
        membership_id=ids.owner_membership_a,
        tenancy_id=ids.tenancy_a,
        renter_id=ids.renter_a,
        person_id=ids.dual_person,
    )

    client = TestClient(create_app())
    try:
        yield client, ids
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


def test_m10_ctx_f01_dual_role_me_keeps_accounts_and_adds_minimal_renter_context(
    setup: tuple[TestClient, _Ids],
) -> None:
    client, ids = setup
    response = client.get("/me", headers=_token(ids.dual_person))
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"personId", "email", "accounts", "renterContexts"}
    assert body["accounts"] == [
        {
            "id": ids.account_a,
            "name": "M10-R2 Konto A",
            "role": "OWNER",
            "shape": "SOLO",
        }
    ]
    assert body["renterContexts"] == [{"tenancyId": ids.tenancy_a}]


def test_m10_ctx_f02_own_overview_is_the_exact_minimal_projection(
    setup: tuple[TestClient, _Ids],
) -> None:
    client, ids = setup
    response = client.get(f"/renter/{ids.tenancy_a}", headers=_token(ids.dual_person))
    assert response.status_code == 200
    assert response.json() == {
        "tenancyId": ids.tenancy_a,
        "validFrom": "2024-03-01",
        "validTo": None,
        "unitLabel": "Wohnung 3 links",
        "buildingName": "Rosenhof",
        "street": "Rosenweg 4",
        "postalCode": "50667",
        "city": "Köln",
    }


def test_m10_ctx_f03_same_account_other_tenancy_is_undiscoverable(
    setup: tuple[TestClient, _Ids],
) -> None:
    client, ids = setup
    response = client.get(f"/renter/{ids.tenancy_a_other}", headers=_token(ids.dual_person))
    assert response.status_code == 404


@pytest.mark.parametrize("target", ["cross_account", "unlinked"])
def test_m10_ctx_f04_cross_account_and_unlinked_callers_are_undiscoverable(
    setup: tuple[TestClient, _Ids], target: str
) -> None:
    client, ids = setup
    if target == "cross_account":
        tenancy_id = ids.tenancy_b
        person_id = ids.dual_person
    else:
        tenancy_id = ids.tenancy_a
        person_id = ids.unlinked_person
    response = client.get(f"/renter/{tenancy_id}", headers=_token(person_id))
    assert response.status_code == 404


def test_m10_ctx_f08_owner_routes_keep_account_session_behavior(
    setup: tuple[TestClient, _Ids],
) -> None:
    client, ids = setup
    response = client.get(f"/a/{ids.account_a}/buildings", headers=_token(ids.dual_person))
    assert response.status_code == 200
    assert ids.building_a in {row["id"] for row in response.json()["buildings"]}
