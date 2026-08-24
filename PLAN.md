# PLAN.md — Lokara roadmap

This file answers two questions:

1. What is built?
2. What comes next?

Build in the execution order below. The current program completes and approves all documentation
before any implementation resumes. Each later slice ends green. Engines and golden fixtures come
before UI. Dates are communication events, not planning inputs.

## Current state

- M0 is complete. M1–M4 are built and green under their original scope, but are not yet fully
  verified against all Berkay specifications.
- The v4 migration is complete. The old TypeScript backend is gone. Mobile moved to M10.
- Composite foreign-key isolation and M5a identity/RLS are complete.
- Three earlier Page 01b fixes remain complete. Slice A now gives Page 01b technical implementation
  closure: all 34 fixture IDs execute through one orchestrator and the full and non-fresh demo gates
  are green. Emir approved Slice A and it was merged locally on 21.08.2026; open wording, cumulation and
  `verify-before-production` flags remain explicit.
- Berkay's Pages 01–08 and 01b exist. They are primary implementation specs, not background notes.
- Round 4 transcription was merged locally on 23.08.2026 as a documentation/fixture correction.
  It supersedes the
  stated Page-01b wording/cumulation, Page-02 classification, AfA K09, Eichfrist and § 559 details
  only where its source says so; all `Konvention`/`UNSICHER` labels remain. The 180-row register
  count remains unresolved and is not edited here. Page 07 planning remains blocked by its two
  missing companion files, notwithstanding earlier summary wording.
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
  shipped. Renter activation/portal remains M10; adviser profile, mapping and tax functions remain
  M7. **All of M6 is locally merged into `main`**: M6-A
  (temporal advances, `d82abcc`), M6-B (finalized archives, `f578f2f`), M6-C1 (the pure matching
  engine, `8306b68`) and M6-C2 (bank persistence, the § 3.1 adapter and owner-scoped endpoints,
  `92e1318`), followed by M6-C3-0's migration-`0020` invariant repair. **M6-C3a is technically
  complete, development-synchronized and locally merged. C3b's three job entrypoints and C3c's
  landlord Zahlungen screen (`6995bc4`) are technically complete and locally merged, which closes
  M6-C and with it M6.**
- **G1 is technically complete and locally merged (`6c257f8`).** The pure `packages/guard-engine`
  executes W1, W2 and W4 for `12-F01`–`12-F06` and `12-F11`–`12-F13`. It adds no database, API, UI,
  scheduler or PDF consumer. W2 now runs the unified six-year MessEV Eichfrist; the slice had
  reversed that merged round-4 decision, and the reversal was undone before the merge.
  `main` is ahead of `origin/main`, which still points to `f372f67`.
  U is next; M9 reminder and delivery integration remains open.

---

## Berkay source registry

Every Page is a calculation or deterministic legal/product-rule source. A milestone may not use a
Page directly from `berkay-work/`. First transcribe it into the target `docs/` file and create its
golden fixtures. Existing docs are not assumed correct merely because they already exist.

