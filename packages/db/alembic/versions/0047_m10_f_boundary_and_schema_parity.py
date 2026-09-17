"""Repair M10 database boundaries and historical schema parity."""

from collections.abc import Sequence

from alembic import op

revision = "0047"
down_revision = "0046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SEARCH_PATH = "pg_catalog, public, pg_temp"


def _install_activation_redemption_guard(*, verify_expiry: bool) -> None:
    if verify_expiry:
        op.execute(f"""
            CREATE OR REPLACE FUNCTION public.enforce_renter_activation_redemption_m10()
            RETURNS trigger
            LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
            BEGIN
              IF current_user = 'lokara_app'
                 AND NEW.account_id IS DISTINCT FROM current_setting('app.account_id', true) THEN
                RETURN NEW;
              END IF;

              NEW.redeemed_at := statement_timestamp();
              PERFORM 1
                FROM public.renter_activation_code AS activation_code
                JOIN public.renter AS renter
                  ON renter.id = activation_code.renter_id
                 AND renter.account_id = activation_code.account_id
               WHERE activation_code.id = NEW.activation_code_id
                 AND activation_code.account_id = NEW.account_id
                 AND activation_code.renter_id = NEW.renter_id
                 AND activation_code.tenancy_id = NEW.tenancy_id
                 AND renter.person_id IS NULL
                 AND statement_timestamp() < activation_code.expires_at;
              IF NOT FOUND THEN
                RAISE EXCEPTION
                  'activation redemption requires a valid, unexpired code and unlinked renter'
                  USING ERRCODE = '23514';
              END IF;
              RETURN NEW;
            END; $$
        """)
        return

    # Restore the 0041 trigger behavior exactly on downgrade.
    op.execute(f"""
        CREATE OR REPLACE FUNCTION public.enforce_renter_activation_redemption_m10()
        RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          IF current_user = 'lokara_app'
             AND NEW.account_id IS DISTINCT FROM current_setting('app.account_id', true) THEN
            RETURN NEW;
          END IF;
          PERFORM 1
            FROM public.renter AS renter
           WHERE renter.id = NEW.renter_id
             AND renter.account_id = NEW.account_id
             AND renter.person_id IS NULL;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'activation redemption requires an unlinked renter'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)


def _install_publication_source_guard(*, verify_payload: bool) -> None:
    statement_payload_guard = ""
    uvi_payload_guard = ""
    if verify_payload:
        statement_payload_guard = """
               AND NEW.content_bytes = archive.content_bytes
               AND NEW.sha256 = archive.sha256
               AND NEW.mime_type = archive.mime_type
               AND NEW.filename = archive.filename
               AND NEW.sha256 = encode(digest(NEW.content_bytes, 'sha256'), 'hex')
        """
        uvi_payload_guard = """
               AND NEW.content_bytes = artifact.content_bytes
               AND NEW.sha256 = artifact.sha256
               AND NEW.mime_type = artifact.mime_type
               AND NEW.filename = artifact.filename
               AND NEW.sha256 = encode(digest(NEW.content_bytes, 'sha256'), 'hex')
        """

    op.execute(f"""
        CREATE OR REPLACE FUNCTION public.enforce_renter_portal_publication_source_m10()
        RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          PERFORM 1
            FROM public.membership AS publisher
           WHERE publisher.id = NEW.published_by_membership_id
             AND publisher.account_id = NEW.account_id
             AND publisher.role = 'OWNER'::public.role
             AND publisher.accepted_at IS NOT NULL
             AND publisher.revoked_at IS NULL;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'renter portal publication requires an active owner publisher'
              USING ERRCODE = '23514';
          END IF;

          IF NEW.source_kind = 'STATEMENT_ARCHIVE' THEN
            PERFORM 1
              FROM public.statement_document_archive AS archive
              JOIN public.statement AS statement
                ON statement.id = archive.statement_id
               AND statement.account_id = archive.account_id
             WHERE archive.id = NEW.statement_archive_id
               AND archive.account_id = NEW.account_id
               AND archive.tenancy_id = NEW.tenancy_id
               AND archive.audience = 'TENANT'
               AND archive.document_type = NEW.document_type
               AND archive.document_type IN ('COVER_LETTER', 'TENANT_STATEMENT')
               AND statement.finalized_at IS NOT NULL
               AND statement.status IN ('FINALIZED'::public.statement_status,
                                        'SUPERSEDED'::public.statement_status)
               AND json_typeof(statement.finalized_snapshot -> 'production_blockers') = 'array'
               AND json_array_length(statement.finalized_snapshot -> 'production_blockers') = 0
               AND NEW.period_start = statement.period_start
               AND NEW.period_end = statement.period_end
               AND NEW.document_month IS NULL
               {statement_payload_guard};
            IF NOT FOUND THEN
              RAISE EXCEPTION 'statement archive is not eligible for renter portal publication'
                USING ERRCODE = '23514';
            END IF;
          ELSIF NEW.source_kind = 'UVI_ARTIFACT' THEN
            PERFORM 1
              FROM public.renter_delivery_artifact AS artifact
              JOIN public.uvi_run AS uvi_run
                ON uvi_run.id = artifact.uvi_run_id
               AND uvi_run.account_id = artifact.account_id
               AND uvi_run.tenancy_id = artifact.tenancy_id
               AND uvi_run.unit_id = artifact.unit_id
             WHERE artifact.id = NEW.renter_delivery_artifact_id
               AND artifact.account_id = NEW.account_id
               AND artifact.tenancy_id = NEW.tenancy_id
               AND artifact.artifact_kind = 'UVI'
               AND artifact.uvi_run_id IS NOT NULL
               AND jsonb_typeof(artifact.production_blockers_snapshot) = 'array'
               AND jsonb_array_length(artifact.production_blockers_snapshot) = 0
               AND NEW.period_start IS NULL
               AND NEW.period_end IS NULL
               AND NEW.document_month = uvi_run.month
               {uvi_payload_guard};
            IF NOT FOUND THEN
              RAISE EXCEPTION 'UVI artifact is not eligible for renter portal publication'
                USING ERRCODE = '23514';
            END IF;
          END IF;
          RETURN NEW;
        END; $$
    """)


def _install_entitlement_chain_guard(*, verify_actor: bool) -> None:
    actor_guard = ""
    trigger_timing = "AFTER"
    if verify_actor:
        trigger_timing = "BEFORE"
        actor_guard = """
          IF current_user = 'lokara_app'
             AND NEW.account_id IS DISTINCT FROM current_setting('app.account_id', true) THEN
            RETURN NEW;
          END IF;

          NEW.recorded_at := statement_timestamp();
          PERFORM 1
            FROM public.membership AS actor
           WHERE actor.id = NEW.recorded_by_membership_id
             AND actor.account_id = NEW.account_id
             AND actor.role = 'OWNER'::public.role
             AND actor.accepted_at IS NOT NULL
             AND actor.revoked_at IS NULL;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'investment entitlement events require an active accepted owner actor'
              USING ERRCODE = '23514';
          END IF;
        """

    op.execute(f"""
        CREATE OR REPLACE FUNCTION public.enforce_investment_entitlement_chain_m10()
        RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        DECLARE predecessor record;
        BEGIN
          {actor_guard}
          IF NEW.version > 1 THEN
            SELECT prior.version INTO predecessor
              FROM public.investment_entitlement_event AS prior
             WHERE prior.id = NEW.supersedes_entitlement_event_id
               AND prior.account_id = NEW.account_id
               AND prior.entitlement_key = NEW.entitlement_key;
            IF NOT FOUND OR NOT predecessor.version = NEW.version - 1 THEN
              RAISE EXCEPTION 'entitlement event must follow the immediate version'
                USING ERRCODE = '23514';
            END IF;
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "DROP TRIGGER IF EXISTS investment_entitlement_event_chain_guard "
        "ON public.investment_entitlement_event"
    )
    op.execute(
        "CREATE TRIGGER investment_entitlement_event_chain_guard "
        f"{trigger_timing} INSERT ON public.investment_entitlement_event FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_investment_entitlement_chain_m10()"
    )


