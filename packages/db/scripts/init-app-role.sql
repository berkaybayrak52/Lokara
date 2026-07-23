-- Local-dev app role. The superuser (lokara) owns the schema and runs migrations;
-- the API runtime connects as lokara_app, which is NOT a superuser, so the
-- FORCEd RLS policies actually bind. Mirrors Supabase, where the runtime role is
-- not a superuser either. Mounted into docker-entrypoint-initdb.d for fresh
-- volumes; safe to re-run manually on an existing database.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lokara_app') THEN
    CREATE ROLE lokara_app LOGIN PASSWORD 'lokara' NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END $$;

GRANT CONNECT ON DATABASE lokara TO lokara_app;
GRANT USAGE ON SCHEMA public TO lokara_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO lokara_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO lokara_app;

-- Tables created by future migrations (run as lokara) inherit the grants.
ALTER DEFAULT PRIVILEGES FOR ROLE lokara IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO lokara_app;
ALTER DEFAULT PRIVILEGES FOR ROLE lokara IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO lokara_app;
