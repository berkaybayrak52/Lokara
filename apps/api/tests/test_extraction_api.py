"""Beleg-Upload (M4, canned) — upload → prefill → confirm.

The two properties this file exists to pin down:

1. **Extraction writes nothing.** Uploading a document leaves the cost list
   byte-identical; only the confirm step — the ordinary Kosten erfassen
   endpoint — creates a row. That is what keeps an OCR miss out of a statement.
2. **No cost type is invented.** The extracted category becomes the same
   free-text label the manual form takes, and the Umlageschlüssel is reported
   as *not* extracted. The BetrKV catalogue is a pending spec (docs/08); a test
   that fails when someone starts guessing it is cheap insurance.
"""

import os
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from lokara_api import create_app
from lokara_api.routers.extraction import LOW_CONFIDENCE_PERCENT, MAX_UPLOAD_BYTES
from lokara_api.settings import ApiSettings
from lokara_db import DbSettings, create_db_engine
from lokara_db.seed import DEMO_ACCOUNT_ID, DEMO_PERSON_ID, seed_demo
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

NBSP = " "  # format_eur puts a non-breaking space before the €
_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "db"
TEST_JWT_ISSUER = "https://lokara.test/auth/v1"

BASE = f"/a/{DEMO_ACCOUNT_ID}"
DEMO_BUILDING_ID = "bld_demo_muster12"
EXTRACT_URL = f"{BASE}/buildings/{DEMO_BUILDING_ID}/extractions"

ISO_ACCOUNT_ID = "acc_iso_check"
ISO_PERSON_ID = "per_iso_owner"


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
        seed_demo(session)
    owner.dispose()
    test_client = TestClient(create_app())
    # Immutable classifications and allocation-key history are retained; void
    # stray costs through the production workflow before duplicate assertions.
    for cost in test_client.get(f"{BASE}/buildings/{DEMO_BUILDING_ID}/costs", headers=DEMO).json()[
        "costs"
    ]:
        if cost["id"] != "cost_demo_garbage":
            assert (
                test_client.post(
                    f"{BASE}/costs/{cost['id']}/void",
                    headers=DEMO,
                    json={"reason": "Testbereinigung"},
                ).status_code
                == 200
            )
    yield test_client


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

PDF_BYTES = b"%PDF-1.7\nfake demo invoice\n"


def _upload(
    client: TestClient,
    *,
    name: str = "rechnung.pdf",
    content: bytes = PDF_BYTES,
    headers: dict[str, str] | None = None,
) -> Any:
    return client.post(
        EXTRACT_URL,
        headers=headers if headers is not None else DEMO,
        files={"file": (name, content, "application/pdf")},
    )


def _extract(client: TestClient) -> dict[str, Any]:
    response = _upload(client)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _costs(client: TestClient) -> list[dict[str, Any]]:
    response = client.get(f"{BASE}/buildings/{DEMO_BUILDING_ID}/costs", headers=DEMO)
    assert response.status_code == 200
    costs: list[dict[str, Any]] = response.json()["costs"]
    return costs


def _field(body: dict[str, Any], field_id: str) -> dict[str, Any]:
    field: dict[str, Any] = next(f for f in body["fields"] if f["id"] == field_id)
    return field


class TestExtraction:
    def test_upload_returns_the_canned_invoice_with_per_field_confidence(
        self, client: TestClient
    ) -> None:
        body = _extract(client)

        assert body["documentName"] == "rechnung.pdf"
        assert body["documentConfidencePercent"] == 97
        assert _field(body, "costCategory")["value"] == "Müllabfuhr"
        assert _field(body, "totalAmount")["value"] == f"1.200,00{NBSP}€"
        assert _field(body, "invoiceDate")["value"] == "15.12.2025"
        assert _field(body, "vendorName")["value"] == "Stadtreinigung Frankfurt GmbH"

    def test_the_inferred_field_is_the_one_flagged_for_review(self, client: TestClient) -> None:
        """The review UI's purpose: send the eye to the weak value. The amount
        was read; the category was guessed."""
        body = _extract(client)

        category = _field(body, "costCategory")
        assert category["needsReview"] is True
        assert category["confidencePercent"] < LOW_CONFIDENCE_PERCENT
        assert _field(body, "totalAmount")["needsReview"] is False

    def test_the_provider_is_named_as_a_stub(self, client: TestClient) -> None:
        """No screen may imply a live OCR integration that does not exist."""
        assert "Stub" in _extract(client)["providerLabel"]

    def test_the_allocation_key_is_reported_as_not_extracted(self, client: TestClient) -> None:
        """The guard against inventing the BetrKV catalogue (docs/08).

        The document says nothing about how a cost is apportioned. The prefill
        carries the manual form's own default and says so — the moment someone
        derives a key from the cost type, this fails.
        """
        body = _extract(client)

        assert "Umlageschlüssel" in body["notExtracted"]
        assert "Abrechnungszeitraum" in body["notExtracted"]
        assert body["prefill"]["key"] == "AREA"  # the manual form's default

    def test_extraction_persists_nothing(self, client: TestClient) -> None:
        before = _costs(client)
        _extract(client)
        _extract(client)
        assert _costs(client) == before

    def test_an_already_entered_invoice_is_flagged_as_a_duplicate(self, client: TestClient) -> None:
        """Same label, same amount, overlapping period — the seeded Müllabfuhr.
        A warning, not a block: the response still carries a full prefill."""
        body = _extract(client)

        duplicate = body["duplicate"]
        assert duplicate is not None
        assert duplicate["label"] == "Müllabfuhr"
        assert duplicate["amountEur"] == f"1.200,00{NBSP}€"
        assert body["prefill"]["amountCents"] == 120000


