"""API configuration (pydantic-settings). DB URLs live in lokara_db.DbSettings."""

from typing import TYPE_CHECKING, Any, Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# local | ci -> developer machines and the CI job; both run the demo path with every
# dev switch on. staging | production -> deployed, reachable, and therefore guarded.
Environment = Literal["local", "ci", "staging", "production"]
JwtAlgorithm = Literal["HS256", "ES256"]

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
    # Local/CI keeps the deterministic HS256 token path. New Supabase projects use
    # asymmetric signing keys, so deployed instances select ES256 and verify the
    # public key through the project's exact JWKS endpoint. The two modes are
    # mutually exclusive; a failed JWKS lookup never falls back to a shared secret.
    supabase_jwt_algorithm: JwtAlgorithm = "HS256"
    supabase_jwt_secret: str = ""
    supabase_jwks_url: str | None = None
    # Exact Supabase Auth issuer. The loopback default keeps local/CI auth usable
    # without requiring developers to retrofit an existing .env; deployments set
    # their project's https://<project-ref>.supabase.co/auth/v1 value explicitly.
    supabase_jwt_issuer: str = Field(
        default="http://127.0.0.1:54321/auth/v1", min_length=1, validate_default=True
    )
    # Dev-only: enables POST /auth/dev-token. MUST be false (or unset) in prod.
    auth_dev_token: bool = False
    # Dev/pitch-only: enables POST /demo/load (one-click demo seed). Off by
    # default — any authenticated caller could otherwise reset the demo account.
    demo_seed_enabled: bool = False
    # Public Nominatim is a demo-only provider. External geocoding stays off
    # unless an operator explicitly enables it; creation still succeeds when
    # the provider is unavailable.
    geocoding_enabled: bool = False
    geocoding_endpoint: str = Field(
        default="https://nominatim.openstreetmap.org/search",
        min_length=1,
        validate_default=True,
    )
    geocoding_contact_email: str = Field(
        default="kontakt@lokara.de", min_length=1, validate_default=True
    )
    geocoding_timeout_seconds: float = Field(default=3.0, gt=0, le=10)
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

        All unsafe routes are checked independently: reporting only the first one found
        sends an operator to close one open door while leaving the others unnoticed.
        """
        problems: list[str] = []
        expected_jwks_url = f"{self.supabase_jwt_issuer.rstrip('/')}/.well-known/jwks.json"
        if self.supabase_jwt_algorithm == "HS256":
            if len(self.supabase_jwt_secret) < 16:
                problems.append(
                    "SUPABASE_JWT_SECRET of at least 16 characters is required for HS256"
                )
            if self.supabase_jwks_url is not None:
                problems.append("SUPABASE_JWKS_URL must be unset for HS256")
        else:
            if self.supabase_jwks_url is None:
                problems.append("SUPABASE_JWKS_URL is required for ES256")
            elif self.supabase_jwks_url != expected_jwks_url:
                problems.append(
                    "SUPABASE_JWKS_URL must be the configured issuer's exact JWKS endpoint"
                )
            if self.supabase_jwt_secret:
                problems.append("SUPABASE_JWT_SECRET must be unset for ES256")
            if self.auth_dev_token:
                problems.append("AUTH_DEV_TOKEN requires the local HS256 mode")

        if self.environment not in DEPLOYED_ENVIRONMENTS:
            if problems:
                raise ValueError("Unsafe authentication configuration: " + "; ".join(problems))
            return self

        issuer = urlsplit(self.supabase_jwt_issuer)
        if issuer.scheme != "https" or not issuer.hostname:
            problems.append("SUPABASE_JWT_ISSUER must be an absolute HTTPS URL")
        if self.supabase_jwks_url is not None:
            jwks = urlsplit(self.supabase_jwks_url)
            if jwks.scheme != "https" or jwks.hostname != issuer.hostname:
                problems.append("SUPABASE_JWKS_URL must use HTTPS on the issuer host")

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
        geocoding_hostname = urlsplit(self.geocoding_endpoint).hostname
        if (
            self.geocoding_enabled
            and geocoding_hostname is not None
            and geocoding_hostname.casefold().rstrip(".") == "nominatim.openstreetmap.org"
        ):
            problems.append(
                "GEOCODING_ENABLED points at public nominatim.openstreetmap.org "
                "(demo-only provider) — disable it or configure a private provider"
            )

        if problems:
            raise ValueError(
                f"Unsafe configuration for ENVIRONMENT={self.environment}: "
                + "; ".join(problems)
                + ". The API refuses to start (docs/01 D9)."
            )
        return self
