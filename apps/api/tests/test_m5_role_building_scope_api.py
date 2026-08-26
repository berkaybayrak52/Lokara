"""M5 role and assigned-building authorization contracts against live Postgres.

These fixtures deliberately exercise the API rather than a dependency in
isolation: account RLS alone cannot distinguish two buildings in one account.
"""

import os
import time
from collections.abc import Iterator
from datetime import UTC, datetime
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
    BuildingAssignment,
    DbSettings,
    Membership,
    Person,
    Role,
    Unit,
    create_db_engine,
)
from lokara_db.seed import DEMO_ACCOUNT_ID, DEMO_PERSON_ID, seed_demo
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "db"
_TEST_JWT_ISSUER = "https://lokara.test/auth/v1"

_ASSIGNED_BUILDING_ID = "bld_m5_assigned"
_FOREIGN_BUILDING_ID = "bld_m5_foreign"
_ASSIGNED_UNIT_ID = "unit_m5_assigned"
_FOREIGN_UNIT_ID = "unit_m5_foreign"
_EMPLOYEE_ID = "per_m5_employee"
_UNASSIGNED_EMPLOYEE_ID = "per_m5_employee_none"
_MULTI_EMPLOYEE_ID = "per_m5_employee_multi"
_TAX_ADVISOR_ID = "per_m5_tax_advisor"
_REVOKED_ID = "per_m5_revoked"
_OTHER_ACCOUNT_ID = "acc_m5_other"
_OTHER_OWNER_ID = "per_m5_other_owner"


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    settings = DbSettings()
    try:
        owner = create_db_engine(settings.direct_url)
        with owner.connect() as connection:
            app_role_sql = (_DB_PACKAGE_DIR / "scripts" / "init-app-role.sql").read_text()
            connection.execute(text(app_role_sql))
            connection.commit()
    except OperationalError as exc:
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")

    command.upgrade(Config(str(_DB_PACKAGE_DIR / "alembic.ini")), "head")
    with Session(owner) as session, session.begin():
        seed_demo(session)
        session.merge(
            Building(
                id=_ASSIGNED_BUILDING_ID,
                account_id=DEMO_ACCOUNT_ID,
                name="M5 Zugewiesen",
                street="Zuweisungsweg 1",
                postal_code="60311",
                city="Frankfurt am Main",
            )
        )
        session.merge(
            Building(
                id=_FOREIGN_BUILDING_ID,
                account_id=DEMO_ACCOUNT_ID,
                name="M5 Nicht zugewiesen",
                street="Sperrweg 2",
                postal_code="60311",
                city="Frankfurt am Main",
            )
        )
        session.merge(
            Unit(
                id=_ASSIGNED_UNIT_ID,
                account_id=DEMO_ACCOUNT_ID,
                building_id=_ASSIGNED_BUILDING_ID,
                label="M5 Zugewiesene Wohnung",
                area_sqm_x100=5000,
            )
        )
        session.merge(
            Unit(
                id=_FOREIGN_UNIT_ID,
                account_id=DEMO_ACCOUNT_ID,
                building_id=_FOREIGN_BUILDING_ID,
                label="M5 Nicht zugewiesene Wohnung",
                area_sqm_x100=5000,
            )
        )
        for person_id in (
            _EMPLOYEE_ID,
            _UNASSIGNED_EMPLOYEE_ID,
            _MULTI_EMPLOYEE_ID,
            _TAX_ADVISOR_ID,
            _REVOKED_ID,
            _OTHER_OWNER_ID,
        ):
            session.merge(Person(id=person_id, email=f"{person_id}@lokara.example"))
        session.merge(Account(id=_OTHER_ACCOUNT_ID, name="M5 Fremdkonto"))
        session.merge(
            Membership(
                id="mem_m5_employee",
                person_id=_EMPLOYEE_ID,
                account_id=DEMO_ACCOUNT_ID,
                role=Role.EMPLOYEE,
                accepted_at=datetime(2025, 1, 1, 9, 0, tzinfo=UTC),
            )
        )
        session.merge(
            Membership(
                id="mem_m5_employee_none",
                person_id=_UNASSIGNED_EMPLOYEE_ID,
                account_id=DEMO_ACCOUNT_ID,
                role=Role.EMPLOYEE,
                accepted_at=datetime(2025, 1, 1, 9, 0, tzinfo=UTC),
            )
        )
        session.merge(
            Membership(
                id="mem_m5_employee_multi",
                person_id=_MULTI_EMPLOYEE_ID,
                account_id=DEMO_ACCOUNT_ID,
                role=Role.EMPLOYEE,
                accepted_at=datetime(2025, 1, 1, 9, 0, tzinfo=UTC),
            )
        )
        session.merge(
            Membership(
                id="mem_m5_tax_advisor",
                person_id=_TAX_ADVISOR_ID,
                account_id=DEMO_ACCOUNT_ID,
                role=Role.TAX_ADVISOR,
                accepted_at=datetime(2025, 1, 1, 9, 0, tzinfo=UTC),
            )
        )
        session.merge(
            Membership(
                id="mem_m5_revoked",
                person_id=_REVOKED_ID,
                account_id=DEMO_ACCOUNT_ID,
                role=Role.EMPLOYEE,
                accepted_at=datetime(2025, 1, 1, 9, 0, tzinfo=UTC),
                revoked_at=datetime.now(UTC),
            )
        )
        session.merge(
            Membership(
                id="mem_m5_other_owner",
                person_id=_OTHER_OWNER_ID,
                account_id=_OTHER_ACCOUNT_ID,
                role=Role.OWNER,
                accepted_at=datetime(2025, 1, 1, 9, 0, tzinfo=UTC),
            )
        )
        for assignment_id, membership_id, building_id in (
            ("ba_m5_employee_assigned", "mem_m5_employee", _ASSIGNED_BUILDING_ID),
            ("ba_m5_multi_assigned", "mem_m5_employee_multi", _ASSIGNED_BUILDING_ID),
            ("ba_m5_multi_foreign", "mem_m5_employee_multi", _FOREIGN_BUILDING_ID),
        ):
            session.merge(
                BuildingAssignment(
                    id=assignment_id,
                    account_id=DEMO_ACCOUNT_ID,
                    membership_id=membership_id,
                    building_id=building_id,
                )
            )
    test_client = TestClient(create_app())
    try:
        yield test_client
    finally:
        test_client.close()
        with Session(owner) as session, session.begin():
            session.execute(
                text("DELETE FROM building_assignment WHERE membership_id LIKE 'mem_m5_%'")
            )
            session.execute(
                text("DELETE FROM unit WHERE building_id IN (:assigned, :foreign)"),
                {"assigned": _ASSIGNED_BUILDING_ID, "foreign": _FOREIGN_BUILDING_ID},
            )
            session.execute(
                text("DELETE FROM building WHERE id IN (:assigned, :foreign)"),
                {"assigned": _ASSIGNED_BUILDING_ID, "foreign": _FOREIGN_BUILDING_ID},
            )
            session.execute(text("DELETE FROM membership WHERE id LIKE 'mem_m5_%'"))
            session.execute(text("DELETE FROM person WHERE id LIKE 'per_m5_%'"))
            session.execute(
                text("DELETE FROM account WHERE id = :account"),
                {"account": _OTHER_ACCOUNT_ID},
            )
        owner.dispose()


