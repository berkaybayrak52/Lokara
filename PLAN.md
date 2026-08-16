# PLAN.md — Lokara roadmap

This file answers two questions:

1. What is built?
2. What comes next?

Build in the execution order below. Each slice ends green. Engines and golden fixtures come before
UI. Dates are communication events, not planning inputs.

## Current state

- M0 is complete. M1–M4 are built and green under their original scope, but are not yet fully
  verified against all Berkay specifications.
- The v4 migration is complete. The old TypeScript backend is gone. Mobile moved to M10.
- Composite foreign-key isolation and M5a identity/RLS are complete.
- Execution rows 1–3 are complete for their bounded fixes. The Page 01b source transcription is
  complete; its executable-golden-test gate, confirmed implementation gaps and final verification
  still block M2 spec closure.
- Berkay's Pages 01–08 and 01b exist. They are primary implementation specs, not background notes.
- Page 01 is partly represented in current `docs/`. Page 01b's transcription is complete but its
  confirmed implementation gaps remain. Pages 02–08 and the full UVI annex still need transcription
  before their related implementation work.
- The M1–M4 reconciliation gate is current and must finish before new feature work continues.
- Row 4 is paused. Its secure bootstrap foundation is complete on `slice/m5-bootstrap-contexts`,
  but the slice is not merged yet.
- Row 4 has not added a new dashboard, portal or account switcher.

---

## Berkay source registry

Every Page is a calculation or deterministic legal/product-rule source. A milestone may not use a
Page directly from `berkay-work/`. First transcribe it into the target `docs/` file and create its
golden fixtures. Existing docs are not assumed correct merely because they already exist.

| Source | Target | Fixtures | Current coverage and dependency |
| --- | --- | --- | --- |
| Page 01 — Die Abrechnung | `docs/08-statement-document.md` + data changes in `docs/02` | `08-F01…F24` | Partial. Selected blocks exist, but the source requires three outputs and answers questions still open in `docs/08`. Blocks M3/M4 spec closure and final M6 statements. |
| Page 01b — Heizkosten & CO₂ | `docs/03-nk-heating-engines.md`; output rules also in `docs/08` | Every `01b-Fxx`, including suffix variants | Full source trace and 34-ID data oracle transcribed; this is not yet executable golden-test closure. A1–A3, F02's factor-independent refusal and exact F18 are green. A2/A3 capability evidence does not close the full fixtures. F02's factor-dependent value remains blocked by the Hu/Ho conflict. A4 is RED; A5–A7 remain pending. Blocks M2 implementation closure, D2 and UVI. |
| Page 02 — BetrKV catalogue | `docs/09-betrkv-catalogue.md` + `packages/rules-store` | `09-F01…F32` | Missing. Blocks M1 spec closure, Slice C and classifications used by M6, M7 and Page 07. |
| Page 03 — AfA | `docs/10-afa.md` | `10-F01…F34` | Missing. Blocks M7 AfA and Page 07 tax KPIs. |
| Page 04 — Anlage V + DATEV | `docs/11-tax-export.md` | `11-F01…F16` | Missing. Blocks M7 export and Page 07 tax KPIs. |
| Page 05 — Wächter/Fristen | `docs/12-guards-deadlines.md` | `12-F01…F24` | Missing. Blocks Row 7, M9 and the UVI due-date guard. |
| Page 06 — Vertragsklauseln | `docs/13-contract-clauses.md` | `CLAUSES-F01…F19` | Missing. Blocks M8. The source defines routing and risk rules, but not a complete clause-text catalogue. |
| Page 07 — Investment-KPIs | `docs/14-investment-kpis.md` | Rename `KPI-F01…F14` to `14-F01…F14`, with an alias map | Missing. Blocks the M10 investment cockpit. |
| Page 08 — Bank-Matching | `docs/15-bank-matching.md` | `BANKMATCH-F01…F13` | Missing. Blocks the bank-matching part of M6. |
| UVI + DWD annexes | `docs/16-uvi.md` | Every annex fixture, including the DWD import set | Missing. Blocks Rows 9–10. |

The new numbers 13–16 are assigned here. Page 01b stays in `docs/03` because that is the active
engine contract; it does not create a second competing heating specification.

### Mandatory inputs for every transcription

- The complete Page, including inputs, units, formula order, rounding, edge cases, worked examples,
  output wording and out-of-scope sections.
- Its matching `Antworten/` corrections and handoff decisions.
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
- Hu/Ho is currently blocked by such a conflict: Antwort 03 says `0.2016 / 0.1820`, while the
  register says `0.201 / 0.181`.
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

