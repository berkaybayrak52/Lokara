"""Add the bounded renter bootstrap context and tenancy-scoped RLS surface."""

from collections.abc import Sequence

from alembic import op

revision = "0042"
down_revision = "0041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NO_RENTER_CONTEXT = "NULLIF(current_setting('app.tenancy_id', true), '') IS NULL"


def _guard_account_policies() -> None:
    op.execute(
        f"""
        DO $policies$
        DECLARE
            policy record;
        BEGIN
            FOR policy IN
                SELECT
                    n.nspname AS schema_name,
                    c.relname AS table_name,
                    p.polname AS policy_name,
                    pg_get_expr(p.polqual, p.polrelid) AS using_expression,
                    pg_get_expr(p.polwithcheck, p.polrelid) AS check_expression
                FROM pg_catalog.pg_policy AS p
                JOIN pg_catalog.pg_class AS c ON c.oid = p.polrelid
                JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND 0 = ANY(p.polroles)
                  AND (
                      COALESCE(pg_get_expr(p.polqual, p.polrelid), '')
                          LIKE '%app.account_id%'
                      OR COALESCE(pg_get_expr(p.polwithcheck, p.polrelid), '')
                          LIKE '%app.account_id%'
                  )
            LOOP
                IF policy.using_expression IS NOT NULL
                   AND policy.check_expression IS NOT NULL THEN
                    EXECUTE format(
                        $policy_sql$
                        ALTER POLICY %I ON %I.%I
                        USING ((%s) AND ({_NO_RENTER_CONTEXT}))
                        WITH CHECK ((%s) AND ({_NO_RENTER_CONTEXT}))
                        $policy_sql$,
                        policy.policy_name,
                        policy.schema_name,
                        policy.table_name,
                        policy.using_expression,
                        policy.check_expression
                    );
                ELSIF policy.using_expression IS NOT NULL THEN
                    EXECUTE format(
                        $policy_sql$
                        ALTER POLICY %I ON %I.%I
                        USING ((%s) AND ({_NO_RENTER_CONTEXT}))
                        $policy_sql$,
                        policy.policy_name,
                        policy.schema_name,
                        policy.table_name,
                        policy.using_expression
                    );
                ELSIF policy.check_expression IS NOT NULL THEN
                    EXECUTE format(
                        $policy_sql$
                        ALTER POLICY %I ON %I.%I
                        WITH CHECK ((%s) AND ({_NO_RENTER_CONTEXT}))
                        $policy_sql$,
                        policy.policy_name,
                        policy.schema_name,
                        policy.table_name,
                        policy.check_expression
                    );
                END IF;
            END LOOP;
        END
        $policies$
        """
    )


