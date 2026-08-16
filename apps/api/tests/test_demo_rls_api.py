"""End-to-end isolation through the API against a live Postgres: JWT →
membership check (403) → RLS-scoped session (cross-tenant reads empty).

Same skip contract as the packages/db suite: skips without a reachable DB,
but LOKARA_REQUIRE_DB (set in CI) forbids the skip. Self-sufficient: applies
init-app-role.sql + alembic upgrade head + the demo seed itself.
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

NBSP = " "
_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "db"
TEST_JWT_ISSUER = "https://lokara.test/auth/v1"

ISO_ACCOUNT_ID = "acc_iso_check"
ISO_PERSON_ID = "per_iso_owner"


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    """TestClient with the demo scenario (plus an empty second account) seeded."""
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
        # "Zero domain data" has to be true on every run, not just the first:
        # TestDemoReset creates a building here to prove the reset cannot reach
        # it, and that row would otherwise survive into the next run and break
        # the isolation test's 404.
        for table in ("unit", "building"):
            session.execute(
                text(f"DELETE FROM {table} WHERE account_id = :a"), {"a": ISO_ACCOUNT_ID}
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


class TestDemoSummary:
    def test_owner_sees_the_seeded_demo(self, client: TestClient) -> None:
        response = client.get(f"/a/{DEMO_ACCOUNT_ID}/summary", headers=_token(DEMO_PERSON_ID))
        assert response.status_code == 200
        body = response.json()
        assert body["accountName"] == "Demo Konto"
        assert body["buildingName"] == "Musterstraße 12"
        assert body["buildingAddress"] == "Musterstraße 12, 60311 Frankfurt am Main"
        assert body["unitCount"] == 3
        bernd = next(t for t in body["tenancies"] if t["renterNames"] == ["Bernd Muster"])
        assert bernd["validTo"] == "2025-07-01"  # exclusive — moves out 30 Jun
        assert bernd["baseRentEur"] == f"680,00{NBSP}€"


class TestApiIsolation:
    def test_no_membership_in_path_account_is_403(self, client: TestClient) -> None:
        """The URL account is independently authorized before domain data is touched."""
        response = client.get(f"/a/{DEMO_ACCOUNT_ID}/summary", headers=_token("per_stranger"))
        assert response.status_code == 403

    def test_unknown_path_account_is_403(self, client: TestClient) -> None:
        response = client.get("/a/acc_ghost/summary", headers=_token("per_stranger"))
        assert response.status_code == 403

    def test_other_accounts_context_cannot_see_demo_rows(self, client: TestClient) -> None:
        """The RLS backstop through the whole stack: a legitimate member of a
        different account gets an empty view (404 'no data'), never the demo
        account's building."""
        response = client.get(f"/a/{ISO_ACCOUNT_ID}/summary", headers=_token(ISO_PERSON_ID))
        assert response.status_code == 404