Current trace audit, 16.08.2026:

- Page 01 has no current doc/test trace for `08-F02…F05`, `F07…F16`, `F18…F20` and `F23…F24`.
- Page 01b now has a complete 34-ID data oracle and source-section trace, but a data table is not an
  executable golden test. Current exact green cases include F02's factor-independent refusal,
  `F03–F06`, `F16`, `F18` and `F28b`. A2/A3 capability contracts are green but do not count as full
  fixture closure. A4 is RED. The A2–A7 rows assign every remaining case; `F02` stays value-blocked
  for its factor-dependent result.
- Pages 02–08 have no complete transcription. Existing references to a few Page 02 fixtures from
  owner-residual work do not count as Page 02 coverage.
- Page 06's routing and risk rules can be transcribed, but its missing clause-text/version catalogue
  needs a separate legal source before that part can be implemented.

---

## 1. Execution order

The order closes legal billing exposure first. Missing UVI or CO₂ disclosure can each reduce the
heating claim by 3%. Missing consumption-based billing can reduce it by 15%.

| # | Status | Work | Required result |
| --- | --- | --- | --- |
| 1 | ✅ Done 13.08.2026 | Wire R1/R5/K9 and Ho/Hu into `heating-engine` | Heating uses the required half-up allocation path. |
| 2 | ✅ Done 15.08.2026 | Eigentümer residual | One residual line per property and cost type: total minus renter shares. It always exists and is never a party or occupancy share. NK stays on largest remainder until Slice C. |
| 3 | ✅ Done 15.08.2026 | CO₂ rounding under § 5 Abs. 1 S. 3 | Annualise, round half-up to one decimal, then classify. Print the same one-decimal value in both PDF locations. |
| A1 | ✅ Green | MDL gross rescaling | `01b-F28b` is executable and green: exact gross quotient, accepted one-cent source residual and owner reconciliation. |
| A2 | ✅ Green `716f741` | Device and segmented readings | H5 typed device/span aggregation and H6 hand-off are green for `F01/F27`, `F15`, `F16`, `F17` and `F22`. Exact WE-03-only `F18` reproduces Berkay's authoritative cents. Capability evidence is not full F01/F15/F17/F22/F27 E2E closure. |
| A3 | ✅ Green `89db9e0` | Plant/CO₂ applicability and source state | Green capability contracts cover `F07–F10` and `F23`: building type, fuel, connected state, proof-gated protection/exclusion, module/disclosure switches and non-blocking R8-value warnings. They are not full fixture E2E closure. |
| A4 | RED spec ready after A3 | Self-billing inputs and plant aggregation | Implement normalized pure capability contracts for `F11–F14`, `F19`, `F20`, `F24`: H1 positions/disclosure carry, K8 overlap and coverage warning, oil stock consumption, H3 priority/fallback/single-block paths and the 50 % owner preview. These tests are not E2E closure. F02's cost refusal is green; its factor-dependent mass remains blocked. |
| A5 | Pending after A4 | Remaining readiness and warning channels | Close `F21`, `F25`, `F26/F26b/F26c`: hard denominator stop, separate unsummed risk amounts, and the two WW-gap thresholds. F23's warning primitive belongs to A3 but still needs E2E projection before fixture closure. |
| A6 | Pending after A5 | MDL net and readiness branches | Close `F28a`, `F29`, `F30`. F29 belongs to the net M2/M3 branch; the gross-rescaling seam is not a closure scaffold. |
| A7 | Pending after A6 | Annual § 6a comparison | Close `F31`: heat adjusted with each year's DWD factor, WW raw, labelled missing-factor fallback, no empty graph, and complete disclosure/risk output. |
| B | After A | Reinforce M3–M4 from Page 01 | Fully transcribe Page 01 into `docs/08` and required `docs/02` changes. Map every `08-Fxx` fixture. Revalidate the current persisted calculation and extraction scope; implement confirmed gaps that belong to M3/M4 and leave M6-only ledger/finalization work explicitly assigned to M6. |
| C | After B | Reinforce M1 from Page 02 | Transcribe Page 02 into `docs/09`, add all `09-Fxx` fixtures and revalidate NK eligibility, allocation and rounding. This replaces the former separate Row 5. |
| 4 | Paused until A–C | M5 roles, URL context and switcher | Secure bootstrap is complete on the slice. Still needed: role enforcement, owner account contexts, switcher, nested-building authorization and the `renter.person_id` negative guard. Renter activation and portal context remain M10. |
| 6 | Open | M6 bank, ledger and finalized statements | Complete Page 01 → `docs/08` first. Transcribe Page 08 → `docs/15` before bank matching. Add actual paid advances, BGH minimum #4, immutable snapshots, one landlord overview and isolated tenant documents. |
| 7 | Open | Page 05 → `docs/12` Wächter set | Implement § 556 deadline, Eichfrist and UVI cadence through one reusable guard mechanism. |
| 8 | Open | Statement copy and citations | Resolve the remaining reviewer findings on ligatures, spacing, copy and footer citations. |
| 9 | Ready after transcription | D2 Heizspiegel comparison value | Reconcile Page 01b and transcribe the UVI/DWD annexes → `docs/16`. Then implement the specified heating-only comparison, guards and labelled fallbacks without extrapolation. |
| 10 | Open | UVI calculation and document | Implement the calculation and tenant document from `docs/16`. Needs monthly readings, Page 05 W4 and Row 9 comparison values. Scheduled delivery waits for M9; portal publication waits for M10 activation. |
| 11 | Ready after transcription; values blocked | M7 tax export and AfA | Transcribe Page 03 → `docs/10` and Page 04 → `docs/11`. Build only the computation paths; flagged register values still block real output. |
| 12 | Open | M8, M10 modules and mobile | Transcribe Page 06 → `docs/13` before the clause engine and Page 07 → `docs/14` before the investment cockpit. Then build documents, tickets, activation, investment, billing and native apps. |