| Source | Target | Fixtures | Current coverage and dependency |
| --- | --- | --- | --- |
| Page 01 — Die Abrechnung | `docs/08-statement-document.md` + data changes in `docs/02` | `08-F01…F24` | Full D1 source trace and exact 24-ID data oracle transcribed. Slice B is complete and locally merged for the persisted M3/M4 path, including the Round-4 Block-(c) correction. M6-A/B ship actual-advance reconciliation and owner-only technical final archives; M6-C1/C2/C3-0/C3a ship bank matching, ledger persistence, the matching service, five owner APIs and audited invariants on local `main`; C3b's scheduler port and three job entrypoints and C3c's Zahlungen screen are technically complete and locally merged. M10 renter delivery remains open. |
| Page 01b — Heizkosten & CO₂ | `docs/03-nk-heating-engines.md`; output rules also in `docs/08` | Every `01b-Fxx`, including suffix variants | Full source trace and exact 34-ID orchestrator suite are green; Slice A was approved and merged locally 21.08.2026. Self-billing and MDL converge on typed readiness, findings, provenance, device evidence, separate unapplied risks and annual comparison; migration `0006`, adapter, API, web and PDF projections are included. Technical closure does not approve flagged values, final block-(c) wording, risk cumulation, MDL ingestion or monthly DWD/UVI work. |
| Page 02 — BetrKV catalogue | `docs/09-betrkv-catalogue.md` + `packages/rules-store` | `09-F01…F32` | Slice C is technically complete (23.08.2026): full/non-fresh demo gates, unchanged PDF fingerprint and both reviews are green. `09-K01…K11`, `trinkwasseruntersuchung` and the administration-cost legal check remain production-blocking. |
| Page 03 — AfA | `docs/10-afa.md` | `10-F01…F34` | Complete transcription approved and merged 21.08.2026. The exact 34-ID data oracle covers purchase-cost ordering, three allocation routes, AfA/use rounding, the 15% guard and annual finance paths. Four CSV rows are `geprüft`; 42 remain `verify-before-production`. Weg B placeholders and the F11 month/day choice block production. No implementation exists. |
| Page 04 — Anlage V + DATEV | `docs/11-tax-export.md` | `11-F01…F16` | Complete transcription approved and merged 21.08.2026. The data-only oracle covers both ledger views, § 11 assignment, splits, readiness, archive and blocked EXTF conventions. Seven register rows are `geprüft`; six remain `verify-before-production`. No implementation exists; flagged values block real output. |
| Page 05 — Wächter/Fristen | `docs/12-guards-deadlines.md` | `12-F01…F24` | Complete transcription approved and merged 21.08.2026. G1 executes the nine selected W1/W2/W4 cases (`12-F01`–`F06`, `F11`–`F13`) through the pure guard engine on `main`. Sixteen of the 18 Page-specific register rows remain `verify-before-production`; rows 128 and 129 were closed by round 4 against § 34 Abs. 2 MessEV and MessEV Anlage 7 and still need matching register entries. W3 and W5–W8 plus all consumers remain open. |
| Page 06 — Vertragsklauseln | `docs/13-contract-clauses.md` | `CLAUSES-F01…F19` | Complete transcription approved and merged 21.08.2026 with the exact 19-ID data oracle, 17-row register surface and explicit ownership boundaries. No implementation exists. The source defines routing and risk rules, but not a complete clause-text/version catalogue or complete Mieterhöhung/Kündigung/Mahnung bodies; those missing sources still block M8. |
| Page 07 — Investment-KPIs | `docs/14-investment-kpis.md` | `14-F01…F14`, with an exact `KPI-*` alias map | Complete transcription approved and merged 21.08.2026 with all 14 data-only fixtures, 18 register rows and explicit Page-03/Page-09/Page-11 boundaries. No implementation exists; flagged conventions, interest-source ambiguity and absent concept sources block production and M10. |
| Page 08 — Bank-Matching | `docs/15-bank-matching.md` | `BANKMATCH-F01…F13` | Complete transcription approved and merged 20.08.2026. Approved `docs/15` and its oracle preserve F03 as the Page's omitted E12 case, so all thirteen entries are executable dictionaries. M6-C1/M6-C2/M6-C3-0/C3a ship the engine, persistence, adapter, matching service, five owner endpoints and audited database invariants on local `main`; C3b's scheduler port and three job entrypoints and C3c's *Zahlungen* screen are technically complete and locally merged. |
| UVI + DWD annexes | `docs/16-uvi.md` | Source-named Block A–D2, DWD and Heizspiegel fixture maps | Complete D2 transcription approved and merged 21.08.2026. U0 transcribes round 4's monthly `hdd_3807` dataset, persisted station-assignment convention, display-rounding decision and K13 vintage rule. Production Blocks C/D2 still require a chosen PLZ geodataset and three missing UVI register rows. UVI calculation, readings and document implementation do not exist; G1 supplies only the W4 cadence evaluator. |

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
  oracle for `12-F01…F24`. All eighteen Page-specific register rows remain
  `verify-before-production`; the 5-year/6-year meter conflict and every other authority gap remain
  explicit. Emir approved the transcription on 21.08.2026. G1 now executes exactly the nine
  selected W1/W2/W4 cases; the remaining Page-05 guards and every application consumer stay open.
