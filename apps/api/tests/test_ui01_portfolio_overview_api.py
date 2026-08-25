"""UI-01 portfolio overview contract against live Postgres.

The endpoint is a compact server read model. These fixtures keep the money and
occupancy semantics at the HTTP boundary so the dashboard never reconstructs
them from building or tenancy feeds.
"""

import os
import time
from collections.abc import Iterator
from datetime import UTC, date, datetime
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
    AdvancePaymentPeriod,
    Building,
    BuildingAssignment,
    DbSettings,
    Membership,
    Person,
    Role,
    Tenancy,
    Unit,
    create_db_engine,
)
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "db"
_TEST_JWT_ISSUER = "https://lokara.test/auth/v1"

_ACCOUNT_ID = "acc_ui01_portfolio"
_EMPTY_ACCOUNT_ID = "acc_ui01_empty"
_OTHER_ACCOUNT_ID = "acc_ui01_other"
_OWNER_ID = "per_ui01_owner"
_EMPTY_OWNER_ID = "per_ui01_empty_owner"
_EMPLOYEE_ID = "per_ui01_employee"
_UNASSIGNED_EMPLOYEE_ID = "per_ui01_employee_none"
_MULTI_EMPLOYEE_ID = "per_ui01_employee_multi"
_ARCHIVED_EMPLOYEE_ID = "per_ui01_employee_archived"
_OTHER_OWNER_ID = "per_ui01_other_owner"

