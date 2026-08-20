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
- Three earlier Page 01b fixes are complete. The Page 01b source transcription is
  complete; its executable-golden-test gate, confirmed implementation gaps and final verification
  still block M2 spec closure.
- Berkay's Pages 01–08 and 01b exist. They are primary implementation specs, not background notes.
- Page 01 is completely transcribed in `docs/08`/`docs/02` with a 24-ID data oracle and green
  consistency checks. Page 01b's transcription is complete but its confirmed implementation gaps
  remain. Page 02 is merged in `docs/09` with an exact 32-ID data oracle; its production catalogue
  and engine integration remain open. Page 08 is completely transcribed, approved and merged with
  all thirteen executable cases. Page 05 is completely transcribed and approved with an exact
  24-ID data oracle. The UVI annex is approved and merged in `docs/16` with source-named data-only
  fixtures. Page 03 is completely transcribed, approved and merged in `docs/10`; Pages 04, 06 and
  07 still need D2 transcription before related work.
- Phase D1 is **complete; approved 17.08.2026; final reconciliation closed 18.08.2026**. All
  implementation remains paused until D2–D3 have been reviewed and approved.
- Phase D2's `docs/15` review gate was approved and its slice merged on **20.08.2026**. The
  `docs/12` and `docs/16` review gates were approved and their slices merged on **21.08.2026**.
  The `docs/10` slice was approved and merged on **21.08.2026**; D2 continues with `docs/11`.
- Phase D3 starts only after Emir reviews and approves D2. It proves that the seven Berkay
  correspondence files have been completely extracted, moves every genuinely unresolved item into
  one current `FRAGEN-an-Berkay-04.md`, updates governance references and then deletes the retired
  correspondence. Implementation remains paused through D3.
- M5 is paused. Its secure bootstrap foundation is complete on `slice/m5-bootstrap-contexts`,
  but the slice is not merged yet.
- That M5 foundation has not added a new dashboard, portal or account switcher.

---

## Berkay source registry

Every Page is a calculation or deterministic legal/product-rule source. A milestone may not use a
Page directly from `berkay-work/`. First transcribe it into the target `docs/` file and create its
golden fixtures. Existing docs are not assumed correct merely because they already exist.

| Source | Target | Fixtures | Current coverage and dependency |
| --- | --- | --- | --- |
| Page 01 — Die Abrechnung | `docs/08-statement-document.md` + data changes in `docs/02` | `08-F01…F24` | Full D1 source trace and exact 24-ID data oracle transcribed. This is specification closure, not application closure: Slice B revalidates M3/M4 and M6 still owns actual advances, Saldo, finalization and isolated tenant documents. |
| Page 01b — Heizkosten & CO₂ | `docs/03-nk-heating-engines.md`; output rules also in `docs/08` | Every `01b-Fxx`, including suffix variants | Full source trace and 34-ID data oracle transcribed; this is not yet executable golden-test closure. F02's CSV factor values/reference behaviour, rules data and factor-independent cost refusal are green, but its end-to-end statement remains open: derived-mass warning/provenance and § 7 Abs. 4 risk output are missing. Slice A capability seams, the self-billing capability and exact F18 are green, but capability evidence does not close the full fixtures. Blocks M2 implementation closure and dependent UVI implementation; it does not block D2 transcription. |
| Page 02 — BetrKV catalogue | `docs/09-betrkv-catalogue.md` + `packages/rules-store` | `09-F01…F32` | Merged with a full D2 source trace and exact 32-ID data oracle. Merge is not production closure or legal approval: no production catalogue or gate was implemented. The current 180-row CSV has no Page 02-assigned rows, so `09-K01…K11` and the three unresolved classifications remain production-blocking. Slice C still owns M1 implementation closure and classifications used by M6, M7 and Page 07. |
| Page 03 — AfA | `docs/10-afa.md` | `10-F01…F34` | Complete transcription approved and merged 21.08.2026. The exact 34-ID data oracle covers purchase-cost ordering, three allocation routes, AfA/use rounding, the 15% guard and annual finance paths. Four CSV rows are `geprüft`; 42 remain `verify-before-production`. Weg B placeholders and the F11 month/day choice block production. No implementation exists. |
| Page 04 — Anlage V + DATEV | `docs/11-tax-export.md` | `11-F01…F16` | Missing. Blocks M7 export and Page 07 tax KPIs. |
| Page 05 — Wächter/Fristen | `docs/12-guards-deadlines.md` | `12-F01…F24` | Complete transcription approved and merged 21.08.2026. The exact 24-ID data oracle covers date arithmetic, strict arrears thresholds, cent rounding, UVI cadence, rent limits, VPI and vacancy. All 18 Page-specific register rows remain `verify-before-production`; the 5-year/6-year meter conflict is unresolved. No guard implementation exists. |
| Page 06 — Vertragsklauseln | `docs/13-contract-clauses.md` | `CLAUSES-F01…F19` | Missing. Blocks M8. The source defines routing and risk rules, but not a complete clause-text catalogue. |
| Page 07 — Investment-KPIs | `docs/14-investment-kpis.md` | Rename `KPI-F01…F14` to `14-F01…F14`, with an alias map | Missing. Blocks the M10 investment cockpit. |
| Page 08 — Bank-Matching | `docs/15-bank-matching.md` | `BANKMATCH-F01…F13` | Complete transcription approved and merged 20.08.2026. The later F03 patch resolves the Page's omitted case as E12, so all thirteen oracle entries are executable dictionaries. Production bank matching remains open for M6. |
| UVI + DWD annexes | `docs/16-uvi.md` | Source-named Block A–D2, DWD and Heizspiegel fixture maps | Complete transcription approved and merged 21.08.2026. Annual DWD factors remain separate from monthly degree-day data; the exact monthly dataset and station-to-PLZ mapping stay `verify-before-production`. No implementation exists. |

