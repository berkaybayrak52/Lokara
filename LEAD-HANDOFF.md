# LEAD-HANDOFF.md — M6 is merged through C2; M6-C3 is the open work

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status` and
`git log` before acting — it describes the repository at one moment, and Git is what is true.

## Current state — 23.08.2026

- `main` is at `92e1318` "merge: complete M6-C2 bank persistence, adapter and endpoints".
- Local `main` is **9 commits ahead of `origin/main`** (`e755b9c`, which Emir pushed at 16:34).
  Nothing has been pushed since. Do not push without his explicit go-ahead.
- The working tree is clean apart from `Antwort-an-Emir_04.md`, which stays untracked at
  repository root by Emir's decision. Keep it out of every commit.
- `slice/m6-workflow-correction` and `slice/m6-c2a-bank-schema` are both fully contained in
  `main` and hold no unmerged work.
- `scripts/gate.sh full` is green: 1119 Python tests, 43 web tests, `mypy --strict` clean, RLS
  38 tenant tables `WITH CHECK` and cross-account-write tested, FK isolation 63 edges, engine
  purity clean. `gate.sh demo` is green and the fingerprint is unchanged:
  `88eb8434eda65f8d7ff82826fc837a58` (149269 bytes).
- The local database was rebuilt from empty twice this session with Emir's permission, which
  also proved migrations `0001`–`0019` apply to a clean database rather than only incrementally.

## What shipped this session

**The workflow correction** (`cc2f758`). `CLAUDE.md` § 10 forbids one agent from writing both a
test and its implementation, so every calculation slice has a mandatory red window — and the Stop
hook, which runs `gate.sh fast`, used to reject turn-endings inside it. Measured over the session
transcripts: ~47 blocks overall, and **12 of the 19 subagent blocks were `spec-scribe`**, the one
role whose deliverable *is* a failing fixture. Write one line naming the slice and the reason to
`.lokara-red`; `fast` then prints every failure and exits 0, while `full` and `demo` treat the
sentinel as a hard failure. It is gitignored and an anonymous sentinel is rejected. `AGENTS.md`
§ 4 also carries brief-and-turn discipline with the measured baseline behind it.

**M6-C1** (`8306b68`) — `packages/matching-engine`, standard library only, all thirteen
`BANKMATCH` cases through real code as 30 tests.

**M6-C2** (`92e1318`) — nine account-scoped tables with migrations `0017`/`0018`/`0019`, the
`docs/15` § 3.1 adapter rewrite with `BANKMATCH-F10` executed at the import boundary, and four
owner-only endpoints carrying the `F12` Page-01 handoff. `docs/02` § 6 holds the persisted shape;
`docs/04` holds the route contract.

## Read this before trusting M6-C2's shape

A `boundary-auditor` pass on 23.08.2026 found **six HIGH defects**, all in code and fixtures
written by a single session. `CLAUDE.md` § 10 wants the fixture author and the implementer to be
different agents; that did not happen anywhere in M6-C2, and this is what it cost.

`0017` got account isolation right and constrained nothing inside one account. A
`payment_allocation` could settle renter 2's debt from renter 1's cash — the exact thing `docs/15`
§ 6 forbids. An allocation could exceed the cents its entry carried, and a negative component
cancelled inside the sum check and then fed Page 01 a negative advance. A `REVERSAL` could be
positive, name no original, or be filed twice, so `F06` nets to +216,000 instead of zero — and
permanently, because the table is append-only. `iban_history` was freely rewritable and required
no confirmation, against § 3.3 and `F09`. `bank_transaction` and `match_proposal` were documented
immutable and were not.

Migration `0019` fixes all six, with fifteen new tests. Each mechanism is listed in `docs/02` § 6
and `PLAN.md` § M6-C.

**Why they shipped:** `check_rls_coverage` accepted a table being *named* in the isolation test,
which an `import` line satisfies. All nine tables passed it while not one had a cross-account
**write** assertion — two of the four tests ran on the owner engine, which bypasses RLS entirely.
The check now demands a `WITH CHECK` clause and a real write assertion, it provably fails when
that coverage is removed, and strengthening it immediately surfaced three more tables predating
this slice (`cost_entry`, `heating_cost_entry`, `allocation_key_assignment`), whose assertions
were added rather than grandfathered.

No second audit ran after `0019`, and `0019` changed a great deal.

## Two deliberate limits — do not "fix" either

1. **The Zahlungsfrist is asked for, never defaulted.** `docs/08` Appendix B flags *Zahlungsfrist
   bei Nachzahlung* `verify-before-production`, and the register is explicit: no statutory
   deadline exists, the claim falls due on receipt of a proper statement, and the customary
   30 days is a `Konvention` anchored only in § 286 Abs. 3 BGB. The Page-01 handoff therefore
   requires an explicit due date and refuses without one. A default would make a flagged
   convention Lokara's answer on every statement, silently and at scale.
2. **The `docs/15` § 4 stored-reference signal is inert.** `_end_to_end_signal` returns 0.
   § 4 scores 15 points against a "stored reference" that §§ 3.2–3.3 define nowhere;
   `receivable.stored_reference` exists as a column so the field has a home, and nothing writes
   it. The question is open in `FRAGEN-an-Berkay-05.md`. Turning the signal on without that
   answer restores the invented convention M6-C1 removed, and `+15` is not cosmetic — it lifts a
   candidate from 25 to 40, which is Unmatched to Review.

## Next work — M6-C3, which completes M6

The German landlord *Zahlungen* screen where a Review proposal is confirmed, the three job
entrypoints (bank sync, 180-day reconsent cleanup, deadline watchers — service functions behind a
scheduler port; Redis, Arq and Celery stay uninstalled, `docs/01` D7 keeps that pick open), and
the `docs/15` implementation-status closure.

It also inherits the LOW audit findings recorded in `PLAN.md` § M6-C, which were deliberately not
fixed: free-text `source_type` and `*_version` columns where `CLAUDE.md` § 6 wants a rules-store
reference; the polymorphic `Receivable.source_id` that carries no composite FK and is therefore
invisible to `check_fk_isolation`; the adapter's `BankTransaction` dataclass accepting a `float`
outside `normalize_transaction`; no pagination on the list endpoints; `require_owner` reporting
"Only owners may create buildings" on payment routes; and `bank_account.consent_expires_at` being
stored and never read, though PSD2 consent expiry is a legal precondition for an AIS pull.

## Traps this session hit — do not rediscover them

- **Append-only tables reject fixture teardown.** `payment_ledger_entry`, `payment_allocation`,
  `bank_transaction`, `match_proposal`, `match_confirmation` and `iban_history` all refuse
  `DELETE`. Retain the fixture graph with per-run UUIDs, the way `test_rls_isolation.py` already
  does — do not try to clean up after yourself, and never disable a trigger to do it.
- **Do not write append-only evidence into the demo account.** `/demo/reset` deletes from
  `statement`, and a FINALIZED row blocks it. A fixture that puts one there breaks
  `TestDemoReset` permanently until the database is rebuilt. Use a dedicated account.
- **The `boundary-auditor` brief needs a rolled-back-transaction rule.** It proved two findings
  with *committed* probe rows in append-only tables, which then blocked the migration that
  forbids them and cost a database rebuild. It did this correctly for one finding and not for two.
- **`check_handoff` is structurally red at HEAD after any docs commit.** `LAST_OUTPUT.md` must
  name HEAD, naming HEAD needs a commit, and the commit moves HEAD. The convention is to run the
  gate *before* the docs commit. Do not loosen the check to make it green.
- **Use `scripts/pdf_fingerprint.sh`, not a raw `md5`.** Two renders of identical code differ in
  `/CreationDate`; the script normalizes that. A raw hash comparison looks like a regression and
  is not one.

## Unresolved authority

- Every `docs/15` matching value stays `verify-before-production` `Konvention` at Rechtsstand
  07/2026: CSV rows 169, 171–173, 177–181. The 60/20/30/15/15/10/5 weights and the 40/79
  thresholds are conventions, never legal support for a match.
- `docs/15` § 5.2's Largest-Remainder tie-break is **missing from the authoritative source**. The
  engine raises `TieBreakUnspecifiedError` on an exact tie and invents no ordering. Open question
  in `FRAGEN-an-Berkay-05.md`.
- `docs/15` § 4's "stored reference" is named by § 4 and defined nowhere in § 3. Same file.
- V1 is AIS-only: no PIS payouts, no SEPA direct debit, no late interest or reminder fees. Renter
  credit is recorded, never paid out. No renter delivery, portal publication or email — that is M10.
- Page 02 remains production-blocked by `09-K01`–`09-K11`, the Trinkwasser route and the
  administration-cost legal check. A technically green path is not legal-production approval.
