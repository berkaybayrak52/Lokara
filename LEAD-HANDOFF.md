# LEAD-HANDOFF.md — next main session

Read `CLAUDE.md`, `AGENTS.md`, `PLAN.md`, then `docs/03-nk-heating-engines.md` § 0.
Verify this handoff with `git status` and `git log` before acting.

## Repository state — 17.08.2026

- Branch: `slice/reconcile-page01b-v2`.
- Baseline before the current checkpoint:
  `a350f98 test(heating): define Page 01b A4 plant aggregation`.
- The checkpoint includes the A4 self-billing source, F02 CSV reconciliation, supporting docs and
  fixtures, the restored single Slice A and the D1–D3 documentation gate.
- Nothing was merged or pushed.
- No `berkay-work/` or rules-store numeric value changed.

## Slice A status

Green on the current branch:

- A1/H7 gross MDL rescaling: `9f7d744`.
- Corrected A2 RED spec: `ca07f3b`.
- A2 implementation, F02 missing-cost refusal and exact Berkay F18 totals: `716f741`.
- A3 RED spec: `e20d792`.
- A3 plant/CO₂ implementation: `89db9e0`.
- A4 RED spec: `a350f98`; self-billing implementation included in the current checkpoint.
- Main-tree fast gate: formatting, lint, strict mypy, engine purity and agent parity green; 307
  pure-package tests passed.

Slice A is not finished. The implemented seams are supporting capability evidence, not full
Page-01b end-to-end fixture closure. The exact remaining closure conditions are in `PLAN.md`.
Implementation is paused while D1–D3 reconcile the docs and retire the extracted correspondence.

## Source decisions that must stay

- F18 uses Berkay's table: renters `108090/74932/43121/101117`, owner `10958`.
- The earlier derived F18 R1 table is superseded.
- F02 missing supplier CO₂ cost is a hard refusal.
- F02 uses the authoritative CSV values: Erdgas Hu `0.201`, Ho `0.181`, conversion provenance
  `0.903`, status `geprüft`, Rechtsstand `07/2026`. The later 01b handoff confirms that the CSV wins
  over Antwort 03's stale pair. Focused F02 and public-provenance verification is green: 64 passed;
  statement re-review has no remaining blocker or high finding.
- A4 oil logic uses consumed stock, not purchases, and does not invent CO₂ cost.

Do not resume Slice A, start Slice B, resume M5, merge or push before D1–D3 are approved. After
that, Slice A must close green before later implementation work.