def _restore_account_policies() -> None:
    # Revision 0041 has one global table policy (`person`) and otherwise uses
    # the account row's `id` or the domain row's `account_id`.  Preserve each
    # policy's command and roles while restoring those exact pre-R2 predicates.
    op.execute(
        """
        DO $policies$
        DECLARE
            policy record;
            account_expression text;
        BEGIN
            FOR policy IN
                SELECT
                    n.nspname AS schema_name,
                    c.relname AS table_name,
                    p.polname AS policy_name,
                    p.polqual IS NOT NULL AS has_using,
                    p.polwithcheck IS NOT NULL AS has_check
                FROM pg_catalog.pg_policy AS p
                JOIN pg_catalog.pg_class AS c ON c.oid = p.polrelid
                JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND 0 = ANY(p.polroles)
                  AND (
                      COALESCE(pg_get_expr(p.polqual, p.polrelid), '')
                          LIKE '%app.tenancy_id%'
                      OR COALESCE(pg_get_expr(p.polwithcheck, p.polrelid), '')
                          LIKE '%app.tenancy_id%'
                  )
            LOOP
                IF policy.table_name = 'person' THEN
                    account_expression :=
                        '(EXISTS (SELECT 1 FROM public.membership AS m '
                        'WHERE m.person_id = person.id '
                        'AND m.account_id = current_setting(''app.account_id'', true))) '
                        'OR (EXISTS (SELECT 1 FROM public.renter AS r '
                        'WHERE r.person_id = person.id '
                        'AND r.account_id = current_setting(''app.account_id'', true)))';
                ELSIF policy.table_name = 'account' THEN
                    account_expression :=
                        'id = current_setting(''app.account_id'', true)';
                ELSE
                    account_expression :=
                        'account_id = current_setting(''app.account_id'', true)';
                END IF;

                IF policy.has_using AND policy.has_check THEN
                    EXECUTE format(
                        'ALTER POLICY %I ON %I.%I USING (%s) WITH CHECK (%s)',
                        policy.policy_name,
                        policy.schema_name,
                        policy.table_name,
                        account_expression,
                        account_expression
                    );
                ELSIF policy.has_using THEN
                    EXECUTE format(
                        'ALTER POLICY %I ON %I.%I USING (%s)',
                        policy.policy_name,
                        policy.schema_name,
                        policy.table_name,
                        account_expression
                    );
                ELSIF policy.has_check THEN
                    EXECUTE format(
                        'ALTER POLICY %I ON %I.%I WITH CHECK (%s)',
                        policy.policy_name,
                        policy.schema_name,
                        policy.table_name,
                        account_expression
                    );
                END IF;
            END LOOP;
        END
        $policies$
        """
    )


def _create_renter_bootstrap_function() -> None:
    op.execute(
        """
        CREATE FUNCTION public.app_bootstrap_contexts(p_person_id text)
        RETURNS TABLE (
            person_id text,
            email text,
            context_kind text,
            account_id text,
            account_name text,
            account_shape public.account_shape,
            membership_role public.role,
            tenancy_id text
        )
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            WITH membership_contexts AS (
                SELECT
                    p.id::text AS person_id,
                    p.email::text AS email,
                    'MEMBERSHIP'::text AS context_kind,
                    a.id::text AS account_id,
                    a.name::text AS account_name,
                    a.shape AS account_shape,
                    m.role AS membership_role,
                    NULL::text AS tenancy_id,
                    1 AS context_order
                FROM public.person AS p
                JOIN public.membership AS m
                  ON m.person_id = p.id
                 AND m.revoked_at IS NULL
                JOIN public.account AS a ON a.id = m.account_id
                WHERE p.id = p_person_id
            ),
            renter_contexts AS (
                SELECT DISTINCT
                    p.id::text AS person_id,
                    p.email::text AS email,
                    'RENTER_TENANCY'::text AS context_kind,
                    t.account_id::text AS account_id,
                    NULL::text AS account_name,
                    NULL::public.account_shape AS account_shape,
                    NULL::public.role AS membership_role,
                    t.id::text AS tenancy_id,
                    2 AS context_order
                FROM public.person AS p
                JOIN public.renter AS r ON r.person_id = p.id
                JOIN public.tenancy_party AS tp
                  ON tp.renter_id = r.id
                 AND tp.account_id = r.account_id
                JOIN public.tenancy AS t
                  ON t.id = tp.tenancy_id
                 AND t.account_id = tp.account_id
                WHERE p.id = p_person_id
            ),
            subject_context AS (
                SELECT
                    p.id::text AS person_id,
                    p.email::text AS email,
                    'SUBJECT'::text AS context_kind,
                    NULL::text AS account_id,
                    NULL::text AS account_name,
                    NULL::public.account_shape AS account_shape,
                    NULL::public.role AS membership_role,
                    NULL::text AS tenancy_id,
                    3 AS context_order
                FROM public.person AS p
                WHERE p.id = p_person_id
                  AND NOT EXISTS (SELECT 1 FROM membership_contexts)
                  AND NOT EXISTS (SELECT 1 FROM renter_contexts)
            ),
            all_contexts AS (
                SELECT * FROM membership_contexts
                UNION ALL
                SELECT * FROM renter_contexts
                UNION ALL
                SELECT * FROM subject_context
            )
            SELECT
                context.person_id,
                context.email,
                context.context_kind,
                context.account_id,
                context.account_name,
                context.account_shape,
                context.membership_role,
                context.tenancy_id
            FROM all_contexts AS context
            ORDER BY
                context.context_order,
                context.account_name NULLS LAST,
                context.account_id,
                context.tenancy_id
        $function$
        """
    )
    op.execute("ALTER FUNCTION public.app_bootstrap_contexts(text) OWNER TO lokara_bootstrap")
    op.execute("REVOKE ALL ON FUNCTION public.app_bootstrap_contexts(text) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION public.app_bootstrap_contexts(text) TO lokara_app")