Slices A–C are a mandatory reconciliation gate. Do not continue Row 4 or start later feature work
until all three are spec-closed and the full and demo gates pass. Rows 1–3 remain complete only for
their named fixes; they do not count as full Page 01b coverage. Row 9 is no longer blocked by the
co2online licence, but it is blocked by the `docs/16` transcription gate. A real § 6a output must
still be checked later.

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
2. **Keep the demo path green.** Every milestone re-verifies database → migration → seed → statement
   → PDF. Fix or revert any break before continuing.
3. **Tag green milestone states.** Use `demo-green-<n>` only after the required gates pass.
4. **Finish one milestone or bounded slice at a time.** Do not merge half-built subsystems.
5. **Keep external services stubbed behind adapters** until their integration slice. No real keys or
   vendor SDKs in engines or domain code.
6. **Docs and code must agree.** A documented rule that code does not follow is a defect.

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

### M1 — Operating-cost engine 🟡 built and green; Page 02 reconciliation pending

- Pure `packages/nk-engine`.
- Day-weighted allocation, vacancy handling and largest-remainder reconciliation.
- DIRECT, MEA and other allocation keys.
- Per-period `AllocationKeyAssignment`; changing a key does not delete entered data.
- Canonical €1,200 golden fixture passes exactly.

**Spec-closed when:** the original gates still pass after complete Page 02 transcription, every
`09-Fxx` fixture exists and all confirmed differences are resolved.

### M2 — Heating and CO₂ engine 🟡 Page 01b transcribed; implementation reconciliation pending

- Pure `packages/heating-engine`.
- HeizkostenV §§ 7/8, § 9 and § 9a.
- Degree-day renter-change allocation.
- CO₂ 10-step landlord/renter split.
- Versioned ratios, tables and `Rechtsstand`.

**Spec-closed when:** complete Page 01b coverage exists, every `01b-Fxx` fixture is traced, Rows 1–3
remain correct and the statement prints the verified split with `Rechtsstand`.

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

**Spec-closed when:** the original demo remains green after complete Page 01 transcription and all
`08-Fxx` statement fixtures pass.

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

## 4. M5 remainder — paused until Slices A–C close

### Prepared on the unmerged `slice/m5-bootstrap-contexts`

- JWT auth carries only the verified Person subject.
- Expiry, issuer, exact audience and authenticated role are validated.
- Account context is never trusted from the token.
- Migration `0006` adds the single bounded `app_bootstrap_contexts(text)` read.
- `GET /me` returns all live account contexts from the database.
- The token-scoped account session and `/demo/summary` are retired.
- The demo summary now uses `/a/{accountId}/summary`.
- `scripts/check_pre_context_reads.py` and 40 mutation tests enforce the boundary.
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

**Spec gate:** finish Page 01 in `docs/08`. Finish Page 08 in `docs/15` before implementing bank
matching. If bank matching is deferred, Page 08 does not block the remaining ledger and statement
work.

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

### M7 — Tax export and AfA

**Spec gate:** transcribe Page 03 into `docs/10` and Page 04 into `docs/11`, including every fixture
and every `verify-before-production` marker. Page 02 must already be transcribed where its cost
classification feeds the export.

