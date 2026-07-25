"""M3 slice gates against a live Postgres: /me, one-click demo load, and the
URL-scoped statement endpoints — golden numbers over HTTP, path re-authorization
(403 without a membership in the URL's account), and the PDF.

Same skip contract as the other live suites: skips without a reachable DB;
LOKARA_REQUIRE_DB (CI) forbids the skip. The PDF test additionally needs
Playwright Chromium (installed in CI, LOKARA_REQUIRE_PDF).
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
from lokara_api.settings import ApiSettings
from lokara_db import Account, DbSettings, Membership, Person, Role, create_db_engine
from lokara_db.seed import DEMO_ACCOUNT_ID, DEMO_PERSON_ID, seed_demo
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

NBSP = " "  # format_eur puts a non-breaking space before the € sign
_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "db"

ISO_ACCOUNT_ID = "acc_iso_m3"
ISO_PERSON_ID = "per_iso_m3"


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
        seed_demo(session)
        session.merge(Person(id=ISO_PERSON_ID, email="iso-m3@lokara.example"))
        session.merge(Account(id=ISO_ACCOUNT_ID, name="Isolationskonto M3"))
        session.merge(
            Membership(
                id="mem_iso_m3",
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


DEMO = _token(DEMO_PERSON_ID, DEMO_ACCOUNT_ID)


class TestMe:
    def test_demo_owner_sees_their_relationship(self, client: TestClient) -> None:
        response = client.get("/me", headers=_token(DEMO_PERSON_ID, DEMO_ACCOUNT_ID))
        assert response.status_code == 200
        body = response.json()
        assert body["personId"] == DEMO_PERSON_ID
        assert body["accounts"] == [
            {"id": DEMO_ACCOUNT_ID, "name": "Demo Konto", "role": "OWNER", "shape": "SOLO"}
        ]

    def test_unknown_person_gets_an_empty_list_not_an_error(self, client: TestClient) -> None:
        """No membership yet ⇒ the dashboard offers "Demo-Szenario laden"."""
        response = client.get("/me", headers=_token("per_nobody", DEMO_ACCOUNT_ID))
        assert response.status_code == 200
        assert response.json()["accounts"] == []


class TestDemoLoad:
    def test_disabled_flag_yields_403(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """DEMO_SEED_ENABLED is off by default — the endpoint must refuse
        (same pattern as AUTH_DEV_TOKEN; settings are read per request)."""
        monkeypatch.setenv("DEMO_SEED_ENABLED", "false")
        response = client.post("/demo/load", headers=DEMO)
        assert response.status_code == 403
        assert "disabled" in response.json()["detail"]

    def test_one_click_load_is_idempotent_and_unlocks_the_portal(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DEMO_SEED_ENABLED", "true")
        response = client.post("/demo/load", headers=DEMO)
        assert response.status_code == 200
        assert response.json() == {"ok": True, "accountId": DEMO_ACCOUNT_ID}

        # Loading twice must not fail (merge semantics).
        assert client.post("/demo/load", headers=DEMO).status_code == 200

        summary = client.get(f"/a/{DEMO_ACCOUNT_ID}/summary", headers=DEMO)
        assert summary.status_code == 200
        assert summary.json()["buildingName"] == "Musterstraße 12"


class TestDemoStatement:
    def test_nk_shares_are_the_canonical_1200(self, client: TestClient) -> None:
        response = client.get(f"/a/{DEMO_ACCOUNT_ID}/statements/demo", headers=DEMO)
        assert response.status_code == 200
        body = response.json()

        [garbage] = body["nkCosts"]
        assert garbage["label"] == "Müllabfuhr"
        assert garbage["keyLabel"] == "Wohnfläche (m²·Tage)"
        assert [(line["amountCents"], line["isLandlord"]) for line in garbage["lines"]] == [
            (60000, False),
            (17852, False),
            (18148, True),  # the vacancy share lands on the Vermieter
            (24000, False),
        ]
        assert [line["weightDisplay"] for line in garbage["lines"]] == [
            "18.250",
            "5.430",
            "5.520",
            "7.300",
        ]
        assert body["nkTotalCents"] == 120000
        assert body["nkTotalCents"] == body["nkInputTotalCents"]  # reconciles
        assert body["nkTotalEur"] == f"1.200,00{NBSP}€"

    def test_heating_shows_the_degree_day_split_and_co2(self, client: TestClient) -> None:
        response = client.get(f"/a/{DEMO_ACCOUNT_ID}/statements/demo", headers=DEMO)
        body = response.json()

        lines = body["heatingLines"]
        assert len(lines) == 4  # A, B-renter, B-landlord (vacancy), C
        bernd = next(line for line in lines if "Bernd Muster" in line["partyLabel"])
        vacancy = next(line for line in lines if line["isLandlord"])
        # 585/415 ‰ degree-day apportionment of unit B's annual consumption.
        assert bernd["heatingConsumptionEur"] == f"786,24{NBSP}€"
        assert vacancy["heatingConsumptionEur"] == f"557,76{NBSP}€"
        assert "Auszug 30.06.2025" in bernd["partyLabel"]

        assert body["heatingTotalCents"] == 1_030_000
        assert body["heatingTotalCents"] == body["heatingInputTotalCents"]

        co2 = body["co2"]
        assert co2["landlordSharePercent"] == 20
        assert co2["landlordAmountEur"] == f"60,00{NBSP}€"
        assert co2["rechtsstand"] == "Rechtsstand 01/2023"
        assert "Rechtsstand 01/2023" in body["rechtsstaende"]
        assert "keine Rechts- oder Steuerberatung" in body["disclaimer"]

    def test_pdf_downloads(self, client: TestClient) -> None:
        response = client.get(f"/a/{DEMO_ACCOUNT_ID}/statements/demo/pdf", headers=DEMO)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers["content-disposition"]
        assert response.content.startswith(b"%PDF-")


class TestPathReauthorization:
    """CLAUDE.md rule 3: the endpoint independently verifies the caller holds
    the relationship named in the URL — the token's own account is irrelevant."""

    def test_member_of_another_account_cannot_enter_the_demo_portal(
        self, client: TestClient
    ) -> None:
        headers = _token(ISO_PERSON_ID, ISO_ACCOUNT_ID)  # a perfectly valid session
        for path in (
            f"/a/{DEMO_ACCOUNT_ID}/summary",
            f"/a/{DEMO_ACCOUNT_ID}/statements/demo",
            f"/a/{DEMO_ACCOUNT_ID}/statements/demo/pdf",
        ):
            assert client.get(path, headers=headers).status_code == 403, path

    def test_stranger_is_rejected(self, client: TestClient) -> None:
        response = client.get(
            f"/a/{DEMO_ACCOUNT_ID}/statements/demo",
            headers=_token("per_stranger", DEMO_ACCOUNT_ID),
        )
        assert response.status_code == 403

    def test_own_portal_shows_no_foreign_rows(self, client: TestClient) -> None:
        """The RLS backstop: the iso account's own portal is empty (404 no
        data), never a view of the demo account's building."""
        response = client.get(
            f"/a/{ISO_ACCOUNT_ID}/statements/demo",
            headers=_token(ISO_PERSON_ID, ISO_ACCOUNT_ID),
        )
        assert response.status_code == 404
