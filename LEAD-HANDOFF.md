# LEAD-HANDOFF.md — Slice A complete, approved and merged

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status` and
`git log` before acting.

## Repository state — 21.08.2026

- Branch: local `main`; Slice A merged at `d6cbb19` from implementation commit `bb41f7c`.
- Slice A passed its implementation, migration, application, document and review gates.
- Emir approved Slice A on 21.08.2026. It is committed and merged locally.
- Nothing was pushed. M5 remains paused.
- D1–D3 remain complete, approved and merged locally.

## Slice A result

- `calculate_page01b_statement(...)` is the shared H0–H8 entry for explicit self-billing and MDL
  inputs. It returns typed readiness, statement values, ordered findings, provenance, device
  evidence, separate unapplied risks and annual comparison.
- Exactly 34 Page 01b fixture IDs execute through that entry. The legacy
  `calculate_heating_statement(...)` remains compatible.
- Migration `0006_page01b_device_metadata` adds the exact heat-device factor and reading segment,
  estimate, tenancy and provenance fields. Existing heat meters backfill to `1.000`.
- The normalized adapter preserves corrections, tenant changes, estimates, device replacements and
  provenance. API, web and PDF project the shared result in German.
- H8 accepts normalized annual DWD factors and labels missing-factor/no-prior fallbacks. Monthly
  import, scheduling and UVI remain outside Slice A.

## Verification

- Focused Slice A suites: 363 Python tests; focused API: 30; focused web render: 1.
- Fast gate: green with 441 pure-package tests.
- UTF-8 full gate: green with 722 Python and 31 web tests.
- Non-fresh demo gate: green; RLS covers 15 tenant tables and all 18 tenant FKs are scoped.
- PDF fingerprint: `34e4f8bda4658f1cc233b38e1c2a8fad` →
  `a45fa3d1e3d69957948e58885b4ab797` (`149280` bytes). The final three-page A4 render passed visual
  review and the deterministic 22-golden/8-canary assertion.

## Boundaries that remain

- Keep the current structural block-(c) copy provisional; do not invent final wording.
- Keep every 3-percent risk separate. There is no automatic sum or deduction.
- Confirmed MDL OCR/API ingestion remains Slice B work.
- Register flags and later Page 02, meter-rule, Page 03, Page 06 and Page 07 dependencies remain
  production blockers in their owning slices.
- The paused M5 branch also uses migration number `0006`; rebase it after Slice A and renumber that
  migration before resuming M5.

## Next decision

Slice B is next in the execution order. Starting Slice B and any push remain separate decisions.
