-- Bootstrap Lokara's restricted runtime role in a hosted Supabase project.
--
-- Run with the project's DIRECT connection as the `postgres` migration owner:
--   psql "$DIRECT_URL" -f packages/db/scripts/init-supabase-app-role.sql
--
-- psql prompts for the runtime password without echoing it. The script never
-- prints or stores that password. Re-running it rotates the role password and
-- restores the required grants; it does not remove any data.

\set ON_ERROR_STOP on
\if :{?lokara_app_password}
\else
\prompt -s 'New password for the restricted lokara_app role: ' lokara_app_password
\endif

SELECT format(
  'CREATE ROLE lokara_app LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS',
  :'lokara_app_password'
)
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'lokara_app')
\gexec

SELECT format(
  'ALTER ROLE lokara_app WITH LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS',
  :'lokara_app_password'
)
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
