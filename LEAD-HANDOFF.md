# LEAD-HANDOFF.md — next main session

This file aligns the next main agent with the current work. Verify every current-state claim against
Git before acting.

## 1. Read in this order

1. `CLAUDE.md` — binding rules and communication style.
2. `AGENTS.md` — lanes, branches and gates.
3. `git status --short --branch` and `git log -5 --oneline`.
4. `PLAN.md` — current execution order.
5. `docs/03-nk-heating-engines.md` § 0 — Page 01b trace, conflicts and gaps.
6. `docs/08-statement-document.md` — Page 01b output projection.
7. `LAST_OUTPUT.md` — short session summary.

For calculations, the source order is `berkay-work/` → `docs/` → code. The authoritative structured
legal source is `berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv`.

## 2. Repository state — 16.08.2026

- Current branch: `slice/reconcile-page01b`, cut from `main`.
- Current HEAD: `891cb7a docs: require early milestone reconciliation`.
- The same approved roadmap change was first committed as `d371cc3` on the paused
  `slice/m5-bootstrap-contexts` branch.
- Slice A spec work is uncommitted.
- Modified: `PLAN.md`, `docs/03-nk-heating-engines.md`, `docs/08-statement-document.md`,
  `packages/domain/tests/test_energy_reference.py`, and
  `packages/heating-engine/tests/test_berkay_01b_co2_stufen.py`.
- New: `packages/heating-engine/tests/berkay_01b_golden.py` and
  `packages/heating-engine/tests/test_berkay_01b_complete_coverage.py`.
- No implementation source, rules-store file or `berkay-work/` file changed.
- Do not commit, merge or push until Emir asks.

## 3. Current work — Slice A

Goal: reinforce M2 against the complete Page 01b source before any later feature work.

### Complete in the uncommitted spec phase

- Every Page 01b source section is traced into `docs/03` and `docs/08`.
- All 34 fixture IDs are recorded, including `F26b`, `F26c`, `F28a` and `F28b`.
- All 47 matching register rows are inventoried: 20 `geprüft`, 27
  `verify-before-production`.
- Superseded rules, dependencies and confirmed implementation gaps are explicit.
- The old factor-dependent F02 assertions no longer silently select one disputed Erdgas factor.
- `F28b/H7` is an executable red contract for the missing MDL gross-rescaling seam.

### Honest fixture status

- The 34-ID data oracle is specification data. It is not executable golden closure.
- Executable current cases: `F03–F06` and `F16`.
- Executable red case: `F28b`.
- `F01`, `F07–F15`, `F17–F27` including `F26b/c`, `F28a`, and `F29–F31` still need
  executable golden tests before their source changes: 27 cases.
- `F01` and `F26` currently have only primitive-level evidence.

### Hard blocker

Hu/Ho must not be guessed:

- current CSV and the 13.08 handoff: `0.201 / 0.181`, marked `geprüft`;
- later Antwort 03: `0.2016 / 0.1820`, requests a CSV update and
  `verify-before-production`;
- that CSV update is absent.

Therefore `F02` has no approved factor-dependent value. Keep it blocked until Berkay supplies a
reconciled register row or Emir gives explicit source-resolution authority.

## 4. Verification already run

- Focused non-red tests: 246 passed, 3 intentionally skipped.
- Ruff lint and format: green.
- Engine purity: 31 files clean.
- `git diff --check`: green.
- Expected red run: 11 passed, 1 failed because
  `rescale_mdl_gross_positions` does not exist. There was no import or collection error.

The full and demo gates have not run for Slice A. They belong at green closure, not at this
intentional red boundary.

## 5. Exact continuation

1. Review the uncommitted spec/test diff. Do not weaken or replace its expected values.
2. Commit the red specification only when Emir authorizes the commit.
3. Use `engine-implementer` for `F28b/H7`; it owns implementation and cannot edit tests.
4. Re-run the focused test and engine package tests.
5. Before each later implementation seam, use `spec-scribe` to promote its data oracle into an
   executable red golden test. Do not let an implementer create its own test.
6. Leave `F02` blocked until Hu/Ho is resolved.
7. Slice A is done only when every Page 01b fixture has executable coverage, confirmed gaps are
   implemented, Rows 1–3 remain correct, and full/demo gates plus required statement review pass.

Do not start Slice B, resume M5 or merge this branch before Slice A closes green.

## 6. Paused work

The secure M5 bootstrap foundation remains on `slice/m5-bootstrap-contexts`. Role enforcement,
nested-building authorization, the account switcher and the `renter.person_id` negative guard remain
unfinished. Do not carry that implementation into this slice.

## 7. Working style

- Answer only what Emir asks.
- Be short, simple and exact.
- Stop at the requested stage.
- Verify claims against Git and command output.
- Preserve legal flags and source conflicts.
- Never run DB-backed demo gates from an agent worktree.
- Update `PLAN.md` for durable status and overwrite `LAST_OUTPUT.md` at session close.