_VISIBLE_BUILDING_ID = "bld_ui01_visible"
_SECOND_BUILDING_ID = "bld_ui01_second"
_ARCHIVED_BUILDING_ID = "bld_ui01_archived"


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
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
    today = date.today()
    with Session(owner) as session, session.begin():
        for person_id in (
            _OWNER_ID,
            _EMPTY_OWNER_ID,
            _EMPLOYEE_ID,
            _UNASSIGNED_EMPLOYEE_ID,
            _MULTI_EMPLOYEE_ID,
            _ARCHIVED_EMPLOYEE_ID,
            _OTHER_OWNER_ID,
        ):
            session.merge(Person(id=person_id, email=f"{person_id}@lokara.example"))
        for account_id, name in (
            (_ACCOUNT_ID, "UI-01 Portfolio"),
            (_EMPTY_ACCOUNT_ID, "UI-01 Leer"),
            (_OTHER_ACCOUNT_ID, "UI-01 Fremdkonto"),
        ):
            session.merge(Account(id=account_id, name=name))
        for membership_id, person_id, account_id, role in (
            ("mem_ui01_owner", _OWNER_ID, _ACCOUNT_ID, Role.OWNER),
            ("mem_ui01_empty_owner", _EMPTY_OWNER_ID, _EMPTY_ACCOUNT_ID, Role.OWNER),
            ("mem_ui01_employee", _EMPLOYEE_ID, _ACCOUNT_ID, Role.EMPLOYEE),
            (
                "mem_ui01_employee_none",
                _UNASSIGNED_EMPLOYEE_ID,
                _ACCOUNT_ID,
                Role.EMPLOYEE,
            ),
            (
                "mem_ui01_employee_multi",
                _MULTI_EMPLOYEE_ID,
                _ACCOUNT_ID,
                Role.EMPLOYEE,
            ),
            (
                "mem_ui01_employee_archived",
                _ARCHIVED_EMPLOYEE_ID,
                _ACCOUNT_ID,
                Role.EMPLOYEE,
            ),
            ("mem_ui01_other_owner", _OTHER_OWNER_ID, _OTHER_ACCOUNT_ID, Role.OWNER),
        ):
            session.merge(
                Membership(
                    id=membership_id,
                    person_id=person_id,
                    account_id=account_id,
                    role=role,
                )
            )

        for building_id, name, archived_at in (
            (_VISIBLE_BUILDING_ID, "UI-01 Zugewiesen", None),
            (_SECOND_BUILDING_ID, "UI-01 Zweites Objekt", None),
            (_ARCHIVED_BUILDING_ID, "UI-01 Archiv", datetime(2020, 1, 1, tzinfo=UTC)),
        ):
            session.merge(
                Building(
                    id=building_id,
                    account_id=_ACCOUNT_ID,
                    name=name,
                    street="Portfolioweg 1",
                    postal_code="60311",
                    city="Frankfurt am Main",
                    archived_at=archived_at,
                )
            )

        units = (
            ("unit_ui01_active", _VISIBLE_BUILDING_ID, "Aktiv"),
            ("unit_ui01_boundary", _VISIBLE_BUILDING_ID, "Heute beendet"),
            ("unit_ui01_future", _VISIBLE_BUILDING_ID, "Zukünftig"),
            ("unit_ui01_second", _SECOND_BUILDING_ID, "Zweites Objekt"),
            ("unit_ui01_archived", _ARCHIVED_BUILDING_ID, "Archiviert"),
        )
        for unit_id, building_id, label in units:
            session.merge(
                Unit(
                    id=unit_id,
                    account_id=_ACCOUNT_ID,
                    building_id=building_id,
                    label=label,
                    area_sqm_x100=5000,
                )
            )

        for tenancy_id, unit_id, valid_from, valid_to, base_rent_cents in (
            ("ten_ui01_active", "unit_ui01_active", date(2020, 1, 1), None, 70_000),
            (
                "ten_ui01_boundary",
                "unit_ui01_boundary",
                date(2020, 1, 1),
                today,
                99_000,
            ),
            (
                "ten_ui01_future",
                "unit_ui01_future",
                date(2999, 1, 1),
                None,
                123_000,
            ),
            (
                "ten_ui01_second",
                "unit_ui01_second",
                today,
                date(2999, 1, 1),
                81_000,
            ),
            (
                "ten_ui01_archived",
                "unit_ui01_archived",
                date(2020, 1, 1),
                None,
                200_000,
            ),
        ):
            session.merge(
                Tenancy(
                    id=tenancy_id,
                    account_id=_ACCOUNT_ID,
                    unit_id=unit_id,
                    valid_from=valid_from,
                    valid_to=valid_to,
                    base_rent_cents=base_rent_cents,
                )
            )

        # A deliberately large advance proves the read model sums Kaltmiete,
        # not Warmmiete or advance schedules.
        session.merge(
            AdvancePaymentPeriod(
                id="adv_ui01_active",
                account_id=_ACCOUNT_ID,
                tenancy_id="ten_ui01_active",
                amount_cents=45_000,
                valid_from=date(2020, 1, 1),
                predecessor_id=None,
                declaration_ref="UI-01 fixture",
            )
        )
        for assignment_id, membership_id, building_id in (
            ("ba_ui01_employee", "mem_ui01_employee", _VISIBLE_BUILDING_ID),
            ("ba_ui01_multi_visible", "mem_ui01_employee_multi", _VISIBLE_BUILDING_ID),
            ("ba_ui01_multi_second", "mem_ui01_employee_multi", _SECOND_BUILDING_ID),
            ("ba_ui01_multi_archived", "mem_ui01_employee_multi", _ARCHIVED_BUILDING_ID),
            (
                "ba_ui01_archived_only",
                "mem_ui01_employee_archived",
                _ARCHIVED_BUILDING_ID,
            ),
        ):
            session.merge(
                BuildingAssignment(
                    id=assignment_id,
                    account_id=_ACCOUNT_ID,
                    membership_id=membership_id,
                    building_id=building_id,
                )
            )
    owner.dispose()

    test_client = TestClient(create_app())
    try:
        yield test_client
    finally:
        test_client.close()