The new numbers 13–16 are assigned here. Page 01b stays in `docs/03` because that is the active
engine contract; it does not create a second competing heating specification.

### Mandatory inputs for every transcription

- The complete Page, including inputs, units, formula order, rounding, edge cases, worked examples,
  output wording and out-of-scope sections.
- Its matching `Antworten/` corrections and handoff decisions while those source files still exist.
  D1 and D2 must extract all of their settled content into the target docs and golden fixtures before
  D3 retires them; worked examples become fixtures rather than long copied prose.
- Every matching `Rechtsstand-Register` entry, including `Rechtsstand`, source, legal/convention
  status and `verify-before-production` flags.
- `Anlagen/Non-Goals V1`; its section for the Page must remain out of scope.
- `Anlagen/README-for-Emir.md`; its arithmetic audit is evidence, not permission to remove source
  flags or provenance.
- For UVI: `Emir_Spec_UVI.md`, `DWD-Klimafaktoren-Import-Spec.md`, `LETZTER-STAND.md`, Page 01b and
  Page 05 W4.

### Source precedence and known conflicts

- `Rechtsstand-Register.csv` controls values and production flags. `Antworten/` controls later
  method corrections. If they conflict, stop and resolve the register; do not choose silently.
- F02's former Hu/Ho conflict is resolved by the authoritative CSV and confirmed by
  `Antwort-an-Emir_01b-Uebergabe.md` § 4a/4b: Erdgas uses `0.201` Hu, `0.181` Ho and the documented
  `0.903` conversion relation, with CSV status `geprüft` and Rechtsstand `07/2026`.
- Page 03 says self-use reduces deductible AfA, not the AfA basis. This replaces stale wording in
  Page 06/Non-Goals.
- The DWD annex contains both `0.40–1.80` and an old `0.50–1.80` test boundary. Its update note also
  disagrees on April versus May 2026. Resolve both during `docs/16` transcription.
- The UVI annex's `RENTER` Membership role and largest-remainder wording conflict with the current
  identity and allocation models. Reconcile them; do not copy them into code.
- `Non-Goals V1` and `README-for-Emir.md` are dated inputs. They contain useful constraints, but
  later Antworten and register corrections must be recorded in each target doc.

### Transcription gate

Each target doc must contain a coverage table mapping every source section and fixture ID to its
doc section and golden test. It must also record conflicts, superseded decisions, dependencies and
unresolved values. `spec-scribe` must mark that table complete before implementation begins. A
missing, conflicting or unverified value stays explicit; it is never guessed.

Current trace status after merged `docs/09`, `docs/15` and approved `docs/12` transcriptions:

- Page 01 has a complete source-section trace in `docs/08`, relevant normalized-model rules in
  `docs/02`, and a data-only oracle covering exactly `08-F01…F24`. Green coverage and arithmetic
  checks do not claim that the current application implements every branch.
