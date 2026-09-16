"""RED M10-I3 HTTP contract from docs/14 § 4.8 (M10-INV-F03…F10)."""

from __future__ import annotations

import importlib
import os
import time
from collections.abc import Iterator, Mapping
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import jwt
import lokara_rules_store
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
_CASE_FIELDS = {
    "caseKey",
    "version",
    "resultId",
    "outcome",
    "calculatedValues",
    "kpiSlots",
    "rechtsstand",
    "productionBlocked",
    "findings",
    "warnings",
}


@dataclass(frozen=True)
class _Graph:
    account_a: str
    account_b: str
    owner_a: str
    employee_a: str
    adviser_a: str
    owner_b: str
    membership_owner_a: str


def _api() -> ModuleType:
    try:
        return importlib.import_module("lokara_api.routers.investment")
    except ModuleNotFoundError:
        pytest.fail("RED M10-I3: lokara_api.routers.investment is missing", pytrace=False)


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


def _valid_facts() -> dict[str, object]:
    return {
        "purchase_price_cents": 30_000_000,
        "acquisition_costs_cents": 3_000_000,
        "monthly_actual_rent_cents": 150_000,
        "vacancy_bp": 500,
        "administration_cents": 50_000,
        "maintenance_cents": 70_000,
        "reserve_cents": 40_000,
        "vacancy_risk_cents": 20_000,
        "equity_cents": 10_000_000,
        "loan_cents": 23_000_000,
        "interest_bp": 350,
        "initial_repayment_bp": 200,
        "marginal_tax_bp": 4_200,
        "building_share_bp": 7_500,
        "afa_rate_bp": 200,
        "analysis_period_months": 12,
        "financing_provenance": "annahme",
        "bank_header": {
            "address": "Musterweg 1, Berlin",
            "property_type": "Wohnhaus",
            "year_built": 1995,
            "area_sqm_x100": 12_000,
            "unit_count": 2,
            "creator": "Eigentümer",
            "export_date": "2026-09-16",
            "layout_version": "bank-view-v1",
        },
    }


def _case_path(account_id: str, case_key: str = "missing-case") -> str:
    return f"/a/{account_id}/investment/cases/{case_key}"


def _nested_keys(value: object) -> set[str]:
    if isinstance(value, Mapping):
        return {str(key) for key in value} | {
            nested_key for nested in value.values() for nested_key in _nested_keys(nested)
        }
    if isinstance(value, list):
        return {nested_key for nested in value for nested_key in _nested_keys(nested)}
    return set()


def _enable(client: TestClient, graph: _Graph, *, enabled: bool = True) -> dict[str, Any]:
    response = client.post(
        f"/a/{graph.account_a}/investment/entitlement",
        headers=_token(graph.owner_a),
        json={"enabled": enabled},
    )
    assert response.status_code == 201
    value = response.json()
    assert isinstance(value, dict)
    return cast(dict[str, Any], value)


