"""RED M9 API contracts for guards, reminders, delivery and checklists.

The pure rules, immutable records and scheduled jobs have their own fixtures.  This
file pins the HTTP boundary which exposes them: account-path authorization, the
owner/employee split, assigned-building filtering, singular renter delivery and the
separation between a provider status and legal delivery evidence.
"""

from __future__ import annotations

import importlib
import os
import time
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, cast

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from lokara_api.settings import ApiSettings
from lokara_db import (
    Account,
    Building,
    BuildingAssignment,
    DbSettings,
    DeliveryScheduleVersion,
    GuardEvaluation,
    GuardResolutionEvent,
    Landlord,
    Membership,
    Person,
    Renter,
    RenterDeliveryArtifact,
    Role,
    Statement,
    StatementArchive,
    Tenancy,
    TenancyParty,
    Unit,
    create_db_engine,
)
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "db"

ACCOUNT = "{account_id}"
CHECKLIST = "{id}"
ITEM = "{item_id}"
DELIVERY = "{id}"

GUARDS = f"/a/{ACCOUNT}/guards"
GUARD_RUNS = f"/a/{ACCOUNT}/guard-runs"
SCHEDULES = f"/a/{ACCOUNT}/delivery-schedules"
REMINDERS = f"/a/{ACCOUNT}/reminders"
CHECKLISTS = f"/a/{ACCOUNT}/checklists"
CHECKLIST_EVENTS = f"/a/{ACCOUNT}/checklists/{CHECKLIST}/items/{ITEM}/events"
DELIVERIES = f"/a/{ACCOUNT}/deliveries"
CONFIRM = f"/a/{ACCOUNT}/deliveries/{DELIVERY}/confirm"


def _module() -> ModuleType:
    try:
        return importlib.import_module("lokara_api.routers.guards_delivery")
    except ModuleNotFoundError:
        pytest.fail(
            "RED M9: lokara_api.routers.guards_delivery is missing",
            pytrace=False,
        )


def _openapi(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "m9-api-contract-secret-at-least-32-chars")
    api = importlib.import_module("lokara_api")
    return cast(dict[str, object], TestClient(api.create_app()).get("/openapi.json").json())


def _operation(schema: dict[str, object], path: str, method: str) -> dict[str, object]:
    paths = cast(dict[str, object], schema["paths"])
    assert path in paths, f"RED M9: route {path} is missing"
    operations = cast(dict[str, object], paths[path])
    assert method in operations, f"RED M9: {method.upper()} {path} is missing"
    return cast(dict[str, object], operations[method])


def _request_schema(schema: dict[str, object], path: str, method: str) -> dict[str, object]:
    operation = _operation(schema, path, method)
    body = cast(dict[str, object], operation["requestBody"])
    content = cast(dict[str, object], body["content"])
    media = cast(dict[str, object], content["application/json"])
    value = cast(dict[str, object], media["schema"])
    reference = value.get("$ref")
    if reference is None:
        return value
    name = cast(str, reference).removeprefix("#/components/schemas/")
    components = cast(dict[str, object], schema["components"])
    schemas = cast(dict[str, object], components["schemas"])
    return cast(dict[str, object], schemas[name])


def _properties(schema: dict[str, object]) -> set[str]:
    return set(cast(dict[str, object], schema["properties"]))


def test_m9_registers_the_complete_account_route_surface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schema = _openapi(monkeypatch)
    expected = {
        GUARDS: {"get"},
        GUARD_RUNS: {"post"},
        SCHEDULES: {"get", "post"},
        REMINDERS: {"get"},
        CHECKLISTS: {"get"},
        CHECKLIST_EVENTS: {"post"},
        DELIVERIES: {"get", "post"},
        CONFIRM: {"post"},
    }
    paths = cast(dict[str, object], schema["paths"])
    for path, methods in expected.items():
        assert path in paths, f"RED M9: route {path} is missing"
        assert methods <= set(cast(dict[str, object], paths[path]))


def test_every_m9_route_uses_the_membership_checked_account_path_dependency() -> None:
    """A router-local raw Session dependency would bypass URL-account membership."""
    from lokara_api.deps import account_session_for_path
    from lokara_api.main import app

    expected_paths = {
        GUARDS,
        GUARD_RUNS,
        SCHEDULES,
        REMINDERS,
        CHECKLISTS,
        CHECKLIST_EVENTS,
        DELIVERIES,
        CONFIRM,
    }
    routes = {
        route.path: route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path in expected_paths
    }
    assert set(routes) == expected_paths, "RED M9: account-scoped router is not registered"
    for path, route in routes.items():
        dependencies = {
            dependency.call
            for dependency in route.dependant.dependencies
            if dependency.call is not None
        }
        assert account_session_for_path in dependencies, (
            f"{path} must independently verify membership in the account carried by the URL"
        )