- Page 01b now has a complete 34-ID data oracle and source-section trace, but a data table is not an
  executable golden test. Current exact end-to-end cases include `F03–F06`, `F16`, `F18` and
  `F28b`. F02's CSV factor values/reference behaviour, rules data and missing-cost refusal are
  green components only; full F02 statement closure remains open for derived-mass
  warning/provenance and § 7 Abs. 4 risk output. The green capability contracts do not count as
  full fixture closure. The self-billing capability is implemented and verified, but remains only
  supporting evidence. Slice A assigns every remaining Page 01b case.
- Page 02 now has a complete source-section trace, all 32 allocable and 11 non-allocable catalogue
  identities, and a data-only oracle covering exactly `09-F01…F32`. Its green checks include the
  Page 01 and Antwort 03 reconciliation. This does not claim current rules-store or NK behavior.
- Page 08 has a complete section/register/correspondence trace and an exact executable oracle for
  `BANKMATCH-F01…F13`. The authoritative later patch resolves F03 as E12 and separates
  `isPotentialDuplicate` Review from silent same-ID re-import dedupe. Emir approved the
  transcription on 20.08.2026 and the slice is merged. Green data-only checks do not claim
  production behavior.
- Page 05 has a complete section/register/non-goal/correspondence trace and an exact data-only
  oracle for `12-F01…F24`. All eighteen Page-specific register rows remain
  `verify-before-production`; the 5-year/6-year meter conflict and every other authority gap remain
  explicit. Emir approved the transcription on 21.08.2026. This is not guard implementation.
- UVI/DWD has a complete annex/Page/W4/register/non-goal/correspondence trace and source-named
  data-only oracles for Blocks A–D2, all nine annual DWD PLZ values/import guards and all 18
  Heizspiegel rows. Emir approved it and the slice was merged on 21.08.2026; it is not implemented. Monthly DWD data and
  station-to-PLZ authority remain production-blocking.
- Page 03 has a complete approved and merged transcription. Pages 04, 06 and 07 have no complete
  transcription.
- Page 06's routing and risk rules can be transcribed, but its missing clause-text/version catalogue
  needs a separate legal source before that part can be implemented.

### Three-phase documentation and correspondence-retirement gate

Source ownership stays explicit during all three phases:

- repository code, `CLAUDE.md` and this plan control shipped architecture and current status;
- `berkay-work/` controls legal and calculation rules, subject to the source precedence above;
- `docs/00`–`docs/08` record dependencies on material assigned by the source registry to
  `docs/09`–`docs/16`; they do not duplicate those detailed contracts.

The correspondence-retirement scope is exactly:

- `FEEDBACK-to-Berkay-01b.md`;
- `FRAGEN-an-Berkay-02.md`;
- `FRAGEN-an-Berkay-03.md`;
- `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_01b-Uebergabe.md`;
- `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md`;
- `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_03.md`;
- `berkay-work/Spec-Seiten/Antworten/08_BankMatching_F03_Patch.md`.

Until D3 passes, these files remain source inputs and must not be deleted or edited merely to remove
a conflict. Every section must be mapped to one target doc section, one golden fixture, an explicit
superseded-history note, or the single unresolved-question file. Git preserves the retired
correspondence history after deletion; the approved `docs/` transcription becomes the durable
project knowledge.

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

**Phase D2 — only after D1 approval.** Create `docs/09`–`docs/16` as separate source-backed spec
slices. The source registry above owns each Berkay Page-to-doc and fixture assignment; do not
duplicate that registry here. Every slice includes its complete coverage table and golden fixtures,
then stops for review with no implementation. Preserve this dependency order:

1. `docs/09`;
2. `docs/15`;
3. `docs/12`, then `docs/16`;
4. `docs/10` and `docs/11`, then final `docs/07` reconciliation;
5. `docs/13`;
6. `docs/14`, only after `docs/09`–`docs/11`.

During D2, finish the correspondence-retirement ledger by extracting every remaining settled item
into `docs/09`–`docs/16` and their golden fixtures. Do not delete the correspondence at the D2 exit.
Stop for Emir's review and approval first.

**Phase D3 — only after D2 approval.** Retire the correspondence without losing information:

1. Prove that every section of all seven files is mapped to an approved doc section, golden fixture,
   superseded-history note or unresolved item.
2. Create `FRAGEN-an-Berkay-04.md` only if genuine questions remain. It contains no settled history,
   completed requests or implementation status.
