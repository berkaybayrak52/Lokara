"""Red M9 job-boundary contracts.

The persistence-backed behavioral suite follows after migration 0025 exists.
These fixtures first pin the public, explicit-clock/account boundary and the
blocked/idempotent result vocabulary so an implementation cannot hide those
states behind a worker or provider.
"""

import os
from dataclasses import fields, is_dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from hashlib import sha256
from inspect import Parameter, signature
from types import SimpleNamespace
from typing import Any, cast

import lokara_api.jobs as jobs
import pytest
from lokara_adapters import DeliveryStatus, EmailDeliveryReceipt
from lokara_db import (
    Building,
    DeliveryScheduleVersion,
    EmailAttempt,
    EmailDeliveryStatusEvent,
    Landlord,
    RenterDeliveryArtifact,
    Statement,
    StatementArchive,
)
from lokara_domain import Period

ENTRYPOINTS = (
    "run_daily_guard_evaluations",
    "dispatch_guard_reminders",
    "schedule_renter_deliveries",
)


def _symbol(name: str) -> Any:
    value = getattr(jobs, name, None)
    assert value is not None, f"M9 jobs boundary is missing {name}"
    return value


def test_m9_job_entrypoints_exist_with_explicit_account_and_clocks() -> None:
    for name in ENTRYPOINTS:
        function = _symbol(name)
        parameters = signature(function).parameters
        assert "account_id" in parameters, name
        assert "today" in parameters, name
        assert "now" in parameters, name
        assert all(parameter not in parameters for parameter in ("account_ids", "accounts")), name


def test_guard_job_result_exposes_idempotent_occurrences_and_push_limitation() -> None:
    result_type = _symbol("GuardEvaluationJobResult")
    assert is_dataclass(result_type)
    names = {field.name for field in fields(result_type)}
    assert {
        "account_id",
        "evaluated_occurrences",
        "existing_occurrences",
        "created_reminders",
        "push_available",
        "production_blockers",
    } <= names


def test_reminder_dispatch_result_keeps_blocked_reasons_visible() -> None:
    result_type = _symbol("ReminderDispatchResult")
    assert is_dataclass(result_type)
    names = {field.name for field in fields(result_type)}
    assert {
        "account_id",
        "queued",
        "already_dispatched",
        "blocked",
        "push_unavailable",
    } <= names


def test_delivery_job_result_distinguishes_provider_delivery_from_legal_receipt() -> None:
    result_type = _symbol("RenterDeliveryJobResult")
    assert is_dataclass(result_type)
    names = {field.name for field in fields(result_type)}
    assert {
        "account_id",
        "scheduled",
        "queued",
        "already_processed",
        "blocked",
        "provider_delivered",
        "legally_confirmed",
    } <= names


def test_delivery_block_reasons_cover_every_no_send_boundary() -> None:
    reason_type = _symbol("DeliveryBlockReason")
    assert {item.value for item in reason_type} >= {
        "SCHEDULE_DISABLED",
        "MISSING_EMAIL",
        "RECIPIENT_SUPPRESSED",
        "PRODUCTION_BLOCKED",
        "MISSING_ARTIFACT",
        "HASH_MISMATCH",
    }


def test_delivery_status_does_not_equal_owner_confirmation() -> None:
    confirmation_type = _symbol("LegalDeliveryConfirmation")
    assert is_dataclass(confirmation_type)
    names = {field.name for field in fields(confirmation_type)}
    assert {"delivered_on", "evidence_reference"} <= names
    assert "provider_status" not in names


def test_delivery_job_legal_confirmation_query_binds_the_immutable_artifact_column() -> None:
    captured: list[object] = []
    events = [
        SimpleNamespace(
            renter_delivery_artifact_id="artifact-bound-1",
            event_snapshot={
                "artifact_id": "forged-json-artifact",
                "delivered_on": "2026-08-20",
            },
            evidence_reference="Einschreiben 2026-08-20",
        )
    ]

    class _Session:
        def scalars(self, statement: object) -> object:
            captured.append(statement)
            return SimpleNamespace(all=lambda: events)

    artifact = SimpleNamespace(
        id="artifact-bound-1",
        building_id="building-1",
        unit_id="unit-1",
        tenancy_id="tenancy-1",
        renter_id="renter-1",
        occurrence_key="statement:2025:renter-1",
    )
    confirmed = jobs._legal_confirmation_exists(
        cast(Any, _Session()),
        account_id="account-1",
        artifact=cast(Any, artifact),
    )

    query = cast(Any, captured[0])
    criteria = " ".join(str(clause) for clause in query._where_criteria)
    assert "guard_resolution_event.renter_delivery_artifact_id" in criteria
    assert "guard_evaluation.occurrence_key" in criteria
    assert confirmed is True, "bound column evidence must not depend on mutable JSON identity"


def test_schedule_kinds_are_only_opt_in_annual_statement_and_uvi() -> None:
    kind_type = _symbol("ScheduledDeliveryKind")
    assert {item.value for item in kind_type} == {"ANNUAL_STATEMENT", "UVI"}


def test_delivery_request_cannot_supply_server_derived_production_eligibility() -> None:
    request_type = _symbol("RenterDeliveryRequest")
    names = {field.name for field in fields(request_type)}
    assert "production_blockers" not in names


def test_schedule_job_derives_due_occurrences_instead_of_accepting_caller_requests() -> None:
    parameters = signature(_symbol("schedule_renter_deliveries")).parameters
    assert "requests" not in parameters
    assert all(parameter.kind is not Parameter.VAR_KEYWORD for parameter in parameters.values())