def _token(person_id: str) -> dict[str, str]:
    now = int(time.time())
    encoded = jwt.encode(
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
    return {"Authorization": f"Bearer {encoded}"}


def test_openapi_declares_the_exact_portfolio_overview_response() -> None:
    document = create_app().openapi()
    operation = document["paths"]["/a/{account_id}/portfolio/overview"]["get"]
    response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    ref_name = response_schema["$ref"].rsplit("/", 1)[-1]
    schema = document["components"]["schemas"][ref_name]
    expected = {
        "buildingCount",
        "unitCount",
        "occupiedUnitCount",
        "vacantUnitCount",
        "mietSollCentsMonthly",
    }
    assert set(schema["properties"]) == expected
    assert set(schema["required"]) == expected


def test_owner_gets_non_archived_portfolio_with_half_open_today_boundaries(
    client: TestClient,
) -> None:
    response = client.get(
        f"/a/{_ACCOUNT_ID}/portfolio/overview",
        headers=_token(_OWNER_ID),
    )
    assert response.status_code == 200
    # `ten_ui01_boundary.valid_to == today` is excluded, while
    # `ten_ui01_second.valid_from == today` contributes 81,000 ct.
    assert response.json() == {
        "buildingCount": 2,
        "unitCount": 4,
        "occupiedUnitCount": 2,
        "vacantUnitCount": 2,
        "mietSollCentsMonthly": 151_000,
    }


def test_empty_owner_gets_five_zeroes(client: TestClient) -> None:
    response = client.get(
        f"/a/{_EMPTY_ACCOUNT_ID}/portfolio/overview",
        headers=_token(_EMPTY_OWNER_ID),
    )
    assert response.status_code == 200
    assert response.json() == {
        "buildingCount": 0,
        "unitCount": 0,
        "occupiedUnitCount": 0,
        "vacantUnitCount": 0,
        "mietSollCentsMonthly": 0,
    }


def test_employee_aggregation_is_limited_to_assigned_buildings(client: TestClient) -> None:
    response = client.get(
        f"/a/{_ACCOUNT_ID}/portfolio/overview",
        headers=_token(_EMPLOYEE_ID),
    )
    assert response.status_code == 200
    assert response.json() == {
        "buildingCount": 1,
        "unitCount": 3,
        "occupiedUnitCount": 1,
        "vacantUnitCount": 2,
        "mietSollCentsMonthly": 70_000,
    }


def test_employee_with_zero_assignments_gets_five_zeroes(client: TestClient) -> None:
    response = client.get(
        f"/a/{_ACCOUNT_ID}/portfolio/overview",
        headers=_token(_UNASSIGNED_EMPLOYEE_ID),
    )
    assert response.status_code == 200
    assert response.json() == {
        "buildingCount": 0,
        "unitCount": 0,
        "occupiedUnitCount": 0,
        "vacantUnitCount": 0,
        "mietSollCentsMonthly": 0,
    }


def test_employee_with_multiple_assignments_aggregates_both_live_buildings(
    client: TestClient,
) -> None:
    response = client.get(
        f"/a/{_ACCOUNT_ID}/portfolio/overview",
        headers=_token(_MULTI_EMPLOYEE_ID),
    )
    assert response.status_code == 200
    # This employee also has an assignment to the archived building. Its one
    # unit and 200,000 ct active rent must not enter any total.
    assert response.json() == {
        "buildingCount": 2,
        "unitCount": 4,
        "occupiedUnitCount": 2,
        "vacantUnitCount": 2,
        "mietSollCentsMonthly": 151_000,
    }


def test_employee_assigned_only_an_archived_building_gets_five_zeroes(
    client: TestClient,
) -> None:
    response = client.get(
        f"/a/{_ACCOUNT_ID}/portfolio/overview",
        headers=_token(_ARCHIVED_EMPLOYEE_ID),
    )
    assert response.status_code == 200
    assert response.json() == {
        "buildingCount": 0,
        "unitCount": 0,
        "occupiedUnitCount": 0,
        "vacantUnitCount": 0,
        "mietSollCentsMonthly": 0,
    }


def test_member_of_another_account_is_refused_by_the_existing_dependency(
    client: TestClient,
) -> None:
    response = client.get(
        f"/a/{_ACCOUNT_ID}/portfolio/overview",
        headers=_token(_OTHER_OWNER_ID),
    )
    assert response.status_code == 403
