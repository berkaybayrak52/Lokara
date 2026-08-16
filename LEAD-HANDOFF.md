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

- Current branch: `slice/reconcile-page01b-v2`, cut from `main`.
- H7 gross MDL rescaling is committed separately at
  `9f7d744 feat(heating): implement H7 gross MDL rescaling`.
- The working tree contains only the next uncommitted RED specification phase.
- No rules-store or `berkay-work/` value was changed. The current CSV remains authoritative.

## 3. Current work — Slice A

Goal: reinforce M2 against the complete Page 01b source before any later feature work.

### Complete in the uncommitted spec phase

- Every Page 01b source section is traced into `docs/03` and `docs/08`.
- All 34 fixture IDs are recorded, including `F26b`, `F26c`, `F28a` and `F28b`.
- All 47 matching register rows are inventoried: 20 `geprüft`, 27
  `verify-before-production`.
- Superseded rules, dependencies and confirmed implementation gaps are explicit.
- F02's factor-independent missing-cost refusal is RED without selecting either Erdgas pair.
- F18 uses only WE-03 as missing (`58/194`) and asserts Berkay's authoritative printed cents; the
  withdrawn per-block override is recorded as superseded.
- A2 has executable RED device/span contracts for F01/F15/F16/F17/F22/F27.
- PLAN has concrete A2–A7 rows assigning every case that is not already exact and green.

### Honest fixture status

- The 34-ID data oracle is specification data. It is not executable golden closure.
- Exact green cases: `F03–F06`, `F16` and `F28b`.
- Intended RED hand-offs: F02 cost refusal, exact F18 and A2 device spans.
- F20 remains partial until H1 aggregation and the § 6a network disclosures exist.
- F29 belongs to the MDL net branch; the gross seam is not closure evidence for it.
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

- New owned tests: Ruff lint/format and strict mypy are green; `git diff --check` is green.
- Expected RED run: 1 passed, 7 failed. F02 currently reaches a `None` money TypeError instead of a
  German `HeatingInputError`; F18 returns `108091/74933/43122/101117` instead of Berkay's table;
  the five A2 cases fail because `HeatingDevice` is absent. Collection succeeds.

The full and demo gates have not run for Slice A. They belong at green closure, not at this
intentional red boundary.

## 5. Exact continuation

1. Review and commit the current RED specification separately from H7 implementation.
2. Use `engine-implementer` for A2; it owns implementation and cannot edit these tests.
3. Preserve F02's factor block. Implement only the independent missing-cost refusal in A2/A3.
4. Implement F18 from its exact WE-03-only input and authoritative output; do not restore the
   withdrawn per-block result.
5. Continue sequentially through PLAN A3–A7, with a RED fixture before each implementation seam.
6. Slice A is done only when every Page 01b fixture has executable coverage, confirmed gaps are
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
