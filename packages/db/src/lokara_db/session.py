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

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from .settings import sqlalchemy_url


def create_db_engine(url: str) -> Engine:
    return create_engine(sqlalchemy_url(url), pool_pre_ping=True)


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
