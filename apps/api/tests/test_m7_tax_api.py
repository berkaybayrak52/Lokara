"""RED M7-D route, role, privacy and failed-generation contracts."""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import textwrap
from datetime import UTC, datetime
from hashlib import sha256
from inspect import signature
from types import ModuleType, SimpleNamespace
from typing import Any, Protocol, cast, get_args, get_origin

import pytest
from fastapi import HTTPException, Response
from lokara_db import Role
from pydantic import BaseModel, ValidationError


class _ArchiveSnapshotLike(Protocol):
    input_snapshot: dict[str, object]


def _api() -> ModuleType:
    try:
        module = importlib.import_module("lokara_api.routers.tax")
    except ModuleNotFoundError:
        pytest.fail("RED M7-D: lokara_api.routers.tax is missing", pytrace=False)
    return module


_ACTIONS = (
    "read",
    "afa_write",
    "event_write",
    "profile_write",
    "mapping_write",
    "generate",
)
_ROLE_CASES = (
    *((Role.OWNER, action, True) for action in _ACTIONS),
    *(
        (Role.TAX_ADVISOR, action, action in {"read", "profile_write", "mapping_write"})
        for action in _ACTIONS
    ),
    *((Role.EMPLOYEE, action, False) for action in _ACTIONS),
)


def test_openapi_exposes_the_complete_account_tax_route_surface() -> None:
    from lokara_api.main import app

    paths = app.openapi()["paths"]
    expected = {
        "/a/{account_id}/tax/buildings": {"get"},
        "/a/{account_id}/tax/afa/preview": {"post"},
        "/a/{account_id}/tax/afa": {"post"},
        "/a/{account_id}/tax/afa/history": {"get"},
        "/a/{account_id}/tax/events": {"get", "post"},
        "/a/{account_id}/tax/events/{event_id}/corrections": {"post"},
        "/a/{account_id}/tax/adviser-profile": {"get", "post"},
        "/a/{account_id}/tax/mappings/{tax_year}": {"get", "post"},
        "/a/{account_id}/tax/readiness": {"post"},
        "/a/{account_id}/tax/exports": {"post", "get"},
        "/a/{account_id}/tax/exports/{export_id}/artifacts/{artifact_id}": {"get"},
    }
    for path, methods in expected.items():
        assert path in paths, f"RED M7-D: route {path} is missing"
        assert methods <= set(paths[path])


@pytest.mark.parametrize(
    ("role", "action", "allowed"),
    _ROLE_CASES,
)
def test_tax_role_matrix(role: Role, action: str, allowed: bool) -> None:
    authorize = getattr(_api(), "authorize_tax_action", None)
    assert callable(authorize), "RED M7-D: authorize_tax_action is missing"
    if allowed:
        authorize(role, action)
    else:
        with pytest.raises(HTTPException) as refused:
            authorize(role, action)
        assert refused.value.status_code == 403


def test_tax_adviser_is_admitted_by_path_dependency_without_owner_portal_access() -> None:
    module = _api()
    dependency = getattr(module, "tax_account_session_for_path", None)
    assert callable(dependency), "RED M7-D: tax-specific account dependency is missing"
    assert module.router.prefix == "/a/{account_id}/tax"


def test_tax_building_list_is_minimized_and_tax_authorized() -> None:
    module = _api()
    endpoint = getattr(module, "list_tax_buildings", None)
    assert callable(endpoint), "M7 tax workspace needs its own minimized building list"
    item_type = getattr(module, "TaxBuildingResponse", None)
    list_type = getattr(module, "TaxBuildingListResponse", None)
    assert item_type is not None and set(item_type.model_fields) == {"id", "label"}
    assert list_type is not None and set(list_type.model_fields) == {"buildings"}

    class Rows:
        def all(self) -> list[object]:
            return [
                SimpleNamespace(
                    id="building-1",
                    name="Musterhaus",
                    street="Musterstraße 12",
                    postal_code="10115",
                    city="Berlin",
                    renter_name="Must not cross the tax boundary",
                )
            ]

    class FakeSession:
        def __init__(self, role: Role) -> None:
            self.info = {"tax_role": role}

        def scalars(self, _statement: object) -> Rows:
            return Rows()

    for role in (Role.OWNER, Role.TAX_ADVISOR):
        response = endpoint("account-1", FakeSession(role))
        dumped = response.model_dump(mode="json")
        assert dumped == {
            "buildings": [{"id": "building-1", "label": "Musterstraße 12, 10115 Berlin"}]
        }
        assert "renter" not in str(dumped).lower()
        assert "mieter" not in str(dumped).lower()

    with pytest.raises(HTTPException) as denied:
        endpoint("account-1", FakeSession(Role.EMPLOYEE))
    assert denied.value.status_code == 403


def test_failed_generation_persists_readiness_only() -> None:
    generate = getattr(_api(), "generate_export", None)
    assert callable(generate), "RED M7-D: generate_export endpoint is missing"

    class FakeSession:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, value: object) -> None:
            self.added.append(value)

        def flush(self) -> None:
            return None

    session = FakeSession()
    body = SimpleNamespace(
        export_kind="DATEV",
        building_id="building-1",
        tax_year=2025,
        generated_at="2025-01-02T03:04:05Z",
        verified_test_bundle=None,
    )
    blocked = generate("account-1", body, session)
    assert isinstance(blocked, Response)
    assert blocked.status_code == 422
    assert json.loads(bytes(blocked.body))["detail"] == (
        "Export gesperrt: Die Quellen müssen zuerst geprüft werden."
    )
    names = [type(row).__name__ for row in session.added]
    assert names == ["TaxExportReadinessAttempt"]
    assert "TaxExportArchive" not in names
    assert "TaxExportArtifact" not in names


def test_tax_payload_contract_never_contains_renter_identity_fields() -> None:
    schemas = getattr(_api(), "PUBLIC_TAX_RESPONSE_SCHEMAS", None)
    assert isinstance(schemas, tuple) and schemas
    forbidden = {"renter", "renter_id", "renter_name", "mieter", "mieter_id", "mieter_name"}
    for schema in schemas:
        fields = set(getattr(schema, "model_fields", {}))
        assert fields.isdisjoint(forbidden)


