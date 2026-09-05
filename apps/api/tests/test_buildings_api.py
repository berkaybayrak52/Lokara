"""Objekte/Einheiten/Mietverhältnisse CRUD against a live Postgres.

The whole chain runs through the URL-scoped API: create Building → Unit →
Tenancy, read back list/detail/timeline, overlap rejected with 422, and the
usual two isolation proofs (path re-authorization + RLS backstop).
"""

import os
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from lokara_adapters.geocoding import GeocodingResult
from lokara_api import create_app
from lokara_api.authorization import PortalScope
from lokara_api.deps import account_session_for_path
from lokara_api.routers import buildings as buildings_router
from lokara_api.schemas import BuildingCreate, BuildingSummary
from lokara_api.settings import ApiSettings
from lokara_db import Account, Building, DbSettings, Membership, Person, Role, create_db_engine
from lokara_db.seed import DEMO_ACCOUNT_ID, DEMO_PERSON_ID, seed_demo
from pydantic import ValidationError
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
                accepted_at=datetime(2025, 1, 1, 9, 0, tzinfo=UTC),
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


def _building_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Testgasse 5",
        "buildingType": "WOHNHAUS",
        "isResidential": True,
        "street": "Testgasse",
        "houseNumber": "5",
        "postalCode": "60313",
        "city": "Frankfurt am Main",
    }
    payload.update(overrides)
    return payload


class _RecordingBuildingSession:
    """Small route-boundary double; these PLZ fixtures never open Postgres."""

    def __init__(self) -> None:
        self.info = {
            "portal_scope": PortalScope(
                role=Role.OWNER,
                building_ids=frozenset(),
                membership_id="mem_plz_fixture",
            )
        }
        self.added: list[Building] = []

    def add(self, building: Building) -> None:
        self.added.append(building)

    def flush(self) -> None:
        pass


@pytest.fixture
def offline_building_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, FastAPI, _RecordingBuildingSession]]:
    monkeypatch.setenv("GEOCODING_ENABLED", "false")
    buildings_router.get_geocoding_gateway.cache_clear()
    app = create_app()
    session = _RecordingBuildingSession()
    app.dependency_overrides[account_session_for_path] = lambda: session
    try:
        with TestClient(app) as test_client:
            yield test_client, app, session
    finally:
        buildings_router.get_geocoding_gateway.cache_clear()


class TestBuildingContracts:
    @pytest.mark.parametrize("missing", ["buildingType", "isResidential", "houseNumber"])
    def test_create_schema_requires_ui03_fields(self, missing: str) -> None:
        payload = _building_payload()
        del payload[missing]
        with pytest.raises(ValidationError):
            BuildingCreate.model_validate(payload)

    def test_create_schema_keeps_german_postcode_and_country_default(self) -> None:
        body = BuildingCreate.model_validate(_building_payload())
        assert body.building_type == "WOHNHAUS"
        assert body.is_residential is True
        assert body.house_number == "5"
        assert body.country == "Deutschland"
        assert body.postal_code == "60313"

    def test_create_schema_rejects_an_address_over_200_composed_characters(self) -> None:
        with pytest.raises(ValidationError):
            BuildingCreate.model_validate(_building_payload(street="A" * 180, houseNumber="1" * 20))

    def test_summary_schema_exposes_type_and_nullable_coordinates(self) -> None:
        summary = BuildingSummary.model_validate(
            {
                "id": "building-1",
                "name": "Geohaus",
                "street": "Geoallee 7",
                "postalCode": "60313",
                "city": "Frankfurt am Main",
                "unitCount": 0,
                "buildingType": "WOHNHAUS",
                "latitude": None,
                "longitude": None,
            }
        )
        assert summary.building_type == "WOHNHAUS"
        assert summary.latitude is None
        assert summary.longitude is None


