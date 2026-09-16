# PLAN.md — Lokara roadmap

This file answers two questions:

1. What is built?
2. What comes next?

Build in the execution order below. The current program completes and approves all documentation
before any implementation resumes. Each later slice ends green. Engines and golden fixtures come
before UI. Dates are communication events, not planning inputs.

## Current state

- **M10-I2 technically complete and verified locally (16.09.2026).** Migration `0045` adds exactly
  three immutable account-scoped investment tables for versioned layouts, frozen inputs and their
  one-to-one results. Composite account FKs, correction chains, owner-only forced RLS, renter
  refusal, canonical PostgreSQL JSONB bytes and database-verified SHA-256 replay are enforced. The
  real `0044 → 0045` application, `109` focused persistence tests and `113` RLS tests pass; RLS
  covers `80` tenant tables and FK isolation covers `161` edges. The boundary audit is clean and
  the full gate passes `2259` Python and `258` web tests. The RED window is closed. The slice is
  uncommitted; M10-I3/I4 remain pending and every Page-07 production blocker remains active.
- **M10-R4 technically complete, verified and locally merged (`ed28f55`, 12.09.2026).** Additive migration `0044` stores
  source-derived immutable publication periods/months; the owner/list API projects them and the
  new `/renter/{tenancyId}` web route group provides activation, own-tenancy, statement and UVI
  screens with the approved copy. Focused DB/API/web tests pass `6 + 20 + 28`; RLS covers `77`
  tables, FK isolation `157` edges, both required reviews are clean and the full gate passes `2048`
  Python and `238` web tests. The owner follow-up `2e65aa9` adds the per-renter activation-code
  action to the Unit overview with owner/current-tenancy availability, one-time display and exact
  accessible party identification; its reviews are clean and the closing full gate passes `2052`
  Python and `246` web tests. Demo repair `4032889` exposes the same action in Portfolio Preview,
  provides a synthetic fresh seven-day spend-once activation flow without browser storage or live
  fallback, and keeps the same-session renter route reachable. Its reviews are clean and the full
  gate passes `2052` Python and `258` web tests. Lane I remains pending.
- **Owner UVI UI technically complete locally (`slice/uvi-owner-ui`, 11.09.2026).**
  Owner-only `/uvi` exposes live object/unit/tenancy/month selection, generation/reopen, scoped
  PDF access, visible production conflicts and preview write protection under `docs/04`.
  The live workspace timestamp crash and mobile overflow/clipped-button defect are repaired.
  Full gate passes 1967 Python and 210 web tests; production build and separate non-fresh demo
  path pass. Ordinary PDF fingerprint is unchanged. Bounded statement/UI and boundary reviews
  are clean; keyboard, 320–1920px responsive checks and 200% CSS scaling pass.
  Live demo generation correctly returns missing-configuration 422; successful browser results
  used intercepted responses, with backend generation/archive and PDF-render coverage in the
  existing suites. No monthly facts were invented. The slice is committed and locally merged into
  `main` as `f576a50`; nothing was pushed. `HANDOFF.md` records evidence and limits. No delivery, portal, legal/calculation
  or backend-schema expansion is included; every `docs/16` and M9 production blocker remains.
- M0 is complete. M1–M4 are built and green under their original scope, but are not yet fully
  verified against all Berkay specifications.
- The v4 migration is complete. The old TypeScript backend is gone. Mobile moved to M11.
- Composite foreign-key isolation and M5a identity/RLS are complete.
- Three earlier Page 01b fixes remain complete. Slice A now gives Page 01b technical implementation
  closure: all 34 fixture IDs execute through one orchestrator and the full and non-fresh demo gates
  are green. Emir approved Slice A and it was merged locally on 21.08.2026; open wording, cumulation and
  `verify-before-production` flags remain explicit.
- Berkay's Pages 01–08 and 01b exist. They are primary implementation specs, not background notes.
- Round 4 transcription was merged locally on 23.08.2026 as a documentation/fixture correction.
  It supersedes the
  stated Page-01b wording/cumulation, Page-02 classification, AfA K09, Eichfrist and § 559 details
  only where its source says so; all `Konvention`/`UNSICHER` labels remain. Berkay's round-five
  answer confirms that “51 → 62” was obsolete prose, not a CSV count. Repository verification
  corrects one claim in that answer: the workspace CSV parses to 180 data records (130 flagged,
  50 checked), not 179; physical line count is invalid because one field contains a newline and the
  file has no final newline. Page 07 planning still lacks its two named companion files.
- Page 01 is completely transcribed in `docs/08`/`docs/02` with a 24-ID data oracle and green
  consistency checks. Page 01b's settled implementation contract is technically closed by Slice A.
  Page 02 is merged in `docs/09` with an exact 32-ID data oracle; its production catalogue
  and engine integration remain open. Page 08 is completely transcribed, approved and merged with
  all thirteen executable cases. Page 05 is completely transcribed and approved with an exact
  24-ID data oracle. The UVI annex is approved and merged in `docs/16` with source-named data-only
  fixtures. Pages 03, 04, 06 and 07 are completely transcribed, approved and merged in `docs/10`,
  `docs/11`, `docs/13` and `docs/14`.
- Phase D1 is **complete; approved 17.08.2026; final reconciliation closed 18.08.2026**.
- Phase D2's `docs/15` review gate was approved and its slice merged on **20.08.2026**. The
  `docs/12` and `docs/16` review gates were approved and their slices merged on **21.08.2026**.
  The `docs/10` and `docs/11` slices and the final `docs/07` tax/archive reconciliation were
  approved and merged on **21.08.2026**. The `docs/13` and `docs/14` transcriptions were approved
  and merged on **21.08.2026**. D2 is complete.
- Phase D3 is **complete and approved 21.08.2026**. `docs/03` Appendix D is the single historical
  ledger, genuine source questions are in the current round-five question file, governance uses the
  post-D3 source model, and the seven retired files have no live dependency. D1-D3 now form the
  approved implementation baseline. Slice A is technically closed, approved and merged locally on
  21.08.2026. Slice B is complete and locally merged after the Round-4 Block-(c) correction;
  the separate §12 pure-engine result remains audit-only and the round-four transcription is
  preserved. No slice was pushed.
- M5 is complete and merged into `main` as `a748729`: secure bootstrap, backend
  membership/assigned-building authorization and the URL-based account chooser/switcher are
  shipped. Renter activation/portal remains M10; adviser profile, mapping and tax functions ship
  with M7. **All of M6 is locally merged into `main`**: M6-A
  (temporal advances, `d82abcc`), M6-B (finalized archives, `f578f2f`), M6-C1 (the pure matching
  engine, `8306b68`) and M6-C2 (bank persistence, the § 3.1 adapter and owner-scoped endpoints,
  `92e1318`), followed by M6-C3-0's migration-`0020` invariant repair. **M6-C3a is technically
  complete, development-synchronized and locally merged. C3b's three job entrypoints and C3c's
  landlord Zahlungen screen (`6995bc4`) are technically complete and locally merged, which closes
  M6-C and with it M6.**
- **G1 is technically complete and locally merged (`6c257f8`).** U1–U5 and M7-0 through M7-E are
  also locally merged. Local `main` is now at the consolidated checkpoint `5a1ee8b`,
  fast-forwarded from `development` with Emir's approval on 06.09.2026. The subsequent Zähler
  preview-data correction and owner UVI UI are included in local `main` commit `f576a50`; nothing
  was pushed.
  The long-lived local `development` branch integrates UI-04, deferred M7-F repairs and M9
  work, including all W1–W8 projections, migration `0025`, account-scoped jobs/API, immutable
  delivery evidence and `/waechter`. Integration alone does not close the other workstreams.
  M7-F remains deferred until after M10; its repair candidate still needs closing reviews and
  verification, and every M7 authority flag continues to block production output. M9 is technically
  complete and review-clean on `development`; it is not production-approved, and every source,
  legal, provider, UVI-artifact and checklist-catalogue blocker remains visible. UI-08 has partial
  automated/review verification, including the later `0040` boundary repair; its live-browser
  matrix remains outstanding. UI-00 through UI-02 retain their earlier evidence. UI-03 through
  UI-08 were implemented under the former direct implementation mode and now have checkpoint
  full/demo and focused review evidence; UI-07 is only the
  non-blocked demo core and remains partial. UI-05A adds the resumable statement workflow and
  migration `0028`; UI-05B adds the server-owned unit dashboard and migration `0029`; UI-07 adds
  the payment workspace and migration `0030`; UI-06 supplies the catalogue-backed cost workspace
  and migration `0031`; UI-08 supplies the meter workspace and migration `0032`. Nothing is pushed.
  Ruff, strict mypy, web lint, typecheck and the production build pass. The UI-05A migration and complete
  local draft → readiness → preview → finalization → correction/archive path were exercised against
  the preserved demo database, and the generated A4 PDFs were visually checked. Those direct-mode UI
  implementations still need complete per-step acceptance and the live interactive-browser
  accessibility matrix; checkpoint gate/review evidence does not establish full UI closure.
  A follow-up stability repair now requires the current optimistic draft version at finalization,
  advances that version when readiness changes, preserves unexpected server faults as errors and
  prevents M9 from treating a cover letter as the annual tenant statement. The compile-level checks
  remain green.
- **29.08.2026 M9 technical close is green and review-clean.** `scripts/gate.sh demo` passes with
  `1916` Python tests and `183` web tests; RLS covers `73` tables and FK isolation covers `144`
  account-scoped foreign keys. The final boundary audit and statement/UI re-review are clean. The
  ordinary statement fingerprint is unchanged at `c4eecb355d57cec620dfcb0134fc9141` / `149275`
  bytes, and no `.lokara-red` sentinel remains. M9 is technically complete on `development`, not
  production-approved. Its provider/scheduler, frozen UVI artifact, checklist catalogue,
  UVI-register/monthly-content/cadence and recorded legal/runtime audit blockers remain explicit.
  No commit, merge or push was performed.
- **05.09.2026 later checkpoint verification is green.** Full and non-fresh demo gates pass
  `1967` Python tests (zero skips) and `188` web tests against migration `0040`; RLS covers `73`
  tables and FK isolation covers `144` account-scoped edges. The ordinary statement retains all
  `22` golden assertions and `8` scale canaries, with unchanged fingerprint
  `c4eecb355d57cec620dfcb0134fc9141` / `149275` bytes. The `0040` repair has `20` rollback-only
  app-role regressions and a clean boundary re-audit. UVI API (`31`), PDF (`13`, including real A4
  rendering) and focused web (`19`) checks passed during the preceding repair session, and the
  final statement/UI re-review is clean. GAS/warm-water conversion, comparison provenance and
  layout repairs are implemented. The full UI live-browser matrix, UI-07's unfinished scope and
  all production/legal limits remain open. Emir authorized the local checkpoint commit on
  05.09.2026; promotion to `main` and push remain separate decisions.

---

## Berkay source registry

Every Page is a calculation or deterministic legal/product-rule source. A milestone may not use a
Page directly from `berkay-work/`. First transcribe it into the target `docs/` file and create its
golden fixtures. Existing docs are not assumed correct merely because they already exist.

| Source                      | Target                                                          | Fixtures                                                  | Current coverage and dependency                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| --------------------------- | --------------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Page 01 — Die Abrechnung    | `docs/08-statement-document.md` + data changes in `docs/02`     | `08-F01…F24`                                              | Full D1 source trace and exact 24-ID data oracle transcribed. Round five confirms unchanged fictional occupancy during partial self-use as a production-safe owner-burdening convention and supplies the extended landlord finding; implementation/copy regression is pending. Slice B and M6 ship the persisted calculation, bank/ledger flow and owner-only final archives. M10 owns renter portal publication. |
| Page 01b — Heizkosten & CO₂ | `docs/03-nk-heating-engines.md`; output rules also in `docs/08` | Every `01b-Fxx`, including suffix variants                | Full source trace and exact 34-ID orchestrator suite are green; Slice A was approved and merged locally 21.08.2026. Self-billing and MDL converge on typed readiness, findings, provenance, device evidence, separate unapplied risks and annual comparison; migration `0006`, adapter, API, web and PDF projections are included. U1–U5 now implement monthly DWD/UVI engineering, but technical closure does not approve flagged values, final block-(c) wording, risk cumulation, MDL ingestion or UVI production authority. |
| Page 02 — BetrKV catalogue  | `docs/09-betrkv-catalogue.md` + `packages/rules-store`          | `09-F01…F32`                                              | Slice C is technically complete (23.08.2026): full/non-fresh demo gates, unchanged PDF fingerprint and both reviews are green. `09-K01…K11`, `trinkwasseruntersuchung` and the administration-cost legal check remain production-blocking.                                                                                                                                                                                                                                                                                      |
| Page 03 — AfA               | `docs/10-afa.md`                                                | `10-F01…F34`                                              | Complete transcription approved and merged 21.08.2026. The normalized pure engine, server-owned rules and the AfA API/web boundary are locally merged and green under `scripts/gate.sh full`. Four CSV rows are `geprüft`; 42 remain `verify-before-production`. F11 selects 453,798 ct, while K09 authority, Weg B and the missing Gutachten share still block production.                                                                                                                                                     |
| Page 04 — Anlage V + DATEV  | `docs/11-tax-export.md`                                         | `11-F01…F16`                                              | Complete transcription approved and merged 21.08.2026. The pure export engine, rules, the strengthened `0024` model and the server-owned artifact/API adapter are locally merged and green under `scripts/gate.sh full`. Artifact bytes are generated by the server from domain inputs; a caller can never supply them. Seven register rows are `geprüft`; six and all affected runtime outputs remain blocked.                                                                                                                 |
| Page 05 — Wächter/Fristen   | `docs/12-guards-deadlines.md`                                   | `12-F01…F24`                                              | Complete transcription approved and merged 21.08.2026. M9 is technically closed. Round five confirms six-year water/heat periods, calendar-year expiry and no Heizkostenverteiler Eichfrist; Berkay will correct existing register rows 128/129 in place. The workspace CSV and historical `12-F05` fixture remain stale, so correction coverage is pending. Real delivery remains default-off and production-blocked. |
| Page 06 — Vertragsklauseln  | `docs/13-contract-clauses.md`                                   | `CLAUSES-F01…F19`                                         | Complete transcription approved and merged 21.08.2026 with the exact 19-ID data oracle, 17-row register surface and explicit ownership boundaries. No implementation exists. The source defines routing and risk rules, but not a complete clause-text/version catalogue or complete Mieterhöhung/Kündigung/Mahnung bodies; those missing sources still block M8.                                                                                                                                                               |
| Page 07 — Investment-KPIs   | `docs/14-investment-kpis.md`                                    | `14-F01…F14`, with an exact `KPI-*` alias map             | Complete transcription approved and merged 21.08.2026 with all 14 data-only fixtures, 18 register rows and explicit Page-03/Page-09/Page-11 boundaries. No implementation exists; flagged conventions, interest-source ambiguity and absent concept sources block production and M10.                                                                                                                                                                                                                                           |
| Page 08 — Bank-Matching     | `docs/15-bank-matching.md`                                      | `BANKMATCH-F01…F13`; round-five supplement pending         | The approved base and thirteen original executable cases are shipped. Round five now specifies tenancy-bound receivables, two structured-reference fields, deterministic component tie-break, owner-declared credit offset plus reminder suppression, event-triggered proposal reruns and identity/debtor-designation evidence. Their migrations, fixtures, engine and UI work are not implemented; the current multi-party 409 remains. |
| UVI + DWD annexes           | `docs/16-uvi.md`                                                | Source-named Block A–D2, DWD and Heizspiegel fixture maps | U1–U5 ship the technical calculation/archive/document path. Round five approves the final punctuation, three zero-divisor labels, interpolation label/footnote and neutral missing-prior sentence; the oracle and implementation are not yet updated. `R-UVI-01`/`R-UVI-02` are supplied but still absent from Berkay's authoritative CSV, so production C/D2 remains blocked. |

The new numbers 13–16 are assigned here. Page 01b stays in `docs/03` because that is the active
engine contract; it does not create a second competing heating specification.

### Mandatory inputs for every transcription

- The complete Page, including inputs, units, formula order, rounding, edge cases, worked examples,
  output wording and out-of-scope sections.
- The approved supersession and correction history recorded in the target doc and `docs/03`
  Appendix D. Retired correspondence is Git history, not a current input.
- Every matching `Rechtsstand-Register` entry, including `Rechtsstand`, source, legal/convention
  status and `verify-before-production` flags.
- `Anlagen/Non-Goals V1`; its section for the Page must remain out of scope.
- `Anlagen/README-for-Emir.md`; its arithmetic audit is evidence, not permission to remove source
  flags or provenance.
- For UVI: `Emir_Spec_UVI.md`, `DWD-Klimafaktoren-Import-Spec.md`, `LETZTER-STAND.md`, Page 01b and
  Page 05 W4.

### Source precedence and known conflicts

- `Rechtsstand-Register.csv` controls structured values and production flags. Approved docs preserve
  method corrections and supersession history. If an original Page/annex conflicts with the
  register or its approved doc, stop and resolve the authority gap; do not choose silently.
- F02's former Hu/Ho conflict is resolved by the authoritative CSV and preserved in approved
  `docs/03` decision 4 and Appendix C: Erdgas uses `0.201` Hu, `0.181` Ho and the documented `0.903`
  conversion relation, with CSV status `geprüft` and Rechtsstand `07/2026`.
- Page 03 says self-use reduces deductible AfA, not the AfA basis. This replaces stale wording in
  Page 06/Non-Goals.
- The DWD annex contains both `0.40–1.80` and an old `0.50–1.80` test boundary. Its update note also
  disagrees on April versus May 2026. Resolve both during `docs/16` transcription.
- The UVI annex's `RENTER` Membership role and largest-remainder wording conflict with the current
  identity and allocation models. Reconcile them; do not copy them into code.
- `Non-Goals V1` and `README-for-Emir.md` are dated inputs. They contain useful constraints, but
  later register or original-source corrections must be recorded in each target doc.

### Transcription gate

Each target doc must contain a coverage table mapping every source section and fixture ID to its
doc section and golden test. It must also record conflicts, superseded decisions, dependencies and
unresolved values. `spec-scribe` must mark that table complete before implementation begins. A
missing, conflicting or unverified value stays explicit; it is never guessed.

Current trace status after merged `docs/09`, `docs/15` and approved `docs/12` transcriptions:

- Page 01 has a complete source-section trace in `docs/08`, relevant normalized-model rules in
  `docs/02`, and a data-only oracle covering exactly `08-F01…F24`. Green coverage and arithmetic
  checks do not claim that the current application implements every branch.
- Page 01b has a complete source trace and an executable orchestrator suite over exactly 34 IDs.
  All warning, blocker, provenance, self-billing, MDL and annual-comparison obligations reach one
  durable result shape. Lower-level capability tests remain supporting evidence. Final wording,
  cumulation and register flags remain unresolved rather than being promoted to production truth.