class TestConfirmGoesThroughTheNormalPath:
    def test_the_prefill_creates_a_cost_via_the_ordinary_endpoint(self, client: TestClient) -> None:
        """Confirm is not a second write path: the review form posts the
        prefill (corrected or not) to Kosten erfassen, which applies the same
        validation and the same append-only allocation key."""
        prefill = _extract(client)["prefill"]

        created = client.post(
            f"{BASE}/buildings/{DEMO_BUILDING_ID}/costs", headers=DEMO, json=prefill
        )
        assert created.status_code == 201, created.text
        cost = created.json()
        try:
            assert cost["label"] == "Müllabfuhr"
            assert cost["amountCents"] == 120000  # integer cents, never a float
            assert cost["amountEur"] == f"1.200,00{NBSP}€"
            assert cost["key"] == "AREA"
            assert cost["assignmentCount"] == 1
        finally:
            # Leave immutable evidence intact but remove this test row from
            # later previews through the supported void workflow.
            assert (
                client.post(
                    f"{BASE}/costs/{cost['id']}/void",
                    headers=DEMO,
                    json={"reason": "Testkorrektur"},
                ).status_code
                == 200
            )

    def test_a_corrected_amount_is_what_gets_stored(self, client: TestClient) -> None:
        """The reviewer overrules the extraction — the whole point of the step."""
        prefill = dict(_extract(client)["prefill"])
        prefill["label"] = "Straßenreinigung"
        prefill["amountCents"] = 45050  # 450,50 € typed as German text client-side

        created = client.post(
            f"{BASE}/buildings/{DEMO_BUILDING_ID}/costs", headers=DEMO, json=prefill
        )
        assert created.status_code == 201, created.text
        cost = created.json()
        try:
            assert cost["label"] == "Straßenreinigung"
            assert cost["amountEur"] == f"450,50{NBSP}€"
        finally:
            assert (
                client.post(
                    f"{BASE}/costs/{cost['id']}/void",
                    headers=DEMO,
                    json={"reason": "Testkorrektur"},
                ).status_code
                == 200
            )

    def test_there_is_no_confirm_route_that_writes_a_cost(self) -> None:
        """The contract, asserted against the OpenAPI schema: extraction is
        read-only, so nothing under /extractions may create anything."""
        paths = create_app().openapi()["paths"]
        extraction_paths = [p for p in paths if "extractions" in p]

        assert extraction_paths == ["/a/{account_id}/buildings/{building_id}/extractions"]
        assert set(paths[extraction_paths[0]]) == {"post"}  # the upload itself


class TestUploadValidation:
    def test_unknown_building_is_rejected_before_upload_processing(
        self, client: TestClient
    ) -> None:
        response = client.post(
            f"{BASE}/buildings/bld_missing/extractions",
            headers=DEMO,
            files={"file": ("rechnung.pdf", PDF_BYTES, "application/pdf")},
        )
        assert response.status_code == 404

    def test_an_unsupported_file_type_is_rejected(self, client: TestClient) -> None:
        response = _upload(client, name="tabelle.xlsx")
        assert response.status_code == 422
        assert "PDF" in response.json()["detail"]

    def test_an_empty_file_is_rejected(self, client: TestClient) -> None:
        assert _upload(client, content=b"").status_code == 422

    def test_an_oversized_file_is_rejected(self, client: TestClient) -> None:
        response = _upload(client, content=b"x" * (MAX_UPLOAD_BYTES + 1))
        assert response.status_code == 413

    def test_a_file_at_the_limit_is_accepted(self, client: TestClient) -> None:
        assert _upload(client, content=b"x" * MAX_UPLOAD_BYTES).status_code == 200


class TestExtractionIsolation:
    def test_another_accounts_member_cannot_extract_here(self, client: TestClient) -> None:
        """Same rule as every other route: holding no Membership in the account
        in the URL is a 403, before any document is read."""
        response = _upload(client, headers=_token(ISO_PERSON_ID))
        assert response.status_code == 403

    def test_an_unauthenticated_upload_is_rejected(self, client: TestClient) -> None:
        response = client.post(EXTRACT_URL, files={"file": ("x.pdf", PDF_BYTES, "application/pdf")})
        assert response.status_code == 401
