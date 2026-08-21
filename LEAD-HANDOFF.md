# LEAD-HANDOFF.md — docs/14 transcription for review

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status`, `git log`
and the named branch before acting.

## Repository state — 21.08.2026

- Branch: `slice/docs-14`, based on main after the approved Page-06 merge.
- The Page-07 transcription is an uncommitted review diff.
- Nothing was committed, merged or pushed. No full/demo gate or PDF fingerprint was run.

## Investment-KPI transcription

`docs/14-investment-kpis.md` and its data-only oracle preserve all seven KPIs, `R1`–`R10`,
`14-K01`–`14-K19`, `14-E01`–`14-E15` and exactly `14-F01`–`14-F14`. The alias map retains every
source `KPI-*` identifier. All 18 register rows, eight Non-Goals, eight source exclusions, the
arithmetic audit and exact seven-file correspondence ledger are present.

The future-only contracts cover the Prüfobjekt snapshot, financing/AfA provenance, partial KPI
results, twelve-month annuity schedule, sensitivity axes and deterministic Bank-PDF view. No
schema, migration, API, engine, UI, PDF renderer, pricing or bank integration was added.

## Explicit unresolved items

- Two Page-07 register rows are `geprüft`; sixteen remain `verify-before-production`.
- Page 03 owns real AfA and deductible interest. The Page-07 acquisition defaults remain labelled
  assumptions, and the R13-interest versus Page-07 R3-interest tax-scenario choice is unresolved.
- Negative tax remains flat-rate scenario arithmetic, never a promised refund or export value.
- The capital-markets permission claim, all defaults/thresholds and AfA availability remain blocked.
- `Lokara_Investitionsmodul_Demo.html` and `AfA-Wizard_Konzept_Entwurf.md` are absent; no contents
  were invented. No question file was created.

## Verification

Focused Page-07 pytest passed 7 tests. Focused Ruff lint and format checks passed. The 18 register
rows match the authoritative CSV field for field. `git diff --check` passed. The main session still
owns the fast gate and independent final diff review.

`berkay-work/`, the seven correspondence files, production source,
`docs/01-tech-stack-explanations.md` and `LAST_OUTPUT.md` remain untouched.

## Current review decision

The uncommitted `docs/14` transcription and exact 14-fixture data oracle await Emir's review. It
adds no production investment implementation, schema, API, UI or PDF renderer.