- Page 02 now has a complete source-section trace, all 32 allocable and 11 non-allocable catalogue
  identities, and a data-only oracle covering exactly `09-F01…F32`. Its green checks include the
  approved Page-01 block-(b) reconciliation. This does not claim current rules-store or NK behavior.
- Page 08 has a complete section/register/correspondence trace and an exact executable oracle for
  `BANKMATCH-F01…F13`. Approved `docs/15` and its oracle resolve F03 as E12 and separate
  `isPotentialDuplicate` Review from silent same-ID re-import dedupe. Emir approved the
  transcription on 20.08.2026 and the slice is merged. Green data-only checks do not claim
  production behavior.
- Page 05 has a complete section/register/non-goal/correspondence trace and an exact data-only
  oracle for `12-F01…F24`. Round five resolves the five-/six-year question and the calendar-year
  end rule; the historical `12-F05` case and workspace register rows 128/129 remain stale until
  their dedicated correction slice/Berkay sync. Other Page-05 authority gaps remain explicit.
- UVI/DWD has a complete annex/Page/W4/register/non-goal/correspondence trace and source-named
  oracles for Blocks A–D2, all nine annual DWD PLZ values/import guards and all 18 Heizspiegel
  rows. U1–U5 now implement calculation, adapters, monthly persistence, owner generation, immutable
  archives and the separate renter document. The selected PLZ dataset's vendored offline lookup and
  PLZ-driven assignment are green, and the PLZ centroid is the production default. Three missing
  register rows and exact monthly content authority remain production-blocking.
- Pages 03, 04, 06 and 07 have complete approved and merged transcriptions. Page 04 includes the
  exact 16-ID data oracle and final `docs/07` tax/archive reconciliation. Page 06 includes exactly
  `CLAUSES-F01…F19`; Page 07 includes exactly `14-F01…F14`.
- Page 06's approved routing and risk transcription preserves all source gaps. Its missing complete
  clause-text/version catalogue and complete Mieterhöhung/Kündigung/Mahnung bodies need a separate
  legal source before M8 implementation.

### Three-phase documentation and correspondence-retirement gate

Source ownership stays explicit during all three phases:

- repository code, `CLAUDE.md` and this plan control shipped architecture and current status;
- original Pages/annexes and the authoritative register feed approved docs under the source
  precedence above;
- `docs/00`–`docs/08` record dependencies on material assigned by the source registry to
  `docs/09`–`docs/16`; they do not duplicate those detailed contracts.

The exact seven-file retirement scope and every section-level disposition live only in `docs/03`
Appendix D. Git preserves the deleted text. Approved docs, fixtures and the current round-five
question file preserve the durable rule, arithmetic, supersession and unresolved-source knowledge.

**Phase D1 — complete; approved 17.08.2026; final reconciliation closed 18.08.2026.** The completed
reconciliation changed documentation and data-only fixtures, not implementation source, and
followed this exact order:

1. Align `docs/03` with the restored single Slice A and record the unresolved DWD uncertainty as a
   dependency, without importing the future `docs/16` contract.
2. Complete the Page 01 transcription in `docs/08` and the relevant parts of `docs/02`.
3. Reconcile product promise and shipped status in `docs/00`.
4. Separate shipped from future architecture in `docs/04`.
5. Reconcile only `docs/01-tech-stack-and-decisions.md`. The separate
   `docs/01-tech-stack-explanations.md` is Emir-owned and outside D1 reconciliation: do not read,
   assess, use or modify it.
6. Reconcile `docs/06` with the shipped demo and documented limits.
7. Put only settled cross-cutting claims in `docs/07`; defer detailed Page 04 rules to `docs/11`.
8. Give `docs/05` an ordinary drift review only.

Every D1 calculation-document change, especially `docs/03` and `docs/08`, must land with a source
coverage table and golden fixtures. D1 contains no implementation. At the D1 exit, stop and inspect
the documentation and fixture diffs, fixture coverage, unresolved legal questions, docs-to-code
drift and the truth of this plan. Do not continue automatically; Emir reviews and approves D1
before D2 starts.

D1 also extracts every settled correspondence item owned by `docs/00`–`docs/08`. Its coverage tables
must identify the originating correspondence file and section, the destination, and whether the item
is current, superseded or still unresolved. Information assigned to `docs/09`–`docs/16` remains in
the retirement ledger for D2 instead of being duplicated into an existing doc.

**Phase D2 — complete; approved 21.08.2026.** `docs/09`–`docs/16` were created as separate
source-backed spec slices. The source registry above owns each Berkay Page-to-doc and fixture
assignment; do not duplicate that registry here. Every slice includes its complete coverage table
and golden fixtures and was reviewed without implementation. The dependency order was:

1. `docs/09`;
2. `docs/15`;
3. `docs/12`, then `docs/16`;
4. `docs/10` and `docs/11`, then final `docs/07` reconciliation;
5. `docs/13`;
6. `docs/14`, only after `docs/09`–`docs/11`.

During D2, every remaining settled item was extracted into `docs/09`–`docs/16` and their golden
fixtures. The correspondence stayed in place at the D2 exit and was retired only after Emir's D3
approval.

**Phase D3 — complete; approved 21.08.2026.** The correspondence was retired without losing
information:

1. Prove that every section of all seven files is mapped to an approved doc section, golden fixture,
   superseded-history note or unresolved item.
2. Keep one current round-five question file because genuine source questions remain. It contains
   no settled history, completed requests or implementation status.
3. Verify the target docs preserve every rule, correction, source reference, supersession,
   verification flag and unresolved risk. Preserve exact arithmetic in fixtures rather than copying
   long worked examples into prose.
4. Update `CLAUDE.md`, `PLAN.md` and `AGENTS.md` so they no longer require or link to the retired
   correspondence and so the approved docs, original Pages, annexes and register define the new
   source model.
5. Verify that no live repository reference depends on any retiring path and that no unresolved item
   is left only in Git history.
6. Delete the seven files together and inspect the complete deletion diff. Emir approved the
   retirement on 21.08.2026.

The approved `docs/00`–`docs/16`, their golden fixtures, the original Pages and annexes, and the
Rechtsstand register now form the complete implementation baseline. Later slices and milestones use
that baseline; they do not restart transcription or silently reinterpret a source. Berkay's open
Page 01b answers are not required to start Slice A. The exact block-(c) wording and reduction-
cumulation choice remain explicit source gaps and may not be guessed or presented as production-
approved behavior.

The completed documentation program satisfies all four conditions:

1. every existing doc is reconciled and every planned `docs/09`–`docs/16` file is approved;
2. every Page, annex, register row and correspondence section has a documented destination or an
   explicit unresolved/superseded disposition;
3. every calculation example that defines behaviour has a golden fixture, and every unverified
   value remains visibly blocked; and
4. the correspondence-retirement and governance-reference diff is approved with no information
   left only in the retiring files.

---

## 1. Execution order

The order closes legal billing exposure first. Missing UVI or CO₂ disclosure can each reduce the
heating claim by 3%. Missing consumption-based billing can reduce it by 15%.

Three bounded Page 01b fixes already precede the current sequence and remain preserved: R1/R5/K9
and Ho/Hu wiring, the Eigentümer residual, and § 5 Abs. 1 S. 3 CO₂ rounding. They are green but do
not replace the complete documentation or reconciliation gates.

| Stage | Status                                                                                                                                                 | Work                                                 | Required result                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D1    | **complete; approved 17.08.2026; final reconciliation closed 18.08.2026**                                                                              | Reconcile existing `docs/00`–`docs/08`               | Documentation and golden fixtures only; no implementation source changes.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| D2    | **complete; approved 21.08.2026**                                                                                                                      | Create source-backed `docs/09`–`docs/16`             | All assigned transcriptions are approved and merged, including `docs/14`; the final `docs/07` tax/archive reconciliation is approved. The phase added documentation and data-only fixtures, not investment implementation.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| D3    | **complete; approved 21.08.2026**                                                                                                                      | Complete extraction and retire Berkay correspondence | Single historical ledger in `docs/03`, one current round-five question file. Round 4 settled its answered decisions; Round 5 retains only its unanswered/source-delivery follow-ups and the external/legal-source gaps. Governance, permanent dependency guard and joint deletion remain intact.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| A     | **complete; approved and merged 21.08.2026**                                                                                                           | Reconcile M2 with Page 01b                           | All 34 Page 01b fixtures, persistence, projections, full gate, non-fresh demo gate and PDF review are green. The approved implementation keeps the two unresolved Page 01b choices explicit.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| B     | **complete; locally merged 23.08.2026**                                                                                                                | Reconcile M3–M4 with Page 01                         | Persisted calculation and extraction revalidated; Block-(c) renders only as the conditional owner-residual subline; full and non-fresh demo gates plus statement review are green. Finalization shipped in M6-B and the payment ledger in M6-C2.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| C     | **technically complete; locally merged 23.08.2026**                                                                                                    | Reconcile M1 with Page 02                            | NK eligibility, allocation, classification and rounding repairs are verified by full/non-fresh demo gates, unchanged PDF fingerprint and both required reviews. Page 02 remains production-blocked by `09-K01`–`09-K11`, the Trinkwasser route and the administration-cost legal check.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| M5    | After A–C                                                                                                                                              | Roles, URL context and switcher                      | **Complete.** Secure bootstrap, membership/assigned-building authorization and the URL-based account chooser/switcher are shipped on `main` (`a748729`). Renter portal is M10; adviser profile/mapping and tax functions are M7.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| M6    | **Original scope technically complete; round-five supplement specified, not implemented**                                                             | Bank, ledger and finalized statements                | M6-A through C3c remain locally merged and green for the original thirteen cases. Berkay's 11.09.2026 answer now requires tenancy-bound receivables, structured reference signals, deterministic ties, explicit credit offset/reminder handling and constrained identity/designation evidence. These changes are recorded in `docs/15` but have no migration, fixture, engine, API or UI implementation yet; the current multi-party 409 remains. |
| G     | **Technically complete, reviewed and locally merged 24.08.2026**                                                                                       | Shared guard foundation                              | Pure W1, W2 and W4 evaluators execute all nine selected Page-05 fixtures with explicit source identity, caller-supplied rule evidence and unresolved production blockers. No database, API, UI, scheduler or PDF integration.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| U     | **Technically complete, reviewed and locally merged 24.08.2026**                                                                                       | UVI comparison, calculation and document             | U1–U5 ship the approved calculation, DWD adapters, monthly inputs, isolated immutable archive, owner generation and separate German renter PDF. Production authority blockers remain explicit; scheduled delivery waits for M9 and portal publication waits for M10.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| M7    | **M7-0…M7-E technically complete; M7-F repair candidate integrated on `development` but deferred and unverified**                                      | Tax export and AfA                                   | The pure AfA/export foundation and Anlage-V paths retain their earlier branch evidence. M7-F still needs closing reviews and verification, and all flagged register values continue to block real output.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| M8    | **Lane A unblocked; lane B source-blocked**                                                                                                            | Document and letter engine                           | Lane A implements Page 06's B1–B8 arithmetic, E1–E11 and the signature gate as a pure engine against `CLAUSES-F01`–`F19`. Lane B — clause catalogue, composition, contract generation, action letters and SEPA capture — cannot start until the missing source-backed clause/version and action-letter bodies are supplied and approved. M7-F does not block either.                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| UI    | **UI-00 through UI-06 and UI-08 are implemented on `development`; UI-07's non-blocked demo core is implemented but partial; later full/demo and focused reviews provide partial verification; live-browser acceptance remains open** | Portfolio UI 00–08                                   | Execute UI-00, UI-01, UI-02, UI-03, UI-04, UI-05A, UI-05B, UI-06, UI-07 and UI-08 from the supplied UX specifications. UI-07 was pulled forward by Emir for the demo. Preserve legal, calculation, isolation and immutable-evidence contracts. Do not reuse or remove `slice/ui-00-layout-global`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| M9    | **Technically complete and review-clean on `development`; not production-approved**                                                              | Reminders, email and checklists                      | W1–W8, migration `0025`, account-scoped jobs/API, default-off delivery and `/waechter` are implemented. `scripts/gate.sh demo` is green with `1916` Python and `183` web tests; RLS/FK checks cover `73` tables and `144` account-scoped foreign keys. Boundary and statement reviews are clean, the ordinary statement fingerprint is unchanged at `c4eecb355d57cec620dfcb0134fc9141` / `149275` bytes, and no `.lokara-red` remains. Provider/scheduler, frozen UVI artifact, checklist catalogue, UVI-register/monthly-content/cadence and all recorded legal/runtime blockers remain production-blocking.                                                                                                                                                                                                                                                                                                                                                    |
| M10   | **R0–R4 and I0–I2 technically complete and verified; I3–I4 pending**                                                                                    | Portals and investment                               | Renter activation, context, overview, immutable publication, source-derived display metadata and the renter portal screens are implemented through migration `0044`. The approved `docs/14` executable fixtures, pure investment engine and immutable persistence are green through migration `0045`; API, entitlement, cockpit UI and Bank-PDF remain pending.                                                                                                                                                                                                                                                                                                                                                                                                                |
| M11   | After M10                                                                                                                                              | Native apps, billing and load test                   | Ship the Expo mobile app against the same FastAPI API, Stripe web billing, RevenueCat mobile billing and the Locust load test.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| M7-F  | **After M10; integrated repair candidate remains required before programme/production closure**                                                        | Finish tax/AfA review and repair                     | Revalidate the boundary repairs, complete statement/docs review, rerun focused and closing verification, and preserve every legal/runtime production blocker.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |

### Slice A — progress and closure

Progress preserved in the current implementation baseline:

- The complete source trace and 34-ID data oracle are transcribed. The three earlier Page 01b fixes
  remain green for their bounded scope.
- `01b-F28b` gross rescaling is executable and green: exact gross quotient, accepted one-cent source
  residual and owner reconciliation.
- Device and segmented-reading capabilities are green at `716f741`: H5 typed device/span
  aggregation and H6 hand-off cover `F01/F27`, `F15`, `F16`, `F17` and `F22`. Exact WE-03-only
  `F18` reproduces Berkay's authoritative cents.
- Plant/CO₂ applicability and source-state capabilities are green at `89db9e0` for `F07–F10` and
  `F23`: building type, fuel, connected state, proof-gated protection/exclusion,
  module/disclosure switches and non-blocking R8-value warnings.
- The self-billing capability RED spec is committed at `a350f98`. Its implementation in
  `self_billing.py` and `__init__.py` covers H1/H1a/H1b/H3/H4 capabilities for `F11–F14`, `F19`,
  `F20` and `F24`. Main-tree verification passes the fast gate: formatting, lint, strict mypy,
  engine purity, agent parity and 307 pure-package tests.
- F02's authoritative CSV factor values/reference behaviour, missing-cost refusal, end-to-end
  warning/provenance and separate § 7 Abs. 4 risk output are green. The K4 production flag remains.

Slice A's closure requirements are satisfied in the approved implementation:

1. H0–H7 are integrated into executable end-to-end Page 01b fixtures, including every open
   `01b-Fxx` obligation.
2. One shared warning/readiness/provenance/risk result and channel covers every open obligation:
   `F02` derived-mass warning/provenance/risk, `F12` fallback warning, `F17` estimate provenance,
   `F20` disclosures, `F21` hard stop, `F23` plausibility projection, `F24` coverage warning, `F25`
   separate unsummed risks, `F26/F26b/F26c` thresholds, and `F30/F31` risk/output. No isolated
   warning primitive counts as fixture closure.
3. The pure MDL net/gross/control-sum boundary is executable for `F28a`, `F28b`, `F29` and `F30`.
   Slice A/M2 owns pure, branch-aware MDL validation/result behaviour: no second deduction in the
   net branch, exact gross rescaling, the correct control-sum reference for each branch, `F29`'s
   blocking result and `F30`'s risk result. Slice B/M3 later revalidates OCR confirmation,
   adapter/API blocking and statement projection; Slice A proves the pure behaviour without pulling
   those M3 integration obligations forward. Gross rescaling is not a scaffold for the net path.
4. H8 consumes normalized annual DWD factors, enforces `0.40–1.80`, keeps WW raw and labels both
   missing-factor and no-prior fallbacks. Monthly import/scheduling and UVI remain outside Slice A.
5. Full and demo gates pass, the before/after PDF fingerprint is recorded, and statement review has
   no unresolved Slice A findings.

Verified closure evidence: 37 orchestrator tests exercise the exact 34-ID register; the focused
Slice A suites pass 363 Python tests plus the API and web projections; the UTF-8 full gate passes
722 Python and 31 web tests; the non-fresh demo gate passes. The PDF fingerprint changed from
`34e4f8bda4658f1cc233b38e1c2a8fad` to `a45fa3d1e3d69957948e58885b4ab797` and the reviewed output is
three clean A4 pages. Emir approved Slice A and it was merged locally on 21.08.2026.

The D1–D3 documentation and correspondence-retirement gates precede the A–C implementation
reconciliation gate. Do not resume M5 or start later feature work until D1–D3 are approved, A–C are
spec-closed and the full and demo gates pass. The three earlier Page 01b fixes remain complete only
for their named scope; they do not count as full Page 01b coverage. UVI implementation is no longer
blocked by the co2online licence. G1 and Slice A are technically green and locally merged; the
U-specific source gaps remain. A real § 6a output must still be checked later.

Slice A started without Berkay answers and keeps both choices visible: current structural block-(c)
copy remains provisional, and every 3-percent risk is shown separately without an automatic sum or
deduction. Neither affected output nor flagged register value is production-approved.

### M7 value warning

The following remain `verify-before-production` placeholders:

- Weg B;
- all Anlage-V line numbers;
- SKR03/SKR04 accounts;
- DATEV EXTF parameters;
- K09's month-granular use-change convention, although `10-F11` technically selects 453,798 ct;
- three BFH case numbers marked `ZITAT UNSICHER`;
- the Page 04 ten-day-rule BFH citation.

The computation paths may be built. Nothing using these values may be sent to a real Steuerberater
or Finanzamt until each value is confirmed.

---

## 2. Hard rules

1. **No calculation without complete transcription.** Follow the Berkay source registry and its
   coverage-table gate. Transcribe first, create every golden fixture, then implement. Never invent
   a legal value. Read register counts and flags from the CSV with a parser; never copy a total into
   the plan as a separately maintained target.
2. **Finish the documentation program before implementation.** D1–D3 run without implementation
   source changes. Every implementation stage begins only from the approved documentation baseline.
3. **Keep the demo path green.** Every milestone re-verifies database → migration → seed → statement
   → PDF. Fix or revert any break before continuing.
4. **Tag green milestone states.** Use `demo-green-<n>` only after the required gates pass.
5. **Finish one milestone or bounded slice at a time.** Do not merge half-built subsystems.
6. **Keep external services stubbed behind adapters** until their integration slice. No real keys or
   vendor SDKs in engines or domain code.
7. **Docs and code must agree.** A documented rule that code does not follow is a defect.

---

## 3. Built foundation and reconciliation status

### M0 — Foundations and scaffolding ✅

Built:

