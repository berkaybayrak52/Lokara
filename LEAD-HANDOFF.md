# LEAD-HANDOFF.md — next main session

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status`,
`git log` and the named branch before acting.

## Repository state — 20.08.2026

- Branch: `main`, after the no-fast-forward merge of `slice/docs-12`.
- `main` is six commits ahead of `origin/main`; nothing was pushed.
- Approved Page 08 is merged. Production bank matching remains open.
- Page 05 is fully transcribed, approved, committed and merged.
- Do not push without Emir's separate instruction.

## Page 05 transcription

`docs/12-guards-deadlines.md` and the data-only Page 05 oracle cover exactly `12-F01…F24`.
The transcription includes W1–W8, all eighteen Page-specific Rechtsstand rows, six shared rows,
all ten Page 05 non-goals, README-for-Emir and the seven-file correspondence ledger.

All eighteen Page-specific rows remain `verify-before-production`. The unresolved 5-year/6-year
meter conflict and every other authority gap remain explicit. `12-F10` is a 3b-to-3a downgrade,
not a complete resolution.

## Verification

The focused Page 05 suite passed 10 tests. Focused Ruff lint/format and `git diff --check` passed.
The full gate is green: strict mypy, 632 Python tests and 30 web tests passed. These are data-only
transcription checks, not production guard behavior or legal approval.

No production, schema, migration, API, engine, adapter, UI or PDF file changed. `berkay-work/`
remains unchanged on this slice. Do not read or modify `docs/01-tech-stack-explanations.md`.

## Next decision

The next D2 document is `docs/16`. Do not start it without Emir's instruction.