def test_afa_request_accepts_normalized_docs_10_facts_without_fixture_shortcut() -> None:
    module = _api()
    request_type = module.AfaRequest
    assert "fixture_id" not in request_type.model_fields
    body = request_type.model_validate(
        {
            "buildingId": "building-1",
            "taxYear": 2025,
            "facts": {
                "erwerbsart": "kauf",
                "gebaeudetyp": "mfh",
                "fertigstellungsjahr": 1978,
                "uebergangNutzenLastenDatum": "2024-03-15",
                "wohnflaecheGesamt": 19400,
                "grundstuecksflaecheM2": 420,
                "kaufpreisCent": 48_000_000,
                "grunderwerbsteuerCent": 3_120_000,
                "notarGrundbuchCent": 720_000,
                "grundschuldkostenCent": 45_000,
                "maklerprovisionCent": 1_713_600,
                "sonstigeAnkCent": 0,
                "beweglicheWgCent": 0,
                "aufteilungsWeg": "vertrag",
                "vertragGebaeudeCent": 27_005_129,
                "vertragBodenCent": 26_548_471,
            },
            "generatedAt": "2025-01-02T03:04:05Z",
        }
    )
    result, rechtsstand, blocked = module._afa_result(body)
    assert result["calculated_values"]["acquisition_total_cents"] == 53_553_600
    assert rechtsstand == module.resolve_afa_rule_bundle(2025).rechtsstand
    assert blocked is True


def test_export_archive_response_preserves_archived_readiness_and_rule_evidence() -> None:
    module = _api()
    required = {
        "readiness_findings",
        "blockers",
        "afa_rechtsstand",
        "export_rechtsstand",
    }
    assert required <= set(module.ExportResponse.model_fields)
    archive = SimpleNamespace(
        id="archive-1",
        version=3,
        readiness_attempt_id="readiness-1",
        sha256="archive-sha",
        generated_at=datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC),
        input_snapshot={
            "readiness_findings": [
                {"code": "mapping_unverified", "message": "Kontenzuordnung prüfen."}
            ],
            "blockers": ["Kontenzuordnung ist nicht verifiziert."],
            "afa_rechtsstand": "09/2031",
            "export_rechtsstand": "10/2032",
        },
    )
    artifact = SimpleNamespace(
        id="artifact-1",
        artifact_kind="anlage_v_pdf",
        filename="anlage-v-2025.pdf",
        sha256="artifact-sha",
    )
    response = module._export_out(archive, [artifact])
    assert response.readiness_findings == archive.input_snapshot["readiness_findings"]
    assert response.blockers == archive.input_snapshot["blockers"]
    assert response.afa_rechtsstand == "09/2031"
    assert response.export_rechtsstand == "10/2032"


def test_afa_responses_expose_true_annual_afa_as_a_first_class_field() -> None:
    module = _api()
    assert "annual_afa_cents" in module.AfaResponse.model_fields
    assert module.AfaHistoryResponse.model_fields["records"].annotation is not None


def test_public_afa_request_cannot_supply_authority_and_server_resolves_rules_by_year() -> None:
    module = _api()
    assert "rules" not in module.AfaRequest.model_fields
    resolver = getattr(module, "resolve_afa_rule_bundle", None)
    assert callable(resolver), "M7-A requires a server-owned tax-year AfA rule resolver"
    resolved = resolver(2025)
    assert resolved.rechtsstand
    assert resolved.source_evidence
    assert resolved.production_blocked is True
    with pytest.raises(ValidationError):
        module.AfaRequest.model_validate(
            {
                "buildingId": "building-1",
                "taxYear": 2025,
                "facts": {"erwerbsart": "kauf"},
                "generatedAt": "2025-01-02T03:04:05Z",
                "rules": {
                    "registerRows": [["client-controlled"]],
                    "rechtsstand": "client-controlled",
                },
            }
        )
    result_source = inspect.getsource(module._afa_result)
    assert "resolve_afa_rule_bundle(body.tax_year)" in result_source


def test_verified_export_freezes_loaded_readiness_and_has_no_evidence_defaults() -> None:
    module = _api()
    generated_at = datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC)
    readiness = SimpleNamespace(
        id="readiness-evidence-1",
        account_id="account-1",
        findings=[{"code": "line_unverified", "message": "Zeilenzuordnung prüfen."}],
        production_blocked=False,
        rechtsstand="10/2032",
        input_snapshot={"afa_rechtsstand": "09/2031", "blockers": []},
    )

    class EvidenceSession:
        def __init__(self) -> None:
            self.added: list[object] = []

        def get(self, model: type[object], identity: str) -> object | None:
            if model.__name__ == "TaxExportReadinessAttempt" and identity == readiness.id:
                return readiness
            return None

        def scalar(self, _statement: object) -> None:
            return None

        def add(self, value: object) -> None:
            self.added.append(value)

        def flush(self) -> None:
            return None

    artifact = module.VerifiedTestArtifact(
        artifact_kind="anlage_v_pdf",
        filename="anlage-v.pdf",
        mime_type="application/pdf",
        content_bytes=b"%PDF test",
    )
    bundle = module.VerifiedTestBundle(bundle_id="server-only", artifacts=[artifact])
    session = EvidenceSession()
    response = module.archive_verified_test_artifacts(
        "account-1", readiness.id, bundle, generated_at, session
    )
    archive = next(row for row in session.added if type(row).__name__ == "TaxExportArchive")
    assert cast(_ArchiveSnapshotLike, archive).input_snapshot == {
        "verified_test_bundle_id": "server-only",
        "readiness_findings": readiness.findings,
        "blockers": [],
        "afa_rechtsstand": "09/2031",
        "export_rechtsstand": "10/2032",
    }
    assert response.readiness_findings == readiness.findings
    assert response.afa_rechtsstand == "09/2031"
    assert response.export_rechtsstand == "10/2032"

    incomplete = SimpleNamespace(
        id="archive-incomplete",
        version=1,
        readiness_attempt_id=readiness.id,
        sha256="sha",
        generated_at=generated_at,
        input_snapshot={"verified_test_bundle_id": "server-only"},
    )
    with pytest.raises(ValueError, match=r"evidence|Rechtsstand|readiness"):
        module._export_out(incomplete, [])


