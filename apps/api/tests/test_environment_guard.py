"""The `ENVIRONMENT` guard — three ways into a deployment with auth effectively off.

`docs/01-tech-stack-and-decisions.md` → **D9**. `.env.example` ships
`AUTH_DEV_TOKEN="true"`, `DEMO_SEED_ENABLED="true"` and a `SUPABASE_JWT_SECRET` that is
published in this repository, and nothing in the tree reads an `ENVIRONMENT`/`APP_ENV`.
Each one alone is a dev-token minter, a seeder that also DELETEs, and a known signing key.

The decision is to fail **at settings construction**, not per request: a per-request
`if settings.auth_dev_token` is one forgotten branch away from being wrong, and the branch
that matters is the one nobody adds.

**Red-window proof:** at `e5de947`, before the implementation existed, the eight guard
cases failed with DID NOT RAISE. The implementation on this slice makes all ten tests
green. No database, no app startup.

Env vars beat the `.env` file in pydantic-settings' precedence order, so `monkeypatch`
here overrides the developer's local file rather than fighting it.
"""

from pathlib import Path

import pytest
from lokara_api.settings import ApiSettings
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_EXAMPLE = REPO_ROOT / ".env.example"

# The literal shipped in .env.example. It must become a named constant in the API so the
# guard compares exactly rather than guessing at a substring.
PUBLISHED_DEV_SECRET = "local-dev-secret-change-me-min-32-chars!!"
SAFE_SECRET = "a-real-deployment-secret-at-least-32-chars"


def _base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """A settings environment that is safe apart from whatever the test then breaks."""
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SAFE_SECRET)
    monkeypatch.setenv("AUTH_DEV_TOKEN", "false")
    monkeypatch.setenv("DEMO_SEED_ENABLED", "false")


class TestEnvironmentIsRequired:
    def test_a_missing_environment_is_a_startup_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No default. A silent fallback to `local` is how a production box ends up with
        the dev switches on and nothing in the logs to say so."""
        _base_env(monkeypatch)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        with pytest.raises(ValidationError):
            ApiSettings()

    def test_an_unknown_environment_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`local | ci | staging | production`, and nothing else. A typo'd `prod` must not
        be read as 'not production' and quietly unlock the dev switches."""
        _base_env(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "prod")
        with pytest.raises(ValidationError):
            ApiSettings()


class TestDeployedEnvironmentsRefuseDevSwitches:
    """Each of the three routes, asserted separately — a guard that only checks the first
    one it finds is a guard that passes for the wrong reason."""

    @pytest.mark.parametrize("environment", ["staging", "production"])
    def test_dev_token_minting_is_refused(
        self, monkeypatch: pytest.MonkeyPatch, environment: str
    ) -> None:
        _base_env(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", environment)
        monkeypatch.setenv("AUTH_DEV_TOKEN", "true")
        with pytest.raises(ValidationError):
            ApiSettings()

    @pytest.mark.parametrize("environment", ["staging", "production"])
    def test_demo_seeding_is_refused(
        self, monkeypatch: pytest.MonkeyPatch, environment: str
    ) -> None:
        """`/demo/reset` DELETEs, and `/demo/load` runs on the unmembered session.
        The boundary is `docs/02` Person read-side constraint 1; its sanctioned
        bootstrap design and checker remain pending in `PLAN.md` Row 4. This flag
        is one of that endpoint's three locks."""
        _base_env(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", environment)
        monkeypatch.setenv("DEMO_SEED_ENABLED", "true")
        with pytest.raises(ValidationError):
            ApiSettings()

    @pytest.mark.parametrize("environment", ["staging", "production"])
    def test_the_published_dev_signing_secret_is_refused(
        self, monkeypatch: pytest.MonkeyPatch, environment: str
    ) -> None:
        """It satisfies `min_length=16`, so the existing validation passes it happily. It
        is also in git, which means anyone can mint a valid token for any subject."""
        _base_env(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", environment)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", PUBLISHED_DEV_SECRET)
        with pytest.raises(ValidationError):
            ApiSettings()


class TestLocalKeepsWorking:
    def test_local_may_have_every_dev_switch_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The control. The guard must not be satisfiable by refusing everything — the
        demo path (clean DB → seed → statement → PDF) runs with all three of these on."""
        monkeypatch.setenv("ENVIRONMENT", "local")
        monkeypatch.setenv("AUTH_DEV_TOKEN", "true")
        monkeypatch.setenv("DEMO_SEED_ENABLED", "true")
        monkeypatch.setenv("SUPABASE_JWT_SECRET", PUBLISHED_DEV_SECRET)
        settings = ApiSettings()
        assert settings.auth_dev_token is True
        assert settings.demo_seed_enabled is True


class TestEnvExampleDocumentsTheKey:
    def test_env_example_ships_an_explicit_environment(self) -> None:
        """A required variable that the example file omits is a required variable every
        new checkout discovers as a crash."""
        example = ENV_EXAMPLE.read_text()
        assert 'ENVIRONMENT="local"' in example, (
            '.env.example must ship ENVIRONMENT="local" — docs/01 D9'
        )
