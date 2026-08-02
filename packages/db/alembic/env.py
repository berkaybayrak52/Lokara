"""Alembic environment — connects as the schema owner (DIRECT_URL).

Request traffic never uses this role: owners bypass RLS. See lokara_db.settings.
"""

from alembic import context
from lokara_db import Base
from lokara_db.settings import DbSettings
from sqlalchemy import create_engine, pool

target_metadata = Base.metadata


def _url() -> str:
    return DbSettings().direct_sqlalchemy_url


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