- UVI/DWD has a complete annex/Page/W4/register/non-goal/correspondence trace and source-named
  data-only oracles for Blocks A–D2, all nine annual DWD PLZ values/import guards and all 18
  Heizspiegel rows. Emir approved it and the slice was merged on 21.08.2026; UVI calculation,
  readings and document work are not implemented, while G1 prepares only W4 cadence. Monthly DWD data and
  station-to-PLZ authority remain production-blocking.
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

| Stage | Status | Work | Required result |
| --- | --- | --- | --- |
| D1 | **complete; approved 17.08.2026; final reconciliation closed 18.08.2026** | Reconcile existing `docs/00`–`docs/08` | Documentation and golden fixtures only; no implementation source changes. |
| D2 | **complete; approved 21.08.2026** | Create source-backed `docs/09`–`docs/16` | All assigned transcriptions are approved and merged, including `docs/14`; the final `docs/07` tax/archive reconciliation is approved. The phase added documentation and data-only fixtures, not investment implementation. |
| D3 | **complete; approved 21.08.2026** | Complete extraction and retire Berkay correspondence | Single historical ledger in `docs/03`, one current round-five question file. Round 4 settled its answered decisions; Round 5 retains only its unanswered/source-delivery follow-ups and the external/legal-source gaps. Governance, permanent dependency guard and joint deletion remain intact. |
| A | **complete; approved and merged 21.08.2026** | Reconcile M2 with Page 01b | All 34 Page 01b fixtures, persistence, projections, full gate, non-fresh demo gate and PDF review are green. The approved implementation keeps the two unresolved Page 01b choices explicit. |
| B | **complete; locally merged 23.08.2026** | Reconcile M3–M4 with Page 01 | Persisted calculation and extraction revalidated; Block-(c) renders only as the conditional owner-residual subline; full and non-fresh demo gates plus statement review are green. Finalization shipped in M6-B and the payment ledger in M6-C2. |
| C | **technically complete; locally merged 23.08.2026** | Reconcile M1 with Page 02 | NK eligibility, allocation, classification and rounding repairs are verified by full/non-fresh demo gates, unchanged PDF fingerprint and both required reviews. Page 02 remains production-blocked by `09-K01`–`09-K11`, the Trinkwasser route and the administration-cost legal check. |
| M5 | After A–C | Roles, URL context and switcher | **Complete.** Secure bootstrap, membership/assigned-building authorization and the URL-based account chooser/switcher are shipped on `main` (`a748729`). Renter portal is M10; adviser profile/mapping and tax functions are M7. |
| M6 | **Technically complete; locally merged 24.08.2026** | Bank, ledger and finalized statements | Implement approved `docs/08` and `docs/15`. **M6-A, M6-B, M6-C1, M6-C2, M6-C3-0 and M6-C3a are locally merged**: temporal advances, BGH minimum #4, immutable snapshots, isolated tenant archives, the pure matching engine against all thirteen fixtures, nine bank/receivable/ledger tables, the § 3.1 adapter, matching service, final `0021` and owner-scoped endpoints. **C3b's scheduler port and three job entrypoints are locally merged**: no schema change, no endpoint, one consent precondition on every AIS pull. **C3c's Zahlungen screen is technically complete and locally merged**: a client-only owner screen that records one final confirm/reject/duplicate outcome, with no manual assignment and no backend change. That merge closes M6-C and completes M6; delivery and the renter portal remain M10. |
| G | **Technically complete and reviewed 24.08.2026; uncommitted and unmerged** | Shared guard foundation | Pure W1, W2 and W4 evaluators execute all nine selected Page-05 fixtures with explicit source identity, caller-supplied rule evidence and unresolved production blockers. No database, API, UI, scheduler or PDF integration. |
| U | After G | UVI comparison, calculation and document | Implement approved `docs/16`, including the heating-only comparison, monthly readings, labelled fallbacks and tenant document. Scheduled delivery waits for M9; portal publication waits for M10. |
| M7 | After U | Tax export and AfA | Implement approved `docs/09`–`docs/11`. Build computation paths and archives; flagged register values continue to block real output. |
| M8 | After M7 | Document and letter engine | Implement approved `docs/13` with versioned clauses and risk gates. |
| M9 | After M8 | Reminders, email and checklists | Extend the existing W1/W2/W4 foundation with the remaining guard projections, reminders, delivery and UVI scheduling from approved `docs/12`. |
| M10 | After M9 | Portals, investment, billing and native apps | Implement renter activation and portal work, the approved `docs/14` investment cockpit, billing and mobile apps. |

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
- three BFH case numbers marked `ZITAT UNSICHER`;
- the Page 04 ten-day-rule BFH citation.