3. Verify the target docs preserve every rule, correction, source reference, supersession,
   verification flag and unresolved risk. Preserve exact arithmetic in fixtures rather than copying
   long worked examples into prose.
4. Update `CLAUDE.md`, `PLAN.md` and `AGENTS.md` so they no longer require or link to the retired
   correspondence and so the approved docs, original Pages, annexes and register define the new
   source model.
5. Verify that no live repository reference depends on any retiring path and that no unresolved item
   is left only in Git history.
6. Delete the seven files together, inspect the complete deletion diff, and stop for Emir's approval.

Implementation resumes only after D3 has passed and Emir has approved the retirement diff. At that
point the approved `docs/00`–`docs/16`, their golden fixtures, the original Pages and annexes, and
the Rechtsstand register form the complete implementation baseline. Later slices and milestones use
that baseline; they do not restart transcription or silently reinterpret a source.

The documentation program is complete only when:

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
| D2 | **In progress — `docs/10` approved and merged; `docs/11` next** | Create source-backed `docs/09`–`docs/16` | `docs/09`, approved `docs/15`, `docs/12`, `docs/16` and `docs/10` are merged. The exact 34-ID AfA oracle is documentation-only; no AfA implementation exists. Continue with `docs/11`. |
| D3 | After D2 approval | Complete extraction and retire Berkay correspondence | Close the seven-file coverage ledger, create only one current `FRAGEN-an-Berkay-04.md` if needed, update governance references, verify no dependent paths, delete the seven files together and stop for Emir's approval. |
| A | Paused for D1–D3 | Reconcile M2 with Page 01b | Integrate the approved Page 01b contract into executable end-to-end fixtures and close M2. Capability seams are supporting evidence, not Slice A closure. |
| B | After A | Reconcile M3–M4 with Page 01 | Revalidate the approved Page 01 contract against persisted calculation and extraction, close M3/M4 gaps and leave ledger/finalization work to M6. |
| C | After B | Reconcile M1 with Page 02 | Revalidate NK eligibility, allocation, classification and rounding against merged `docs/09` and close M1. |
| M5 | After A–C | Roles, URL context and switcher | Finish the prepared secure bootstrap slice, role enforcement, owner contexts, switcher, nested-building authorization and the `renter.person_id` negative guard. |
| M6 | After M5 | Bank, ledger and finalized statements | Implement approved `docs/08` and `docs/15`: actual advances, BGH minimum #4, immutable snapshots, bank matching, landlord overview, isolated tenant documents, and remaining statement copy/citation findings. |
| G | After M6 | Shared guard foundation | Implement the approved `docs/12` rules needed by § 556, Eichfrist, UVI cadence and later M9 work through one reusable guard mechanism. |
| U | After G | UVI comparison, calculation and document | Implement approved `docs/16`, including the heating-only comparison, monthly readings, labelled fallbacks and tenant document. Scheduled delivery waits for M9; portal publication waits for M10. |
| M7 | After U | Tax export and AfA | Implement approved `docs/09`–`docs/11`. Build computation paths and archives; flagged register values continue to block real output. |
| M8 | After M7 | Document and letter engine | Implement approved `docs/13` with versioned clauses and risk gates. |
| M9 | After M8 | Reminders, email and checklists | Complete the guard-driven reminder and delivery system from approved `docs/12`, including UVI scheduling. |
| M10 | After M9 | Portals, investment, billing and native apps | Implement renter activation and portal work, the approved `docs/14` investment cockpit, billing and mobile apps. |

### Slice A — progress and closure

Progress preserved on the current branch:

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
- F02's authoritative CSV factor values/reference behaviour, rules data and missing-cost refusal
  are green components. Its end-to-end statement warning/provenance and § 7 Abs. 4 risk output
  remain open.

These capability seams are not end-to-end Page 01b closure. Slice A closes only when:

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
4. H8 annual comparison starts only after the DWD rule/import ownership and the conflicting
   range/date inputs are reconciled. It covers `F31` without pulling UVI D2 into Slice A.
5. Full and demo gates pass, the before/after PDF fingerprint is recorded, and statement review has
   no unresolved Slice A findings.

The D1–D3 documentation and correspondence-retirement gates precede the A–C implementation
reconciliation gate. Do not resume M5 or start later feature work until D1–D3 are approved, A–C are
spec-closed and the full and demo gates pass. The three earlier Page 01b fixes remain complete only
for their named scope; they do not count as full Page 01b coverage. UVI implementation is no longer
blocked by the co2online licence, but it remains blocked until `docs/16`, the shared guard
foundation and Slice A are approved and green. A real § 6a output must still be checked later.

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

