"""RED M10-I4 API/default-layout contract from docs/14 § 4.9 (F06…F08)."""

from __future__ import annotations

import importlib
import json
import os
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, cast

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from lokara_api import create_app
from lokara_api.settings import ApiSettings
from lokara_db import DbSettings, create_db_engine, new_id
from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError

_DB_DIR = Path(__file__).resolve().parents[3] / "packages" / "db"
_PREFIX = "/a/{account_id}/investment"
_ROUTES = {
    f"{_PREFIX}/entitlement": {"get", "post"},
    f"{_PREFIX}/cases": {"post"},
    f"{_PREFIX}/cases/{{case_key}}": {"get"},
    f"{_PREFIX}/cases/{{case_key}}/sensitivity": {"get"},
    f"{_PREFIX}/cases/{{case_key}}/bank-view": {"get"},
    f"{_PREFIX}/cases/{{case_key}}/bank-pdf": {"get"},
}


@dataclass(frozen=True)
class _Graph:
    account_a: str
    account_b: str
    owner_a: str
    employee_a: str
    adviser_a: str
    owner_b: str


def _api() -> ModuleType:
    return importlib.import_module("lokara_api.routers.investment")


def _pdf() -> ModuleType:
    return importlib.import_module("lokara_pdf")


def _token(person_id: str) -> dict[str, str]:
    now = int(time.time())
    encoded = jwt.encode(
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
    return {"Authorization": f"Bearer {encoded}"}


def _facts() -> dict[str, object]:
    return {
        "purchasePriceCents": 42_000_000,
        "acquisitionCostsCents": 3_360_000,
        "monthlyActualRentCents": 265_000,
        "vacancyBp": 0,
        "administrationCents": 360_000,
        "maintenanceCents": 300_000,
        "reserveCents": 0,
        "vacancyRiskCents": 63_600,
        "equityCents": 11_360_000,
        "loanCents": 34_000_000,
        "interestBp": 390,
        "initialRepaymentBp": 200,
        "marginalTaxBp": 4_200,
        "buildingShareBp": 7_500,
        "afaRateBp": 200,
        "analysisPeriodMonths": 12,
        "financingProvenance": "annahme",
        "bankHeader": {
            "address": "Musterstraße 1, 10115 Berlin",
            "propertyType": "Mehrfamilienhaus",
            "yearBuilt": 1995,
            "areaSqmX100": 19_400,
            "unitCount": 4,
            "creator": "Eigentümer",
            "exportDate": "2026-09-16",
            "layoutVersion": "DEFAULT_BANK/1",
        },
    }


def _enable(client: TestClient, account_id: str, owner_id: str, enabled: bool = True) -> None:
    response = client.post(
        f"/a/{account_id}/investment/entitlement",
        headers=_token(owner_id),
        json={"enabled": enabled},
    )
    assert response.status_code == 201


def _create(
    client: TestClient,
    account_id: str,
    owner_id: str,
    *,
    layout_version_id: str | None = None,
) -> Any:
    body: dict[str, object] = {"facts": _facts()}
    if layout_version_id is not None:
        body["layoutVersionId"] = layout_version_id
    return client.post(
        f"/a/{account_id}/investment/cases",
        headers=_token(owner_id),
        json=body,
    )


@pytest.fixture(scope="module")
def environment() -> Iterator[tuple[TestClient, Engine]]:
    settings = DbSettings()
    try:
        owner = create_db_engine(settings.direct_url)
        with owner.connect() as connection:
            connection.execute(text((_DB_DIR / "scripts" / "init-app-role.sql").read_text()))
            connection.commit()
    except OperationalError as exc:
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")
    command.upgrade(Config(str(_DB_DIR / "alembic.ini")), "head")
    client = TestClient(create_app())
    yield client, owner
    client.close()
    owner.dispose()


@pytest.fixture
def graph(environment: tuple[TestClient, Engine]) -> _Graph:
    _client, owner = environment
    ids = [new_id() for _ in range(10)]
    value = _Graph(
        account_a=ids[0],
        account_b=ids[1],
        owner_a=ids[2],
        employee_a=ids[3],
        adviser_a=ids[4],
        owner_b=ids[5],
    )
    with owner.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO account (id, name, shape, plan) VALUES "
                "(:aa, 'I4 A', 'SOLO', 'TRIAL'), (:ab, 'I4 B', 'SOLO', 'TRIAL')"
            ),
            {"aa": value.account_a, "ab": value.account_b},
        )
        for person_id in (value.owner_a, value.employee_a, value.adviser_a, value.owner_b):
            connection.execute(
                text("INSERT INTO person (id, email) VALUES (:id, :email)"),
                {"id": person_id, "email": f"{person_id}@example.test"},
            )
        for membership_id, person_id, account_id, role in (
            (ids[6], value.owner_a, value.account_a, "OWNER"),
            (ids[7], value.employee_a, value.account_a, "EMPLOYEE"),
            (ids[8], value.adviser_a, value.account_a, "TAX_ADVISOR"),
            (ids[9], value.owner_b, value.account_b, "OWNER"),
        ):
            connection.execute(
                text(
                    "INSERT INTO membership "
                    "(id, person_id, account_id, role, accepted_at, revoked_at) VALUES "
                    "(:id, :person, :account, :role, :accepted, NULL)"
                ),
                {
                    "id": membership_id,
                    "person": person_id,
                    "account": account_id,
                    "role": role,
                    "accepted": datetime(2026, 9, 16, tzinfo=UTC),
                },
            )
    return value