def _create(client: TestClient, graph: _Graph, facts: Mapping[str, object] | None = None) -> Any:
    return client.post(
        f"/a/{graph.account_a}/investment/cases",
        headers=_token(graph.owner_a),
        json={"facts": dict(_valid_facts() if facts is None else facts)},
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
    with owner.connect() as connection:
        exists = connection.scalar(
            text("SELECT to_regclass('public.investment_entitlement_event') IS NOT NULL")
        )
    if not exists:
        pytest.fail("RED M10-I3: migration 0046 entitlement table is missing")
    client = TestClient(create_app())
    yield client, owner
    client.close()
    owner.dispose()


@pytest.fixture
def graph(environment: tuple[TestClient, Engine]) -> _Graph:
    _client, owner = environment
    ids = [new_id() for _ in range(11)]
    value = _Graph(
        account_a=ids[0],
        account_b=ids[1],
        owner_a=ids[2],
        employee_a=ids[3],
        adviser_a=ids[4],
        owner_b=ids[5],
        membership_owner_a=ids[6],
    )
    with owner.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO account (id, name, shape, plan) VALUES "
                "(:aa, 'Investment A', 'SOLO', 'TRIAL'), "
                "(:ab, 'Investment B', 'SOLO', 'TRIAL')"
            ),
            {"aa": value.account_a, "ab": value.account_b},
        )
        people = (
            value.owner_a,
            value.employee_a,
            value.adviser_a,
            value.owner_b,
        )
        for person_id in people:
            connection.execute(
                text("INSERT INTO person (id, email) VALUES (:id, :email)"),
                {"id": person_id, "email": f"{person_id}@example.test"},
            )
        for membership_id, person_id, account_id, role in (
            (value.membership_owner_a, value.owner_a, value.account_a, "OWNER"),
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


def test_m10_inv_f10_openapi_has_exact_investment_route_surface() -> None:
    document = create_app().openapi()
    actual = {
        path: {method for method in operations if method not in {"parameters"}}
        for path, operations in document["paths"].items()
        if path.startswith(_PREFIX)
    }
    assert actual == _ROUTES
    investment_document = str({path: document["paths"][path] for path in actual}).lower()
    for forbidden in (
        "renter_names",
        "rentername",
        "pricing",
        "planname",
        "purchaseflow",
        "billing",
        "stripe",
        "revenuecat",
    ):
        assert forbidden not in investment_document


def test_m10_inv_f05_server_owns_one_versioned_blocked_rule_bundle() -> None:
    resolver = getattr(lokara_rules_store, "resolve_investment_rule_bundle", None)
    assert callable(resolver), "RED M10-I3: investment rules-store resolver is missing"
    resolved = resolver(date(2026, 7, 1))
    if is_dataclass(resolved) and not isinstance(resolved, type):
        values = asdict(resolved)
    elif isinstance(resolved, Mapping):
        values = dict(resolved)
    else:
        values = {
            name: getattr(resolved, name)
            for name in (
                "default_building_share_bp",
                "default_afa_rate_bp",
                "default_marginal_tax_bp",
                "interest_sensitivity_offsets_bp",
                "repayment_sensitivity_steps_bp",
                "dscr_amber_hundredths",
                "dscr_green_hundredths",
                "cashflow_amber_cents",
                "cashflow_green_cents",
                "source_evidence",
                "rechtsstand",
                "production_blocked",
            )
        }
    assert set(values) == {
        "default_building_share_bp",
        "default_afa_rate_bp",
        "default_marginal_tax_bp",
        "interest_sensitivity_offsets_bp",
        "repayment_sensitivity_steps_bp",
        "dscr_amber_hundredths",
        "dscr_green_hundredths",
        "cashflow_amber_cents",
        "cashflow_green_cents",
        "source_evidence",
        "rechtsstand",
        "production_blocked",
    }
    assert values["rechtsstand"] == "07/2026"
    assert values["production_blocked"] is True
    assert values["source_evidence"]


def test_m10_inv_f03_only_owner_can_reach_every_investment_route(
    environment: tuple[TestClient, Engine], graph: _Graph
) -> None:
    client, _owner = environment
    calls = (
        ("get", f"/a/{graph.account_a}/investment/entitlement", None),
        ("post", f"/a/{graph.account_a}/investment/entitlement", {"enabled": True}),
        ("post", f"/a/{graph.account_a}/investment/cases", {"facts": _valid_facts()}),
        ("get", _case_path(graph.account_a), None),
        ("get", f"{_case_path(graph.account_a)}/sensitivity", None),
        ("get", f"{_case_path(graph.account_a)}/bank-view", None),
        ("get", f"{_case_path(graph.account_a)}/bank-pdf", None),
    )
    for person_id in (graph.employee_a, graph.adviser_a, graph.owner_b):
        for method, path, body in calls:
            response = client.request(method, path, headers=_token(person_id), json=body)
            assert response.status_code == 403


def test_m10_inv_f02_owner_enable_disable_appends_server_owned_versions(
    environment: tuple[TestClient, Engine], graph: _Graph
) -> None:
    client, owner = environment
    absent = client.get(
        f"/a/{graph.account_a}/investment/entitlement", headers=_token(graph.owner_a)
    )
    assert absent.status_code == 200
    assert absent.json()["enabled"] is False
    assert absent.json().get("eventId") is None
    first = _enable(client, graph)
    second = _enable(client, graph, enabled=False)
    assert first["enabled"] is True and first["version"] == 1
    assert second["enabled"] is False and second["version"] == 2
    with owner.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT version, enabled, recorded_by_membership_id, recorded_at "
                "FROM investment_entitlement_event WHERE account_id = :account "
                "ORDER BY version"
            ),
            {"account": graph.account_a},
        ).all()
    assert [(row.version, row.enabled) for row in rows] == [(1, True), (2, False)]
    assert all(row.recorded_by_membership_id == graph.membership_owner_a for row in rows)
    assert all(row.recorded_at is not None for row in rows)


@pytest.mark.parametrize("state", ("absent", "disabled"))
def test_m10_inv_f04_absent_or_disabled_entitlement_denies_every_case_route(
    environment: tuple[TestClient, Engine], graph: _Graph, state: str
) -> None:
    client, _owner = environment
    if state == "disabled":
        _enable(client, graph, enabled=False)
    for method, path, body in (
        ("post", f"/a/{graph.account_a}/investment/cases", {"facts": _valid_facts()}),
        ("get", _case_path(graph.account_a), None),
        ("get", f"{_case_path(graph.account_a)}/sensitivity", None),
        ("get", f"{_case_path(graph.account_a)}/bank-view", None),
        ("get", f"{_case_path(graph.account_a)}/bank-pdf", None),
    ):
        response = client.request(method, path, headers=_token(graph.owner_a), json=body)
        assert response.status_code == 403