The computation paths may be built. Nothing using these values may be sent to a real Steuerberater
or Finanzamt until each value is confirmed.

---

## 2. Hard rules

1. **No calculation without complete transcription.** Follow the Berkay source registry and its
   coverage-table gate. Transcribe first, create every golden fixture, then implement. Never invent
   a legal value. The authoritative register currently has 130 of 180 rows marked
   `verify-before-production`.
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

The Expo mobile skeleton is not part of the completed foundation. It moved to M10.

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
- Add the landlord *Zahlungen* confirmation/rejection screen without inventing manual assignment.
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
     `spec-scribe`**, the one role whose deliverable is a *failing* fixture — the gate is fighting
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
  account isolation right and constrained nothing *inside* one account. A `payment_allocation`
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
  could be minted for the wrong renter from a *rejected* confirmation. `open_costs_cents` and
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
  counts and 68 legacy Auto confirmations are unchanged. C3a excludes jobs, the *Zahlungen* screen,
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
- **M6-C3c — Zahlungen screen. Technically complete; locally merged 24.08.2026 (`6995bc4`).** The German landlord *Zahlungen*
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
  expose — that payload gap is C3a's and stays open. (4) The E2E signal is rendered as *noch nicht
  ausgewertet* rather than as an unmet criterion, because `docs/15` § 4 marks it inert and the
  engine returns 0 for it unconditionally; it goes live only when the stored reference exists.
  (5) The screen is owner-only in navigation as well as in the API: every route behind it calls
  `require_owner`, so the nav entry is hidden for `EMPLOYEE` to avoid a guaranteed dead end. That
  is navigation honesty, not authorization — the API re-authorizes independently.
  **Recorded, not fixed.** `require_owner` answers 403 with the English, route-inaccurate detail
  `"Only owners may create buildings"` (`authorization.py`), which the client would print verbatim;
  the ledger renders `created_at` through a timezone-naive string split, so a late-evening booking
  on a UTC server can show the previous calendar day; the loading and error copy
  *"Bitte API und Datenbank prüfen"* is developer-facing but is the established house convention in
  seven other screens and was not diverged from here; `Ablehnen` and `Dublette` write an immutable
  record with no confirmation step; and a decided proposal does not link to the journal entry it
  produced. None of these is introduced by this slice's own code except the last two.

**Hard constraints:**

- Provider transaction identity is unique on `(account_id, bank_account_id,
  provider_transaction_id)`, never on the provider ID alone.
- The payment ledger is append-only. Reversals append compensating rows; nothing is edited.
- An IBAN is learned only from a confirmed match and never when null.
- The § 5.2 Largest-Remainder tie-break convention is missing from the authoritative source. The
  engine and service tests prove refusal and complete rollback on an exact tie; no tie-break is
  invented.
- Matching confidence is a Lokara convention and is never presented as legal support for a match.
- Background jobs ship as service functions behind a scheduler port. Redis, Arq and Celery stay
  uninstalled until a real worker slice; `docs/01` D7 keeps that pick open.