def _layout_rows(owner: Engine, account_id: str) -> list[Any]:
    with owner.connect() as connection:
        return list(
            connection.execute(
                text(
                    "SELECT id, layout_key, version, layout_snapshot, "
                    "supersedes_layout_version_id FROM investment_layout_version "
                    "WHERE account_id = :account ORDER BY layout_key, version"
                ),
                {"account": account_id},
            ).all()
        )


def test_m10_i4_f07_openapi_has_exactly_seven_investment_method_paths() -> None:
    document = create_app().openapi()
    actual = {
        path: {method for method in operations if method != "parameters"}
        for path, operations in document["paths"].items()
        if path.startswith(_PREFIX)
    }
    assert actual == _ROUTES


def test_m10_i4_f06_omitted_layout_creates_and_reuses_server_default(
    environment: tuple[TestClient, Engine], graph: _Graph
) -> None:
    client, owner = environment
    _enable(client, graph.account_a, graph.owner_a)
    first = _create(client, graph.account_a, graph.owner_a)
    second = _create(client, graph.account_a, graph.owner_a)
    assert first.status_code == second.status_code == 201

    rows = _layout_rows(owner, graph.account_a)
    assert len(rows) == 1
    row = rows[0]
    assert (row.layout_key, row.version, row.supersedes_layout_version_id) == (
        "DEFAULT_BANK",
        1,
        None,
    )
    expected = getattr(_pdf(), "DEFAULT_BANK_LAYOUT_SNAPSHOT", None)
    assert isinstance(expected, dict), "RED M10-I4: server-owned default layout is missing"
    assert row.layout_snapshot == expected
    with owner.connect() as connection:
        bound = (
            connection.execute(
                text(
                    "SELECT layout_version_id FROM investment_input_snapshot "
                    "WHERE account_id = :account ORDER BY frozen_at"
                ),
                {"account": graph.account_a},
            )
            .scalars()
            .all()
        )
    assert bound == [row.id, row.id]


def test_m10_i4_f06_defaults_are_account_isolated_and_explicit_layout_stays_exact(
    environment: tuple[TestClient, Engine], graph: _Graph
) -> None:
    client, owner = environment
    _enable(client, graph.account_a, graph.owner_a)
    _enable(client, graph.account_b, graph.owner_b)
    assert _create(client, graph.account_a, graph.owner_a).status_code == 201
    assert _create(client, graph.account_b, graph.owner_b).status_code == 201
    row_a = _layout_rows(owner, graph.account_a)[0]
    row_b = _layout_rows(owner, graph.account_b)[0]
    assert row_a.id != row_b.id
    assert row_a.layout_key == row_b.layout_key == "DEFAULT_BANK"

    explicit_id = new_id()
    with owner.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO investment_layout_version "
                "(id, account_id, layout_key, version, layout_snapshot, "
                "supersedes_layout_version_id) VALUES "
                "(:id, :account, 'CUSTOM_BANK', 1, CAST(:snapshot AS jsonb), NULL)"
            ),
            {
                "id": explicit_id,
                "account": graph.account_a,
                "snapshot": json.dumps({"schema_version": "custom-v1", "marker": "EXACT"}),
            },
        )
    created = _create(
        client,
        graph.account_a,
        graph.owner_a,
        layout_version_id=explicit_id,
    )
    assert created.status_code == 201
    with owner.connect() as connection:
        frozen = connection.scalar(
            text(
                "SELECT layout_version_id FROM investment_input_snapshot "
                "WHERE account_id = :account AND case_key = :case_key"
            ),
            {"account": graph.account_a, "case_key": created.json()["caseKey"]},
        )
    assert frozen == explicit_id


