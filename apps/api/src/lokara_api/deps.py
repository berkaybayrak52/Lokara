"""Request-scoped DB session with the RLS context set — the isolation spine.

Enforced twice per CLAUDE.md rule 3: (1) this dependency verifies the caller
holds a live Membership in the claimed account, (2) Postgres RLS scopes every
row via the transaction-local `app.account_id` GUC underneath.

Endpoints using this dependency are sync `def` on purpose: FastAPI runs them
in the threadpool, so the blocking psycopg driver never stalls the event loop
(async engine + asyncpg can land later without changing the contract).
"""

from collections.abc import Iterator
from contextlib import AbstractContextManager
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException
from lokara_db import DbSettings, Membership, account_scoped_session, create_db_engine
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from .auth import AuthContext, require_auth


@lru_cache(maxsize=1)
def _engine() -> Engine:
    # DATABASE_URL = the non-owner lokara_app role — RLS binds (never DIRECT_URL).
    return create_db_engine(DbSettings().database_url)


def raw_account_scoped_session(account_id: str) -> AbstractContextManager[Session]:
    """An RLS-scoped session WITHOUT the membership gate — only for endpoints
    whose semantics forbid it (/me lists relationships, /demo/load creates the
    membership it would be gated on). RLS still confines every row underneath."""
    return account_scoped_session(_engine(), account_id)


def account_session(
    auth: Annotated[AuthContext, Depends(require_auth)],
) -> Iterator[Session]:
    """Yields a session whose transaction carries the caller's account context.

    The membership check runs under RLS already scoped to the claimed account:
    a caller without a row there gets 403 before any domain data is touched.
    TODO(supabase): at M5 the account id moves from the token claim to the URL
    (/a/{accountId}/…) — this dependency then takes it from the path instead.
    """
    with account_scoped_session(_engine(), auth.account_id) as session:
        membership = session.scalar(
            select(Membership).where(
                Membership.person_id == auth.person_id,
                Membership.account_id == auth.account_id,
                Membership.revoked_at.is_(None),
            )
        )
        if membership is None:
            raise HTTPException(
                status_code=403, detail="Caller holds no membership in this account"
            )
        yield session


AccountSession = Annotated[Session, Depends(account_session)]


def account_session_for_path(
    account_id: str,
    auth: Annotated[AuthContext, Depends(require_auth)],
) -> Iterator[Session]:
    """The URL-carried variant (docs/04 M5 routing, used by /a/{account_id}/…):
    context comes from the path, never the session — the endpoint independently
    verifies the caller holds a live Membership in the account named in the URL
    (CLAUDE.md rule 3: hiding a UI link protects nothing)."""
    with account_scoped_session(_engine(), account_id) as session:
        membership = session.scalar(
            select(Membership).where(
                Membership.person_id == auth.person_id,
                Membership.account_id == account_id,
                Membership.revoked_at.is_(None),
            )
        )
        if membership is None:
            raise HTTPException(
                status_code=403, detail="Caller holds no membership in this account"
            )
        yield session


PathAccountSession = Annotated[Session, Depends(account_session_for_path)]
