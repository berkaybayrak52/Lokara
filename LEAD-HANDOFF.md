# LEAD-HANDOFF.md — M6-C3b complete and locally merged

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status` and
`git log` before acting. Git remains authoritative.

## Current state — 24.08.2026

- M6-C3b is technically complete and locally merged into `main`. Slice commit `1e86059` was merged
  as `4927dc1`. **Nothing was pushed.**
- Preserve the untracked `Antwort-an-Emir_04.md`. Never stage with `git add -A`.
- M6-C3a remains technically complete, development-synchronized and locally merged into `main`.
- The slice is `packages/adapters/src/lokara_adapters/scheduler.py`
  (`ScheduledJob`, `SchedulerPort`, `StubScheduler`), `apps/api/src/lokara_api/bank_sync.py`,
  `apps/api/src/lokara_api/jobs.py`, `deps.job_account_session`, and the acceptance files
  `apps/api/tests/test_m6c3b_jobs.py` (10) and `packages/adapters/tests/test_scheduler_port.py` (12).
- The jobs add no endpoint, no table, no column and no migration. Alembic stays at `0021`.
- Sync imports from every connected bank account, then matches the merged result in
  `(bank_booking_date, provider_transaction_id)` order. A § 4 `AUTO_MATCH` settles on a schedule;
  `NEEDS_REVIEW` still moves no money. `expire_bank_consents` and `watch_deadlines` write nothing.

## Database state

Unchanged from the C3a handoff: development matches the final amended migration `0021`, and Alembic
is at `0021`. C3b required no schema change. Do not reset the Docker volume and do not run
`scripts/verify_demo_path.sh --fresh`. The validated backup remains at
`/tmp/lokara-m6c3a-pre-migration-20260824.dump`.

The demo seed now sets `bank_account.consent_expires_at` on the demo bank account, computed as
`now + 180 days`, so the AIS pull still works after the consent precondition. `reset_demo` names it
as the one column its "same ids, same numbers" promise no longer covers. No statement figure,
allocation or PDF byte reads it.

## Evidence

`scripts/gate.sh fast`, `full` and `demo` are green: 1,233 Python and 43 web tests,
`mypy --strict` clean over 200 files, `check_pre_context_reads.py`, `check_rls_coverage.py`,
`check_fk_isolation.py` and `check_engine_purity.py` clean. The PDF is unchanged at
`88eb8434eda65f8d7ff82826fc837a58` / 149269 bytes. The nine DB-backed job tests were re-run with
`LOKARA_REQUIRE_DB=1`, so they provably hit Postgres. The merged-FIFO fixture was verified to fail
under the previous per-bank-account ordering, so it discriminates rather than merely passing.

## What the boundary audit changed

Two HIGH and three lesser findings were fixed rather than recorded:

- `deps.job_account_session` refuses a session whose role bypasses RLS. `run_for_accounts` takes an
  engine, the owner `DIRECT_URL` engine bypasses FORCEd RLS, and `run_match` resolves its scope from
  the row it found — a job wired to that engine would have settled across accounts with no error.
- `0021`'s three reconciliation constraints are `DEFERRABLE INITIALLY DEFERRED`, so releasing a
  savepoint proved nothing: a violation would have surfaced at the outer COMMIT and discarded the
  whole run after it was already counted as `settled`. Each savepoint now forces
  `SET CONSTRAINTS ALL IMMEDIATE`, restores `ALL DEFERRED`, and refuses `IntegrityError`.
- The dedupe set carries its own `account_id` predicate; sync no longer orders settlement by
  `bank_account_id` before the booking date; `reset_demo`'s determinism claim is corrected.

## Recorded, not fixed

- `matching_service.run_match` resolves a `BankTransaction` by id alone. That is the C3a contract,
  now backed by the RLS-role guard above. Changing its signature is a C3a change, not a C3b one.
- The DB-backed API fixtures commit undeletable append-only rows into the developer database with no
  teardown. Inherited from `test_m6c3a_matching_service.py`; C3b adds a second account per run.
- `AIS_CONSENT_MAX_DAYS = 180` is a code literal, duplicated as `180` in the seed, where
  `CLAUDE.md` § 6 wants a rules-store value. It cannot be registered until the register has a row.

## Unresolved authority

- The 180-day AIS consent window has **no row** in
  `berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv`. It is a Lokara `Konvention`,
  `verify-before-production`, `Rechtsstand 08/2026`, on an unverified reading of PSD2 RTS Art. 10.
  No expiry is ever defaulted from it; a `NULL` consent refuses the pull instead.
- No cross-account enumeration exists. `account` is scoped by its own id and `CLAUDE.md` § 3.3
  allows exactly one pre-context read, so a real scheduler must be handed its account ids.
  `docs/15` § 5.6 records the gap as open.
- Every Page-08 weight and threshold keeps `verify-before-production` at `Rechtsstand 07/2026`.
  Green gates are not legal-production approval.

## Process deviation to know about

`.lokara-red` declared that the C3b fixtures would land before the implementation. They did not: the
source was written in parallel with the fixture author. The `CLAUDE.md` § 10 separation held — the
fixture author worked from the pinned contract in its brief and never read `jobs.py` or
`bank_sync.py` — but the red run had to be proved by blocking the modules on the import path rather
than by their absence.

## What remains in M6

**C3c — open:** the landlord *Zahlungen* screen. It may confirm, reject or mark duplicate; it does
not provide manual assignment. M6 is not closed until it ships. Renter delivery, portal publication
and email stay with M10.