def test_exact_ui_transfer_date_changes_first_year_and_deductible_afa() -> None:
    module = _api()
    payload = {
        "buildingId": "building-1",
        "facts": {
            "erwerbsart": "kauf",
            "gebaeudetyp": "mfh",
            "fertigstellungsjahr": 1978,
            "uebergangNutzenLastenDatum": "2024-03-15",
            "wohnflaecheGesamt": 19400,
            "grundstuecksflaecheM2": 420,
            "kaufpreisCent": 48_000_000,
            "grunderwerbsteuerCent": 3_120_000,
            "notarGrundbuchCent": 720_000,
            "grundschuldkostenCent": 45_000,
            "maklerprovisionCent": 1_713_600,
            "sonstigeAnkCent": 0,
            "beweglicheWgCent": 0,
            "aufteilungsWeg": "vertrag",
            "vertragGebaeudeCent": 27_005_129,
            "vertragBodenCent": 26_548_471,
        },
        "generatedAt": "2025-01-02T03:04:05Z",
    }
    results: dict[int, dict[str, object]] = {}
    for tax_year in (2024, 2025):
        body = module.AfaRequest.model_validate({**payload, "taxYear": tax_year})
        snapshot, _, _ = module._afa_result(body)
        results[tax_year] = cast(dict[str, object], snapshot["calculated_values"])
    assert results[2024]["annual_afa_cents"] == 450_086
    assert results[2024]["deductible_afa_cents"] == 450_086
    assert results[2024]["non_deductible_afa_cents"] == 0
    assert results[2025]["annual_afa_cents"] == 540_103
    assert results[2025]["deductible_afa_cents"] == 540_103
    assert results[2025]["non_deductible_afa_cents"] == 0


def test_temporal_self_use_exposes_distinct_tax_year_and_deductible_amounts() -> None:
    module = _api()
    assert {
        "tax_year_afa_cents",
        "deductible_afa_cents",
        "non_deductible_afa_cents",
    } <= set(module.AfaResponse.model_fields)
    body = module.AfaRequest.model_validate(
        {
            "buildingId": "building-1",
            "taxYear": 2025,
            "facts": {
                "erwerbsart": "kauf",
                "gebaeudetyp": "mfh",
                "fertigstellungsjahr": 1978,
                "uebergangNutzenLastenDatum": "2024-03-15",
                "wohnflaecheGesamt": 19400,
                "grundstuecksflaecheM2": 420,
                "kaufpreisCent": 48_000_000,
                "grunderwerbsteuerCent": 3_120_000,
                "notarGrundbuchCent": 720_000,
                "grundschuldkostenCent": 45_000,
                "maklerprovisionCent": 1_713_600,
                "sonstigeAnkCent": 0,
                "beweglicheWgCent": 0,
                "aufteilungsWeg": "vertrag",
                "vertragGebaeudeCent": 27_005_129,
                "vertragBodenCent": 26_548_471,
                "selfUsePeriods": [
                    {
                        "vonDatum": "2025-01-01",
                        "bisDatum": "2025-12-31",
                        "selbstgenutzteFlaeche": 9700,
                        "einheitIds": [],
                    }
                ],
            },
            "generatedAt": "2025-01-02T03:04:05Z",
        }
    )
    snapshot, rechtsstand, blocked = module._afa_result(body)
    values = cast(dict[str, object], snapshot["calculated_values"])
    assert values["tax_year_afa_cents"] == 540_103
    assert values["deductible_afa_cents"] == 270_052
    assert values["non_deductible_afa_cents"] == 270_051
    response = module.AfaResponse(
        building_id="building-1",
        tax_year=2025,
        result=snapshot,
        tax_year_afa_cents=540_103,
        deductible_afa_cents=270_052,
        non_deductible_afa_cents=270_051,
        rechtsstand=rechtsstand,
        production_blocked=blocked,
        generated_at=datetime(2025, 1, 2, tzinfo=UTC),
    )
    assert response.tax_year_afa_cents == 540_103
    assert response.deductible_afa_cents == 270_052
    assert response.non_deductible_afa_cents == 270_051


def test_verified_archive_rejects_readiness_snapshot_without_blockers_key() -> None:
    module = _api()
    readiness = SimpleNamespace(
        id="readiness-without-blockers",
        account_id="account-1",
        findings=[{"code": "ready", "message": "Testnachweis vollständig."}],
        input_snapshot={"afa_rechtsstand": "08/2026"},
        rechtsstand="07/2026",
        afa_record_version_id=None,
        mapping_version_id="mapping-1",
    )

    class MissingBlockersSession:
        def __init__(self) -> None:
            self.added: list[object] = []

        def get(self, model: type[object], identity: str) -> object | None:
            if model.__name__ == "TaxExportReadinessAttempt" and identity == readiness.id:
                return readiness
            return None

        def scalar(self, _statement: object) -> None:
            return None

        def add(self, value: object) -> None:
            self.added.append(value)

        def flush(self) -> None:
            return None

    bundle = module.VerifiedTestBundle(
        bundle_id="server-only",
        artifacts=[
            module.VerifiedTestArtifact(
                artifact_kind="anlage_v_pdf",
                filename="anlage-v.pdf",
                mime_type="application/pdf",
                content_bytes=b"%PDF test",
            )
        ],
    )
    session = MissingBlockersSession()
    with pytest.raises(ValueError, match=r"blocker|evidence|readiness"):
        module.archive_verified_test_artifacts(
            "account-1", readiness.id, bundle, datetime(2025, 1, 2, tzinfo=UTC), session
        )
    assert session.added == []


def test_api_blocked_export_copy_is_plain_and_not_internal_production_wording() -> None:
    module = _api()

    class Session:
        def __init__(self) -> None:
            self.info = {"tax_role": Role.OWNER}
            self.added: list[object] = []

        def add(self, value: object) -> None:
            self.added.append(value)

        def flush(self) -> None:
            return None

    response = module.generate_export(
        "account-1",
        SimpleNamespace(
            export_kind="anlage_v_pdf",
            building_id="building-1",
            tax_year=2025,
            generated_at="2025-01-02T03:04:05Z",
        ),
        Session(),
    )
    detail = json.loads(bytes(response.body))["detail"]
    assert detail.startswith("Export gesperrt:")
    assert "Produktionsausgabe" not in detail


