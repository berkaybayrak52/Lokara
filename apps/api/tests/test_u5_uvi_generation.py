"""Red U5 contract for owner-only UVI generation and archived documents.

The calculation values remain owned by the source-named U1/U2/U3 fixtures.
This file pins only the application boundary that composes and archives them.
"""

from __future__ import annotations

import importlib
import inspect
import json
import os
import runpy
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, cast

import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from fastapi.testclient import TestClient
from lokara_db import DbSettings, Role, UviDeliveryEvent, UviRun, create_db_engine, new_id
from sqlalchemy import Connection, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

ACCOUNT = "{account_id}"
BUILDING = "{building_id}"
RUN = "{run_id}"

GENERATE = f"/a/{ACCOUNT}/buildings/{BUILDING}/uvi-runs"
DOCUMENT = f"/a/{ACCOUNT}/buildings/{BUILDING}/uvi-runs/{RUN}/document"

_DB_DIR = Path(__file__).resolve().parents[3] / "packages" / "db"
_ORACLE = runpy.run_path(str(_DB_DIR.parent / "rules-store/tests/berkay_uvi_golden.py"))
UVI_EXAMPLES = cast(dict[str, dict[str, object]], _ORACLE["UVI_EXAMPLES"])


def _openapi(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "u5-openapi-contract-secret-32-chars")
    api = importlib.import_module("lokara_api")
    return cast(dict[str, object], TestClient(api.create_app()).get("/openapi.json").json())


def _operations(schema: dict[str, object], path: str) -> dict[str, object]:
    paths = schema["paths"]
    assert isinstance(paths, dict)
    operations = paths[path]
    assert isinstance(operations, dict)
    return operations