def _repair_historical_schema() -> None:
    # A development-only account.support_code column existed before the consolidated
    # 0040 checkpoint. Fresh databases never had it, so remove it only where present.
    op.execute("""
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
              FROM information_schema.columns
             WHERE table_schema = 'public'
               AND table_name = 'account'
               AND column_name = 'support_code'
          ) THEN
            ALTER TABLE public.account DROP COLUMN IF EXISTS support_code;
          END IF;
        END $$
    """)

    # Historical development schemas carried incomplete or divergent copies of
    # the 0026 building checks. Recreate the canonical constraints conditionally.
    op.execute("ALTER TABLE public.building DROP CONSTRAINT IF EXISTS ck_building_type")
    op.execute("ALTER TABLE public.building DROP CONSTRAINT IF EXISTS ck_building_type_allowed")
    op.execute("ALTER TABLE public.building DROP CONSTRAINT IF EXISTS ck_building_latitude_range")
    op.execute("ALTER TABLE public.building DROP CONSTRAINT IF EXISTS ck_building_longitude_range")
    op.execute("""
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
             WHERE conrelid = 'public.building'::regclass AND conname = 'ck_building_type'
          ) THEN
            ALTER TABLE public.building ADD CONSTRAINT ck_building_type CHECK (
              building_type IN (
                'WOHN_UND_GESCHAEFTSHAUS', 'WOHNHAUS',
                'GEWERBEIMMOBILIE', 'EINFAMILIENHAUS'
              )
            );
          END IF;
          IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
             WHERE conrelid = 'public.building'::regclass
               AND conname = 'ck_building_latitude_range'
          ) THEN
            ALTER TABLE public.building ADD CONSTRAINT ck_building_latitude_range
              CHECK (latitude BETWEEN -90 AND 90);
          END IF;
          IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
             WHERE conrelid = 'public.building'::regclass
               AND conname = 'ck_building_longitude_range'
          ) THEN
            ALTER TABLE public.building ADD CONSTRAINT ck_building_longitude_range
              CHECK (longitude BETWEEN -180 AND 180);
          END IF;
        END $$
    """)


def upgrade() -> None:
    _repair_historical_schema()
    _install_activation_redemption_guard(verify_expiry=True)
    _install_publication_source_guard(verify_payload=True)
    _install_entitlement_chain_guard(verify_actor=True)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_renter_portal_publication_successor
            ON public.renter_portal_publication (
              account_id, tenancy_id, document_type, supersedes_publication_id
            )
         WHERE supersedes_publication_id IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS public.uq_renter_portal_publication_successor")
    _install_entitlement_chain_guard(verify_actor=False)
    _install_publication_source_guard(verify_payload=False)
    _install_activation_redemption_guard(verify_expiry=False)