def test_one_artifact_dispatch_has_an_explicit_request_boundary() -> None:
    parameters = signature(_symbol("dispatch_renter_artifact")).parameters
    assert set(parameters) == {
        "session",
        "account_id",
        "today",
        "now",
        "request",
        "gateway",
    }
    assert parameters["session"].kind is Parameter.POSITIONAL_OR_KEYWORD
    assert all(
        parameters[name].kind is Parameter.KEYWORD_ONLY
        for name in ("account_id", "today", "now", "request", "gateway")
    )
    assert all(parameter.kind is not Parameter.VAR_KEYWORD for parameter in parameters.values())


def test_artifact_freezer_has_only_server_source_inputs() -> None:
    parameters = signature(_symbol("freeze_renter_delivery_artifact")).parameters
    assert set(parameters) == {
        "session",
        "account_id",
        "source_kind",
        "source_id",
        "renter_id",
        "occurrence_key",
        "now",
    }
    assert {
        "content_bytes",
        "sha256",
        "production_blockers",
        "production_blockers_snapshot",
        "building_id",
        "unit_id",
        "tenancy_id",
    }.isdisjoint(parameters)

    result_type = _symbol("ArtifactFreezeResult")
    assert is_dataclass(result_type)
    assert {"artifact", "created", "blocked_reason", "detail"} <= {
        field.name for field in fields(result_type)
    }


class _ReminderSession:
    def scalars(self, _statement: object) -> object:
        return SimpleNamespace(
            all=lambda: [
                SimpleNamespace(id="email-reminder", channel="EMAIL"),
                SimpleNamespace(id="in-app-reminder", channel="IN_APP"),
            ]
        )


def test_reminders_without_a_dispatch_provider_are_blocked_not_fake_queued() -> None:
    result = jobs.dispatch_guard_reminders(
        _ReminderSession(),  # type: ignore[arg-type]
        account_id="account-1",
        today=date(2026, 8, 25),
        now=datetime(2026, 8, 25, 9, 0, tzinfo=UTC),
    )
    assert result.queued == 0
    assert {item.reminder_id for item in result.blocked} == {
        "email-reminder",
        "in-app-reminder",
    }
    assert all("nicht verfügbar" in item.reason.lower() for item in result.blocked)


class _ClaimSession:
    def __init__(self, scalar_values: list[object]) -> None:
        self._scalar_values = iter(scalar_values)
        self.added: list[object] = []
        self.flushed: list[object] = []

    def scalar(self, _statement: object) -> object:
        return next(self._scalar_values)

    def scalars(self, _statement: object) -> object:
        return SimpleNamespace(all=lambda: [])

    def add(self, value: object) -> None:
        self.added.append(value)

    def flush(self) -> None:
        self.flushed.extend(self.added[len(self.flushed) :])


class _ClaimCheckingGateway:
    provider_idempotency_enforced = True

    def __init__(self, session: _ClaimSession, now: datetime) -> None:
        self.session = session
        self.now = now
        self.calls = 0

    def send(self, _email: object) -> EmailDeliveryReceipt:
        self.calls += 1
        assert any(isinstance(item, EmailAttempt) for item in self.session.flushed), (
            "the local attempt must be staged before the provider-idempotent send"
        )
        return EmailDeliveryReceipt(
            message_id="provider-message-1",
            status=DeliveryStatus.QUEUED,
            accepted_at=self.now,
        )


class _NoSendGateway:
    provider_idempotency_enforced = True

    def send(self, _email: object) -> EmailDeliveryReceipt:
        raise AssertionError("an existing durable claim must suppress a duplicate send")


class _UnverifiedGateway:
    provider_idempotency_enforced = False

    def __init__(self) -> None:
        self.calls = 0

    def send(self, _email: object) -> EmailDeliveryReceipt:
        self.calls += 1
        raise AssertionError("gateway without provider idempotency must never be called")


class _UnexpectedSendGateway:
    provider_idempotency_enforced = True

    def __init__(self) -> None:
        self.calls = 0

    def send(self, _email: object) -> EmailDeliveryReceipt:
        self.calls += 1
        return EmailDeliveryReceipt(
            message_id="must-not-send",
            status=DeliveryStatus.QUEUED,
            accepted_at=datetime(2026, 8, 25, 9, 0, tzinfo=UTC),
        )


@pytest.mark.parametrize("asynchronous_status", ("BOUNCED", "COMPLAINED"))
def test_async_negative_status_history_suppresses_future_occurrence_dispatch(
    asynchronous_status: str,
) -> None:
    """A later provider event is authoritative even if its suppression insert was missed."""
    content = b"future occurrence after asynchronous negative status"
    artifact = SimpleNamespace(
        id="artifact-future",
        content_bytes=content,
        sha256=sha256(content).hexdigest(),
        filename="future.pdf",
        mime_type="application/pdf",
        production_blocked=False,
        production_blockers_snapshot=(),
    )

    class _AsyncHistorySession(_ClaimSession):
        def scalars(self, statement: object) -> object:
            entity = statement.column_descriptions[0].get("entity")  # type: ignore[attr-defined]
            rows = [asynchronous_status] if entity is EmailDeliveryStatusEvent else []
            return SimpleNamespace(all=lambda: rows)

    session = _AsyncHistorySession(
        [
            SimpleNamespace(id="renter-1", email="Mieter@Example.de"),
            None,
            artifact,
            None,
        ]
    )
    gateway = _UnexpectedSendGateway()
    result = jobs.dispatch_renter_artifact(
        session,  # type: ignore[arg-type]
        account_id="account-1",
        today=date(2026, 8, 25),
        now=datetime(2026, 8, 25, 9, 0, tzinfo=UTC),
        request=jobs.RenterDeliveryRequest(
            building_id="building-1",
            renter_id="renter-1",
            delivery_kind=jobs.ScheduledDeliveryKind.ANNUAL_STATEMENT,
            occurrence_key="statement:2026:renter-1",
            subject_de="Ihre Betriebskostenabrechnung",
            html_body_de="Dokument im Anhang.",
            from_name="Vermieter Beispiel",
            sender_address="zustellung@lokara.de",
            artifact_id=artifact.id,
        ),
        gateway=gateway,
    )

    assert gateway.calls == 0
    assert result.blocked[0].reason is jobs.DeliveryBlockReason.RECIPIENT_SUPPRESSED