def test_m10_inv_f05_f06_create_is_atomic_and_reads_only_stored_snapshots(
    environment: tuple[TestClient, Engine], graph: _Graph, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, owner = environment
    _enable(client, graph)
    created = _create(client, graph)
    assert created.status_code == 201
    body = created.json()
    assert set(body) == _CASE_FIELDS
    assert body["version"] == 1 and body["outcome"] == "calculated"
    case_key = body["caseKey"]
    with owner.connect() as connection:
        stored = connection.execute(
            text(
                "SELECT i.result_snapshot FROM investment_input_snapshot s "
                "JOIN investment_result_snapshot i ON i.input_snapshot_id = s.id "
                "AND i.account_id = s.account_id WHERE s.account_id = :account "
                "AND s.case_key = :case_key"
            ),
            {"account": graph.account_a, "case_key": case_key},
        ).one()

    module = _api()

    def explode(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("stored GET routes must not recalculate or resolve live rules")

    monkeypatch.setattr(module, "calculate_investment_snapshot", explode)
    if hasattr(module, "resolve_investment_rule_bundle"):
        monkeypatch.setattr(module, "resolve_investment_rule_bundle", explode)

    replay = client.get(_case_path(graph.account_a, case_key), headers=_token(graph.owner_a))
    assert replay.status_code == 200 and replay.json() == body
    sensitivity = client.get(
        f"{_case_path(graph.account_a, case_key)}/sensitivity",
        headers=_token(graph.owner_a),
    )
    assert sensitivity.status_code == 200
    assert set(sensitivity.json()) == {
        "interestSensitivity",
        "repaymentSensitivity",
        "repaymentAxisMeaning",
    }
    assert (
        sensitivity.json()["interestSensitivity"] == stored.result_snapshot["interest_sensitivity"]
    )
    bank = client.get(
        f"{_case_path(graph.account_a, case_key)}/bank-view", headers=_token(graph.owner_a)
    )
    assert bank.status_code == 200
    assert bank.json() == {"bankView": stored.result_snapshot["bank_view"]}
    assert _nested_keys(bank.json()).isdisjoint(
        {
            "renter",
            "renterId",
            "renterName",
            "renter_id",
            "renter_name",
            "renter_names",
            "mieter",
            "mieterId",
            "mieterName",
            "mieter_id",
            "mieter_name",
        }
    )


def test_m10_inv_f07_valid_engine_hard_block_is_persisted(
    environment: tuple[TestClient, Engine], graph: _Graph
) -> None:
    client, owner = environment
    _enable(client, graph)
    response = _create(
        client,
        graph,
        {
            "loan_cents": 34_000_000,
            "interest_bp": 390,
            "fixed_monthly_annuity_cents": 100_000,
            "financing_provenance": "annahme",
        },
    )
    assert response.status_code == 201
    assert response.json()["outcome"] == "hard_block"
    with owner.connect() as connection:
        outcome = connection.scalar(
            text(
                "SELECT r.result_snapshot ->> 'outcome' FROM investment_result_snapshot r "
                "JOIN investment_input_snapshot i ON i.id = r.input_snapshot_id "
                "AND i.account_id = r.account_id WHERE i.account_id = :account "
                "AND i.case_key = :case_key"
            ),
            {"account": graph.account_a, "case_key": response.json()["caseKey"]},
        )
    assert outcome == "hard_block"


@pytest.mark.parametrize(
    "payload",
    (
        {"facts": _valid_facts(), "rules": {}},
        {"facts": _valid_facts(), "result": {}},
        {"facts": _valid_facts(), "engineVersion": "caller"},
        {"facts": _valid_facts(), "caseKey": "caller"},
        {"facts": {**_valid_facts(), "renter_names": ["Mieter A"]}},
        {"facts": {**_valid_facts(), "purchase_price_cents": -1}},
    ),
)
def test_m10_inv_f08_invalid_or_authority_bearing_request_writes_nothing(
    environment: tuple[TestClient, Engine], graph: _Graph, payload: dict[str, object]
) -> None:
    client, owner = environment
    _enable(client, graph)
    with owner.connect() as connection:
        before = connection.scalar(
            text("SELECT count(*) FROM investment_input_snapshot WHERE account_id = :account"),
            {"account": graph.account_a},
        )
    response = client.post(
        f"/a/{graph.account_a}/investment/cases",
        headers=_token(graph.owner_a),
        json=payload,
    )
    assert response.status_code == 422
    with owner.connect() as connection:
        after = connection.scalar(
            text("SELECT count(*) FROM investment_input_snapshot WHERE account_id = :account"),
            {"account": graph.account_a},
        )
    assert after == before


def test_m10_inv_f09_foreign_and_missing_case_keys_are_identical_404(
    environment: tuple[TestClient, Engine], graph: _Graph
) -> None:
    client, _owner = environment
    _enable(client, graph)
    created = _create(client, graph)
    assert created.status_code == 201
    foreign_case = created.json()["caseKey"]
    owner_b_entitlement = client.post(
        f"/a/{graph.account_b}/investment/entitlement",
        headers=_token(graph.owner_b),
        json={"enabled": True},
    )
    assert owner_b_entitlement.status_code == 201
    foreign = client.get(_case_path(graph.account_b, foreign_case), headers=_token(graph.owner_b))
    missing = client.get(
        _case_path(graph.account_b, "does-not-exist"), headers=_token(graph.owner_b)
    )
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()
