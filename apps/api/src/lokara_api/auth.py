"""Supabase-JWT auth shared by the web and mobile transports.

Authentication establishes only the verified subject. Account context always
comes from an ``/a/{account_id}/...`` URL and is authorized independently.
"""

import time
from dataclasses import dataclass
from typing import Annotated, Any

import jwt
from fastapi import Cookie, Depends, Header, HTTPException

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


def verify_supabase_token(token: str, secret: str, issuer: str | None = None) -> AuthContext:
    """Verify the complete Supabase access-token provenance contract.

    TODO(supabase): confirm whether the real project uses legacy HS256 or
    asymmetric signing keys via JWKS (ES256/RS256). The issuer, audience, role,
    expiry and subject checks remain required with either signing mechanism.
    """
    expected_issuer = issuer or ApiSettings().supabase_jwt_issuer
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            issuer=expected_issuer,
            audience=AUTHENTICATED_AUDIENCE,
            options={"require": REQUIRED_JWT_CLAIMS},
        )
    except jwt.InvalidTokenError as exc:
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
    return verify_supabase_token(token, settings.supabase_jwt_secret, settings.supabase_jwt_issuer)


def create_dev_token(secret: str, issuer: str | None = None) -> str:
    """DEV ONLY — issue a subject-only token through the production auth path."""
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