**M6-C closed when:** all thirteen fixtures pass through the application service and persistence,
the three job entrypoints are callable, a landlord can confirm or reject a Review proposal in the
UI, every isolation boundary remains green, and the rendered statement is unchanged. Every one of
those conditions is met on `main`, so **M6-C is closed** and **M6 is technically complete**;
delivery and the renter portal remain M10. Technical closure is not legal-production approval: the
Page-08 weights and thresholds stay `verify-before-production` at `Rechtsstand 07/2026`, the
180-day AIS consent window still has no register row, and the § 4 stored-reference signal stays
inert until its source gap is answered.

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

**U0 status:** the round-4 transcription is complete and locally merged as `738e048`, not pushed.
`docs/16` §§ 7.1/7.2 carry the monthly `hdd_3807` dataset and the persisted station-to-PLZ
convention, § 4 carries the display-rounding decision and § 8.2 carries the K13 vintage maintenance.
The oracle gained four constants and no golden value moved. U0 is documentation plus data-only
fixtures; no UVI engine, importer, schema, API, UI, PDF or delivery code exists. U1 implements the
pure engine next.

**Approved-spec prerequisite:** `docs/16`, spec-closed Slice A and the G1 cadence foundation.

- Implement the specified heating-only comparison with labelled fallbacks and no extrapolation.
- Add monthly readings, the UVI calculation and the separate tenant document.
- Keep scheduled delivery in M9 and portal publication in M10.

**Done when:** every `docs/16` calculation fixture passes, the specified monthly `hdd_3807` input and
persisted station assignment are implemented, the PLZ geodataset is chosen, the missing UVI register
rows exist and the UVI document is tenant-isolated. Round 4 resolved the dataset and Block C
rounding order; production Blocks C/D2 remain blocked by the unchosen PLZ geodataset and missing
UVI register rows. G1 remains technically closed.

### M7 — Tax export and AfA

**Approved-spec prerequisite:** `docs/09`–`docs/11`, including every fixture and every
`verify-before-production` marker.

- Pure `packages/export-engine` for Anlage V and DATEV EXTF.
- DATEV output is byte-exact Windows-1252 with semicolons and CRLF.
- Readiness check and immutable export archive with hash and timestamp.
- Pure `packages/afa-engine`, AfA wizard, 15% guard and loan-interest prefill.
- Preserve every `verify-before-production` flag from the M7 warning above.

**Done when:** DATEV and Anlage-V golden tests pass byte-exactly and the export is archived
immutably. Production use remains blocked until flagged values are verified.

### M8 — Document and letter engine

**Approved-spec prerequisite:** `docs/13`, including its legal/convention labels, risk gates,
non-goals and all `CLAUSES-Fxx` fixtures, plus a separate approved source-backed catalogue for the
missing clause bodies and complete Mieterhöhung/Kündigung/Mahnung bodies.

- Versioned clause blocks from the later approved text catalogue and stored clause composition.
- A legal change creates a new clause version and flags affected contracts.
- Page-06 risk/routing inputs for Mieterhöhung, Kündigung, Mahnung and SEPA mandate; the complete
  action texts are not supplied by `docs/13`.
- Destatis VPI adapter and stub Mietspiegel provider.

**Done when:** a contract is generated from versioned clauses and a clause update identifies every
affected contract.

### M9 — Reminders, email and checklists

**Approved-spec prerequisite:** `docs/12` and the G1 foundation. M9 extends the existing W1/W2/W4
engine with remaining guard projections, reminders, email and checklists without redefining those
rules.

- Add the remaining arrears and move-in/out guard projections and compose them with the existing
  § 556, Eichfrist and UVI cadence evaluators.
- Stubbed email provider using Lokara's domain and the landlord as the From-name, with an immutable
  delivery-status ledger.
- Suppress bounced and complained-about addresses.
- Count the § 556 access deadline backwards. UVI and annual statements keep separate delivery rules.
- Three-colour delivery indicator.
- Data-driven checklist library that creates reminders.