def test_m10_i4_f06_concurrent_case_creation_cannot_fork_default_layout(
    environment: tuple[TestClient, Engine], graph: _Graph
) -> None:
    client, owner = environment
    _enable(client, graph.account_a, graph.owner_a)

    def create_one() -> tuple[int, str | None]:
        with TestClient(create_app()) as isolated:
            response = _create(isolated, graph.account_a, graph.owner_a)
            return response.status_code, cast(str | None, response.json().get("caseKey"))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: create_one(), range(2)))
    assert [status for status, _case in results] == [201, 201]
    assert all(case_key for _status, case_key in results)
    rows = _layout_rows(owner, graph.account_a)
    assert [(row.layout_key, row.version) for row in rows] == [("DEFAULT_BANK", 1)]


def test_m10_i4_f07_pdf_route_requires_owner_entitlement_and_hides_case_existence(
    environment: tuple[TestClient, Engine], graph: _Graph
) -> None:
    client, _owner = environment
    _enable(client, graph.account_a, graph.owner_a)
    created = _create(client, graph.account_a, graph.owner_a)
    assert created.status_code == 201
    case_key = created.json()["caseKey"]
    path = f"/a/{graph.account_a}/investment/cases/{case_key}/bank-pdf"
    for person_id in (graph.employee_a, graph.adviser_a, graph.owner_b):
        assert client.get(path, headers=_token(person_id)).status_code == 403

    _enable(client, graph.account_b, graph.owner_b)
    foreign = client.get(
        f"/a/{graph.account_b}/investment/cases/{case_key}/bank-pdf",
        headers=_token(graph.owner_b),
    )
    missing = client.get(
        f"/a/{graph.account_b}/investment/cases/missing-case/bank-pdf",
        headers=_token(graph.owner_b),
    )
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()


def test_m10_i4_f08_pdf_uses_stored_exact_layout_and_never_recalculates(
    environment: tuple[TestClient, Engine],
    graph: _Graph,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, owner = environment
    _enable(client, graph.account_a, graph.owner_a)
    created = _create(client, graph.account_a, graph.owner_a)
    assert created.status_code == 201
    case_key = created.json()["caseKey"]
    first_layout = _layout_rows(owner, graph.account_a)[0]
    with owner.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO investment_layout_version "
                "(id, account_id, layout_key, version, layout_snapshot, "
                "supersedes_layout_version_id) VALUES "
                "(:id, :account, 'DEFAULT_BANK', 2, CAST(:snapshot AS jsonb), :previous)"
            ),
            {
                "id": new_id(),
                "account": graph.account_a,
                "snapshot": json.dumps({"schema_version": "future-v2", "marker": "MUST_NOT_FLOAT"}),
                "previous": first_layout.id,
            },
        )

    module = _api()
    captured: list[Any] = []

    def explode(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("Bank-PDF must not run the engine or resolve live rules")

    def render(data: object) -> bytes:
        captured.append(data)
        return b"%PDF-1.7\nFROZEN"

    monkeypatch.setattr(module, "calculate_investment_snapshot", explode)
    monkeypatch.setattr(module, "resolve_investment_rule_bundle", explode)
    renderer = getattr(module, "render_investment_bank_pdf", None)
    assert callable(renderer), "RED M10-I4: stored Bank-PDF renderer integration is missing"
    monkeypatch.setattr(module, "render_investment_bank_pdf", render)

    response = client.get(
        f"/a/{graph.account_a}/investment/cases/{case_key}/bank-pdf",
        headers=_token(graph.owner_a),
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert "attachment" in response.headers["content-disposition"]
    assert f"investitionsuebersicht-{case_key}.pdf" in response.headers["content-disposition"]
    assert response.content == b"%PDF-1.7\nFROZEN"
    assert len(captured) == 1
    data: Any = captured[0]
    assert data.layout_version_id == first_layout.id
    assert data.layout_snapshot == first_layout.layout_snapshot
    assert "MUST_NOT_FLOAT" not in json.dumps(data.layout_snapshot)


def test_m10_i4_f08_legacy_null_layout_returns_conflict_without_default_binding(
    environment: tuple[TestClient, Engine],
    graph: _Graph,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _owner = environment
    _enable(client, graph.account_a, graph.owner_a)
    module = _api()
    original = module._stored_case

    def legacy_case(*args: object, **kwargs: object) -> tuple[object, object]:
        stored_input, stored_result = original(*args, **kwargs)
        return SimpleNamespace(
            **{
                **stored_input.__dict__,
                "layout_version_id": None,
            }
        ), stored_result

    created = _create(client, graph.account_a, graph.owner_a)
    assert created.status_code == 201
    monkeypatch.setattr(module, "_stored_case", legacy_case)
    response = client.get(
        f"/a/{graph.account_a}/investment/cases/{created.json()['caseKey']}/bank-pdf",
        headers=_token(graph.owner_a),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Für dieses Prüfobjekt ist keine PDF-Vorlage gespeichert."