def _token(person_id: str) -> dict[str, str]:
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": person_id,
            "iss": str(getattr(ApiSettings(), "supabase_jwt_issuer", _TEST_JWT_ISSUER)),
            "aud": "authenticated",
            "role": "authenticated",
            "iat": now,
            "exp": now + 3600,
        },
        ApiSettings().supabase_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


_BASE = f"/a/{DEMO_ACCOUNT_ID}"


class TestM5Roles:
    def test_owner_keeps_all_current_buildings(self, client: TestClient) -> None:
        response = client.get(f"{_BASE}/buildings", headers=_token(DEMO_PERSON_ID))
        assert response.status_code == 200
        ids = {building["id"] for building in response.json()["buildings"]}
        assert {_ASSIGNED_BUILDING_ID, _FOREIGN_BUILDING_ID} <= ids

    def test_assigned_employee_sees_only_assigned_building(self, client: TestClient) -> None:
        response = client.get(f"{_BASE}/buildings", headers=_token(_EMPLOYEE_ID))
        assert response.status_code == 200
        assert [building["id"] for building in response.json()["buildings"]] == [
            _ASSIGNED_BUILDING_ID
        ]

    def test_unassigned_employee_sees_no_buildings(self, client: TestClient) -> None:
        response = client.get(f"{_BASE}/buildings", headers=_token(_UNASSIGNED_EMPLOYEE_ID))
        assert response.status_code == 200
        assert response.json()["buildings"] == []

    def test_multi_assigned_employee_sees_each_assigned_building(self, client: TestClient) -> None:
        response = client.get(f"{_BASE}/buildings", headers=_token(_MULTI_EMPLOYEE_ID))
        assert response.status_code == 200
        assert {building["id"] for building in response.json()["buildings"]} == {
            _ASSIGNED_BUILDING_ID,
            _FOREIGN_BUILDING_ID,
        }

    def test_tax_advisor_can_bootstrap_but_cannot_use_owner_portal(
        self, client: TestClient
    ) -> None:
        me = client.get("/me", headers=_token(_TAX_ADVISOR_ID))
        assert me.status_code == 200
        assert me.json()["accounts"] == [
            {"id": DEMO_ACCOUNT_ID, "name": "Demo Konto", "role": "TAX_ADVISOR", "shape": "SOLO"}
        ]
        assert client.get(f"{_BASE}/buildings", headers=_token(_TAX_ADVISOR_ID)).status_code == 403

    def test_revoked_membership_is_not_a_portal_context(self, client: TestClient) -> None:
        assert client.get(f"{_BASE}/buildings", headers=_token(_REVOKED_ID)).status_code == 403
        response = client.get("/me", headers=_token(_REVOKED_ID))
        assert response.status_code == 200
        assert response.json()["accounts"] == []

    def test_member_of_another_account_cannot_open_this_account(self, client: TestClient) -> None:
        assert client.get(f"{_BASE}/buildings", headers=_token(_OTHER_OWNER_ID)).status_code == 403


