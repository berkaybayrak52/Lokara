"""Objekte/Einheiten/Mietverhältnisse CRUD against a live Postgres.

The whole chain runs through the URL-scoped API: create Building → Unit →
Tenancy, read back list/detail/timeline, overlap rejected with 422, and the
usual two isolation proofs (path re-authorization + RLS backstop).
"""

import os
import time
from collections.abc import Iterator
from pathlib import Path

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from lokara_api import create_app
from lokara_api.settings import ApiSettings
from lokara_db import Account, DbSettings, Membership, Person, Role, create_db_engine
from lokara_db.seed import DEMO_ACCOUNT_ID, DEMO_PERSON_ID, seed_demo
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "db"
TEST_JWT_ISSUER = "https://lokara.test/auth/v1"

ISO_ACCOUNT_ID = "acc_iso_crud"
ISO_PERSON_ID = "per_iso_crud"


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    settings = DbSettings()
    try:
        owner = create_db_engine(settings.direct_url)
        with owner.connect() as conn:
            conn.execute(text((_DB_PACKAGE_DIR / "scripts" / "init-app-role.sql").read_text()))
            conn.commit()
    except OperationalError as exc:
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")
    command.upgrade(Config(str(_DB_PACKAGE_DIR / "alembic.ini")), "head")
    with Session(owner) as session, session.begin():
        seed_demo(session)  # provides the demo person's OWNER membership
        session.merge(Person(id=ISO_PERSON_ID, email="iso-crud@lokara.example"))
        session.merge(Account(id=ISO_ACCOUNT_ID, name="Isolationskonto CRUD"))
        session.merge(
            Membership(
                id="mem_iso_crud",
                person_id=ISO_PERSON_ID,
                account_id=ISO_ACCOUNT_ID,
                role=Role.OWNER,
            )
        )
    owner.dispose()
    yield TestClient(create_app())


