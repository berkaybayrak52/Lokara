"""End-to-end isolation through the API against a live Postgres: JWT →
membership check (403) → RLS-scoped session (cross-tenant reads empty).

Same skip contract as the packages/db suite: skips without a reachable DB,
but LOKARA_REQUIRE_DB (set in CI) forbids the skip. Self-sufficient: applies
init-app-role.sql + alembic upgrade head + the demo seed itself.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from lokara_api import create_app
from lokara_api.auth import create_dev_token
from lokara_api.settings import ApiSettings
from lokara_db import Account, DbSettings, Membership, Person, Role, create_db_engine
from lokara_db.seed import DEMO_ACCOUNT_ID, seed_demo
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

NBSP = " "
_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "db"

ISO_ACCOUNT_ID = "acc_iso_check"
ISO_PERSON_ID = "per_iso_owner"


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    """TestClient with the demo scenario (plus an empty second account) seeded."""
    settings = DbSettings()
    try:
        owner = create_db_engine(settings.direct_url)
        with owner.connect() as conn:
            conn.execute(
                text((_DB_PACKAGE_DIR / "scripts" / "init-app-role.sql").read_text())
            )
            conn.commit()
    except OperationalError as exc:
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")
    command.upgrade(Config(str(_DB_PACKAGE_DIR / "alembic.ini")), "head")
    with Session(owner) as session, session.begin():
        seed_demo(session)
        # Second account with a valid OWNER membership but zero domain data —
        # its context must see nothing of the demo account through the API.
        session.merge(Person(id=ISO_PERSON_ID, email="iso@lokara.example"))
        session.merge(Account(id=ISO_ACCOUNT_ID, name="Isolationskonto"))
        session.merge(
            Membership(
                id="mem_iso_owner",
                person_id=ISO_PERSON_ID,
                account_id=ISO_ACCOUNT_ID,
                role=Role.OWNER,
            )
        )
    owner.dispose()
    yield TestClient(create_app())


def _token(person_id: str, account_id: str) -> dict[str, str]:
    encoded = jwt.encode(
        {"sub": person_id, "account_id": account_id},
        ApiSettings().supabase_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {encoded}"}


class TestDemoSummary:
    def test_owner_sees_the_seeded_demo(self, client: TestClient) -> None:
        headers = {
            "Authorization": f"Bearer {create_dev_token(ApiSettings().supabase_jwt_secret)}"
        }
        response = client.get("/demo/summary", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["accountName"] == "Demo Konto"
        assert body["buildingName"] == "Musterstraße 12"
        assert body["buildingAddress"] == "Musterstraße 12, 60311 Frankfurt am Main"
        assert body["unitCount"] == 3
        bernd = next(
            t for t in body["tenancies"] if t["renterNames"] == ["Bernd Muster"]
        )
        assert bernd["validTo"] == "2025-07-01"  # exclusive — moves out 30 Jun
        assert bernd["baseRentEur"] == f"680,00{NBSP}€"


class TestApiIsolation:
    def test_no_membership_in_claimed_account_is_403(self, client: TestClient) -> None:
        """A valid JWT claiming the demo account, but the person holds no
        membership there — the app-logic check fires before any domain data."""
        response = client.get(
            "/demo/summary", headers=_token("per_stranger", DEMO_ACCOUNT_ID)
        )
        assert response.status_code == 403

    def test_unknown_account_context_is_403(self, client: TestClient) -> None:
        response = client.get("/demo/summary", headers=_token("per_stranger", "acc_ghost"))
        assert response.status_code == 403

    def test_other_accounts_context_cannot_see_demo_rows(self, client: TestClient) -> None:
        """The RLS backstop through the whole stack: a legitimate member of a
        different account gets an empty view (404 'no data'), never the demo
        account's building."""
        response = client.get(
            "/demo/summary", headers=_token(ISO_PERSON_ID, ISO_ACCOUNT_ID)
        )
        assert response.status_code == 404