class TestM5BuildingScope:
    def test_employee_write_is_limited_to_assigned_building(self, client: TestClient) -> None:
        headers = _token(_EMPLOYEE_ID)
        assigned = client.post(
            f"{_BASE}/buildings/{_ASSIGNED_BUILDING_ID}/units",
            headers=headers,
            json={"label": "M5 Mitarbeiterzugang", "areaSqmX100": 4200},
        )
        assert assigned.status_code == 201
        foreign = client.post(
            f"{_BASE}/buildings/{_FOREIGN_BUILDING_ID}/units",
            headers=headers,
            json={"label": "M5 Verboten", "areaSqmX100": 4200},
        )
        assert foreign.status_code == 404

    @pytest.mark.parametrize(
        "path",
        [
            f"/buildings/{_FOREIGN_BUILDING_ID}",
            f"/units/{_FOREIGN_UNIT_ID}",
            f"/buildings/{_FOREIGN_BUILDING_ID}/costs",
            f"/buildings/{_FOREIGN_BUILDING_ID}/meters",
            f"/buildings/{_FOREIGN_BUILDING_ID}/mdl-statements",
            f"/buildings/{_FOREIGN_BUILDING_ID}/statement",
        ],
    )
    def test_unassigned_nested_resources_are_undiscoverable(
        self, client: TestClient, path: str
    ) -> None:
        response = client.get(f"{_BASE}{path}", headers=_token(_EMPLOYEE_ID))
        assert response.status_code == 404

    def test_one_assignment_resolves_summary_to_that_building(self, client: TestClient) -> None:
        response = client.get(f"{_BASE}/summary", headers=_token(_EMPLOYEE_ID))
        assert response.status_code == 200
        assert response.json()["buildingName"] == "M5 Zugewiesen"

    def test_zero_assignments_return_no_account_level_data(self, client: TestClient) -> None:
        response = client.get(f"{_BASE}/summary", headers=_token(_UNASSIGNED_EMPLOYEE_ID))
        assert response.status_code == 404

    def test_multiple_assignments_require_an_explicit_building(self, client: TestClient) -> None:
        assert client.get(f"{_BASE}/summary", headers=_token(_MULTI_EMPLOYEE_ID)).status_code == 422


class TestM5BootstrapAndOpenApi:
    def test_me_is_context_only(self, client: TestClient) -> None:
        response = client.get("/me", headers=_token(_EMPLOYEE_ID))
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"personId", "email", "accounts"}
        assert body["accounts"] == [
            {"id": DEMO_ACCOUNT_ID, "name": "Demo Konto", "role": "EMPLOYEE", "shape": "SOLO"}
        ]

    def test_no_current_request_schema_can_write_renter_person_id(self) -> None:
        document = create_app().openapi()
        schemas = document["components"]["schemas"]

        def resolve(schema: object) -> object:
            if isinstance(schema, dict) and "$ref" in schema:
                return schemas[schema["$ref"].rsplit("/", 1)[-1]]
            return schema

        def contains_renter_person_id(schema: object) -> bool:
            schema = resolve(schema)
            if not isinstance(schema, dict):
                return False
            properties = schema.get("properties", {})
            if isinstance(properties, dict) and {"personId", "person_id"} & set(properties):
                return True
            return any(contains_renter_person_id(item) for item in schema.get("allOf", []))

        writable: list[str] = []
        for path, operations in document["paths"].items():
            for method, operation in operations.items():
                if method not in {"post", "put", "patch"}:
                    continue
                request_body = operation.get("requestBody", {})
                for media in request_body.get("content", {}).values():
                    if contains_renter_person_id(media.get("schema", {})):
                        writable.append(f"{method.upper()} {path}")
        assert writable == []
