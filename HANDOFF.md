# Lokara handoff — M10-R1 technically complete

## Current slice — 11.09.2026

M10-R1 is technically complete on `slice/m10-r1-activation-codes`, created from local `main` at
`a82023a`. The resulting local slice commit is recorded in `LAST_OUTPUT.md`; it is not merged or
pushed.

- Migration `0041` and the ORM define account-scoped activation codes, immutable redemption
  evidence and immutable attributable-refusal evidence. Direct non-null `renter.person_id` INSERTs
  and writes without matching redemption evidence are blocked for runtime and owner roles.
- Owner-only issuance stores only the SHA-256 digest. Redemption uses the non-secret account
  locator only to open an RLS-scoped session, links exactly the authenticated Person and appends one
  spend under concurrency.
- All refusal cases, including missing/null/non-string request shapes, use the same timed HTTP 400
  `M10-COPY-03` response. Safely attributable refusals append `renter_activation_attempt`; malformed
  or nonexistent locators remain structured operational logs without raw values.
- `resolve_bootstrap_subject` consumers are checked exactly to `me.py` and
  `renter_activation.py`. `.lokara-red` is removed.
- Focused verification: DB/RLS `116 passed`; activation API/M5 guard `39 passed`; pre-context
  `48 passed`; schema inventory `26 passed`.
- Boundary re-audit is clean. RLS covers `76` tenant tables and FK isolation covers `152`
  account-scoped edges; the live pre-context checker is clean.
- Closing `scripts/gate.sh full` is green: `2003` Python tests and `210` web tests; Ruff,
  formatting, strict mypy, purity, parity, ESLint and TypeScript pass.
- Preserve the five untracked `adjustment/` reference files; they remain untouched.

The remaining decision is whether to merge this slice into local `main`. Do not merge or push
without Emir's authorization.

## Earlier verified checkpoint

## Owner UVI UI — verified local completion, 11.09.2026

The verified source commit is `f576a50`, locally merged into `main` on 11.09.2026. Implementation
and bounded verification are complete. No push was performed or authorized. This section
supersedes the older checkpoint continuation below for the UVI task.

### Result

- Owner-only navigation after Zähler opens `/a/[accountId]/uvi`. Live account-scoped object,
  unit, tenancy and month selection exposes the existing generation/reopen and scoped PDF path.
- The page shows server errors and production conflicts, blocks duplicate submissions and hides
  stale results when selection changes. Preview offers no generation/download success.
- Shared transport rejects unsupported preview mutations before network access, while retaining
  supported synthetic payment decisions. The existing Zähler `gasConversion: null` fix is preserved.
- Live `asOf` timestamps now produce the correct previous-month default. The former date-only
  assumption caused a verified live RangeError; the realistic timestamp fixture failed before repair.
- Small screens force the shell's 72px icon navigation without overwriting the desktop preference.
  Controls shrink, long labels/actions wrap without clipping, and header spacing clears the fixed bell.
- No backend, schema, calculation, legal value, PDF renderer, delivery or portal change was made.

### Closing evidence

- `scripts/gate.sh full`: green, 1967 Python tests (zero skips), 210 web tests; lint, types,
  purity, parity and pre-context checks pass. Log: `/tmp/lokara-uvi-full-gate.log`.
- `scripts/verify_demo_path.sh` without `--fresh`: green on the preserved local database;
  73 RLS tables, 144 account-scoped FKs, 22 PDF goldens and 8 scale canaries.
  Log: `/tmp/lokara-uvi-demo-path.log`. Full gate and demo path were run separately to avoid
  repeating the already-green full suite; no combined `gate.sh demo` run is claimed for this slice.
- Web production build passes and includes `/a/[accountId]/uvi`.
  Log: `/tmp/lokara-uvi-web-build.log`. Its first sandboxed attempt could not fetch existing
  Google Fonts; the approved network-enabled retry passed.
- Ordinary statement PDF before and after fingerprint is unchanged:
  `c4eecb355d57cec620dfcb0134fc9141`, 149275 bytes.
- Local Chromium UI checks passed at 320, 390, 1280, 1440 and 1920 px, fresh mobile load,
  desktop → mobile → desktop preference preservation, and 200% CSS scaling. Keyboard Tab
  reaches submit through native month segments; Enter submits once. No horizontal overflow.
  Success, missing-data error, selection-change hiding and preview states were inspected.
- Statement/UI re-review is clean; the prior P1 mobile finding is resolved. Boundary review of
  owner/account/building/run checks, stale results and preview transport is clean.
