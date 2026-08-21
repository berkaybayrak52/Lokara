# LEAD-HANDOFF.md — docs/14 merged

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status`, `git log`
and the named branch before acting.

## Repository state — 21.08.2026

- Branch: `main`, after the no-fast-forward merge of `slice/docs-14`.
- Slice commit: `9b69f97`. Merge commit: `9f9b549`.
- The Page-07 transcription and Phase D2 are approved and merged.
- Nothing was pushed. No demo gate or PDF fingerprint was run.

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
rows match the authoritative CSV field for field. `git diff --check` passed. The fast gate passed
404 pure-package tests. The UTF-8 full gate passed 678 Python tests and 30 web tests, plus lint,
types, purity, parity and handoff checks.

`berkay-work/`, the seven correspondence files, production source,
`docs/01-tech-stack-explanations.md` remain untouched.

## Next decision

Phase D2 is complete and approved. Do not start D3 correspondence retirement without Emir's
instruction.