- Pure `packages/export-engine` for Anlage V and DATEV EXTF.
- DATEV output is byte-exact Windows-1252 with semicolons and CRLF.
- Readiness check and immutable export archive with hash and timestamp.
- Pure `packages/afa-engine`, AfA wizard, 15% guard and loan-interest prefill.
- Preserve every `verify-before-production` flag from the M7 warning above.

**Done when:** DATEV and Anlage-V golden tests pass byte-exactly and the export is archived
immutably. Production use remains blocked until flagged values are verified.

### M8 — Document and letter engine

**Spec gate:** transcribe Page 06 into `docs/13`, including its legal/convention labels, risk gates,
non-goals and all `CLAUSES-Fxx` fixtures.

- Versioned clause blocks and stored clause composition.
- A legal change creates a new clause version and flags affected contracts.
- Mieterhöhung, Kündigung, Mahnung and SEPA mandate.
- Destatis VPI adapter and stub Mietspiegel provider.

**Done when:** a contract is generated from versioned clauses and a clause update identifies every
affected contract.

### M9 — Reminders, email and checklists

**Spec gate:** transcribe Page 05 into `docs/12` before building any deadline or reminder rule.

- Shared trigger/state-machine engine for § 556, arrears, move-in/out and UVI.
- Stubbed email provider using Lokara's domain and the landlord as the From-name, with an immutable
  delivery-status ledger.
- Suppress bounced and complained-about addresses.
- Count the § 556 access deadline backwards. UVI and annual statements keep separate delivery rules.
- Three-colour delivery indicator.
- Data-driven checklist library that creates reminders.

**Done when:** the § 556 deadline escalates correctly and delivery status is visible.

### M10 — Portals, modules and native apps

**Spec gate:** transcribe Page 07 into `docs/14` before the investment cockpit. The calculation
depends on the completed Page 02, Page 03 and Page 04 contracts. Renter activation remains governed
by `docs/02` and the M5 no-write guard.

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

These existing docs need focused updates. Update them only through the relevant spec slice, so the
new source coverage and golden fixtures land together.

| Existing doc | Why it needs work |
| --- | --- |
| `docs/00-product-overview.md` | It advertises statements longer than 12 months, while Page 01 hard-blocks them. Its compliance claim must also distinguish the current demo from the still-incomplete final tenant document. |
| `docs/01-tech-stack-explanations.md` | It still opens with an old TODO pass and unfinished abbreviation work. Clean it after the active architecture docs settle. |
| `docs/02-data-model.md` | Page 01 is explicitly only partly transcribed. Pages 02–04, Page 08 and UVI add catalogue, ledger, export, matching and delivery data. Preserve Page 03's rule that self-use reduces deductible AfA, not its basis. Remove stale alternatives as models settle. |
| `docs/03-nk-heating-engines.md` | Page 01b, Antworten 02/03, all 47 matching register rows and the DWD/UVI dependencies are reconciled. Preserve its blocked Hu/Ho value and superseded-rule record while the RED fixtures and confirmed implementation gaps are closed. |
| `docs/04-web-app-structure.md` | It calls the completed Page 02 source a pending spec and includes future mobile/engine packages and optional UI work as if present. Separate shipped structure from future architecture and preserve M10 renter ownership. |
| `docs/06-demo-scenarios.md` | The current M5 bootstrap/onboarding limits are aligned. Extend it later with the complete Page 01 landlord/tenant output flow and the related milestone personas. |
| `docs/07-compliance.md` | Add the provenance, production-blocking flags, delivery and retention rules introduced by Pages 01, 04, 05, 06 and UVI. |
| `docs/08-statement-document.md` | It contains selected Page 01 patches, not a proven full transcription. It still has open questions answered by Pages 01/02 and stale block-(b) `0,00` wording. Rebuild its structure around all three outputs and every `08-Fxx` fixture before M6. |

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

`docs/01-tech-stack-and-decisions.md` and `docs/05` need ordinary drift review, but the current audit
found no missing Berkay calculation contract that requires a new section there.

---

## 7. Product floor

M0 is complete. M1–M4 are the current green, demoable floor: a persisted-data operating-cost and
heating calculation view with CO₂ allocation and tenant isolation. They are not yet fully
spec-closed. Slices A–C must reconcile them with Pages 01, 01b and 02 before feature work continues.
The finalized tenant document still waits for M6.

Protect that floor. Correctness comes before breadth. If work stops, stop at a green state.
