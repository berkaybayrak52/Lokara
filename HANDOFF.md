# Lokara handoff — verified local checkpoint

## Repository

- Validation parent `edb7008` on `development`. `LAST_OUTPUT.md` records current HEAD after commit.
- Pre-commit inventory: 93 tracked changes and 31 untracked entries. Preserve local reference artifacts.
- Local `main` is `3898776` (UI-01 portfolio dashboard merge).
- No `.lokara-red` sentinel exists.
- The existing local Postgres container is healthy and Alembic is applied at `0040 (head)`.
- Emir authorized the local checkpoint commit on 05.09.2026. No merge, push, downgrade,
  rebuild or `--fresh` run occurred.

## Requested outcome

Close and consolidate the current large checkpoint: inspect the complete diff, repair verification
failures, complete the required reviews, run `scripts/gate.sh full` and `scripts/gate.sh demo`, then
present the commit decision to Emir. The local checkpoint commit is now authorized;
promotion to `main` and push remain separate decisions.

## Repairs carried forward from the preceding session

- Initial formatting/import/type-ignore failures were repaired.
- A full gate then passed with `1941` Python tests and `183` web tests. This pass predates migration
  `0040` and the final statement/UI repairs, so it is supporting evidence, not the closing gate.
- Ordinary statement fingerprint recorded before final closure work:
  `c4eecb355d57cec620dfcb0134fc9141` / `149275` bytes.
- Boundary audit found that `heating_cost_entry` was mutable and that four nullable `CHECK`
  expressions accepted incomplete evidence.
- Regression class `TestUi08WorkspaceInvariants` now covers the defects with 20 rollback-only
  app-role cases. Migration `0040_ui08_workspace_invariants.py` and matching ORM constraints repair
  them. The database is at `0040`; all 20 tests pass; the focused boundary re-audit is clean.
- Statement/UI review found incorrect warm-water comparison mapping, discarded/false provenance,
  low-contrast legal text, forbidden `rechtssichere` copy, nested controls, an incomplete modal and
  later A4 clipping/fallback-attribution defects.
- Those current regressions are repaired. Verified focused evidence: API UVI file `31 passed`, UVI
  PDF/render file `13 passed`, focused web regressions `19 passed`, Ruff/format/mypy and focused
  ESLint/typecheck clean.
- Final statement/UI re-review is clean: accepted warm-water and fallback documents are each one
  unclipped A4 page; values are `125/+375/+300,0`, raw `250/+250/+100,0`, and
  `365/+135/+37,0`; fallback attribution is truthful; the legal-copy, nested-control and modal
  findings are resolved.

## Closing evidence — 05.09.2026

- `scripts/gate.sh full` and `scripts/gate.sh demo` both pass: 1967 Python tests, zero skips,
  and 188 web tests. Ruff, format, strict mypy, purity, parity and pre-context checks pass.
- The non-fresh demo preserves the existing database at `0040`. RLS covers 73 account-scoped
  tables; all 144 account-scoped foreign keys preserve isolation. Seed and statement rendering
  pass, including 22 PDF golden assertions and 8 scale-leak canaries.
- Before and after demo rendering, the ordinary PDF fingerprint is exactly
  `c4eecb355d57cec620dfcb0134fc9141` / `149275` bytes.
- Closing verification exposed only maintenance defects: formatting in `0040`, a SQLAlchemy
  result typing issue in the new invariant test, and a stale hardcoded migration head. These
  are repaired; the head test now resolves Alembic's single head and requires revision `0022`.
- Two real UVI PDF tests previously skipped for missing `pypdf`. It is now a locked development
  dependency. Required-PDF runs fail on rendering errors rather than skipping; a forced-error
  probe verified that behavior. All 13 UVI document tests now execute under the full/demo gates.
- Documentation reconciliation and independent re-review are complete. PLAN and docs/02, /04,
  /12 and /16 reflect implemented GAS/warm-water UVI, migrations through `0040`, owner routes,
  temporal advances, current verification and outstanding UI acceptance. The two residual PLAN
  wording findings were corrected exactly as requested and checked by the main session.
- `adjustment/` now identifies the actual guard discovery token and records the already-selected
  WZB PLZ source. No legal values, authority flags or application behavior changed this session.
- Staged and unstaged state were inspected separately; nothing is staged. `git diff --check`
  passes. All pre-existing source edits, implementation files and local artifacts remain preserved.

## Important scope decision

The ordinary demo PDF still says advances are not included. This is pre-existing and its unchanged
fingerprint confirms it is not a checkpoint regression. `docs/08-statement-document.md` explicitly
defines that PDF as a non-final live preview and assigns actual advances/Saldo and formal minimum #4
to the separate M6-B finalized tenant archive. Do not silently broaden this checkpoint to redesign
that preview.

## Exact continuation

1. The authorized local commit is `feat: consolidate M9, UVI and portfolio workspaces` on
   `development`. Confirm it in Git and read `LAST_OUTPUT.md` for the actual resulting HEAD.
   The checkpoint does not claim full portfolio UI acceptance.
2. Preserve local design/reference artifacts outside the commit. Do not restart implementation
   or repeat unchanged completed reviews merely because a new session begins.
3. If source changes after the evidence above, run the affected checks/review before further
   consolidation and update `LAST_OUTPUT.md` to the actual resulting HEAD.
4. Promotion to `main` and push remain separate decisions. M10 is the next milestone in PLAN,
   but no M10 implementation is authorized by this checkpoint handoff. M7-F remains after M10.

Emir's recurring usage rule: at about 10% remaining of the 5-hour limit, stop work and write a
precise handoff. Use visible quota information or Emir's warning; elapsed wall-clock time alone
does not reveal the remaining usage quota. A direct stop request takes effect immediately.

## Production limits unchanged

- M9 is technically closed and the later checkpoint is verified; neither is production-approved.
- No real provider or scheduler; automation remains default-off.
- UVI delivery still lacks a frozen artifact; the production checklist catalogue is empty.
- UVI register authority, exact monthly content, cadence and recorded legal/runtime audit limits
  remain production-blocking.
- UI-07 remains a partial demo core; complete per-step UI acceptance and the live-browser
  accessibility matrix remain outstanding and are not cleared by the automated gates.