- Bun/Turborepo TypeScript workspace and uv Python workspace;
- Next.js web app, FastAPI API and shared packages;
- Ruff, strict mypy, pytest, ESLint, TypeScript checks, Vitest and CI;
- themed Tailwind and shadcn/ui design system;
- SQLAlchemy models, Alembic migrations and Supabase/Postgres RLS;
- API auth dependency and typed web client;
- temporal core schema with integer-cent money;
- Playwright PDF service.

The Expo mobile skeleton is not part of the completed foundation. It moved to M11.

### M1 — Operating-cost engine 🟡 Slice C technically complete; Page 02 production-blocked

- Pure `packages/nk-engine`.
- Day-weighted allocation, vacancy handling and largest-remainder reconciliation.
- DIRECT, MEA and other allocation keys.
- Per-period `AllocationKeyAssignment`; changing a key does not delete entered data.
- Canonical €1,200 golden fixture passes exactly.

**Technical closure evidence (23.08.2026):** Slice C proves the engine against approved `docs/09`;
every `09-Fxx` fixture passes, confirmed differences are resolved, full/non-fresh demo gates and
required reviews are green, and the PDF fingerprint is unchanged. This does not clear
`09-K01`–`09-K11`, the Trinkwasser route or the administration-cost legal check.

### M2 — Heating and CO₂ engine 🟢 Slice A complete and approved

- Pure `packages/heating-engine`.
- HeizkostenV §§ 7/8, § 9 and § 9a.
- Degree-day renter-change allocation.
- CO₂ 10-step landlord/renter split.
- Versioned ratios, tables and `Rechtsstand`.

**Approved closure evidence:** every `01b-Fxx` fixture passes through the shared orchestrator, the
three earlier bounded fixes remain correct, and API/web/PDF print the verified split with
`Rechtsstand`. Emir approved Slice A on 21.08.2026; its provisional wording and separate-risk
boundaries remain unchanged.

### M3 — Web vertical slice and PDF 🟢 Slice B complete; locally merged 23.08.2026

Built:

- URL-scoped landlord portal under `/a/{accountId}`;
- membership check plus RLS for account access;
- `/me`-derived navigation and demo loading;
- buildings, units, tenancies and occupancy timeline;
- cost entries, allocation keys, meters and readings;
- statement creation and NK/heating PDF download;
- autosave so leaving a flow does not lose entered data;
- statement inputs from persisted rows, not fixture constants.

**Slice B status:** persisted path is green and locally merged. The original demo remains green and
all `08-Fxx` statement fixtures pass. The Round-4 Block-(c) correction and M6-B owner-only final
archives are complete; renter delivery/portal remains M10.

### M4 — Document extraction demo 🟢 Slice B complete; locally merged 23.08.2026

- Shared upload → prefill → confirm flow.
- Stub Vision adapter with canned invoices.
- Per-field confidence and API-owned review threshold.
- Extraction writes nothing until the ordinary cost form is confirmed.

Not included:

- automatic allocation-key choice, which needs the Slice C BetrKV catalogue;
- Beleg persistence, file hash and object storage.

**Slice B status:** its confirmed extraction path feeds the Page 01 statement model without
bypassing review or tenant-document isolation. The Round-4 Block-(c) correction is complete.

### FK isolation slice ✅

- All 17 tenant-to-tenant foreign-key edges carry `account_id`.
- Parents expose `UNIQUE (id, account_id)`.
- Nullable links use `MATCH SIMPLE`.
- `building_assignment` carries its own structurally consistent `account_id`.
- `scripts/check_fk_isolation.py` guards future edges.

### M5a — Identity schema and RLS ✅

- Person, Account, Membership, Landlord, Renter and SelfUsePeriod model.
- Roles live on Membership. Account shape lives on Account.
- `landlord`, `self_use_period` and global `person` isolation are tested.
- Person visibility uses Membership-based RLS and denies reads without context.
- RLS coverage and the demo path are green.

---

## 4. M5 — complete

### Locally merged bootstrap foundation (`1300db1`)

- JWT auth carries only the verified Person subject.
- Expiry, issuer, exact audience and authenticated role are validated.
- Account context is never trusted from the token.
- Its migration is `0014`, following Slice C's `0013`.
- `GET /me` returns all live account contexts from the database.
- The token-scoped account session and `/demo/summary` are retired.
- The demo summary now uses `/a/{accountId}/summary`.
- The pre-context checker and 40 mutation tests enforce the boundary.
- Full and non-fresh demo gates are green (993 Python tests); the boundary audit has no finding.
- The statement review found two pre-existing Page-01 document/PDF mismatches (the output title/scope
  and heating demo totals). It found no M5 UI regression; reconcile those separately before claiming
  the current PDF is a formal tenant statement.

This work added no new dashboard, portal or account switcher.

### Locally merged backend role and building-scope guard (`99ac47e`)

- `OWNER` retains the current owner-portal surface.
- `EMPLOYEE` can reach only assigned buildings; zero assignments expose no buildings.
- `TAX_ADVISOR` may use `/me` but is denied all current `/a/{accountId}/…` owner-portal routes.
- Every current building-scoped route resolves the owning building before work; inaccessible buildings
  and nested resources return `404`.
- Employee building lists are filtered. Account-level routes use a single assignment, return no data
  for zero assignments, and require an explicit building for multiple assignments.
- The API fixtures cover role, revocation, cross-account and nested-resource cases, and prove the
  current OpenAPI request surface cannot write `renter.person_id`.
- The full gate and boundary audit are green. No migration, switcher, renter activation, tax route,
  web or PDF change is included.

### Locally merged account chooser and switcher (`a748729`)

- `/` enters a sole `OWNER` or `EMPLOYEE` context. With multiple contexts it shows every live
  `/me` context as a URL link; a sole `TAX_ADVISOR` context is chosen deliberately.
- The portal shell shows the same ordinary-link switcher only for multiple contexts. The URL remains
  the authorization input, so tabs, reloads and bookmarks are re-authorized per request.
- `TAX_ADVISOR` shows the German preparation state, never owner navigation or routed owner content.
  Adviser profile, account mapping and tax functions remain M7.
- `EMPLOYEE` keeps the assigned-building surface but has no building-create or demo load/reset UI;
  zero-data states state that no object is assigned. Server-side role and building checks remain the
  authorization boundary.

M5 is complete and merged on `main`: roles behave correctly; every nested building route
verifies its URL context; multiple account contexts switch by URL and are re-authorized per request;
the pre-context checker stays green; and no current API route writes `renter.person_id`. Renter
activation, renter URL context and renter portal authorization are M10 work. C3b is technically
complete and locally merged, and so is C3c.

---

## 5. Later milestones

### M6 — Bank, ledger and finalized statements

**Approved-spec prerequisite:** D1's `docs/08` and D2's `docs/15`. If bank matching is deferred,
`docs/15` does not block the remaining ledger and statement work.

#### M6-A — temporal advances and confirmed owner preview

**Status:** implementation and review closed on 23.08.2026; merged as `d82abcc`.

M6-A replaced the `tenancy.advance_payment_cents` scalar with the account-scoped,
composite-FK-protected `AdvancePaymentPeriod` append-only Soll schedule, and added `AdvancePayment`
money evidence, `AdvanceAllocation`, `AdvanceReconciliation` and its allocations. Migration `0015`
backfills every existing tenancy as one open-ended period at `tenancy.valid_from` and drops the
scalar; `packages/db/tests/test_m6_advance_models.py` asserts the column is gone. It also ships the
confirmed owner advance preview, its API projection and the RLS boundaries for every new table.

**Implementation acceptance:** contractual Soll is temporal, never a current-value scalar. Accepted
money evidence is immutable and reversals are positive rows carrying a direction, never edits.
Reconciliation requires an explicit confirmation; an unconfirmed period yields a preview only.

**M6-A closed when:** the temporal schedule replaced the scalar with a verified backfill, actual
advances are separable from contractual Soll, and the owner preview is confirmed before any Saldo
branch is frozen. This work is complete — do not reopen it as M6-C scope.

#### M6-B — finalized, isolated statement documents

**Status:** implementation and review closed on 23.08.2026. M6-B is deliberately limited to
technical finalization archives: immutable statement snapshots,
database PDF bytes/hashes, one owner overview plus independently rendered eligible-tenancy documents,
Saldo settlement records, versioned delivery addresses/instructions and correction-only versioning.
It preserves every `verify-before-production`/`Konvention` label and does not enable renter delivery,
portal publication, email, bank matching, finAPI or legal-production approval. The existing live
landlord preview/demo PDF remains outside this renderer.

**Implementation acceptance:** owner-only atomic finalization requires confirmed reconciliation for
every eligible tenancy (explicit zero accepted); a failure leaves no partial archive. Positive timely
Saldo creates a receivable, negative creates a credit/refund obligation, zero creates neither, and a
late positive is only `Rechnerischer Saldo` without an explicit recorded exception. Corrections name
the latest final version and append `vN+1`; archived snapshots and bytes never change. Zero-day
tenancies are excluded from tenant documents/settlements and footnoted in the owner archive. Required
fixtures are `M6B-F02`–`F04`, `F10`, `F14`, `F16`–`F19`, `M6B-IMM`, `M6B-CORR` and `M6B-ISO` in
`docs/08`.

- Keep finAPI stubbed behind the bank adapter until a separate provider-integration slice.
- C3a joins the matching engine to persistence and is technically complete,
  development-synchronized and locally merged.
- Add background job entrypoints for bank sync, 180-day reconsent cleanup and deadline watchers.
- Add the landlord _Zahlungen_ confirmation/rejection screen without inventing manual assignment.
- Deliver/publish renter documents only after the separate M10 portal and legal-production work.

**M6-B closed when:** confirmed advances produce frozen Saldo branches; owner-only finalization is
immutable and reproducible; owner and isolated tenant archives are separately rendered; zero-day
tenancies are excluded and footnoted. **M6 is technically complete and locally merged**: C3a is
technically complete, development-synchronized and locally merged, and C3b's job entrypoints and
C3c's Zahlungen screen are technically complete and locally merged.
Temporal contractual advances are **not** open work: M6-A shipped them. Delivery and the renter
portal are M10, not M6.

#### M6-C — bank matching, payment ledger and the Zahlungen screen

**Status:** technically complete; locally merged 24.08.2026. C3a is technically complete,
development-synchronized and locally merged into `main`; C3b and C3c are technically complete and
locally merged.
**Approved-spec prerequisite:** `docs/15`, whose
thirteen `BANKMATCH-F01`–`F13` fixtures are the acceptance surface. Three bounded slices:

- **M6-C1 — complete and merged.** Pure `packages/matching-engine`: § 4 signals and decision
  order, § 5.1 designation/FIFO/§ 367 settlement, § 5.2 principal split and § 5.3 reversal. All
  thirteen fixtures run through real code as 30 tests. The package needs the standard library
  only — not even `lokara-domain` — and refuses `float` at the single import boundary.

  **The merge gate is closed.** `scoring.py::_end_to_end_signal` had bound § 4's "stored
  reference" to `profile.payment_code`, but §§ 3.2–3.3 define no such field — an invented
  matching convention with no source, exercised by zero fixtures, and +15 moves a candidate from
  Unmatched to Review. The signal now returns 0 with the gap recorded in its docstring, in
  `docs/15` § 4 and in `FRAGEN-an-Berkay-05.md`. `docs/15`'s status lines were updated in the
  same change. The § 5.3 reversal lookup is a different mechanism, is source-backed and
  fixture-covered by `F06`, and was not touched.

- **Workflow correction — done and merged.** The short process slice `PLAN.md` put before M6-C2,
  from what M6-C1 cost:
  1. The stop gate cannot express "RED on purpose". `CLAUDE.md` § 10 forbids one agent from writing
     both a test and its implementation, so every calculation slice has a mandatory red window —
     and the gate rejects turn-endings inside it with an identical error dump. Measured over the
     session transcripts: **9 main-session blocks plus 2 in subagents during the M6-C1 session
     alone**, and roughly 47 across all sessions. **12 of the 19 subagent blocks were
     `spec-scribe`**, the one role whose deliverable is a _failing_ fixture — the gate is fighting
     the rule that creates the red window. **Shipped:** `.lokara-red` names the slice and the
     reason; `scripts/check_red_sentinel.py` reports it, `gate.sh fast` prints every failure and
     exits 0 while it exists, and `full`/`demo` treat it as a hard failure, so merging requires it
     absent. It is gitignored, an anonymous sentinel is rejected, and
     `scripts/tests/test_red_sentinel.py` proves the check can fail.
  2. Agent briefs must name their files. Subagents are ~39 % of all token spend, and 95 % of that
     is context re-read, so cost is turns × context, not brief length. Measured per run:
     `spec-scribe` 84 turns / 9,7 M tokens, `app-implementer` 93 / 8,7 M, `engine-implementer`
     66 / 5,4 M, `docs-reconciler` 143 / 11,9 M. The lever is naming the exact files, fixture IDs
     and acceptance command up front instead of letting an agent discover them. **Shipped** as
     `AGENTS.md` § 4 "Brief and turn discipline", including a ~40-turn stop condition and the
     measured baseline a later change is judged against. It is a rule, not a gate; `gate.sh fast`
     itself runs in 1,5 s and is never the cost.

  Two further fixes were measured and **rejected**; do not rediscover them as good ideas.
  Skipping the gate for read-only agents fixes nothing: `boundary-auditor`, `statement-reviewer`
  and `docs-reconciler` were blocked zero times in 16 runs. Downgrading the reviewers to a cheaper
  model saves about 3 % — the three read-only reporters cost 53 M of roughly 1,8 B tokens — and
  `statement-reviewer` exists to catch the de-scaling defect class that the passing test suite
  cannot see.

  Not in scope: the agent roster. Six agents with distinct lanes is not the problem, and the
  test-author/implementer separation stays — it found the § 4 stored-reference defect that two
  readings of `docs/15` had missed, and it caught the main session's own edit to the acceptance
  fixture. An earlier claim that worktree copy-back silently reverted a `scripts/gate.sh` edit was
  **wrong**: the main session had `cd`-ed into an agent worktree and never returned. Worktree
  copy-back is not known to have failed; do not act on that claim.