def test_client_payload_can_never_supply_a_verified_test_bundle() -> None:
    module = _api()
    request_type = module.GenerateExportRequest
    assert "verified_test_bundle" not in request_type.model_fields
    with pytest.raises(ValidationError):
        request_type.model_validate(
            {
                "exportKind": "anlage_v_pdf",
                "buildingId": "building-1",
                "taxYear": 2025,
                "generatedAt": "2025-01-02T03:04:05Z",
                "mappingVersionId": "mapping-1",
                "verifiedTestBundle": {
                    "bundleId": "client-controlled",
                    "artifacts": [
                        {
                            "artifactKind": "anlage_v_pdf",
                            "filename": "forged.pdf",
                            "mimeType": "application/pdf",
                            "content": "client bytes",
                        }
                    ],
                },
            }
        )


def test_verified_generation_resolves_rules_and_builds_artifacts_from_domain_inputs() -> None:
    module = _api()
    generate = getattr(module, "generate_verified_test_export", None)
    assert callable(generate)
    assert list(signature(generate).parameters) == [
        "account_id",
        "readiness_attempt_id",
        "generated_at",
        "session",
    ]
    source = inspect.getsource(generate)
    for required_call in (
        "resolve_verified_export_rule_bundle",
        "build_anlage_v_overview",
        "encode_anlage_v_csv",
        "encode_datev_extf",
        "anlage_v_overview_html",
        "archive_verified_test_artifacts",
    ):
        assert required_call in source
    assert "content_bytes" not in signature(generate).parameters
    assert "bundle" not in signature(generate).parameters


def test_archive_stream_key_is_account_building_year_and_kind_not_readiness_id() -> None:
    source = inspect.getsource(_api().archive_verified_test_artifacts)
    assert "TaxExportArchive.account_id" in source
    assert "building_id" in source
    assert "tax_year" in source
    assert "export_kind" in source
    assert "TaxExportArchive.readiness_attempt_id ==" not in source


def test_internal_archive_helper_freezes_exact_server_generated_bytes_without_identity() -> None:
    module = _api()
    server_helper = getattr(module, "archive_verified_test_artifacts", None)
    assert callable(server_helper), (
        "verified generation needs an internal exact-byte archive helper"
    )
    assert list(signature(server_helper).parameters) == [
        "account_id",
        "readiness_attempt_id",
        "bundle",
        "generated_at",
        "session",
    ]

    artifact_type = module.VerifiedTestArtifact
    bundle_type = module.VerifiedTestBundle
    assert "content_bytes" in artifact_type.model_fields
    assert "content" not in artifact_type.model_fields
    forbidden = {"renter", "renter_id", "renter_name", "mieter", "mieter_id", "mieter_name"}
    assert set(artifact_type.model_fields).isdisjoint(forbidden)
    assert set(bundle_type.model_fields).isdisjoint(forbidden)

    pdf_bytes = b"%PDF-1.7\nLokara M7 verified test artifact\n"
    csv_bytes = "Art;Betrag\r\nKaltmiete;23280,00\r\n".encode("windows-1252")
    bundle = bundle_type(
        bundle_id="server-test-only-2025",
        artifacts=[
            artifact_type(
                artifact_kind="anlage_v_pdf",
                filename="anlage-v-test.pdf",
                mime_type="application/pdf",
                content_bytes=pdf_bytes,
            ),
            artifact_type(
                artifact_kind="anlage_v_csv",
                filename="anlage-v-test.csv",
                mime_type="text/csv; charset=windows-1252",
                content_bytes=csv_bytes,
            ),
        ],
    )
    with pytest.raises(ValidationError):
        artifact_type.model_validate(
            {
                "artifactKind": "anlage_v_pdf",
                "filename": "identity-leak.pdf",
                "mimeType": "application/pdf",
                "contentBytes": pdf_bytes,
                "renterName": "Must not be accepted",
            }
        )

    class FakeSession:
        def __init__(self) -> None:
            self.added: list[object] = []
            self.flushes = 0
            self.readiness = SimpleNamespace(
                id="readiness-1",
                account_id="account-1",
                findings=[
                    {"code": "verified_test_bundle", "message": "Testnachweise sind vollständig."}
                ],
                input_snapshot={"blockers": []},
                afa_record_version_id="afa-1",
                mapping_version_id="mapping-1",
                rechtsstand=None,
            )

        def get(self, model: type[object], identity: str) -> object | None:
            if model.__name__ == "TaxExportReadinessAttempt" and identity == "readiness-1":
                return self.readiness
            if model.__name__ == "AfaRecordVersion" and identity == "afa-1":
                return SimpleNamespace(rechtsstand="08/2026")
            if model.__name__ == "TaxMappingVersion" and identity == "mapping-1":
                return SimpleNamespace(rechtsstand="07/2026")
            return None

        def add(self, value: object) -> None:
            self.added.append(value)

        def scalar(self, _statement: object) -> int:
            return 0

        def flush(self) -> None:
            self.flushes += 1

    generated_at = datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC)
    session = FakeSession()
    response = server_helper(
        "account-1",
        "readiness-1",
        bundle,
        generated_at,
        session,
    )

    archives: list[Any] = [row for row in session.added if type(row).__name__ == "TaxExportArchive"]
    artifacts: list[Any] = [
        row for row in session.added if type(row).__name__ == "TaxExportArtifact"
    ]
    assert len(archives) == 1
    assert len(artifacts) == 2
    assert len(session.added) == 3
    assert session.flushes == 1

    archive = archives[0]
    expected_bytes = [pdf_bytes, csv_bytes]
    assert archive.account_id == "account-1"
    assert archive.readiness_attempt_id == "readiness-1"
    assert archive.generated_at == generated_at
    assert archive.production_blocked is False
    assert archive.sha256 == sha256(b"".join(expected_bytes)).hexdigest()
    assert archive.input_snapshot["readiness_findings"] == session.readiness.findings
    assert archive.input_snapshot["blockers"] == []
    assert archive.input_snapshot["afa_rechtsstand"] == "08/2026"
    assert archive.input_snapshot["export_rechtsstand"] == "07/2026"
    assert [row.content_bytes for row in artifacts] == expected_bytes
    assert [row.sha256 for row in artifacts] == [
        sha256(content).hexdigest() for content in expected_bytes
    ]
    assert all(row.account_id == "account-1" for row in artifacts)
    assert all(row.archive_id == archive.id for row in artifacts)
    assert all(row.generated_at == generated_at for row in artifacts)
    assert all(row.production_blocked is False for row in artifacts)

    assert response.id == archive.id
    assert response.readiness_attempt_id == "readiness-1"
    assert response.generated_at == generated_at
    assert response.sha256 == archive.sha256
    assert [row.sha256 for row in response.artifacts] == [row.sha256 for row in artifacts]
    assert forbidden.isdisjoint(response.model_dump().keys())