### M1 — Operating-cost engine 🟡 built and green; Page 02 spec merged, production open

- Pure `packages/nk-engine`.
- Day-weighted allocation, vacancy handling and largest-remainder reconciliation.
- DIRECT, MEA and other allocation keys.
- Per-period `AllocationKeyAssignment`; changing a key does not delete entered data.
- Canonical €1,200 golden fixture passes exactly.

**Spec-closed when:** Slice C proves the existing engine against approved `docs/09`, every `09-Fxx`
fixture passes and all confirmed differences are resolved.

### M2 — Heating and CO₂ engine 🟡 Page 01b transcribed; implementation reconciliation pending

- Pure `packages/heating-engine`.
- HeizkostenV §§ 7/8, § 9 and § 9a.
- Degree-day renter-change allocation.
- CO₂ 10-step landlord/renter split.
- Versioned ratios, tables and `Rechtsstand`.

**Spec-closed when:** Slice A proves complete Page 01b coverage, every `01b-Fxx` fixture passes, the
three earlier bounded fixes remain correct and the statement prints the verified split with
`Rechtsstand`.

### M3 — Web vertical slice and PDF 🟡 built and green; Page 01 reconciliation pending

Built:

- URL-scoped landlord portal under `/a/{accountId}`;
- membership check plus RLS for account access;
- `/me`-derived navigation and demo loading;
- buildings, units, tenancies and occupancy timeline;
- cost entries, allocation keys, meters and readings;
- statement creation and NK/heating PDF download;
- autosave so leaving a flow does not lose entered data;
- statement inputs from persisted rows, not fixture constants.

**Spec-closed when:** Slice B proves the persisted path against approved `docs/08`, the original demo
remains green and all `08-Fxx` statement fixtures pass.

### M4 — Document extraction demo 🟡 built and green; Page 01 reconciliation pending

- Shared upload → prefill → confirm flow.
- Stub Vision adapter with canned invoices.
- Per-field confidence and API-owned review threshold.
- Extraction writes nothing until the ordinary cost form is confirmed.

Not included:

- automatic allocation-key choice, which needs the Slice C BetrKV catalogue;
- Beleg persistence, file hash and object storage.

**Spec-closed when:** its confirmed extraction path still feeds the Page 01 statement model after
Slice B, without bypassing review or tenant-document isolation.

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

## 4. M5 remainder — paused until D1–D3 and Slices A–C close

### Prepared on the unmerged `slice/m5-bootstrap-contexts`

- JWT auth carries only the verified Person subject.
- Expiry, issuer, exact audience and authenticated role are validated.
- Account context is never trusted from the token.
- Migration `0006` adds the single bounded `app_bootstrap_contexts(text)` read.
- `GET /me` returns all live account contexts from the database.
- The token-scoped account session and `/demo/summary` are retired.
- The demo summary now uses `/a/{accountId}/summary`.
- The branch's `git show slice/m5-bootstrap-contexts:scripts/check_pre_context_reads.py` checker and
  40 mutation tests enforce the boundary; the checker is not present on `main` yet.
- Full gate, demo path and boundary audit are green.

This work added no new dashboard, portal or account switcher.

### Still open

- Complete the existing owner portal with role-aware account context.
- Keep owner context in `/a/{accountId}/…`.
- Show a context switcher only when a Person has more than one context.
- Enforce OWNER, EMPLOYEE and TAX_ADVISOR behaviour in app logic.
- Restrict EMPLOYEE access to assigned buildings. No assignments means no visibility.
- Make TAX_ADVISOR read-only.
- Validate every nested `{buildingId}` through `PathAccountSession` before work begins.
- Return a deliberate 403/404 for a foreign or unauthorized building.
- Add an OpenAPI guard proving no route writes `renter.person_id`. Only M10 activation may write it.

**Done when:** roles behave correctly; every nested building route verifies its URL context;
multiple account contexts switch by URL and are re-authorized per request; the pre-context checker
stays green; no current API route writes `renter.person_id`. Renter activation, renter URL context
and renter portal authorization are M10 work.

---

## 5. Later milestones

### M6 — Bank, ledger and finalized statements