**Done when:** the § 556 deadline escalates correctly and delivery status is visible.

### M10 — Portals, modules and native apps

**Approved-spec prerequisite:** `docs/14`; its calculations also depend on approved `docs/09`–
`docs/11`. Renter activation remains governed by `docs/02` and the M5 no-write guard.

- Renter activation, renter portal, tickets and tax-adviser guest access.
- Investment pipeline and seven-KPI cockpit.
- `renter.person_id` starts NULL and is written only by single-use activation-code redemption.
- Decide and enforce whether `renter.person_id` becomes immutable after activation.
- Expo mobile app using the same FastAPI API, auth model and client patterns. Capacitor/PWA remains
  the fallback if native delivery slips.
- Stripe web billing and RevenueCat mobile billing.
- Locust load test at roughly 100 concurrent users before launch.

**Done when:** activation links only the intended Person and tenancy; spent, foreign and direct-write
attempts fail; renters see only their tenancy; the investment cockpit uses the annuity schedule; the
mobile app logs in and reads one real screen.

---

## 6. Documentation reconciliation queue

Phase D1 owns the existing-doc reconciliation in the order below. Legal and calculation detail
assigned to `docs/09`–`docs/16` stays there; existing docs record only the dependency and settled
cross-cutting claim. Source coverage and golden fixtures land with every calculation-doc change.

| Existing doc | Why it needs work |
| --- | --- |
| `docs/03-nk-heating-engines.md` | Align the existing Page 01b contract and fixtures with the restored single Slice A. Preserve the current F02 decisions and record the unresolved DWD/UVI dependency without duplicating `docs/16`. |
| `docs/08-statement-document.md` + relevant `docs/02-data-model.md` sections | Complete the Page 01 transcription, source coverage and `08-Fxx` fixtures. Record dependencies on future catalogue, tax, bank and UVI specs instead of copying their contracts here. |
| `docs/00-product-overview.md` | Reconcile the product promise with shipped status, the Page 01 period hard stop, the owner-only M6-B final archive and still-incomplete renter delivery. |
| `docs/04-web-app-structure.md` | Separate shipped structure from future architecture and preserve M10 renter ownership. Future packages remain dependencies, not shipped components. |
| `docs/01-tech-stack-and-decisions.md` only | Reconcile locked decisions, shipped architecture and stale TODOs after `docs/04`. `docs/01-tech-stack-explanations.md` is Emir-owned and outside reconciliation; do not read, assess, use or modify it. |
| `docs/06-demo-scenarios.md` | Reconcile the current demo, M5 bootstrap/onboarding limits and the D1 Page 01 output contract. |
| `docs/07-compliance.md` | Include only settled cross-cutting claims during D1. Defer detailed Page 04 rules to `docs/11` and perform final reconciliation after the relevant D2 specs exist. |
| `docs/05-design-system.md` | Ordinary drift review only; no missing Berkay calculation contract is assigned here. |

Create these docs because no current file owns their complete contracts:

| New doc | Reason |
| --- | --- |
| `docs/09-betrkv-catalogue.md` | Versioned operating-cost classification and allocation rules from Page 02. |
| `docs/10-afa.md` | AfA inputs, methods, guards, rounding and fixtures from Page 03. |
| `docs/11-tax-export.md` | Anlage V and byte-exact DATEV rules from Page 04. |
| `docs/12-guards-deadlines.md` | Reusable deadline/guard rules from Page 05. |
| `docs/13-contract-clauses.md` | Clause-selection decisions, risk gates and workflow routing from Page 06; complete clause/action texts remain a separate missing source. |
| `docs/14-investment-kpis.md` | KPI definitions, financing assumptions and calculation order from Page 07. |
| `docs/15-bank-matching.md` | Deterministic signals, confidence outcomes and review rules from Page 08. |
| `docs/16-uvi.md` | Complete UVI calculation, DWD import, cadence, delivery and fallback contract from the annexes and linked Pages. |

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
