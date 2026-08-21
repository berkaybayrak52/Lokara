# LEAD-HANDOFF.md — docs/11 prepared

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status`, `git log`
and the named branch before acting.

## Repository state — 21.08.2026

- Branch: `slice/docs-11`, created from clean `main` at `61ba292`.
- The Page-04 transcription is prepared, unapproved, uncommitted and unstaged.
- Nothing was merged or pushed. No full/demo gate or PDF fingerprint was run.

## Tax-export transcription

`docs/11-tax-export.md` and its data-only oracle cover one payment ledger feeding the Anlage-V
overview and DATEV EXTF. They preserve `11-K01`–`11-K11`, `R1`–`R9`, `11-E01`–`11-E15`, exactly
`11-F01`–`11-F16`, the eight Page-04 Non-Goals, two delegated source boundaries, the arithmetic
audit and the exact seven-file correspondence ledger.

The future-only contracts cover accepted payments, the Page-03 handoff, tax-adviser profile,
year-versioned mappings, readiness evidence and immutable export versions. No production engine,
rules data, schema, API, adapter, screen, PDF or archive was added.

## Explicit unresolved items

- The current 13 Page-04 register rows are mirrored exactly: seven are `geprüft`; six remain
  `verify-before-production`.
- Anlage-V lines, SKR03/SKR04 accounts, EXTF parameters and Festschreibung semantics, S/H
  orientation and the BFH citation remain production-blocking.
- `disagioAbziehbarCent` and handed-off maintenance have no separate source mapping; future M7 must
  assign their lines and prevent double-counting against ledger `instandhaltung`.
- No new question file was created during D2.

## Verification

Focused Page-04 pytest passed 10 tests. Focused Ruff lint/format and both diff checks passed. The
13 fixture rows match the authoritative 180-row CSV field for field. `scripts/gate.sh fast` is
green: Ruff, format, strict mypy, engine purity, agent parity and 388 pure-package tests passed.

`berkay-work/`, the seven correspondence files, production source and
`docs/01-tech-stack-explanations.md` remain untouched.

## Next decision

Review the prepared diff. Commit or merge only after Emir approves it.
