# LEAD-HANDOFF.md — docs/10 prepared

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status`, `git log`
and the named branch before acting.

## Repository state — 21.08.2026

- Branch: `slice/docs-10`, created from clean `main`.
- The docs/10 transcription is prepared and uncommitted for Emir's review.
- No commit, merge or push was performed.

## AfA transcription

`docs/10-afa.md` and its data-only oracle cover all Page 03 inputs, `R1`–`R13`, `10-K01`–`10-K15`,
`10-E01`–`10-E26` and exactly `10-F01`–`10-F34`. They also preserve all 13 Page-03 Non-Goals,
README-for-Emir, Antwort 01b § 4b and the exact seven-file correspondence ledger.

The current CSV metadata is mirrored exactly: four rows are `geprüft` and 42 remain
`verify-before-production`. Self-use reduces deductible AfA, never its basis, and does not extend
the depreciation period. The 15% guard requires `leistungBis`, separately from Page 02 `abfluss`.
Variante S remains isolated from the Page 01/02 reference strand.

## Explicit unresolved items

- Weg B remains production-blocked until the BMF source tables replace the four F02 placeholders.
- The month-granular K09 result and day-granular F11 alternative remain unresolved and block
  production use-change output.
- Unverified EStR versions, BFH citations and § 7b values remain explicit.
- No new question file was created during D2.

## Verification

Focused AfA pytest passed 10 tests. Focused Ruff lint/format and `git diff --check` passed. The fast
gate is green: strict mypy, purity, parity and 378 pure-package tests passed.

The slice must contain only documentation and the two data-only fixture files. No production,
schema, migration, API, engine, adapter, UI or PDF source belongs in it. `berkay-work/`, the seven
correspondence files and `docs/01-tech-stack-explanations.md` remain untouched.

## Next decision

Emir reviews the uncommitted docs/10 slice. A later merge requires separate commit and merge
authorization plus `scripts/gate.sh full`. Do not start `docs/11` from this session.
