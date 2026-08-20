# LEAD-HANDOFF.md — docs/16 merged

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status`, `git log`
and the named branch before acting.

## Repository state — 21.08.2026

- Branch: `main`, after the no-fast-forward merge of `slice/docs-16`.
- Slice commit: `f8db915`. Merge commit: `f0c609a`.
- The docs/16 transcription is approved, committed and merged.
- `main` remains ahead of `origin/main`; nothing was pushed.
- Do not push without Emir's separate instruction.

## UVI transcription

`docs/16-uvi.md` and its source-named data-only oracle cover the complete UVI annex, DWD annual
climate-factor import and latest-state note, all 18 Heizspiegel rows, Page 01b H8/F31, approved Page
05 W4, all eleven relevant Non-Goals, README-for-Emir, twelve register rows and the exact seven-file
correspondence ledger.

The approved transcription applies the later corrections: DWD range `0.40–1.80`; annual factors separate from
monthly degree days; D2 heat-only deductions `24/8`; non-positive guard; labelled over-500
fallback; corrected `1,368 / +132 / +9.6%`; renter as Person/Tenancy context; no second heating-money
allocation; three valid Block D units including the target; provisional HKV, labelled raw-weather
fallback and elapsed-day interpolation.

## Explicit unresolved items

- The exact monthly DWD degree-day dataset and station-to-PLZ mapping remain
  `verify-before-production` and block production Blocks C/D2.
- W4 retains its year-round versus heating-season uncertainty.
- The GEG § 82 notice identity and Wärmepumpe deduction/year freshness remain flagged.
- Block C says to compute on unrounded values but prints `-52 / 952 = -5.5%`; the exact-value path
  yields `-5.4%`. The oracle preserves the printed result and records the conflict for resolution.

## Verification

Focused UVI pytest passed 10 tests. Focused Ruff lint/format and `git diff --check` passed. The full
gate is green: strict mypy, purity, parity, 642 Python tests and 30 web tests passed.

No production, schema, migration, API, engine, adapter, UI or PDF source changed. `berkay-work/`
and `docs/01-tech-stack-explanations.md` remain untouched.

## Next decision

The next D2 specs in the recorded dependency order are `docs/10` and `docs/11`. Do not start them
without Emir's instruction.
