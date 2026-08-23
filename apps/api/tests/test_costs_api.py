"""Kosten erfassen + the key-switch guarantee (docs/06 Scenario 3).

THE test in this file: switching a cost's Umlageschlüssel re-runs the
calculation and **destroys no entered data** — the cost row is untouched, the
whole assignment history survives, and switching back reproduces the original
golden numbers exactly. That is the objego/immocloud pain point on screen.

Also: the seeded demo statement must keep producing the canonical €1,200 split
now that it reads real CostEntry rows instead of a fixture constant.
"""

import os
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from lokara_api import create_app
from lokara_api.settings import ApiSettings
from lokara_db import DbSettings, create_db_engine
from lokara_db.seed import DEMO_ACCOUNT_ID, DEMO_PERSON_ID, seed_demo
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

NBSP = " "  # format_eur puts a non-breaking space before the €
_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "db"
TEST_JWT_ISSUER = "https://lokara.test/auth/v1"

BASE = f"/a/{DEMO_ACCOUNT_ID}"
DEMO_BUILDING_ID = "bld_demo_muster12"

# The canonical fixture (docs/03), by unit label so the assertions read.
GOLDEN_AREA_SHARES = [60000, 17852, 24000, 18148]


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
        # Classifications are append-only. Test-created costs are voided below,
        # so no destructive cleanup is permitted here.
    owner.dispose()
    test_client = TestClient(create_app())
    # A prior interrupted local run may have append-only test rows.  Retire
    # them through the public void workflow; they remain evidence but cannot
    # contaminate this module's later previews.
    for cost in test_client.get(f"{BASE}/buildings/{DEMO_BUILDING_ID}/costs", headers=DEMO).json()[
        "costs"
    ]:
        if cost["id"] != "cost_demo_garbage":
            response = test_client.post(
                f"{BASE}/costs/{cost['id']}/void",
                headers=DEMO,
                json={"reason": "Testbereinigung"},
            )
            assert response.status_code == 200, response.text
    yield test_client


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


def _seeded_cost(client: TestClient) -> dict[str, Any]:
    costs = client.get(f"{BASE}/buildings/{DEMO_BUILDING_ID}/costs", headers=DEMO).json()["costs"]
    return next(c for c in costs if c["id"] == "cost_demo_garbage")


def _nk_shares(client: TestClient, cost_id: str) -> list[int]:
    body = client.get(f"{BASE}/statements/demo", headers=DEMO).json()
    cost = next(c for c in body["nkCosts"] if c["label"] == "Müllabfuhr")
    del cost_id  # matched by label — ids differ per seed run only for new costs
    return [line["amountCents"] for line in cost["lines"]]


class TestSeededCostFeedsTheStatement:
    def test_the_seeded_cost_is_a_real_row_with_an_area_key(self, client: TestClient) -> None:
        cost = _seeded_cost(client)
        assert cost["label"] == "Müllabfuhr"
        assert cost["amountCents"] == 120000
        assert cost["amountEur"] == f"1.200,00{NBSP}€"
        assert cost["key"] == "AREA"
        assert cost["keyLabel"] == "Wohnfläche (m²·Tage)"
        assert cost["periodFrom"] == "2025-01-01"
        assert cost["periodTo"] == "2026-01-01"

    def test_statement_still_reproduces_the_golden_numbers_from_real_rows(
        self, client: TestClient
    ) -> None:
        """The fixture constant is gone; the numbers must not move."""
        body = client.get(f"{BASE}/statements/demo", headers=DEMO).json()
        [garbage] = body["nkCosts"]
        assert [line["amountCents"] for line in garbage["lines"]] == GOLDEN_AREA_SHARES
        assert body["nkTotalCents"] == 120000 == body["nkInputTotalCents"]
        assert body["nkTotalEur"] == f"1.200,00{NBSP}€"


class TestKeySwitchLosesNoData:
    """docs/06 Scenario 3: change the key → statement re-computes → nothing lost."""

    def test_switch_to_units_recomputes_and_back_to_area_restores_goldens(
        self, client: TestClient
    ) -> None:
        before = _seeded_cost(client)
        assert before["key"] == "AREA"
        assignments_before = before["assignmentCount"]
        assert _nk_shares(client, "cost_demo_garbage") == GOLDEN_AREA_SHARES

        # ── switch to UNITS: same cost row, different weights ────────────────
        switched = client.post(
            f"{BASE}/costs/cost_demo_garbage/key", headers=DEMO, json={"key": "UNITS"}
        )
        assert switched.status_code == 200
        after = switched.json()
        assert after["key"] == "UNITS"
        # The entered data is byte-identical — only the key moved.
        for field in ("id", "label", "amountCents", "periodFrom", "periodTo"):
            assert after[field] == before[field], field
        # History grew; nothing was overwritten.
        assert after["assignmentCount"] == assignments_before + 1

        units_shares = _nk_shares(client, "cost_demo_garbage")
        assert sum(units_shares) == 120000  # still reconciles to the cent
        assert units_shares != GOLDEN_AREA_SHARES  # the key really changed the maths

        # ── switch back: the original numbers must return exactly ───────────
        back = client.post(
            f"{BASE}/costs/cost_demo_garbage/key", headers=DEMO, json={"key": "AREA"}
        )
        assert back.status_code == 200
        assert back.json()["key"] == "AREA"
        assert back.json()["assignmentCount"] == assignments_before + 2
        assert _nk_shares(client, "cost_demo_garbage") == GOLDEN_AREA_SHARES

        final = _seeded_cost(client)
        assert final["amountCents"] == 120000  # the money never moved
        assert final["label"] == "Müllabfuhr"