def _dereference(schema: dict[str, object], value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    reference = value.get("$ref")
    if reference is None:
        return value
    assert isinstance(reference, str)
    name = reference.removeprefix("#/components/schemas/")
    components = schema["components"]
    assert isinstance(components, dict)
    schemas = components["schemas"]
    assert isinstance(schemas, dict)
    resolved = schemas[name]
    assert isinstance(resolved, dict)
    return resolved


def test_u5_owner_generation_and_archive_document_routes_are_defined(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U5-API-01: generation creates a run; retrieval addresses that exact run."""
    schema = _openapi(monkeypatch)
    generate = _operations(schema, GENERATE)
    document = _operations(schema, DOCUMENT)

    assert set(generate) >= {"post"}
    assert set(document) >= {"get"}
    post = generate["post"]
    assert isinstance(post, dict)
    assert "201" in post["responses"]

    request_body = post["requestBody"]
    assert isinstance(request_body, dict)
    content = request_body["content"]
    assert isinstance(content, dict)
    media_type = content["application/json"]
    assert isinstance(media_type, dict)
    request_schema = _dereference(schema, media_type["schema"])
    properties = request_schema["properties"]
    assert isinstance(properties, dict)
    assert set(properties) == {"tenancyId", "targetMonth"}
    required = request_schema["required"]
    assert isinstance(required, list)
    assert set(required) == {"tenancyId", "targetMonth"}

    response = post["responses"]["201"]
    assert isinstance(response, dict)
    response_content = response["content"]
    assert isinstance(response_content, dict)
    response_media = response_content["application/json"]
    assert isinstance(response_media, dict)
    response_schema = _dereference(schema, response_media["schema"])
    response_properties = response_schema["properties"]
    assert isinstance(response_properties, dict)
    assert {
        "runId",
        "documentUrl",
        "productionBlocked",
        "unresolvedConflicts",
    } <= set(response_properties)


def test_u5_contract_documents_owner_and_relationship_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U5-API-02: role and nested-resource failures are explicit HTTP outcomes."""
    schema = _openapi(monkeypatch)
    for method, path in (("post", GENERATE), ("get", DOCUMENT)):
        operation = _operations(schema, path)[method]
        assert isinstance(operation, dict)
        responses = operation["responses"]
        assert isinstance(responses, dict)
        assert {"403", "404"} <= set(responses)
    post = _operations(schema, GENERATE)["post"]
    assert isinstance(post, dict)
    responses = post["responses"]
    assert isinstance(responses, dict)
    assert "422" in responses


def test_u5_adds_no_scheduled_send_or_renter_publication_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U5-API-03: M9 delivery and M10 renter publication remain absent."""
    schema = _openapi(monkeypatch)
    paths = schema["paths"]
    assert isinstance(paths, dict)
    uvi_paths = {path for path in paths if "uvi" in path.lower()}
    assert uvi_paths == {GENERATE, DOCUMENT}
    forbidden = ("publish", "portal", "email", "send", "schedule", "deliver")
    assert not any(word in path.lower() for path in uvi_paths for word in forbidden)


def test_u5_resolves_the_named_u4b_models_and_normalized_engine_server_side() -> None:
    """U5-PREREQ: the two-field request depends on the explicit U4b symbols."""
    import lokara_uvi_engine
    from lokara_db import models

    assert getattr(models, "UviMonthlyDegreeDay", None) is not None
    assert getattr(models, "BuildingUviConfiguration", None) is not None
    assert getattr(models, "UviBuildingMonthlyEvidence", None) is not None
    assert getattr(models, "UviBuildingMonthlyEvidenceSource", None) is not None
    assert getattr(lokara_uvi_engine, "NormalizedBlockAInput", None) is not None
    assert callable(getattr(lokara_uvi_engine, "evaluate_normalized_block_a", None))


def test_u5_configuration_resolution_never_resurrects_an_expired_ancestor() -> None:
    """U5-PREREQ-02: deepest eligible successor wins before valid_to is checked."""
    module = _uvi_module()
    resolver = getattr(module, "resolve_building_uvi_configuration", None)
    assert callable(resolver), "U5 configuration resolver is missing"
    root = SimpleNamespace(
        id="config-root",
        supersedes_configuration_id=None,
        valid_from=date(2026, 1, 1),
        valid_to=None,
    )
    expired_successor = SimpleNamespace(
        id="config-successor",
        supersedes_configuration_id=root.id,
        valid_from=date(2026, 4, 1),
        valid_to=date(2026, 7, 1),
    )
    result = resolver((root, expired_successor), date(2026, 7, 1))
    assert result.selected_configuration_id == expired_successor.id
    assert result.status == "blocked"


def _uvi_module() -> ModuleType:
    try:
        return importlib.import_module("lokara_api.routers.uvi_runs")
    except ModuleNotFoundError as exc:
        pytest.fail(f"U5 production module is missing: {exc}")


def test_u5_employee_generation_is_forbidden_before_any_write() -> None:
    """U5-API-04: generation is OWNER-only, including assigned employees."""
    module = _uvi_module()
    create = getattr(module, "create_uvi_run", None)
    request_type = getattr(module, "UviRunCreate", None)
    assert callable(create), "U5 create_uvi_run endpoint is missing"
    assert request_type is not None, "U5 UviRunCreate request type is missing"

    class RefuseWrites:
        def __init__(self) -> None:
            self.info: dict[str, Any] = {
                "portal_scope": SimpleNamespace(role=Role.EMPLOYEE, building_ids=frozenset({"b-1"}))
            }

        def add(self, _row: object) -> None:
            pytest.fail("employee rejection must happen before a persistence write")

        def add_all(self, _rows: object) -> None:
            pytest.fail("employee rejection must happen before a persistence write")

    body = request_type(tenancy_id="t-1", target_month=date(2026, 7, 1))
    with pytest.raises(HTTPException) as refused:
        create("a-1", "b-1", body, RefuseWrites())
    assert refused.value.status_code == 403


def test_u5_router_preserves_immutable_generation_and_archive_boundaries() -> None:
    """U5-API-05: one run/event per attempt; document reads the frozen run only."""
    module = _uvi_module()
    source = inspect.getsource(module)

    # The endpoint must use the established nested authorization checks and U4
    # records. A generated event belongs to the same transaction as its run.
    for marker in (
        "require_owner",
        "require_building",
        "UviRun",
        "UviDeliveryEvent",
        '"GENERATED"',
        "uvi_document_html",
    ):
        assert marker in source, f"U5 router is missing {marker}"

    # A retry is an INSERT path. The immutable U4 evidence is never updated or
    # deleted by generation, and retrieval never calls a live evaluator.
    assert ".update(" not in source
    assert ".delete(" not in source
    document = getattr(module, "download_uvi_document", None)
    assert callable(document), "U5 archived document endpoint is missing"
    document_source = inspect.getsource(document)
    assert "UviRun" in document_source
    assert "uvi_document_html" in document_source
    assert "evaluate_block_" not in document_source


class _LiveU5:
    def __init__(
        self,
        client: TestClient,
        connection: Connection,
        ids: dict[str, str],
        rendered_html: list[str],
    ) -> None:
        self.client = client
        self.connection = connection
        self.ids = ids
        self.rendered_html = rendered_html

    @property
    def generate_path(self) -> str:
        return GENERATE.format(
            account_id=self.ids["account"],
            building_id=self.ids["building"],
        )

    def document_path(self, run_id: str) -> str:
        return DOCUMENT.format(
            account_id=self.ids["account"],
            building_id=self.ids["building"],
            run_id=run_id,
        )


def _seed_u5_graph(
    connection: Connection,
    *,
    missing: str | None,
    block_d_ready: bool = False,
) -> dict[str, str]:
    block_a = UVI_EXAMPLES["emir_spec_block_a_kwh"]
    block_b = UVI_EXAMPLES["emir_spec_block_b_previous_month"]
    block_c = UVI_EXAMPLES["emir_spec_block_c_weather_adjusted"]
    block_d2 = UVI_EXAMPLES["approved_block_d2_heat_only"]
    ids = {
        name: new_id()
        for name in (
            "account",
            "person",
            "membership",
            "building",
            "unit",
            "tenancy",
            "renter",
            "tenancy_party",
            "foreign_building",
            "foreign_unit",
            "foreign_tenancy",
            "meter",
            "raw_target",
            "raw_previous",
            "raw_prior_year",
            "monthly_target",
            "monthly_previous",
            "monthly_prior_year",
            "source_target",
            "source_previous",
            "source_prior_year",
            "station_target",
            "station_prior_year",
            "degree_target",
            "degree_prior_year",
            "configuration",
            "comparable_unit_1",
            "comparable_unit_2",
            "comparable_tenancy_1",
            "comparable_tenancy_2",
            "comparable_meter_1",
            "comparable_meter_2",
            "comparable_raw_1",
            "comparable_raw_2",
            "comparable_monthly_1",
            "comparable_monthly_2",
            "comparable_source_1",
            "comparable_source_2",
        )
    }
    connection.execute(
        text("INSERT INTO person (id, email) VALUES (:person, :email)"),
        {**ids, "email": f"u5-{ids['person']}@lokara.example"},
    )
    connection.execute(
        text(
            "INSERT INTO account (id, name, shape, plan)"
            " VALUES (:account, 'U5 Integrationskonto', 'SOLO', 'TRIAL')"
        ),
        ids,
    )
    connection.execute(
        text(
            "INSERT INTO membership (id, person_id, account_id, role, accepted_at)"
            " VALUES (:membership, :person, :account, 'OWNER', now())"
        ),
        ids,
    )
    connection.execute(
        text(
            "INSERT INTO building (id, account_id, name, street, postal_code, city) VALUES"
            " (:building, :account, 'U5 Haus', 'UVI-Weg 1', '10115', 'Berlin'),"
            " (:foreign_building, :account, 'Fremdes U5 Haus', 'UVI-Weg 2', '10115',"
            " 'Berlin')"
        ),
        ids,
    )
    connection.execute(
        text(
            "INSERT INTO unit (id, account_id, building_id, label, area_sqm_x100) VALUES"
            " (:unit, :account, :building, 'U5 Wohnung', :target_area),"
            " (:foreign_unit, :account, :foreign_building, 'Andere Wohnung', 8000)"
        ),
        {**ids, "target_area": 8000 if block_d_ready else 30000},
    )
    connection.execute(
        text(
            "INSERT INTO tenancy"
            " (id, account_id, unit_id, valid_from, valid_to, base_rent_cents) VALUES"
            " (:tenancy, :account, :unit, '2025-01-01', NULL, 100000),"
            " (:foreign_tenancy, :account, :foreign_unit, '2025-01-01', NULL, 100000)"
        ),
        ids,
    )
    connection.execute(
        text(
            "INSERT INTO renter (id, account_id, legal_name, email, person_id)"
            " VALUES (:renter, :account, 'U5 Mieter', 'u5-renter@example.test', NULL)"
        ),
        ids,
    )
    connection.execute(
        text(
            "INSERT INTO tenancy_party (id, account_id, tenancy_id, renter_id)"
            " VALUES (:tenancy_party, :account, :tenancy, :renter)"
        ),
        ids,
    )
    connection.execute(
        text(
            "INSERT INTO meter"
            " (id, account_id, building_id, unit_id, kind, measurement_unit, serial,"
            " calibration_valid_until, valuation_factor_x1000) VALUES"
            " (:meter, :account, :building, :unit, 'HEAT', 'KWH', :serial,"
            " '2029-12-31', 1000)"
        ),
        {**ids, "serial": f"U5-{ids['meter']}"},
    )

    if block_d_ready:
        block_d = UVI_EXAMPLES["emir_spec_block_d_building_cross_section"]
        comparables = cast(tuple[dict[str, object], ...], block_d["comparables"])
        for index, comparable in enumerate(comparables, start=1):
            suffix = str(index)
            unit_id = ids[f"comparable_unit_{suffix}"]
            tenancy_id = ids[f"comparable_tenancy_{suffix}"]
            meter_id = ids[f"comparable_meter_{suffix}"]
            raw_id = ids[f"comparable_raw_{suffix}"]
            monthly_id = ids[f"comparable_monthly_{suffix}"]
            source_id = ids[f"comparable_source_{suffix}"]
            kwh = cast(int, comparable["kwh"])
            connection.execute(
                text(
                    "INSERT INTO unit"
                    " (id, account_id, building_id, label, area_sqm_x100) VALUES"
                    " (:unit, :account, :building, :label, :area)"
                ),
                {
                    **ids,
                    "unit": unit_id,
                    "label": f"U5 Vergleich {suffix}",
                    "area": cast(int, comparable["area_sqm"]) * 100,
                },
            )
            connection.execute(
                text(
                    "INSERT INTO tenancy"
                    " (id, account_id, unit_id, valid_from, valid_to, base_rent_cents)"
                    " VALUES (:tenancy, :account, :unit, '2025-01-01', NULL, 100000)"
                ),
                {**ids, "tenancy": tenancy_id, "unit": unit_id},
            )
            connection.execute(
                text(
                    "INSERT INTO meter"
                    " (id, account_id, building_id, unit_id, kind, measurement_unit, serial,"
                    " calibration_valid_until, valuation_factor_x1000) VALUES"
                    " (:meter, :account, :building, :unit, 'HEAT', 'KWH', :serial,"
                    " '2029-12-31', 1000)"
                ),
                {
                    **ids,
                    "meter": meter_id,
                    "unit": unit_id,
                    "serial": f"U5-C{suffix}-{meter_id}",
                },
            )
            connection.execute(
                text(
                    "INSERT INTO meter_reading"
                    " (id, account_id, meter_id, read_at, value_x1000, reason, source)"
                    " VALUES (:raw, :account, :meter, '2026-07-01', :value,"
                    " 'PERIODIC', 'MANUAL')"
                ),
                {**ids, "raw": raw_id, "meter": meter_id, "value": kwh * 1000},
            )
            connection.execute(
                text(
                    "INSERT INTO monthly_meter_reading"
                    " (id, account_id, meter_id, tenancy_id, unit_id, month,"
                    " consumption_x1000, reason, source, interpolation_method,"
                    " supersedes_reading_id) VALUES"
                    " (:monthly, :account, :meter, :tenancy, :unit, '2026-07-01', :value,"
                    " 'PERIODIC', 'MANUAL', 'source-backed-u5-comparable', NULL)"
                ),
                {
                    **ids,
                    "monthly": monthly_id,
                    "meter": meter_id,
                    "tenancy": tenancy_id,
                    "unit": unit_id,
                    "value": kwh * 1000,
                },
            )
            connection.execute(
                text(
                    "INSERT INTO monthly_meter_reading_source"
                    " (id, account_id, monthly_meter_reading_id, meter_reading_id)"
                    " VALUES (:source, :account, :monthly, :raw)"
                ),
                {**ids, "source": source_id, "monthly": monthly_id, "raw": raw_id},
            )

    month_rows = (
        (
            "target",
            date(2026, 7, 1),
            cast(int, block_a["result_kwh"]),
            ids["raw_target"],
            ids["monthly_target"],
            ids["source_target"],
        ),
        (
            "previous",
            date(2026, 6, 1),
            cast(int, block_b["previous_kwh"]),
            ids["raw_previous"],
            ids["monthly_previous"],
            ids["source_previous"],
        ),
        (
            "prior_year",
            date(2025, 7, 1),
            cast(int, block_c["previous_year_kwh"]),
            ids["raw_prior_year"],
            ids["monthly_prior_year"],
            ids["source_prior_year"],
        ),
    )
    for name, month, kwh, raw_id, monthly_id, source_id in month_rows:
        if missing == "reading" and name == "target":
            continue
        connection.execute(
            text(
                "INSERT INTO meter_reading"
                " (id, account_id, meter_id, read_at, value_x1000, reason, source)"
                " VALUES (:id, :account, :meter, :month, :value, 'PERIODIC', 'MANUAL')"
            ),
            {**ids, "id": raw_id, "month": month, "value": kwh * 1000},
        )
        connection.execute(
            text(
                "INSERT INTO monthly_meter_reading"
                " (id, account_id, meter_id, tenancy_id, unit_id, month, consumption_x1000,"
                " reason, source, interpolation_method, supersedes_reading_id) VALUES"
                " (:id, :account, :meter, :tenancy, :unit, :month, :value, 'PERIODIC',"
                " 'MANUAL', 'source-backed-u5-fixture', NULL)"
            ),
            {**ids, "id": monthly_id, "month": month, "value": kwh * 1000},
        )
        connection.execute(
            text(
                "INSERT INTO monthly_meter_reading_source"
                " (id, account_id, monthly_meter_reading_id, meter_reading_id)"
                " VALUES (:id, :account, :monthly, :raw)"
            ),
            {**ids, "id": source_id, "monthly": monthly_id, "raw": raw_id},
        )

    station_rows = (
        (
            ids["station_target"],
            ids["degree_target"],
            date(2026, 7, 1),
            Decimal(str(block_c["degree_days_current"])),
            None if missing == "share" else Decimal(str(block_d2["degree_day_share"])),
            "target",
        ),
        (
            ids["station_prior_year"],
            ids["degree_prior_year"],
            date(2025, 7, 1),
            Decimal(str(block_c["degree_days_previous_year"])),
            None,
            "prior-year",
        ),
    )
    for assignment_id, degree_id, month, degree_days, annual_share, suffix in station_rows:
        connection.execute(
            text(
                "INSERT INTO uvi_station_assignment"
                " (id, account_id, postal_code, month, station_id, distance_km,"
                " source_type, source_id) VALUES"
                " (:id, :account, '10115', :month, :station, 12.345, 'DWD_MONTHLY',"
                " :source_id)"
            ),
            {
                **ids,
                "id": assignment_id,
                "month": month,
                "station": f"U5-{suffix}",
                "source_id": f"DWD-assignment-{ids['account']}-{suffix}",
            },
        )
        if missing == "degree" and suffix == "target":
            continue
        connection.execute(
            text(
                "INSERT INTO uvi_monthly_degree_day"
                " (id, account_id, station_assignment_id, station_id, month,"
                " monthly_degree_days, valid_day_count, source_file, source_id, provenance,"
                " rechtsstand, verification_status, monthly_annual_share,"
                " supersedes_degree_day_id) VALUES"
                " (:id, :account, :assignment, :station, :month, :degree_days, 31,"
                " :source_file, :source_id, CAST(:provenance AS jsonb), '08/2026',"
                " 'verify-before-production', :annual_share, NULL)"
            ),
            {
                **ids,
                "id": degree_id,
                "assignment": assignment_id,
                "station": f"U5-{suffix}",
                "month": month,
                "degree_days": degree_days,
                "source_file": f"DWD-{suffix}.csv",
                "source_id": f"DWD-degree-{ids['account']}-{suffix}",
                "provenance": json.dumps({"source": "DWD", "fixture": suffix}),
                "annual_share": annual_share,
            },
        )

    if missing != "config":
        connection.execute(
            text(
                "INSERT INTO building_uvi_configuration"
                " (id, account_id, building_id, energy_source, energy_reference,"
                " explicit_hkv_allocator, calorific_factor, valid_from, valid_to, source_type,"
                " source_id,"
                " rechtsstand, verification_status, supersedes_configuration_id) VALUES"
                " (:configuration, :account, :building, 'Erdgas', 'HO', false, NULL,"
                " '2025-01-01', NULL, 'UVI_CONFIGURATION', :source_id, '08/2026',"
                " 'verify-before-production', NULL)"
            ),
            {**ids, "source_id": f"U5-config-{ids['account']}"},
        )
    return ids


@contextmanager
def _live_u5_graph(
    monkeypatch: pytest.MonkeyPatch,
    *,
    missing: str | None = None,
    block_d_ready: bool = False,
) -> Iterator[_LiveU5]:
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "u5-live-contract-secret-32-chars")
    settings = DbSettings()
    try:
        owner = create_db_engine(settings.direct_url)
        with owner.connect() as init_connection:
            init_connection.execute(text((_DB_DIR / "scripts/init-app-role.sql").read_text()))
            init_connection.commit()
    except OperationalError as exc:
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")
    command.upgrade(Config(str(_DB_DIR / "alembic.ini")), "head")
    connection = owner.connect()
    transaction = connection.begin()
    app: Any = None
    try:
        ids = _seed_u5_graph(connection, missing=missing, block_d_ready=block_d_ready)
        from lokara_api import create_app
        from lokara_api.authorization import PortalScope
        from lokara_api.deps import account_session_for_path

        module = importlib.import_module("lokara_api.routers.uvi_runs")
        rendered_html: list[str] = []

        def fake_render_html_to_pdf(html: str) -> bytes:
            rendered_html.append(html)
            return b"%PDF-1.7\nU5 archived fixture\n"

        monkeypatch.setattr(module, "render_html_to_pdf", fake_render_html_to_pdf)
        app = create_app()

        def owner_session(account_id: str) -> Iterator[Session]:
            assert account_id == ids["account"]
            with (
                Session(bind=connection, join_transaction_mode="create_savepoint") as session,
                session.begin(),
            ):
                session.info["portal_scope"] = PortalScope(
                    role=Role.OWNER,
                    building_ids=frozenset(),
                    membership_id=ids["membership"],
                )
                yield session

        app.dependency_overrides[account_session_for_path] = owner_session
        with TestClient(app) as client:
            yield _LiveU5(client, connection, ids, rendered_html)
    finally:
        if app is not None:
            app.dependency_overrides.clear()
        transaction.rollback()
        connection.close()
        owner.dispose()


def _archive_rows(live: _LiveU5) -> tuple[list[UviRun], list[UviDeliveryEvent]]:
    with Session(bind=live.connection, join_transaction_mode="create_savepoint") as session:
        runs = list(
            session.scalars(
                select(UviRun)
                .where(UviRun.account_id == live.ids["account"])
                .order_by(UviRun.created_at, UviRun.id)
            )
        )
        events = list(
            session.scalars(
                select(UviDeliveryEvent)
                .where(UviDeliveryEvent.account_id == live.ids["account"])
                .order_by(UviDeliveryEvent.occurred_at, UviDeliveryEvent.id)
            )
        )
        for row in (*runs, *events):
            session.expunge(row)
    return runs, events


def _post_generation(live: _LiveU5, tenancy_id: str | None = None) -> Any:
    return live.client.post(
        live.generate_path,
        json={
            "tenancyId": tenancy_id or live.ids["tenancy"],
            "targetMonth": "2026-07-01",
        },
    )


def _insert_later_corrections(live: _LiveU5) -> None:
    raw_id = new_id()
    monthly_id = new_id()
    live.connection.execute(
        text(
            "INSERT INTO meter_reading"
            " (id, account_id, meter_id, read_at, value_x1000, reason, source)"
            " VALUES (:raw, :account, :meter, '2026-07-31', 999000,"
            " 'CORRECTION', 'MANUAL')"
        ),
        {**live.ids, "raw": raw_id},
    )
    live.connection.execute(
        text(
            "INSERT INTO monthly_meter_reading"
            " (id, account_id, meter_id, tenancy_id, unit_id, month, consumption_x1000,"
            " reason, source, interpolation_method, supersedes_reading_id) VALUES"
            " (:monthly, :account, :meter, :tenancy, :unit, '2026-07-01', 999000,"
            " 'CORRECTION', 'MANUAL', 'later-correction', :monthly_target)"
        ),
        {**live.ids, "monthly": monthly_id},
    )
    live.connection.execute(
        text(
            "INSERT INTO monthly_meter_reading_source"
            " (id, account_id, monthly_meter_reading_id, meter_reading_id)"
            " VALUES (:id, :account, :monthly, :raw)"
        ),
        {**live.ids, "id": new_id(), "monthly": monthly_id, "raw": raw_id},
    )
    live.connection.execute(
        text(
            "INSERT INTO uvi_monthly_degree_day"
            " (id, account_id, station_assignment_id, station_id, month,"
            " monthly_degree_days, valid_day_count, source_file, source_id, provenance,"
            " rechtsstand, verification_status, monthly_annual_share,"
            " supersedes_degree_day_id) VALUES"
            " (:id, :account, :station_target, 'U5-target', '2026-07-01', 999, 31,"
            " 'DWD-later.csv', :source_id, '{\"source\":\"later\"}'::jsonb, '08/2026',"
            " 'verify-before-production', 0.20, :degree_target)"
        ),
        {
            **live.ids,
            "id": new_id(),
            "source_id": f"DWD-later-{new_id()}",
        },
    )


def _insert_equivalent_comparable_source_correction(live: _LiveU5) -> None:
    """Change only one comparable's archived evidence identity, not its heat value."""
    raw_id = new_id()
    monthly_id = new_id()
    live.connection.execute(
        text(
            "INSERT INTO meter_reading"
            " (id, account_id, meter_id, read_at, value_x1000, reason, source) VALUES"
            " (:raw, :account, :meter, '2026-07-31', 1300000, 'CORRECTION', 'MANUAL')"
        ),
        {**live.ids, "raw": raw_id, "meter": live.ids["comparable_meter_1"]},
    )
    live.connection.execute(
        text(
            "INSERT INTO monthly_meter_reading"
            " (id, account_id, meter_id, tenancy_id, unit_id, month, consumption_x1000,"
            " reason, source, interpolation_method, supersedes_reading_id) VALUES"
            " (:monthly, :account, :meter, :tenancy, :unit, '2026-07-01', 1300000,"
            " 'CORRECTION', 'MANUAL', 'equivalent-source-correction', :predecessor)"
        ),
        {
            **live.ids,
            "monthly": monthly_id,
            "meter": live.ids["comparable_meter_1"],
            "tenancy": live.ids["comparable_tenancy_1"],
            "unit": live.ids["comparable_unit_1"],
            "predecessor": live.ids["comparable_monthly_1"],
        },
    )
    live.connection.execute(
        text(
            "INSERT INTO monthly_meter_reading_source"
            " (id, account_id, monthly_meter_reading_id, meter_reading_id)"
            " VALUES (:source, :account, :monthly, :raw)"
        ),
        {**live.ids, "source": new_id(), "monthly": monthly_id, "raw": raw_id},
    )


def _insert_interpolated_target_correction(live: _LiveU5) -> None:
    """Select an otherwise equivalent target month with the internal interpolation marker."""
    raw_id = new_id()
    monthly_id = new_id()
    live.connection.execute(
        text(
            "INSERT INTO meter_reading"
            " (id, account_id, meter_id, read_at, value_x1000, reason, source)"
            " VALUES (:raw, :account, :meter, '2026-07-31', 900000,"
            " 'CORRECTION', 'MANUAL')"
        ),
        {**live.ids, "raw": raw_id},
    )
    live.connection.execute(
        text(
            "INSERT INTO monthly_meter_reading"
            " (id, account_id, meter_id, tenancy_id, unit_id, month, consumption_x1000,"
            " reason, source, interpolation_method, supersedes_reading_id) VALUES"
            " (:monthly, :account, :meter, :tenancy, :unit, '2026-07-01', 900000,"
            " 'CORRECTION', 'MANUAL', 'linear_by_elapsed_days', :monthly_target)"
        ),
        {**live.ids, "monthly": monthly_id},
    )
    live.connection.execute(
        text(
            "INSERT INTO monthly_meter_reading_source"
            " (id, account_id, monthly_meter_reading_id, meter_reading_id)"
            " VALUES (:source, :account, :monthly, :raw)"
        ),
        {**live.ids, "source": new_id(), "monthly": monthly_id, "raw": raw_id},
    )


def _insert_water_distractors(live: _LiveU5) -> None:
    """Add same-month water rows that must never enter a heat UVI."""
    for suffix, unit_id, tenancy_id in (
        ("target", live.ids["unit"], live.ids["tenancy"]),
        (
            "comparable",
            live.ids["comparable_unit_1"],
            live.ids["comparable_tenancy_1"],
        ),
    ):
        meter_id = new_id()
        raw_id = new_id()
        monthly_id = new_id()
        live.ids[f"water_meter_{suffix}"] = meter_id
        live.connection.execute(
            text(
                "INSERT INTO meter"
                " (id, account_id, building_id, unit_id, kind, measurement_unit, serial,"
                " calibration_valid_until, valuation_factor_x1000) VALUES"
                " (:meter, :account, :building, :unit, 'COLD_WATER', 'CUBIC_METRE', :serial,"
                " '2032-12-31', NULL)"
            ),
            {
                **live.ids,
                "meter": meter_id,
                "unit": unit_id,
                "serial": f"U5-WATER-{suffix}-{meter_id}",
            },
        )
        live.connection.execute(
            text(
                "INSERT INTO meter_reading"
                " (id, account_id, meter_id, read_at, value_x1000, reason, source)"
                " VALUES (:raw, :account, :meter, '2026-07-01', 777000,"
                " 'PERIODIC', 'MANUAL')"
            ),
            {**live.ids, "raw": raw_id, "meter": meter_id},
        )
        live.connection.execute(
            text(
                "INSERT INTO monthly_meter_reading"
                " (id, account_id, meter_id, tenancy_id, unit_id, month, consumption_x1000,"
                " reason, source, interpolation_method, supersedes_reading_id) VALUES"
                " (:monthly, :account, :meter, :tenancy, :unit, '2026-07-01', 777000,"
                " 'PERIODIC', 'MANUAL', 'water-distractor', NULL)"
            ),
            {
                **live.ids,
                "monthly": monthly_id,
                "meter": meter_id,
                "tenancy": tenancy_id,
                "unit": unit_id,
            },
        )
        live.connection.execute(
            text(
                "INSERT INTO monthly_meter_reading_source"
                " (id, account_id, monthly_meter_reading_id, meter_reading_id)"
                " VALUES (:source, :account, :monthly, :raw)"
            ),
            {**live.ids, "source": new_id(), "monthly": monthly_id, "raw": raw_id},
        )


def _insert_three_month_configurations(live: _LiveU5) -> None:
    """Persist distinct compatible conversion rules for the three compared months."""
    configurations = (
        ("prior_year", date(2025, 1, 1), Decimal("1"), None),
        ("previous", date(2026, 6, 1), Decimal("2"), "prior_year"),
        ("target", date(2026, 7, 1), Decimal("3"), "previous"),
    )
    for suffix, valid_from, factor, predecessor_suffix in configurations:
        configuration_id = new_id()
        live.ids[f"configuration_{suffix}"] = configuration_id
        predecessor_id = (
            None if predecessor_suffix is None else live.ids[f"configuration_{predecessor_suffix}"]
        )
        live.connection.execute(
            text(
                "INSERT INTO building_uvi_configuration"
                " (id, account_id, building_id, energy_source, energy_reference,"
                " explicit_hkv_allocator, calorific_factor, valid_from, valid_to, source_type,"
                " source_id,"
                " rechtsstand, verification_status, supersedes_configuration_id) VALUES"
                " (:id, :account, :building, 'Erdgas', 'HO', false, :factor, :valid_from, NULL,"
                " 'UVI_CONFIGURATION', :source_id, '08/2026', 'verify-before-production',"
                " :predecessor)"
            ),
            {
                **live.ids,
                "id": configuration_id,
                "factor": factor,
                "valid_from": valid_from,
                "source_id": f"U5-config-{suffix}-{live.ids['account']}",
                "predecessor": predecessor_id,
            },
        )
    live.connection.execute(
        text("UPDATE meter SET measurement_unit = 'CUBIC_METRE' WHERE id = :meter"),
        live.ids,
    )


def _insert_building_evidence_with_two_sources(live: _LiveU5) -> list[dict[str, str]]:
    """Insert one selected target-month parent with two deliberately unordered links."""
    live.ids.update(
        {
            "building_main_meter": new_id(),
            "building_raw_1": new_id(),
            "building_raw_2": new_id(),
            "building_evidence": new_id(),
            "building_evidence_link_1": new_id(),
            "building_evidence_link_2": new_id(),
        }
    )
    live.connection.execute(
        text(
            "INSERT INTO meter"
            " (id, account_id, building_id, unit_id, kind, measurement_unit, serial,"
            " calibration_valid_until, valuation_factor_x1000) VALUES"
            " (:building_main_meter, :account, :building, NULL, 'HEAT', 'KWH', :serial,"
            " '2029-12-31', 1000)"
        ),
        {**live.ids, "serial": f"U5-MAIN-{live.ids['building_main_meter']}"},
    )
    for index, read_at, value in (
        (1, date(2026, 7, 1), 1000000),
        (2, date(2026, 7, 31), 4000000),
    ):
        live.connection.execute(
            text(
                "INSERT INTO meter_reading"
                " (id, account_id, meter_id, read_at, value_x1000, reason, source)"
                " VALUES (:raw, :account, :building_main_meter, :read_at, :value,"
                " 'PERIODIC', 'MANUAL')"
            ),
            {
                **live.ids,
                "raw": live.ids[f"building_raw_{index}"],
                "read_at": read_at,
                "value": value,
            },
        )
    live.connection.execute(
        text(
            "INSERT INTO uvi_building_monthly_evidence"
            " (id, account_id, building_id, main_meter_id, month,"
            " measured_building_heat_kwh_x1000, building_hkv_movement_x1000, source_type,"
            " source_id, raw_evidence, supersedes_evidence_id) VALUES"
            " (:building_evidence, :account, :building, :building_main_meter, '2026-07-01',"
            " 3000000, NULL, 'UVI_BUILDING_EVIDENCE', 'U5-building-evidence-target',"
            ' \'{"method":"meter-delta"}\'::jsonb, NULL)'
        ),
        live.ids,
    )
    expected = sorted(
        (
            {
                "id": live.ids["building_evidence_link_1"],
                "meter_reading_id": live.ids["building_raw_1"],
            },
            {
                "id": live.ids["building_evidence_link_2"],
                "meter_reading_id": live.ids["building_raw_2"],
            },
        ),
        key=lambda item: item["id"],
    )
    for link in reversed(expected):
        live.connection.execute(
            text(
                "INSERT INTO uvi_building_monthly_evidence_source"
                " (id, account_id, building_monthly_evidence_id, main_meter_id,"
                " meter_reading_id) VALUES"
                " (:id, :account, :building_evidence, :building_main_meter, :reading)"
            ),
            {**live.ids, "id": link["id"], "reading": link["meter_reading_id"]},
        )
    return expected


def test_u5_database_generation_archives_exact_inputs_results_and_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U5-DB-01: POST atomically archives one immutable run and GENERATED event."""
    with _live_u5_graph(monkeypatch) as live:
        response = _post_generation(live)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["productionBlocked"] is True
        assert body["unresolvedConflicts"]
        assert body["documentUrl"] == live.document_path(body["runId"])

        runs, events = _archive_rows(live)
        assert len(runs) == len(events) == 1
        first = runs[0]
        assert events[0].uvi_run_id == first.id
        assert events[0].status == "GENERATED"
        assert first.id == body["runId"]
        assert first.tenancy_id == live.ids["tenancy"]
        assert first.unit_id == live.ids["unit"]
        assert first.month == date(2026, 7, 1)
        assert first.station_assignment_id == live.ids["station_target"]
        assert first.station_id == "U5-target"
        assert first.station_distance_km == Decimal("12.345")
        assert first.source_type == "DWD_MONTHLY"
        assert first.source_id == f"DWD-assignment-{live.ids['account']}-target"
        assert first.heizspiegel_vintage == "2025/billing-year-2024"
        assert len(first.sha256) == 64
        assert first.inputs and first.results

        block_a = UVI_EXAMPLES["emir_spec_block_a_kwh"]
        block_b = UVI_EXAMPLES["emir_spec_block_b_previous_month"]
        block_c = UVI_EXAMPLES["emir_spec_block_c_weather_adjusted"]
        block_d2 = UVI_EXAMPLES["approved_block_d2_heat_only"]
        assert first.inputs["monthly_movements_x1000"] == {
            "target": cast(int, block_a["result_kwh"]) * 1000,
            "previous": cast(int, block_b["previous_kwh"]) * 1000,
            "prior_year": cast(int, block_c["previous_year_kwh"]) * 1000,
        }
        assert first.inputs["monthly_reading_ids"] == {
            "target": live.ids["monthly_target"],
            "previous": live.ids["monthly_previous"],
            "prior_year": live.ids["monthly_prior_year"],
        }
        assert first.inputs["raw_reading_ids"] == {
            "target": [live.ids["raw_target"]],
            "previous": [live.ids["raw_previous"]],
            "prior_year": [live.ids["raw_prior_year"]],
        }
        assert first.inputs["degree_days"] == {
            "target": str(block_c["degree_days_current"]),
            "prior_year": str(block_c["degree_days_previous_year"]),
            "target_annual_share": str(block_d2["degree_day_share"]),
        }
        assert first.inputs["building_configuration_id"] == live.ids["configuration"]
        assert first.inputs["building_configuration"] == {
            "energy_source": "Erdgas",
            "energy_reference": "HO",
            "explicit_hkv_allocator": False,
            "calorific_factor": None,
            "source_type": "UVI_CONFIGURATION",
            "source_id": f"U5-config-{live.ids['account']}",
            "rechtsstand": "08/2026",
            "verification_status": "verify-before-production",
        }
        assert first.inputs["station_assignment_ids"] == {
            "target": live.ids["station_target"],
            "prior_year": live.ids["station_prior_year"],
        }
        assert first.inputs["target_unit"] == {
            "unit_id": live.ids["unit"],
            "area_sqm_x100": 30000,
        }
        assert first.inputs["target_meter"] == {
            "meter_id": live.ids["meter"],
            "kind": "HEAT",
            "measurement_unit": "KWH",
        }
        assert first.inputs["comparables"] == []
        assert first.inputs["degree_day_rows"] == {
            "target": {
                "id": live.ids["degree_target"],
                "station_assignment_id": live.ids["station_target"],
                "station_id": "U5-target",
                "month": "2026-07-01",
                "monthly_degree_days": str(block_c["degree_days_current"]),
                "valid_day_count": 31,
                "monthly_annual_share": str(block_d2["degree_day_share"]),
                "source_file": "DWD-target.csv",
                "source_id": f"DWD-degree-{live.ids['account']}-target",
                "provenance": {"source": "DWD", "fixture": "target"},
                "rechtsstand": "08/2026",
                "verification_status": "verify-before-production",
            },
            "prior_year": {
                "id": live.ids["degree_prior_year"],
                "station_assignment_id": live.ids["station_prior_year"],
                "station_id": "U5-prior-year",
                "month": "2025-07-01",
                "monthly_degree_days": str(block_c["degree_days_previous_year"]),
                "valid_day_count": 31,
                "monthly_annual_share": None,
                "source_file": "DWD-prior-year.csv",
                "source_id": f"DWD-degree-{live.ids['account']}-prior-year",
                "provenance": {"source": "DWD", "fixture": "prior-year"},
                "rechtsstand": "08/2026",
                "verification_status": "verify-before-production",
            },
        }
        assert first.inputs["station_assignments"] == {
            "target": {
                "id": live.ids["station_target"],
                "station_id": "U5-target",
                "distance_km": "12.345",
                "source_type": "DWD_MONTHLY",
                "source_id": f"DWD-assignment-{live.ids['account']}-target",
            },
            "prior_year": {
                "id": live.ids["station_prior_year"],
                "station_id": "U5-prior-year",
                "distance_km": "12.345",
                "source_type": "DWD_MONTHLY",
                "source_id": f"DWD-assignment-{live.ids['account']}-prior-year",
            },
        }
        assert first.inputs["normalized_block_inputs"] == {
            "block_a": {
                "monthly_movement_x1000": cast(int, block_a["result_kwh"]) * 1000,
                "measurement_unit": "KWH",
                "energy_reference": "HO",
                "calorific_factor": None,
                "explicit_hkv_allocator": False,
                "measured_building_heat_kwh_x1000": None,
                "building_hkv_movement_x1000": None,
            },
            "block_b": {
                "current_heat_kwh": cast(int, block_a["result_kwh"]),
                "previous_heat_kwh": cast(int, block_b["previous_kwh"]),
            },
            "block_c": {
                "current_heat_kwh": cast(int, block_a["result_kwh"]),
                "prior_year_heat_kwh": cast(int, block_c["previous_year_kwh"]),
                "target_degree_day_id": live.ids["degree_target"],
                "prior_year_degree_day_id": live.ids["degree_prior_year"],
                "target_degree_days": str(block_c["degree_days_current"]),
                "prior_year_degree_days": str(block_c["degree_days_previous_year"]),
            },
            "block_d": {
                "target_area_sqm_x100": 30000,
                "target_heat_kwh": cast(int, block_a["result_kwh"]),
                "comparable_reading_ids": [],
                "minimum_valid_units_including_target": 3,
            },
            "block_d2": {
                "configuration_id": live.ids["configuration"],
                "degree_day_id": live.ids["degree_target"],
                "target_area_sqm_x100": 30000,
                "current_heat_kwh": cast(int, block_a["result_kwh"]),
                "monthly_annual_share": str(block_d2["degree_day_share"]),
                "heizspiegel_mittel_kwh_m2a": block_d2["heizspiegel_mittel_kwh_m2a"],
                "warm_water_deduction_kwh_m2a": block_d2["warm_water_deduction_kwh_m2a"],
            },
        }
        assert first.inputs["resolved_u2"] == {
            "configuration_id": live.ids["configuration"],
            "energy_source": "Erdgas",
            "energy_reference": "HO",
            "source_type": "UVI_CONFIGURATION",
            "source_id": f"U5-config-{live.ids['account']}",
            "heizspiegel_vintage": "2025/billing-year-2024",
            "size_class": "250-500",
            "heizspiegel_row": {
                "middle_kwh_m2a": block_d2["heizspiegel_mittel_kwh_m2a"],
                "warm_water_deduction_kwh_m2a": block_d2["warm_water_deduction_kwh_m2a"],
                "source": "heizspiegel.de/heizkosten-pruefen/methodik-heizspiegel",
                "rechtsstand": "09/2025",
                "verification_status": "verify-before-production",
            },
        }
        assert (
            cast(dict[str, object], first.results["block_a"])["heat_kwh"] == block_a["result_kwh"]
        )
        assert (
            cast(dict[str, object], first.results["block_b"])["delta_kwh"] == block_b["delta_kwh"]
        )
        assert (
            cast(dict[str, object], first.results["block_c"])["delta_kwh"] == block_c["delta_kwh"]
        )
        d2_result = cast(dict[str, object], first.results["block_d2"])
        assert d2_result["heizspiegel_mittel_kwh_m2a"] == block_d2["heizspiegel_mittel_kwh_m2a"]
        assert d2_result["warm_water_deduction_kwh_m2a"] == block_d2["warm_water_deduction_kwh_m2a"]
        assert first.results["production_blocked"] is True
        assert first.results["unresolved_conflicts"]
        assert {
            item["code"]
            for item in cast(list[dict[str, object]], first.results["unresolved_conflicts"])
        } == {"uvi_plz_geodataset_unresolved", "uvi_register_rows_missing"}
        evidence_sources = {
            item["source"] for item in cast(list[dict[str, object]], first.results["rule_evidence"])
        }
        assert {
            f"U5-config-{live.ids['account']}",
            f"DWD-degree-{live.ids['account']}-target",
            f"DWD-degree-{live.ids['account']}-prior-year",
            f"DWD-assignment-{live.ids['account']}-target",
            "heizspiegel.de/heizkosten-pruefen/methodik-heizspiegel",
        } <= evidence_sources
        assert first.results["reduction_risks"] == [
            {
                "code": "hkv_12_1_s2_remote_readability_3pct",
                "status": "verify-before-production",
                "automatic_deduction": False,
            },
            {
                "code": "hkv_12_1_s3_uvi_information_3pct",
                "status": "verify-before-production",
                "automatic_deduction": False,
            },
        ]
        assert cast(dict[str, object], first.results["document"])["legal_risks_de"] == []

        frozen_inputs = first.inputs
        frozen_results = first.results
        frozen_hash = first.sha256
        retry = _post_generation(live)
        assert retry.status_code == 201, retry.text
        retry_runs, retry_events = _archive_rows(live)
        assert len(retry_runs) == len(retry_events) == 2
        original = next(row for row in retry_runs if row.id == first.id)
        assert original.inputs == frozen_inputs
        assert original.results == frozen_results
        assert original.sha256 == frozen_hash
        assert retry.json()["runId"] != first.id
        assert {event.status for event in retry_events} == {"GENERATED"}


def test_u5_selects_only_heat_rows_in_one_compatible_device_category(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U5-BOUNDARY-01: water rows are neither target input nor Block D comparable."""
    with _live_u5_graph(monkeypatch, block_d_ready=True) as live:
        _insert_water_distractors(live)

        response = _post_generation(live)
        assert response.status_code == 201, response.text
        run = _archive_rows(live)[0][0]
        assert cast(dict[str, object], run.inputs["target_meter"])["kind"] == "HEAT"
        comparables = cast(list[dict[str, object]], run.inputs["comparables"])
        assert len(comparables) == 2
        assert {row["meter_kind"] for row in comparables} == {"HEAT"}
        assert {row["measurement_unit"] for row in comparables} == {"KWH"}
        assert not {
            live.ids["water_meter_target"],
            live.ids["water_meter_comparable"],
        } & {
            cast(str, cast(dict[str, object], run.inputs["target_meter"])["meter_id"]),
            *(cast(str, row["meter_id"]) for row in comparables),
        }


def test_u5_uses_the_configuration_effective_in_each_compared_month(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U5-BOUNDARY-02: target, previous and prior-year conversion are independently temporal."""
    with _live_u5_graph(monkeypatch, missing="config") as live:
        _insert_three_month_configurations(live)

        response = _post_generation(live)
        assert response.status_code == 201, response.text
        run = _archive_rows(live)[0][0]
        block_b = cast(dict[str, object], run.results["block_b"])
        block_c = cast(dict[str, object], run.results["block_c"])
        assert block_b["delta_kwh"] == 1000  # 900*3 - 850*2
        assert block_c["reference_kwh"] == 952  # 1000*1, weather-adjusted by 590/620


def test_u5_hash_archive_contains_complete_block_a_snapshots_for_all_three_months(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U5-BOUNDARY-03: every compared month freezes meter, config and building evidence."""
    with _live_u5_graph(monkeypatch) as live:
        response = _post_generation(live)
        assert response.status_code == 201, response.text
        run = _archive_rows(live)[0][0]
        normalized_months = cast(dict[str, dict[str, object]], run.inputs["normalized_months"])
        expected = {
            "target": (live.ids["monthly_target"], 900000),
            "previous": (live.ids["monthly_previous"], 850000),
            "prior_year": (live.ids["monthly_prior_year"], 1000000),
        }
        assert set(normalized_months) == set(expected)
        for name, (reading_id, movement_x1000) in expected.items():
            snapshot = normalized_months[name]
            assert snapshot["monthly_reading_id"] == reading_id
            assert snapshot["monthly_movement_x1000"] == movement_x1000
            assert snapshot["meter"] == {
                "id": live.ids["meter"],
                "kind": "HEAT",
                "measurement_unit": "KWH",
            }
            assert snapshot["building_configuration_id"] == live.ids["configuration"]
            assert snapshot["building_monthly_evidence"] == {
                "id": None,
                "measured_building_heat_kwh_x1000": None,
                "building_hkv_movement_x1000": None,
            }
        assert len(run.sha256) == 64


def test_u5_building_evidence_snapshot_archives_sorted_authoritative_source_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U5-BOUNDARY-05: selected building evidence freezes every source-link identity."""
    with _live_u5_graph(monkeypatch) as live:
        expected_links = _insert_building_evidence_with_two_sources(live)

        response = _post_generation(live)
        assert response.status_code == 201, response.text
        first = _archive_rows(live)[0][0]
        normalized_months = cast(dict[str, dict[str, object]], first.inputs["normalized_months"])
        evidence = cast(dict[str, object], normalized_months["target"]["building_monthly_evidence"])
        assert evidence["id"] == live.ids["building_evidence"]
        assert evidence["main_meter_id"] == live.ids["building_main_meter"]
        assert evidence["source_links"] == expected_links
        assert all(set(link) == {"id", "meter_reading_id"} for link in expected_links)

        frozen_inputs = json.loads(json.dumps(first.inputs))
        frozen_hash = first.sha256
        third_reading = new_id()
        third_link = new_id()
        live.connection.execute(
            text(
                "INSERT INTO meter_reading"
                " (id, account_id, meter_id, read_at, value_x1000, reason, source)"
                " VALUES (:reading, :account, :building_main_meter, '2026-07-15', 2500000,"
                " 'PERIODIC', 'MANUAL')"
            ),
            {**live.ids, "reading": third_reading},
        )
        live.connection.execute(
            text(
                "INSERT INTO uvi_building_monthly_evidence_source"
                " (id, account_id, building_monthly_evidence_id, main_meter_id,"
                " meter_reading_id) VALUES"
                " (:link, :account, :building_evidence, :building_main_meter, :reading)"
            ),
            {**live.ids, "link": third_link, "reading": third_reading},
        )

        retry = _post_generation(live)
        assert retry.status_code == 201, retry.text
        runs = _archive_rows(live)[0]
        original = next(run for run in runs if run.id == first.id)
        replacement = next(run for run in runs if run.id != first.id)
        replacement_months = cast(
            dict[str, dict[str, object]], replacement.inputs["normalized_months"]
        )
        replacement_evidence = cast(
            dict[str, object], replacement_months["target"]["building_monthly_evidence"]
        )
        assert replacement_evidence["source_links"] == sorted(
            [*expected_links, {"id": third_link, "meter_reading_id": third_reading}],
            key=lambda item: item["id"],
        )
        assert replacement.sha256 != frozen_hash
        assert original.inputs == frozen_inputs
        assert original.sha256 == frozen_hash


def test_u5_archived_document_provenance_identifies_both_weather_months_and_d2_share(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U5-DOC-REVIEW-03: renter provenance names every DWD value and identity used."""
    with _live_u5_graph(monkeypatch) as live:
        response = _post_generation(live)
        assert response.status_code == 201, response.text
        run = _archive_rows(live)[0][0]
        document = cast(dict[str, object], run.results["document"])
        block_c = cast(dict[str, object], document["block_c"])
        block_d2 = cast(dict[str, object], document["block_d_or_d2"])
        block_c_provenance = cast(list[str], block_c["provenance_de"])
        block_d2_provenance = " · ".join(cast(list[str], block_d2["provenance_de"]))

        for expected_month_source in (
            (
                "Zielmonat 07/2026",
                "590 Kd",
                "Station U5-target",
                "12,345 km",
                "DWD-target.csv",
                f"DWD-degree-{live.ids['account']}-target",
                f"DWD-assignment-{live.ids['account']}-target",
            ),
            (
                "Vorjahresmonat 07/2025",
                "620 Kd",
                "Station U5-prior-year",
                "12,345 km",
                "DWD-prior-year.csv",
                f"DWD-degree-{live.ids['account']}-prior-year",
                f"DWD-assignment-{live.ids['account']}-prior-year",
            ),
        ):
            assert any(
                all(exact_source_fact in item for exact_source_fact in expected_month_source)
                for item in block_c_provenance
            ), expected_month_source

        for exact_d2_fact in (
            "0,19",
            "Quelle: Deutscher Wetterdienst",
            "DWD-target.csv",
            f"DWD-degree-{live.ids['account']}-target",
        ):
            assert exact_d2_fact in block_d2_provenance


def test_u5_archived_document_translates_internal_interpolation_provenance_to_german(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U5-DOC-REVIEW-04: archive and renter document contain only approved German copy."""
    with _live_u5_graph(monkeypatch) as live:
        _insert_interpolated_target_correction(live)
        response = _post_generation(live)
        assert response.status_code == 201, response.text
        run = _archive_rows(live)[0][0]
        document = cast(dict[str, object], run.results["document"])
        block_a = cast(dict[str, object], document["block_a"])
        provenance = " · ".join(cast(list[str], block_a["provenance_de"]))
        assert "linear_by_elapsed_days" not in provenance
        assert "linear nach verstrichenen Tagen interpoliert" in provenance


def test_u5_document_reads_only_the_archived_run_after_later_source_corrections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U5-DB-02: GET renders archived data, never a new live calculation."""
    with _live_u5_graph(monkeypatch) as live:
        generated = _post_generation(live)
        assert generated.status_code == 201, generated.text
        run_id = generated.json()["runId"]
        live.rendered_html.clear()
        first_pdf = live.client.get(live.document_path(run_id))
        assert first_pdf.status_code == 200
        assert first_pdf.headers["content-type"].startswith("application/pdf")
        assert first_pdf.content.startswith(b"%PDF-1.7")
        assert len(live.rendered_html) == 1
        archived_html = live.rendered_html[0]
        assert "07/2026" in archived_html
        assert "U5 Wohnung" in archived_html
        assert "900" in archived_html
        assert "Andere Wohnung" not in archived_html
        assert "Fremdes U5 Haus" not in archived_html

        _insert_later_corrections(live)
        second_pdf = live.client.get(live.document_path(run_id))
        assert second_pdf.status_code == 200
        assert second_pdf.content == first_pdf.content
        assert live.rendered_html == [archived_html, archived_html]
        runs, events = _archive_rows(live)
        assert len(runs) == len(events) == 1
        assert runs[0].id == run_id


def test_u5_cross_building_tenancy_is_404_without_archive_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U5-DB-03: nested tenancy mismatch is hidden and writes no evidence."""
    with _live_u5_graph(monkeypatch) as live:
        response = _post_generation(live, live.ids["foreign_tenancy"])
        assert response.status_code == 404
        assert _archive_rows(live) == ([], [])


@pytest.mark.parametrize("missing", ("config", "reading"))
def test_u5_missing_authoritative_input_is_422_without_archive_rows(
    monkeypatch: pytest.MonkeyPatch,
    missing: str,
) -> None:
    """U5-DB-04: server-side prerequisite gaps fail atomically before UviRun."""
    with _live_u5_graph(monkeypatch, missing=missing) as live:
        response = _post_generation(live)
        assert response.status_code == 422, response.text
        assert _archive_rows(live) == ([], [])


def test_u5_one_unit_d2_missing_annual_share_is_422_without_archive_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U5-DB-05: only the selected D2 branch requires the annual degree-day share."""
    with _live_u5_graph(monkeypatch, missing="share") as live:
        response = _post_generation(live)
        assert response.status_code == 422, response.text
        assert _archive_rows(live) == ([], [])


@pytest.mark.parametrize(
    ("missing", "weather_label"),
    (
        ("degree", "nicht witterungsbereinigt"),
        ("share", None),
    ),
    ids=("no-degree-row-raw-block-c", "degree-row-without-d2-share"),
)
def test_u5_ready_block_d_does_not_require_d2_or_weather_prerequisites(
    monkeypatch: pytest.MonkeyPatch,
    missing: str,
    weather_label: str | None,
) -> None:
    """U5-DB-06: three valid units select D before weather/share/Heizspiegel resolution."""
    block_d = UVI_EXAMPLES["emir_spec_block_d_building_cross_section"]
    raw_c = UVI_EXAMPLES["approved_block_c_raw_weather_fallback"]
    with _live_u5_graph(monkeypatch, missing=missing, block_d_ready=True) as live:
        response = _post_generation(live)
        assert response.status_code == 201, response.text
        runs, events = _archive_rows(live)
        assert len(runs) == len(events) == 1
        run = runs[0]
        assert run.heizspiegel_vintage is None
        if missing == "degree":
            assert (
                run.station_assignment_id,
                run.station_id,
                run.station_distance_km,
            ) == (None, None, None)
        archived_d = cast(dict[str, object], run.results["block_d"])
        assert archived_d["status"] == "ready"
        assert archived_d["expected_target_kwh"] == block_d["expected_kwh"]
        assert archived_d["delta_kwh"] == block_d["delta_kwh"]
        assert archived_d["percent"] == block_d["percent"]
        assert run.results["block_d2"] is None
        archived_c = cast(dict[str, object], run.results["block_c"])
        assert archived_c["label_de"] == weather_label
        if weather_label is not None:
            assert archived_c["delta_kwh"] == raw_c["raw_delta_kwh"]
            assert archived_c["percent"] == raw_c["raw_percent"]

        comparable_specs = cast(tuple[dict[str, object], ...], block_d["comparables"])
        assert run.inputs["comparables"] == [
            {
                "unit_id": live.ids[f"comparable_unit_{index}"],
                "area_sqm_x100": cast(int, spec["area_sqm"]) * 100,
                "monthly_reading_id": live.ids[f"comparable_monthly_{index}"],
                "meter_id": live.ids[f"comparable_meter_{index}"],
                "meter_kind": "HEAT",
                "measurement_unit": "KWH",
                "raw_reading_ids": [live.ids[f"comparable_raw_{index}"]],
                "computed_heat_kwh": spec["kwh"],
            }
            for index, spec in enumerate(comparable_specs, start=1)
        ]


def test_u5_hash_binds_comparable_source_identity_without_rewriting_prior_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U5-DB-07: an equivalent correction changes the new archive hash by identity."""
    with _live_u5_graph(monkeypatch, block_d_ready=True) as live:
        first_response = _post_generation(live)
        assert first_response.status_code == 201, first_response.text
        first_run = _archive_rows(live)[0][0]
        frozen_inputs = first_run.inputs
        frozen_hash = first_run.sha256

        _insert_equivalent_comparable_source_correction(live)
        second_response = _post_generation(live)
        assert second_response.status_code == 201, second_response.text
        runs, events = _archive_rows(live)
        assert len(runs) == len(events) == 2
        original = next(row for row in runs if row.id == first_run.id)
        replacement = next(row for row in runs if row.id != first_run.id)
        assert original.inputs == frozen_inputs
        assert original.sha256 == frozen_hash
        assert replacement.sha256 != frozen_hash
        replacement_d = cast(dict[str, object], replacement.results["block_d"])
        original_d = cast(dict[str, object], first_run.results["block_d"])
        assert replacement_d["expected_target_kwh"] == original_d["expected_target_kwh"]
