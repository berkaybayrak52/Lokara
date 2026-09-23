"""Supabase-JWT auth shared by the web and mobile transports.

Authentication establishes only the verified subject. Account context always
comes from an ``/a/{account_id}/...`` URL and is authorized independently.
"""

import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Cookie, Depends, Header, HTTPException
from jwt import PyJWKClient, PyJWKClientError

from .settings import ApiSettings

# Web transport: the Next.js session route stores the JWT in this HttpOnly
# cookie; mobile sends it as a Bearer header. Same token, same verification.
ACCESS_TOKEN_COOKIE = "lokara_access_token"

DEV_TOKEN_EXPIRES_IN_SECONDS = 60 * 60
# Fixed demo identities — must match the lokara_db.seed demo scenario.
DEV_PERSON_ID = "per_demo_owner"
AUTHENTICATED_AUDIENCE = "authenticated"
AUTHENTICATED_ROLE = "authenticated"
REQUIRED_JWT_CLAIMS = ["sub", "exp", "iss", "aud", "role"]


@dataclass(frozen=True)
class AuthContext:
    """Claims the API relies on after JWT verification."""

    person_id: str  # Supabase user id (JWT `sub`) — maps onto Person


@lru_cache(maxsize=8)
def _jwks_client(url: str) -> PyJWKClient:
    """Return a cached client which still refreshes keys on an unknown ``kid``."""

    return PyJWKClient(url)


def verify_supabase_token(
    token: str,
    secret: str | None,
    issuer: str | None = None,
    *,
    algorithm: str = "HS256",
    jwks_url: str | None = None,
) -> AuthContext:
    """Verify the complete Supabase access-token provenance contract.

    Local/CI tokens use HS256. Deployed Supabase tokens use ES256 and the
    project's exact JWKS endpoint. There is no cross-algorithm fallback.
    """
    expected_issuer = issuer or ApiSettings().supabase_jwt_issuer
    try:
        if algorithm == "ES256":
            if jwks_url is None:
                raise jwt.InvalidTokenError("ES256 verifier has no JWKS endpoint")
            verification_key: jwt.PyJWK | str = _jwks_client(jwks_url).get_signing_key_from_jwt(
                token
            )
        elif algorithm == "HS256":
            if secret is None:
                raise jwt.InvalidTokenError("HS256 verifier has no signing secret")
            verification_key = secret
        else:
            raise jwt.InvalidAlgorithmError("Unsupported JWT algorithm")
        payload: dict[str, Any] = jwt.decode(
            token,
            verification_key,
            algorithms=[algorithm],
            issuer=expected_issuer,
            audience=AUTHENTICATED_AUDIENCE,
            options={"require": REQUIRED_JWT_CLAIMS},
        )
    except (jwt.InvalidTokenError, PyJWKClientError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    person_id = payload.get("sub")
    if not isinstance(person_id, str) or not person_id:
        raise HTTPException(status_code=401, detail="Token carries no valid subject")
    if payload.get("aud") != AUTHENTICATED_AUDIENCE:
        raise HTTPException(status_code=401, detail="Token carries no exact authenticated audience")
    if payload.get("role") != AUTHENTICATED_ROLE:
        raise HTTPException(status_code=401, detail="Token carries no authenticated role")
    return AuthContext(person_id=person_id)


def require_auth(
    authorization: Annotated[str | None, Header()] = None,
    lokara_access_token: Annotated[str | None, Cookie(alias=ACCESS_TOKEN_COOKIE)] = None,
) -> AuthContext:
    """FastAPI dependency: JWT via Bearer header (mobile) or HttpOnly cookie
    (web) → verified AuthContext. One verification path for both transports;
    the header wins if both are present."""
    if authorization is not None and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ")
    elif lokara_access_token is not None:
        token = lokara_access_token
    else:
        raise HTTPException(status_code=401, detail="Missing bearer token or session cookie")
    settings = ApiSettings()
    return verify_supabase_token(
        token,
        settings.supabase_jwt_secret,
        settings.supabase_jwt_issuer,
        algorithm=settings.supabase_jwt_algorithm,
        jwks_url=settings.supabase_jwks_url,
    )


def create_dev_token(secret: str | None, issuer: str | None = None) -> str:
    """DEV ONLY — issue a subject-only token through the production auth path."""
    if secret is None:
        raise ValueError("The development token path requires SUPABASE_JWT_SECRET")
    now = int(time.time())
    expected_issuer = issuer or ApiSettings().supabase_jwt_issuer
    return jwt.encode(
        {
            "sub": DEV_PERSON_ID,
            "iss": expected_issuer,
            "aud": AUTHENTICATED_AUDIENCE,
            "role": AUTHENTICATED_ROLE,
            "iat": now,
            "exp": now + DEV_TOKEN_EXPIRES_IN_SECONDS,
        },
        secret,
        algorithm="HS256",
    )


RequireAuth = Annotated[AuthContext, Depends(require_auth)]