**Approved-spec prerequisite:** D1's `docs/08` and D2's `docs/15`. If bank matching is deferred,
`docs/15` does not block the remaining ledger and statement work.

- Add Redis workers and webhooks.
- Keep finAPI stubbed behind the bank adapter.
- Match transactions using IBAN, amount and payment purpose.
- Store transactions and versioned IBAN-to-renter mappings.
- Add an append-only Payment Ledger with mandatory payment date.
- Replace `Tenancy.advance_payment_cents` with temporal `AdvancePaymentPeriod` rows and backfill
  existing tenancies.
- Add BGH formal minimum #4: deduct actual paid advances and print Saldo/Nachzahlung/Guthaben.
- Keep previews live and unarchived.
- Finalization creates one immutable, reproducible snapshot with inputs, results, engine/rule
  versions, `Rechtsstand`, timestamps, hashes and archived documents.
- Corrections create `vN+1`; old versions and referenced inputs remain intact.
- Render one internal landlord overview, one separate document per eligible tenancy and the
  landlord-only vacancy schedule required by Page 01.
- A tenancy with zero period-clipped usage days gets no tenant document or portal entry. The landlord
  overview receives the required footnote.
- Never generate one all-renters PDF and crop or hide sections.
- Add background jobs for bank sync, 180-day reconsent cleanup and deadline watchers.

**Done when:** seeded bank transactions match; actual paid advances produce the Saldo; temporal
advances work; preview creates no archive; finalization is immutable and reproducible; landlord and
tenant documents are separated; zero-day tenancies are excluded and footnoted.

### Shared guard foundation and UVI implementation slice

**Approved-spec prerequisite:** `docs/12`, `docs/16` and spec-closed Slice A.

- Implement the shared § 556, Eichfrist and UVI cadence guards needed before M9.
- Implement the specified heating-only comparison with labelled fallbacks and no extrapolation.
- Add monthly readings, the UVI calculation and the separate tenant document.
- Keep scheduled delivery in M9 and portal publication in M10.

**Done when:** every `docs/16` calculation fixture passes, the DWD conflicts are resolved, the UVI
document is tenant-isolated, and the shared due-date guard is executable. If the DWD inputs remain
unresolved, this slice stays blocked.

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
non-goals and all `CLAUSES-Fxx` fixtures.

- Versioned clause blocks and stored clause composition.
- A legal change creates a new clause version and flags affected contracts.
- Mieterhöhung, Kündigung, Mahnung and SEPA mandate.
- Destatis VPI adapter and stub Mietspiegel provider.

**Done when:** a contract is generated from versioned clauses and a clause update identifies every
affected contract.

### M9 — Reminders, email and checklists

**Approved-spec prerequisite:** `docs/12`. The bounded shared guard foundation lands before the UVI
slice; M9 completes reminders, email and checklists without redefining those rules.

- Shared trigger/state-machine engine for § 556, arrears, move-in/out and UVI.
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
| `docs/00-product-overview.md` | Reconcile the product promise with shipped status, the Page 01 period hard stop and the still-incomplete final tenant document. |
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
| `docs/13-contract-clauses.md` | Versioned clause decisions and risk gates from Page 06. |
| `docs/14-investment-kpis.md` | KPI definitions, financing assumptions and calculation order from Page 07. |
| `docs/15-bank-matching.md` | Deterministic signals, confidence outcomes and review rules from Page 08. |
| `docs/16-uvi.md` | Complete UVI calculation, DWD import, cadence, delivery and fallback contract from the annexes and linked Pages. |

The new-doc table is the output inventory, not a second source assignment: the Berkay source
registry above remains authoritative. Create these only in D2 and in its dependency order.

---

## 7. Product floor

M0 is complete. M1–M4 are the current green, demoable floor: a persisted-data operating-cost and
heating calculation view with CO₂ allocation and tenant isolation. They are not yet fully
spec-closed. D1 is complete; approved 17.08.2026; final reconciliation closed 18.08.2026.
`docs/09` and the approved `docs/15`, `docs/12`, `docs/16` and `docs/10` transcriptions are merged.
Implementation remains paused; `docs/11`, later D2 and D3 gates still require Emir's review.
After all three
documentation and correspondence-retirement gates are approved, Slices
A–C retain their order and reconcile implementation
with Pages 01b, 01 and 02 before feature work continues. The finalized tenant document still waits
for M6.

Protect that floor. Correctness comes before breadth. If work stops, stop at a green state.