def test_email_attempt_claim_is_recorded_before_idempotent_gateway_side_effect() -> None:
    now = datetime(2026, 8, 25, 9, 0, tzinfo=UTC)
    content = b"immutable statement bytes"
    request = jobs.RenterDeliveryRequest(
        building_id="building-1",
        renter_id="renter-1",
        delivery_kind=jobs.ScheduledDeliveryKind.ANNUAL_STATEMENT,
        occurrence_key="statement:2025:renter-1",
        subject_de="Ihre Betriebskostenabrechnung",
        html_body_de="Dokument im Anhang.",
        from_name="Vermieter Beispiel",
        sender_address="zustellung@lokara.de",
        artifact_id="artifact-1",
    )
    session = _ClaimSession(
        [
            SimpleNamespace(id="renter-1", email="mieter@example.de"),
            None,
            SimpleNamespace(
                id="artifact-1",
                content_bytes=content,
                sha256=sha256(content).hexdigest(),
                filename="abrechnung.pdf",
                mime_type="application/pdf",
                production_blocked=False,
            ),
            None,
        ]
    )
    gateway = _ClaimCheckingGateway(session, now)

    dispatch = _symbol("dispatch_renter_artifact")
    dispatch(
        session,
        account_id="account-1",
        today=date(2026, 8, 25),
        now=now,
        request=request,
        gateway=gateway,
    )
    assert gateway.calls == 1


def test_dispatch_refuses_gateway_without_provider_idempotency_guarantee() -> None:
    now = datetime(2026, 8, 25, 9, 0, tzinfo=UTC)
    content = b"immutable statement bytes"
    request = jobs.RenterDeliveryRequest(
        building_id="building-1",
        renter_id="renter-1",
        delivery_kind=jobs.ScheduledDeliveryKind.ANNUAL_STATEMENT,
        occurrence_key="statement:2025:renter-1",
        subject_de="Ihre Betriebskostenabrechnung",
        html_body_de="Dokument im Anhang.",
        from_name="Vermieter Beispiel",
        sender_address="zustellung@lokara.de",
        artifact_id="artifact-1",
    )
    session = _ClaimSession(
        [
            SimpleNamespace(id="renter-1", email="mieter@example.de"),
            None,
            SimpleNamespace(
                id="artifact-1",
                content_bytes=content,
                sha256=sha256(content).hexdigest(),
                filename="abrechnung.pdf",
                mime_type="application/pdf",
                production_blocked=False,
                production_blockers_snapshot=(),
            ),
            None,
        ]
    )
    gateway = _UnverifiedGateway()
    dispatch = _symbol("dispatch_renter_artifact")

    result = dispatch(
        session,
        account_id="account-1",
        today=date(2026, 8, 25),
        now=now,
        request=request,
        gateway=gateway,
    )

    assert gateway.calls == 0
    assert result.blocked[0].reason is jobs.DeliveryBlockReason.IDEMPOTENCY_UNAVAILABLE


def test_existing_email_claim_makes_duplicate_and_retry_runs_no_send() -> None:
    now = datetime(2026, 8, 25, 9, 0, tzinfo=UTC)
    content = b"immutable statement bytes"
    request = jobs.RenterDeliveryRequest(
        building_id="building-1",
        renter_id="renter-1",
        delivery_kind=jobs.ScheduledDeliveryKind.ANNUAL_STATEMENT,
        occurrence_key="statement:2025:renter-1",
        subject_de="Ihre Betriebskostenabrechnung",
        html_body_de="Dokument im Anhang.",
        from_name="Vermieter Beispiel",
        sender_address="zustellung@lokara.de",
        artifact_id="artifact-1",
    )
    session = _ClaimSession(
        [
            SimpleNamespace(id="renter-1", email="mieter@example.de"),
            None,
            SimpleNamespace(
                id="artifact-1",
                content_bytes=content,
                sha256=sha256(content).hexdigest(),
                filename="abrechnung.pdf",
                mime_type="application/pdf",
                production_blocked=False,
            ),
            SimpleNamespace(id="durable-attempt-1"),
        ]
    )
    dispatch = _symbol("dispatch_renter_artifact")
    result = dispatch(
        session,
        account_id="account-1",
        today=date(2026, 8, 25),
        now=now,
        request=request,
        gateway=_NoSendGateway(),
    )
    assert result.already_processed == 1
    assert result.queued == 0