- Main inspected staged and unstaged state: nothing staged, unrelated local artifacts preserved.

### Verification limits and production boundaries

- Live sign-in, account lookup and meter-workspace selection work. With existing demo data,
  generation returns the correct 422: “Für diesen Monat fehlt eine gültige UVI-Gebäudekonfiguration.”
  The UI displays it and exposes no false PDF link. The demo account had no existing UVI archive.
- Browser success screenshots use intercepted test responses. Actual generation/archive/PDF
  boundaries are covered by the existing U5 database tests; real PDF rendering is covered by
  the PDF suite. No successful UVI download from this live demo account is claimed.
- No monthly UVI facts were invented or seeded to manufacture a successful demo. Production
  authority, content/cadence and frozen-delivery-artifact blockers in docs/16 and M9 remain.
- This review closes the bounded owner UVI screen, not the wider portfolio browser matrix or M10.

### Continuation and retained evidence

No implementation remains in this slice. Commit and local merge are complete; push awaits Emir's
separate decision. Preserve all existing uncommitted `adjustment/` reference artifacts.
The two supported local services remain on ports 3000/3001; existing `lokara-db` is healthy.
Temporary evidence can be regenerated if cleaned:
`/tmp/lokara-uvi-browser-matrix.py`, `/tmp/lokara-uvi-browser-check.py`, and screenshots in
`/tmp/lokara-uvi-browser/` (`result-*.png`, `mobile-fresh.png`, `live.png`,
`live-generation.png`, `error.png`, `preview.png`). The oldest standalone
`/tmp/lokara-uvi-preview.png` predates the landmark/spacing repair and is obsolete.

Emir last reported 28% of the 5-hour allowance remaining. At 10% remaining, stop and hand off;
use visible quota information or Emir's warning, never elapsed wall time as a quota estimate.

## Repository

- Validation parent `edb7008` on `development`. `LAST_OUTPUT.md` records current HEAD after commit.
- Pre-commit inventory: 93 tracked changes and 31 untracked entries. Preserve local reference artifacts.
- Local `main` was fast-forwarded to `f576a50` on 11.09.2026 with Emir's authorization.
  `development` remains at `5a1ee8b`; the Zähler preview fix is included in `f576a50`.
- No `.lokara-red` sentinel exists.
- The existing local Postgres container is healthy and Alembic is applied at `0040 (head)`.
- Emir authorized the local checkpoint commit on 05.09.2026 and its merge on 06.09.2026.
  No push, downgrade, rebuild or `--fresh` run occurred.

## Requested outcome

Close and consolidate the current large checkpoint: inspect the complete diff, repair verification
failures, complete the required reviews, run `scripts/gate.sh full` and `scripts/gate.sh demo`, then
present the commit decision to Emir. The local checkpoint commit is now authorized;
promotion to local `main` is complete. Push remains a separate decision.

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

### Local follow-up — Zähler preview loading

After commit `5a1ee8b`, Emir reported that Chrome opens Zähler but shows
“Zählerbestand konnte nicht geladen werden.” The live API returns HTTP 200 and matches the
frontend contract. The synthetic preview response instead failed validation for all 13 meters:
required nullable `gasConversion` was omitted. Chrome retaining preview mode is the likely
browser difference; its actual storage was not inspected.

The shared preview meter factory now explicitly returns `gasConversion: null` for its non-gas
meters. `apps/web/src/lib/demo-preview.test.ts` proved the defect red and now verifies the
complete workspace contract. The focused 189 web tests, ESLint and TypeScript passed before the
UVI slice; the later full gate passes 210 web tests and includes this repair. The scoped statement
review is clean. This follow-up is included in `f576a50`; the earlier checkpoint evidence belongs
to `5a1ee8b`.
Chrome visual confirmation remains with Emir because no browser connection is available.

### Checkpoint continuation

1. The authorized local commit is `feat: consolidate M9, UVI and portfolio workspaces` on
   `development`. Confirm it in Git and read `LAST_OUTPUT.md` for the actual resulting HEAD.
   The checkpoint does not claim full portfolio UI acceptance.
2. Preserve local design/reference artifacts outside the commit. Do not restart implementation
   or repeat unchanged completed reviews merely because a new session begins.
3. If source changes after the evidence above, run the affected checks/review before further
   consolidation and update `LAST_OUTPUT.md` to the actual resulting HEAD.
4. Promotion to local `main` is complete; push remains a separate decision. M10 is the next milestone in PLAN,
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