def _token(person_id: str) -> dict[str, str]:
    now = int(time.time())
    encoded = jwt.encode(
        {
            "sub": person_id,
            "iss": str(getattr(ApiSettings(), "supabase_jwt_issuer", TEST_JWT_ISSUER)),
            "aud": "authenticated",
            "role": "authenticated",
            "iat": now,
            "exp": now + 3600,
        },
        ApiSettings().supabase_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {encoded}"}


DEMO = _token(DEMO_PERSON_ID)
BASE = f"/a/{DEMO_ACCOUNT_ID}"


class TestCreateChain:
    tenancy_id: str
    """One flowing scenario: Building → Unit → Tenancy → timeline read-back."""

    building_id: str
    unit_id: str

    def test_create_building(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE}/buildings",
            headers=DEMO,
            json={
                "name": "Testgasse 5",
                "street": "Testgasse 5",
                "postalCode": "60313",
                "city": "Frankfurt am Main",
                "houseNumber": "1",
                "buildingType": "WOHNHAUS",
                "isResidential": True,
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Testgasse 5"
        assert body["unitCount"] == 0
        TestCreateChain.building_id = body["id"]

        listing = client.get(f"{BASE}/buildings", headers=DEMO).json()
        names = [b["name"] for b in listing["buildings"]]
        assert "Musterstraße 12" in names and "Testgasse 5" in names
        # The seeded building stays first (created_at order) — the demo
        # statement and dashboard summary remain pinned to it.
        assert names[0] == "Musterstraße 12"

    def test_invalid_postal_code_is_422(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE}/buildings",
            headers=DEMO,
            json={
                "name": "X",
                "street": "X 1",
                "houseNumber": "1",
                "postalCode": "123",
                "city": "F",
                "buildingType": "WOHNHAUS",
                "isResidential": True,
            },
        )
        assert response.status_code == 422

    def test_create_unit(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE}/buildings/{TestCreateChain.building_id}/units",
            headers=DEMO,
            json={"label": "Wohnung 1 (EG)", "areaSqmX100": 6450},  # 64,50 m²
        )
        assert response.status_code == 201
        body = response.json()
        assert body["areaSqm"] == 64.5
        assert body["occupiedToday"] is False
        TestCreateChain.unit_id = body["id"]

        detail = client.get(f"{BASE}/buildings/{TestCreateChain.building_id}", headers=DEMO).json()
        assert [u["label"] for u in detail["units"]] == ["Wohnung 1 (EG)"]

    def test_create_tenancy_and_read_timeline(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE}/units/{TestCreateChain.unit_id}/tenancies",
            headers=DEMO,
            json={
                "renterName": "Erika Musterfrau",
                "validFrom": "2024-03-01",
                "validTo": None,
                "baseRentCents": 89000,
                "initialAdvancePaymentCents": 21000,
                "advanceDeclarationRef": "Mietvertrag 2024-02-15",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["renterNames"] == ["Erika Musterfrau"]
        assert body["baseRentEur"].startswith("890,00")
        assert body["activeToday"] is True
        assert "advancePaymentCents" not in body
        assert len(body["advancePaymentSchedule"]) == 1
        assert body["advancePaymentSchedule"][0]["amountCents"] == 21000
        assert body["advancePaymentSchedule"][0]["validFrom"] == "2024-03-01"
        assert body["advancePaymentSchedule"][0]["validTo"] is None
        TestCreateChain.tenancy_id = body["id"]

        successor = client.post(
            f"{BASE}/buildings/{TestCreateChain.building_id}/tenancies/"
            f"{TestCreateChain.tenancy_id}/advance-schedule",
            headers=DEMO,
            json={
                "amountCents": 24000,
                "validFrom": "2024-07-01",
                "declarationRef": "§ 560-Anpassung 2024-06-15",
            },
        )
        assert successor.status_code == 201, successor.text
        successor_id = successor.json()["id"]
        schedule_read = client.get(f"{BASE}/units/{TestCreateChain.unit_id}", headers=DEMO)
        assert schedule_read.status_code == 200, schedule_read.text
        periods = schedule_read.json()["tenancies"][0]["advancePaymentSchedule"]
        assert [(row["amountCents"], row["validFrom"], row["validTo"]) for row in periods] == [
            (21000, "2024-03-01", "2024-07-01"),
            (24000, "2024-07-01", None),
        ]
        assert periods[0]["predecessorId"] is None
        assert periods[1]["id"] == successor_id
        assert periods[1]["predecessorId"] == periods[0]["id"]

        detail = client.get(f"{BASE}/units/{TestCreateChain.unit_id}", headers=DEMO).json()
        assert detail["buildingName"] == "Testgasse 5"
        assert [t["renterNames"] for t in detail["tenancies"]] == [["Erika Musterfrau"]]

        building = client.get(
            f"{BASE}/buildings/{TestCreateChain.building_id}", headers=DEMO
        ).json()
        assert building["units"][0]["occupiedToday"] is True

    def test_overlapping_tenancy_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE}/units/{TestCreateChain.unit_id}/tenancies",
            headers=DEMO,
            json={
                "renterName": "Max Doppelt",
                "validFrom": "2025-01-01",  # inside the open-ended tenancy
                "validTo": "2025-12-31",
                "baseRentCents": 50000,
                "initialAdvancePaymentCents": 10000,
                "advanceDeclarationRef": "Mietvertrag",
            },
        )
        assert response.status_code == 422
        assert "overlap" in response.json()["detail"].lower()

    def test_backwards_period_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE}/units/{TestCreateChain.unit_id}/tenancies",
            headers=DEMO,
            json={
                "renterName": "Zeitreisende",
                "validFrom": "2030-01-01",
                "validTo": "2029-01-01",
                "baseRentCents": 1,
                "initialAdvancePaymentCents": 0,
                "advanceDeclarationRef": "Mietvertrag",
            },
        )
        assert response.status_code == 422


class TestIsolation:
    def test_foreign_member_cannot_write_into_the_demo_account(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE}/buildings",
            headers=_token(ISO_PERSON_ID),
            json={
                "name": "Einbruch 1",
                "street": "E 1",
                "houseNumber": "1",
                "postalCode": "60000",
                "city": "F",
                "buildingType": "WOHNHAUS",
                "isResidential": True,
            },
        )
        assert response.status_code == 403

    def test_own_list_shows_no_foreign_buildings(self, client: TestClient) -> None:
        listing = client.get(f"/a/{ISO_ACCOUNT_ID}/buildings", headers=_token(ISO_PERSON_ID))
        assert listing.status_code == 200
        assert listing.json()["buildings"] == []

    def test_foreign_unit_detail_is_404_not_leak(self, client: TestClient) -> None:
        """RLS backstop: the demo unit is invisible from the iso account's
        context, even with a guessed id."""
        response = client.get(
            f"/a/{ISO_ACCOUNT_ID}/units/unit_demo_a",
            headers=_token(ISO_PERSON_ID),
        )
        assert response.status_code == 404