def test_statement_artifact_freezer_copies_exact_archive_and_is_idempotent() -> None:
    now = datetime(2026, 8, 25, 9, 0, tzinfo=UTC)
    content = b"exact finalized tenant statement"
    archive = SimpleNamespace(
        id="statement-archive-1",
        account_id="account-1",
        statement_id="statement-1",
        tenancy_id="tenancy-1",
        audience="TENANT",
        content_bytes=content,
        sha256=sha256(content).hexdigest(),
        mime_type="application/pdf",
        filename="abrechnung-2025.pdf",
    )
    session = _ClaimSession(
        [
            None,
            archive,
            SimpleNamespace(
                id="statement-1",
                building_id="building-1",
                finalized_snapshot={
                    "production_blockers": [
                        "verify-before-production",
                        "missing-approved-delivery-copy",
                    ]
                },
            ),
            SimpleNamespace(id="tenancy-1", unit_id="unit-1"),
            SimpleNamespace(id="unit-1", building_id="building-1"),
            SimpleNamespace(tenancy_id="tenancy-1", renter_id="renter-1"),
        ]
    )
    freeze = _symbol("freeze_renter_delivery_artifact")
    first = freeze(
        session,
        account_id="account-1",
        source_kind=jobs.ScheduledDeliveryKind.ANNUAL_STATEMENT,
        source_id=archive.id,
        renter_id="renter-1",
        occurrence_key="statement:2025:renter-1",
        now=now,
    )
    artifacts = [item for item in session.added if isinstance(item, RenterDeliveryArtifact)]
    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact.content_bytes is content
    assert artifact.sha256 == archive.sha256
    assert artifact.statement_archive_id == archive.id
    assert artifact.uvi_run_id is None
    assert artifact.building_id == "building-1"
    assert artifact.unit_id == "unit-1"
    assert artifact.tenancy_id == "tenancy-1"
    assert artifact.renter_id == "renter-1"
    assert artifact.occurrence_key == "statement:2025:renter-1"
    # This stub statement freezes a blocker list without the Page-01 inventory it was
    # derived from, so the freezer records the incomplete authority envelope ahead of
    # the stored blockers rather than copying a half envelope through as if clean.
    assert artifact.production_blockers_snapshot == [
        "STATEMENT-AUTHORITY-ENVELOPE-INCOMPLETE",
        "verify-before-production",
        "missing-approved-delivery-copy",
    ]
    assert first.artifact is artifact
    assert first.created is True

    replay_session = _ClaimSession([artifact])
    replay = freeze(
        replay_session,
        account_id="account-1",
        source_kind=jobs.ScheduledDeliveryKind.ANNUAL_STATEMENT,
        source_id=archive.id,
        renter_id="renter-1",
        occurrence_key="statement:2025:renter-1",
        now=now,
    )
    assert replay.artifact is artifact
    assert replay.created is False
    assert replay_session.added == []


def test_uvi_blockers_are_derived_from_the_bound_run_and_rechecked_at_dispatch() -> None:
    run = SimpleNamespace(
        id="uvi-run-1",
        account_id="account-1",
        tenancy_id="tenancy-1",
        unit_id="unit-1",
        results={
            "production_blocked": True,
            "unresolved_conflicts": [
                {
                    "code": "UVI-SOURCE-CONFLICT",
                    "description": "UVI-Quelle muss vor Produktion geprüft werden.",
                    "production_blocking": True,
                }
            ],
        },
    )
    derive = _symbol("derive_uvi_production_blockers")
    blockers = derive(run)
    assert blockers
    assert any("UVI-SOURCE-CONFLICT" in blocker for blocker in blockers)

    content = b"forged legacy UVI bytes"
    artifact = SimpleNamespace(
        id="artifact-uvi-1",
        building_id="building-1",
        unit_id="unit-1",
        tenancy_id="tenancy-1",
        renter_id="renter-1",
        artifact_kind="UVI",
        occurrence_key="uvi:2026-07:renter-1",
        statement_archive_id=None,
        uvi_run_id=run.id,
        content_bytes=content,
        sha256=sha256(content).hexdigest(),
        filename="uvi.pdf",
        mime_type="application/pdf",
        production_blocked=False,
        production_blockers_snapshot=(),
    )
    request = jobs.RenterDeliveryRequest(
        building_id="building-1",
        renter_id="renter-1",
        delivery_kind=jobs.ScheduledDeliveryKind.UVI,
        occurrence_key=artifact.occurrence_key,
        subject_de="Ihre monatliche Verbrauchsinformation",
        html_body_de="Dokument im Anhang.",
        from_name="Vermieter Beispiel",
        sender_address="zustellung@lokara.de",
        artifact_id=artifact.id,
    )
    session = _ClaimSession(
        [
            SimpleNamespace(id="renter-1", email="mieter@example.de"),
            None,
            artifact,
            run,
        ]
    )
    dispatch = _symbol("dispatch_renter_artifact")
    result = dispatch(
        session,
        account_id="account-1",
        today=date(2026, 8, 25),
        now=datetime(2026, 8, 25, 9, 0, tzinfo=UTC),
        request=request,
        gateway=_NoSendGateway(),
    )
    assert result.blocked[0].reason is jobs.DeliveryBlockReason.PRODUCTION_BLOCKED
    assert "UVI-SOURCE-CONFLICT" in result.blocked[0].detail


def test_uvi_freezer_reports_missing_document_bytes_instead_of_inventing_them() -> None:
    run = SimpleNamespace(
        id="uvi-run-without-bytes",
        account_id="account-1",
        tenancy_id="tenancy-1",
        unit_id="unit-1",
        results={"production_blocked": False, "unresolved_conflicts": []},
    )
    session = _ClaimSession([None, run])
    freeze = _symbol("freeze_renter_delivery_artifact")
    result = freeze(
        session,
        account_id="account-1",
        source_kind=jobs.ScheduledDeliveryKind.UVI,
        source_id=run.id,
        renter_id="renter-1",
        occurrence_key="uvi:2026-07:renter-1",
        now=datetime(2026, 8, 25, 9, 0, tzinfo=UTC),
    )
    assert result.artifact is None
    assert result.created is False
    assert result.blocked_reason is jobs.DeliveryBlockReason.MISSING_ARTIFACT
    assert "Dokument" in result.detail or "Bytes" in result.detail
    assert not any(isinstance(item, RenterDeliveryArtifact) for item in session.added)


