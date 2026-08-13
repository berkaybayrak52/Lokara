"""Database configuration (pydantic-settings).

Two URLs on purpose (docs/02 "runtime connects as a non-owner app role"):
- DATABASE_URL — request traffic, as the restricted `lokara_app` role, so the
  FORCEd RLS policies actually bind (owners/superusers bypass RLS).
- DIRECT_URL — migrations only, as the schema owner.
On Supabase this maps onto the pooled vs direct connection split.

TODO(supabase): point both at the Supabase Cloud (EU/Frankfurt) project once it
exists; until then docker-compose.yml provides the local fallback.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

_LIBPQ_SCHEME = "postgresql://"
_SQLALCHEMY_SCHEME = "postgresql+psycopg://"


def sqlalchemy_url(url: str) -> str:
    """Normalizes a libpq-style URL (shared with psql) to the psycopg3 driver."""
    if url.startswith(_LIBPQ_SCHEME):
        return _SQLALCHEMY_SCHEME + url.removeprefix(_LIBPQ_SCHEME)
    return url


class DbSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://lokara_app:lokara@localhost:54322/lokara"
    direct_url: str = "postgresql://lokara:lokara@localhost:54322/lokara"

    @property
    def database_sqlalchemy_url(self) -> str:
        return sqlalchemy_url(self.database_url)

    @property
    def direct_sqlalchemy_url(self) -> str:
        return sqlalchemy_url(self.direct_url)
