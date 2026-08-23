"""Engine + RLS-scoped session helpers.

Isolation is enforced twice (CLAUDE.md rule 3): app logic scopes every query by
account_id, and Postgres RLS backstops it. The RLS context is a per-transaction
GUC (`app.account_id`); `set_config(..., is_local => true)` dies with the
transaction, so it can never leak across requests sharing a pooled connection.

The engine for request traffic MUST be built from DATABASE_URL (the non-owner
`lokara_app` role) — owners/superusers bypass RLS. DIRECT_URL is for migrations.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from .models import AccountShape, Role
from .settings import sqlalchemy_url


def create_db_engine(url: str) -> Engine:
    return create_engine(sqlalchemy_url(url), pool_pre_ping=True)


@dataclass(frozen=True, slots=True)
class BootstrapContext:
    """One typed row returned by the bounded pre-account-context read."""

    person_id: str
    email: str
    account_id: str | None
    account_name: str | None
    account_shape: AccountShape | None
    membership_role: Role | None


def bootstrap_contexts(engine: Engine, person_id: str) -> tuple[BootstrapContext, ...]:
    """Resolve a verified subject and its live Memberships without account context.

    The database function is the complete authorization boundary for this one
    pre-context read.  This helper neither sets ``app.account_id`` nor issues a
    direct table query.
    """
    statement = text("SELECT * FROM public.app_bootstrap_contexts(CAST(:person_id AS text))")
    with Session(engine) as session:
        rows = session.execute(statement, {"person_id": person_id}).all()

    return tuple(
        BootstrapContext(
            person_id=str(row.person_id),
            email=str(row.email),
            account_id=str(row.account_id) if row.account_id is not None else None,
            account_name=str(row.account_name) if row.account_name is not None else None,
            account_shape=(
                AccountShape(str(row.account_shape)) if row.account_shape is not None else None
            ),
            membership_role=(
                Role(str(row.membership_role)) if row.membership_role is not None else None
            ),
        )
        for row in rows
    )


@contextmanager
def account_scoped_session(engine: Engine, account_id: str) -> Iterator[Session]:
    """One transaction with the caller's account_id as RLS context.

    The caller must already have verified that the authenticated Person holds
    the claimed account relationship — the URL/menu is navigation, not
    authorization. Commits on clean exit, rolls back on exception.
    """
    with Session(engine) as session, session.begin():
        session.execute(
            text("SELECT set_config('app.account_id', :account_id, true)"),
            {"account_id": account_id},
        )
        yield session