_ACTIONS = (
    "guards_read",
    "guard_run",
    "schedule_read",
    "schedule_write",
    "reminder_read",
    "checklist_read",
    "checklist_write",
    "delivery_read",
    "send",
    "confirm",
)
_ROLE_CASES = (
    *((Role.OWNER, action, True) for action in _ACTIONS),
    *(
        (
            Role.EMPLOYEE,
            action,
            action in {"guards_read", "checklist_read", "checklist_write"},
        )
        for action in _ACTIONS
    ),
    *((Role.TAX_ADVISOR, action, False) for action in _ACTIONS),
)


@pytest.mark.parametrize(("role", "action", "allowed"), _ROLE_CASES)
def test_m9_role_matrix(role: Role, action: str, allowed: bool) -> None:
    authorize = getattr(_module(), "authorize_m9_action", None)
    assert callable(authorize), "RED M9: authorize_m9_action is missing"
    if allowed:
        authorize(role, action)
    else:
        with pytest.raises(HTTPException) as refused:
            authorize(role, action)
        assert refused.value.status_code == 403


class _EmptyReadSession:
    def scalars(self, _statement: object) -> object:
        return SimpleNamespace(all=lambda: [])

    def execute(self, _statement: object) -> object:
        return SimpleNamespace(all=lambda: [])


def test_each_m9_read_route_uses_its_narrow_authorization_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    seen: list[str] = []

    def authorize(_session: object, action: str) -> object:
        seen.append(action)
        return SimpleNamespace(role=Role.OWNER, building_ids=frozenset())

    monkeypatch.setattr(module, "_authorize", authorize)
    session = _EmptyReadSession()
    for function_name, expected_action in (
        ("list_guards", "guards_read"),
        ("list_delivery_schedules", "schedule_read"),
        ("list_reminders", "reminder_read"),
        ("list_checklists", "checklist_read"),
        ("list_deliveries", "delivery_read"),
    ):
        function = getattr(module, function_name)
        function("account-1", session)
        assert seen.pop() == expected_action


def test_employee_resources_are_filtered_by_assigned_building() -> None:
    """List filtering and id-only anti-enumeration share one explicit boundary."""
    module = _module()
    filter_rows = getattr(module, "filter_m9_rows_for_scope", None)
    require_row = getattr(module, "require_m9_row_for_scope", None)
    assert callable(filter_rows), "RED M9: assigned-building list filter is missing"
    assert callable(require_row), "RED M9: assigned-building resource check is missing"

    rows = (
        SimpleNamespace(id="visible", building_id="building-assigned"),
        SimpleNamespace(id="hidden", building_id="building-unassigned"),
    )
    employee = SimpleNamespace(
        role=Role.EMPLOYEE,
        building_ids=frozenset({"building-assigned"}),
    )
    owner = SimpleNamespace(role=Role.OWNER, building_ids=frozenset())

    assert [row.id for row in filter_rows(rows, employee)] == ["visible"]
    assert [row.id for row in filter_rows(rows, owner)] == ["visible", "hidden"]
    assert require_row(rows[0], employee).id == "visible"
    with pytest.raises(HTTPException) as hidden:
        require_row(rows[1], employee)
    assert hidden.value.status_code == 404


def test_schedule_contract_is_versioned_and_defaults_to_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schema = _openapi(monkeypatch)
    request = _request_schema(schema, SCHEDULES, "post")
    assert {"buildingId", "deliveryKind", "validFrom"} <= _properties(request)
    # Opt-in means omission cannot silently turn delivery on.
    enabled = cast(dict[str, object], cast(dict[str, object], request["properties"])["enabled"])
    assert enabled.get("default") is False

    response_type = getattr(_module(), "DeliveryScheduleResponse", None)
    assert response_type is not None, "RED M9: DeliveryScheduleResponse is missing"
    assert {
        "id",
        "building_id",
        "delivery_kind",
        "version",
        "enabled",
        "supersedes_schedule_version_id",
        "valid_from",
        "schedule_snapshot",
    } <= set(response_type.model_fields)


