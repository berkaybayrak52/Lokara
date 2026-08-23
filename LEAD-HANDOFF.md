# LEAD-HANDOFF.md — M6-C3-0 technically closed and locally merged

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status` and
`git log` before acting — it describes the repository at one moment, and Git is what is true.

## Current state — 24.08.2026

- Branch before merge: `slice/m6-c3-0-invariant-repair`, based on local `main` at `063ff5b`.
  M6-C3-0 and the repository-wide status reconciliation were committed and locally merged on
  24.08.2026. No push was authorized or performed.
- `Antwort-an-Emir_04.md` stays untracked by Emir's decision, and is **not** in `.gitignore`.
  Never `git add -A`; stage by explicit path.
- **`.lokara-red` is absent.** The repair window is closed.
- **`scripts/gate.sh full` and the non-fresh `scripts/gate.sh demo` are green:** 1,143 Python
  tests and 43 web tests passed; all deterministic checks and the complete demo path passed.
- PDF fingerprint is unchanged: `88eb8434eda65f8d7ff82826fc837a58`, 149269 bytes.

## The one thing to know

**The amended `0020` is proved from an empty schema and development now matches it.** A
fresh `lokara_amend_check` reached revision `0020`; all 21 trigger functions have
`search_path = pg_catalog, public, pg_temp`; the six amended bodies use `public.*`; and the three
affected triggers are `AFTER`. R13–R17 passed, then R18 passed; the full focused repair/RLS set was
89 passed and the coverage checker reported all 38 tenant tables clean.

The approved hand-delta then hardened the 21 functions, replaced the six bodies and recreated the
three triggers on development in one transaction. Their function hashes and trigger timings match
the throwaway schema. The full gate exposed one pre-existing difference: development recorded
`0020` but lacked the mixed-sign allocation CHECK that a fresh `0020` creates. Emir approved that
one addition; it is validated and the focused, full and demo gates are green. The throwaway
database is dropped. The validated pre-repair backup remains at
`/tmp/lokara-m6c3-0-pre-repair-20260824.dump`.

## What this session did

A `boundary-auditor` pass over `0020` and the slice diff — the one the previous handoff said had
never run — found **two HIGH and five MEDIUM** defects, all confirmed inside rolled-back
transactions. I re-verified H1 and M4 first-hand before acting on either.

- **H1 (HIGH).** The first `enforce_payment_allocation_renter` draft resolved the renter with
  `IF match_proposal_id … ELSIF reverses_entry_id`. `ck_payment_ledger_reversal_shape` does not
  forbid a REVERSAL from also carrying its own proposal, and `docs/15` § 5.3 says it legitimately
  may — the return is a distinct provider movement. So the `IF` branch won, the reversed
  payment's renter was never consulted, and renter 1's returned cash could settle renter 2's debt. The
  migration's own comment (`0020:135-139`) admits its premise is an observation of today's twelve
  rows, not an invariant.
- **H2 (HIGH).** None of the **21** plpgsql trigger functions pinned `search_path`, and every
  parent lookup was unqualified. `lokara_app` holds TEMP and `pg_temp` resolves before `public`, so
  a fabricated `receivable` or `payment_ledger_entry` could answer the trigger while the FKs and RLS
  still bind the real table. Needs arbitrary SQL on the app connection to exploit — but it also
  fires by accident, the first time any job creates a temp table with one of those names.
- **M3-a, M3-b, M4, M5, M6, M7 and five LOW.** See `docs/02` § 6 "Closed on `0020`" and the
  recorded M6-C3 follow-ups.

**Done and green:** M4 (`scripts/check_rls_coverage.py` rebuilt on `ast`; all four matcher cases
pass; 38 tenant tables still clean, so no table's coverage had been resting on glue) and M6 (the
settled-receivable test repointed to the discriminating shape).

**Proved:** H1, H2, M3-a and M5 — fixtures `M6C3R-R13`–`R18` pass on both the fresh disposable
schema and the repaired development schema. M6-C3-0 is technically closed.

## Emir's decisions this session — do not relitigate

1. Fix all six findings on this slice, not a subset.
2. **Amend `0020` in place**, do not stack an `0021`. The migration was uncommitted before this
   local merge, so no other machine had the earlier form.
3. Harden **all 21** trigger functions, not only this slice's nine. The twelve predating ones
   guard statement finalization, archive hashes and the M6-A advances, and carry the same hole.
4. Emir authorized the repository-wide documentation reconciliation, commit and local merge on
   24.08.2026. No push was authorized.

## Next steps, in order

1. Start M6-C3 only after Emir authorizes that implementation slice.
2. Do not push until Emir separately asks.

## Recorded, not fixed — M6-C3 inherits these

`M3-b` (`credit_cents` unconstrained: a 1-cent payment can record 5.000,00 € of credit; `docs/15`
§ 5.1 makes credit the remainder after allocation), `M7` (nothing requires a ledger entry to rest
on a *confirmed* match, though § 4 step 6 says no amount is settled before confirmation — the
slice's own fixture books 600,00 € against a `NEEDS_REVIEW` proposal), and five LOW: the
Nachzahlung period index versus a correction statement, a reversal that need not net its original
to zero, no receivable-side allocation cap, the retained per-run test graph, and F07 being
representable but unreachable through the pipeline.

`Receivable.source_id` stays polymorphic — a composite FK there is a schema redesign on a table
that now carries append-only evidence.

## After this slice — M6-C3, which completes M6

**Nothing today joins the matching engine to the database.** `apps/api` references none of
`MatchProposal`, `MatchConfirmation`, `PaymentLedgerEntry`, `PaymentAllocation`,
`IbanHistory` or `RenterMatchingProfile` — verified by grep. The engine is fixture-complete and
entirely unwired; its only importer is its own test file. That bridge is the substance of M6-C3.

Two facts found while scoping it, so C3a does not rediscover them: `apps/api/pyproject.toml` does
not declare `lokara-matching-engine` (the workspace root does), and `ck_match_proposal_decision`
uses UPPERCASE values while the engine's `Decision` StrEnum is lowercase — translate, do not widen
the CHECK.

Emir approved three slices — **C3a** `matching_service.py` beside `statement_service.py` plus five
owner-scoped endpoints; **C3b** three job functions behind a scheduler port, Redis/Arq/Celery
uninstalled (`docs/01` D7); **C3c** the *Zahlungen* screen following `features/kosten`, confirm or
reject only, no manual assignment. Full scope in `PLAN.md` § M6-C.

## Two deliberate limits — do not "fix" either

1. **The Zahlungsfrist is asked for, never defaulted.** No statutory deadline exists; the customary
   30 days is a `Konvention` anchored only in § 286 Abs. 3 BGB. A default would make a flagged
   convention Lokara's answer on every statement, silently and at scale.
2. **The `docs/15` § 4 stored-reference signal is inert.** `_end_to_end_signal` returns 0. Turning
   it on without Berkay's answer restores the invented convention M6-C1 removed, and `+15` lifts a
   candidate from 25 to 40 — Unmatched to Review.

## Traps — do not rediscover them

- **A subagent's closing claim is not evidence.** Check the database, re-run the tests. This
  session caught a false "all tests pass" only by looking.
- **An audit finding is evidence, not a patch.** The previous session rejected two of its
  auditor's proposed fixes after checking them against the engine and § 5.3, and was right both
  times.
- **A read-only auditor must probe inside a rolled-back transaction.** In `AGENTS.md` § 7 and both
  auditor definitions. The 23.08 pass committed probe rows into append-only tables, which then
  blocked the migration forbidding them and cost a rebuild.
- **Worktree copy-back is manual.** Diff, copy, run the gates in the main tree, then remove it.
- **`check_handoff` is structurally red at HEAD after any docs commit.** `LAST_OUTPUT.md` must name
  HEAD, naming HEAD needs a commit, and the commit moves HEAD. Run the gate *before* the docs
  commit. Do not loosen the check.
- **Append-only tables reject fixture teardown.** Retain the graph with per-run UUIDs and write
  assertions as *refused* inserts, which roll back and leave nothing. Never disable a trigger.
- **Do not write append-only evidence into the demo account.** `/demo/reset` deletes from
  `statement`, and a FINALIZED row blocks it permanently until a rebuild.
- **Use `scripts/pdf_fingerprint.sh`, not a raw `md5`** — `/CreationDate` differs between renders.
- **Postgres is on port 54322**, not 5432.

## Unresolved authority

- Every `docs/15` matching value stays `verify-before-production` `Konvention` at Rechtsstand
  07/2026: CSV rows 169, 171–173, 177–181. The 60/20/30/15/15/10/5 weights and the 40/79
  thresholds are conventions, never legal support for a match.
- `docs/15` § 5.2's Largest-Remainder tie-break is **missing from the authoritative source**. The
  engine raises `TieBreakUnspecifiedError` and invents no ordering.
- `docs/15` § 4's "stored reference" is named by § 4 and defined nowhere in § 3.
- **Three questions** in `FRAGEN-an-Berkay-05.md` with interim handling recorded, none blocking:
  splitting one Nachzahlung across a joint tenancy (refused with 409); whether overpayment credit
  settles a later receivable (recorded, never auto-applied); and what a future rejection does and
  whether manual assignment exists (the contract records an outcome and settles nothing; the
  service/UI is not shipped and manual assignment is absent).
- Whether a learned IBAN must equal its transaction's `counterpart_iban` is **undecided** —
  normalization lives in the adapter, not in SQL. `M6C3R-R16`/`R17` deliberately do not test it.
- V1 is AIS-only: no PIS payouts, no SEPA direct debit, no late interest or reminder fees. Renter
  credit is recorded, never paid out. No renter delivery, portal publication or email — that is M10.
- Page 02 remains production-blocked by `09-K01`–`09-K11`, the Trinkwasser route and the
  administration-cost legal check. A technically green path is not legal-production approval.