def test_authority_flags_are_server_owned_and_rejected_from_client_payloads() -> None:
    module = _api()
    cases = (
        (
            module.AfaRuleIn,
            "verified_for_test",
            {"registerRows": [], "rechtsstand": "07/2026", "verifiedForTest": True},
        ),
        (
            module.AdviserProfileCreate,
            "production_blocked",
            {
                "profile": {},
                "generatedAt": "2025-01-02T03:04:05Z",
                "productionBlocked": False,
            },
        ),
        (
            module.TaxMappingCreate,
            "production_blocked",
            {
                "mapping": {},
                "sourceVersion": "test",
                "rechtsstand": "07/2026",
                "generatedAt": "2025-01-02T03:04:05Z",
                "productionBlocked": False,
            },
        ),
    )
    for request_type, forbidden_field, payload in cases:
        assert forbidden_field not in request_type.model_fields
        with pytest.raises(ValidationError):
            request_type.model_validate(payload)


def _nested_model_types(annotation: object) -> set[type[BaseModel]]:
    found: set[type[BaseModel]] = set()
    pending = [annotation]
    while pending:
        item = pending.pop()
        if isinstance(item, type) and issubclass(item, BaseModel):
            if item in found:
                continue
            found.add(item)
            pending.extend(field.annotation for field in item.model_fields.values())
        else:
            origin = get_origin(item)
            if origin is not None:
                pending.extend(get_args(item))
    return found


def test_profile_and_mapping_use_explicit_extra_forbid_identity_free_models() -> None:
    module = _api()
    forbidden = {"renter", "renter_id", "renter_name", "mieter", "mieter_id", "mieter_name"}
    for request_type, field_name in (
        (module.AdviserProfileCreate, "profile"),
        (module.TaxMappingCreate, "mapping"),
    ):
        nested_models = _nested_model_types(request_type.model_fields[field_name].annotation)
        assert nested_models, f"{request_type.__name__}.{field_name} must not be a free-form dict"
        for nested_type in nested_models:
            assert nested_type.model_config.get("extra") == "forbid"
            assert set(nested_type.model_fields).isdisjoint(forbidden)


def test_afa_facts_recursively_reject_renter_identity_keys() -> None:
    request_type = _api().AfaRequest
    with pytest.raises(ValidationError):
        request_type.model_validate(
            {
                "buildingId": "building-1",
                "taxYear": 2025,
                "fixtureId": "10-F01",
                "facts": {"acquisition": {"renterName": "Must not be accepted"}},
                "rules": {"registerRows": [], "rechtsstand": "07/2026"},
                "generatedAt": "2025-01-02T03:04:05Z",
            }
        )


def test_payment_allocation_materializer_splits_components_without_guessing() -> None:
    module = _api()
    materialize = getattr(module, "materialize_payment_allocation_components", None)
    assert callable(materialize), "M7-D requires server-side M6 component materialization"

    class FakeSession:
        def __init__(self) -> None:
            self.added: list[Any] = []

        def scalar(self, statement: object) -> object | None:
            params = set(statement.compile().params.values())  # type: ignore[attr-defined]
            return next(
                (
                    row
                    for row in self.added
                    if getattr(row, "source_payment_allocation_id", None) in params
                    and getattr(row, "source_component", None) in params
                ),
                None,
            )

        def add(self, row: object) -> None:
            self.added.append(row)

        def add_all(self, rows: list[object]) -> None:
            self.added.extend(rows)

        def flush(self) -> None:
            return None

    payment_date = datetime(2025, 1, 3, tzinfo=UTC).date()
    recorded_at = datetime(2025, 1, 4, tzinfo=UTC)
    rent_allocation = SimpleNamespace(
        id="allocation-rent",
        costs_cents=10,
        interest_cents=20,
        principal_cents=1_000,
        base_rent_cents=600,
        nk_advance_cents=250,
        heating_advance_cents=100,
        garage_cents=50,
    )
    other_allocation = SimpleNamespace(
        id="allocation-other",
        costs_cents=0,
        interest_cents=0,
        principal_cents=500,
        base_rent_cents=0,
        nk_advance_cents=0,
        heating_advance_cents=0,
        garage_cents=0,
    )
    session = FakeSession()
    for _ in range(2):
        for allocation in (rent_allocation, other_allocation):
            materialize(
                account_id="account-1",
                building_id="building-1",
                allocation=allocation,
                payment_date=payment_date,
                recorded_at=recorded_at,
                source_context={},
                session=session,
            )

    events = [row for row in session.added if type(row).__name__ == "TaxEvent"]
    identity = [(row.source_payment_allocation_id, row.source_component) for row in events]
    assert identity == [
        ("allocation-rent", "costs"),
        ("allocation-rent", "interest"),
        ("allocation-rent", "base_rent"),
        ("allocation-rent", "nk_advance"),
        ("allocation-rent", "heating_advance"),
        ("allocation-rent", "garage"),
        ("allocation-other", "principal"),
    ]
    assert [row.amount_cents for row in events] == [10, 20, 600, 250, 100, 50, 500]
    assert [row.category for row in events] == [
        None,
        None,
        "kaltmiete",
        "nk_vorauszahlung",
        "nk_vorauszahlung",
        None,
        None,
    ]
    assert all(row.account_id == "account-1" for row in events)
    assert all(row.building_id == "building-1" for row in events)
    assert all(row.payment_date == payment_date for row in events)
    assert all(row.recorded_at == recorded_at for row in events)


