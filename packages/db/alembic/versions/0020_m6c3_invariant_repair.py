"""M6-C3-0 invariant repair: the fourth parent trigger, and the four rules 0019 got wrong.

The boundary audit of M6-C2 found two separate defects in `0019`.

*Missing.* `docs/02` § 6 documents **four** parent-scope triggers; `0019` created three.
The fourth — the one that guards the row which actually moves the money — was never
written, so renter one's cash could settle renter two's debt through
`payment_allocation` even though every proposal and receivable above it was correct.

*Wrong.* Three constraints `0019` did create contradict the matching engine's own
fixture-verified output or `docs/15`:

- `ck_payment_allocation_no_negative_components` rejects
  `reversal.py:112-123`, which negates every component of the allocation it compensates.
  A CHECK cannot see the parent entry's `kind`, so the sign rule cannot live in one.
- `enforce_payment_allocation_cap` compared against `abs(amount_cents)`, which grants a
  -1.080,00 € REVERSAL a +1.080,00 € budget — and left `entry_cents` NULL-able, so when
  the entry was not found `allocated + x > NULL` evaluated to NULL, the `IF` was not
  taken and the trigger returned NEW. It failed **open**.
- `uq_iban_history_active (account_id, normalized_iban)` makes `docs/15` § 3.3 `F07` —
  two active renters sharing one IBAN, each scored ambiguous and routed to Review —
  unrepresentable. Two spouses on one joint account are the ordinary case, not an abuse.
- `ck_receivable_open_components` only asserted `open_principal_cents <= open_cents`,
  so the settlement engine and the arrears guard could read two different open
  principals from one row.

Everything here is a repair of `0019`. No row in the live database violates any of it
(verified 23.08.2026), so it applies in place.

---

**Second audit re-run, 23.08.2026.** A re-audit of `0020` *as first written* found four
more defects, recorded in `docs/02` § 6 "Closed on `0020`" as H1, H2, M3-a and M5. This
migration is uncommitted and applied only to the local database, so they are repaired
here rather than in an `0021`.

- **H1** — `enforce_payment_allocation_renter` resolved the entry's renter with
  `IF match_proposal_id … ELSIF reverses_entry_id`, so a REVERSAL's *own* proposal
  shadowed the reversed payment's renter and renter 1's returned cash could settle
  renter 2's debt. `docs/15` § 5.3 makes the return a distinct provider movement that
  legitimately carries a proposal of its own, and `ck_payment_ledger_reversal_shape`
  does not forbid one — so the repair is the resolution rule, never a ban on the
  column: the reversed entry decides, and a proposal of the reversal's own must agree.
- **H2** — every plpgsql trigger function in the database had no `search_path` and
  looked its parents up unqualified. `lokara_app` holds TEMP, so a temp table named
  `receivable` or `payment_ledger_entry` answered the trigger's SELECT while the
  foreign keys and RLS policies still bound `public`; the row that landed was the
  forged one.
- **M3-a** — `enforce_iban_history_confirmation` checked the renter and the `CONFIRMED`
  outcome but never tied `learned_from_transaction_id` to the confirmed proposal's
  `bank_transaction_id`, so a learned IBAN could cite no movement at all, or one nobody
  reviewed (`docs/15` § 3.3).
- **M5** — the parent-scope `BEFORE ROW` triggers on `payment_allocation` and
  `iban_history` ran *before* `WCO_RLS_INSERT_CHECK` and refused every cross-account
  write with a `CheckViolation`, masking the RLS policy so nothing could ever exercise
  its `WITH CHECK`. They are re-timed to `AFTER`; they still fail closed.

**This migration deliberately hardens functions created by earlier migrations.** H2 is
not a property of one slice: `pg_temp` shadowing neutralises *any* unqualified lookup,
and `0009`, `0010`–`0012`, `0015`, `0016` and `0017` all created plpgsql trigger
functions with the same exposure. Fixing only the nine this slice owns would leave
twelve guards — the M6-A advance caps, the M6-B statement finalization scope checks and
three append-only guards — defeatable by the application role. Emir's decision was to
fix all 21. This migration owns the body of six of them and gives those both the
setting and schema-qualified lookups; the other fifteen are hardened with
`ALTER FUNCTION … SET search_path` and their bodies are **not** reproduced here, because
a migration that re-states another migration's logic silently forks it.

`SET search_path = pg_catalog, public, pg_temp` lists `pg_temp` **last on purpose**. If
`pg_temp` is not named in `search_path` at all, PostgreSQL searches it *first*, ahead of
`pg_catalog`, so `SET search_path = pg_catalog, public` would do nothing about H2
(verified on PostgreSQL 16.14). Naming it last is the pattern the PostgreSQL manual
prescribes for exactly this attack.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# H2. See the module docstring: `pg_temp` last, never omitted.
_SEARCH_PATH = "pg_catalog, public, pg_temp"

# The plpgsql trigger functions whose bodies this migration does not own. The six it
# does own are created or replaced below with schema-qualified lookups and the same
# setting inline; these fifteen only receive the setting, so no earlier migration's
# logic is forked into this file. Six plus fifteen is every plpgsql function in the
# schema.
_HARDENED_ELSEWHERE = (
    # 0009 and 0010–0012 — Slice-B integrity guards and the Page 02 catalogue.
    "prevent_fiktivbelegung_rewrite",
    "prevent_confirmed_cost_classification_rewrite",
    # 0015 — M6-A temporal advances.
    "enforce_advance_allocation_cap",
    "enforce_advance_payment_period_successor",
    "enforce_advance_payment_single_reversal",
    "enforce_advance_reconciliation_allocation_tenancy",
    "prevent_advance_rewrite",
    # 0016 — M6-B finalized archives.
    "enforce_statement_archive_hash",
    "enforce_statement_finalization",
    "enforce_statement_predecessor_scope",
    "enforce_statement_tenancy_scope",
    "prevent_m6b_rewrite",
    # 0017 and 0019 — M6-C2 append-only guards and the IBAN versioning rule. Their
    # bodies contain no lookup to shadow, but a `search_path` they do not control is
    # still a dependency they should not have.
    "prevent_payment_ledger_rewrite",
    "prevent_m6c2_evidence_rewrite",
    "enforce_iban_history_versioning",
)


def upgrade() -> None:
    # ── H2. No trigger may be answered by a table the caller invented ─────────────
    # `lokara_app` holds TEMP, PostgreSQL resolves `pg_temp` before `public` for
    # relation names, and not one plpgsql function in the schema pinned its
    # `search_path`. A temp `receivable`, `payment_ledger_entry`, `match_proposal`,
    # `match_confirmation` or `tenancy_party` therefore answered the trigger's SELECT
    # while the composite foreign keys and the RLS policies still bound the real table
    # — so the trigger approved a fabricated parent and the row that landed was the
    # forged one. `CLAUDE.md` § 3.3 makes isolation a property of the database, not of
    # the caller's search path.
    #
    # Fifteen functions get only the setting (see `_HARDENED_ELSEWHERE`). The six this
    # migration writes get the setting *and* schema-qualified lookups, so they are
    # correct even if a later migration alters the setting away.
    for function_name in _HARDENED_ELSEWHERE:
        op.execute(f"ALTER FUNCTION {function_name}() SET search_path = {_SEARCH_PATH}")

    # `0019`'s first parent-scope trigger. Only the lookup changes; the rule is
    # unaltered, and the trigger keeps its `BEFORE` timing — `receivable` is not one of
    # the two tables M5 re-times, because in a foreign account's context this same
    # lookup is what refuses the row, which is defence in depth working.
    op.execute(f"""
        CREATE OR REPLACE FUNCTION enforce_receivable_tenancy_party() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM public.tenancy_party p
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

    # ── S2. A proposal names both a debt and its renter, or neither ───────────────
    # `0019:60` early-returned when *either* was NULL, which let a half-populated
    # proposal through unchecked. An UNMATCHED or DEDUPED proposal names neither
    # (`0017` makes both columns nullable for exactly that case); one that names a
    # receivable but no renter — or the reverse — is a defect, and `match_proposal` is
    # append-only, so it can never be corrected afterwards.
    #
    # S1: the lookup now carries `AND account_id = NEW.account_id`. The composite FKs
    # already stop a cross-account edge, but a trigger that decides who may be paid
    # should assert its own isolation rather than inherit it.
    op.execute(f"""
        CREATE OR REPLACE FUNCTION enforce_match_proposal_renter() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        DECLARE debt_renter text;
        BEGIN
          IF NEW.receivable_id IS NULL AND NEW.renter_id IS NULL THEN RETURN NEW; END IF;
          IF NEW.receivable_id IS NULL OR NEW.renter_id IS NULL THEN
            RAISE EXCEPTION 'match proposal names a receivable without its renter,'
              ' or a renter without its receivable' USING ERRCODE = '23514';
          END IF;
          SELECT r.renter_id INTO debt_renter FROM public.receivable r
            WHERE r.id = NEW.receivable_id AND r.account_id = NEW.account_id;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'match proposal names no receivable in its own account'
              USING ERRCODE = '23514';
          END IF;
          IF debt_renter IS DISTINCT FROM NEW.renter_id THEN
            RAISE EXCEPTION 'match proposal names a renter other than the debt''s renter'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)

    # ── C5. A reversal reverses a payment, exactly ────────────────────────────────
    # `0019`'s `ck_payment_ledger_reversal_shape` only asserts that a REVERSAL is
    # negative and names an original. It cannot read that original, so a -500,00 €
    # reversal of a 600,00 € payment passed, and so did a reversal of a reversal —
    # which has no defined restore target (`docs/15` § 5.3 restores the receivable to
    # what the *payment* left it at). The ledger is append-only; neither is correctable.
    #
    # Deliberately absent: any rule tying the two entries' `bank_transaction_id`
    # together. § 5.3 makes the return a *distinct* provider movement, resolved by E2E
    # or mandate reference. Requiring one shared transaction id would encode a fixture
    # shortcut and make the real shape unrepresentable.
    #
    # S1 again: both lookups are scoped by `NEW.account_id`, and both fail closed.
    op.execute(f"""
        CREATE OR REPLACE FUNCTION enforce_ledger_entry_evidence() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        DECLARE proposal_tx text; original_kind text; original_cents bigint;
        BEGIN
          IF NEW.reverses_entry_id IS NOT NULL THEN
            SELECT o.kind, o.amount_cents INTO original_kind, original_cents
              FROM public.payment_ledger_entry o
              WHERE o.id = NEW.reverses_entry_id AND o.account_id = NEW.account_id;
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
          IF NEW.match_proposal_id IS NULL THEN RETURN NEW; END IF;
          SELECT p.bank_transaction_id INTO proposal_tx
            FROM public.match_proposal p
            WHERE p.id = NEW.match_proposal_id AND p.account_id = NEW.account_id;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'ledger entry cites no proposal in its own account'
              USING ERRCODE = '23514';
          END IF;
          IF proposal_tx IS DISTINCT FROM NEW.bank_transaction_id THEN
            RAISE EXCEPTION 'ledger entry cites a proposal for a different transaction'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)

    # ── C1. The fourth parent trigger: an allocation belongs to one renter ────────
    # `docs/15` § 6: "A match never moves money between renters. One confirmed
    # transaction belongs to exactly one renter." `0019` enforced that a proposal names
    # its receivable's renter and that a receivable's renter is a party to its tenancy,
    # and then never looked at `payment_allocation` — the row that moves the cents.
    #
    # The entry's renter is reached two ways, and only two:
    #   * `reverses_entry_id` → the reversed entry's proposal. This is the normal
    #     reversal path, not an edge case: all 12 REVERSAL rows in the live database
    #     carry `match_proposal_id IS NULL` (boundary audit 23.08.2026), because the
    #     return movement usually has no proposal of its own.
    #   * otherwise `match_proposal_id` → `match_proposal.renter_id`.
    # An entry with neither has no resolvable renter, so C1 cannot be evaluated for it
    # and it may not carry an allocation at all. Fail closed, never open.
    #
    # H1: the two sources are **not** alternatives, and the first draft of this function
    # treated them as one — `IF match_proposal_id … ELSIF reverses_entry_id`. `docs/15`
    # § 5.3 makes the return a distinct provider movement resolved by E2E or mandate
    # reference, so it may legitimately carry a proposal of its own, and
    # `ck_payment_ledger_reversal_shape` does not forbid that column on a REVERSAL. The
    # `IF` branch therefore won and the reversed payment's renter was never consulted:
    # renter 1's returned cash settled renter 2's debt, which is precisely what § 6
    # forbids — "a match never moves money between renters".
    #
    # The repair is the resolution rule, not a ban. Banning `match_proposal_id` on a
    # REVERSAL would make the § 5.3 shape unrepresentable. § 5.3 says the reversal
    # restores what the *payment* left, so the reversed entry decides; a proposal the
    # reversal carries itself is admissible evidence only while it agrees.
    op.execute(f"""
        CREATE FUNCTION enforce_payment_allocation_renter() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        DECLARE
          entry_proposal text; original_entry text;
          own_renter text; entry_renter text; debt_renter text;
        BEGIN
          SELECT e.match_proposal_id, e.reverses_entry_id INTO entry_proposal, original_entry
            FROM public.payment_ledger_entry e
            WHERE e.id = NEW.ledger_entry_id AND e.account_id = NEW.account_id;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'payment allocation names no ledger entry in its own account'
              USING ERRCODE = '23514';
          END IF;

          IF entry_proposal IS NOT NULL THEN
            SELECT p.renter_id INTO own_renter FROM public.match_proposal p
              WHERE p.id = entry_proposal AND p.account_id = NEW.account_id;
          END IF;

          IF original_entry IS NOT NULL THEN
            SELECT p.renter_id INTO entry_renter
              FROM public.payment_ledger_entry o
              JOIN public.match_proposal p
                ON p.id = o.match_proposal_id AND p.account_id = NEW.account_id
              WHERE o.id = original_entry AND o.account_id = NEW.account_id;
            IF entry_renter IS NULL THEN
              RAISE EXCEPTION 'the entry this reversal reverses has no resolvable'
                ' renter, so the reversal may not carry an allocation'
                USING ERRCODE = '23514';
            END IF;
            IF entry_proposal IS NOT NULL AND own_renter IS DISTINCT FROM entry_renter THEN
              RAISE EXCEPTION 'a reversal''s own proposal names a renter other than the'
                ' reversed payment''s renter; the reversal restores what that payment'
                ' left' USING ERRCODE = '23514';
            END IF;
          ELSIF entry_proposal IS NOT NULL THEN
            entry_renter := own_renter;
          ELSE
            RAISE EXCEPTION 'ledger entry cites neither a proposal nor an original'
              ' entry, so its renter cannot be resolved and it may not carry an'
              ' allocation' USING ERRCODE = '23514';
          END IF;

          SELECT r.renter_id INTO debt_renter FROM public.receivable r
            WHERE r.id = NEW.receivable_id AND r.account_id = NEW.account_id;

          IF entry_renter IS NULL OR debt_renter IS NULL
             OR entry_renter IS DISTINCT FROM debt_renter THEN
            RAISE EXCEPTION 'payment allocation settles the debt of a renter other'
              ' than the ledger entry''s renter' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    # M5: `AFTER`, not `BEFORE`. See the timing note at the end of this migration.
    op.execute(
        "CREATE TRIGGER payment_allocation_renter AFTER INSERT OR UPDATE ON payment_allocation "
        "FOR EACH ROW EXECUTE FUNCTION enforce_payment_allocation_renter()"
    )

    # ── C6/C7. The cap is signed, kind-aware, and takes the lock ──────────────────
    # The sign rule cannot be a CHECK: a CHECK sees only its own row, and whether a
    # component may be negative depends on the parent entry's `kind`. `0019` guessed
    # "never negative" and thereby rejected `reversal.py:112-123`, its own engine's
    # fixture-verified output.
    op.drop_constraint(
        "ck_payment_allocation_no_negative_components", "payment_allocation", type_="check"
    )
    # One part of the sign rule does *not* need the parent, and belongs in a CHECK: an
    # allocation may not carry a positive component **and** a negative one. Whichever
    # `kind` the entry has, the trigger below already refuses such a row — a PAYMENT
    # allows no negative component, a REVERSAL allows no positive one — so this
    # constraint rejects nothing the trigger accepts. It is the kind-independent residue
    # of the rule, not a second rule.
    #
    # It is written as a CHECK rather than folded into the trigger for two reasons.
    # `0019`'s concern was a *cancelling* component: `+100.000 / -100.000` sums to the
    # `principal_cents` that `ck_payment_allocation_components_sum` demands, passes it,
    # and then feeds Page 01's annual actual-advance total a negative advance
    # (`docs/15` § 5.2). And the M5 re-timing below moves the trigger to `AFTER`, which
    # in PostgreSQL runs after unique-index insertion — so on a row that also collides
    # with `uq_payment_allocation_entry_receivable` the cancellation would be reported
    # as a duplicate key and the money defect would go unnamed. `ExecConstraints` runs
    # after the RLS `WITH CHECK` and before the index, which is exactly the slot this
    # rule needs.
    op.create_check_constraint(
        "ck_payment_allocation_no_negative_component_beside_a_positive",
        "payment_allocation",
        "NOT ("
        " (costs_cents > 0 OR interest_cents > 0 OR principal_cents > 0"
        "  OR base_rent_cents > 0 OR nk_advance_cents > 0"
        "  OR heating_advance_cents > 0 OR garage_cents > 0)"
        " AND"
        " (costs_cents < 0 OR interest_cents < 0 OR principal_cents < 0"
        "  OR base_rent_cents < 0 OR nk_advance_cents < 0"
        "  OR heating_advance_cents < 0 OR garage_cents < 0)"
        ")",
    )
    # `FOR UPDATE` is the C7 half. Without it two concurrent inserts against one entry
    # both read `allocated = 0` and both pass the cap.
    # `uq_payment_allocation_entry_receivable` only catches the same-receivable case,
    # and `docs/15` F04's overpayment is two receivables settled from one entry.
    op.execute(f"""
        CREATE OR REPLACE FUNCTION enforce_payment_allocation_cap() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        DECLARE entry_cents bigint; entry_kind text; allocated bigint; new_total bigint;
        BEGIN
          SELECT e.amount_cents, e.kind INTO entry_cents, entry_kind
            FROM public.payment_ledger_entry e
            WHERE e.id = NEW.ledger_entry_id AND e.account_id = NEW.account_id
            FOR UPDATE;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'payment allocation names no ledger entry in its own account'
              USING ERRCODE = '23514';
          END IF;

          SELECT coalesce(sum(a.costs_cents + a.interest_cents + a.principal_cents), 0)
            INTO allocated FROM public.payment_allocation a
            WHERE a.ledger_entry_id = NEW.ledger_entry_id
              AND a.account_id = NEW.account_id
              AND a.id <> NEW.id;
          new_total := allocated + NEW.costs_cents + NEW.interest_cents + NEW.principal_cents;

          IF entry_kind = 'PAYMENT' THEN
            IF NEW.costs_cents < 0 OR NEW.interest_cents < 0 OR NEW.principal_cents < 0
               OR NEW.base_rent_cents < 0 OR NEW.nk_advance_cents < 0
               OR NEW.heating_advance_cents < 0 OR NEW.garage_cents < 0 THEN
              RAISE EXCEPTION 'a PAYMENT allocation may not carry a negative'
                ' component; that is a reversal wearing a payment''s kind'
                USING ERRCODE = '23514';
            END IF;
            IF new_total > entry_cents THEN
              RAISE EXCEPTION 'payment allocation exceeds the cents its ledger entry carried'
                USING ERRCODE = '23514';
            END IF;
          ELSE
            IF NEW.costs_cents > 0 OR NEW.interest_cents > 0 OR NEW.principal_cents > 0
               OR NEW.base_rent_cents > 0 OR NEW.nk_advance_cents > 0
               OR NEW.heating_advance_cents > 0 OR NEW.garage_cents > 0 THEN
              RAISE EXCEPTION
                'a REVERSAL allocation may not carry a positive component; a reversal returns money'
                USING ERRCODE = '23514';
            END IF;
            IF new_total < entry_cents THEN
              RAISE EXCEPTION 'payment allocation gives back more cents than its'
                ' reversal entry carried' USING ERRCODE = '23514';
            END IF;
          END IF;
          RETURN NEW;
        END; $$
    """)
    # M5 again. `payment_allocation_cap` is the *other* BEFORE trigger on this table,
    # it fires ahead of `payment_allocation_renter` (triggers of one timing fire in
    # name order), and in a foreign account's RLS context its parent lookup finds
    # nothing and raises the identical "names no ledger entry in its own account".
    # Re-timing only the renter trigger would therefore leave the policy just as
    # masked. `FOR UPDATE` still serialises two concurrent inserts: an AFTER ROW
    # trigger runs inside the same statement, so the second insert blocks on the lock
    # and re-reads the sum once the first commits.
    op.execute("DROP TRIGGER payment_allocation_cap ON payment_allocation")
    op.execute(
        "CREATE TRIGGER payment_allocation_cap AFTER INSERT OR UPDATE ON payment_allocation "
        "FOR EACH ROW EXECUTE FUNCTION enforce_payment_allocation_cap()"
    )

    # ── C2. A learned IBAN needs *its own* confirmation ───────────────────────────
    # `0019` kept `ck_iban_history_requires_confirmation`, which asserts only that
    # *a* confirmation id is present. It never checks whose proposal that confirmation
    # confirmed, nor what the user decided — so a REJECTED review, or renter one's
    # confirmation, could mint the +60 unique-IBAN signal for renter two.
    # `docs/15` § 3.3: an IBAN is learned only after a user *confirms* a Review proposal.
    #
    # M3-a. § 3.3 stores `learned_from_transaction_id` beside `confirmed_match_id`, and
    # the IBAN is learned from a confirmed review of a *movement*. The first draft
    # checked the renter and the outcome and left the provenance column unconstrained,
    # so a learned IBAN could name no transaction at all, or one nobody reviewed — and
    # `iban_history` is append-only, so neither is correctable. The confirmed proposal
    # names exactly one `bank_transaction_id`; that is the movement, and no other.
    #
    # Deliberately absent: any comparison of `normalized_iban` with that transaction's
    # `counterpart_iban`. Normalization belongs to the adapter (`CLAUDE.md` § 6), no
    # source fixes a canonical form SQL could compare against, and that decision is not
    # made. Writing it here would invent the convention rather than transcribe it.
    op.execute(f"""
        CREATE FUNCTION enforce_iban_history_confirmation() RETURNS trigger
        LANGUAGE plpgsql SET search_path = {_SEARCH_PATH} AS $$
        DECLARE confirmed_outcome text; proposal_renter text; proposal_tx text;
        BEGIN
          SELECT c.outcome, p.renter_id, p.bank_transaction_id
            INTO confirmed_outcome, proposal_renter, proposal_tx
            FROM public.match_confirmation c
            JOIN public.match_proposal p
              ON p.id = c.match_proposal_id AND p.account_id = NEW.account_id
            WHERE c.id = NEW.confirmed_match_id AND c.account_id = NEW.account_id;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'iban history cites no confirmation in its own account'
              USING ERRCODE = '23514';
          END IF;
          IF confirmed_outcome <> 'CONFIRMED' THEN
            RAISE EXCEPTION 'an IBAN is learned only from a CONFIRMED review, not from %',
              confirmed_outcome USING ERRCODE = '23514';
          END IF;
          IF proposal_renter IS DISTINCT FROM NEW.renter_id THEN
            RAISE EXCEPTION
              'iban history claims an IBAN for a renter other than the confirmed proposal''s renter'
              USING ERRCODE = '23514';
          END IF;
          IF NEW.learned_from_transaction_id IS NULL THEN
            RAISE EXCEPTION 'iban history names no transaction it was learned from; an'
              ' IBAN is learned from a confirmed review of a movement'
              USING ERRCODE = '23514';
          END IF;
          IF NEW.learned_from_transaction_id IS DISTINCT FROM proposal_tx THEN
            RAISE EXCEPTION 'iban history was learned from a transaction other than the'
              ' one its confirmed proposal decided' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    # M5: `AFTER`, not `BEFORE`. See the timing note at the end of this migration.
    op.execute(
        "CREATE TRIGGER iban_history_confirmation AFTER INSERT OR UPDATE ON iban_history "
        "FOR EACH ROW EXECUTE FUNCTION enforce_iban_history_confirmation()"
    )

    # ── C8. Active-IBAN uniqueness is per renter, never per account ───────────────
    # `docs/15` § 3.3 F07: "If two active renters share it, each receives the ambiguous
    # signal and the result is Review." `0019` made that state unrepresentable, so the
    # ambiguity the scoring rule exists to resolve could never be reached — two spouses
    # on one joint account are the ordinary case.
    #
    # The guarantee worth keeping is narrower and survives: one renter may not hold the
    # same IBAN active twice. History is versioned (CLAUDE.md § 6), so the predecessor's
    # `valid_to` is closed first.
    op.execute("DROP INDEX uq_iban_history_active")
    op.execute(
        "CREATE UNIQUE INDEX uq_iban_history_active_renter ON iban_history "
        "(account_id, renter_id, normalized_iban) WHERE valid_to IS NULL"
    )

    # ── C3. The receivable projection agrees with itself ──────────────────────────
    # `settlement.py:140` computes `open_after = receivable.open_cents - principal`.
    # Only the principal component reduces `open_cents`, so `open_cents` **is** the open
    # principal — the relation is equality, not a three-way sum. A sum rule would
    # contradict the fixture-verified engine, so it is not written here.
    #
    # `open_costs_cents` and `open_interest_cents` stay bounded below only. Nothing in
    # `docs/15` bounds them above; they arrive from Page 05 in M9, and inventing a
    # ceiling now would be inventing a rule.
    op.drop_constraint("ck_receivable_open_components", "receivable", type_="check")
    op.create_check_constraint(
        "ck_receivable_open_components",
        "receivable",
        "open_costs_cents >= 0 AND open_interest_cents >= 0 AND open_principal_cents >= 0"
        " AND open_principal_cents = open_cents AND open_cents <= expected_cents",
    )

    # ── C9. One Nachzahlung per tenancy and period ────────────────────────────────
    # The Page 01 handoff guard in `payments.py:203-221` is a bare SELECT followed by an
    # INSERT: two concurrent requests both pass it and the renter's debt doubles.
    # `uq_receivable_source` does not cover this — a correction statement is a new
    # `source_id`, so the two rows differ there on purpose.
    op.execute(
        "CREATE UNIQUE INDEX uq_receivable_nk_nachzahlung_period ON receivable "
        "(account_id, tenancy_id, period) WHERE category = 'nk_nachzahlung'"
    )

    # ── M5. Why three triggers above are AFTER and one is not ─────────────────────
    # PostgreSQL 16 evaluates `WCO_RLS_INSERT_CHECK` after every BEFORE ROW trigger and
    # before every AFTER ROW trigger. A BEFORE trigger that resolves a parent through an
    # RLS-scoped lookup therefore *masks* the policy: in a foreign account's context the
    # parent is invisible, the trigger raises its own CheckViolation, and the row never
    # reaches the policy. `payment_allocation` and `iban_history` were refused that way
    # on every cross-account write, so their `WITH CHECK` clauses had no coverage at all
    # — drop either policy and the isolation suite stayed green.
    #
    # Both tables' parent-scope triggers are AFTER now, so the policy speaks first and
    # `packages/db/tests/test_rls_isolation.py` can require it by name. Nothing is
    # relaxed: every one of them still raises when it cannot see its parent, which is
    # what an ordinary same-account defect looks like. `payment_allocation` is
    # append-only (`0017`), so an AFTER trigger has no BEFORE-trigger row edit to miss.
    #
    # `receivable_tenancy_party` stays BEFORE on purpose. It has no separate isolation
    # role to expose: a foreign-account receivable dies on "renter is not a party to its
    # tenancy", which is the same rule working, and re-timing it would change an
    # M6-C2 refusal this slice was not asked to touch.


def downgrade() -> None:
    raise RuntimeError("M6-C3 invariant repairs are intentionally not downgraded")
