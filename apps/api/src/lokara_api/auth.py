"""Supabase-JWT auth (HS256) — port of the NestJS SupabaseJwtGuard.

TODO(supabase): with a real project the `account_id` claim does not exist —
at M5 the account context moves to the URL (/a/{accountId}/…) and the API
resolves Person → Membership → Account, verifying the caller holds that
relationship. Until then tokens carry an explicit account_id claim (see the
dev-token endpoint), and the membership check runs in deps.account_session.
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
DEV_ACCOUNT_ID = "acc_demo_lokara"


@dataclass(frozen=True)
class AuthContext:
    """Claims the API relies on after JWT verification."""

    person_id: str  # Supabase user id (JWT `sub`) — maps onto Person at M5
    account_id: str  # the account whose data this request may touch (RLS context)


def verify_supabase_token(token: str, secret: str) -> AuthContext:
    try:
        payload: dict[str, Any] = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    person_id = payload.get("sub")
    account_id = payload.get("account_id") or (payload.get("app_metadata") or {}).get(
        "account_id"
    )
    if not isinstance(person_id, str) or not isinstance(account_id, str) or not account_id:
        raise HTTPException(status_code=401, detail="Token carries no account context")
    return AuthContext(person_id=person_id, account_id=account_id)


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
    return verify_supabase_token(token, ApiSettings().supabase_jwt_secret)


def create_dev_token(secret: str) -> str:
    """DEV ONLY — a token shaped like a Supabase access token, so the auth path
    is exercisable without a Supabase project. TODO(supabase): delete at M5."""
    now = int(time.time())
    return jwt.encode(
        {
            "sub": DEV_PERSON_ID,
            "account_id": DEV_ACCOUNT_ID,
            "role": "authenticated",
            "iat": now,
            "exp": now + DEV_TOKEN_EXPIRES_IN_SECONDS,
        },
        secret,
        algorithm="HS256",
    )


RequireAuth = Annotated[AuthContext, Depends(require_auth)]
