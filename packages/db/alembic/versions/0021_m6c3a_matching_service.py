"""M6-C3a persistence: ranked proposals, reversal snapshots and booking evidence."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SEARCH_PATH = "pg_catalog, public, pg_temp"

_SNAPSHOT_FIELDS = (
    "open_costs_cents",
    "open_interest_cents",
    "open_principal_cents",
    "open_cents",
    "status",
)


def upgrade() -> None:
    # One transaction is one immutable proposal run. Existing evidence predates the
    # explicit rank, so order it by the documented Review signals and stable row id.
    # `match_proposal` is append-only; remove only its rewrite trigger for this bounded
    # migration backfill and restore it before the new invariant becomes visible.
    op.add_column("match_proposal", sa.Column("rank", sa.Integer(), nullable=True))
    op.execute("DROP TRIGGER match_proposal_append_only ON public.match_proposal")
    op.execute("""
        WITH ranked AS (
          SELECT id,
                 row_number() OVER (
                   PARTITION BY bank_transaction_id
                   ORDER BY signal_amount DESC,
                            signal_code_or_surname DESC,
                            signal_e2e DESC,
                            signal_period DESC,
                            confidence DESC,
                            created_at ASC,
                            id ASC
                 ) AS proposal_rank
          FROM public.match_proposal
        )
        UPDATE public.match_proposal AS proposal
           SET rank = ranked.proposal_rank
          FROM ranked
         WHERE proposal.id = ranked.id
    """)
    # Future triggers cannot validate evidence already present at migration time. Stop
    # on a malformed account-scoped legacy run; never normalize differing evidence.
    op.execute("""
        DO $legacy_proposal_validation$
        DECLARE malformed_run record;
        BEGIN
          SELECT account_id, bank_transaction_id INTO malformed_run
            FROM public.match_proposal
           GROUP BY account_id, bank_transaction_id
          HAVING min(rank) <> 1
              OR max(rank) <> count(*)
              OR count(DISTINCT rank) <> count(*)
              OR count(DISTINCT decision) <> 1
              OR count(DISTINCT reason_de) <> 1
              OR count(DISTINCT convention_version) <> 1
           LIMIT 1;
          IF FOUND THEN
            RAISE EXCEPTION
              'legacy proposal run is malformed: account %, transaction %',
              malformed_run.account_id, malformed_run.bank_transaction_id
              USING ERRCODE = '23514';
          END IF;
        END
        $legacy_proposal_validation$;
    """)
    op.execute(
        "CREATE TRIGGER match_proposal_append_only BEFORE UPDATE OR DELETE "
        "ON public.match_proposal FOR EACH ROW "
        "EXECUTE FUNCTION public.prevent_m6c2_evidence_rewrite()"
    )
    op.alter_column("match_proposal", "rank", nullable=False)
    op.create_check_constraint("ck_match_proposal_rank_positive", "match_proposal", "rank > 0")
    op.create_index(
        "uq_match_proposal_transaction_rank",
        "match_proposal",
        ["bank_transaction_id", "rank"],
        unique=True,
    )

    # A proposal run is one INSERT statement. Locking the transaction row closes the
    # concurrent two-first-writers race; excluding the transition rows distinguishes
    # the initial batch from any later attempt to append immutable evidence.
    op.execute(f"""
        CREATE FUNCTION public.seal_match_proposal_run_m6c3a() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        DECLARE proposal_run record;
        BEGIN
          FOR proposal_run IN
            SELECT DISTINCT inserted.account_id, inserted.bank_transaction_id
              FROM inserted_proposals AS inserted
             ORDER BY inserted.account_id, inserted.bank_transaction_id
          LOOP
            PERFORM 1
              FROM public.bank_transaction AS bank_tx
             WHERE bank_tx.id = proposal_run.bank_transaction_id
               AND bank_tx.account_id = proposal_run.account_id
             FOR UPDATE;
            IF NOT FOUND THEN
              RAISE EXCEPTION 'proposal run names no transaction in its own account'
                USING ERRCODE = '23514';
            END IF;
            IF EXISTS (
              SELECT 1
                FROM public.match_proposal AS proposal
               WHERE proposal.account_id = proposal_run.account_id
                 AND proposal.bank_transaction_id = proposal_run.bank_transaction_id
                 AND NOT EXISTS (
                   SELECT 1 FROM inserted_proposals AS inserted
                    WHERE inserted.id = proposal.id
                 )
            ) THEN
              RAISE EXCEPTION 'a transaction already has its immutable proposal run'
                USING ERRCODE = '23514';
            END IF;
          END LOOP;
          RETURN NULL;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER match_proposal_run_seal AFTER INSERT ON public.match_proposal "
        "REFERENCING NEW TABLE AS inserted_proposals FOR EACH STATEMENT "
        "EXECUTE FUNCTION public.seal_match_proposal_run_m6c3a()"
    )
    op.execute(f"""
        CREATE FUNCTION public.validate_match_proposal_run_m6c3a() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        DECLARE
          proposal_count bigint;
          distinct_ranks bigint;
          minimum_rank integer;
          maximum_rank integer;
          decisions bigint;
          reasons bigint;
          versions bigint;
        BEGIN
          SELECT count(*), count(DISTINCT proposal.rank), min(proposal.rank), max(proposal.rank),
                 count(DISTINCT proposal.decision), count(DISTINCT proposal.reason_de),
                 count(DISTINCT proposal.convention_version)
            INTO proposal_count, distinct_ranks, minimum_rank, maximum_rank,
                 decisions, reasons, versions
            FROM public.match_proposal AS proposal
           WHERE proposal.account_id = NEW.account_id
             AND proposal.bank_transaction_id = NEW.bank_transaction_id;
          IF minimum_rank <> 1 OR maximum_rank <> proposal_count
             OR distinct_ranks <> proposal_count THEN
            RAISE EXCEPTION 'proposal run ranks must be contiguous from 1 through its row count'
              USING ERRCODE = '23514';
          END IF;
          IF decisions <> 1 OR reasons <> 1 OR versions <> 1 THEN
            RAISE EXCEPTION
              'one proposal run must share its decision, reason and convention version'
              USING ERRCODE = '23514';
          END IF;
          RETURN NULL;
        END; $$
    """)
    op.execute(
        "CREATE CONSTRAINT TRIGGER match_proposal_run_consistency "
        "AFTER INSERT ON public.match_proposal DEFERRABLE INITIALLY DEFERRED "
        "FOR EACH ROW EXECUTE FUNCTION public.validate_match_proposal_run_m6c3a()"
    )

    # IBAN learning uses the exact confirmation instant. Convert legacy DATE values to
    # midnight UTC so their prior calendar meaning is stable across session time zones.
    op.alter_column(
        "iban_history",
        "valid_from",
        existing_type=sa.Date(),
        type_=sa.DateTime(timezone=True),
        postgresql_using="valid_from::timestamp AT TIME ZONE 'UTC'",
        existing_nullable=False,
    )
    op.alter_column(
        "iban_history",
        "valid_to",
        existing_type=sa.Date(),
        type_=sa.DateTime(timezone=True),
        postgresql_using="valid_to::timestamp AT TIME ZONE 'UTC'",
        existing_nullable=True,
    )

    # Old allocations remain valid with no reconstruction evidence. New service rows
    # carry a complete before/after projection pair; a half-snapshot is never useful
    # evidence and must not become immutable ledger history.
    for side in ("before", "after"):
        for field in _SNAPSHOT_FIELDS:
            if field == "status":
                op.add_column(
                    "payment_allocation",
                    sa.Column(f"{side}_{field}", sa.String(), nullable=True),
                )
            else:
                op.add_column(
                    "payment_allocation",
                    sa.Column(f"{side}_{field}", sa.BigInteger(), nullable=True),
                )

    snapshot_columns = [
        f"{side}_{field}" for side in ("before", "after") for field in _SNAPSHOT_FIELDS
    ]
    all_null = " AND ".join(f"{column} IS NULL" for column in snapshot_columns)
    all_present = " AND ".join(f"{column} IS NOT NULL" for column in snapshot_columns)
    op.create_check_constraint(
        "ck_payment_allocation_projection_snapshots_complete",
        "payment_allocation",
        f"(({all_null}) OR ({all_present}))",
    )
    op.create_check_constraint(
        "ck_payment_allocation_projection_snapshot_status",
        "payment_allocation",
        "before_status IS NULL OR ("
        "before_status IN ('open', 'partial', 'settled')"
        " AND after_status IN ('open', 'partial', 'settled')"
        " AND after_status = resulting_status)",
    )

    # A rent principal is classified into the four named rent components. A Page-01
    # Nachzahlung has no source-backed split, so its neutral principal remains whole
    # and every named rent/advance component stays zero. Parent lookup is AFTER RLS.
    op.drop_constraint("ck_payment_allocation_components_sum", "payment_allocation", type_="check")
    op.execute(f"""
        CREATE FUNCTION public.enforce_payment_allocation_components_m6c3a() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        DECLARE receivable_category text;
        BEGIN
          SELECT receivable.category INTO receivable_category
            FROM public.receivable AS receivable
           WHERE receivable.id = NEW.receivable_id
             AND receivable.account_id = NEW.account_id;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'payment allocation names no receivable in its own account'
              USING ERRCODE = '23514';
          END IF;
          IF receivable_category = 'rent' THEN
            IF NEW.base_rent_cents + NEW.nk_advance_cents
               + NEW.heating_advance_cents + NEW.garage_cents <> NEW.principal_cents THEN
              RAISE EXCEPTION 'rent allocation components must sum to principal cents'
                USING ERRCODE = '23514';
            END IF;
          ELSIF receivable_category = 'nk_nachzahlung' THEN
            IF NEW.base_rent_cents <> 0 OR NEW.nk_advance_cents <> 0
               OR NEW.heating_advance_cents <> 0 OR NEW.garage_cents <> 0 THEN
              RAISE EXCEPTION 'Nachzahlung carries no rent or advance component split'
                USING ERRCODE = '23514';
            END IF;
          ELSE
            RAISE EXCEPTION 'payment allocation has an unsupported receivable category'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER payment_allocation_components AFTER INSERT OR UPDATE "
        "ON public.payment_allocation FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_payment_allocation_components_m6c3a()"
    )

    # Decisions are evidence about the run's selected candidate, never about an
    # arbitrary lower rank or an Auto/Unmatched row. AFTER timing exposes RLS first.
    op.execute(f"""
        CREATE FUNCTION public.enforce_match_confirmation_target_m6c3a() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        DECLARE proposal_rank integer; proposal_decision text;
        BEGIN
          SELECT proposal.rank, proposal.decision INTO proposal_rank, proposal_decision
            FROM public.match_proposal AS proposal
           WHERE proposal.id = NEW.match_proposal_id
             AND proposal.account_id = NEW.account_id;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'confirmation names no proposal in its own account'
              USING ERRCODE = '23514';
          END IF;
          IF NEW.outcome NOT IN ('CONFIRMED', 'REJECTED', 'DUPLICATE') THEN
            RAISE EXCEPTION 'confirmation outcome is invalid' USING ERRCODE = '23514';
          END IF;
          IF proposal_rank <> 1 OR proposal_decision <> 'NEEDS_REVIEW' THEN
            RAISE EXCEPTION 'only the rank-1 NEEDS_REVIEW proposal may be decided'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER match_confirmation_target AFTER INSERT OR UPDATE "
        "ON public.match_confirmation FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_match_confirmation_target_m6c3a()"
    )

    # PAYMENT entries now require positive matching evidence. This is deliberately an
    # AFTER trigger: PostgreSQL applies the table's RLS WITH CHECK before an AFTER ROW
    # parent lookup, so a cross-account insert is refused by the isolation boundary
    # rather than having that refusal masked by an invisible proposal.
    op.execute("DROP TRIGGER payment_ledger_entry_evidence ON public.payment_ledger_entry")
    op.execute("DROP FUNCTION public.enforce_ledger_entry_evidence()")
    op.execute(f"""
        CREATE FUNCTION public.enforce_ledger_entry_evidence_m6c3a() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        DECLARE
          proposal_tx text;
          proposal_decision text;
          proposal_rank integer;
          original_kind text;
          original_cents bigint;
          confirmed boolean;
        BEGIN
          IF NEW.reverses_entry_id IS NOT NULL THEN
            SELECT original.kind, original.amount_cents
              INTO original_kind, original_cents
              FROM public.payment_ledger_entry AS original
             WHERE original.id = NEW.reverses_entry_id
               AND original.account_id = NEW.account_id;
            IF NOT FOUND THEN
              RAISE EXCEPTION 'ledger entry reverses no entry in its own account'
                USING ERRCODE = '23514';
            END IF;
            IF original_kind <> 'PAYMENT' THEN
              RAISE EXCEPTION
                'only a PAYMENT may be reversed; a chain of reversals has no defined restore target'
                USING ERRCODE = '23514';
            END IF;
            IF NEW.amount_cents <> -original_cents THEN
              RAISE EXCEPTION 'a reversal must negate the entry it reverses exactly'
                USING ERRCODE = '23514';
            END IF;
          END IF;

          IF NEW.match_proposal_id IS NOT NULL THEN
            SELECT proposal.bank_transaction_id, proposal.decision, proposal.rank
              INTO proposal_tx, proposal_decision, proposal_rank
              FROM public.match_proposal AS proposal
             WHERE proposal.id = NEW.match_proposal_id
               AND proposal.account_id = NEW.account_id;
            IF NOT FOUND THEN
              RAISE EXCEPTION 'ledger entry cites no proposal in its own account'
                USING ERRCODE = '23514';
            END IF;
            IF proposal_tx IS DISTINCT FROM NEW.bank_transaction_id THEN
              RAISE EXCEPTION 'ledger entry cites a proposal for a different transaction'
                USING ERRCODE = '23514';
            END IF;
          END IF;

          IF NEW.kind = 'PAYMENT' THEN
            IF NEW.match_proposal_id IS NULL THEN
              RAISE EXCEPTION 'a PAYMENT requires AUTO_MATCH or confirmed review evidence'
                USING ERRCODE = '23514';
            END IF;
            IF proposal_rank <> 1 THEN
              RAISE EXCEPTION 'a PAYMENT may cite only the rank-1 proposal'
                USING ERRCODE = '23514';
            END IF;
            IF proposal_decision = 'NEEDS_REVIEW' THEN
              SELECT EXISTS (
                SELECT 1
                  FROM public.match_confirmation AS confirmation
                 WHERE confirmation.match_proposal_id = NEW.match_proposal_id
                   AND confirmation.account_id = NEW.account_id
                   AND confirmation.outcome = 'CONFIRMED'
              ) INTO confirmed;
            ELSE
              confirmed := false;
            END IF;
            IF proposal_decision <> 'AUTO_MATCH'
               AND NOT (proposal_decision = 'NEEDS_REVIEW' AND confirmed) THEN
              RAISE EXCEPTION 'a PAYMENT requires AUTO_MATCH or confirmed review evidence'
                USING ERRCODE = '23514';
            END IF;
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER payment_ledger_evidence AFTER INSERT OR UPDATE "
        "ON public.payment_ledger_entry FOR EACH ROW "
        "EXECUTE FUNCTION public.enforce_ledger_entry_evidence_m6c3a()"
    )

    # Reconciliation is deferred so the service can append the immutable ledger row
    # before its allocation rows. Both entry and allocation inserts schedule the same
    # final check, closing the loophole where allocations were appended later.
    op.create_check_constraint(
        "ck_payment_ledger_reversal_credit_zero",
        "payment_ledger_entry",
        "kind <> 'REVERSAL' OR credit_cents = 0",
    )
    op.execute(f"""
        CREATE FUNCTION public.enforce_payment_reconciliation_m6c3a() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        DECLARE
          target_entry_id text;
          target_account_id text;
          entry_kind text;
          entry_amount bigint;
          entry_credit bigint;
          original_entry_id text;
          assigned bigint;
          original_assigned bigint;
        BEGIN
          IF TG_TABLE_NAME = 'payment_ledger_entry' THEN
            target_entry_id := NEW.id;
            target_account_id := NEW.account_id;
          ELSE
            target_entry_id := NEW.ledger_entry_id;
            target_account_id := NEW.account_id;
          END IF;

          SELECT entry.kind, entry.amount_cents, entry.credit_cents, entry.reverses_entry_id
            INTO entry_kind, entry_amount, entry_credit, original_entry_id
            FROM public.payment_ledger_entry AS entry
           WHERE entry.id = target_entry_id
             AND entry.account_id = target_account_id;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'payment reconciliation names no ledger entry in its own account'
              USING ERRCODE = '23514';
          END IF;

          SELECT coalesce(sum(allocation.costs_cents
                              + allocation.interest_cents
                              + allocation.principal_cents), 0)
            INTO assigned
            FROM public.payment_allocation AS allocation
           WHERE allocation.ledger_entry_id = target_entry_id
             AND allocation.account_id = target_account_id;

          IF entry_kind = 'PAYMENT' THEN
            IF entry_credit IS DISTINCT FROM entry_amount - assigned THEN
              RAISE EXCEPTION
                'PAYMENT credit must equal its amount minus assigned cents at transaction end'
                USING ERRCODE = '23514';
            END IF;
          ELSE
            IF entry_credit <> 0 THEN
              RAISE EXCEPTION 'REVERSAL credit must be zero' USING ERRCODE = '23514';
            END IF;
            SELECT coalesce(sum(allocation.costs_cents
                                + allocation.interest_cents
                                + allocation.principal_cents), 0)
              INTO original_assigned
              FROM public.payment_allocation AS allocation
             WHERE allocation.ledger_entry_id = original_entry_id
               AND allocation.account_id = target_account_id;
            IF assigned IS DISTINCT FROM -original_assigned THEN
              RAISE EXCEPTION
                'REVERSAL allocations must negate the original PAYMENT allocations exactly'
                USING ERRCODE = '23514';
            END IF;
          END IF;
          RETURN NULL;
        END; $$
    """)
    op.execute(
        "CREATE CONSTRAINT TRIGGER payment_ledger_reconciliation "
        "AFTER INSERT ON public.payment_ledger_entry DEFERRABLE INITIALLY DEFERRED "
        "FOR EACH ROW EXECUTE FUNCTION public.enforce_payment_reconciliation_m6c3a()"
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER payment_allocation_reconciliation "
        "AFTER INSERT ON public.payment_allocation DEFERRABLE INITIALLY DEFERRED "
        "FOR EACH ROW EXECUTE FUNCTION public.enforce_payment_reconciliation_m6c3a()"
    )


def downgrade() -> None:
    raise RuntimeError("M6-C3a matching evidence is intentionally not downgraded")