def _real_finalized_snapshot_with_open_legal_surfaces() -> dict[str, object]:
    """Build the exact M6-B envelope instead of inventing an M9-only shape."""
    from lokara_api.routers.finalized_statements import _finalized_snapshot

    projection = SimpleNamespace(
        audience=SimpleNamespace(value="OWNER"),
        tenancy_id=None,
        window=Period(date(2025, 1, 1), date(2026, 1, 1)),
        nk_costs=(),
        nk_lines=(),
        heating_lines=(),
        owner_residual=None,
        party_labels={},
        findings=(),
        non_allocable_costs=(),
    )
    tenant_projection = SimpleNamespace(**{**projection.__dict__, "tenancy_id": "tenancy-1"})
    bundle = SimpleNamespace(
        normalized_inputs={
            "nk": {
                "rule_evidence": [
                    {
                        "code": "STATEMENT-NK-RULE-VERIFY",
                        "verification_status": "verify-before-production",
                    }
                ]
            },
            "page01b": {
                "legal_status": [
                    {
                        "code": "STATEMENT-HKV-LEGAL-VERIFY",
                        "status": "verify-before-production",
                    }
                ]
            },
        },
        rechtsstaende=("08/2026",),
        rechtsstand_entries=("§ 556 BGB — 08/2026",),
        nk_result={
            "production_blocked": True,
            "production_blockers": ["STATEMENT-NK-SUMMARY-BLOCKED"],
        },
        heating_result=None,
        page01b_result=None,
        heating_input_total=Decimal("12.34"),
        heating_missing_reason=None,
        nk_findings=("STATEMENT-FINDING-VERIFY: verify-before-production",),
    )
    address = SimpleNamespace(
        id="address-1",
        version=1,
        valid_from=date(2025, 1, 1),
        addressee="Anna Beispiel",
        street="Musterstraße 1",
        postal_code="10115",
        city="Berlin",
        country="DE",
    )
    reconciliation = SimpleNamespace(id="recon-1", version=1, total_cents=100)
    instruction = SimpleNamespace(
        id="instruction-1",
        version=1,
        valid_from=date(2025, 1, 1),
        instruction_text="Text",
    )
    return _finalized_snapshot(
        bundle=bundle,  # type: ignore[arg-type]
        owner_projection=projection,  # type: ignore[arg-type]
        vacancy_projection=projection,  # type: ignore[arg-type]
        eligible=cast(
            Any,
            [
                (
                    SimpleNamespace(
                        id="tenancy-1",
                        unit=SimpleNamespace(label="WE 1"),
                        valid_from=date(2025, 1, 1),
                        valid_to=None,
                    ),
                    tenant_projection,
                    address,
                    reconciliation,
                    200,
                    100,
                )
            ],
        ),
        instruction=cast(Any, instruction),
        exception_reason=None,
        landlord_name="Vermieter Beispiel",
        building_name="Musterhaus",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
    )


def test_real_finalized_snapshot_cannot_omit_or_bypass_legal_blockers() -> None:
    snapshot = _real_finalized_snapshot_with_open_legal_surfaces()
    assert "production_blockers" in snapshot, (
        "the real _finalized_snapshot envelope must never make absence mean production-safe"
    )
    blockers = snapshot["production_blockers"]
    assert isinstance(blockers, list)
    joined = " | ".join(str(item) for item in blockers)
    for marker in (
        "STATEMENT-NK-RULE-VERIFY",
        "STATEMENT-HKV-LEGAL-VERIFY",
        "STATEMENT-NK-SUMMARY-BLOCKED",
        "STATEMENT-FINDING-VERIFY",
    ):
        assert marker in joined

    content = b"exact finalized tenant statement"
    archive = SimpleNamespace(
        id="statement-archive-real-shape",
        account_id="account-1",
        statement_id="statement-real-shape",
        tenancy_id="tenancy-1",
        audience="TENANT",
        content_bytes=content,
        sha256=sha256(content).hexdigest(),
        mime_type="application/pdf",
        filename="abrechnung-2025.pdf",
    )
    session = _ClaimSession(
        [
            None,
            archive,
            SimpleNamespace(
                id="statement-real-shape",
                building_id="building-1",
                finalized_snapshot=snapshot,
            ),
            SimpleNamespace(id="tenancy-1", unit_id="unit-1"),
            SimpleNamespace(id="unit-1", building_id="building-1"),
            SimpleNamespace(tenancy_id="tenancy-1", renter_id="renter-1"),
        ]
    )
    result = jobs.freeze_renter_delivery_artifact(
        session,  # type: ignore[arg-type]
        account_id="account-1",
        source_kind=jobs.ScheduledDeliveryKind.ANNUAL_STATEMENT,
        source_id=archive.id,
        renter_id="renter-1",
        occurrence_key="statement:2025:renter-1",
        now=datetime(2026, 8, 25, 9, 0, tzinfo=UTC),
    )
    assert result.artifact is not None
    artifact_blockers = " | ".join(
        str(item) for item in result.artifact.production_blockers_snapshot
    )
    assert artifact_blockers == joined


