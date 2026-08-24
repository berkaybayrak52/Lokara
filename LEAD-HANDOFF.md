# LEAD-HANDOFF.md — M6-C3a complete and locally merged

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status` and
`git log` before acting. Git remains authoritative.

## Current state — 24.08.2026

- M6-C3a is technically complete, development-synchronized and locally merged into `main`.
  Nothing was pushed.
- Preserve the modified `LAST_OUTPUT.md` and untracked `Antwort-an-Emir_04.md`. Never stage with
  `git add -A`.
- The matching engine is connected to Postgres through `matching_service.py`; the API exposes
  exactly five new owner-scoped C3a capabilities: profile upsert, match execution, grouped proposal
  list, final decision and payment-ledger list.
- All thirteen `BANKMATCH-F01`–`F13` cases pass through service and persistence. Review moves no
  money before confirmation; reject/duplicate remain final and money-free; repeated and genuinely
  concurrent matching produce one sealed run and at most one ledger result.
- Rank-1-only evidence, immutable proposal runs, projection snapshots, PAYMENT/reversal
  reconciliation, Nachzahlung component neutrality, exact IBAN timestamps and atomic reversal/tie
  conflicts are enforced and covered.

## Database state — important

**Development now matches the final amended migration `0021` verified in the disposable
`lokara_c3a_check` database.** That disposable database was dropped after every check passed. One
fail-fast transaction validated all existing proposal groups,
mapped legacy IBAN dates to midnight UTC and installed only the missing final constraints, triggers
and hardened functions. Alembic remains at `0021`.

The independent catalog comparison and `boundary-auditor` found no differences or findings.
Development retained 293 proposals, 82 confirmations, 170 ledger entries, 80 allocations, 48 IBAN
history rows and all 68 legacy Auto confirmations. Rolled-back behavior/RLS probes, 167 focused
tests, the UTF-8 full gate and the non-fresh demo gate are green. The PDF remains
`88eb8434eda65f8d7ff82826fc837a58` / 149269 bytes. The validated backup remains at
`/tmp/lokara-m6c3a-pre-migration-20260824.dump`. Do not reset the Docker volume or run
`scripts/verify_demo_path.sh --fresh`.

## What remains in M6-C3

- **C3b — open:** bank sync, 180-day reconsent cleanup and deadline-watcher job functions behind a
  scheduler port. Redis, Arq and Celery remain uninstalled.
- **C3c — open:** landlord *Zahlungen* screen. It may confirm, reject or mark duplicate; it does not
  provide manual assignment.

M6 is not closed until C3b and C3c are complete. Renter delivery, portal publication and email stay
with M10.

## Deliberate exclusions and unresolved authority

- finAPI stays stubbed behind the adapter. C3a adds no production provider integration.
- Manual assignment and automatic later use of renter credit do not exist. Credit is recorded, not
  paid out or silently reused.
- The `docs/15` § 4 stored-reference signal remains inert. The source names the signal but does not
  define the compared field; enabling its +15 would invent a convention.
- The Largest-Remainder tie-break is still absent from the authoritative source. Engine and service
  tests prove refusal and full rollback on an exact tie; no ordering is invented.
- All Page-08 matching weights and thresholds retain their `verify-before-production` convention
  status and `Rechtsstand 07/2026`. Green technical checks are not legal-production approval.
- The Zahlungsfrist is requested and never defaulted; the customary 30 days remains a flagged
  convention.
- `Receivable.source_id` remains polymorphic. `ordering_version` and `convention_version` remain
  free text rather than rules-store foreign keys. Pagination and the generic owner-denial copy are
  unchanged.
- V1 remains AIS-only: no PIS payout, SEPA direct debit, late-interest calculation, renter delivery
  or production approval.

## Safety and verification boundaries

- A reviewer probe belongs in a rolled-back transaction. Never disable triggers or leave evidence
  in append-only tables.
- Preserve account scoping in both API membership checks and Postgres RLS.
- Use the final migration, the disposable database and the exact development catalog comparison as
  the synchronized schema evidence.
- Use `scripts/pdf_fingerprint.sh` for statement evidence. The established unchanged baseline is
  `88eb8434eda65f8d7ff82826fc837a58` / 149269 bytes.
