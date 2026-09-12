# Lokara handoff — owner activation demo complete

## Demo preview repair closure — 12.09.2026

Demo repair `4032889` is fast-forwarded into local `main`; nothing was pushed. The local demo stack
was restarted through `scripts/Lokara Demo.command` and verified healthy: database healthy, API
`/health` 200 and web `/` 200.

- Portfolio Preview exposes `Mieterportal` only for a rented preview unit and issues a fresh
  synthetic activation code for the exact preview tenancy/renter pair.
- Preview codes expire after seven days, spend once, stay in module memory and unlock only the
  activated renter context, overview and empty document list.
- Recognized preview refusals remain local synthetic 404s and never fall through to live API data;
  wrong account, tenancy and renter paths are refused.
- The successful owner result offers a same-tab `Mieterportal öffnen` link only in preview mode.
  Live issuance continues to show the raw code without inviting the owner into the renter context.
- Statement/UI and boundary reviews are clean. The full gate passes `2052` Python and `258` web
  tests; `.lokara-red` is absent.
- Preserve `LAST_OUTPUT.md` and the five unrelated `adjustment/` files. No push is authorized.

## Owner activation follow-up closure — 12.09.2026

The follow-up is committed as `2e65aa9` and fast-forwarded into local `main`. Nothing was pushed.
The named RED window is closed and `.lokara-red` is absent.

- Emir requested an owner-side activation-code button in the lower-right `Mieterportal` module of
  the Unit overview.
- The feature and fixtures are implemented in the API dashboard projection, strict client contract,
  query hook, Unit overview and focused API/web tests.
- The API exposes the portal module only to an owner with exactly one unconflicted current tenancy.
  The UI provides one activation action per renter, single-flight pending behavior, unique party
  identification, exact one-time code output and Europe/Berlin expiry without browser persistence.
- Focused verification is green: API `4 passed`; web `10 passed`. The statement/UI review and
  boundary audit are clean after the UI findings were repaired.
- `scripts/gate.sh full` is green: Ruff, formatting, strict mypy, purity, agent parity, pre-context,
  all `2052` Python tests, ESLint, TypeScript and all `246` web tests pass.
- The boundary auditor ran one existing activation API test whose fixture commits random non-demo
  append-only test rows without cleanup. It stopped further probes and did not attempt forbidden
  deletion. The repository result and demo account are unaffected.
- Preserve `LAST_OUTPUT.md` as the live checkpoint and the five unrelated `adjustment/` files.

## M10-R4 closure — 12.09.2026

M10-R4 is technically complete and locally merged into `main` as `ed28f55`. Nothing is pushed. The
five unrelated untracked `adjustment/` files remain untouched.

- Migration `0044`, ORM and API copy immutable statement periods/UVI months from their sources.
- The renter route group provides activation, own-tenancy, statement and UVI screens with exact
  approved copy, renter-aware entry and context switching.
- Focused DB/API/web tests pass `6 + 20 + 28`; RLS covers `77` tables, FK isolation `157` edges and
  the pre-context checker is clean.
- Statement review and boundary re-audit are clean. The full gate passes `2048` Python and `238`
  web tests. `.lokara-red` is absent.

No R4 work remains. Lane I is next under `PLAN.md`; do not push without Emir's decision.

## M10-R3 closure — 11.09.2026

M10-R3 is technically complete and locally merged into `main` as source commit `2ba245d`. Nothing
was pushed. The named `.lokara-red` window is closed.

- `M10-PUB-F01`–`F07` specify and cover migration `0043`, immutable tenancy-scoped publication,
  source eligibility, exact archived-byte copying, owner-only publication, renter-only listing and
  download, digest verification and the required cross-account write refusal.
- `RenterPortalPublication`, its account-safe composite foreign keys, forced RLS, append-only guard,
  source uniqueness and UVI `PUBLISHED` uniqueness are implemented. A real
  `0043 → 0042 → 0043` migration cycle passed.
- The owner API copies and verifies existing statement/UVI artifacts, enforces production blockers,
  is idempotent for the same source request and appends the UVI `PUBLISHED` event in the same
  transaction. The renter API reads only stored publication rows and verifies the stored digest
  before returning bytes.
- Focused DB/API/RLS verification passes `132` tests. RLS covers `77` tenant tables, FK isolation
  covers `157` tenant-to-tenant edges and pre-context checks are clean.
- The mandatory boundary audit found no confirmed or suspected issue. Its only verification limit
  is that concurrent duplicate requests were reviewed through indexes/savepoints rather than a live
  stress test.
- `scripts/gate.sh full` is green with `2045` Python and `210` web tests. Ruff, formatting, strict
  mypy, purity, parity and pre-context checks pass.
- Preserve all five unrelated untracked `adjustment/` files. They remain untouched.

No implementation or review work remains in M10-R3. Push remains a separate decision.

## Previous checkpoint — M10-R2 technically complete

## M10-R2 closure — 11.09.2026

M10-R2 is technically complete. Source commit `92e18d5` was fast-forwarded into local `main` on
11.09.2026. Nothing was pushed.

- The named red window is closed; `.lokara-red` is absent.
- The spec lane pinned `M10-CTX-F01…F08`, migration `0042`, the minimal `/me.renterContexts`
  shape and `GET /renter/{tenancy_id}` overview. R3 publication moves to migration `0043`.
- Migration `0042`, `renter_scoped_session` and DB exports are implemented. The sole bootstrap
  function now returns typed SUBJECT/MEMBERSHIP/RENTER_TENANCY rows with exact six-table privilege.
  Every permissive PUBLIC account policy stops at renter context; SELECT is allowlisted only to the
  exact tenancy, its unit and building, and renter-context writes are refused.
- Database verification is green: `134 passed`; RLS covers `76` tables; FK isolation covers `152`
  edges. A real `0042 → 0041 → 0042` cycle passed. Fast gate is green under the sentinel.
- `scripts/check_pre_context_reads.py` is updated for the six-table/nine-policy boundary. Its `45`
  mutation tests pass, and the live checker is now clean.
- The API half is implemented in `apps/api/src/**`: shared bootstrap resolution in `deps.py`,
  `PathRenterSession`, minimal `/me.renterContexts`, exact `GET /renter/{tenancy_id}` overview,
  schemas and router wiring. Renter activation uses the moved shared resolver.
- Main-session focused verification passes `116` DB/API/checker tests. RLS covers `76` tables, FK
  isolation covers `152` edges, and the pre-context checker is clean. The mandatory boundary audit
  found no confirmed or suspected issue; its adversarial database probes were rollback-only.
- `scripts/gate.sh full` passes with `2021` Python tests and `210` web tests. Ruff, formatting,
  strict mypy, purity, parity, pre-context, ESLint and TypeScript checks are green. The first closing
  run exposed one strict-mypy fixture defect; the spec lane repaired and formatted it, and its `45`
  focused checker tests pass.
- Preserve all five untracked `adjustment/` files; they are unrelated.

No implementation or review work remains in R2. Preserve the five unrelated `adjustment/` files.
Never push without separate approval. M10-R3 publication is the next planned slice.

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