class _ScalarRows:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows


class _ReadinessSession:
    def __init__(self, *, afa_building: str = "building-1", mapping_year: int = 2025) -> None:
        self.info = {"tax_role": Role.OWNER}
        self.added: list[object] = []
        self.afa = SimpleNamespace(
            id="afa-1",
            building_id=afa_building,
            tax_year=2025,
            result_snapshot={"afaAbziehbarCent": 120_000},
        )
        self.profile = SimpleNamespace(
            id="profile-1",
            profile_snapshot={"beraternummer": "123", "mandantennummer": "456"},
        )
        self.mapping = SimpleNamespace(
            id="mapping-1",
            tax_year=mapping_year,
            mapping_snapshot=[
                {
                    "category": "kaltmiete",
                    "account": "8400",
                    "verification_flag": "verify-before-production",
                }
            ],
        )
        self.events: list[object] = [
            SimpleNamespace(
                id="event-1",
                building_id="building-1",
                payment_date=datetime(2025, 2, 1, tzinfo=UTC).date(),
                due_date=None,
                category="kaltmiete",
                amount_cents=100_000,
                direction="einnahme",
                source_snapshot={"beleg_referenz": "ledger-1"},
            )
        ]

    def get(self, model: type[object], row_id: str) -> object | None:
        return (
            {
                "AfaRecordVersion": self.afa,
                "TaxAdviserProfileVersion": self.profile,
                "TaxMappingVersion": self.mapping,
            }.get(model.__name__)
            if row_id
            else None
        )

    def scalars(self, _statement: object) -> _ScalarRows:
        return _ScalarRows(self.events)

    def add(self, row: object) -> None:
        self.added.append(row)

    def flush(self) -> None:
        return None


def _readiness_body(module: ModuleType) -> object:
    return module.ReadinessRequest(
        export_kind="datev_extf",
        building_id="building-1",
        tax_year=2025,
        generated_at=datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC),
        afa_record_version_id="afa-1",
        adviser_profile_version_id="profile-1",
        mapping_version_id="mapping-1",
    )


def test_readiness_loads_matching_versions_and_persists_engine_findings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _api()
    calls: list[dict[str, Any]] = []
    findings = (
        SimpleNamespace(severity="gelb", code="missing_account", finding_id="event-1"),
        SimpleNamespace(severity="rot", code="authority_unverified", finding_id="mapping-1"),
    )

    def evaluate_export_readiness(**kwargs: object) -> object:
        calls.append(kwargs)
        return SimpleNamespace(
            findings=findings,
            rechtsstand="07/2026",
            production_blocked=True,
        )

    monkeypatch.setattr(
        module, "evaluate_export_readiness", evaluate_export_readiness, raising=False
    )
    session = _ReadinessSession()
    response = module.evaluate_readiness("account-1", _readiness_body(module), session)

    assert len(calls) == 1
    call = calls[0]
    assert call["afa_record"] == session.afa.result_snapshot
    assert call["adviser_profile"] == session.profile.profile_snapshot
    assert call["mapping"] == session.mapping.mapping_snapshot
    ledger_events = call["ledger_events"]
    assert isinstance(ledger_events, list)
    assert ledger_events == [
        {
            "event_id": "event-1",
            "payment_date": datetime(2025, 2, 1, tzinfo=UTC).date(),
            "due_date": None,
            "category": "kaltmiete",
            "amount_cents": 100_000,
            "direction": "einnahme",
            "source": {"beleg_referenz": "ledger-1"},
        }
    ]
    assert len(session.added) == 1
    attempt: Any = session.added[0]
    assert attempt.findings_snapshot == [
        {"severity": "gelb", "code": "missing_account", "finding_id": "event-1"},
        {"severity": "rot", "code": "authority_unverified", "finding_id": "mapping-1"},
    ]
    assert attempt.production_blocked is True
    assert response.findings == attempt.findings_snapshot


def test_real_readiness_builder_freezes_blockers_and_feeds_verified_archive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _api()

    def evaluated(**_kwargs: object) -> object:
        return SimpleNamespace(
            findings=(
                SimpleNamespace(
                    severity="rot",
                    code="mapping_unverified",
                    finding_id="mapping-1",
                    message="Die Kontenzuordnung ist nicht verifiziert.",
                ),
            ),
            rechtsstand="07/2026",
            production_blocked=True,
        )

    monkeypatch.setattr(module, "evaluate_export_readiness", evaluated)

    class ArchiveReadinessSession(_ReadinessSession):
        def __init__(self) -> None:
            super().__init__()
            self.attempt: object | None = None
            self.afa.rechtsstand = "08/2026"
            self.mapping.rechtsstand = "07/2026"

        def get(self, model: type[object], row_id: str) -> object | None:
            if model.__name__ == "TaxExportReadinessAttempt":
                return self.attempt if getattr(self.attempt, "id", None) == row_id else None
            return super().get(model, row_id)

        def scalar(self, _statement: object) -> None:
            return None

    session = ArchiveReadinessSession()
    attempt = module._build_validated_readiness_attempt(
        "account-1", _readiness_body(module), session
    )
    session.attempt = attempt
    assert attempt.input_snapshot["blockers"] == ["Die Kontenzuordnung ist nicht verifiziert."]
    assert attempt.input_snapshot["readiness_result"]["production_blocked"] is True
    bundle = module.VerifiedTestBundle(
        bundle_id="server-builder-proof",
        artifacts=[
            module.VerifiedTestArtifact(
                artifact_kind="anlage_v_pdf",
                filename="anlage-v.pdf",
                mime_type="application/pdf",
                content_bytes=b"%PDF builder evidence",
            )
        ],
    )
    archived = module.archive_verified_test_artifacts(
        "account-1", attempt.id, bundle, attempt.generated_at, session
    )
    assert archived.blockers == ["Die Kontenzuordnung ist nicht verifiziert."]
    assert archived.readiness_findings == attempt.findings_snapshot
    assert archived.afa_rechtsstand == "08/2026"
    assert archived.export_rechtsstand == "07/2026"


