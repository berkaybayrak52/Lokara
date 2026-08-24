# LEAD-HANDOFF.md — G1 technically complete on slice; U is next

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status` and
`git log` before acting. Git remains authoritative.

## Current state — 24.08.2026

- **M6 is technically complete and locally merged.** C3c's landlord *Zahlungen* screen was
  committed as `92e0dcd` and merged into `main` as `6995bc4`, which closes M6-C and with it M6.
  Current `main` and `origin/main` both point to `f372f67`.
- Every `M6-C closed when` condition is now met on `main`: all thirteen `BANKMATCH` fixtures pass
  through the service and persistence, the three job entrypoints are callable, a landlord can
  confirm or reject a Review proposal in the UI, every isolation boundary is green and the rendered
  statement is unchanged.
- **G1 is technically complete and reviewed on `slice/g-shared-guard-foundation`.** It remains
  uncommitted, unmerged and unpushed. The next stage after G1 closure is U (UVI), then M7.
- Preserve the untracked `Antwort-an-Emir_04.md`. Never stage with `git add -A`.
- `slice/m6-c3c-zahlungen` is merged and can be deleted whenever Emir wants; it is kept for now.

## What G1 prepares

`packages/guard-engine` is a pure internal package with three evaluators: W1 statement deadline,
W2 meter calibration and W4 UVI cadence. Exactly `12-F01`–`12-F06` and `12-F11`–`12-F13` execute
through production code. Inputs carry source identity and `today`; callers supply evidence,
Rechtsstand, verification status and scoped conflicts. No database, API, UI, scheduler, provider,
e-mail, push or PDF consumer was added.

W2 executes the unified six-year MessEV period, `geprüft` at Rechtsstand 08/2026; the five-year
Warmwasser/WMZ value is superseded Rechtsstand and must not be restored. What remains attached to
warm-water, heat-meter and heat-exchanger results is the non-blocking retrofit-transition label.
Missing W1 copy and post-retrofit W4 behavior remain explicit source gaps. W3 and W5–W8, UVI calculation/document work and all reminders and
delivery remain open.

## What C3c shipped

Client-only: `apps/web/src/features/zahlungen/` (`proposal-view.ts`, `queries.ts`,
`zahlungen-page.tsx`, `review-list.tsx`, `ledger-list.tsx`), the route
`apps/web/src/app/a/[accountId]/zahlungen/page.tsx`, five snake_case Zod mirrors in
`lib/contracts.ts`, `centsToEurDisplay` in `lib/format.ts`, one gated `NAV_ITEMS` entry in
`features/portal/app-shell.tsx`, and `esbuild: { jsx: 'automatic' }` in `apps/web/vitest.config.ts`
so a `.tsx` render test compiles under the automatic runtime the components are written against.

No endpoint, no table, no column, no migration. Alembic stays at `0021` and no backend file
changed.

Acceptance files: `features/zahlungen/proposal-view.test.ts` (23) for the pure joiner and
`features/zahlungen/zahlungen-view.test.tsx` (12) rendering the screen to static markup for the
properties the joiner cannot hold — no decision control off an open `NEEDS_REVIEW` row, no reversal
control in the journal. Two nav cases in `features/portal/account-switcher.test.tsx` and four
`centsToEurDisplay` cases in `lib/format.test.ts`.

## Database state

Unchanged: development matches migration `0021` and Alembic is at `0021`. C3c and G1 require no
schema change. Do not reset the Docker volume and do not run `scripts/verify_demo_path.sh --fresh`. The
validated backup remains at `/tmp/lokara-m6c3a-pre-migration-20260824.dump`.

## Evidence

For G1, focused tests pass, `scripts/gate.sh fast` is green with 561 pure-package tests, and the
UTF-8 full gate is green with 1,252 Python and 84 web tests. Strict mypy and engine purity are clean.
The statement review's one W2 conflict-scope finding was fixed fixture-first and re-reviewed with
no remaining finding. The red window was proved first by the missing `lokara_guard_engine` module
and again by the reviewer-driven missing applicability field.

The raw PDF MD5 is timestamp-dependent. `scripts/pdf_fingerprint.sh` normalizes those timestamps;
its before/after value is unchanged at `88eb8434eda65f8d7ff82826fc837a58`, 149269 bytes. The full
gate also keeps the PDF content assertions green.

## Recorded, not fixed

- `require_owner` answers 403 with the English, route-inaccurate detail
  `"Only owners may create buildings"` (`authorization.py`), which the client prints verbatim.
- The ledger renders `created_at` through a timezone-naive string split, so a late-evening booking
  on a UTC server can show the previous calendar day. Backend/timezone decision.
- `match_proposal.convention_version` is persisted but not exposed by `_candidate_json` or
  `list_proposals`, so the screen's `Rechtsstand` stamp is a page-level constant. That payload gap
  is C3a's.
- The error copy *"Bitte API und Datenbank prüfen"* is developer-facing, but it is the house
  convention in seven other screens; diverging on one screen would be worse.
- `Ablehnen` and `Dublette` write an immutable record with no confirmation step, and a decided
  proposal does not link to the journal entry it produced.
- The screen has never been exercised against a live API: the four queries and the 409 conflict
  path are unverified at runtime.

## Unresolved authority — technical closure is not legal approval

- Every Page-05-specific register row remains `verify-before-production` except W2's Eichfrist and
  year-end rules, which round 4 closed against MessEV Anlage 7 and § 34 Abs. 2 at Rechtsstand
  08/2026. CSV rows 128 and 129 still print the superseded readings and need new register entries.
  W1 date interpretation and W4 year-round/heating-season cadence remain unresolved. G1 must not
  enable production output.

- Every Page-08 weight and threshold keeps `verify-before-production` at `Rechtsstand 07/2026`. The
  screen presents confidence as a decision aid and states it is not legal proof of a match. Green
  gates are not legal-production approval.
- No renter name is displayed anywhere, because no route resolves a `renter_id` to a `legal_name`.
  The payer is identified by the bank `counterpart_name` and `purpose`.
- The § 4 stored-reference signal stays inert until Berkay answers the open question in
  `FRAGEN-an-Berkay-05.md`.
- The 180-day AIS consent window still has no row in the authoritative register (C3b).

Per `CLAUDE.md`, these carry forward: once the milestone programme is complete, they need their own
execution order and every affected path must be re-verified before production use.
