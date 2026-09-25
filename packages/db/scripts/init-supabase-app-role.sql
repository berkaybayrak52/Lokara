-- Bootstrap Lokara's restricted runtime role in a hosted Supabase project.
--
-- Run with the project's owner connection as `postgres` and provide the password
-- through a psql variable (the value is not printed or stored):
--   psql "$DIRECT_URL" -v "lokara_app_password=$LOKARA_APP_PASSWORD" \
--     -f packages/db/scripts/init-supabase-app-role.sql
--
-- Re-running the script rotates the role password and restores the required
-- grants; it does not remove any data.

\set ON_ERROR_STOP on
\if :{?lokara_app_password}
\else
\echo 'ERROR: provide lokara_app_password with psql -v'
\quit 3
\endif

SELECT format(
  'CREATE ROLE lokara_app LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS',
  :'lokara_app_password'
)
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'lokara_app')
\gexec

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_catalog.pg_roles
    WHERE rolname = 'lokara_app'
      AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)
  ) THEN
    RAISE EXCEPTION 'lokara_app has unsafe elevated privileges';
  END IF;
END $$;

SELECT format('ALTER ROLE lokara_app WITH LOGIN PASSWORD %L', :'lokara_app_password')
\gexec

GRANT CONNECT ON DATABASE postgres TO lokara_app;
GRANT USAGE ON SCHEMA public TO lokara_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO lokara_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO lokara_app;

-- Alembic runs as Supabase's `postgres` role. Future tables and sequences must
-- remain reachable by the runtime role, where FORCE RLS then limits every row.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO lokara_app;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO lokara_app;

\unset lokara_app_password
