"""Static contract for the hosted-Supabase runtime-role bootstrap."""

from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "init-supabase-app-role.sql"
MIGRATIONS = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def test_supabase_runtime_role_is_non_owner_and_cannot_bypass_rls() -> None:
    sql = SCRIPT.read_text()

    assert "CREATE ROLE lokara_app LOGIN" in sql
    assert "NOSUPERUSER" in sql
    assert "NOCREATEDB" in sql
    assert "NOCREATEROLE" in sql
    assert "NOBYPASSRLS" in sql
    assert "GRANT CONNECT ON DATABASE postgres TO lokara_app" in sql


def test_supabase_runtime_role_receives_current_and_future_schema_grants() -> None:
    sql = SCRIPT.read_text()

    assert "GRANT USAGE ON SCHEMA public TO lokara_app" in sql
    assert "ON ALL TABLES IN SCHEMA public TO lokara_app" in sql
    assert "ON ALL SEQUENCES IN SCHEMA public TO lokara_app" in sql
    assert "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public" in sql


def test_supabase_runtime_password_is_supplied_without_a_literal() -> None:
    sql = SCRIPT.read_text()

    assert "\\prompt" not in sql
    assert "\\if :{?lokara_app_password}" in sql
    assert "\\quit 3" in sql
    assert ":'lokara_app_password'" in sql
    assert "PASSWORD 'lokara'" not in sql


def test_existing_runtime_role_is_verified_before_password_rotation() -> None:
    sql = SCRIPT.read_text()

    assert "rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls" in sql
    assert "lokara_app has unsafe elevated privileges" in sql
    assert "ALTER ROLE lokara_app WITH LOGIN PASSWORD %L" in sql
    assert "ALTER ROLE lokara_app WITH LOGIN PASSWORD %L NOSUPERUSER" not in sql


def test_bootstrap_function_is_not_exposed_to_supabase_data_api_roles() -> None:
    for revision in ("0014_bootstrap_contexts_read.py", "0042_m10_renter_context.py"):
        migration = (MIGRATIONS / revision).read_text()
        for role in ("anon", "authenticated", "service_role"):
            assert role in migration
        assert "REVOKE EXECUTE ON FUNCTION public.app_bootstrap_contexts(text)" in migration