@pytest.mark.parametrize(
    ("afa_building", "mapping_year"),
    (("building-other", 2025), ("building-1", 2024)),
)
def test_readiness_rejects_mismatched_version_references(
    afa_building: str, mapping_year: int
) -> None:
    module = _api()
    session = _ReadinessSession(afa_building=afa_building, mapping_year=mapping_year)
    with pytest.raises(HTTPException) as rejected:
        module.evaluate_readiness("account-1", _readiness_body(module), session)
    assert rejected.value.status_code == 422
    assert session.added == []


def test_tax_event_correction_uses_a_database_valid_source_component() -> None:
    module = _api()
    previous = SimpleNamespace(id="event-original")

    class FakeSession:
        def __init__(self) -> None:
            self.info = {"tax_role": Role.OWNER}
            self.added: list[Any] = []

        def get(self, _model: type[object], _row_id: str) -> object:
            return previous

        def add(self, row: object) -> None:
            self.added.append(row)

        def flush(self) -> None:
            return None

    body = module.TaxEventCorrectionCreate(
        building_id="building-1",
        payment_date="2025-02-01",
        due_date=None,
        category="kaltmiete",
        amount_cents=100_000,
        direction="einnahme",
        source_payment_allocation_id=None,
        source={},
        recorded_at="2025-02-02T03:04:05Z",
        correction_reason="Betrag berichtigt",
    )
    session = FakeSession()
    module.correct_event("account-1", "event-original", body, session)
    assert len(session.added) == 1
    row = session.added[0]
    allowed = {
        "manual",
        "costs",
        "interest",
        "principal",
        "base_rent",
        "nk_advance",
        "heating_advance",
        "garage",
    }
    assert row.source_component in allowed
    assert row.supersedes_tax_event_id == "event-original"


def test_reversal_materialization_normalizes_sign_and_direction() -> None:
    module = _api()
    materialize = module.materialize_payment_allocation_components

    class FakeSession:
        def __init__(self) -> None:
            self.added: list[Any] = []

        def scalar(self, _statement: object) -> None:
            return None

        def add(self, row: object) -> None:
            self.added.append(row)

        def flush(self) -> None:
            return None

    allocation = SimpleNamespace(
        id="allocation-reversal",
        costs_cents=-10,
        interest_cents=-20,
        principal_cents=-600,
        base_rent_cents=-600,
        nk_advance_cents=0,
        heating_advance_cents=0,
        garage_cents=0,
    )
    session = FakeSession()
    materialize(
        account_id="account-1",
        building_id="building-1",
        allocation=allocation,
        payment_date=datetime(2025, 2, 2, tzinfo=UTC).date(),
        recorded_at=datetime(2025, 2, 3, tzinfo=UTC),
        source_context={"ledger_kind": "REVERSAL"},
        session=session,
    )
    events = [row for row in session.added if type(row).__name__ == "TaxEvent"]
    assert [(row.source_component, row.amount_cents, row.direction) for row in events] == [
        ("costs", 10, "ausgabe"),
        ("interest", 20, "ausgabe"),
        ("base_rent", 600, "ausgabe"),
    ]


def test_matching_transactions_call_tax_materialization_for_payment_and_reversal() -> None:
    from lokara_api import matching_service

    for function_name in ("_settle_payment", "_reverse_payment"):
        function = getattr(matching_service, function_name)
        tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert "materialize_payment_allocation_components" in called, (
            f"{function_name} must materialize TaxEvent rows in its own transaction"
        )


def test_generation_uses_the_same_validated_engine_readiness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _api()
    calls: list[dict[str, object]] = []

    def evaluate_export_readiness(**kwargs: object) -> object:
        calls.append(kwargs)
        return SimpleNamespace(
            findings=(
                SimpleNamespace(
                    severity="rot", code="engine_generation_block", finding_id="mapping-1"
                ),
            ),
            rechtsstand="07/2026",
            production_blocked=True,
        )

    monkeypatch.setattr(module, "evaluate_export_readiness", evaluate_export_readiness)
    session = _ReadinessSession()
    readiness_body: Any = _readiness_body(module)
    body = module.GenerateExportRequest.model_validate(readiness_body.model_dump(mode="json"))
    response = module.generate_export("account-1", body, session)
    assert response.status_code == 422
    assert len(calls) == 1
    attempts: list[Any] = [
        row for row in session.added if type(row).__name__ == "TaxExportReadinessAttempt"
    ]
    assert len(attempts) == 1
    assert attempts[0].findings_snapshot == [
        {"severity": "rot", "code": "engine_generation_block", "finding_id": "mapping-1"}
    ]
    assert not any(
        type(row).__name__ in {"TaxExportArchive", "TaxExportArtifact"} for row in session.added
    )


def test_verified_archive_versions_and_supersession_are_per_logical_export_stream() -> None:
    module = _api()

    class FakeRows:
        def __init__(self, rows: list[Any]) -> None:
            self._rows = rows

        def first(self) -> object | None:
            return self._rows[0] if self._rows else None

        def all(self) -> list[Any]:
            return self._rows

    class FakeSession:
        def __init__(self) -> None:
            self.added: list[Any] = []
            self.readiness = {
                readiness_id: SimpleNamespace(
                    id=readiness_id,
                    account_id="account-1",
                    findings=[
                        {"code": "verified_test_stream", "message": "Teststream ist vollständig."}
                    ],
                    input_snapshot={"blockers": []},
                    building_id="building-1",
                    tax_year=2025,
                    export_kind="anlage_v_csv",
                    afa_record_version_id=f"afa-{readiness_id}",
                    mapping_version_id=f"mapping-{readiness_id}",
                    rechtsstand=None,
                )
                for readiness_id in ("readiness-a", "readiness-b")
            }

        def get(self, model: type[object], identity: str) -> object | None:
            if model.__name__ == "TaxExportReadinessAttempt":
                return self.readiness.get(identity)
            if model.__name__ == "AfaRecordVersion" and identity.startswith("afa-readiness-"):
                return SimpleNamespace(rechtsstand="08/2026")
            if model.__name__ == "TaxMappingVersion" and identity.startswith("mapping-readiness-"):
                return SimpleNamespace(rechtsstand="07/2026")
            return None

        def _matching_archives(self, statement: object) -> list[Any]:
            params = set(statement.compile().params.values())  # type: ignore[attr-defined]
            return sorted(
                [
                    row
                    for row in self.added
                    if type(row).__name__ == "TaxExportArchive"
                    and {row.building_id, row.tax_year, row.export_kind} <= params
                ],
                key=lambda row: row.version,
                reverse=True,
            )

        def scalar(self, statement: object) -> object:
            matching = self._matching_archives(statement)
            if matching:
                return matching[0]
            return len([row for row in self.added if type(row).__name__ == "TaxExportArchive"])

        def scalars(self, statement: object) -> FakeRows:
            return FakeRows(self._matching_archives(statement))

        def add(self, row: object) -> None:
            self.added.append(row)

        def flush(self) -> None:
            return None

    bundle = module.VerifiedTestBundle(
        bundle_id="server-stream-test",
        artifacts=[
            module.VerifiedTestArtifact(
                artifact_kind="anlage_v_csv",
                filename="test.csv",
                mime_type="text/csv",
                content_bytes=b"test bytes",
            )
        ],
    )
    session = FakeSession()
    for readiness_id in ("readiness-a", "readiness-a", "readiness-b"):
        module.archive_verified_test_artifacts(
            "account-1",
            readiness_id,
            bundle,
            datetime(2025, 2, 3, tzinfo=UTC),
            session,
        )
    archives = [row for row in session.added if type(row).__name__ == "TaxExportArchive"]
    assert [(row.readiness_attempt_id, row.version) for row in archives] == [
        ("readiness-a", 1),
        ("readiness-a", 2),
        ("readiness-b", 3),
    ]
    assert archives[0].supersedes_archive_id is None
    assert archives[1].supersedes_archive_id == archives[0].id
    assert archives[2].supersedes_archive_id == archives[1].id