def test_real_statement_service_freezes_the_exact_page01_authority_inventory() -> None:
    """The M9 freezer consumes server-owned rule evidence, never invented input keys."""
    import lokara_rules_store as rules_store

    resolve = getattr(rules_store, "resolve_page01_statement_rules", None)
    assert callable(resolve), (
        "RED M9: rules-store must own a versioned Page-01 statement-authority resolver"
    )

    expected_flagged = (
        "Fiktivbelegung bei Leerstand",
        "Gradtagszahltabelle VDI (K3)",
        "Kürzungsrecht — fehlende fernablesbare Ausstattung",
        "Rundungsweg (Seite 01 / docs/03 § 6)",
        "Geräteliste auf der Mieterausfertigung (K10)",
        "Zahlungsfrist bei Nachzahlung",
        "Verteilungsrest (K9)",
        "Grundkostenanteil (K1)",
        (
            "Kürzungsrecht — fehlende oder unvollständige § 6a-Information "
            "(UVI + Abrechnungs-Infoblock)"
        ),
        "Verbrauchsvergleich — Umfang und Bereinigung",
        "Grundkosten-Verteilung nach m²-Tagen (K2)",
        "§ 35a-Block auf der Betriebskostenabrechnung",
        "Wording Leerstandsaufstellung",
        "Kürzungsrecht — CO₂-Anteil nicht ausgewiesen",
        "CO₂-Mieteranteil — Pro-rata-Ableitung (D7 Schritt 6)",
    )
    authority = resolve(date(2026, 8, 25))
    evidence = tuple(authority.evidence)
    assert len(evidence) == 26
    assert (
        tuple(row.name for row in evidence if row.verification_status == "verify-before-production")
        == expected_flagged
    )
    assert sum(row.verification_status == "geprüft" for row in evidence) == 11
    for row in evidence:
        assert row.source
        assert row.legal_basis
        assert row.rechtsnatur
        assert row.rechtsstand

    # Continue through the real statement service and the real M6-B finalizer.
    # If Postgres is unavailable locally this second half skips, while CI requires it.
    from lokara_api.routers.finalized_statements import _finalized_snapshot
    from lokara_api.statement_service import (
        StatementAudience,
        compute_statement,
        project_statement,
    )
    from lokara_db import DbSettings, create_db_engine
    from lokara_db.seed import seed_demo
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import Session

    engine = create_db_engine(DbSettings().direct_url)
    try:
        with Session(engine) as session, session.begin():
            seed_demo(session)
            bundle = compute_statement(session, building_id="bld_demo_muster12")
            frozen_evidence = tuple(bundle.statement_rule_evidence)
            assert tuple(row["name"] for row in frozen_evidence) == tuple(
                row.name for row in evidence
            )
            assert tuple(row["verification_status"] for row in frozen_evidence) == tuple(
                row.verification_status for row in evidence
            )
            owner = project_statement(bundle, StatementAudience.OWNER)
            vacancy = project_statement(bundle, StatementAudience.TAX)
            snapshot = _finalized_snapshot(
                bundle=bundle,
                owner_projection=owner,
                vacancy_projection=vacancy,
                eligible=[],
                instruction=cast(
                    Any,
                    SimpleNamespace(
                        id="authority-test-instruction",
                        version=1,
                        valid_from=date(2025, 1, 1),
                        instruction_text="Test",
                    ),
                ),
                exception_reason=None,
                period_start=date(2025, 1, 1),
                period_end=date(2025, 12, 31),
            )
    except OperationalError as exc:
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable: {exc}")
    finally:
        engine.dispose()

    assert snapshot["statement_rule_evidence"] == list(frozen_evidence)
    production_blockers = snapshot["production_blockers"]
    assert isinstance(production_blockers, list)
    blocker_text = " | ".join(str(item) for item in production_blockers)
    assert all(name in blocker_text for name in expected_flagged)
    derived_blockers = " | ".join(
        str(item) for item in jobs.derive_statement_production_blockers(snapshot)
    )
    assert all(name in derived_blockers for name in expected_flagged)


@pytest.mark.parametrize(
    "snapshot",
    (
        {"statement_rule_evidence": []},
        {"production_blockers": []},
        {
            "production_blockers": [],
            "statement_rule_evidence": [
                {
                    "name": "Fiktivbelegung bei Leerstand",
                    "verification_status": "verify-before-production",
                    "rechtsstand": "07/2026",
                }
            ],
        },
        {
            "production_blockers": [],
            "statement_rule_evidence": [
                {
                    "name": f"invented-row-{index}",
                    "verification_status": "geprüft",
                    "rechtsstand": "99/9999",
                }
                for index in range(26)
            ],
        },
    ),
)
def test_statement_delivery_fails_closed_without_exact_complete_authority_envelope(
    snapshot: dict[str, object],
) -> None:
    blockers = jobs.derive_statement_production_blockers(snapshot)
    assert "STATEMENT-AUTHORITY-ENVELOPE-INCOMPLETE" in blockers


def test_statement_delivery_derives_blockers_from_the_published_authority_inventory() -> None:
    """A writer cannot clear delivery by emitting an empty blocker projection."""

    from dataclasses import asdict

    from lokara_rules_store.page01_statement import PAGE_01_STATEMENT_RULES

    published_evidence = [asdict(row) for row in PAGE_01_STATEMENT_RULES.versions[0].value.evidence]
    expected_identities = (
        "Kürzungsrecht — CO₂-Anteil nicht ausgewiesen",
        "CO₂-Mieteranteil — Pro-rata-Ableitung (D7 Schritt 6)",
    )
    published_by_name = {row["name"]: row for row in published_evidence}
    assert all(
        published_by_name[identity]["verification_status"] == "verify-before-production"
        for identity in expected_identities
    )

    blockers = jobs.derive_statement_production_blockers(
        {
            "production_blockers": [],
            "statement_rule_evidence": published_evidence,
        }
    )
    blocker_text = " | ".join(str(item) for item in blockers)
    missing = [identity for identity in expected_identities if identity not in blocker_text]
    assert not missing, (
        "published verify-before-production evidence must remain delivery blockers; "
        f"missing {missing}"
    )


