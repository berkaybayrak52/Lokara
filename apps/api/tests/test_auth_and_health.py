"""Auth + health contract tests — no database required."""

import jwt
import pytest
from fastapi.testclient import TestClient
from lokara_api import create_app
from lokara_api.auth import DEV_ACCOUNT_ID, DEV_PERSON_ID
from lokara_api.settings import ApiSettings


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


class TestHealth:
    def test_health_is_public(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["service"] == "lokara-api"


class TestAuthGuard:
    def test_missing_token_is_401(self, client: TestClient) -> None:
        assert client.post("/calc/nk", json={}).status_code == 401
        assert client.get("/demo/summary").status_code == 401

    def test_garbage_token_is_401(self, client: TestClient) -> None:
        response = client.get("/demo/summary", headers={"Authorization": "Bearer not-a-jwt"})
        assert response.status_code == 401

    def test_wrong_signature_is_401(self, client: TestClient) -> None:
        forged = jwt.encode(
            {"sub": DEV_PERSON_ID, "account_id": DEV_ACCOUNT_ID},
            "wrong-secret-wrong-secret-32-bytes-long!",
            algorithm="HS256",
        )
        response = client.get("/demo/summary", headers={"Authorization": f"Bearer {forged}"})
        assert response.status_code == 401

    def test_token_without_account_context_is_401(self, client: TestClient) -> None:
        secret = ApiSettings().supabase_jwt_secret
        token = jwt.encode({"sub": DEV_PERSON_ID}, secret, algorithm="HS256")
        response = client.get("/demo/summary", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Token carries no account context"


class TestDevToken:
    def test_disabled_by_default_returns_403(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AUTH_DEV_TOKEN", "false")
        assert client.post("/auth/dev-token").status_code == 403

    def test_enabled_issues_a_verifiable_supabase_shaped_token(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AUTH_DEV_TOKEN", "true")
        response = client.post("/auth/dev-token")
        assert response.status_code == 200
        body = response.json()
        assert body["expiresInSeconds"] == 3600
        claims = jwt.decode(
            body["accessToken"], ApiSettings().supabase_jwt_secret, algorithms=["HS256"]
        )
        assert claims["sub"] == DEV_PERSON_ID
        assert claims["account_id"] == DEV_ACCOUNT_ID
