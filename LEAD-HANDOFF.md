# LEAD-HANDOFF.md — M6-B merged; M6-C is the open work

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status` and
`git log` before acting.

## Current continuation brief — 23.08.2026

- `main` is at `f578f2f` "merge: complete M6-B finalized archives". `slice/m6-b-review-closure`
  (`c8ca352`) is fully contained in it and has no unmerged work; the two commits have identical
  trees.
- Local `main` is 8 commits ahead of `origin/main` (`a748729`, the M5 merge). Nothing has been
  pushed since M5. Do not push without Emir's explicit go-ahead.
- The only retained untracked file is `Antwort-an-Emir_04.md`. Emir decided it stays untracked at
  repository root; keep it out of every commit.
- M6-B is implementation- and review-closed. It ships owner-only atomic finalization, immutable
  normalized snapshots, stored PDF bytes/SHA-256 hashes, versioned delivery addresses and payment/
  credit instructions, isolated owner and eligible-tenancy archives, Saldo settlements, correction
  `vN+1`, account-preserving FKs and RLS.
- Focused M6-B archive/API/RLS tests, the full gate and the non-fresh demo gate are green. Boundary
  and statement reviews are closed. The live demo fingerprint is unchanged:
  `88eb8434eda65f8d7ff82826fc837a58` (149269 bytes).
- The existing demo PDF remains a live landlord preview. M6-B archive PDFs are owner-only technical
  archives; they are not renter delivery, portal publication, email delivery or legal-production
  approval.

## Remaining M6 scope — M6-C

Sliced into three, per Emir's decision of 23.08.2026:

- **M6-C1** — pure `packages/matching-engine` against approved `docs/15`: scoring, decision order,
  § 366/§ 367 settlement, principal-component split and reversal. All thirteen
  `BANKMATCH-F01`–`F13` fixtures must run through real code.
- **M6-C2** — persistence and boundary: bank/receivable/IBAN-history/proposal/ledger models,
  migration `0017`, RLS and composite FKs, the § 3.1 rewrite of the finAPI-stubbed bank adapter,
  owner-scoped endpoints, and the Page-01 handoff that turns a finalized `RECEIVABLE`
  `StatementSettlement` into an `nk_nachzahlung` receivable.
- **M6-C3** — the German landlord *Zahlungen* screen where a Review proposal is confirmed, plus the
  three job entrypoints and the `docs/15` implementation-status closure.

Background jobs (bank sync, 180-day reconsent cleanup, deadline watchers) ship as service functions
behind a scheduler port. Redis, Arq and Celery stay uninstalled: `docs/01` D7 leaves that pick open
until a real worker slice, and a stubbed finAPI has nothing real to schedule.

Delivery and renter-portal work stay outside M6, after the separate M10 authorization and
legal-production scope.

## Correction — temporal advances are shipped

Earlier handoffs listed "temporal contractual advances" as remaining M6 scope. That is wrong.
M6-A shipped `AdvancePaymentPeriod`, and migration `0015` backfills and drops the
`tenancy.advance_payment_cents` scalar; `packages/db/tests/test_m6_advance_models.py` asserts the
column is gone. Do not reopen that work.

## Unresolved authority

- Preserve all `verify-before-production`, `Konvention` and other open legal flags. In particular,
  payment timing/deadline questions are not settled by technical finalization, and the `docs/15`
  matching weights and 40/79 thresholds (CSV rows 169, 171–173, 177–181) remain flagged
  conventions, never legal support for a match.
- `docs/15` § 5.2 records that the Largest-Remainder tie-break convention is **missing from the
  authoritative source**. An implementation must raise on an exact tie rather than invent a rule,
  and the gap needs a Berkay answer.
- `Antwort-an-Emir_04.md` stays untracked at repository root by Emir's decision.