class TestDemoReset:
    """`POST /demo/reset` — the pitch's undo button. It DELETES, so the two
    things worth proving are that it removes exactly the stray rows and that
    it cannot touch another account's data."""

    def test_reset_removes_stray_rows_and_restores_the_scenario(self, client: TestClient) -> None:
        headers = _token(DEMO_PERSON_ID)
        base = f"/a/{DEMO_ACCOUNT_ID}"

        # A rehearsal leftover: exactly what pollutes the Objekte list.
        created = client.post(
            f"{base}/buildings",
            headers=headers,
            json={
                "name": "Testgasse 5",
                "street": "Testgasse 5",
                "postalCode": "60313",
                "city": "Frankfurt am Main",
            },
        )
        assert created.status_code == 201
        listed = client.get(f"{base}/buildings", headers=headers).json()["buildings"]
        assert "Testgasse 5" in [b["name"] for b in listed]

        assert client.post("/demo/reset", headers=headers).status_code == 200

        buildings = client.get(f"{base}/buildings", headers=headers).json()["buildings"]
        assert [b["name"] for b in buildings] == ["Musterstraße 12"]
        # Re-seeded, not merely emptied: the scenario is back in full.
        assert buildings[0]["unitCount"] == 3
        summary = client.get(f"/a/{DEMO_ACCOUNT_ID}/summary", headers=headers).json()
        assert len(summary["tenancies"]) == 3

    def test_reset_removes_a_stray_tenancy_graph_but_retains_page02_evidence(
        self, client: TestClient
    ) -> None:
        """Immutable demo costs stay; a separate rehearsal tenancy does not."""
        headers = _token(DEMO_PERSON_ID, DEMO_ACCOUNT_ID)
        base = f"/a/{DEMO_ACCOUNT_ID}"
        before = client.get(f"{base}/buildings/bld_demo_muster12/costs", headers=headers)
        assert before.status_code == 200
        evidence_ids = [cost["id"] for cost in before.json()["costs"]]
        assert "cost_demo_garbage" in evidence_ids

        building = client.post(
            f"{base}/buildings",
            headers=headers,
            json={
                "name": "Resetkette 9",
                "street": "Resetweg 9",
                "postalCode": "60313",
                "city": "Frankfurt am Main",
            },
        )
        assert building.status_code == 201
        unit = client.post(
            f"{base}/buildings/{building.json()['id']}/units",
            headers=headers,
            json={"label": "Wohnung Reset", "areaSqmX100": 5000},
        )
        assert unit.status_code == 201
        tenancy = client.post(
            f"{base}/units/{unit.json()['id']}/tenancies",
            headers=headers,
            json={
                "renterName": "Reset Mieter",
                "validFrom": "2025-01-01",
                "validTo": None,
                "baseRentCents": 70000,
                "advancePaymentCents": 12000,
            },
        )
        assert tenancy.status_code == 201
        agreement = client.post(
            f"{base}/tenancies/{tenancy.json()['id']}/operating-cost-agreements",
            headers=headers,
            json={
                "allocationAgreed": True,
                "mehrbelastungClause": False,
                "namedOtherCosts": [],
                "contractualKeys": {},
                "validFrom": "2025-01-01",
                "validTo": None,
            },
        )
        assert agreement.status_code == 201
        cost = client.post(
            f"{base}/buildings/{building.json()['id']}/costs",
            headers=headers,
            json={
                "label": "Resetkosten",
                "catalogueId": "gebaeudereinigung",
                "amountCents": 10000,
                "periodFrom": "2025-01-01",
                "periodTo": "2026-01-01",
            },
        )
        assert cost.status_code == 201

        assert client.post("/demo/reset", headers=headers).status_code == 200

        buildings = client.get(f"{base}/buildings", headers=headers).json()["buildings"]
        assert [row["name"] for row in buildings] == ["Musterstraße 12"]
        after = client.get(f"{base}/buildings/bld_demo_muster12/costs", headers=headers)
        assert after.status_code == 200
        assert [cost["id"] for cost in after.json()["costs"]] == evidence_ids
        engine = create_db_engine(DbSettings().direct_url)
        try:
            with Session(engine) as session:
                retired = session.execute(
                    text("SELECT voided_at FROM cost_entry WHERE id = :id"),
                    {"id": cost.json()["id"]},
                ).scalar_one()
                assert retired is not None
        finally:
            engine.dispose()

    def test_reset_leaves_the_callers_own_access_intact(self, client: TestClient) -> None:
        """It must not wipe the Account/Membership it runs under — doing so
        would 403 the very session that pressed the button."""
        headers = _token(DEMO_PERSON_ID)
        assert client.post("/demo/reset", headers=headers).status_code == 200
        me = client.get("/me", headers=headers).json()
        assert DEMO_ACCOUNT_ID in [a["id"] for a in me["accounts"]]

    def test_reset_cannot_delete_another_accounts_rows(self, client: TestClient) -> None:
        """The guarantee that matters for a DELETE endpoint.

        Like /demo/load, this one is not scoped to the caller — it always acts
        on the fixed demo account, so any authenticated caller may trigger it
        (both are dev-only and flag-gated). What must hold is that it can never
        reach past that account: the DELETEs run under the demo account's RLS
        context, so a caller from elsewhere cannot use it to wipe their own —
        or anyone else's — data.
        """
        iso = _token(ISO_PERSON_ID)
        created = client.post(
            f"/a/{ISO_ACCOUNT_ID}/buildings",
            headers=iso,
            json={
                "name": "Fremdes Haus",
                "street": "Fremdweg 1",
                "postalCode": "10115",
                "city": "Berlin",
            },
        )
        assert created.status_code == 201

        assert client.post("/demo/reset", headers=iso).status_code == 200

        survivors = client.get(f"/a/{ISO_ACCOUNT_ID}/buildings", headers=iso).json()
        assert [b["name"] for b in survivors["buildings"]] == ["Fremdes Haus"]
        # …and the demo account is the one that got re-seeded.
        demo = client.get(f"/a/{DEMO_ACCOUNT_ID}/buildings", headers=_token(DEMO_PERSON_ID)).json()
        assert [b["name"] for b in demo["buildings"]] == ["Musterstraße 12"]