- **M6-C2 — complete.** The nine tables (`bank_account`, `bank_transaction`, `receivable`,
  `renter_matching_profile`, `iban_history`, `match_proposal`, `match_confirmation`,
  `payment_ledger_entry`, `payment_allocation`) ship with migration `0017`, FORCEd RLS and
  composite `(id, account_id)` FKs; `check_rls_coverage` reports 38 tenant tables and
  `check_fk_isolation` 62 edges. `packages/adapters/.../bank.py` is rewritten to the § 3.1
  contract with `BANKMATCH-F10` executed at the import boundary, and `StubBankGateway` now honours
  its `bank_account_id`. Owner-scoped endpoints and the Page-01 handoff (`F12`, 24,500 cents copied
  exactly, not repeatable per statement) are in `apps/api/.../routers/payments.py`.

  Two limits ship with it. The **Zahlungsfrist is asked for, never defaulted**: `docs/08` flags it
  `verify-before-production`, the register records no statutory deadline, and the 30-day figure is
  a `Konvention` — so the handoff refuses without an explicit due date. The **§ 4 stored-reference
  signal stays inert**: `receivable.stored_reference` exists as a column, nothing writes it, and
  turning the signal on without Berkay's answer restores the invented convention M6-C1 removed.

  Migration `0018` narrows the receivable component-sum check to `category = 'rent'`. An
  `nk_nachzahlung` has no rent, garage or advance component, and § 5.2 makes the cost of getting
  this wrong concrete: the paid NK-advance component feeds the annual actual-advance total Page 01
  consumes, so parking a Nachzahlung there to satisfy the arithmetic would double-count it as an
  advance that was never paid.

  **Boundary audit, 23.08.2026 — six HIGH findings, all fixed in migration `0019`.** `0017` got
  account isolation right and constrained nothing _inside_ one account. A `payment_allocation`
  could settle renter 2's debt from renter 1's cash (§ 6: "a match never moves money between
  renters"); an allocation could exceed the cents its entry carried, and a negative component
  cancelled inside the sum check and then fed Page 01 a negative advance; a `REVERSAL` could be
  positive, name no original, or be filed twice, so `F06` nets to +216,000 instead of zero;
  `iban_history` was freely rewritable and needed no confirmation, against § 3.3 and `F09`;
  `bank_transaction` and `match_proposal` were documented immutable and were not; and the
  receivable's § 367 projection columns could contradict `status`. `0019` adds the parent-scope
  triggers, the allocation cap and non-negativity, the reversal shape, IBAN provenance and
  versioning, append-only on the evidence tables, and the missing uniqueness.

  Two router defects came with it: the `F12` handoff took the first `TenancyParty` and silently
  discarded the rest, so a joint tenancy attributed the Nachzahlung to an arbitrary spouse; and the
  supersede path let a correcting `v2` bill the same renter again. Both now refuse rather than
  guess.

  **Why all six shipped:** `check_rls_coverage` accepted "the table is named in the isolation
  test", which an `import` line satisfies. All nine tables passed while not one had a
  cross-account **write** assertion — two of the four tests ran on the owner engine, which
  bypasses RLS. The check now requires a `WITH CHECK` clause and a real write assertion, and
  immediately found three more tables predating this slice (`cost_entry`, `heating_cost_entry`,
  `allocation_key_assignment`), whose assertions were added rather than grandfathered.

  **Recorded, not fixed — M6-C3 inherits these.** `receivable.source_type`,
  `payment_ledger_entry.ordering_version` and `match_proposal.convention_version` are
  unconstrained free text, and `CLAUDE.md` § 6 puts versioned legal rules in the rules store, not
  in a caller-supplied string. `Receivable.source_id` is polymorphic, so it carries no composite
  FK and `check_fk_isolation` cannot see it — the traceability § 147 AO needs is asserted by a test
  but not guaranteed by the schema. The adapter's `BankTransaction` dataclass has no
  `__post_init__`, so a `float` reaching `amount_cents` from an `Any`-typed payload bypasses the
  refusal in `cents_from_provider_amount` and silently truncates in Postgres. The list endpoints
  have no pagination. `require_owner` reports "Only owners may create buildings" on payment routes.
  `bank_account.consent_expires_at` is stored and never read, though a PSD2 consent expiry is a
  legal precondition for an AIS pull. `0017`'s downgrade raises, so a CI job that resets by
  downgrading wedges there.

- **M6-C3-0 — invariant repair. Technically complete and locally merged 24.08.2026.**
  A `boundary-auditor` pass over `0020` and the slice diff — the one the previous handoff
  said had never run — found **two HIGH and five MEDIUM** defects in the repair itself.
  The HIGH pair mattered most. **H1:** the first `enforce_payment_allocation_renter` draft
  resolved the entry's renter with `IF match_proposal_id … ELSIF reverses_entry_id`, and
  `ck_payment_ledger_reversal_shape` does not forbid a REVERSAL from carrying its own
  proposal — which `docs/15` § 5.3 says it legitimately may, being a distinct provider
  movement. So a reversal's own proposal shadows the reversed payment's renter and renter
  1's returned cash could settle renter 2's debt. That is the same sentence `0019` and `0020`
  were each written to enforce, missed for the third time. **H2:** none of the 21
  plpgsql trigger functions pinned `search_path`, and every parent lookup was unqualified;
  `lokara_app` holds TEMP and `pg_temp` resolves before `public`, so a
  fabricated `receivable` or `payment_ledger_entry` answers any trigger while the foreign
  keys and RLS still bind the real table. It also breaks by accident: any future job that
  creates a temp table with one of those names disables the guard for its whole session.

  Emir's scope decisions, 23.08.2026: fix all six findings, amend `0020` in place rather
  than stack an `0021`, and harden **all 21** trigger functions, not only this slice's
  nine — the twelve predating ones guard statement finalization, archive hashes and the
  M6-A advances, and carry the identical hole.

  **Closure evidence, 24.08.2026.** The amended `0020` is proved from an empty disposable
  database: revision `0020`, all 21 functions hardened, six qualified replacement bodies,
  three `AFTER` triggers, R13–R18 green, 89 focused tests green and all 38 RLS tables clean.
  The verified function/trigger hand-delta and Emir-approved missing CHECK are applied to
  development. UTF-8 full and non-fresh demo gates are green with 1,143 Python and 43 web
  tests; the PDF is unchanged at `88eb8434eda65f8d7ff82826fc837a58` / 149269 bytes.
  `.lokara-red` is closed and `lokara_amend_check` is dropped. The slice is locally merged;
  nothing was pushed.

- **M6-C3-0 — the original entry, superseded above.**
  A second boundary audit, run over `0019` before anything was built on its triggers, found four
  HIGH defects. **The fourth parent-scope trigger `docs/02` § 6 documents had never been written**,
  so an allocation could still settle another renter's debt — the one rule `docs/15` § 6 states
  outright, and the defect the whole `0017` audit was about, re-documented as fixed. A learned IBAN
  could be minted for the wrong renter from a _rejected_ confirmation. `open_costs_cents` and
  `open_interest_cents` had no upper bound and no relation to `open_cents`. And
  `check_rls_coverage`'s new write-assertion requirement was **vacuous for all nine tables**: it
  split the suite only at method indentation, so the module-level `m6c2_bank_rows` fixture — which
  names all nine and writes on the owner engine, asserting nothing — was glued onto an unrelated
  statement test that carried both markers.

  Two further findings were design contradictions, not oversights. `0019`'s blanket non-negative
  check rejected `reversal.py`'s own compensating rows while `abs(amount_cents)` granted a −108.000
  reversal a +108.000 budget, so a reversal could not be recorded at all; and
  `uq_iban_history_active` made the `F07` shared-IBAN state unrepresentable, though § 3.3 requires
  it to exist and yield Review — two spouses on one joint account.

  Migration `0020` repairs all of it with twelve fixtures (`M6C3R-R01`–`R12`). The repaired
  coverage check immediately named four more tables predating the slice — `building_assignment`,
  `confirmed_cost_classification`, `membership`, `operating_cost_agreement` — whose apparent
  coverage was foreign-key isolation, not `WITH CHECK`; their assertions were added rather than
  grandfathered.

  **Two of the audit's own proposed fixes were rejected after checking them against the code.**
  It offered `costs + interest + principal = open_cents`; `settlement.py` computes
  `open_after = open_cents - principal`, so `open_cents` **is** the open principal and that sum
  would have contradicted the fixture-verified engine — the constraint is equality. It also
  proposed requiring a reversal to share its original's `bank_transaction_id`; all twelve existing
  reversals do, but that is the test graph's shortcut, and § 5.3 makes the return a distinct
  movement resolved by E2E reference. An audit finding is evidence, not a patch.

- **M6-C3a — matching service and owner API. Technically complete, development-synchronized and
  locally merged 24.08.2026.** Migration `0021` adds
  deterministic proposal ranks, nullable legacy-compatible allocation projection snapshots,
  confirmed/Auto PAYMENT evidence and deferred ledger/allocation reconciliation. A new
  `matching_service.py` persists all thirteen `BANKMATCH-F01`–`F13` paths and exposes exactly five
  owner-scoped capabilities: matching-profile upsert, immutable match execution, grouped proposal
  list, final decision and immutable payment-ledger list. The acceptance files are
  `apps/api/tests/test_m6c3a_matching_service.py` and
  `packages/db/tests/test_migration_0021_m6c3a.py`; both are green with the implementation.
  The final amended `0021` is verified from the disposable `lokara_c3a_check` database. Development
  now matches it exactly after one validated transactional hand-delta: column types, constraints,
  trigger timing/deferrability, hardened function definitions and hashes are identical. Evidence
  counts and 68 legacy Auto confirmations are unchanged. C3a excludes jobs, the _Zahlungen_ screen,
  pagination, manual assignment and automatic later use of renter credit.
- **M6-C3b — job entrypoints. Technically complete 24.08.2026.** Three account-scoped functions in
  `apps/api/src/lokara_api/jobs.py` behind `lokara_adapters.SchedulerPort` and its in-memory
  `StubScheduler`: `sync_bank_transactions`, `expire_bank_consents` and `watch_deadlines`, with
  `run_for_accounts` opening one `account_scoped_session` per caller-supplied id. Redis, Arq and
  Celery remain uninstalled; the port only answers which jobs are due. The `docs/15` § 3.1 dedupe
  rule moved out of the owner endpoint into `bank_sync.import_transactions`, which both callers now
  share and which refuses a pull without a standing PSD2 consent — closing the M6-C2 finding that
  `consent_expires_at` was stored and never read. Sync matches what it imported in
  `(bank_booking_date, provider_transaction_id)` order, one `begin_nested()` SAVEPOINT per
  transaction, so a refusal is bounded to its own movement; a § 4 `AUTO_MATCH` therefore settles on
  a schedule while `NEEDS_REVIEW` still moves no money. The two reporting jobs write nothing and
  delete nothing: `bank_transaction` stays append-only under § 147 AO, so "cleanup" means stopping
  the pull. The watcher reports overdue receivables as days and cents only — no `docs/12` guard
  rule, threshold, warning copy or escalation, which stay with the guard-foundation slice. The
  acceptance files are `apps/api/tests/test_m6c3b_jobs.py` and
  `packages/adapters/tests/test_scheduler_port.py`. **Two limits ship with it.**
  `AIS_CONSENT_MAX_DAYS = 180` has no row in the authoritative register, so it is a `Konvention`,
  `verify-before-production`, `Rechtsstand 08/2026`, on an unverified reading of PSD2 RTS Art. 10;
  no expiry is ever defaulted from it and it serves only as a ceiling check. And no cross-account
  enumeration exists — `account` is scoped by its own id and `CLAUDE.md` § 3.3 allows exactly one
  pre-context read, so a real scheduler must be handed its account ids. `docs/15` § 5.6 records
  that gap as open.
- **M6-C3c — Zahlungen screen. Technically complete; locally merged 24.08.2026 (`6995bc4`).** The German landlord _Zahlungen_
  screen at `/a/{accountId}/zahlungen`, client-side only: no endpoint, no schema, no migration
  (Alembic stays at `0021`) and no backend change. It reads `GET /match-proposals`,
  `GET /payment-ledger`, `GET /bank-transactions` and `GET /receivables`, and writes exactly one
  final outcome through `POST /bank-transactions/{id}/decision`. Buttons appear only on an open
  `NEEDS_REVIEW` row; auto-booked, unmatched, deduplicated and already-decided rows are read-only
  evidence, and the Zahlungsjournal has no edit, delete or reversal control. There is no manual
  assignment: the client never selects a receivable, and §§ 366, 367 BGB ordering stays on the
  server. The pure joiner is `features/zahlungen/proposal-view.ts`; its acceptance file is
  `apps/web/src/features/zahlungen/proposal-view.test.ts` (23 cases), with `centsToEurDisplay`
  covered in `apps/web/src/lib/format.test.ts`. A second acceptance file,
  `apps/web/src/features/zahlungen/zahlungen-view.test.tsx` (12 cases), renders the screen to
  static markup and asserts the safety properties the joiner cannot: that a decision control is
  absent on every row that is not an open `NEEDS_REVIEW`, and that no reversal control exists in
  the journal. Two further cases in `account-switcher.test.tsx` hold the owner-only nav entry.
  `apps/web/vitest.config.ts` sets `esbuild: { jsx: 'automatic' }` so those `.tsx` tests compile
  under the same automatic runtime Next's SWC pipeline gives the components. The screen is reachable from the navigation but is
  **not** part of the six-screen demo path: `docs/06` stays at six, the demo seed is unchanged, and
  the rendered statement is unchanged at 149269 bytes with 22 goldens present and 8 scale-leak
  canaries absent.
  **Five limits ship with it.** (1) No renter name is displayed anywhere. A candidate carries
  `renter_id` and `receivable_id` only, no route resolves a renter id to a `legal_name`, so the
  payer is identified by the bank `counterpart_name` and `purpose` and the candidate by its
  Forderung. A bare id is never printed where a name belongs. (2) The § 4 point weights remain
  `Konvention`, `verify-before-production`, `Rechtsstand 07/2026`; the screen presents them as a
  decision aid and states in German that they are not legal proof that a payment belongs to a
  claim. (3) The `Rechtsstand` stamp is a page-level constant. The authoritative per-proposal value
  is `match_proposal.convention_version`, which `_candidate_json` and `list_proposals` do not
  expose — that payload gap is C3a's and stays open. (4) The E2E signal is rendered as _noch nicht
  ausgewertet_ rather than as an unmet criterion, because `docs/15` § 4 marks it inert and the
  engine returns 0 for it unconditionally. Round five now names the mandate/E2E fields, but the
  signal stays inert until their migration, fixtures and engine change land.
  (5) The screen is owner-only in navigation as well as in the API: every route behind it calls
  `require_owner`, so the nav entry is hidden for `EMPLOYEE` to avoid a guaranteed dead end. That
  is navigation honesty, not authorization — the API re-authorizes independently.
  **Recorded, not fixed.** `require_owner` answers 403 with the English, route-inaccurate detail
  `"Only owners may create buildings"` (`authorization.py`), which the client would print verbatim;
  the ledger renders `created_at` through a timezone-naive string split, so a late-evening booking
  on a UTC server can show the previous calendar day; the loading and error copy
  _"Bitte API und Datenbank prüfen"_ is developer-facing but is the established house convention in
  seven other screens and was not diverged from here; `Ablehnen` and `Dublette` write an immutable
  record with no confirmation step; and a decided proposal does not link to the journal entry it
  produced. None of these is introduced by this slice's own code except the last two.

**Hard constraints:**

- Provider transaction identity is unique on `(account_id, bank_account_id,
provider_transaction_id)`, never on the provider ID alone.
- The payment ledger is append-only. Reversals append compensating rows; nothing is edited.
- An IBAN is learned only from a confirmed match and never when null.
- The shipped § 5.2 Largest-Remainder implementation refuses and fully rolls back an exact tie.
  Round five now specifies `base_rent`, `nk_advance`, `heating_advance`, `garage`; the new fixture
  and implementation remain pending.
- Matching confidence is a Lokara convention and is never presented as legal support for a match.
- Background jobs ship as service functions behind a scheduler port. Redis, Arq and Celery stay
  uninstalled until a real worker slice; `docs/01` D7 keeps that pick open.

**M6-C closed when:** all thirteen fixtures pass through the application service and persistence,
the three job entrypoints are callable, a landlord can confirm or reject a Review proposal in the
UI, every isolation boundary remains green, and the rendered statement is unchanged. Every one of
those conditions is met on `main`, so **M6-C is closed** and **M6 is technically complete**;
delivery and the renter portal remain M10. This closes only the original M6 contract; the
round-five supplement in `docs/15` is pending. Technical closure is not legal-production approval:
the Page-08 weights and thresholds stay `verify-before-production`, the 180-day AIS consent window
still has no register row, and the structured-reference signal remains inert until implemented.

The raw demo PDF is not byte-identical between runs: it embeds `/CreationDate` and `/ModDate`, so
its raw MD5 changes while the byte count stays at 149269. `scripts/pdf_fingerprint.sh` normalizes
those timestamps and produces the stable fingerprint `88eb8434eda65f8d7ff82826fc837a58`.
`assert_statement_pdf` separately enforces 22 goldens present and 8 scale-leak canaries absent.

### G1 — shared guard foundation

**Status:** technically complete and statement-reviewed 24.08.2026; locally merged as `6c257f8`
and not pushed.

The pure `packages/guard-engine` implements `evaluate_statement_deadline`,
`evaluate_meter_calibration` and `evaluate_uvi_cadence` against exactly `12-F01`–`12-F06` and
`12-F11`–`12-F13`. Inputs carry explicit source identity and `today`; caller-supplied bundles carry
source, Rechtsstand, verification status and scoped conflicts. W2 executes the unified six-year
MessEV period from round 4 (`geprüft`, 08/2026); the superseded five-year Warmwasser/WMZ value is
recorded as not restorable, and only the non-blocking retrofit-transition label remains.
Missing W1 copy and post-retrofit W4 behavior remain explicit source gaps. No persistence,
API, UI, scheduler, provider, e-mail, push or PDF consumer was added.

Focused tests, fast and UTF-8 full gates are green. The normalized PDF fingerprint and byte count
remain `88eb8434eda65f8d7ff82826fc837a58` and 149269 bytes. Statement review has no remaining
finding. Technical closure does not clear any `verify-before-production` marker.

### U — UVI comparison, calculation and document

**Approved-spec prerequisite:** `docs/16`, spec-closed Slice A and the G1 cadence foundation.

- Implement the specified heating-only comparison with labelled fallbacks and no extrapolation.
- Add monthly readings, the UVI calculation and the separate tenant document.
- Keep scheduled delivery in M9 and portal publication in M10.

**Engineering is done when:** every `docs/16` calculation fixture passes, the specified monthly
`hdd_3807` input and persisted station assignment are implemented, durable inputs and the archive
are tenant-isolated, and owner generation plus the separate renter document pass both required
reviews and the demo gate. **Production clearance additionally requires** the selected PLZ dataset's
vendored lookup and PLZ-driven assignment to remain source-pinned and reproducible; both are green,
and the former PLZ-dataset production flag is cleared. Round five supplies `R-UVI-01`/`R-UVI-02`,
but their authoritative CSV synchronization and the exact versioned monthly content authority still
block production. The newly approved display strings still need oracle and implementation coverage.

**U0 status:** the round-4 transcription is complete and locally merged as `738e048`, not pushed.
`docs/16` §§ 7.1/7.2 carry the monthly `hdd_3807` dataset and the persisted station-to-PLZ
convention, § 4 carries the display-rounding decision and § 8.2 carries the K13 vintage maintenance.
The oracle gained four constants and no golden value moved. U0 is documentation plus data-only
fixtures.

**U1 status:** the pure `packages/uvi-engine` is complete and locally merged as `d02c838`, not
pushed. It
executes `docs/16` Blocks A, B, C with its raw fallback, D, D2, the HKV provisional path and linear
mid-month interpolation against the nine `UVI_EXAMPLES` cases. Block C rounds the displayed kWh
before deriving delta and percent, per § 4. The engine imports `lokara_domain` only and reuses no
rules-store table. No importer, adapter, schema, API, UI, PDF or delivery code exists yet. U1
satisfies the first `Done when` condition and no other.

**U1 statement review.** The required `statement-reviewer` pass verified all nine German output
strings byte-exactly against `docs/16` and found no wording defect. It found one structural gap
instead: the engine has no provenance channel on its results. `packages/guard-engine`, merged one
slice earlier, carries `GuardSourceIdentity` plus `source`, `rechtsstand` and `verification_status`
on every rule bundle; `packages/uvi-engine` carries none of that. The consequences are that the
unconfirmed Wärmepumpe deduction renders identically to a checked gas value, the § 8.2 over-500
fallback label and the § 7.2 DWD attribution, station and distance have nowhere to travel, Block A
cannot carry the § 5 provisional label, and two of four blocked HKV branches still return a
renter-facing label. Four further points are missing German wording rather than missing code and are
asked in `FRAGEN-an-Berkay-05.md`. U1 was merged with these limits recorded; U1b closes them, and no
UVI output reaches a renter before U5.

**U1b status:** engine provenance and labelled suppression is **technically complete, reviewed and
locally merged**. Feature commit `ed82202` was merged as `ee83535`; nothing is pushed.
`lokara_domain.provenance` now holds `SourceIdentity`, `RuleEvidence` and `RuleConflict` with the
guard engine's exact field names; every UVI evaluator takes a caller-supplied `UviRuleBundle` and
every result returns the evidence and unresolved conflicts it used. `BlockCResult` carries the § 7.2
DWD attribution, station id, distance and an over-50 km boolean; `BlockD2Input` takes a
`ResolvedHeizspiegelRow` bundle instead of bare `Decimal` deductions, and `BlockD2Result` returns the
size class actually used and a caller-supplied `fallback_label_de`. A blocked result now carries no
renter-facing label anywhere: `basis_de`, `label_de` and `attribution_de` are `None` under a
suppressed comparison. No arithmetic changed and no golden value moved. The merged
`packages/guard-engine` was left untouched as briefed.

The required `statement-reviewer` pass verified the renter-facing
suppression and exact ready-state labels. It found that Block D2 returned only its resolved-row
evidence and dropped distinct bundle evidence; a separate failing fixture and engine fix now retain
both in deterministic, deduplicated order. The closing full gate is green. At U1b close,
`BlockAResult.label_de` still needed the U5 composer to carry the § 5 provisional label and
`SourceIdentity` still needed a durable U4 consumer. U4/U5 now close both handoffs through the
immutable source-complete run archive and the separate renter document.

**U2 status:** versioned Heizspiegel rules data is complete, statement-reviewed and locally merged.
Feature commit `75cfaec` was merged as `2559848`; nothing is pushed. The 18 rows, five deductions,
non-positive import guard, two visible over-500 fallbacks, exact attribution and 1 October vintage
resolution feed `ResolvedHeizspiegelRow`. Review found and the two-lane fix closed dynamic
future-vintage row identity and effective-Rechtsstand provenance. Focused U2 tests pass 11, all
rules-store tests pass 135, the fast gate passes 598 pure-package tests and the full gate passes
1,289 Python plus 84 web tests. Production flags remain unchanged.

**U3a status:** the annual DWD climate-factor adapter is complete, boundary-audited and locally
merged. Feature commit `62b2918` was merged as `fcc3ad8`; nothing is pushed. It normalizes strict
CSV, comma-CSV and XML inputs, enforces file/row period and publication provenance, all eight annual
guards, exact source metadata, explicit raw fallback and retry-safe pure merge behavior. The
canonical heating engine remains the only annual adjustment calculation path. Focused tests pass
49, all adapter tests pass 97 and the full gate passes 1,338 Python plus 84 web tests. Monthly
`hdd_3807` and station assignment remain U3b.

**U3b status:** monthly DWD normalization and deterministic station assignment are complete,
boundary-audited and locally merged. Feature commit `a37f9a3` was merged as `78c5cce`; nothing is
pushed. The parser retains all nine documented fields and canonical DWD evidence; assignment
requires one station valid for at least 25 days in both months, accepts the existing explicit
versioned-centroid input, uses DWD-row coordinates and returns reproducible
source/convention/distance evidence with no invented German wording. Audit fixtures close coordinate
drift, parser-origin bypass, incomplete archive provenance and unstable-distance findings. Focused
tests pass 136, all adapter tests pass 184 and the full gate passes 1,425 Python plus 84 web tests.
The U3 PLZ-coordinate follow-up now selects
`https://github.com/WZBSocialScienceCenter/plz_geocoord/commit/927da8a86e9b6e5ebb499cd9259cd1afd3e3c6d2`,
version January 2019, licence Apache-2.0, with WZB attribution. The exact raw source is
`https://raw.githubusercontent.com/WZBSocialScienceCenter/plz_geocoord/927da8a86e9b6e5ebb499cd9259cd1afd3e3c6d2/plz_geocoord.csv`;
the vendored bytes have SHA-256
`d427a6687a7cb286b3a9b4091831a06aaf0a0da40bd7c76cab7a82ac96e0d9a2` and exactly 8,298 data rows
excluding the header. Its vendored offline lookup and PLZ-driven assignment entrypoint are green;
the existing explicit-centroid entrypoint remains compatible. The PLZ centroid is the production
default, and the former PLZ-dataset production flag is cleared. All other production blocks stay
visible.

**U4/U5 closure status.** U4 feature `74857a6` was merged as `7a18bec`. U5 feature `36d62b2` was
merged as `a54350f`. Migration `0023` adds the server-side normalized prerequisites; owner-side
generation resolves heat-only compatible readings and each month's effective configuration,
archives complete source identities and canonical hashes, and renders one separate German renter
document. The closing boundary audit and statement review report no findings. The demo gate passes
1,542 Python and 84 web tests; the existing statement fingerprint remains
`88eb8434eda65f8d7ff82826fc837a58` at 149269 bytes. Nothing is pushed.

**Warmwasser UVI extension status.** The approved specification is transcribed in `docs/16-uvi.md`
§ 8.3 and the golden fixture in this checkpoint is
`packages/uvi-engine/tests/test_uvi_warm_water_golden.py`. The fixture covers a central,
remotely-read `WARM_WATER` meter, the versioned § 9 conversion (`tw`-configured, `125 kWh/m³`
for the fixture's 60 °C setting), Block B, raw
prior-year comparison without weather adjustment and D2's `warm_water_deduction × area × monthly
share`. The engine, API assembly and conditional PDF block are now implemented and the golden
coverage is green. Separate API/PDF regressions retain distinct previous-month, raw prior-year
and D2 values, per-block provenance and the complete legal/footer tail on one unclipped A4 page.
Volumetric conversion must fail loudly if the approved rules-store conversion is not
available; no heating-only shortcut is permitted. The applicable § 6a interpretation, monthly
content authority and remote-read applicability remain `verify-before-production`.

**Remaining external authority.** The PLZ dataset choice is closed:
`WZBSocialScienceCenter/plz_geocoord`, January 2019, commit
`927da8a86e9b6e5ebb499cd9259cd1afd3e3c6d2`, SHA-256
`d427a6687a7cb286b3a9b4091831a06aaf0a0da40bd7c76cab7a82ac96e0d9a2`, 8,298 data rows and
Apache-2.0, attributed to Markus Konrad and the Wissenschaftszentrum Berlin für Sozialforschung
(WZB), is the production centroid default for DWD nearest-station assignment. The vendored offline
lookup and PLZ-driven assignment entrypoint are green, and the former PLZ-dataset production flag
is cleared. No runtime geocoding or network fallback is allowed for DWD assignment. Berkay has
supplied the exact two UVI rows, but the authoritative CSV still parses to 180 data records and does
not contain them. Blocks C and D2 remain production-blocked until that sync, the exact
monthly content list and the other `verify-before-production` items in `docs/16` are resolved.
Scheduling is M9; renter portal publication is M10.

### M7 — Tax export and AfA

**Scope and authority boundary:** implement M7 technically from approved `docs/09`–`docs/11`.
Reuse Slice C's Page-02 implementation; do not rebuild it. Technical completion never means
production or legal approval. Current authority flags continue to block production exports, and no
step below is complete until its named evidence exists.

**Status — M7-0…M7-E technically complete on `main`; the M7-F repair candidate is integrated on
`development` but remains deliberately deferred and unverified until after M10.**
M7-B's verified-export adapter, which was the declared RED window, is closed: artifact bytes are now
generated by the server from domain inputs and frozen by an internal `archive_verified_test_artifacts`
boundary, the readiness projection carries no tenant identity, and archive versions and supersession
run per logical export stream (account, building, tax year, export kind), never per readiness
attempt. `.lokara-red` was removed only after the focused suite went green.

Earlier M7-0…M7-E evidence: `scripts/gate.sh fast` and `scripts/gate.sh full` were green — `1709` pytest, `106` vitest,
strict mypy over `234` source files, engine purity, agent parity, RLS coverage `55` tenant tables and
FK isolation `97` foreign keys. The non-fresh demo path is green, and `scripts/pdf_fingerprint.sh`
reports the ordinary NK/heating statement unchanged at `88eb8434eda65f8d7ff82826fc837a58` /
`149269` bytes, so M7 altered nothing a landlord already read. The development database was
reconciled to the final `0024` and its seven M7 tables now match the models column for column.

**That is foundation evidence only, and M7-F is not finished.** Its first fresh boundary audit ran and
confirmed four unresolved defects: blocked artifacts remain directly downloadable; retrieval does
not verify stored bytes against their digest; same-account readiness evidence can reference the
wrong building/year context; and the safe source-snapshot allowlist drops required ledger signals.
The statement review was interrupted, the docs closure review has not run, and regression-first
repairs were checkpointed and integrated without closing review or verification. M7-F is parked
until after M10 and is required
before final programme or production closure. Every applicable authority limit stands: K09's
month-granular convention, Weg-B
placeholders, the missing Gutachten share, all Anlage-V line numbers, SKR03/SKR04 accounts, DATEV
EXTF parameters and Soll/Haben orientation remain `verify-before-production` and continue to block
real output. Successful archive behaviour uses the explicitly verified test-only rule bundle;
runtime mappings stay blocked.

#### M7-0 — AfA authority reconciliation

- Keep K09's selected technical result: `10-F11 = 453,798 ct`.
- Preserve the authoritative CSV status `verify-before-production`; remove the incorrect
  `geprüft` fixture claim.
- Reconcile stale K09 statements in `docs/02`, `docs/10`, `docs/11` and this plan.
- Preserve Weg-B placeholders and the `leistungBis` versus `abfluss` boundary.

#### M7-A — Pure AfA engine

- Create RED executable tests before implementation, then add pure `packages/afa-engine`.
- A1 covers acquisition, allocation, rates, annual series, self-use and predecessor continuation.
- A2 covers later costs, the 15% guard, loans, Disagio and the Page-04 handoff.
- Execute all `10-F01…F34` using integer cents, basis points and exact `Decimal`.
- The public boundary is
  `calculate_afa_record(AfaInput, AfaRuleBundle, tax_year) -> AfaResult`.
- Every result returns deterministic findings, source evidence, `Rechtsstand` and
  `production_blocked`.

#### M7-B — Pure export engine and rules

- Create RED executable tests for `11-F01…F16`, then add pure `packages/export-engine`.
- Implement `assign_tax_year`, `evaluate_export_readiness`, `build_anlage_v_overview`,
  `encode_anlage_v_csv` and `encode_datev_extf`.
- Implement tax-year assignment, readiness, Anlage-V aggregation/CSV and DATEV EXTF encoding.
- Add versioned AfA rules, Anlage-V layouts, SKR mappings and the EXTF profile to `rules-store`.
- Every output has deterministic ordering, an explicit generation time and resolved rule evidence.
- Keep all unverified lines, accounts, EXTF parameters and Soll/Haben orientation blocked.
- Exclude Disagio and handed-off maintenance until their mapping and deduplication gap is resolved.

#### M7-C — Persistence

- Add migration `0024`.
- Add immutable, account-scoped records for AfA versions, normalized tax events, adviser-profile
  versions, mapping versions, readiness attempts, export archives and archived artifacts.
- Materialize accepted M6 payment components idempotently without guessing missing categories.
- Preserve nullable dates/categories so readiness can report them.
- Enforce composite foreign keys, RLS, refused cross-account writes, append-only corrections and
  immutable archive bytes.

#### M7-D — API and authorization

- Add AfA preview/create/history endpoints.
- Add tax-event list/create/correction endpoints.
- Add adviser-profile and year-mapping endpoints.
- Add readiness, generation, history and archived-download endpoints.
- `OWNER` receives full M7 access. `TAX_ADVISOR` receives read access plus profile/mapping writes
  only. `EMPLOYEE` receives no tax access.
- Failed generation stores readiness evidence but no artifact.

#### M7-E — Web and PDF

- Add `/a/{accountId}/steuern` with object/year selection.
- Add the AfA wizard, readiness view, adviser/mapping settings and immutable export history.
- Replace the tax-adviser placeholder with the restricted tax workspace.
- Render the Anlage-V overview as German PDF and CSV.
- Keep renter names out of adviser and export payloads.
- Show every production blocker and disable real downloads while applicable authority remains
  unverified.

#### M7-F — Review and closure

**Deferred until after M10 by Emir's decision.** This deferral does not block M8, M9, independent
M10 renter work or M11 native-app and billing work. It does block M7-dependent
tax-adviser/integrated-tax closure, any M7 production claim and final programme closure.

- Resolve all four findings from the completed initial boundary audit.
- Rerun the boundary audit after repairs.
- Complete the interrupted statement review for the tax UI and Anlage-V PDF.
- Run final docs reconciliation after repairs.
- Verify every golden fixture, authorization, RLS, immutability, deterministic bytes and
  archived-byte retrieval.
- Prove migration `0024` on an empty disposable database and compare development schema parity.
- Run fast, full and non-fresh demo gates.
- Record the existing statement PDF fingerprint before and after.
- Update this plan with actual completion evidence and remaining production blockers.

**Outside M7:** ELSTER, DATEV network transfer, VAT calculation, M8, M9, M10, M11 and investment
KPIs. Successful archive behavior uses an explicitly verified test rule bundle; current runtime
mappings remain blocked. The missing AfA wizard concept file is not reconstructed; the UI follows approved
`docs/10`.

### M8 — Document and letter engine

**Approved-spec prerequisite:** `docs/13`, including its legal/convention labels, risk gates,
non-goals and all `CLAUSES-F01`–`CLAUSES-F19` fixtures, plus a separate approved source-backed
catalogue for the missing clause bodies and complete Mieterhöhung/Kündigung/Mahnung bodies.

**Done when:** a contract is generated from versioned clauses and a clause update identifies every
affected contract. **That condition is currently unreachable** — see the three blockers below. It
stays as written because it is the correct milestone target, not because M8 can reach it today.

#### The M8 problem — three distinct blockers, verified 25.08.2026

**1. `docs/13` contains decisions about clauses, not clauses.** The transcription is complete and
approved for what Page 06 actually supplies: which clause combinations conflict, which signature
route each combination forces, the B1–B8 increase and limit arithmetic, and the E1–E11 edge cases.
It supplies **no clause body and no letter body**. `docs/13` §§ 3.1, 3.6, 7 and 11 each say so
outright. A contract generator therefore has every rule needed to _validate_ a contract and no text
with which to _produce_ one. The same applies to Mieterhöhung, Kündigung and Mahnung: Page 06
approves the workflow inputs and routing, never the declaration itself. This is a missing source,
not a missing implementation, and no agent may close it by drafting German legal text.

**2. Eleven authority gaps, and several are missing rules rather than unverified values.**
`docs/13` § 7 lists all eleven. Four cannot be implemented at all, because the rule itself is
unknown: the day-accurate start of the § 559 six-year window (`[UNSICHER]`, an unsupported reading
of the statute), the state-regulation territory list behind the 15% § 558 cap, the cent-residual
split for a deposit maximum not divisible by three, and the fixed-term-over-one-year signature
route, which the register names but no fixture exercises. The remaining seven are flagged values
that block output but not construction — including both small-repair conventions, the SEPA 36-month
expiry and the final index-decline behaviour.

**3. A dependency inversion against M9.** `docs/13` § 4 delegates dates, thresholds, guard state and
trigger timing for B1, B2, B3 and B7 to `docs/12`. Those are exactly `docs/12`'s W6 (graduated
rent), W7 (index rent), W5 (§ 558 comparative rent) and W3 (arrears and grace payment) — and G1
shipped only W1, W2 and W4. W3 and W5–W8 are unimplemented and currently scheduled for **M9, after
M8**. So M8's B3 and B7 results depend on machinery a later milestone owns.

**Decided resolution for blocker 3:** do not reorder M9. The clause engine takes caller-supplied
guard state and rule evidence, exactly as `packages/guard-engine` already takes caller-supplied
bundles with source, `Rechtsstand`, verification status and scoped conflicts. M8 then computes and
routes without owning the dates, and M9 later supplies the real projections to the same boundary.
An M8 slice must not reimplement a `docs/12` guard, and must not silently default a date.

**Consequence for scheduling.** M8 splits into an unblocked lane and a blocked lane. Lane A below
can start immediately and is genuinely useful: it is the whole of Page 06's arithmetic and routing.
Lane B cannot start, and no part of it may be approximated to make the milestone look finished.

#### Lane A — unblocked: the pure clause and risk engine

##### M8-A0 — executable Page-06 fixtures

**Agent:** `spec-scribe`. Mandatory red window — declare it in `.lokara-red` (`AGENTS.md` § 4).

- `packages/rules-store/tests/berkay_13_golden.py` is the approved **data-only** oracle with exactly
  `CLAUSES-F01`–`CLAUSES-F19`. Turn it into executable engine tests, following
  `packages/afa-engine/tests/test_berkay_10_executable.py` as the precedent.
- Cover B1–B8 and E1–E11 as behaviour, including the cases the oracle carries only as data: the
  F07 over-limit repair contributing **zero** rather than the limit or the excess, F11's calculated
  lower rent with no automatic adjustment, F12's ineffective ten-month step, F15's blocked simple
  e-signature and F16/F17's warn-only § 556d with a stored, unverified self-declaration.
- Every blocked convention enters as caller-supplied rule evidence, never as an engine constant.
  The F07 limits in particular are unverified conventions and must be visible as such in the test.

**Done when:** the suite covers exactly `CLAUSES-F01`–`CLAUSES-F19`, fails against absent code, and
no golden value from the merged oracle moved.

##### M8-A1 — pure `packages/clause-engine`

**Agent:** `engine-implementer`.

- New pure package following the `packages/afa-engine` layout; register it in the `LAYERS` table of
  `scripts/check_engine_purity.py` or purity does not cover it.
- Integer cents with half-up rounding; `Decimal` for VPI points, square metres and rates; no float.
- Implement B1 graduated rent, B2 index rent, B3a/B3b comparative-rent caps, B4a/B4b modernization
  including the parallel § 559 Abs. 3a €0.50/m² heating subcap and the mandatory
  `massnahmeArt ∈ {allgemein, heizung_555b_1, heizung_555b_1a}`, B5 small repairs, B6 deposit,
  B7a/B7b arrears thresholds and B8 § 556d.
- All dates, three-year lookbacks, cure events and guard state arrive as caller-supplied evidence
  per the decided resolution above. The engine computes; it does not own the calendar.
- The § 559 six-year window start is a **caller-supplied anchor with no default**. It is
  `[UNSICHER]` in the source; an engine that picks one silently invents law.
- Every result returns ordered findings, severity, blocking versus warn-only, required
  acknowledgement, legal/convention label, `Rechtsstand` and its production-blocked state, matching
  the `packages/guard-engine` provenance pattern.

**Done when:** all nineteen fixtures pass, `scripts/gate.sh fast` is green, `.lokara-red` is
removed, `mypy --strict` passes and no float touches money.

##### M8-A2 — compatibility and signature gate

**Agent:** `engine-implementer`, in the same package.

- Return the `docs/13` § 3.3 ordered result: selected clause versions, conflicts, required form,
  allowed signature route, blocking state, legal sources, verification flags and affected contract
  references.
- Graduated and index rent are mutually exclusive. A simple e-signature is blocked for either and
  routes to paper or future QES. QES is not a V1 capability.
- The fixed-term-over-one-year route has no worked fixture in the source. Implement it as an
  explicit unresolved route that refuses rather than guesses, and keep the coverage gap visible.

##### M8-A3 — blocked conventions in the rules store

**Agent:** `engine-implementer`.

- Add the Page-06 conventions to `packages/rules-store` as versioned, flagged rows: both
  small-repair limits, the signature gate V1 convention, the § 556d product handling, the SEPA
  36-month expiry and the 15% cap territory flag.
- Every one of the eight `verify-before-production` rows keeps its flag, source, legal nature and
  `Rechtsstand`. A rule that is present is not a rule that is approved.
- The 15% territory list is absent, so the flag is an input the caller sets. `docs/12` row 120
  records the same gap; do not invent a state list on either side.

##### M8-A4 — Destatis VPI adapter

**Agent:** `engine-implementer`.

- `packages/adapters/src/lokara_adapters/destatis.py` already defines the `PriceIndexGateway` port,
  `PriceIndexValue` and `VPI_SERIES_CODE = "61111-0002"` on base 2020 = 100, with the real GENESIS
  call marked TODO. Complete the normalization and guards behind the existing port; only this module
  knows the vendor format.
- Enforce the B2 preconditions the adapter can see: an officially published index, a compatible
  base year, and month normalization to the first of the month. Rebasing is outside Page 06 —
  refuse an incompatible basis rather than converting it.
- Keep the provider stubbed. No real GENESIS key or network call in this slice.
- The Mietspiegel provider stays a stub: `docs/12` row 116 makes comparative rent a nullable manual
  input with no procurement, so there is nothing to integrate.

##### M8-A5 — lane A review and closure

- `boundary-auditor` for the adapter boundary and any rules-store change.
- No `statement-reviewer` pass is required while lane A renders nothing a landlord or renter reads.
- Fast and full gates green; the ordinary statement fingerprint must stay
  `88eb8434eda65f8d7ff82826fc837a58` at 149269 bytes, because lane A touches no rendered output.

**Lane A closes when:** the nineteen fixtures pass through the pure engine and gate, the flagged
conventions are versioned and visible, and no clause body, letter body, schema, API or screen was
added.

#### Lane B — blocked: catalogue, composition, documents and letters

**Do not start any slice below until the missing source exists and Emir approves its transcription.**
The prerequisite is a source-backed catalogue containing the clause bodies with stable block IDs and
versions, and complete Mieterhöhung, Kündigung and Mahnung bodies. **It is not a Berkay
deliverable and will not arrive by asking him:** the round-five question file's
_Nicht erneut erfragt_ section classifies the complete clause catalogue with bodies as external
legal/source work, and round four already answered the Page-06 product decisions. No Page-06 item
is currently open with Berkay. Obtaining the catalogue is therefore a separate sourcing decision.
Until it lands, lane B has no acceptance surface at all: there is nothing to render and nothing to
compare a render against.

- **M8-B0** — transcribe the delivered catalogue into `docs/13` (or a new owned doc) with a complete
  coverage table and golden fixtures, under the same gate every other Page passed. `spec-scribe`.
- **M8-B1** — versioned clause-block persistence and stored composition per `docs/13` § 3.2:
  immutable version references, validity period, source version, `Rechtsstand`, verification flag
  and compatibility metadata. A legal change creates a new version and identifies every affected
  composition; it never overwrites.
- **M8-B2** — contract generation from a frozen composition, with the same deterministic
  archive/immutability discipline M6-B and M7-C already use.
- **M8-B3** — the action workflows for Mieterhöhung, Kündigung and Mahnung, consuming lane A's risk
  result and `docs/12` guard state. Generation only; sending stays M9.
- **M8-B4** — SEPA mandate capture per `docs/13` § 3.5: reference of at most 35 characters, unique
  per mandate, non-future date, one missing field marks the mandate incomplete without blocking the
  contract. Storage and display only — no collection, no PIS, no creditor ID.
- **M8-B5** — review and closure, including a required `statement-reviewer` pass, since a landlord
  and a renter both read these documents.

#### M8 production blockers — technical closure never clears these

- All eight `verify-before-production` Page-06 register rows, including both small-repair
  conventions and the SEPA 36-month expiry.
- The four unknown rules: the § 559 six-year window start, the 15% state territory list, the deposit
  cent-residual split and the fixed-term signature route.
- Final index-decline product behaviour, which stays informational with no automatic adjustment.
- Planned Mietrecht-II changes to index rent and grace-payment effects were not in force under the
  source's stated dates and need a fresh as-of check before production.
- No clause or letter body may be drafted by an agent. A missing legal text is asked, never written.

### M9 — Reminders, email and checklists

**Status — M9 is technically complete and review-clean on `development`; it is not
production-approved.** The final repository-wide demo gate, boundary audit, statement/UI re-review
and fingerprint check are green. The workstream includes these completed repairs:

- Migration `0025` created `guard_resolution_event` before `renter_delivery_artifact`, so its W1
  foreign key could not resolve and the migration failed on any database that had not already
  received an earlier draft. Creation order now follows the dependency, and the reversed drop order
  follows from it.
- `dispatch_renter_artifact` wrote a `RecipientSuppressionEvent` that
  `append_recipient_suppression_from_status_m9` already derives from the status event. The
  deduplication trigger skips the second insert by returning `NULL`, which the ORM reports as a
  `FlushError` — so every synchronous `BOUNCED`/`COMPLAINED` receipt crashed the job. The trigger is
  now the single owner of that derivation.
- A bounce or complaint recorded only in the append-only provider status history did not suppress a
  later occurrence, because the dispatch path read the suppression projection alone. It now consults
  the history directly.
- `derive_statement_production_blockers` read an absent or invented Page-01 authority inventory as
  "clear". A statement envelope must reproduce one published `PAGE_01_STATEMENT_RULES` version
  verbatim, or it carries `STATEMENT-AUTHORITY-ENVELOPE-INCOMPLETE` and cannot be delivered.
- Both renter-delivery write endpoints previously returned HTTP 500. Real migrated-Postgres tests
  now exercise them; request context, confirmation artifact/membership bindings and accepted-owner
  enforcement are repaired.
- Checklist and W1 evidence triggers now require accepted memberships and consistent annual-
  statement artifact bindings. Consumers use the bound artifact column instead of snapshot JSON.
- Statement delivery blockers are now derived from the published Page-01 inventory instead of
  trusting a writer-provided blocker list.

The three M9 test modules also set `SUPABASE_JWT_SECRET` in the process environment at import time,
which broke 31 unrelated authenticated API tests in a whole-suite run. Test environment is now
fixture-scoped.

The final GAS/UVI boundary close also repaired three explicit contracts:

- Configuration resolution treats `[M, next M)` as the complete calendar month: a boundary strictly
  inside blocks, while `valid_from = M`, `valid_to = next M` and a successor starting at `next M`
  remain valid exact edges.
- Fresh PostgreSQL migration acceptance from `0032` through `0034` proves that nullable
  `condition_number` is added without an `UPDATE` or backfill and that the final constraint neither
  rewrites existing append-only combined-factor evidence nor infers legacy status from supplier or
  legal metadata. Legacy factor plus `NULL` remains persisted evidence and blocks gas conversion
  until a source-backed successor supplies both components.
- Renter-visible GAS provenance now uses German decimal commas and dates and renders an open period
  as `gültig ab 01.07.2026`, never ISO date plus `bis offen`.

**Approved-spec prerequisite:** `docs/12` and the G1 foundation. M9 extends the existing W1/W2/W4
engine with remaining guard projections, reminders, email and checklists without redefining those
rules.

- All W1–W8 evaluators and `12-F01`–`12-F24` execute through versioned Page-05 rules.
- Migration `0025` stores immutable evaluations, reminders/resolutions, opt-in schedule versions,
  exact-byte artifacts and hashes, email/status/suppression evidence and checklist item events.
- Jobs and endpoints are caller-account-scoped and idempotent. Owners may send or confirm legal
  delivery; employees see assigned-building guards and may append checklist events; tax advisers
  have no M9 access.
- `/waechter` shows deadlines, delivery state and checklists with labelled status, blockers and
  accessible controls. Provider `DELIVERED` is transport evidence only; W1 requires an owner
  confirmation with `delivered_on` and an evidence reference.
- Automation defaults off. No real email, worker, scheduler, push or Destatis provider is selected;
  UVI delivery lacks frozen PDF bytes and the production checklist catalogue is empty.

#### M9-R — completed endpoint and boundary repair

The database-backed endpoint tests, request-context repair, W1 confirmation bindings and
writer-trust repair are complete. The follow-up boundary audit also found and drove repairs for
unaccepted membership scope and forgeable/non-annual W1 evidence bindings. A fresh boundary review
is clean; its focused verification passed `112` tests. The numbered requirements below are the
completed repair record, not the current resume task.

1. **Database-backed write tests completed.** The real migrated-Postgres suite now posts to
   `POST /a/{account_id}/deliveries` and `POST /a/{account_id}/deliveries/{delivery_id}/confirm`.
   It first proved both failures red under the declared `.lokara-red` window and now verifies the
   repaired ORM, check-constraint and trigger paths.

2. **Forged-context check restored.** Delivery validation now uses the request body instead of
   aliasing the fetched `RenterDeliveryArtifact` as request context. The real-row path verifies the
   fetched building, unit, tenancy, renter and tenancy party against the artifact's declared
   foreign-key chain.

3. **W1 confirmation bindings recorded.** `PortalScope` now carries `membership_id`, and
   `confirm_delivery` writes both `renter_delivery_artifact_id` and
   `confirmed_by_membership_id`. The application role rule and database trigger now agree on an
   accepted, unrevoked owner confirmation, preserving the § 147 AO actor.

4. **Writer-trust gap closed.** `derive_statement_production_blockers` now derives the expected
   blockers from the published `PAGE_01_STATEMENT_RULES` inventory instead of trusting the
   snapshot writer's blocker list.

5. **Earlier checkpoint verification completed.** At that checkpoint, `scripts/gate.sh demo` was
   green with `1844` pytest and `130` vitest; the ordinary statement fingerprint was
   `88eb8434eda65f8d7ff82826fc837a58` / `149269` bytes and the boundary review was clean. The
   statement review was still red at that historical checkpoint; M9-U below records its repair and
   the superseding final evidence.

#### M9-U — final repository close green and review-clean

The first UI repair added explicit German W1–W8 titles, known blocker labels, reminder-channel
labels, suppression-reason labels and semantic blocker lists. M9-U now adds explicit German labels
for `missing_warning_copy:last_day`, `missing_warning_copy:reminder_90_days`,
`missing_post_retrofit_rule`, `missing_uvi_cadence_start` and `basis_year_mismatch`. Authority
markers use the legal/rule fallback; unknown internal keys use a neutral internal-production-blocker
fallback. Identical displayed blocker messages are deduplicated. The approved German hash-integrity
message is explicitly allowlisted, so its useful `SHA-256` wording remains visible.

The first re-review found one remaining HIGH defect: a warning identical to the first production
blocker was rendered twice. A focused regression now requires the sentence to appear once while the
explicit `Produktionssperre` field remains visible, and the repair uses “Sperrgrund: siehe Hinweis
oben.” instead of repeating the text. Focused verification is green with `129` Python tests and `25`
Vitest tests; web lint, strict typecheck and the production build pass. The final required
statement/UI re-review is clean.

The red non-destructive demo run on 28.08.2026 was an earlier checkpoint, not the final state. The
final `scripts/gate.sh demo` is green with `1916` Python tests and `183` web tests. RLS coverage is
green for `73` tables and FK isolation is green for `144` account-scoped foreign keys. The final
boundary audit and statement/UI re-review are clean. The ordinary statement fingerprint remains
unchanged throughout the final close at `c4eecb355d57cec620dfcb0134fc9141` / `149275` bytes, and no
`.lokara-red` sentinel remains. M9 is therefore technically complete and review-clean on
`development`; this does not approve production use.

The production blockers are preserved: no real provider or scheduler is selected, automation stays
default-off, UVI delivery still lacks a frozen artifact, the production checklist catalogue remains
empty, and UVI register authority, exact monthly content and delivery cadence remain unresolved.
The legal/runtime audit limits below also remain production-blocking.

These audit findings stay open and unfixed, and are recorded as `verify-before-production` rather
than repaired inside M9-R: client-supplied `today`/`now` on `POST /guard-runs` stamps immutable
evidence; discovery-token expansion can create unbounded undeletable rows; `StubEmailGateway`
claims `provider_idempotency_enforced = True` from per-process memory and accumulates renter PDFs
across accounts; and `evaluators.py` hardcodes five legal values and uses exact `days == 30` /
`days == 90` equality, which permanently loses a W1 warning whenever a run is missed.

**Technical DoD met:** required verification is green, the ordinary statement fingerprint is
unchanged, required reviews are clean and all production blockers remain explicit. This closes M9
technically on `development`, not legally or operationally for production.

### Portfolio UI 00–08 programme

**Status — UI-00 through UI-06 and UI-08 are implemented on `development`; UI-07's non-blocked
demo core is implemented but partial. UI-03 onward now has later checkpoint full/demo and focused
review evidence; complete per-step acceptance and the live-browser matrix remain outstanding.** UI-00 was prepared from
clean `main` in the new `slice/ui-00-layout-global-clean` worktree, never from the dirty M7-F tree, the preserved M9
worktree or the unwanted `slice/ui-00-layout-global` worktree. Static UI review, 108 web tests,
lint, types, production build and the fast gate are green. A clean `scripts/gate.sh full` is also
green against a disposable PostgreSQL 16 database migrated to `0024`: 1,709 pytest and 108 vitest
tests pass, and the disposable container was removed without touching the shared M9 database.
The running UI serves the German 404 state and supplied logo/icon assets, but live viewport, 200%
zoom, keyboard, focus, reduced-motion and visual-overflow verification remains blocked because no
browser session is available. Emir explicitly authorized local merge and the UI-01 start with that
check still recorded as outstanding. Do not reuse or remove the unwanted worktree; its removal
requires Emir's separate approval.

UI-01 now has its five-field portfolio endpoint, real Mietsoll/occupancy dashboard, and explicit
unavailable states instead of the source's proposed 82/18 finance and 5/10/20 ticket mocks. Focused
fixtures, boundary audit, statement review, fast, full and non-fresh demo gates are green: 1,717
pytest and 117 vitest tests pass, and the statement remains 149,269 bytes. The disposable database
was removed. The demo gate restarted the shared Postgres container without targeting it for any
migration or seed; its preserved M9 volume was verified still at `0025`. Live UI-01 viewport, zoom,
keyboard, focus, reduced-motion and overflow verification remains blocked because no browser
session is available. Emir explicitly authorized local merge with that check still outstanding.

UI-02 now supplies the 248/72px account-scoped collapsible shell, role-aware icon navigation,
keyboard account menu, shared page header and branded loading/error states across landlord routes.
Emir accepted the live shell. Statement review, fast, production build and a clean full gate are
green: 1,717 pytest and 137 vitest tests pass. The disposable PostgreSQL 16 container was removed
without touching the shared M9 database. The automated viewport/zoom screenshot matrix remains
unavailable and is recorded as outstanding.

UI-03 supplies the repaired `advancePaymentSchedule` contract, the
`initialAdvancePaymentCents`/`advanceDeclarationRef` create payload, migration `0026`'s five
building columns, the gateway-bound best-effort geocoder with external lookup off by default, both
wizard routes, the non-filtering Liste/Karte toggle on Leaflet and the inactive photo slots. It was
built under the former direct implementation mode with lint, strict types and production-build
evidence. Later checkpoint full/demo gates and focused reviews add partial verification; complete
live-browser acceptance remains outstanding. `0026` and M9's `0025` are parallel children of `0024`; empty merge revision `0027`
joins them on `development`. Its Build-Notes assumptions live in `docs/04`: the placeholder Nominatim contact address,
the still-unconfirmed `/a/{accountId}/vertraege/neu?unitId={unitId}` generator route, the
token-only photo placeholder and the omitted optional detail-page slot.

UI-04 supplies the Objektakte: one server-owned dashboard projection with a single `asOf`, the four
KPIs including the weighted €/m² figure, three-state unit rows that separate vacancy from
Eigennutzung, receivable-backed balances, at most three prioritized facts, three compact module
summaries and an owner-only object-overview PDF rendered from the same snapshot. Under the direct
implementation mode ruff, `mypy --strict`, typecheck, lint and the production build pass, and **no
test suite, boundary audit or statement review ran** — it is **implemented; unverified — no test
evidence**. Explicit limits: no building update route exists, so "Objekt bearbeiten" is absent
rather than linked to a 404; OD5's per-unit Wohnen/Gewerbe split is **source-blocked** because no
authoritative unit usage type exists; recurring rent receivables are **source-blocked** on
`07_Zahlungen.md` [P13], so the projection reads existing receivables and generates none; statement
readiness, payments under review and guard-derived meter hints produce no facts because none of them
has a persisted projection yet; "Vorgänge", contacts, documents and object activity are omitted; and
OD18's three demo objects wait on the portfolio seed, which still carries one building.

UI-05A supplies account/building-scoped, optimistic-versioned statement drafts, an idempotent demo
evidence set, the Abrechnung list, start flow, six-step autosaving wizard, server-owned readiness,
separate cover-letter and tenant-statement previews, immutable final archives and successor-based
corrections. Migration `0028` adds the RLS-protected draft table and separates archived document
types without rewriting existing archive evidence. The PDF renderer remains display-only and all
money comes from the existing engines/frozen snapshot. Applicable Page-02 authority flags remain
visible: technical demo documents are explicitly watermarked as not production-approved. M9 email
and M10 portal actions stay inactive. Under direct implementation mode, ruff, strict mypy, web lint,
typecheck and production build pass; the local end-to-end path and stored hashes were checked and
the A4 output was visually inspected. Later checkpoint full/demo gates and clean boundary/focused
statement/UI re-reviews add partial verification; the complete live-browser accessibility matrix
remains outstanding. The 27.08 stability repair also binds finalization to the current optimistic draft
version and restricts M9 annual-statement sources to archived `TENANT_STATEMENT` documents.

UI-05B supplies the unit record: one account-scoped dashboard read model resolves the current state,
parties, contract facts, authoritative monthly amounts, server-generated use history and existing
final tenant archives at one `asOf`. Migration `0029` adds append-only versions for unit profile and
contract classification plus dated contract positions and documented rent changes. The owner-only
forms are action-triggered; the page no longer exposes database boundary language or derives time
segments from the browser clock. UI-07 now supplies the owner-only payment projection; the renter
portal remains deferred until M10, and messages/upload storage until real models and policies exist. Under
direct mode, ruff, strict mypy, web lint, typecheck and production build pass; the migration, demo
seed and authenticated live API read also pass. Later checkpoint full/demo gates and clean
boundary/focused statement/UI re-reviews add partial verification; the complete live-browser
accessibility matrix remains outstanding.

The supplied files are authoritative UX intent. Existing approved legal rules, pure-engine
contracts, account isolation and immutable evidence remain authoritative wherever a proposed
backend detail conflicts. No page may invent counts, money, legal status, deadlines, provider
state, uploads, portal access or other unavailable product state.

#### Source custody and documentation

- Relocate only `berkay-work/berkay-specs/` to `berkay-work/Spec-Seiten/UI/`; preserve every file's
  contents. This relocation was **locally merged** with UI-00; all
  source hashes match and the former source directory is no longer present in the dirty M7-F tree.
- Preserve this filename order: `00`, `01`, `02`, `03`, `04`, `05_Abrechnung`, `05_Einheiten`,
  `06`, `07`, `08`.
- Keep the PNG assets with the UI sources. Install the supplied horizontal logo and copy the
  supplied favicon PNG to Next.js `app/icon.png` only in UI-00.
- Transcribe implementation decisions into the owning approved documents; do not copy the source
  specifications into `docs/`.
- `docs/04-web-app-structure.md` owns routes and API contracts; `docs/05-design-system.md` owns
  shared UI rules and asset usage; `docs/06-demo-scenarios.md` owns the expanded portfolio demo.
  Update `docs/02`, `docs/08`, `docs/09`, `docs/12` or `docs/15` only when that document's domain
  contract actually changes.
- During execution, classify every requirement as **implemented**, **source-blocked**,
  **production-blocked** or **intentionally inactive**. A placeholder never counts as implemented.
- Preserve unrelated dirty and untracked files. Never use `git add -A`.

#### Ordered UI register

| Step   | Source file                  | Current status                                                                                                                                                                                                                                   | Required implementation and explicit limits                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------ | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UI-00  | `00_Layout-Global.md`        | **Locally merged 25.08.2026; implementation, static review and clean disposable-database full gate are green; live browser verification remains outstanding by explicit Emir decision**                                                          | Install the supplied horizontal logo and `app/icon.png`; update metadata; establish the 1440px content frame, shared page spacing, natural card heights, branded KPI accents and global loading/error/not-found states. Remove development-facing copy and the global object filter. Audit lifecycle metadata, but leave domain-specific schema additions to their owning later steps.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| UI-01  | `01_Dashboard.md`            | **Locally merged 25.08.2026; implementation, reviews, fast/full and non-fresh demo are green; live browser verification remains outstanding by explicit Emir decision**                                                                          | Add `GET /a/{account_id}/portfolio/overview` returning exactly `buildingCount`, `unitCount`, `occupiedUnitCount`, `vacantUnitCount` and `mietSollCentsMonthly`. Aggregate only visible, non-archived buildings and respect employee building scope. Replace the single-building dashboard with the portfolio layout. The proposed 82/18 finance mock and fake ticket counters are **intentionally inactive**; render real values or an honest unavailable/onboarding state.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| UI-02  | `02_App-Shell-Desktop.md`    | **Locally merged 25.08.2026; implementation, focused fixtures, statement review, fast/full and production build are green; Emir accepted the live shell; automated screenshot matrix remains outstanding**                                       | Implement the 248px expanded and 72px collapsed sidebar, persistent account-scoped preference, full logo versus icon, accessible tooltips, active navigation, account menu and shared page header. Keep authorization server-enforced; hiding navigation is presentation only. Roll the shell across existing landlord routes and remove obsolete development navigation copy. Track this filename as UI-02 even though its internal heading says 09.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| UI-03  | `03_Objekte.md`              | **Locally merged 25.08.2026; later full/demo and focused reviews green; partially verified, live-browser matrix outstanding** | First repair the tenancy frontend contract to consume `advancePaymentSchedule` and send `initialAdvancePaymentCents` plus `advanceDeclarationRef`. Add building type, residential flag, country and nullable coordinates without silently changing engine decisions. Build object/unit routes and wizards, list/map switch and inactive photo slots. Geocoding and tiles use configurable adapters. Public Nominatim/OSM is demo-only, cached, attributed and failure-tolerant; production defaults disabled.                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| UI-04  | `04_Objekt-Dashboard.md`     | **Integrated on `development`; later full/demo and focused reviews green; partially verified, live-browser matrix and recorded source-blocked scope remain open**                          | Add `/a/{account_id}/buildings/{building_id}/dashboard` as a server-owned read model with `asOf`, four authoritative KPIs, up to three prioritized facts, compact unit rows and explicit module availability. Do not aggregate financial truth in the browser. Generate object-summary PDFs server-side as immutable, owner-only snapshots with digest verification. Payment-dependent values now read UI-07's existing receivable facts; recurring receivable generation remains **source-blocked**.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| UI-05A | `05_Abrechnung-erstellen.md` | **Implemented on `development`; archive flow, stability repair, later full/demo and focused reviews green; partially verified, interactive-browser matrix outstanding**                     | Account/building-scoped, optimistic-versioned drafts, list/start routes, six-step autosaving wizard, server-owned readiness, separate A4 cover/tenant previews, M6-B finalization/archive integration and append-only correction history are implemented. Finalization requires the current draft version, and M9 accepts only `TENANT_STATEMENT` as an annual-statement source. The demo seed supplies addresses, payment copy and confirmed actual advances. Page-02 authority flags remain visible and every affected PDF is marked as a technical, non-production-approved demo. M9 email and M10 portal actions remain intentionally inactive. Advance recommendations, late-positive exception capture and source-owned letter variants remain source-blocked rather than invented.                                                                                                                                                                                             |
| UI-05B | `05_Einheiten-Dashboard.md`  | **Implemented on `development`; migration/seed/API, later full/demo and focused reviews green; partially verified, live-browser matrix outstanding**                                                                 | `/a/{account_id}/units/{unit_id}/dashboard` supplies one server-owned `asOf`, current tenancy first, collapsible server-generated history and explicit optional-module availability. Migration `0029` persists structured unit use, fixed-point rooms, controlled amenities, parking/garage contract positions and append-only rent changes with composite isolation-safe FKs, forced RLS and insert-only triggers; unknown facts stay absent. Only existing finalized tenant documents are listed. UI-07 now supplies the owner-only payment projection; portal controls remain deferred until M10, and messages/storage until real models and policies exist.                                                                                                                                                                                                                                                                                                                       |
| UI-06  | `06_Kosten.md`               | **Implemented on `development`; create/list/void flow, full/demo, copy regressions and focused reviews green; partially verified, live-browser matrix outstanding**                                      | The full-width object-local list, touched-year filter, `/a/{account_id}/kosten/neu`, server-owned catalogue endpoint and grouped picker are implemented. Creation sends `catalogueId`, an optional effective `keyOverride` and `directUnitId`. Status uses persisted classification findings and production blockers. Removal uses the existing reason-required void workflow. Migration `0031` stores non-allocable documentation without an invented key and excludes it before renter-allocation input. Beleg import remains an **intentionally inactive** beta path and its old route remains unlinked.                                                                                                                                                                                                                                                                                                                                                                           |
| UI-07  | `07_Zahlungen.md`            | **Demo core implemented on `development`; full/demo, focused drawer regressions and statement/UI re-review green; partial, complete scope and live-browser matrix outstanding**                                         | One owner-scoped cursor-paginated read model now supplies every bank transaction, backend counts and account/search/date/direction/status filters over a 100-day default window. The default page combines the three property-labelled demo Mietkonten; its local account filter scopes the list, and the table names the account in a dedicated column. The seed supplies 50 multi-month rows while preserving the current full/partial/review/unmatched/duplicate/ignored demo cases. The page also supplies a 400px detail drawer, proposal confirmation and append-only ignore/restore including safe page-local bulk actions. Unit and object payment links/projections use the same receivable facts. Manual reassignment, cash/manual-payment evidence, overpayment decisions, historical anomaly engine, recurring receivables, complete cross-dashboard aggregates, productive sync/reconnect and exact history-reset remain unimplemented or source-blocked; see `docs/04`. |
| UI-08  | `08_Zaehler.md`              | **Implemented on `development`; full/demo, GAS checks, 0040 regressions and boundary/statement re-reviews green; partially verified, required browser matrix outstanding**                    | The full-width object → building/unit → meter hierarchy and `/a/{account_id}/zaehler/neu` are implemented with explicit device types, remote-readability state and lifecycle periods. Reason-required void/removal and atomic replacement preserve readings. Append-only readings use structured preflight findings, backend periods and consumption provenance. Versioned internal/external heating-billing modes, structured internal inputs and the confirmed MDL handoff prevent simultaneous authoritative results. Shared calibration evaluation is reused. OCR/upload, radio connection/import and productive provider sync remain **intentionally inactive**; calibration authority and the remaining live-browser acceptance matrix remain production/closure blockers.                                                                                                                                                                                                                          |

Implement one numbered specification completely before the next. Direct implementation mode has
ended; the normal `AGENTS.md` fixture, review and gate flow is active. Current checkpoint
consolidation remains on the existing `development` branch; new slices follow branch discipline.

#### UI-08 implementation record — implemented, partially verified

**Source basis.** The reviewed
`/Users/berkaybayrak/Claude/Projects/Lokara/Adjustments/08_Zaehler.md` and the tracked
`berkay-work/Spec-Seiten/UI/08_Zaehler.md` are byte-identical. Implementation replaced the recorded
starting conditions: one selected building with a flat meter list, an inline create form, a nullable
calibration date with router-local status logic, hard deletion, 2025-bound reading/consumption
presentation and one free-form heating-cost entry path.

| Order | Adjustment scope | Implemented result | Remaining closure limit |
| --- | --- | --- | --- |
| 1 | **Z4, Z6, Z9 — contracts, lifecycle and calibration facts** | Migration `0032` adds account-scoped device facts, lifecycle/predecessor/successor links, remote readability and distinct calibration-data states. Device type and fixed unit are validated server-side. Replacement is atomic; removal and void append reasoned lifecycle evidence; readings and statement sources remain immutable. Calibration uses the shared evaluation path. | The authoritative versioned calibration rule and transition treatment remain **MUSS-INPUT/source-blocked** and must be approved before production. Migration `0040` closes nullable checks and invoice immutability; 20 rollback-only regressions pass and the boundary re-audit is clean. |
| 2 | **Z1, Z2, Z3 — information architecture and inventory tree** | The short header and one primary action precede the full-width object → building meters/units → meter hierarchy. Active and historical devices are separated; the backend-owned expired list drives previous/next navigation. | Keyboard, focus and 200% zoom behaviour still require the deferred live-browser matrix. |
| 3 | **Z5, Z7, Z8 — create wizard, readings and consumption** | `/a/{account_id}/zaehler/neu` has account/object-scoped draft recovery and server-fixed units. Reading preflight returns lifecycle, duplicate-date, rollback, correction and tenancy findings. Warnings require persisted confirmation, blockers refuse the write and corrections append linked successors. Backend periods expose measured/incomplete/estimated/not-applicable provenance and exact boundary readings. | Checkpoint full/demo and focused GAS/navigation regressions are green; complete live interaction acceptance remains outstanding. |
| 4 | **Z10 — remote readability** | `REMOTE_READABLE`, `NOT_REMOTE_READABLE` and `UNKNOWN` are persisted and displayed; manual readings remain `MANUAL`. | Connection controls, credentials, productive sync and fake provider state remain **intentionally inactive**. |
| 5 | **Z11, Z12, Z13 — heating-billing mode and inputs** | Append-only mode versions select Lokara or an external provider per object/period. A confirmed MDL statement is the only authoritative external handoff and suppresses the parallel internal statement result. Internal inputs are categorized, source-linked and readiness-projected; the OCR segment is disabled without a file input or request. | Productive provider integration, upload/OCR/storage and inferred legal values remain out of scope. The `0040` first-reasoned-void repair, 20 regressions and clean boundary/statement re-reviews now provide evidence; live-browser acceptance remains outstanding. |
| 6 | **Z14, Z15, Z16 — states, accessibility and acceptance** | Loading, empty, error, success, draft, read-only and permission states are implemented. Migration `0032`, seed, Web lint/typecheck, Ruff, strict mypy, authenticated workspace/reading preflight and both Next routes pass locally. | Full/demo gates and focused boundary/statement re-reviews are green. The required 1280/1440/1920 px, keyboard and 200% zoom matrix is outstanding, so UI-08 is not technically closed. |

**Out of scope for UI-08:** productive radio/MDL connectivity, OCR/upload/storage, provider contracts,
invented calibration rules, UVI delivery, mobile/tablet variants, electricity meters, engine rewrites
and changes to existing heating golden values. The original gas exclusion was superseded by the
28.08.2026 decision in `docs/16` § 3.2; only the approved gas-volume tuple was added. M9 technically
closed on 29.08.2026; UI-08's remaining acceptance matrix is still required before portfolio closure.

#### Interfaces and invariants

- Every new table is account-scoped, uses composite isolation-safe foreign keys, has ENABLE/FORCE
  RLS with a `WITH CHECK` policy, and has a test that attempts and refuses a cross-account write.
- Dashboards consume compact server read models. The client never reconstructs money, legal status
  or deadlines from raw payloads.
- Drafts use explicit versions. Final statements, PDFs, readings, rent changes, payment events and
  lifecycle history are append-only or corrected through linked successor records.
- Public Nominatim and OSM tile services are demo providers only. They require identification,
  caching, attribution, limited traffic and provider switchability and provide no SLA. Preserve the
  provider policies at <https://operations.osmfoundation.org/policies/nominatim/> and
  <https://operations.osmfoundation.org/policies/tiles/>.
- Next.js App Router owns the installed PNG icon through its `app/icon.png` metadata convention:
  <https://nextjs.org/docs/app/api-reference/file-conventions/metadata/app-icons>.
- No page-local mock counts, invented payment percentages, fake tickets, simulated uploads, fake
  portal access or false provider-connection state.

#### Verification and closure

**Historical direct implementation mode, set by Emir on 25.08.2026, has ended.** UI-03 onward
initially had compile/live-flow evidence only. The later checkpoint adds automated full/demo
verification and focused boundary/statement/UI reviews. These steps are now partially verified;
complete per-step acceptance, including the required live-browser matrix, remains open. Normal
`AGENTS.md` verification is active.

- Run focused tests and `scripts/gate.sh fast` during each slice. Run `scripts/gate.sh full` before
  closing each numbered specification.
- Run the non-fresh demo gate after UI-01, UI-03, UI-05A, UI-06 and UI-08. Never run
  `scripts/verify_demo_path.sh --fresh` without Emir's explicit permission.
- Run `boundary-auditor` after migrations, endpoints, adapters, isolation, immutable archives and
  payment or meter workflows.
- Run `statement-reviewer` for every landlord-facing step. Record `scripts/pdf_fingerprint.sh`
  before and after UI-04 and UI-05A.
- Verify 1280px, 1440px and 1920px layouts, 200% zoom, keyboard-only operation, visible focus,
  reduced motion, German copy, loading/empty/error/403/404 states and WCAG 2.1 AA contrast.
- Close a step only when all implementable scope is green and reviewed. Missing `MUSS-INPUT`
  features remain explicit blockers in this plan; they never become complete through placeholders.

### M10 — Portals and investment

**Execution prerequisite:** M9's 29.08.2026 technical closure is recorded above. The later
checkpoint is consolidated on local `main`, and Emir authorized M10-R0 on 11.09.2026.

**Approved-spec prerequisite:** `docs/14`; its calculations also depend on approved `docs/09`–
`docs/11`. Renter activation remains governed by `docs/02` and the M5 no-write guard.

**Two independent lanes.** Lane R (renter activation, context and portal) and lane I (investment
cockpit) share no table, engine, endpoint or screen. Run R first: it carries the legal exposure and
closes the one open M5 handoff. Do not interleave them. While direct implementation mode is active,
work on `development`; after that mode ends, branch according to `AGENTS.md` § 4.

#### M10 scope corrections — verified against the repository 25.08.2026

Three items previously listed under M10 are not M10 implementation work:

- **Tax-adviser guest access is already shipped.** `TAX_ADVISOR` is enforced per request by
  `authorize_tax_action` in `apps/api/src/lokara_api/routers/tax.py`, the account chooser handles a
  sole adviser context (M5, `a748729`), and `docs/02` § 2 records the role as shipped on `main`.
  Only M7-F's deferred repair touches it. Do not rebuild it under M10.
- **Tickets have no approved source.** No file in `docs/00`–`docs/16` defines a ticket entity,
  workflow, state machine or German copy; the sole mention is one line in the `docs/02` future
  inventory, which explicitly does not approve a schema. Hard rule 1 therefore blocks
  implementation. M10 does not build tickets. Route the missing source to
  `FRAGEN-an-Berkay-05.md` and leave the feature unscheduled until a source-backed spec exists.
- **Renter delivery stays M9.** M10 publishes a document into the renter context. Scheduling,
  e-mail and the delivery-status ledger remain M9 (`docs/16` § 12, `docs/12`).

#### M10 decisions — Emir accepted all four on 25.08.2026

These are settled inputs, not open questions. An agent implements them as written and does not
reopen them.

- **D1 — the renter pre-context read.** A renter has no `Membership`, and `app_bootstrap_contexts`
  returns membership contexts only (`BootstrapContext` in
  `packages/db/src/lokara_db/session.py`). `scripts/check_pre_context_reads.py` limits the
  `lokara_bootstrap` role to `person`, `membership` and `account`, so a renter login resolves no
  context at all today. `CLAUDE.md` § 3.3 permits exactly **one** pre-context identity read.
  **Decided:** extend that one function, its role grants and the checker's expected boundary to the
  renter/tenancy witness. A second pre-context function is refused. The same slice updates the
  `CLAUDE.md` § 3.3 wording and runs a fresh `boundary-auditor` pass; neither is optional, because
  this widens the single most sensitive boundary in the system.
- **D2 — the renter RLS context.** `packages/db/alembic/versions/0005_person_read_isolation.py`
  states outright that the renter portal is **not** an `app.account_id` context and that M10 must
  not solve it by handing a renter the landlord's account id. **Decided:** keep `app.account_id`
  for account scope and add a second transaction-local GUC (`app.tenancy_id`) plus renter-specific
  `FOR SELECT` policies on exactly the renter-visible tables, so one renter cannot read another
  tenancy in the same account even if application logic fails. Isolation stays enforced twice. This
  decides the shape of a future migration after the consolidated `0040` head.
- **D3 — `renter.person_id` immutability after activation.** `docs/02` § 2 assigns this decision to
  M10. **Decided:** immutable after activation. A genuine change appends a corrective row; nothing
  updates the link in place, per rule 3.2.
- **D4 — investment entitlement.** `docs/06` says investor access is unlocked by an entitlement,
  not an identity role, and billing moved to M11. **Decided:** an account-level entitlement written
  by an `OWNER`-only route, enforced server-side, with Stripe/RevenueCat wiring deferred to M11.
  `docs/14` § 1 records the `4,90 EUR` add-on as unapproved source metadata; no price, plan name or
  purchase flow may appear in M10.

Two scope calls were accepted with them: tickets stay source-blocked and unscheduled, and the
investment entitlement carries no billing dependency.

#### Lane R — renter activation, context and portal

##### M10-R0 — renter authorization design

**Agent:** `spec-scribe`. Documentation only; no schema, code or migration.

**Status:** reviewed locally on `slice/m10-r0-renter-authorization`; full gate green. `docs/02` and
`docs/04` now record D1–D3 without an open choice, define the tenancy-scoped read allowlist, specify
append-only portal publication and enumerate `M10-ACT-F01…F07`. Berkay's 11.09.2026 answer supplies
the exact `M10-COPY-01…06` strings and the public refusal side-channel rules, so M10-R4 is no longer
copy-blocked. No implementation source or fixture was added.

- Record the answers to D1, D2 and D3 in `docs/02` § 2 as the binding contract, replacing the
  current "open" wording, and mirror the future-architecture entry in `docs/04`.
- Specify the activation-code contract: tenancy-bound, per-person, single-use, hashed at rest,
  expiring, spend-once evidence, and the exact refusal cases (spent, expired, wrong tenancy,
  wrong account, already-linked renter, unknown person, unknown code).
- Specify exactly which rows a renter context may read, per table. The landlord's all-party
  calculation view is never exposed (`docs/16` § 12).
- Record the exact approved `M10-COPY-01…06` strings and the uniform public-refusal/timing boundary.

**Done when:** `docs/02` and `docs/04` state the renter context, the pre-context read change and the
immutability decision without an open choice, and the refusal cases are enumerable as fixtures.

##### M10-R1 — activation codes and the single `person_id` writer

**Agent:** `spec-scribe` (RED fixtures) then `engine-implementer`. Migration `0041` — the next
revision after the consolidated `0040_ui08_workspace_invariants.py` head.

**Technically complete, review-clean and locally merged into `main` as `cbecfa7` (11.09.2026):**
migration `0041`, ORM and API implement
owner-only hash-at-rest issuance, atomic spend-once redemption and all `M10-ACT-F01…F07` outcomes.
Direct non-null `renter.person_id` INSERTs and writes without matching redemption evidence are
blocked for runtime and owner roles. Missing/null/non-string shapes use the same timed HTTP `400`
path; safely attributable refusals append forced-RLS, append-only `renter_activation_attempt`
evidence. All three activation tables have positive/negative RLS read and refused cross-account
write coverage. `resolve_bootstrap_subject` consumers are allowlisted exactly to `me.py` and
`renter_activation.py`; `.lokara-red` is absent. The boundary re-audit is clean. Closing full gate
passes `2003` Python and `210` web tests; RLS covers `76` tables and FK isolation `152` edges.

- Add the account-scoped, composite-FK-protected activation-code table with `FORCE ROW LEVEL
SECURITY`, a `WITH CHECK` policy and a refused cross-account **write** assertion, or
  `scripts/check_rls_coverage.py` rejects it.
- Redemption is the **only** positive writer of `renter.person_id`
  (`packages/db/src/lokara_db/models.py`, `Renter`). Enforce single use in the database, not only in
  the service: a spent code is never redeemable twice under concurrency.
- Keep the M5 negative guard green:
  `apps/api/tests/test_m5_role_building_scope_api.py::test_no_current_request_schema_can_write_renter_person_id`
  must continue to pass for every route except the one new redemption route.
- Code generation and issuance are owner-only. Store a hash, never the code.

**Done when:** every enumerated refusal case is a passing fixture, redemption links exactly the
intended Person and tenancy, a second redemption of the same code fails, and `check_rls_coverage`
and `check_fk_isolation` are green with their new counts recorded.

##### M10-R2 — renter context and the `/renter/{tenancyId}` API

**Status:** technically complete, verified and locally merged as `92e18d5`. Migration `0042`,
the renter-scoped session helper and the API satisfy `M10-CTX-F01…F08`: the single-function
bootstrap extension, minimal `/me` and overview projections, exact renter RLS allowlist, zero
writes, adversarial same-account denial and owner non-regression. All `116` focused
DB/API/checker tests pass; RLS covers `76` tables, FK isolation covers `152` edges and the
pre-context checker is clean. The mandatory boundary audit is clean with rollback-only probes,
and the full gate passes `2021` Python and `210` web tests. No `.lokara-red` sentinel remains.
M10-R3 and migration `0043` remain pending.

**Agent:** `spec-scribe` (RED fixtures), then `engine-implementer` for migration `0042` and the DB
session helper, then `app-implementer` for the API boundary.

- The D1 pre-context extension and D2 renter session helper run alongside
  `account_scoped_session` in `packages/db/src/lokara_db/session.py` and the dependencies in
  `apps/api/src/lokara_api/deps.py`. `PathAccountSession` stays untouched for owner routes.
- `GET /me` returns renter contexts as well as membership contexts.
- The renter router lives next to `apps/api/src/lokara_api/routers/portal.py`. Every route verifies
  the tenancy named in the URL against the authenticated Person's renter link, then scopes RLS.
- R2 exposes only the renter's own tenancy overview. Published documents join this boundary in R3.
  No owner route, cross-tenancy read, building-wide view or other party's figures are exposed.

**Verified:** a renter session reads its own tenancy and is refused every other tenancy in the same
account with the app check disabled in a rolled-back probe; no owner route changed behaviour; and
`scripts/check_pre_context_reads.py` is green against its deliberately updated boundary.

##### M10-R3 — publication of renter documents

**Agent:** `spec-scribe` (RED fixtures), then `engine-implementer` for
`0043_m10_renter_portal_publication.py`, then `app-implementer`.

**Status (11.09.2026):** technically complete, verified and locally merged as `2ba245d`.
`M10-PUB-F01`–`F07`, migration `0043`, the ORM model, owner publication and renter list/download
routes are green. The named red
window is closed. A real `0043 → 0042 → 0043` cycle passed; focused DB/API/RLS verification passes
`132` tests; RLS covers `77` tenant tables, FK isolation covers `157` tenant-to-tenant edges and the
pre-context checker is clean. The mandatory boundary audit found no confirmed or suspected issue.
The full gate passes `2045` Python and `210` web tests. No rendered document changed, and no e-mail,
scheduling or reminder behavior was added.

- Publication is an append-only owner action over artifacts that already exist: the M6-B tenant
  archives in `statement_document_archive` (which already carries `audience` and `tenancy_id`) and
  a blocker-free frozen UVI artifact from M9. It copies and hashes the archived bytes into the
  tenancy-scoped `renter_portal_publication` record specified by M10-R0; it never re-renders or
  recalculates. `uvi_delivery_event` already accepts a `PUBLISHED` status; append it in the same
  transaction, never rewrite the original event.
- The renter reads archived bytes; nothing is re-rendered or recalculated for a renter.
- Publication does not send anything. No e-mail, no scheduling, no reminder.
- Every production blocker on the underlying artifact still applies. A blocked statement or UVI run
  must not become publishable merely because a portal exists.

**Done when:** an owner can publish exactly one existing archived document to exactly one tenancy,
the renter sees only published documents, retrieval verifies the stored digest, and no artifact
carrying an unresolved production blocker is publishable.

##### M10-R4 — renter portal screens

**Agent:** `spec-scribe` for the display-metadata prerequisite, then `engine-implementer` for
`0044_m10_renter_publication_display_period.py`, then `app-implementer`, then
`statement-reviewer` (required — a renter reads this).

**Status (12.09.2026):** technically complete, verified and locally merged as `ed28f55`.
`M10-PUB-F08`, migration `0044`, the
ORM/API projection and the renter route group are green. Statement titles use only the immutable
source period; UVI titles use only the immutable source month. Activation, overview, both document
lists, exact copy, renter-aware entry and context switching are covered by `28` web fixtures. The
statement review and boundary re-audit are clean; the full gate passes `2048` Python and `238` web
tests. The named red window is closed.

Owner activation follow-up `2e65aa9` is also locally merged. The Unit overview's lower-right
`Mieterportal` module now issues an activation code for an explicitly identified current renter
through the existing owner-only endpoint and displays the raw code once with its exact
Europe/Berlin expiry. Overlapping issuance is blocked in the UI; no code is stored in browser
storage. The API projection enables the module only for an owner with exactly one unconflicted
current tenancy. Focused API/web tests pass `4 + 10`; statement/UI and boundary reviews are clean;
the full gate passes `2052` Python and `246` web tests.

Demo repair `4032889` is locally merged. Portfolio Preview now exposes the action for rented units
and implements a fully synthetic issuance, activation, context, overview and empty-document path.
Codes are fresh, expire after seven days, are spend-once and remain only in module memory. Recognized
preview refusals never fall through to the live backend, wrong account/tenancy/renter paths are
denied, and the same-tab portal link is preview-only. Statement/UI and boundary reviews are clean;
the full gate passes `2052` Python and `258` web tests.

- New route group `apps/web/src/app/renter/[tenancyId]/`, separate from `a/[accountId]`.
- Before the screen work, extend each immutable publication with the underlying statement period or
  UVI month. The owner request stays unchanged; owner/list response items add `periodStart`,
  `periodEnd` and `documentMonth`. No title may be guessed from a filename or publication time.
- German copy, `docs/05` tokens, WCAG 2.1 AA and BFSG per `CLAUDE.md` § 9.
- Screens: own tenancy overview, published statement documents, published UVI documents. Nothing
  else. No landlord figures, no other party, no all-party allocation view.
- The context switcher appears only when the person holds more than one context.
- Use the exact `M10-COPY-01…06` strings from `docs/02`, including the generic activation refusal,
  the `Als Mieter` switcher group and `Als PDF speichern` action. Do not paraphrase them.

**Done when:** the statement review has no unresolved finding, no renter-facing string is invented,
and the six-screen owner demo path in `docs/06` is unchanged.

#### Lane I — investment cockpit (`docs/14`)

##### M10-I0 — executable Page-07 fixtures

**Agent:** `spec-scribe`. This is a mandatory red window — declare it in `.lokara-red`
(`AGENTS.md` § 4).

**Technical completion (12.09.2026):** the executable suite passes `94` tests and covers the final
top-level Wizard AfA provenance and one-cent repayment-axis guards. The read-only statement review
is clean, and the fast gate passes with `734` pure-package tests. Negative closing balance on early
payoff remains an explicit specification-authority limit because `docs/14` does not define payoff
capping; no behavior was invented. All `docs/14` production blockers remain active. The named red
window is closed. The full gate passes with `2146` Python and `258` web tests. Commit, merge and push
are not done.

- `packages/rules-store/tests/berkay_14_golden.py` is the approved **data-only** oracle with exactly
  `14-F01`–`14-F14`. Turn it into executable engine tests, following
  `packages/afa-engine/tests/test_berkay_10_executable.py` as the precedent.
- Cover `R1`–`R10`, all fifteen edge cases `14-E01`–`14-E15` and the `14-K01`–`14-K19` conventions
  as behaviour, including the `14-E08` non-positive-repayment hard block and the `—` /
  "Daten unvollständig" partial results. No fabricated zero anywhere.

**Done when:** the executable suite covers exactly `14-F01`–`14-F14`, fails against absent code, and
no golden value from the merged oracle moved.

##### M10-I1 — pure `packages/investment-engine`

**Agent:** `engine-implementer`.

- New pure package following the `packages/afa-engine` layout; register it in the `LAYERS` table of
  `scripts/check_engine_purity.py` or purity does not cover it.
- Integer cents, integer basis points, KPI ratios in hundredths, `Decimal` with `ROUND_HALF_UP` at
  exactly the specified boundaries, no `float` across the contract.
- Implement `R1`–`R10`: effective rent, NOI, the twelve-row annuity schedule with its reconciliation
  probes, AfA reference with Page-03 provenance precedence, the flat tax scenario, cashflow, the
  seven KPI formulas, completeness and both sensitivity axes.
- Every result carries source evidence, `Rechtsstand` and its production-blocked state, matching the
  `packages/guard-engine` / `packages/uvi-engine` provenance pattern.

**Done when:** all `14-F01`–`14-F14` pass, `scripts/gate.sh fast` is green, `.lokara-red` is
removed, and `mypy --strict` passes with no float in money.

##### M10-I2 — Prüfobjekt persistence

**Approved persistence contract (12.09.2026):** `docs/14` § 4.7 supersedes the former no-schema
marker for M10-I2 only. It fixes the three append-only tables, correction streams, composite account
FKs, canonical JSON bytes and SHA-256 replay contract, nullable frozen layout selection and exact
RLS boundary. All Page-07 production blockers remain active. RED fixtures precede implementation.

**Agent:** `engine-implementer`. Migration `0045`.

- Immutable, account-scoped Prüfobjekt input snapshot, KPI result and versioned layout per
  `docs/14` §§ 4.1–4.3 and 4.7. Missing data stays missing; it is never stored as zero.
- Financing provenance (`annahme` / `indikativ` / `angebot`) and AfA provenance are stored, not
  derived at read time.
- Composite FKs, FORCEd RLS, `WITH CHECK` policies, refused cross-account write assertions,
  append-only corrections.
- A Prüfobjekt is not a `Building`. It must not enter statements, tax exports or the demo path.

**Done when:** `check_rls_coverage` and `check_fk_isolation` are green with recorded counts, and a
frozen snapshot reproduces its KPI result byte-for-byte.

**Technical completion (16.09.2026):** migration `0045`, mapped metadata and the three append-only
tables satisfy the approved § 4.7 contract. A real `0044 → 0045` application and all `109` focused
persistence tests pass, including byte-identical replay, correction streams, immutable writes,
cross-account refusal and renter-context refusal. The full RLS suite passes `113`; RLS covers `80`
tenant tables and FK isolation covers all `161` tenant edges. The read-only boundary audit has no
finding, the full gate passes `2259` Python and `258` web tests, and `.lokara-red` is absent. The
slice is uncommitted; all Page-07 production blockers remain active.

##### M10-I3 — investment API and entitlement

**Agent:** `app-implementer`.

- Owner-scoped routes under `/a/{accountId}` for Prüfobjekt create, KPI read, sensitivity and the
  Bank-PDF view. `EMPLOYEE` and `TAX_ADVISOR` receive no investment access.
- Enforce the D4 entitlement server-side. Hiding the navigation entry is not authorization.
- No pricing, plan name or purchase flow.

##### M10-I4 — investment cockpit and Bank-PDF

**Agent:** `app-implementer`, then `statement-reviewer` (required).

- `/a/{accountId}/investment` with the seven KPIs, both sensitivity axes and the twelve-month
  schedule. Missing KPIs render `—` with "Daten unvollständig".
- The `14-K19` colours are liquidity indicators under the user's own assumptions. No score, ranking,
  winner, default target return or recommendation (`docs/14` § 10).
- The Bank-PDF is `f(frozen snapshot, versioned layout) → bytes` with **no** recalculation, the
  fixed block order of `docs/14` § 4.6, the permanent
  "Auslauf zum Kaufpreis, nicht zum Beleihungswert" LTV label, the § 2 artifact disclosure and the
  approved "rechtskonform, keine Rechts- oder Steuerberatung" disclaimer. It contains no renter
  name and is not an export, archive, valuation or credit decision.

**Done when:** two renders of one frozen snapshot are byte-identical, `14-F12`'s partial-data view
still renders, and the statement review has no unresolved finding.

#### M10-F — review and closure

- `boundary-auditor` over the renter context, activation, publication and investment tables. A
  read-only auditor proves findings inside a rolled-back transaction (`AGENTS.md` § 7).
- `statement-reviewer` for the renter portal and the Bank-PDF.
- `docs-reconciler` at close.
- Prove the future M10 migrations from consolidated head `0040` on an empty disposable database and
  compare development schema parity.
- Run fast, full and non-fresh demo gates. Record `scripts/pdf_fingerprint.sh` before and after: the
  ordinary NK/heating statement must remain `c4eecb355d57cec620dfcb0134fc9141` at 149275 bytes.
- Update this plan with actual evidence and the remaining production blockers.

**Done when:** activation links only the intended Person and tenancy; spent, foreign and direct-write
attempts fail; renters see only their tenancy; and the investment cockpit uses the annuity schedule.

#### M10 production blockers — technical closure never clears these

- Sixteen of the eighteen Page-07 register rows remain `verify-before-production`: every KPI
  default, threshold, the 30/360 planning recurrence, the Bank-PDF choices and the financing-source
  labels (`docs/14` § 3).
- The two source files Page 07 names, `Lokara_Investitionsmodul_Demo.html` and
  `AfA-Wizard_Konzept_Entwurf.md`, do not exist in the repository and are not reconstructed.
- The capital-markets permission claim is unconfirmed (`docs/14` § 2).
- The negative `steuerCent` scenario, the editable 42% marginal-tax default and the Page-03 R13 /
  Page-07 R3 interest ambiguity stay scenario arithmetic, never a tax result.
- Renter-facing UVI content stays blocked until the supplied `R-UVI-01`/`R-UVI-02` rows appear in
  the authoritative CSV and the other authority prerequisites in `docs/16` are resolved; the green
  vendored PLZ lookup, approved display copy and a portal do not clear them.
- Tickets remain unspecified and unscheduled.

### M11 — Native apps, billing and load test

**Prerequisite:** M10. Mobile, billing and the load test consume the shipped API and web contracts;
they introduce no second backend and no second auth model. `docs/01` keeps Expo/React Native,
Stripe, RevenueCat and Locust as locked decisions.

- Expo mobile app using the same FastAPI API, auth model and client patterns. Capacitor/PWA remains
  the fallback if native delivery slips.
- Stripe web billing and RevenueCat mobile billing.
- Locust load test at roughly 100 concurrent users before launch.

**Done when:** the mobile app logs in and reads one real screen.

---

## 6. Documentation reconciliation queue

Phase D1 owns the existing-doc reconciliation in the order below. Legal and calculation detail
assigned to `docs/09`–`docs/16` stays there; existing docs record only the dependency and settled
cross-cutting claim. Source coverage and golden fixtures land with every calculation-doc change.

| Existing doc                                                                | Why it needs work                                                                                                                                                                                       |
| --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `docs/03-nk-heating-engines.md`                                             | Align the existing Page 01b contract and fixtures with the restored single Slice A. Preserve the current F02 decisions and record the unresolved DWD/UVI dependency without duplicating `docs/16`.      |
| `docs/08-statement-document.md` + relevant `docs/02-data-model.md` sections | Complete the Page 01 transcription, source coverage and `08-Fxx` fixtures. Record dependencies on future catalogue, tax, bank and UVI specs instead of copying their contracts here.                    |
| `docs/00-product-overview.md`                                               | Reconcile the product promise with shipped status, the Page 01 period hard stop, the owner-only M6-B final archive and still-incomplete renter delivery.                                                |
| `docs/04-web-app-structure.md`                                              | Separate shipped structure from future architecture and preserve M10 renter ownership. Future packages remain dependencies, not shipped components.                                                     |
| `docs/01-tech-stack-and-decisions.md` only                                  | Reconcile locked decisions, shipped architecture and stale TODOs after `docs/04`. `docs/01-tech-stack-explanations.md` is Emir-owned and outside reconciliation; do not read, assess, use or modify it. |
| `docs/06-demo-scenarios.md`                                                 | Reconcile the current demo, M5 bootstrap/onboarding limits and the D1 Page 01 output contract.                                                                                                          |
| `docs/07-compliance.md`                                                     | Include only settled cross-cutting claims during D1. Defer detailed Page 04 rules to `docs/11` and perform final reconciliation after the relevant D2 specs exist.                                      |
| `docs/05-design-system.md`                                                  | Ordinary drift review only; no missing Berkay calculation contract is assigned here.                                                                                                                    |

Create these docs because no current file owns their complete contracts:

| New doc                       | Reason                                                                                                                                   |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `docs/09-betrkv-catalogue.md` | Versioned operating-cost classification and allocation rules from Page 02.                                                               |
| `docs/10-afa.md`              | AfA inputs, methods, guards, rounding and fixtures from Page 03.                                                                         |
| `docs/11-tax-export.md`       | Anlage V and byte-exact DATEV rules from Page 04.                                                                                        |
| `docs/12-guards-deadlines.md` | Reusable deadline/guard rules from Page 05.                                                                                              |
| `docs/13-contract-clauses.md` | Clause-selection decisions, risk gates and workflow routing from Page 06; complete clause/action texts remain a separate missing source. |
| `docs/14-investment-kpis.md`  | KPI definitions, financing assumptions and calculation order from Page 07.                                                               |
| `docs/15-bank-matching.md`    | Deterministic signals, confidence outcomes and review rules from Page 08.                                                                |
| `docs/16-uvi.md`              | Complete UVI calculation, DWD import, cadence, delivery and fallback contract from the annexes and linked Pages.                         |

The new-doc table is the output inventory, not a second source assignment: the Berkay source
registry above remains authoritative. Create these only in D2 and in its dependency order.

---

## 7. Product floor

M0 is complete. M1–M4 are the current green, demoable floor: a persisted-data operating-cost and
heating calculation view with CO₂ allocation and tenant isolation. They are not yet fully
spec-closed. D1 is complete; approved 17.08.2026; final reconciliation closed 18.08.2026. D2 and all
`docs/09`–`docs/16` transcriptions are complete, approved and merged. D3 is complete and approved;
the correspondence retirement closes the documentation program. Slice A is complete, approved and
merged locally; Slice B is complete and locally merged after the Round-4 Block-(c) correction.
Slices A–C retain their order and reconcile implementation with Pages 01b, 01 and 02
before feature work continues.
M6-B ships finalized owner-only tenant archives; renter delivery and portal publication wait for M10.

Protect that floor. Correctness comes before breadth. If work stops, stop at a green state.
