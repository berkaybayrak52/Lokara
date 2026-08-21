# LEAD-HANDOFF.md — docs/13 merged

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status`, `git log`
and the named branch before acting.

## Repository state — 21.08.2026

- Branch: `main`, after the no-fast-forward merge of `slice/docs-13`.
- Slice commit: `fbba9f1`. Merge commit: `910b340`.
- The Page-06 transcription is approved and merged.
- Nothing was pushed. No demo gate or PDF fingerprint was run.

## Contract-clause transcription

`docs/13-contract-clauses.md` and its data-only oracle preserve Page 06's `B1`–`B8`, `E1`–`E11`,
exactly `CLAUSES-F01`–`CLAUSES-F19`, all 17 register rows, the seven Page-06 Non-Goals, eleven
source exclusions, the arithmetic audit and the exact seven-file correspondence ledger.

The future-only contracts cover versioned clause references, composition, compatibility/signature
gates, immutable risk results, optional SEPA capture and action-workflow inputs. No clause body,
letter body, production rule, schema, migration, API, engine, adapter, UI or signature/payment
integration was added.

## Explicit unresolved items

- Nine Page-06 register rows are `geprüft`; eight remain `verify-before-production`.
- Index-decline behavior, the § 559 six-year-window start, state-regulation coverage, small-repair
  defaults, planned Mietrecht-II changes, SEPA expiry and the missing fixed-term signature fixture
  remain unresolved.
- Page 06 supplies no complete clause-text/version catalogue or complete Mieterhöhung-,
  Kündigung- or Mahnung bodies. These missing sources still block M8 implementation.
- The stale Page-06 AfA-basis wording is explicitly superseded: Page 03 reduces deductible AfA,
  never the basis; Page 04 owns tax income; Page 06 only routes the self-use period.
- No new question file was created during D2.

## Verification

Focused Page-06 pytest passed 9 tests. Focused Ruff lint and format checks passed. The 17 register
rows match the authoritative CSV field for field. `git diff --check` passed. The fast gate is green:
strict mypy, engine purity, agent parity and 397 pure-package tests passed.

The UTF-8 full gate is green: Ruff, format, strict mypy, engine purity, agent parity, 671 Python
tests, 30 web tests, web lint/typecheck and the handoff check passed.

`berkay-work/`, the seven correspondence files, production source,
`docs/01-tech-stack-explanations.md` remain untouched.

## Next decision

The next D2 transcription is `docs/14`. Do not start it without Emir's instruction.
