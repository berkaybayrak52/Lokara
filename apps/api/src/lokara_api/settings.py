"""API configuration (pydantic-settings). DB URLs live in lokara_db.DbSettings."""

from typing import TYPE_CHECKING, Any, Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# local | ci -> developer machines and the CI job; both run the demo path with every
# dev switch on. staging | production -> deployed, reachable, and therefore guarded.
Environment = Literal["local", "ci", "staging", "production"]

# The signing secret shipped in .env.example (line 33) and committed to this
# repository. Anyone holding it can mint a valid token for any subject, so a deployed
# environment must never keep it. Named constant, not an inline literal: the guard
# compares it exactly rather than guessing at a substring or a prefix.
PUBLISHED_DEV_JWT_SECRET = "local-dev-secret-change-me-min-32-chars!!"

DEPLOYED_ENVIRONMENTS: frozenset[Environment] = frozenset({"staging", "production"})


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Required, no default (docs/01 D9). A missing ENVIRONMENT is a startup failure:
    # a silent fallback to "local" is how a production box ends up with the dev
    # switches on and nothing in the logs to say so. An unknown value ("prod") fails
    # the Literal rather than being read as "not production".
    environment: Environment
    # TODO(supabase): the real project's JWT secret (Settings → API). The auth
    # dependency verifies HS256 access tokens with it — when wiring real
    # Supabase, check whether the project uses HS256 or asymmetric JWKS.
    # Empty default only so mypy accepts env-driven construction; the validated
    # min_length makes a missing SUPABASE_JWT_SECRET fail loudly at startup.
    # min_length alone is not enough: the published dev secret satisfies it happily,
    # which is why _refuse_dev_switches_in_deployed_environments checks it by value.
    supabase_jwt_secret: str = Field(default="", min_length=16, validate_default=True)
    # Dev-only: enables POST /auth/dev-token. MUST be false (or unset) in prod.
    auth_dev_token: bool = False
    # Dev/pitch-only: enables POST /demo/load (one-click demo seed). Off by
    # default — any authenticated caller could otherwise reset the demo account.
    demo_seed_enabled: bool = False
    api_port: int = 3001
    web_origin: str = "http://localhost:3000"

    if TYPE_CHECKING:
        # Type-checking only; pydantic-settings builds the real __init__ at runtime.
        # Without this, pydantic's mypy plugin synthesises an __init__ in which the
        # now-required `environment` is a required *keyword argument*, and every
        # `ApiSettings()` in the tree becomes a [call-arg] error — even though the
        # value comes from the environment, which is the entire point of the class.
        def __init__(self, **overrides: Any) -> None: ...

    @model_validator(mode="after")
    def _refuse_dev_switches_in_deployed_environments(self) -> Self:
        """Fail at settings construction, never per request (docs/01 D9).

        A per-request `if settings.auth_dev_token` is one forgotten branch away from
        being wrong, and the branch that matters is the one nobody adds. Refusing to
        build the settings object takes the process down once, loudly, at boot — the
        failure mode you want for "this deployment is unsafe".

        All three routes are checked independently: reporting only the first one found
        sends an operator to close one of three open doors.
        """
        if self.environment not in DEPLOYED_ENVIRONMENTS:
            return self

        problems: list[str] = []
        if self.auth_dev_token:
            problems.append("AUTH_DEV_TOKEN is on (mints tokens for any subject) — unset it")
        if self.demo_seed_enabled:
            problems.append(
                "DEMO_SEED_ENABLED is on (POST /demo/load seeds, POST /demo/reset DELETEs) "
                "— unset it"
            )
        if self.supabase_jwt_secret == PUBLISHED_DEV_JWT_SECRET:
            problems.append(
                "SUPABASE_JWT_SECRET is still the placeholder published in .env.example "
                "— set a real deployment secret"
            )

        if problems:
            raise ValueError(
                f"Unsafe configuration for ENVIRONMENT={self.environment}: "
                + "; ".join(problems)
                + ". The API refuses to start (docs/01 D9)."
            )
        return self
