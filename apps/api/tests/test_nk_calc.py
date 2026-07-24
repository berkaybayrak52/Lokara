"""The Phase E DoD gate: a JWT-auth'd NK request returns the €1,200 fixture's
numbers byte-exact over HTTP (MIGRATION-PLAN Phase E). No database required."""

import pytest
from fastapi.testclient import TestClient
from lokara_api import create_app
from lokara_api.auth import create_dev_token
from lokara_api.settings import ApiSettings

NBSP = " "

# The canonical €1,200 garbage-cost scenario (docs/03, Appendix A.4):
# 365-day period, AREA key, Renter 2 moves out 30 Jun (valid_to exclusive).
FIXTURE_REQUEST = {
    "billingPeriod": {"validFrom": "2025-01-01", "validTo": "2026-01-01"},
    "units": [
        {"unitId": "unit-a", "areaSqmX100": 5000},
        {"unitId": "unit-b", "areaSqmX100": 3000},
        {"unitId": "unit-c", "areaSqmX100": 2000},
    ],
    "occupancies": [
        {"unitId": "unit-a", "tenancyId": "ten-a", "period": {"validFrom": "2023-04-01"}},
        {
            "unitId": "unit-b",
            "tenancyId": "ten-b",
            "period": {"validFrom": "2021-09-01", "validTo": "2025-07-01"},
        },
        {"unitId": "unit-c", "tenancyId": "ten-c", "period": {"validFrom": "2024-01-01"}},
    ],
    "costs": [
        {"costId": "garbage", "label": "Müllabfuhr", "amountCents": 120000, "key": "AREA"}
    ],
}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


def _auth_header() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_dev_token(ApiSettings().supabase_jwt_secret)}"}


class TestNkCalc:
    def test_requires_auth(self, client: TestClient) -> None:
        assert client.post("/calc/nk", json=FIXTURE_REQUEST).status_code == 401

    def test_eur_1200_fixture_byte_exact(self, client: TestClient) -> None:
        response = client.post("/calc/nk", json=FIXTURE_REQUEST, headers=_auth_header())
        assert response.status_code == 200
        body = response.json()
        assert [
            (line["unitId"], line["tenancyId"], line["amountCents"]) for line in body["lines"]
        ] == [
            ("unit-a", "ten-a", 60000),
            ("unit-b", "ten-b", 17852),
            ("unit-b", None, 18148),  # vacancy Jul–Dec falls on the landlord
            ("unit-c", "ten-c", 24000),
        ]
        assert body["totalCents"] == 120000
        assert body["totalEur"] == f"1.200,00{NBSP}€"
        assert body["lines"][0]["amountEur"] == f"600,00{NBSP}€"

    def test_engine_validation_maps_to_422(self, client: TestClient) -> None:
        open_period = {**FIXTURE_REQUEST, "billingPeriod": {"validFrom": "2025-01-01"}}
        response = client.post("/calc/nk", json=open_period, headers=_auth_header())
        assert response.status_code == 422

    def test_pydantic_rejects_malformed_body(self, client: TestClient) -> None:
        broken = {**FIXTURE_REQUEST, "costs": [{"costId": "x"}]}
        response = client.post("/calc/nk", json=broken, headers=_auth_header())
        assert response.status_code == 422
