"""Add the sole bounded read that is allowed before account context exists.

``app_bootstrap_contexts(text)`` resolves a verified authentication subject to
its local Person and live account Memberships.  It is intentionally the only
``SECURITY DEFINER`` function in ``public``: the owner is a dedicated NOLOGIN,
non-bypass role which can SELECT exactly the three identity tables involved.

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-16
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A separate owner keeps SECURITY DEFINER bounded by ordinary grants and
    # FORCE RLS.  Creation is conditional because roles are cluster-global and
    # may outlive a restored database; the unconditional ALTER below is what
    # makes an existing role satisfy the same bounded contract.
    op.execute(
        """
        DO $role$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_catalog.pg_roles
                WHERE rolname = 'lokara_bootstrap'
            ) THEN
                CREATE ROLE lokara_bootstrap
                NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
            END IF;
        END
        $role$
        """
    )
    op.execute(
        """
        ALTER ROLE lokara_bootstrap
        NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS
        """
    )

    # A restored cluster could also carry stale memberships for the role.  It
    # must neither inherit ambient privileges nor be reachable via SET ROLE by
    # another principal, so normalize both directions before granting anything.
    op.execute(
        """
        DO $memberships$
        DECLARE
            membership record;
        BEGIN
            FOR membership IN
                SELECT granted.rolname AS granted_role,
                       member.rolname AS member_role
                FROM pg_catalog.pg_auth_members AS edge
                JOIN pg_catalog.pg_roles AS granted ON granted.oid = edge.roleid
                JOIN pg_catalog.pg_roles AS member ON member.oid = edge.member
                WHERE granted.rolname = 'lokara_bootstrap'
                   OR member.rolname = 'lokara_bootstrap'
            LOOP
                EXECUTE format(
                    'REVOKE %I FROM %I',
                    membership.granted_role,
                    membership.member_role
                );
            END LOOP;
        END
        $memberships$
        """
    )

    # Reusing a cluster-global role must not preserve direct privileges from an
    # older database incarnation.  Start from no application-owned privileges,
    # then grant only the schema usage and three reads required by the function.
    op.execute("REVOKE ALL PRIVILEGES ON SCHEMA public FROM lokara_bootstrap")
    op.execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM lokara_bootstrap")
    op.execute("REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM lokara_bootstrap")
    op.execute("REVOKE ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public FROM lokara_bootstrap")
    op.execute("GRANT USAGE ON SCHEMA public TO lokara_bootstrap")
    op.execute("GRANT SELECT ON TABLE person, membership, account TO lokara_bootstrap")

    # These policies are permissive only for the named bootstrap owner.  The TO
    # clauses are load-bearing: USING (true) must never apply to PUBLIC traffic.
    op.execute(
        """
        CREATE POLICY person_bootstrap_select ON person
        FOR SELECT TO lokara_bootstrap
        USING (true)
        """
    )
    op.execute(
        """
        CREATE POLICY membership_bootstrap_select ON membership
        FOR SELECT TO lokara_bootstrap
        USING (true)
        """
    )
    op.execute(
        """
        CREATE POLICY account_bootstrap_select ON account
        FOR SELECT TO lokara_bootstrap
        USING (true)
        """
    )

    op.execute(
        """
        CREATE FUNCTION public.app_bootstrap_contexts(p_person_id text)
        RETURNS TABLE (
            person_id text,
            email text,
            account_id text,
            account_name text,
            account_shape public.account_shape,
            membership_role public.role
        )
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT
                p.id::text AS person_id,
                p.email::text AS email,
                a.id::text AS account_id,
                a.name::text AS account_name,
                a.shape AS account_shape,
                m.role AS membership_role
            FROM public.person AS p
            LEFT JOIN public.membership AS m
              ON m.person_id = p.id
             AND m.revoked_at IS NULL
            LEFT JOIN public.account AS a
              ON a.id = m.account_id
            WHERE p.id = p_person_id
            ORDER BY a.name NULLS LAST, a.id
        $function$
        """
    )
    op.execute("ALTER FUNCTION public.app_bootstrap_contexts(text) OWNER TO lokara_bootstrap")
    op.execute("REVOKE ALL ON FUNCTION public.app_bootstrap_contexts(text) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION public.app_bootstrap_contexts(text) TO lokara_app")


def downgrade() -> None:
    # Remove the callable before removing the privileges and role it depends on.
    op.execute("REVOKE EXECUTE ON FUNCTION public.app_bootstrap_contexts(text) FROM lokara_app")
    op.execute("DROP FUNCTION public.app_bootstrap_contexts(text)")

    op.execute("DROP POLICY account_bootstrap_select ON account")
    op.execute("DROP POLICY membership_bootstrap_select ON membership")
    op.execute("DROP POLICY person_bootstrap_select ON person")

    op.execute("REVOKE SELECT ON TABLE person, membership, account FROM lokara_bootstrap")
    op.execute("REVOKE USAGE ON SCHEMA public FROM lokara_bootstrap")
    # Roles are cluster-global while Alembic state is database-local.  Keep the
    # now privilege-free NOLOGIN/NOINHERIT role so downgrading one restored
    # database cannot delete an owner that another database still depends on;
    # a later upgrade safely reuses and normalizes it.