def test_annual_schedule_accepts_only_the_stable_archive_source_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Period and occurrence identity are server-owned archive consequences."""
    schema = _request_schema(_openapi(monkeypatch), SCHEDULES, "post")
    fields = _properties(schema)
    assert "sourceId" in fields
    assert {
        "scheduleSnapshot",
        "statementId",
        "statementPeriod",
        "periodStart",
        "periodEnd",
        "occurrenceKey",
    }.isdisjoint(fields)
    assert "sourceId" in set(cast(list[str], schema["required"]))


class _ScheduleCreateSession:
    def __init__(
        self,
        *,
        building: Any,
        archive: Any,
        statement: Any,
    ) -> None:
        self.building = building
        self.archive = archive
        self.statement = statement
        self.added: list[object] = []

    def scalar(self, query: object) -> object:
        entity = query.column_descriptions[0].get("entity")  # type: ignore[attr-defined]
        if entity is Building:
            return self.building
        if entity is StatementArchive:
            return self.archive
        if entity is Statement:
            return self.statement
        if entity is DeliveryScheduleVersion:
            return None
        return None

    def scalars(self, query: object) -> object:
        value = self.scalar(query)
        return SimpleNamespace(all=lambda: [] if value is None else [value])

    def execute(self, _query: object) -> object:
        pair = (self.archive, self.statement)
        return SimpleNamespace(one_or_none=lambda: pair, first=lambda: pair)

    def add(self, row: object) -> None:
        self.added.append(row)

    def flush(self) -> None:
        return None


def _annual_schedule_source_context(*, statement_building_id: str) -> tuple[Any, Any, Any]:
    building = SimpleNamespace(id="building-1")
    statement = SimpleNamespace(
        id="statement-2025",
        account_id="account-1",
        building_id=statement_building_id,
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
    )
    archive = SimpleNamespace(
        id="archive-tenant-2025",
        account_id="account-1",
        statement_id=statement.id,
        tenancy_id="tenancy-1",
        audience="TENANT",
    )
    return building, archive, statement


def test_schedule_creation_freezes_canonical_statement_binding_server_side(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    request_type = module.DeliveryScheduleCreate
    building, archive, statement = _annual_schedule_source_context(
        statement_building_id="building-1"
    )
    session = _ScheduleCreateSession(
        building=building,
        archive=archive,
        statement=statement,
    )
    monkeypatch.setattr(module, "_authorize", lambda _session, _action: None)

    response = module.create_delivery_schedule(
        "account-1",
        request_type(
            building_id="building-1",
            delivery_kind="ANNUAL_STATEMENT",
            valid_from=date(2026, 8, 25),
            source_id=archive.id,
        ),
        session,
    )

    assert response.enabled is False
    assert response.version == 1
    assert response.schedule_snapshot == {
        "enabled": False,
        "valid_from": "2026-08-25",
        "statement_archive_id": archive.id,
        "statement_id": statement.id,
        "statement_period": {
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
        },
        "occurrence_key": ("annual-statement:statement-2025:archive-tenant-2025:tenancy-1"),
    }


def test_schedule_creation_rejects_same_account_archive_from_another_building(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    request_type = module.DeliveryScheduleCreate
    building, archive, statement = _annual_schedule_source_context(
        statement_building_id="building-2"
    )
    session = _ScheduleCreateSession(
        building=building,
        archive=archive,
        statement=statement,
    )
    monkeypatch.setattr(module, "_authorize", lambda _session, _action: None)

    with pytest.raises(HTTPException) as refused:
        module.create_delivery_schedule(
            "account-1",
            request_type(
                building_id="building-1",
                delivery_kind="ANNUAL_STATEMENT",
                valid_from=date(2026, 8, 25),
                source_id=archive.id,
            ),
            session,
        )
    assert refused.value.status_code in {404, 422}


def test_delivery_request_is_one_renter_and_one_frozen_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request_schema(_openapi(monkeypatch), DELIVERIES, "post")
    fields = _properties(request)
    assert {"buildingId", "renterId", "artifactId", "deliveryKind", "occurrenceKey"} <= fields
    assert fields.isdisjoint(
        {"recipientEmails", "recipients", "cc", "bcc", "attachmentBytes", "artifactSha256"}
    )
    assert {"buildingId", "renterId", "artifactId", "deliveryKind", "occurrenceKey"} <= set(
        cast(list[str], request["required"])
    )


def test_delivery_response_keeps_blocked_provider_and_legal_states_separate() -> None:
    response_type = getattr(_module(), "DeliveryResponse", None)
    assert response_type is not None, "RED M9: DeliveryResponse is missing"
    fields = set(response_type.model_fields)
    assert {
        "blocked_reason",
        "provider_status",
        "provider_delivered_at",
        "legally_confirmed",
        "delivered_on",
        "evidence_reference",
    } <= fields

    provider_only = response_type(
        id="delivery-1",
        renter_id="renter-1",
        artifact_id="artifact-1",
        blocked_reason=None,
        provider_status="DELIVERED",
        provider_delivered_at="2026-08-25T10:00:00Z",
        legally_confirmed=False,
        delivered_on=None,
        evidence_reference=None,
    )
    assert provider_only.provider_status == "DELIVERED"
    assert provider_only.legally_confirmed is False
    assert provider_only.delivered_on is None


def test_confirmation_requires_owner_evidence_not_a_provider_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schema = _openapi(monkeypatch)
    request = _request_schema(schema, CONFIRM, "post")
    assert _properties(request) == {"deliveredOn", "evidenceReference"}
    assert set(cast(list[str], request["required"])) == {"deliveredOn", "evidenceReference"}

    request_type = getattr(_module(), "DeliveryConfirmationCreate", None)
    assert request_type is not None, "RED M9: DeliveryConfirmationCreate is missing"
    with pytest.raises(ValidationError):
        request_type(delivered_on=date(2026, 8, 25), evidence_reference="   ")
    confirmed = request_type(
        delivered_on=date(2026, 8, 25),
        evidence_reference="Einschreiben-Beleg 2026-08-25",
    )
    assert confirmed.delivered_on == date(2026, 8, 25)


def test_confirmation_matches_the_complete_w1_statement_context() -> None:
    """A coincidentally equal renter/occurrence key must not resolve another W1."""
    checker = getattr(_module(), "validate_w1_delivery_confirmation", None)
    assert callable(checker), "RED M9: complete W1 confirmation validator is missing"

    artifact = SimpleNamespace(
        artifact_kind="ANNUAL_STATEMENT",
        building_id="building-1",
        unit_id="unit-1",
        tenancy_id="tenancy-1",
        renter_id="renter-1",
        occurrence_key="statement:2025:renter-1",
    )
    evaluation = SimpleNamespace(
        guard_code="W1",
        building_id="building-1",
        unit_id="unit-1",
        tenancy_id="tenancy-1",
        renter_id="renter-1",
        occurrence_key="statement:2025:renter-1",
    )
    checker(artifact=artifact, evaluation=evaluation)

    for field, forged_value in (
        ("artifact_kind", "UVI"),
        ("building_id", "building-2"),
        ("unit_id", "unit-2"),
        ("tenancy_id", "tenancy-2"),
        ("renter_id", "renter-2"),
        ("occurrence_key", "statement:2024:renter-1"),
    ):
        forged_artifact = SimpleNamespace(**artifact.__dict__)
        setattr(forged_artifact, field, forged_value)
        with pytest.raises(HTTPException) as refused:
            checker(artifact=forged_artifact, evaluation=evaluation)
        assert refused.value.status_code == 422


def test_w1_confirmation_future_late_and_on_time_decisions_are_distinct() -> None:
    decide = getattr(_module(), "evaluate_w1_delivery_confirmation", None)
    assert callable(decide), "RED M9: W1 delivery-date decision helper is missing"
    artifact = SimpleNamespace(
        id="artifact-1",
        artifact_kind="ANNUAL_STATEMENT",
        building_id="building-1",
        unit_id="unit-1",
        tenancy_id="tenancy-1",
        renter_id="renter-1",
        occurrence_key="statement:2025:renter-1",
    )
    evaluation = SimpleNamespace(
        guard_code="W1",
        building_id="building-1",
        unit_id="unit-1",
        tenancy_id="tenancy-1",
        renter_id="renter-1",
        occurrence_key="statement:2025:renter-1",
        result_snapshot={"boundary_date": "2026-08-20"},
    )

    with pytest.raises(HTTPException) as future:
        decide(
            artifact=artifact,
            evaluation=evaluation,
            delivered_on=date(2026, 8, 26),
            today=date(2026, 8, 25),
        )
    assert future.value.status_code == 422

    late = decide(
        artifact=artifact,
        evaluation=evaluation,
        delivered_on=date(2026, 8, 24),
        today=date(2026, 8, 25),
    )
    assert late.record_delivery_evidence is True
    assert late.late_delivery is True
    assert late.resolve_w1 is False
    assert late.append_resolution_event is False

    on_time = decide(
        artifact=artifact,
        evaluation=evaluation,
        delivered_on=date(2026, 8, 20),
        today=date(2026, 8, 25),
    )
    assert on_time.record_delivery_evidence is True
    assert on_time.late_delivery is False
    assert on_time.resolve_w1 is True
    assert on_time.append_resolution_event is True


class _CorrectionSession:
    def __init__(self, artifact: Any, evaluation: Any, current_event: Any) -> None:
        self.artifact = artifact
        self.evaluation = evaluation
        self.current_event = current_event
        self.added: list[object] = []

    def scalar(self, statement: object) -> object:
        entity = statement.column_descriptions[0].get("entity")  # type: ignore[attr-defined]
        if entity is RenterDeliveryArtifact:
            return self.artifact
        if entity is GuardEvaluation:
            return self.evaluation
        if entity is GuardResolutionEvent:
            return self.current_event
        return None

    def add(self, value: object) -> None:
        self.added.append(value)
        if isinstance(value, GuardResolutionEvent):
            self.current_event = value

    def flush(self) -> None:
        return None


@pytest.mark.parametrize(
    ("corrected_on", "resolves_w1"),
    (
        (date(2026, 8, 22), False),
        (date(2026, 8, 20), True),
    ),
)
def test_late_delivery_correction_appends_superseding_evidence_and_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    corrected_on: date,
    resolves_w1: bool,
) -> None:
    module = _module()
    artifact = SimpleNamespace(
        id="artifact-1",
        artifact_kind="ANNUAL_STATEMENT",
        building_id="building-1",
        unit_id="unit-1",
        tenancy_id="tenancy-1",
        renter_id="renter-1",
        occurrence_key="statement:2025:renter-1",
    )
    evaluation = SimpleNamespace(
        id="evaluation-1",
        guard_code="W1",
        building_id="building-1",
        unit_id="unit-1",
        tenancy_id="tenancy-1",
        renter_id="renter-1",
        occurrence_key="statement:2025:renter-1",
        result_snapshot={"boundary_date": "2026-08-20"},
    )
    late_event = SimpleNamespace(
        id="late-event-1",
        event_type="statement_delivery_evidence_late",
        evidence_reference="Erstbeleg",
        event_snapshot={
            "artifact_id": artifact.id,
            "delivered_on": "2026-08-24",
            "confirmed_by_owner": True,
            "late_delivery": True,
            "resolves_w1": False,
        },
    )
    session = _CorrectionSession(artifact, evaluation, late_event)
    monkeypatch.setattr(
        module,
        "_authorize",
        lambda _session, action: (
            SimpleNamespace(role=Role.OWNER, membership_id="membership-owner-1")
            if action == "confirm"
            else None
        ),
    )
    monkeypatch.setattr(
        module,
        "_delivery_response",
        lambda _session, _account_id, _artifact: session.current_event,
    )
    body = module.DeliveryConfirmationCreate(
        delivered_on=corrected_on,
        evidence_reference="Korrekturbeleg",
    )
    now = datetime(2026, 8, 25, 9, 0, tzinfo=UTC)

    module.confirm_delivery(
        "account-1",
        artifact.id,
        body,
        session,
        now,
    )
    assert len(session.added) == 1
    correction = session.added[0]
    assert isinstance(correction, GuardResolutionEvent)
    assert correction.event_snapshot["supersedes_event_id"] == late_event.id
    assert correction.event_snapshot["corrects_delivered_on"] == "2026-08-24"
    assert correction.event_snapshot["delivered_on"] == corrected_on.isoformat()
    assert correction.event_snapshot["resolves_w1"] is resolves_w1
    assert correction.event_snapshot["late_delivery"] is (not resolves_w1)
    assert (
        "correction" in correction.event_type
        or correction.event_snapshot.get("is_correction") is True
    )

    module.confirm_delivery(
        "account-1",
        artifact.id,
        body,
        session,
        now,
    )
    assert session.added == [correction], "the same correction must be idempotent"


def test_confirmation_uses_stable_account_scoped_idempotency_and_allows_correction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    key_for = getattr(module, "guard_resolution_idempotency_key", None)
    assert callable(key_for), "RED M9: stable resolution idempotency-key helper is missing"

    first = key_for(
        account_id="account-1",
        delivery_id="artifact-1",
        delivered_on=date(2026, 8, 20),
        evidence_reference="Einschreiben 4711",
    )
    replay = key_for(
        account_id="account-1",
        delivery_id="artifact-1",
        delivered_on=date(2026, 8, 20),
        evidence_reference="Einschreiben 4711",
    )
    corrected = key_for(
        account_id="account-1",
        delivery_id="artifact-1",
        delivered_on=date(2026, 8, 21),
        evidence_reference="Korrekturbeleg 4712",
    )
    foreign_account = key_for(
        account_id="account-2",
        delivery_id="artifact-1",
        delivered_on=date(2026, 8, 20),
        evidence_reference="Einschreiben 4711",
    )

    assert first == replay
    assert len({first, corrected, foreign_account}) == 3
    assert all(isinstance(value, str) and value.strip() for value in (first, corrected))

    # The database uniqueness fixture is the concurrent-insert backstop. The API
    # contract must reuse an existing identical event while a correction appends.
    event = GuardResolutionEvent(
        id="resolution-1",
        account_id="account-1",
        guard_evaluation_id="evaluation-1",
        event_type="statement_sent",
        occurred_at=datetime(2026, 8, 25, 9, 0, tzinfo=UTC),
        evidence_reference="Einschreiben 4711",
        event_snapshot={"delivered_on": "2026-08-20"},
        idempotency_key=first,
    )
    assert event.idempotency_key == first


def test_guard_run_accepts_only_server_source_ids_and_explicit_clocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request_schema(_openapi(monkeypatch), GUARD_RUNS, "post")
    fields = _properties(request)
    assert fields == {"today", "now", "sourceIds"}
    assert set(cast(list[str], request["required"])) == {"today", "now", "sourceIds"}
    assert fields.isdisjoint(
        {
            "occurrences",
            "inputSnapshot",
            "resultSnapshot",
            "ruleSnapshot",
            "productionBlockers",
            "reminderChannels",
        }
    )


def test_write_contracts_document_role_and_relationship_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schema = _openapi(monkeypatch)
    for method, path in (
        ("post", GUARD_RUNS),
        ("post", SCHEDULES),
        ("post", CHECKLIST_EVENTS),
        ("post", DELIVERIES),
        ("post", CONFIRM),
    ):
        responses = cast(dict[str, object], _operation(schema, path, method)["responses"])
        assert {"403", "404", "422"} <= set(responses), (
            f"{method.upper()} {path} must expose role, hidden-resource and forged-context refusal"
        )


def test_router_checks_every_same_account_relationship_before_delivery_write() -> None:
    """An account match alone is insufficient for nested renter document context."""
    module = _module()
    checker = getattr(module, "validate_delivery_relationships", None)
    assert callable(checker), "RED M9: delivery relationship validator is missing"

    context = SimpleNamespace(
        building_id="building-1",
        unit_id="unit-1",
        tenancy_id="tenancy-1",
        renter_id="renter-1",
        artifact_id="artifact-1",
    )
    checker(
        context,
        building=SimpleNamespace(id="building-1"),
        unit=SimpleNamespace(id="unit-1", building_id="building-1"),
        tenancy=SimpleNamespace(id="tenancy-1", unit_id="unit-1"),
        renter=SimpleNamespace(id="renter-1"),
        tenancy_party=SimpleNamespace(tenancy_id="tenancy-1", renter_id="renter-1"),
        artifact=SimpleNamespace(
            id="artifact-1",
            building_id="building-1",
            unit_id="unit-1",
            tenancy_id="tenancy-1",
            renter_id="renter-1",
        ),
    )

    for forged_name, forged in (
        ("building", SimpleNamespace(id="building-2")),
        ("unit", SimpleNamespace(id="unit-1", building_id="building-2")),
        ("tenancy", SimpleNamespace(id="tenancy-1", unit_id="unit-2")),
        ("renter", SimpleNamespace(id="renter-2")),
        (
            "tenancy_party",
            SimpleNamespace(tenancy_id="tenancy-1", renter_id="renter-2"),
        ),
        (
            "artifact",
            SimpleNamespace(
                id="artifact-1",
                building_id="building-1",
                unit_id="unit-1",
                tenancy_id="tenancy-1",
                renter_id="renter-2",
            ),
        ),
    ):
        values = {
            "building": SimpleNamespace(id="building-1"),
            "unit": SimpleNamespace(id="unit-1", building_id="building-1"),
            "tenancy": SimpleNamespace(id="tenancy-1", unit_id="unit-1"),
            "renter": SimpleNamespace(id="renter-1"),
            "tenancy_party": SimpleNamespace(tenancy_id="tenancy-1", renter_id="renter-1"),
            "artifact": SimpleNamespace(
                id="artifact-1",
                building_id="building-1",
                unit_id="unit-1",
                tenancy_id="tenancy-1",
                renter_id="renter-1",
            ),
        }
        values[forged_name] = forged
        with pytest.raises(HTTPException) as refused:
            checker(context, **values)
        assert refused.value.status_code in {404, 422}


@pytest.fixture
def live_delivery_api(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, dict[str, str], Any]]:
    """Run each delivery write inside one rollback-only migrated-Postgres graph."""

    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "m9r-live-secret-at-least-32-characters")
    settings = DbSettings()
    try:
        owner = create_db_engine(settings.direct_url)
        with owner.connect() as init_connection:
            init_connection.execute(
                text((_DB_PACKAGE_DIR / "scripts" / "init-app-role.sql").read_text())
            )
            init_connection.commit()
    except OperationalError as exc:
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")

    command.upgrade(Config(str(_DB_PACKAGE_DIR / "alembic.ini")), "head")
    connection = owner.connect()
    transaction = connection.begin()
    app: Any = None
    ids = {
        "account": "acc_m9r_live_delivery",
        "person": "per_m9r_live_owner",
        "membership": "mem_m9r_live_owner",
        "landlord": "lan_m9r_live",
        "building": "bld_m9r_live",
        "unit": "unit_m9r_live",
        "tenancy": "ten_m9r_live",
        "renter": "ren_m9r_live",
        "party": "tp_m9r_live",
        "statement": "stmt_m9r_live",
        "archive": "archive_m9r_live",
        "evaluation": "eval_m9r_live_w1",
        "artifact": "artifact_m9r_live_statement",
        "occurrence": "statement:2025:ren_m9r_live",
    }
    now = datetime(2026, 8, 25, 9, 0, tzinfo=UTC)
    content = b"%PDF-1.7\nM9-R live delivery fixture\n"
    try:
        with (
            Session(bind=connection, join_transaction_mode="create_savepoint") as session,
            session.begin(),
        ):
            for row in (
                Person(
                    id=ids["person"],
                    email="m9r-owner@lokara.example",
                    name="M9-R Eigentümer",
                ),
                Account(id=ids["account"], name="M9-R Zustellkonto"),
                Membership(
                    id=ids["membership"],
                    person_id=ids["person"],
                    account_id=ids["account"],
                    role=Role.OWNER,
                    accepted_at=now,
                    revoked_at=None,
                ),
                Landlord(
                    id=ids["landlord"],
                    account_id=ids["account"],
                    legal_name="M9-R Vermieter",
                    address="Testweg 1, 60311 Frankfurt am Main",
                ),
                Building(
                    id=ids["building"],
                    account_id=ids["account"],
                    landlord_id=ids["landlord"],
                    name="M9-R Testobjekt",
                    street="Testweg 1",
                    postal_code="60311",
                    city="Frankfurt am Main",
                    fiktivbelegung_waiver_note=None,
                    archived_at=None,
                ),
                Unit(
                    id=ids["unit"],
                    account_id=ids["account"],
                    building_id=ids["building"],
                    label="Wohnung 1",
                    area_sqm_x100=5000,
                ),
                Renter(
                    id=ids["renter"],
                    account_id=ids["account"],
                    legal_name="M9-R Mieter",
                    email="m9r-renter@lokara.example",
                    person_id=None,
                ),
                Tenancy(
                    id=ids["tenancy"],
                    account_id=ids["account"],
                    unit_id=ids["unit"],
                    valid_from=date(2025, 1, 1),
                    valid_to=None,
                    base_rent_cents=100_000,
                ),
                TenancyParty(
                    id=ids["party"],
                    account_id=ids["account"],
                    tenancy_id=ids["tenancy"],
                    renter_id=ids["renter"],
                ),
                Statement(
                    id=ids["statement"],
                    account_id=ids["account"],
                    building_id=ids["building"],
                    period_start=date(2025, 1, 1),
                    period_end=date(2025, 12, 31),
                    version=1,
                    total_cents=0,
                    content_hash=sha256(content).hexdigest(),
                    finalized_snapshot={},
                    finalized_at=now,
                    supersedes_statement_id=None,
                ),
                StatementArchive(
                    id=ids["archive"],
                    account_id=ids["account"],
                    statement_id=ids["statement"],
                    audience="TENANT",
                    tenancy_id=ids["tenancy"],
                    content_bytes=content,
                    sha256=sha256(content).hexdigest(),
                    mime_type="application/pdf",
                    filename="betriebskostenabrechnung-2025.pdf",
                ),
                GuardEvaluation(
                    id=ids["evaluation"],
                    account_id=ids["account"],
                    guard_code="W1",
                    subject_type="STATEMENT",
                    subject_id=ids["statement"],
                    building_id=ids["building"],
                    unit_id=ids["unit"],
                    tenancy_id=ids["tenancy"],
                    renter_id=ids["renter"],
                    occurrence_key=ids["occurrence"],
                    input_snapshot={},
                    result_snapshot={"boundary_date": "2026-08-20"},
                    rule_snapshot={"guard_code": "W1"},
                    evaluated_at=now,
                ),
                RenterDeliveryArtifact(
                    id=ids["artifact"],
                    account_id=ids["account"],
                    building_id=ids["building"],
                    unit_id=ids["unit"],
                    tenancy_id=ids["tenancy"],
                    renter_id=ids["renter"],
                    artifact_kind="ANNUAL_STATEMENT",
                    occurrence_key=ids["occurrence"],
                    statement_archive_id=ids["archive"],
                    uvi_run_id=None,
                    content_bytes=content,
                    sha256=sha256(content).hexdigest(),
                    mime_type="application/pdf",
                    filename="betriebskostenabrechnung-2025.pdf",
                    production_blockers_snapshot=["M9-R-EXPECTED-PRODUCTION-BLOCKER"],
                    generated_at=now,
                ),
            ):
                session.add(row)
                session.flush()

        from lokara_api import create_app
        from lokara_api.authorization import PortalScope
        from lokara_api.deps import account_session_for_path

        module = _module()
        app = create_app()

        def owner_session(account_id: str, auth: object | None = None) -> Iterator[Session]:
            del auth
            assert account_id == ids["account"]
            with (
                Session(bind=connection, join_transaction_mode="create_savepoint") as session,
                session.begin(),
            ):
                scope_values: dict[str, object] = {
                    "role": Role.OWNER,
                    "building_ids": frozenset(),
                }
                if "membership_id" in PortalScope.__dataclass_fields__:
                    scope_values["membership_id"] = ids["membership"]
                session.info["portal_scope"] = cast(Any, PortalScope)(**scope_values)
                yield session

        for route in app.routes:
            if not isinstance(route, APIRoute) or route.path not in {DELIVERIES, CONFIRM}:
                continue
            for dependency in route.dependant.dependencies:
                if dependency.call is account_session_for_path:
                    monkeypatch.setattr(dependency, "call", owner_session)
                elif dependency.call is module.delivery_clock:
                    monkeypatch.setattr(dependency, "call", lambda: now)
        with TestClient(app) as client:
            issued_at = int(time.time())
            token = jwt.encode(
                {
                    "sub": ids["person"],
                    "iss": str(ApiSettings().supabase_jwt_issuer),
                    "aud": "authenticated",
                    "role": "authenticated",
                    "iat": issued_at,
                    "exp": issued_at + 3600,
                },
                ApiSettings().supabase_jwt_secret,
                algorithm="HS256",
            )
            client.headers["Authorization"] = f"Bearer {token}"
            yield client, ids, connection
    finally:
        if app is not None:
            app.dependency_overrides.clear()
        transaction.rollback()
        connection.close()
        owner.dispose()


def test_delivery_post_executes_the_real_orm_relationship_path(
    live_delivery_api: tuple[TestClient, dict[str, str], Any],
) -> None:
    client, ids, _connection = live_delivery_api
    response = client.post(
        f"/a/{ids['account']}/deliveries",
        json={
            "buildingId": ids["building"],
            "renterId": ids["renter"],
            "artifactId": ids["artifact"],
            "deliveryKind": "ANNUAL_STATEMENT",
            "occurrenceKey": ids["occurrence"],
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["blockedReason"] == "PRODUCTION_BLOCKED"


def test_delivery_confirmation_executes_the_real_owner_evidence_constraints(
    live_delivery_api: tuple[TestClient, dict[str, str], Any],
) -> None:
    client, ids, _connection = live_delivery_api
    response = client.post(
        f"/a/{ids['account']}/deliveries/{ids['artifact']}/confirm",
        json={
            "deliveredOn": "2026-08-20",
            "evidenceReference": "Einschreiben M9-R 2026-08-20",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["legallyConfirmed"] is True


@pytest.mark.parametrize("role", (Role.OWNER, Role.EMPLOYEE))
def test_pending_membership_cannot_obtain_account_scope(
    live_delivery_api: tuple[TestClient, dict[str, str], Any],
    monkeypatch: pytest.MonkeyPatch,
    role: Role,
) -> None:
    """The real account dependency must reject an invitation before acceptance."""

    _client, ids, connection = live_delivery_api
    suffix = role.value.lower()
    person_id = f"per_m9r_pending_{suffix}"
    membership_id = f"mem_m9r_pending_{suffix}"
    with (
        Session(bind=connection, join_transaction_mode="create_savepoint") as session,
        session.begin(),
    ):
        session.add(
            Person(
                id=person_id,
                email=f"m9r-pending-{suffix}@lokara.example",
                name=f"M9-R pending {role.value}",
            )
        )
        session.flush()
        session.add(
            Membership(
                id=membership_id,
                person_id=person_id,
                account_id=ids["account"],
                role=role,
                accepted_at=None,
                revoked_at=None,
            )
        )
        session.flush()
        if role is Role.EMPLOYEE:
            session.add(
                BuildingAssignment(
                    id="assignment_m9r_pending_employee",
                    account_id=ids["account"],
                    membership_id=membership_id,
                    building_id=ids["building"],
                )
            )
            session.flush()

    import lokara_api.deps as deps

    @contextmanager
    def rollback_scoped_session(_engine: object, account_id: str) -> Iterator[Session]:
        assert account_id == ids["account"]
        with (
            Session(bind=connection, join_transaction_mode="create_savepoint") as session,
            session.begin(),
        ):
            yield session

    monkeypatch.setattr(deps, "account_scoped_session", rollback_scoped_session)
    dependency = cast(
        Generator[Session],
        deps.account_session_for_path(
            ids["account"], cast(Any, SimpleNamespace(person_id=person_id))
        ),
    )
    try:
        with pytest.raises(HTTPException) as refused:
            next(dependency)
        assert refused.value.status_code == 403
    finally:
        dependency.close()


def test_delivery_legal_event_query_binds_the_immutable_artifact_column() -> None:
    module = _module()
    captured: list[object] = []

    class _Session:
        def scalar(self, statement: object) -> None:
            captured.append(statement)
            return None

    artifact = SimpleNamespace(
        id="artifact-bound-1",
        building_id="building-1",
        unit_id="unit-1",
        tenancy_id="tenancy-1",
        renter_id="renter-1",
        occurrence_key="statement:2025:renter-1",
    )
    module._legal_event(_Session(), "account-1", artifact)

    query = cast(Any, captured[0])
    criteria = " ".join(str(clause) for clause in query._where_criteria)
    assert "guard_resolution_event.renter_delivery_artifact_id" in criteria
    assert "event_snapshot" not in criteria
    assert "guard_evaluation.occurrence_key" in criteria