@pytest.mark.parametrize(
    ("results", "marker"),
    (
        (
            {
                "rule_evidence": [
                    {
                        "source": "DWD-row",
                        "verification_status": "verify-before-production",
                    }
                ],
                "production_blocked": False,
            },
            "DWD-row",
        ),
        (
            {
                "reduction_risks": [
                    {
                        "code": "hkv_12_1_s3_uvi_information_3pct",
                        "status": "verify-before-production",
                    }
                ],
                "production_blocked": False,
            },
            "hkv_12_1_s3_uvi_information_3pct",
        ),
        (
            {
                "unresolved_conflicts": [
                    {
                        "code": "UVI-SOURCE-CONFLICT",
                        "production_blocking": True,
                    }
                ],
                "production_blocked": False,
            },
            "UVI-SOURCE-CONFLICT",
        ),
        ({"production_blocked": True}, "UVI-PRODUCTION-BLOCKED"),
    ),
)
def test_real_uvi_result_surfaces_block_even_with_empty_artifact_snapshot(
    results: dict[str, object], marker: str
) -> None:
    run = SimpleNamespace(
        id="uvi-run-real-shape",
        account_id="account-1",
        tenancy_id="tenancy-1",
        unit_id="unit-1",
        results=results,
    )
    blockers = jobs.derive_uvi_production_blockers(run)
    assert marker in " | ".join(blockers)

    content = b"frozen UVI bytes"
    artifact = SimpleNamespace(
        id="artifact-uvi-real-shape",
        building_id="building-1",
        unit_id="unit-1",
        tenancy_id="tenancy-1",
        renter_id="renter-1",
        artifact_kind="UVI",
        occurrence_key="uvi:2026-07:renter-1",
        statement_archive_id=None,
        uvi_run_id=run.id,
        content_bytes=content,
        sha256=sha256(content).hexdigest(),
        filename="uvi.pdf",
        mime_type="application/pdf",
        production_blocked=False,
        production_blockers_snapshot=(),
    )
    request = jobs.RenterDeliveryRequest(
        building_id="building-1",
        renter_id="renter-1",
        delivery_kind=jobs.ScheduledDeliveryKind.UVI,
        occurrence_key=artifact.occurrence_key,
        subject_de="Ihre monatliche Verbrauchsinformation",
        html_body_de="Dokument im Anhang.",
        from_name="Vermieter Beispiel",
        sender_address="zustellung@lokara.de",
        artifact_id=artifact.id,
    )
    session = _ClaimSession(
        [
            SimpleNamespace(id="renter-1", email="mieter@example.de"),
            None,
            artifact,
            run,
        ]
    )
    outcome = jobs.dispatch_renter_artifact(
        session,  # type: ignore[arg-type]
        account_id="account-1",
        today=date(2026, 8, 25),
        now=datetime(2026, 8, 25, 9, 0, tzinfo=UTC),
        request=request,
        gateway=_NoSendGateway(),
    )
    assert outcome.blocked[0].reason is jobs.DeliveryBlockReason.PRODUCTION_BLOCKED
    assert marker in outcome.blocked[0].detail


class _AnnualScheduleSession:
    def __init__(
        self,
        schedule: object,
        archives: list[object],
        statement: object | None = None,
    ) -> None:
        self.schedule = schedule
        self.archives = archives
        self.statement = statement

    def scalars(self, statement: object) -> object:
        entity = statement.column_descriptions[0].get("entity")  # type: ignore[attr-defined]
        if entity is DeliveryScheduleVersion:
            rows = [self.schedule]
        elif entity is StatementArchive:
            rows = self.archives
        else:
            rows = ["renter-1"]
        return SimpleNamespace(all=lambda: rows)

    def scalar(self, statement: object) -> object:
        entity = statement.column_descriptions[0].get("entity")  # type: ignore[attr-defined]
        if entity is Building:
            return SimpleNamespace(id="building-1", landlord_id="landlord-1")
        if entity is Landlord:
            return SimpleNamespace(id="landlord-1", legal_name="Vermieter Beispiel")
        if entity is Statement:
            return self.statement
        return None


