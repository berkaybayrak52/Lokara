"""Auth + health contract tests — no database required."""

import time

import jwt
import lokara_api.auth as auth_module
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from lokara_api import create_app
from lokara_api.auth import DEV_PERSON_ID
from lokara_api.settings import ApiSettings

TEST_JWT_ISSUER = "https://lokara.test/auth/v1"


def _configured_issuer() -> str:
    return str(getattr(ApiSettings(), "supabase_jwt_issuer", TEST_JWT_ISSUER))


def _valid_claims() -> dict[str, object]:
    now = int(time.time())
    return {
        "sub": DEV_PERSON_ID,
        "iss": _configured_issuer(),
        "aud": "authenticated",
        "role": "authenticated",
        "iat": now,
        "exp": now + 3600,
    }


def _encoded(claims: dict[str, object], secret: str | None = None) -> str:
    return jwt.encode(
        claims,
        secret or ApiSettings().supabase_jwt_secret,
        algorithm="HS256",
    )


def _required_claims(kwargs: dict[str, object]) -> set[str]:
    options = kwargs.get("options")
    if not isinstance(options, dict):
        return set()
    required = options.get("require", [])
    return {str(claim) for claim in required} if isinstance(required, list) else set()


def _require_auth() -> auth_module.AuthContext:
    return auth_module.require_auth(
        authorization="Bearer synthetic-token",
        lokara_access_token=None,
    )


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
        assert client.get("/me").status_code == 401

    def test_garbage_token_is_401(self, client: TestClient) -> None:
        response = client.get("/me", headers={"Authorization": "Bearer not-a-jwt"})
        assert response.status_code == 401

    def test_wrong_signature_is_401(self, client: TestClient) -> None:
        forged = _encoded(
            _valid_claims(),
            secret="wrong-secret-wrong-secret-32-bytes-long!",
        )
        response = client.get("/me", headers={"Authorization": f"Bearer {forged}"})
        assert response.status_code == 401

    def test_compliant_subject_only_token_is_authenticated(self, client: TestClient) -> None:
        """Account context comes from /a/{account_id}, never from the JWT.

        The deliberately incomplete pure-calculation body reaches Pydantic and returns 422;
        a 401 here means auth still requires the retired account claim.
        """
        token = _encoded(_valid_claims())
        response = client.post("/calc/nk", json={}, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 422
        assert "account_id" not in _valid_claims()

    def test_token_without_subject_is_401(self, client: TestClient) -> None:
        claims = _valid_claims()
        claims.pop("sub")
        token = _encoded(claims)
        response = client.post("/calc/nk", json={}, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    @pytest.mark.parametrize("claim", ["exp", "iss", "aud", "role"])
    def test_missing_required_provenance_claim_is_401(
        self, monkeypatch: pytest.MonkeyPatch, claim: str
    ) -> None:
        claims = _valid_claims()
        claims.pop(claim)

        def decode(*_args: object, **kwargs: object) -> dict[str, object]:
            if claim in _required_claims(kwargs):
                raise jwt.exceptions.MissingRequiredClaimError(claim)
            return claims

        monkeypatch.setattr(jwt, "decode", decode)
        with pytest.raises(HTTPException) as error:
            _require_auth()
        assert error.value.status_code == 401

    def test_expired_token_is_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        claims = _valid_claims()
        claims["exp"] = int(time.time()) - 1

        def decode(*_args: object, **kwargs: object) -> dict[str, object]:
            if "exp" in _required_claims(kwargs):
                raise jwt.ExpiredSignatureError
            return claims

        monkeypatch.setattr(jwt, "decode", decode)
        with pytest.raises(HTTPException) as error:
            _require_auth()
        assert error.value.status_code == 401

    @pytest.mark.parametrize(
        ("claim", "wrong_value"),
        [
            ("iss", "https://attacker.invalid/auth/v1"),
            ("aud", "anon"),
        ],
    )
    def test_mismatched_provenance_claim_is_401(
        self,
        monkeypatch: pytest.MonkeyPatch,
        claim: str,
        wrong_value: str,
    ) -> None:
        claims = _valid_claims()
        claims[claim] = wrong_value

        def decode(*_args: object, **kwargs: object) -> dict[str, object]:
            expected = kwargs.get("issuer" if claim == "iss" else "audience")
            if expected is not None:
                error = (
                    jwt.exceptions.InvalidIssuerError()
                    if claim == "iss"
                    else jwt.exceptions.InvalidAudienceError()
                )
                raise error
            return claims

        monkeypatch.setattr(jwt, "decode", decode)
        with pytest.raises(HTTPException) as error:
            _require_auth()
        assert error.value.status_code == 401

    def test_list_audience_is_rejected_even_when_it_contains_authenticated(
        self, client: TestClient
    ) -> None:
        claims = _valid_claims()
        claims["aud"] = ["authenticated"]
        token = _encoded(claims)

        response = client.post(
            "/calc/nk",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    def test_non_authenticated_role_is_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        claims = _valid_claims()
        claims["role"] = "service_role"

        def decode(*_args: object, **_kwargs: object) -> dict[str, object]:
            return claims

        monkeypatch.setattr(jwt, "decode", decode)
        with pytest.raises(HTTPException) as error:
            _require_auth()
        assert error.value.status_code == 401


class TestAuthSettings:
    def test_issuer_is_explicitly_configured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SUPABASE_JWT_ISSUER", TEST_JWT_ISSUER)
        assert getattr(ApiSettings(), "supabase_jwt_issuer", None) == TEST_JWT_ISSUER


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
            body["accessToken"],
            ApiSettings().supabase_jwt_secret,
            algorithms=["HS256"],
            issuer=_configured_issuer(),
            audience="authenticated",
            options={"require": ["sub", "exp", "iss", "aud", "role"]},
        )
        assert claims["sub"] == DEV_PERSON_ID
        assert claims["iss"] == _configured_issuer()
        assert claims["aud"] == "authenticated"
        assert claims["role"] == "authenticated"
        assert int(claims["exp"]) > int(time.time())
        assert "account_id" not in claims
        assert "account_id" not in claims.get("app_metadata", {})


class TestRoutingSurface:
    def test_legacy_token_scoped_demo_summary_is_retired(self) -> None:
        paths = set(create_app().openapi()["paths"])
        assert "/demo/summary" not in paths
        assert "/a/{account_id}/summary" in paths
