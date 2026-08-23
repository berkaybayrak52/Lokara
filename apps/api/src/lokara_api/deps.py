"""Database session boundaries with transaction-local RLS context.

Ordinary ``/a/{account_id}/...`` requests use ``PathAccountSession``: the URL
names the account, a live Membership independently authorizes it, and Postgres
RLS scopes every row underneath. The fixed ``DEMO_ACCOUNT_ID`` load/reset path
is the narrow exception: it uses ``unmembered_account_session`` because loading
creates the Membership it would otherwise require, while still setting the
same RLS context.

Endpoints using this dependency are sync `def` on purpose: FastAPI runs them
in the threadpool, so the blocking psycopg driver never stalls the event loop
(async engine + asyncpg can land later without changing the contract).
"""

from collections.abc import Iterator
from contextlib import AbstractContextManager
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException
from lokara_db import (
    BuildingAssignment,
    DbSettings,
    Membership,
    Role,
    account_scoped_session,
    create_db_engine,
)
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from .auth import AuthContext, require_auth


@lru_cache(maxsize=1)
def _engine() -> Engine:
    # DATABASE_URL = the non-owner lokara_app role — RLS binds (never DIRECT_URL).
    return create_db_engine(DbSettings().database_url)


def unmembered_account_session(account_id: str) -> AbstractContextManager[Session]:
    """An RLS-scoped session for fixed-account demo bootstrap writes only.

    Demo load creates the Membership that would otherwise gate it, while demo
    reset must operate on that same fixed account. The helper remains scoped by
    ``app.account_id`` underneath and must not be used for ordinary requests.
    """
    return account_scoped_session(_engine(), account_id)


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
        if membership.role is Role.TAX_ADVISOR:
            raise HTTPException(
                status_code=403, detail="Tax advisor portal routes are not available yet"
            )
        assignment_ids = frozenset(
            session.scalars(
                select(BuildingAssignment.building_id).where(
                    BuildingAssignment.membership_id == membership.id
                )
            ).all()
        )
        # Local import avoids a dependency cycle: authorization needs the
        # PathAccountSession alias while this dependency creates it.
        from .authorization import PortalScope

        session.info["portal_scope"] = PortalScope(
            role=membership.role,
            building_ids=assignment_ids if membership.role is Role.EMPLOYEE else frozenset(),
        )
        yield session


PathAccountSession = Annotated[Session, Depends(account_session_for_path)]