def test_enabled_annual_schedule_freezes_statement_archive_before_dispatch_idempotently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = SimpleNamespace(
        id="statement-archive-current",
        statement_id="statement-2025",
        tenancy_id="tenancy-1",
        audience="TENANT",
    )
    historical_archive = SimpleNamespace(
        id="statement-archive-historical",
        statement_id="statement-2024",
        tenancy_id="tenancy-old",
        audience="TENANT",
    )
    occurrence_key = "annual-statement:statement-2025:statement-archive-current:tenancy-1"
    schedule = SimpleNamespace(
        id="schedule-1",
        building_id="building-1",
        delivery_kind="ANNUAL_STATEMENT",
        version=1,
        enabled=False,
        valid_from=date(2026, 8, 25),
        schedule_snapshot={
            "statement_archive_id": archive.id,
            "statement_id": archive.statement_id,
            "statement_period": {
                "period_start": "2025-01-01",
                "period_end": "2025-12-31",
            },
            "occurrence_key": occurrence_key,
        },
    )
    session = _AnnualScheduleSession(schedule, [historical_archive, archive])
    freeze_calls: list[dict[str, object]] = []
    dispatch_calls: list[jobs.RenterDeliveryRequest] = []
    artifact = SimpleNamespace(
        id="artifact-1",
        building_id="building-1",
        renter_id="renter-1",
        artifact_kind="ANNUAL_STATEMENT",
        occurrence_key=occurrence_key,
    )

    def freeze(_session: object, **kwargs: object) -> object:
        freeze_calls.append(kwargs)
        return jobs.ArtifactFreezeResult(
            artifact=artifact,  # type: ignore[arg-type]
            created=len(freeze_calls) == 1,
            blocked_reason=None,
            detail=None,
        )

    def dispatch(_session: object, **kwargs: object) -> object:
        dispatch_calls.append(cast(jobs.RenterDeliveryRequest, kwargs["request"]))
        return jobs.RenterDeliveryJobResult(
            account_id="account-1",
            scheduled=1,
            queued=int(len(dispatch_calls) == 1),
            already_processed=int(len(dispatch_calls) > 1),
            blocked=(),
            provider_delivered=0,
            legally_confirmed=0,
        )

    monkeypatch.setattr(jobs, "freeze_renter_delivery_artifact", freeze)
    monkeypatch.setattr(jobs, "dispatch_renter_artifact", dispatch)
    clock = datetime(2026, 8, 25, 9, 0, tzinfo=UTC)

    disabled = jobs.schedule_renter_deliveries(
        session,  # type: ignore[arg-type]
        account_id="account-1",
        today=date(2026, 8, 25),
        now=clock,
    )
    assert disabled.scheduled == 0
    assert freeze_calls == []
    assert dispatch_calls == []

    schedule.enabled = True
    first = jobs.schedule_renter_deliveries(
        session,  # type: ignore[arg-type]
        account_id="account-1",
        today=date(2026, 8, 25),
        now=clock,
    )
    replay = jobs.schedule_renter_deliveries(
        session,  # type: ignore[arg-type]
        account_id="account-1",
        today=date(2026, 8, 25),
        now=clock,
    )
    assert first.scheduled == 1, "the bound occurrence must not enumerate archive history"
    assert first.queued == 1
    assert replay.already_processed == 1
    assert len(freeze_calls) == len(dispatch_calls) == 2
    assert all(call["source_id"] == archive.id for call in freeze_calls)
    assert all(call["occurrence_key"] == occurrence_key for call in freeze_calls)
    assert all(
        call["source_kind"] is jobs.ScheduledDeliveryKind.ANNUAL_STATEMENT for call in freeze_calls
    )
    assert all(request.artifact_id == artifact.id for request in dispatch_calls)


@pytest.mark.parametrize(
    ("snapshot_change", "statement_building_id"),
    (
        ({"occurrence_key": "annual-statement:attacker-chosen-replay-key"}, "building-1"),
        (
            {
                "statement_period": {
                    "period_start": "2024-01-01",
                    "period_end": "2024-12-31",
                }
            },
            "building-1",
        ),
        ({}, "building-2"),
    ),
    ids=("forged-occurrence", "forged-period", "archive-from-another-building"),
)
def test_schedule_dispatch_rechecks_the_complete_canonical_archive_binding(
    monkeypatch: pytest.MonkeyPatch,
    snapshot_change: dict[str, object],
    statement_building_id: str,
) -> None:
    """A corrupted snapshot must not mint a second idempotency identity or send."""
    archive = SimpleNamespace(
        id="statement-archive-current",
        statement_id="statement-2025",
        tenancy_id="tenancy-1",
        audience="TENANT",
    )
    statement = SimpleNamespace(
        id=archive.statement_id,
        account_id="account-1",
        building_id=statement_building_id,
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
    )
    canonical_occurrence = "annual-statement:statement-2025:statement-archive-current:tenancy-1"
    snapshot: dict[str, object] = {
        "statement_archive_id": archive.id,
        "statement_id": statement.id,
        "statement_period": {
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
        },
        "occurrence_key": canonical_occurrence,
    }
    snapshot.update(snapshot_change)
    schedule = SimpleNamespace(
        id="schedule-1",
        building_id="building-1",
        delivery_kind="ANNUAL_STATEMENT",
        version=1,
        enabled=True,
        valid_from=date(2026, 8, 25),
        schedule_snapshot=snapshot,
    )
    session = _AnnualScheduleSession(schedule, [archive], statement)
    freeze_calls: list[dict[str, object]] = []
    dispatch_calls: list[dict[str, object]] = []

    def freeze(_session: object, **kwargs: object) -> object:
        freeze_calls.append(kwargs)
        return jobs.ArtifactFreezeResult(
            artifact=SimpleNamespace(
                id="artifact-forged",
                building_id="building-1",
                renter_id="renter-1",
                artifact_kind="ANNUAL_STATEMENT",
                occurrence_key=kwargs["occurrence_key"],
            ),  # type: ignore[arg-type]
            created=True,
            blocked_reason=None,
            detail=None,
        )

    def dispatch(_session: object, **kwargs: object) -> object:
        dispatch_calls.append(kwargs)
        return jobs.RenterDeliveryJobResult(
            account_id="account-1",
            scheduled=1,
            queued=1,
            already_processed=0,
            blocked=(),
            provider_delivered=0,
            legally_confirmed=0,
        )

    monkeypatch.setattr(jobs, "freeze_renter_delivery_artifact", freeze)
    monkeypatch.setattr(jobs, "dispatch_renter_artifact", dispatch)

    result = jobs.schedule_renter_deliveries(
        session,  # type: ignore[arg-type]
        account_id="account-1",
        today=date(2026, 8, 25),
        now=datetime(2026, 8, 25, 9, 0, tzinfo=UTC),
    )

    assert result.scheduled == 0
    assert result.blocked
    assert freeze_calls == []
    assert dispatch_calls == []
