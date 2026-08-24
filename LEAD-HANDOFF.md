# LEAD-HANDOFF.md — M6 complete; G (shared guard foundation) is next

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status` and
`git log` before acting. Git remains authoritative.

## Current state — 24.08.2026

- **M6 is technically complete and locally merged.** C3c's landlord *Zahlungen* screen was
  committed as `92e0dcd` and merged into `main` as `6995bc4`, which closes M6-C and with it M6.
  **Nothing is pushed.** No branch has a remote.
- Every `M6-C closed when` condition is now met on `main`: all thirteen `BANKMATCH` fixtures pass
  through the service and persistence, the three job entrypoints are callable, a landlord can
  confirm or reject a Review proposal in the UI, every isolation boundary is green and the rendered
  statement is unchanged.
- The next stage in `PLAN.md`'s execution order is **G — the shared guard foundation** against
  approved `docs/12`, then U (UVI), then M7.
- Preserve the untracked `Antwort-an-Emir_04.md`. Never stage with `git add -A`.
- `slice/m6-c3c-zahlungen` is merged and can be deleted whenever Emir wants; it is kept for now.

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

Unchanged: development matches migration `0021` and Alembic is at `0021`. C3c required no schema
change. Do not reset the Docker volume and do not run `scripts/verify_demo_path.sh --fresh`. The
validated backup remains at `/tmp/lokara-m6c3a-pre-migration-20260824.dump`.

## Evidence

`scripts/gate.sh fast`, `full` and `demo` are green on the merged tree: 1,233 Python and 84 web
tests, `mypy --strict` clean, `check_pre_context_reads.py`, `check_rls_coverage.py`,
`check_fk_isolation.py` and `check_engine_purity.py` clean. The rendered statement is unchanged at
149269 bytes, 22 goldens present and 8 scale-leak canaries absent. The red window was proved real:
the fixture failed with a missing-module error before `proposal-view.ts` existed.

**The demo PDF's MD5 is not a reproducible invariant.** The PDF embeds `/CreationDate` and
`/ModDate`, so the hash changes on every render while the byte count stays at 149269. The
`88eb8434eda65f8d7ff82826fc837a58` recorded in earlier handoffs was only ever valid for one render
instant, and no gate ever checked it. Use the byte count plus `assert_statement_pdf`'s content
assertions instead, and do not "verify" that hash again.

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

## Unresolved authority — M6 is technically closed, not legally approved

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