class TestCostCreation:
    def test_create_cost_with_units_key(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE}/buildings/{DEMO_BUILDING_ID}/costs",
            headers=DEMO,
            json={
                "label": "Hausreinigung",
                "catalogueId": "gebaeudereinigung",
                "amountCents": 60000,
                "periodFrom": "2025-01-01",
                "periodTo": "2026-01-01",
                "keyOverride": "UNITS",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["key"] == "UNITS"
        assert body["assignmentCount"] == 1
        assert body["amountEur"] == f"600,00{NBSP}€"

        # It joins the statement and every cost still reconciles.
        statement = client.get(f"{BASE}/statements/demo", headers=DEMO).json()
        labels = [c["label"] for c in statement["nkCosts"]]
        assert "Hausreinigung" in labels
        cleaning = next(c for c in statement["nkCosts"] if c["label"] == "Hausreinigung")
        assert sum(line["amountCents"] for line in cleaning["lines"]) == 60000
        assert statement["nkTotalCents"] == statement["nkInputTotalCents"]

        voided = client.post(
            f"{BASE}/costs/{body['id']}/void", headers=DEMO, json={"reason": "Testkorrektur"}
        )
        assert voided.status_code == 200

    def test_direct_key_requires_a_target(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE}/buildings/{DEMO_BUILDING_ID}/costs",
            headers=DEMO,
            json={
                "label": "Reparatur",
                "amountCents": 10000,
                "periodFrom": "2025-01-01",
                "periodTo": "2026-01-01",
                "key": "DIRECT",
            },
        )
        assert response.status_code == 422

    def test_non_direct_key_must_not_carry_a_target(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE}/buildings/{DEMO_BUILDING_ID}/costs",
            headers=DEMO,
            json={
                "label": "Reparatur",
                "amountCents": 10000,
                "periodFrom": "2025-01-01",
                "periodTo": "2026-01-01",
                "key": "AREA",
                "directUnitId": "unit_demo_a",
            },
        )
        assert response.status_code == 422

    def test_direct_cost_goes_to_one_unit_only(self, client: TestClient) -> None:
        created = client.post(
            f"{BASE}/buildings/{DEMO_BUILDING_ID}/costs",
            headers=DEMO,
            json={
                "label": "Reparatur Wohnung A",
                "catalogueId": "etagenheizung_wartung",
                "amountCents": 30000,
                "periodFrom": "2025-01-01",
                "periodTo": "2026-01-01",
                "directUnitId": "unit_demo_a",
            },
        )
        assert created.status_code == 201
        cost_id = created.json()["id"]

        statement = client.get(f"{BASE}/statements/demo", headers=DEMO).json()
        repair = next(c for c in statement["nkCosts"] if c["label"] == "Reparatur Wohnung A")
        assert repair["keyLabel"] == "Direktzuordnung"
        # The whole amount lands on unit A's party lines, nothing spreads.
        assert sum(line["amountCents"] for line in repair["lines"]) == 30000
        assert all(
            "Wohnung A" in line["partyLabel"] for line in repair["lines"] if not line["isLandlord"]
        )

        assert (
            client.post(
                f"{BASE}/costs/{cost_id}/void", headers=DEMO, json={"reason": "Testkorrektur"}
            ).status_code
            == 200
        )

    def test_period_must_be_ordered(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE}/buildings/{DEMO_BUILDING_ID}/costs",
            headers=DEMO,
            json={
                "label": "Rückwärts",
                "amountCents": 100,
                "periodFrom": "2026-01-01",
                "periodTo": "2025-01-01",
                "key": "AREA",
            },
        )
        assert response.status_code == 422


class TestIsolation:
    def test_unknown_or_invisible_buildings_are_not_cost_routes(self, client: TestClient) -> None:
        unknown = "bld_missing"
        assert client.get(f"{BASE}/buildings/{unknown}/costs", headers=DEMO).status_code == 404
        assert (
            client.post(
                f"{BASE}/buildings/{unknown}/costs",
                headers=DEMO,
                json={
                    "label": "Unbekannt",
                    "catalogueId": "gebaeudereinigung",
                    "amountCents": 100,
                    "periodFrom": "2025-01-01",
                    "periodTo": "2026-01-01",
                },
            ).status_code
            == 404
        )

    def test_stranger_cannot_read_or_write_costs(self, client: TestClient) -> None:
        stranger = _token("per_stranger")
        assert (
            client.get(f"{BASE}/buildings/{DEMO_BUILDING_ID}/costs", headers=stranger).status_code
            == 403
        )
        assert (
            client.post(
                f"{BASE}/costs/cost_demo_garbage/key", headers=stranger, json={"key": "UNITS"}
            ).status_code
            == 403
        )
