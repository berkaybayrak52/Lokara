# LEAD-HANDOFF.md — M6-B complete

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status` and
`git log` before acting.

## Current continuation brief — 23.08.2026

- Branch before merge: `slice/m6-b-review-closure`, based on local `main` at `d82abcc`. The only
  retained untracked file is `Antwort-an-Emir_04.md`; it is excluded from the M6-B commit pending
  Emir's filing decision.
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

## Remaining M6 scope

- Bank matching and finAPI adapter work.
- Temporal contractual advances, payment ledger/cash events and matching evidence.
- Delivery and renter-portal work, after the separate M10 authorization and legal-production scope.

## Unresolved authority

- Preserve all `verify-before-production`, `Konvention` and other open legal flags. In particular,
  payment timing/deadline questions are not settled by technical finalization.
- `Antwort-an-Emir_04.md` stays untracked at repository root. Emir must decide whether and where it
  is filed; do not include it in this slice.
