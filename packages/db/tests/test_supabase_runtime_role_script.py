"""Static contract for the hosted-Supabase runtime-role bootstrap."""

from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "init-supabase-app-role.sql"


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


def test_supabase_runtime_password_is_prompted_and_not_literal() -> None:
    sql = SCRIPT.read_text()

    assert "\\prompt -s" in sql
    assert ":'lokara_app_password'" in sql
    assert "PASSWORD 'lokara'" not in sql