class TestCreateChain:
    tenancy_id: str
    """One flowing scenario: Building → Unit → Tenancy → timeline read-back."""

    building_id: str
    unit_id: str

    def test_create_building(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE}/buildings",
            headers=DEMO,
            json=_building_payload(),
        )
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Testgasse 5"
        assert body["street"] == "Testgasse 5"
        assert body["buildingType"] == "WOHNHAUS"
        assert body["latitude"] == 50.11539440000001
        assert body["longitude"] == 8.680582099999999
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
                "buildingType": "WOHNHAUS",
                "isResidential": True,
                "street": "X",
                "houseNumber": "1",
                "postalCode": "123",
                "city": "F",
            },
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("missing", ["buildingType", "isResidential", "houseNumber"])
    def test_new_building_fields_are_required(self, client: TestClient, missing: str) -> None:
        payload = _building_payload(name=f"Fehlend {missing}")
        del payload[missing]
        response = client.post(f"{BASE}/buildings", headers=DEMO, json=payload)
        assert response.status_code == 422

    def test_composed_street_must_fit_the_existing_200_character_limit(
        self, client: TestClient
    ) -> None:
        response = client.post(
            f"{BASE}/buildings",
            headers=DEMO,
            json=_building_payload(name="Zu lange Adresse", street="A" * 180, houseNumber="1" * 20),
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
                "buildingType": "WOHNHAUS",
                "isResidential": True,
                "street": "E",
                "houseNumber": "1",
                "postalCode": "60000",
                "city": "F",
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


class TestOfflinePlzBuildingBoundary:
    def test_default_known_plz_stores_vendored_centroid_without_network(
        self,
        offline_building_client: tuple[TestClient, FastAPI, _RecordingBuildingSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        client, _app, session = offline_building_client

        def reject_network(*args: object, **kwargs: object) -> None:
            del args, kwargs
            pytest.fail("default PLZ lookup must not call Nominatim")

        monkeypatch.setattr("lokara_api.geocoding_http.urlopen", reject_network)
        response = client.post(
            f"{BASE}/buildings",
            json=_building_payload(name="Offline-PLZ-Haus"),
        )

        assert response.status_code == 201, response.text
        assert len(session.added) == 1
        building = session.added[0]
        expected = (50.11539440000001, 8.680582099999999)
        assert (building.latitude, building.longitude) == expected
        assert (response.json()["latitude"], response.json()["longitude"]) == expected

    def test_default_unknown_five_digit_plz_is_422_and_writes_nothing(
        self,
        offline_building_client: tuple[TestClient, FastAPI, _RecordingBuildingSession],
    ) -> None:
        client, _app, session = offline_building_client
        response = client.post(
            f"{BASE}/buildings",
            json=_building_payload(
                name="Unbekannte PLZ",
                postalCode="00000",
            ),
        )

        assert response.status_code == 422, response.text
        assert "00000" in response.json()["detail"]
        assert session.added == []

    def test_explicit_custom_geocoding_gateway_override_remains_compatible(
        self,
        offline_building_client: tuple[TestClient, FastAPI, _RecordingBuildingSession],
    ) -> None:
        client, app, session = offline_building_client

        class CustomGateway:
            address: str | None = None

            def geocode(self, address: str) -> GeocodingResult:
                self.address = address
                return GeocodingResult(latitude=48.137154, longitude=11.576124)

        custom_gateway = CustomGateway()
        app.dependency_overrides[buildings_router.get_geocoding_gateway] = lambda: custom_gateway
        response = client.post(
            f"{BASE}/buildings",
            json=_building_payload(
                name="Explizites Gateway",
                street="Gatewayweg",
                houseNumber="9",
            ),
        )

        assert response.status_code == 201, response.text
        assert custom_gateway.address == ("Gatewayweg 9, 60313 Frankfurt am Main, Deutschland")
        assert len(session.added) == 1
        assert (session.added[0].latitude, session.added[0].longitude) == (
            48.137154,
            11.576124,
        )


class TestGeocodingBoundary:
    @staticmethod
    def _override(client: TestClient, gateway: object) -> Callable[..., Any]:
        dependency = buildings_router.get_geocoding_gateway
        cast(FastAPI, client.app).dependency_overrides[dependency] = lambda: gateway
        return dependency

    def test_normalized_coordinates_are_saved_and_returned_in_summary(
        self, client: TestClient
    ) -> None:
        from lokara_adapters.geocoding import GeocodingResult

        class Gateway:
            address: str | None = None

            def geocode(self, address: str) -> GeocodingResult:
                self.address = address
                return GeocodingResult(latitude=50.1109, longitude=8.6821)

        gateway = Gateway()
        dependency = self._override(client, gateway)
        try:
            response = client.post(
                f"{BASE}/buildings",
                headers=DEMO,
                json=_building_payload(
                    name="Geohaus 7",
                    buildingType="WOHN_UND_GESCHAEFTSHAUS",
                    street="Geoallee",
                    houseNumber="7",
                ),
            )
            assert response.status_code == 201, response.text
            body = response.json()
            assert gateway.address == "Geoallee 7, 60313 Frankfurt am Main, Deutschland"
            assert body["buildingType"] == "WOHN_UND_GESCHAEFTSHAUS"
            assert body["latitude"] == pytest.approx(50.1109)
            assert body["longitude"] == pytest.approx(8.6821)
            assert isinstance(body["latitude"], float)
            assert isinstance(body["longitude"], float)

            listing = client.get(f"{BASE}/buildings", headers=DEMO)
            listed = next(row for row in listing.json()["buildings"] if row["id"] == body["id"])
            assert listed["buildingType"] == "WOHN_UND_GESCHAEFTSHAUS"
            assert listed["latitude"] == pytest.approx(50.1109)
            assert listed["longitude"] == pytest.approx(8.6821)
        finally:
            cast(FastAPI, client.app).dependency_overrides.pop(dependency, None)

    def test_gateway_failure_never_blocks_create(self, client: TestClient) -> None:
        class FailingGateway:
            def geocode(self, address: str) -> None:
                del address
                raise OSError("network unavailable")

        dependency = self._override(client, FailingGateway())
        try:
            response = client.post(
                f"{BASE}/buildings",
                headers=DEMO,
                json=_building_payload(name="Haus ohne Geopunkt", houseNumber="9"),
            )
            assert response.status_code == 201, response.text
            assert response.json()["latitude"] is None
            assert response.json()["longitude"] is None
        finally:
            cast(FastAPI, client.app).dependency_overrides.pop(dependency, None)