def _create_membership_bootstrap_function() -> None:
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
            LEFT JOIN public.account AS a ON a.id = m.account_id
            WHERE p.id = p_person_id
            ORDER BY a.name NULLS LAST, a.id
        $function$
        """
    )
    op.execute("ALTER FUNCTION public.app_bootstrap_contexts(text) OWNER TO lokara_bootstrap")
    op.execute("REVOKE ALL ON FUNCTION public.app_bootstrap_contexts(text) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION public.app_bootstrap_contexts(text) TO lokara_app")


def upgrade() -> None:
    _guard_account_policies()

    op.execute("DROP FUNCTION public.app_bootstrap_contexts(text)")
    op.execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM lokara_bootstrap")
    op.execute(
        "GRANT SELECT ON TABLE person, membership, account, renter, tenancy_party, tenancy "
        "TO lokara_bootstrap"
    )
    for table in ("renter", "tenancy_party", "tenancy"):
        op.execute(
            f"CREATE POLICY {table}_bootstrap_select ON public.{table} "
            "FOR SELECT TO lokara_bootstrap USING (true)"
        )
    _create_renter_bootstrap_function()

    op.execute(
        """
        CREATE POLICY tenancy_renter_select ON public.tenancy
        FOR SELECT TO lokara_app
        USING (
            account_id = current_setting('app.account_id', true)
            AND id = current_setting('app.tenancy_id', true)
        )
        """
    )
    op.execute(
        """
        CREATE POLICY unit_renter_select ON public.unit
        FOR SELECT TO lokara_app
        USING (
            account_id = current_setting('app.account_id', true)
            AND id IN (
                SELECT renter_tenancy.unit_id
                FROM public.tenancy AS renter_tenancy
                WHERE renter_tenancy.id = current_setting('app.tenancy_id', true)
                  AND renter_tenancy.account_id = current_setting('app.account_id', true)
            )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY building_renter_select ON public.building
        FOR SELECT TO lokara_app
        USING (
            account_id = current_setting('app.account_id', true)
            AND id IN (
                SELECT renter_unit.building_id
                FROM public.unit AS renter_unit
                JOIN public.tenancy AS renter_tenancy
                  ON renter_tenancy.unit_id = renter_unit.id
                 AND renter_tenancy.account_id = renter_unit.account_id
                WHERE renter_tenancy.id = current_setting('app.tenancy_id', true)
                  AND renter_tenancy.account_id = current_setting('app.account_id', true)
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY building_renter_select ON public.building")
    op.execute("DROP POLICY unit_renter_select ON public.unit")
    op.execute("DROP POLICY tenancy_renter_select ON public.tenancy")

    op.execute("DROP FUNCTION public.app_bootstrap_contexts(text)")
    for table in ("tenancy", "tenancy_party", "renter"):
        op.execute(f"DROP POLICY {table}_bootstrap_select ON public.{table}")
    op.execute("REVOKE SELECT ON TABLE renter, tenancy_party, tenancy FROM lokara_bootstrap")
    _create_membership_bootstrap_function()

    _restore_account_policies()