def test_only_owner_can_persist_a_readiness_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _api()

    def ready(**_kwargs: object) -> object:
        return SimpleNamespace(findings=(), rechtsstand="07/2026", production_blocked=True)

    monkeypatch.setattr(module, "evaluate_export_readiness", ready)
    adviser = _ReadinessSession()
    adviser.info["tax_role"] = Role.TAX_ADVISOR
    with pytest.raises(HTTPException) as denied:
        module.evaluate_readiness("account-1", _readiness_body(module), adviser)
    assert denied.value.status_code == 403
    assert adviser.added == []

    owner = _ReadinessSession()
    owner.info["tax_role"] = Role.OWNER
    module.evaluate_readiness("account-1", _readiness_body(module), owner)
    assert [type(row).__name__ for row in owner.added] == ["TaxExportReadinessAttempt"]


def test_correction_preserves_its_building_and_source_stream() -> None:
    module = _api()
    previous = SimpleNamespace(
        id="event-original",
        building_id="building-1",
        source_payment_allocation_id="allocation-1",
        source_component="base_rent",
    )

    class FakeSession:
        def __init__(self) -> None:
            self.info = {"tax_role": Role.OWNER}
            self.added: list[Any] = []

        def get(self, _model: type[object], _row_id: str) -> object:
            return previous

        def add(self, row: object) -> None:
            self.added.append(row)

        def flush(self) -> None:
            return None

    body = module.TaxEventCorrectionCreate(
        building_id="building-other",
        payment_date="2025-02-01",
        category="kaltmiete",
        amount_cents=90_000,
        direction="einnahme",
        source_payment_allocation_id="allocation-other",
        source={},
        recorded_at="2025-02-02T03:04:05Z",
        correction_reason="Betrag berichtigt",
    )
    session = FakeSession()
    module.correct_event("account-1", previous.id, body, session)
    row = session.added[0]
    assert row.building_id == previous.building_id
    assert row.source_payment_allocation_id == previous.source_payment_allocation_id
    assert row.source_component == previous.source_component


def test_readiness_projects_only_current_tax_event_leaves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _api()
    original = SimpleNamespace(
        id="event-original",
        building_id="building-1",
        payment_date=datetime(2025, 2, 1, tzinfo=UTC).date(),
        due_date=None,
        category="kaltmiete",
        amount_cents=100_000,
        direction="einnahme",
        source_snapshot={},
        supersedes_tax_event_id=None,
    )
    correction = SimpleNamespace(
        id="event-correction",
        building_id="building-1",
        payment_date=datetime(2025, 2, 1, tzinfo=UTC).date(),
        due_date=None,
        category="kaltmiete",
        amount_cents=90_000,
        direction="einnahme",
        source_snapshot={},
        supersedes_tax_event_id="event-original",
    )

    class LeafSession(_ReadinessSession):
        def __init__(self) -> None:
            super().__init__()
            self.events = [original, correction]

    calls: list[dict[str, Any]] = []

    def ready(**kwargs: object) -> object:
        calls.append(kwargs)
        return SimpleNamespace(findings=(), rechtsstand="07/2026", production_blocked=True)

    monkeypatch.setattr(module, "evaluate_export_readiness", ready)
    session = LeafSession()
    module.evaluate_readiness("account-1", _readiness_body(module), session)
    ledger_events: Any = calls[0]["ledger_events"]
    assert [event["event_id"] for event in ledger_events] == ["event-correction"]


def test_mapping_entries_must_match_the_path_tax_year() -> None:
    module = _api()

    class FakeSession:
        def __init__(self) -> None:
            self.info = {"tax_role": Role.TAX_ADVISOR}
            self.added: list[object] = []

        def scalar(self, _statement: object) -> None:
            return None

        def add(self, row: object) -> None:
            self.added.append(row)

        def flush(self) -> None:
            return None

    body = module.TaxMappingCreate.model_validate(
        {
            "mapping": [
                {
                    "taxYear": 2024,
                    "category": "kaltmiete",
                    "anlageVLine": "31",
                    "skr03Account": "8400",
                    "skr04Account": "4400",
                    "direction": "einnahme",
                    "validFrom": "2024-01-01",
                    "verificationFlag": "verify-before-production",
                    "sourceVersion": "test",
                }
            ],
            "sourceVersion": "test",
            "rechtsstand": "07/2026",
            "generatedAt": "2025-01-02T03:04:05Z",
        }
    )
    session = FakeSession()
    with pytest.raises(HTTPException) as rejected:
        module.create_mapping("account-1", 2025, body, session)
    assert rejected.value.status_code == 422
    assert session.added == []
