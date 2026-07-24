"""API configuration (pydantic-settings). DB URLs live in lokara_db.DbSettings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # TODO(supabase): the real project's JWT secret (Settings → API). The auth
    # dependency verifies HS256 access tokens with it — when wiring real
    # Supabase, check whether the project uses HS256 or asymmetric JWKS.
    # Empty default only so mypy accepts env-driven construction; the validated
    # min_length makes a missing SUPABASE_JWT_SECRET fail loudly at startup.
    supabase_jwt_secret: str = Field(default="", min_length=16, validate_default=True)
    # Dev-only: enables POST /auth/dev-token. MUST be false (or unset) in prod.
    auth_dev_token: bool = False
    api_port: int = 3001
    web_origin: str = "http://localhost:3000"
