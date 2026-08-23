"""M6-C2 money invariants found by the boundary audit: parents, caps, reversals, immutability.

`0017` got account isolation right — RLS is ENABLEd, FORCEd and policied on all nine
tables, and every reference is a composite `(id, account_id)` edge. What it did not
constrain is everything *inside* one account: which parent a row may name, how much a
payment may settle, what a reversal has to look like, and which tables may be rewritten
at all.

M6-A already enforces the equivalent rules one ledger earlier
(`enforce_advance_allocation_cap`, `enforce_advance_payment_single_reversal`,
`enforce_statement_tenancy_scope`). This is the same set for the payment ledger.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# docs/15 § 4: "Confirmation records the actor and time; it does not rewrite the
# original proposal." § 5.3: the ledger is append-only. § 3.1 calls the bank
# transaction the immutable normalized provider movement, and CLAUDE.md § 3.2 names
# IBAN history in the immutable/versioned list. All of those were docstrings only.
_NEWLY_APPEND_ONLY = ("bank_transaction", "match_proposal", "match_confirmation")


def upgrade() -> None:
    # ── 1. A row may not name a parent that contradicts its siblings ──────────────
    # docs/15 § 6: "A match never moves money between renters. One confirmed
    # transaction belongs to exactly one renter." The composite FKs stop cross-account
    # links; nothing stopped a same-account link to the wrong parent, so renter 1's
    # cash could settle renter 2's rent.
    op.execute("""
        CREATE FUNCTION enforce_receivable_tenancy_party() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM tenancy_party p
            WHERE p.tenancy_id = NEW.tenancy_id
              AND p.renter_id = NEW.renter_id
              AND p.account_id = NEW.account_id
          ) THEN
            RAISE EXCEPTION 'receivable renter is not a party to its tenancy'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER receivable_tenancy_party BEFORE INSERT OR UPDATE ON receivable "
        "FOR EACH ROW EXECUTE FUNCTION enforce_receivable_tenancy_party()"
    )

    op.execute("""
        CREATE FUNCTION enforce_match_proposal_renter() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE debt_renter text;
        BEGIN
          IF NEW.receivable_id IS NULL OR NEW.renter_id IS NULL THEN RETURN NEW; END IF;
          SELECT r.renter_id INTO debt_renter FROM receivable r WHERE r.id = NEW.receivable_id;
          IF debt_renter IS DISTINCT FROM NEW.renter_id THEN
            RAISE EXCEPTION 'match proposal names a renter other than the debt''s renter'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER match_proposal_renter BEFORE INSERT OR UPDATE ON match_proposal "
        "FOR EACH ROW EXECUTE FUNCTION enforce_match_proposal_renter()"
    )

    op.execute("""
        CREATE FUNCTION enforce_ledger_entry_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE proposal_tx text;
        BEGIN
          IF NEW.match_proposal_id IS NULL THEN RETURN NEW; END IF;
          SELECT p.bank_transaction_id INTO proposal_tx
            FROM match_proposal p WHERE p.id = NEW.match_proposal_id;
          IF proposal_tx IS DISTINCT FROM NEW.bank_transaction_id THEN
            RAISE EXCEPTION 'ledger entry cites a proposal for a different transaction'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER payment_ledger_entry_evidence BEFORE INSERT OR UPDATE "
        "ON payment_ledger_entry FOR EACH ROW EXECUTE FUNCTION enforce_ledger_entry_evidence()"
    )

    # ── 2. An allocation may not settle money that never arrived ──────────────────
    # Mirrors enforce_advance_allocation_cap. Without it a 1.080,00 € payment could
    # settle 5.000,00 €, and a negative component cancelled inside the sum check —
    # which then fed Page 01's annual actual-advance total a negative advance.
    op.create_check_constraint(
        "ck_payment_allocation_no_negative_components",
        "payment_allocation",
        "costs_cents >= 0 AND interest_cents >= 0 AND principal_cents >= 0"
        " AND base_rent_cents >= 0 AND nk_advance_cents >= 0"
        " AND heating_advance_cents >= 0 AND garage_cents >= 0",
    )
    op.create_unique_constraint(
        "uq_payment_allocation_entry_receivable",
        "payment_allocation",
        ["ledger_entry_id", "receivable_id"],
    )
    op.execute("""
        CREATE FUNCTION enforce_payment_allocation_cap() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE entry_cents bigint; allocated bigint;
        BEGIN
          SELECT abs(e.amount_cents) INTO entry_cents
            FROM payment_ledger_entry e WHERE e.id = NEW.ledger_entry_id;
          SELECT coalesce(sum(a.costs_cents + a.interest_cents + a.principal_cents), 0)
            INTO allocated FROM payment_allocation a
            WHERE a.ledger_entry_id = NEW.ledger_entry_id AND a.id <> NEW.id;
          IF allocated + NEW.costs_cents + NEW.interest_cents + NEW.principal_cents
             > entry_cents THEN
            RAISE EXCEPTION 'payment allocation exceeds the cents its ledger entry carried'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER payment_allocation_cap BEFORE INSERT ON payment_allocation "
        "FOR EACH ROW EXECUTE FUNCTION enforce_payment_allocation_cap()"
    )

    # ── 3. A reversal has a shape ─────────────────────────────────────────────────
    # docs/15 § 5.3 and F06: the ledger nets to zero and the debt reopens at exactly
    # what it was. A positive REVERSAL, one naming no original, or two reversals of
    # one payment all break that — permanently, because the table is append-only.
    op.create_check_constraint(
        "ck_payment_ledger_reversal_shape",
        "payment_ledger_entry",
        "(kind = 'REVERSAL') = (reverses_entry_id IS NOT NULL)"
        " AND (kind <> 'REVERSAL' OR amount_cents < 0)"
        " AND (kind <> 'PAYMENT' OR amount_cents >= 0)",
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_payment_ledger_one_reversal ON payment_ledger_entry "
        "(reverses_entry_id) WHERE reverses_entry_id IS NOT NULL"
    )

    # ── 4. A learned IBAN exists only because it was confirmed ────────────────────
    # docs/15 § 3.3 and F09. Without this the +60 unique-IBAN signal could be created
    # by anything able to insert, and flipping one row redirects a renter's next
    # payment onto someone else's debt with no review step.
    op.create_check_constraint(
        "ck_iban_history_requires_confirmation",
        "iban_history",
        "confirmed_match_id IS NOT NULL AND confirmed_by IS NOT NULL",
    )
    op.create_foreign_key(
        "iban_history_confirmed_match_id_fkey",
        "iban_history",
        "match_confirmation",
        ["confirmed_match_id", "account_id"],
        ["id", "account_id"],
    )
    # § 3.3: "the IBAN must have exactly one active renter mapping". That was decided
    # by a query with no uniqueness behind it.
    op.execute(
        "CREATE UNIQUE INDEX uq_iban_history_active ON iban_history "
        "(account_id, normalized_iban) WHERE valid_to IS NULL"
    )
    # Versioned, not frozen: the one legitimate change is closing an open period.
    op.execute("""
        CREATE FUNCTION enforce_iban_history_versioning() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'iban history is append-only' USING ERRCODE = '23514';
          END IF;
          IF OLD.valid_to IS NULL AND NEW.valid_to IS NOT NULL
             AND (to_jsonb(NEW) - 'valid_to') IS NOT DISTINCT FROM (to_jsonb(OLD) - 'valid_to')
          THEN RETURN NEW; END IF;
          RAISE EXCEPTION 'iban history is append-only; only closing an open period is permitted'
            USING ERRCODE = '23514';
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER iban_history_versioning BEFORE UPDATE OR DELETE ON iban_history "
        "FOR EACH ROW EXECUTE FUNCTION enforce_iban_history_versioning()"
    )

    # ── 5. Evidence that was documented immutable now is ──────────────────────────
    # § 147 AO: the provider fact and the recorded reason a payment was auto-assigned
    # must be re-derivable years later. Both were freely mutable.
    op.execute("""
        CREATE FUNCTION prevent_m6c2_evidence_rewrite() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'matching evidence is append-only' USING ERRCODE = '23514';
        END; $$
    """)
    for table in _NEWLY_APPEND_ONLY:
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION prevent_m6c2_evidence_rewrite()"
        )
    # One proposal confirmed twice is one payment booked twice once M6-C3 drives
    # ledger entries off confirmations.
    op.create_unique_constraint(
        "uq_match_confirmation_proposal", "match_confirmation", ["account_id", "match_proposal_id"]
    )

    # ── 6. A receivable's § 367 projection columns must agree with each other ─────
    # § 5.1 step 3 walks costs, then interest, then principal. Unconstrained, the
    # settlement engine and the arrears guard read different totals from one row.
    op.create_check_constraint(
        "ck_receivable_open_components",
        "receivable",
        "open_costs_cents >= 0 AND open_interest_cents >= 0 AND open_principal_cents >= 0"
        " AND open_principal_cents <= open_cents",
    )
    op.create_check_constraint(
        "ck_receivable_settled_has_nothing_open",
        "receivable",
        "(status = 'settled')"
        " = (open_cents = 0 AND open_costs_cents = 0 AND open_interest_cents = 0)",
    )
    # The handoff's "already created" guard was a SELECT then an INSERT with nothing
    # behind it: two concurrent requests both passed and both inserted, doubling a
    # renter's debt.
    op.execute(
        "CREATE UNIQUE INDEX uq_receivable_source ON receivable "
        "(account_id, source_type, source_id, tenancy_id) WHERE source_id IS NOT NULL"
    )


def downgrade() -> None:
    raise RuntimeError("M6-C2 money invariants are intentionally not downgraded")
