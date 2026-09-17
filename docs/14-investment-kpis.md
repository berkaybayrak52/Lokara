# Investment KPIs — planning calculations and deterministic bank view

**Status:** D2 transcription complete; M10-I0–I4 technically implemented and locally verified; I4 locally merged

**Rechtsstand:** 07/2026

**Authoritative Page:**
`berkay-work/Spec-Seiten/07 · Investment-KPIs 3a95fd4207318157a94ec8b5474bedba.md`

**Fixtures:** exactly `14-F01`–`14-F14` in
`packages/rules-store/tests/berkay_14_golden.py`

**Implementation status:** the pure engine, section-4.7 persistence contract and section-4.8 API
contract are technically complete through migration `0046`. The section-4.9 cockpit, server-owned
default layout and frozen Bank-PDF are implemented and verified locally on
`slice/m10-i4-investment-cockpit`, committed as `97f6448` and locally merged into `main`. M10-F is
technically complete and review-clean locally on 17.09.2026; its closure changes remain uncommitted.
No production approval is implied; all Page-07 production blockers remain. Pricing and bank
integration remain outside this contract.

This document defines a planning calculation for a **Prüfobjekt**: a property being
considered for purchase. It produces exactly seven KPIs and a deterministic Bank-PDF view. The
results are conventions and scenarios, not a valuation, credit decision, bank application,
investment recommendation, tax export or promise of a tax result.

## 1. Sources, precedence, identifiers and audit

The transcription uses the complete original Page 07, all 18 Page-07 rows in the authoritative 180-row
`Rechtsstand-Register.csv`, the eight Page-07 entries in `Non-Goals V1`, the
`README-for-Emir.md` arithmetic audit and the historical disposition in `docs/03` Appendix D. The CSV
controls structured values and flags.

The source identifiers are normalized without changing their meaning:

| Source | Durable identifier |
| --- | --- |
| `KPI-K01…KPI-K19` | `14-K01…14-K19` |
| `KPI-E01…KPI-E15` | `14-E01…14-E15` |
| `KPI-F01…KPI-F14` | `14-F01…14-F14` |
| `R1…R10` | unchanged |

The audit recomputed all 14 Page-07 fixtures with `Decimal`, integer cents and half-up rounding and
found the printed arithmetic exact. This approves no convention, heuristic or flagged value and
does not prove production behavior.

The source assigns the feature to M10 and labels it an optional `4,90 EUR` add-on. That is source
metadata only: this transcription approves neither pricing nor a purchasable product.

Page 07 names `Lokara_Investitionsmodul_Demo.html` and `AfA-Wizard_Konzept_Entwurf.md` as inputs.
Neither file exists in the repository. Their contents are unknown and are not reconstructed here.

## 2. Authority and compatibility boundaries

- `docs/10-afa.md` owns real AfA and deductible-interest data. The 75% building share, 2% AfA rate
  and 42% marginal-tax rate here are acquisition-phase assumptions only.
- Page 03 R13 hands over annual full AfA and deductible interest. Page 07 R3 independently derives
  first-year annuity interest for a planning scenario. The source does not resolve which interest
  amount a future production tax scenario must use. Fixtures reproduce Page-07 arithmetic but do
  not choose a tax rule.
- A negative `steuerCent` is flat-rate scenario arithmetic. It is not a promised refund, a tax
  entitlement or a value for Anlage V/DATEV.
- `docs/09-betrkv-catalogue.md` owns non-allocable category identities. This Page consumes only
  user-entered planning amounts for administration, maintenance, reserve and vacancy risk.
- `docs/11-tax-export.md` owns cash-basis tax behavior, export readiness and immutable archive
  architecture. The Bank-PDF is a planning view only and contains no renter names.
- Product output uses the approved `rechtskonform, keine Rechts- oder Steuerberatung` disclaimer.
  No StBerG product wording is added. The artifact-specific disclosure is:
  “Vom Vermieter erstellte Zusammenfassung auf Basis eigener Angaben und Annahmen. Keine
  Immobilienbewertung, kein Beleihungswert, kein Gutachten, keine Bonitätsauskunft.”
- The source claim that no capital-markets permission is required remains uncertain until legal
  confirmation. Product wording stays with calculation/metric, never recommendation or guarantee.

## 3. Complete register surface

The exact CSV metadata is mirrored field for field in `PAGE_07_REGISTER_ROWS`. There are exactly
18 rows: two `geprüft` and sixteen `verify-before-production`; thirteen `Konvention`, three
`Heuristik` and two `Gesetz`. `geprüft` means the cited statutory text was checked, not that the
product or result is lawyer-approved.

The two checked rows are the V+V surplus-calculation form and AfA/interest as Werbungskosten. All
KPI definitions, defaults, thresholds, the 30/360 planning recurrence, Bank-PDF choices and
financing-source labels remain blocked before production.

## 4. Logical contracts and M10-I2 persistence

All money is integer cents. Rates and ratios are integer basis points. KPI ratios are integer
hundredths. `Decimal` with `ROUND_HALF_UP` is used exactly at specified division or multiplication
boundaries; no float crosses the contract.

### 4.1 Prüfobjekt input snapshot

The implemented immutable snapshot groups object/purchase data, monthly cold rent and vacancy assumption,
four user-entered operating amounts, financing assumptions, tax/AfA provenance, optional Bank-PDF
header data and rule/layout versions. It records `finanzierungQuelle` as `annahme`, `indikativ` or
`angebot`. Missing data stays missing; it is never replaced by zero.

### 4.2 Financing and AfA provenance

Each financing value records whether it is a pre-offer assumption, indication or offer. Each AfA
value records whether it came from Page-03 R13, the implemented cockpit wizard or the acquisition-phase
default. A linked Page-03 record wins. The snapshot must retain both source and version.

### 4.3 Partial KPI result

Each of the seven KPI slots returns either a fixed-point value or `—`, required-input gaps,
before/after-tax label, assumption badges and source versions. Missing inputs produce “Daten
unvollständig”; no fabricated zero. No overall score or purchase decision is returned.

### 4.4 Twelve-month annuity schedule

The implemented schedule contains exactly twelve ordered rows with opening balance, rounded monthly
interest, repayment and closing balance, plus annual interest, repayment, debt service and closing
balance. Every row reconciles and the annual sums reconcile. Non-positive repayment hard-blocks.

### 4.5 Sensitivity axes

The interest axis reruns R3–R7 at five configured steps, default `−100/−50/0/+50/+100` basis points.
The repayment axis varies initial repayment at constant interest and must show liquidity and debt
reduction together. Interest is a stress axis; repayment is a financing-structure trade-off.

### 4.6 Deterministic Bank-PDF view

The implemented view is `f(frozen KPI snapshot, versioned layout) → bytes`. It performs no
recalculation. Blocks are ordered: header/disclosure, investment, financing/LTV, rent and planning
costs, seven KPIs, sensitivity, twelve-month schedule, assumptions/method including the `14-K01`
through `14-K13` definitions, and disclosure. Missing KPIs remain `—`. LTV is labelled “Auslauf zum
Kaufpreis, nicht zum Beleihungswert”. The view includes no renter names and is not a tax export,
archive, valuation, credit decision or bank application.

### 4.7 M10-I2 persistence contract — migration `0045`

This subsection supersedes the former “no schema approval” marker for M10-I2 only. It is a technical
persistence decision accepted on 12.09.2026. It does not approve any production-blocked Page-07
convention or legal claim.

M10-I2 adds exactly three account-scoped, append-only tables. A Prüfobjekt is identified by the
stable `case_key` on its input-snapshot correction stream. It has no `building_id`, no relationship
to `building`, and no path into statements, tax exports or the owner demo.

#### `investment_layout_version`

| Column | Type and nullability | Meaning |
| --- | --- | --- |
| `id` | string PK | immutable row identity |
| `account_id` | string, not null | account boundary |
| `layout_key` | nonblank string, not null | stable logical layout stream |
| `version` | positive integer, not null | stream version, starting at `1` |
| `layout_snapshot` | nonempty JSONB object, not null | complete renderer-owned layout definition |
| `supersedes_layout_version_id` | string, nullable | prior version in the same account and `layout_key` |
| `created_at` | timezone timestamp, not null | append time |

`(id, account_id, layout_key)` and `(account_id, layout_key, version)` are unique. The predecessor
is a composite self-FK on `(supersedes_layout_version_id, account_id, layout_key)`. Version `1` has
no predecessor; every version above `1` has exactly the immediately preceding version. Each stream
has one root and each row has at most one successor, so corrections cannot fork.

#### `investment_input_snapshot`

| Column | Type and nullability | Meaning |
| --- | --- | --- |
| `id` | string PK | immutable frozen-input identity |
| `account_id` | string, not null | account boundary |
| `case_key` | nonblank string, not null | stable Prüfobjekt correction stream |
| `version` | positive integer, not null | stream version, starting at `1` |
| `input_snapshot` | JSONB object, not null | normalized public engine facts |
| `rule_snapshot` | nonempty JSONB object, not null | complete `InvestmentRuleBundle` used for calculation |
| `financing_provenance_snapshot` | nonempty JSONB object, not null | stored financing source and version |
| `afa_provenance_snapshot` | nonempty JSONB object, not null | stored AfA source and version |
| `layout_version_id` | string, nullable | frozen layout selection; null means no Bank-PDF layout selected |
| `canonical_payload_version` | nonblank string, not null | exactly `postgres-jsonb-text-v1` |
| `canonical_payload_bytes` | nonempty bytes, not null | canonical reproduction-input bytes defined below |
| `sha256` | 64 lowercase hex characters, not null | SHA-256 of `canonical_payload_bytes` |
| `supersedes_input_snapshot_id` | string, nullable | prior version in the same account and `case_key` |
| `frozen_at` | timezone timestamp, not null | time at which inputs became immutable |

The public `input_snapshot` shape uses only these normalized engine keys, with their existing engine
types: integer cents/rates/month counts; string provenance/version fields; tuple values serialized as
JSON arrays; and nested JSON objects for `afa_reference` and `bank_header`:

```text
purchase_price_cents, acquisition_costs_cents, monthly_actual_rent_cents, vacancy_bp,
administration_cents, maintenance_cents, reserve_cents, vacancy_risk_cents, equity_cents,
loan_cents, interest_bp, initial_repayment_bp, fixed_monthly_annuity_cents, marginal_tax_bp,
building_share_bp, afa_rate_bp, annual_full_afa_cents, afa_record_version,
analysis_period_months, financing_provenance, afa_reference, bank_header, renter_names
```

No other key is permitted. Each supplied cents/rate/month field is a JSON integer, never a string,
fraction or boolean. Purchase price, acquisition costs, monthly rent, all four planning costs,
equity, loan, interest, initial repayment, fixed annuity, AfA rate and annual full AfA are
nonnegative. `vacancy_bp` and `building_share_bp` are `0…10000`, `marginal_tax_bp` is `0…9999`,
and `analysis_period_months` is nonnegative. `financing_provenance`, when supplied, is one of the
strings `annahme`, `indikativ` or `angebot`. `afa_record_version`, when supplied, is a nonblank
string and is required when top-level `annual_full_afa_cents` is non-null.

`afa_reference` is null or an object containing only `afa_basis_cents`,
`annual_full_afa_cents`, `source` and `record_version`. Its two amount fields are null or
nonnegative JSON integers. If either amount is non-null, both metadata fields are required as
nonblank strings. `bank_header` is null or an object containing only `address`, `property_type`,
`year_built`, `area_sqm_x100`, `unit_count`, `creator`, `export_date` and `layout_version`.
Supplied text fields are nonblank strings; `year_built` is a positive JSON integer; area and unit
count are nonnegative JSON integers. `renter_names` is null or an array of strings and remains
excluded from Bank-PDF output.

An optional value that was absent stays absent or JSON null exactly as received. It is never
replaced by numeric zero. A zero is stored only when the caller explicitly supplied a valid zero.
`rule_snapshot` has exactly these required fields and JSON types:

```text
default_building_share_bp: integer 0…10000
default_afa_rate_bp: nonnegative integer
default_marginal_tax_bp: integer 0…9999
interest_sensitivity_offsets_bp: exactly five ordered integers with exactly one 0
repayment_sensitivity_steps_bp: exactly four strictly increasing positive integers
dscr_amber_hundredths: nonnegative integer
dscr_green_hundredths: nonnegative integer, at least dscr_amber_hundredths
cashflow_amber_cents: integer
cashflow_green_cents: integer, at least cashflow_amber_cents
source_evidence: nonempty array of nonblank strings
rechtsstand: nonblank string
production_blocked: boolean
```

`financing_provenance_snapshot` has exactly nonblank string `source` and `record_version`; `source`
is one of `annahme`, `indikativ` or `angebot`. `afa_provenance_snapshot` preserves the complete
engine provenance object and requires nonblank string `source` and `record_version` plus boolean
`assumption`. Linked Page-03 and Wizard nested provenance remains inside that object unchanged.

`(id, account_id, case_key)` and `(account_id, case_key, version)` are unique. The predecessor is a
composite self-FK on `(supersedes_input_snapshot_id, account_id, case_key)` with the same root,
immediate-version and no-fork rules as layout versions. `layout_version_id`, when present, is a
composite FK with `account_id` to `investment_layout_version(id, account_id)`.

#### `investment_result_snapshot`

| Column | Type and nullability | Meaning |
| --- | --- | --- |
| `id` | string PK | immutable result identity |
| `account_id` | string, not null | account boundary |
| `input_snapshot_id` | string, not null | the one frozen input that produced this result |
| `engine_version` | nonblank string, not null | exact investment-engine release identity |
| `result_snapshot` | nonempty JSONB object, not null | complete plain `InvestmentResult` mapping |
| `canonical_payload_version` | nonblank string, not null | exactly `postgres-jsonb-text-v1` |
| `canonical_result_bytes` | nonempty bytes, not null | canonical result bytes defined below |
| `sha256` | 64 lowercase hex characters, not null | SHA-256 of `canonical_result_bytes` |
| `calculated_at` | timezone timestamp, not null | calculation time |

`(id, account_id)` is unique. `(input_snapshot_id, account_id)` is both a composite FK to
`investment_input_snapshot(id, account_id)` and unique, so a frozen input has at most one stored
result. A correction appends a new input version and its new result; a result is never corrected or
relinked in place. `result_snapshot` has exactly all fields of the plain `InvestmentResult`:

```text
outcome: "calculated" or "hard_block"
calculated_values, kpi_slots: objects
source_evidence: nonempty array of nonblank strings
rechtsstand: nonblank string
production_blocked: boolean
applied_conventions: nonempty array of nonblank strings
financing_provenance, afa_provenance, tax_provenance, bank_view: objects
interest_sensitivity, repayment_sensitivity: arrays of objects
repayment_axis_meaning, tax_scenario_label: nonblank strings
findings, warnings: arrays of strings
guard: object
```

No field may be omitted and no additional field is permitted. A `hard_block` keeps the engine's
nonempty financing provenance selected before the repayment guard, empty calculated values and KPI
slots, empty AfA/tax provenance, empty Bank view and sensitivity containers, and the complete
nonblank repayment guard. A `calculated` result keeps its complete values and an empty guard.
Database shape checks reject structurally incomplete or invented result mappings. The canonical
replay check below remains the authority for the numeric content.

#### Canonical bytes and lifecycle

Canonical JSON is PostgreSQL JSONB text encoded as UTF-8. For an input row the value is the JSONB
object with exactly these keys: `afa_provenance`, `financing_provenance`, `input`,
`layout_version_id` and `rules`, populated from the corresponding frozen columns. Its UTF-8 bytes
must equal `canonical_payload_bytes`. For a result row, `canonical_result_bytes` is exactly UTF-8
`result_snapshot::text`. Each stored SHA-256 is the lowercase hex digest of its canonical byte
column. Migration triggers reject any mismatch; application-supplied hashes are never trusted.

Byte-for-byte reproduction means loading only the frozen input row, its frozen rule snapshot and
the identified `engine_version`, running the pure engine, converting its plain result through the
same `postgres-jsonb-text-v1` serializer, and obtaining exactly `canonical_result_bytes` and its
SHA-256. Live account, layout or legal-rule rows never participate in replay.

All three tables reject `UPDATE` and `DELETE`. Layout and input corrections use INSERT plus their
scoped predecessor. A layout row becomes immutable when inserted; an input freezes its nullable
layout selection at `frozen_at`; and the result permanently binds to that input. All three tables
ENABLE and FORCE RLS. Owner-account `SELECT` and `INSERT` policies use `app.account_id`, refuse a
nonempty renter `app.tenancy_id`, and every INSERT policy has an equivalent `WITH CHECK`. M10-I3
adds entitlement and role authorization above this database account boundary.

### 4.8 M10-I3 entitlement and API contract — migration `0046`

This subsection is the accepted D4 technical decision for M10-I3, fixed on 16.09.2026. It does not
approve a price, plan name, purchase flow, billing provider, PDF renderer or any production-blocked
Page-07 convention. Stripe and RevenueCat remain M11 work. The legal and calculation Rechtsstand
remains **07/2026**.

#### Immutable account entitlement

Migration `0046` adds exactly one account-scoped append-only table,
`investment_entitlement_event`:

| Column | Type and nullability | Meaning |
| --- | --- | --- |
| `id` | string PK | immutable event identity |
| `account_id` | string, not null | account boundary |
| `entitlement_key` | string, not null, exactly `INVESTMENT` | the sole M10 investment entitlement stream |
| `version` | positive integer, not null | stream version, starting at `1` |
| `enabled` | boolean, not null | entitlement state from this event onward |
| `supersedes_entitlement_event_id` | string, nullable | immediately preceding event in the same account and stream |
| `recorded_by_membership_id` | string, not null | owner Membership that authorized the event |
| `recorded_at` | server timestamp with timezone, not null | database append time; never caller-supplied |

`(id, account_id, entitlement_key)` and `(account_id, entitlement_key, version)` are unique. The
predecessor is a composite self-FK on
`(supersedes_entitlement_event_id, account_id, entitlement_key)`. The author is a composite FK on
`(recorded_by_membership_id, account_id)` to `membership(id, account_id)`. Version `1` has no
predecessor; every later event points to the immediately preceding version. Each account stream has
one root and every event has at most one successor, so versions cannot skip, cross accounts or fork.

The table rejects `UPDATE` and `DELETE`, and it ENABLEs and FORCEs RLS. `SELECT` and `INSERT` are
limited to the active `app.account_id`, refuse nonempty renter context, and the INSERT policy has an
equivalent `WITH CHECK`. RLS supplies account isolation only. The API separately proves that the
live authorizing Membership is `OWNER`; database account scope is not treated as role authorization.

M10-F migration `0047` adds a database backstop: an entitlement event's author must be a live,
accepted, unrevoked `OWNER` in the same account, and `recorded_at` is overwritten with
`statement_timestamp()` on insertion. The immediate-version predecessor check remains in force.
This closes direct-write actor and caller-supplied timestamp gaps; it adds no table, column, route
or production entitlement. Foreign-account application writes remain subject to forced RLS.

#### Exact route and role surface

The complete M10-I3 surface is exactly:

```text
GET  /a/{account_id}/investment/entitlement
POST /a/{account_id}/investment/entitlement
POST /a/{account_id}/investment/cases
GET  /a/{account_id}/investment/cases/{case_key}
GET  /a/{account_id}/investment/cases/{case_key}/sensitivity
GET  /a/{account_id}/investment/cases/{case_key}/bank-view
```

There is no list route, correction route, PDF route, price, plan name, purchase flow or billing
integration. Every route requires a live `OWNER` Membership in the path account. `EMPLOYEE`,
`TAX_ADVISOR`, a foreign-account Membership and renter context receive no investment access. Only
the owner entitlement POST may enable or disable access. It accepts only `enabled`; the server
appends the next version with its own timestamp, predecessor and author Membership. GET returns the
latest stored state, or `enabled=false` with no event identity when the stream is absent.

An absent entitlement or a latest event with `enabled=false` denies every case route server-side.
Navigation visibility is never authorization. A `case_key` that is absent or belongs to another
account returns the same anti-enumeration `404`.

#### Server-owned create and immutable reads

Case POST accepts exactly `facts` plus optional `layoutVersionId`. `facts` is the normalized public
engine input from § 4.7 except that `renter_names` is forbidden at this boundary. Extra request
fields are rejected, including caller-supplied rules, result, engine version, canonical bytes or
hash, provenance snapshots, account/case/version identifiers and timestamps. These values are
derived by the server and never trusted from the client.

The server resolves one versioned investment rule bundle from `packages/rules-store`. It contains
the complete § 4.7 rule shape, source evidence and Rechtsstand, and keeps every applicable Page-07
production blocker active (`production_blocked=true`). The server then runs the pure
`investment-engine`, derives the complete financing and AfA provenance, canonical PostgreSQL JSONB
bytes and hashes, and atomically inserts input version `1` plus exactly one result. There is no
Building, statement, tax-export or demo dependency.

Malformed public facts or an engine input that cannot produce a valid `InvestmentResult` return
`422` and store neither input nor result. A valid engine `hard_block` is different: it is a complete
auditable result under § 4.7 and is persisted with its input exactly like a calculated result.

All GET routes load the latest stored input/result pair and never run the engine or consult live
rules/layout data. The KPI read returns the logical `caseKey`, input `version` and result identity,
plus the stored `outcome`, `calculatedValues`, `kpiSlots`, twelve-month schedule through the stored
calculated values, `rechtsstand`, `productionBlocked`, `findings` and `warnings`. Sensitivity returns
only the stored `interestSensitivity`, `repaymentSensitivity` and `repaymentAxisMeaning`. Bank-view
returns only the stored `bankView`. No response surface contains `renter_names` or any other renter
identity.

#### M10-I3 RED fixtures

| Fixture | Required behavior |
| --- | --- |
| `M10-INV-F01` | migration `0046` and mapped entitlement event have the exact account-safe append-only shape |
| `M10-INV-F02` | owner enable/disable appends the immediate, non-forking version chain with server author/time |
| `M10-INV-F03` | only `OWNER` reaches any investment route; employee, tax adviser and foreign Membership are denied |
| `M10-INV-F04` | absent or latest-disabled entitlement denies every case route |
| `M10-INV-F05` | valid create atomically stores input v1 plus one result and GET replays the stored result |
| `M10-INV-F06` | KPI, sensitivity and Bank-view reads use stored snapshots only and expose their bounded fields |
| `M10-INV-F07` | a valid engine `hard_block` is persisted as a complete result |
| `M10-INV-F08` | forbidden or invalid request data returns `422` and writes nothing |
| `M10-INV-F09` | foreign/missing cases are `404`; renter identity and billing/product surfaces are absent |
| `M10-INV-F10` | OpenAPI exposes exactly the six route-method pairs above, with no list/correction/PDF route |

### 4.9 M10-I4 cockpit, default layout and Bank-PDF contract

This subsection is the accepted M10-I4 technical decision, fixed on 16.09.2026. It adds no table,
calculation, pricing, purchase, billing, bank integration or production approval. The legal and
calculation Rechtsstand remains **07/2026**, and every production blocker in § 11 stays active.

#### Server-owned immutable default layout

The account-scoped `investment_layout_version` stream with `layout_key = "DEFAULT_BANK"` is the
server-owned Bank-PDF default. Its canonical layout snapshot is a nonempty JSON object with schema
version `investment-bank-pdf-v1`, locale `de-DE`, A4 format, and this exact ordered block list:

```text
header_disclosure
investment
financing_ltv
rent_and_planning_costs
seven_kpis
sensitivity
twelve_month_schedule
assumptions_method
disclosure
```

It also freezes the artifact disclosure from § 2, the product disclaimer
`rechtskonform, keine Rechts- oder Steuerberatung`, the permanent LTV wording
`Auslauf zum Kaufpreis, nicht zum Beleihungswert`, and the missing-value glyph `—`. These are
renderer data, not live copy looked up at download time.

When case POST omits `layoutVersionId`, the server takes an account-and-layout-stream advisory
transaction lock and resolves the latest `DEFAULT_BANK` row. If none exists, it appends version 1
from the server-owned canonical snapshot. If a later server release changes that canonical
snapshot, the first subsequent case appends the immediate next version; it never updates a row.
Concurrent creates for one account therefore produce one root or one immediate successor, never a
fork. Different accounts always receive different account-scoped rows. A latest row whose snapshot
already equals the canonical snapshot is reused.

The selected row ID is persisted on the new frozen input before the case transaction completes.
An explicitly supplied same-account `layoutVersionId` remains supported and is frozen unchanged.
An existing case never floats to a later default-layout version. Default resolution, optional
layout append, input and result insertion are one transaction: any case failure leaves none of
those writes behind. No layout-management route, caller-supplied layout snapshot or new table is
added.

#### Exact route, authorization and frozen rendering

M10-I4 adds exactly one route to the six route-method pairs in § 4.8:

```text
GET /a/{account_id}/investment/cases/{case_key}/bank-pdf
```

The complete investment API surface is therefore exactly seven method-path pairs. The PDF route
requires a live `OWNER` Membership and latest enabled D4 entitlement exactly like every other case
route. Employee, tax-adviser, foreign-Membership and renter contexts are denied. A missing or
foreign `case_key` returns the same anti-enumeration `404` as the stored JSON reads.

The route loads only the latest frozen input/result pair for that case and the exact
`investment_layout_version.id` stored on that input. Its renderer input is an immutable, slotted
value carrying the stored `bank_view`, complete stored result snapshot, exact stored layout
snapshot and their frozen identities. It does not run the investment engine, resolve a live rule
bundle, resolve the latest layout stream, or read Building, Renter, statement, tax-export or demo
data. A legacy frozen input whose `layout_version_id` is null receives `409` with
`Für dieses Prüfobjekt ist keine PDF-Vorlage gespeichert.`; it never acquires the current default
retroactively.

The response is `application/pdf` with attachment filename
`investitionsuebersicht-{case_key}.pdf`. For identical frozen renderer input and the same renderer
version, two renders are byte-identical. The document uses the exact block order above. It renders
all seven stored KPI slots, both stored sensitivity axes and exactly twelve stored schedule rows;
it performs no arithmetic. Under `14-F12` partial data stays renderable: every unavailable value is
the standalone glyph `—`, with `Daten unvollständig`, and the financing section carries a soft
missing-financing note. Missing loan facts must not be presented as known zero debt or as
`Kein Fremdkapital`; that non-applicability statement is reserved for explicitly stored zero
financing. The `14-F12` data-only oracle records this as
`partial_pdf_renderable=true` but has no second partial mapping. Its machine-readable partial branch
therefore follows only the Page-07 F12/E12 sentence: keep the reference purchase, rent and planning
facts; omit financing; keep factor, gross and net; and render LTV, DSCR, cashflow, equity return and
break-even as `—`. Empty sensitivity and schedule sections show, in their own block, respectively
`Daten unvollständig – ohne Finanzierung ist keine Sensitivität verfügbar.` and
`Daten unvollständig – ohne Finanzierung ist kein Annuitätenplan verfügbar.` They render no empty
table. Export dates use German `DD.MM.JJJJ`; every rendered money value has two decimal places,
including `0,00 €`.

The `M10-I4-F03` renderer fixture consumes the actual engine-derived Bank view of that no-financing
input, not a manually assembled partial mapping. Its expected factor/gross/net values come from
the approved `14-F01` oracle; each missing financing-dependent KPI, both LTV values and the empty
sensitivity/schedule blocks are checked separately so an earlier failure cannot hide another one.

The document visibly prints the artifact disclosure, product disclaimer, Rechtsstand and
production-blocked state. It contains no renter identity and is not a valuation, appraisal, credit
decision, bank application, archive, tax export or investment recommendation. It has no automatic
sending and no purchase or billing action.

#### Cockpit route and case hand-off

The owner-only web route is `/a/{accountId}/investment`. Navigation visibility follows the live
Membership, but the API remains authoritative. The page first loads entitlement. Pending, failed,
absent/disabled and non-owner states do not request case data or expose creation/download actions.

The selected immutable case is carried only as the URL query `caseKey`. If it is present, the page
loads that exact case through the three stored JSON reads from § 4.8; it neither guesses nor lists
cases. If absent, the page offers the Page-07 Prüfobjekt input flow and posts to the existing case
route. The UI omits `layoutVersionId`; the server binds the default as specified above. After a
successful POST it replaces the URL with the returned `caseKey` and displays that frozen result.
Reload and share therefore preserve the case hand-off without local storage, a list route or a
correction route.

Case entry uses landlord-facing euros, percentages, years, square metres and unit counts, never
raw cents or basis points. It covers purchase price and acquisition costs; monthly actual cold
rent and vacancy; all four annual planning-cost amounts; equity, loan, interest, initial repayment
and financing provenance; marginal tax, building share and AfA rate; and the optional Bank header
address, property type, construction year, area, unit count, creator and export date. On explicit
submit the client only validates and normalizes these values to the exact public § 4.7 API facts:
euros to integer cents, percentages to integer basis points and square metres to integer
hundredths. It sends the fixed twelve-month analysis period and performs no KPI, schedule,
sensitivity, tax, AfA or financing calculation.

The cockpit shows exactly the seven KPIs from § 6, the five stored interest rows, the four stored
repayment rows and exactly twelve stored schedule rows. Unavailable KPI values use `—` and `Daten
unvollständig`. Only DSCR and after-tax monthly cashflow may use the stored `14-K19` red/amber/green
liquidity colours. The visible explanation says `Liquiditätsindikator unter Ihren Annahmen – keine
Risikobewertung und keine Bankzusage.` Repayment keeps liquidity and debt reduction together and
states that it is a structure trade-off, not a stress or risk axis. There is no score, ranking,
winner, recommendation, default target return or client-side recalculation. The download action
targets only the exact Bank-PDF route above.

#### M10-I4 RED fixtures

| Fixture | Required behavior |
| --- | --- |
| `M10-I4-F01` | immutable renderer data consumes only frozen bank-view/result/exact-layout snapshots |
| `M10-I4-F02` | Bank-PDF uses the exact block order, German disclosures, disclaimer and LTV wording |
| `M10-I4-F03` | the Page-07 F12/E12 no-financing subcase renders standalone `—`, honest in-block absence notes and no empty tables |
| `M10-I4-F04` | PDF contains no renter identity, valuation/advice claim, sending, purchase or billing surface |
| `M10-I4-F05` | two Chromium renders of one frozen input are byte-identical |
| `M10-I4-F06` | omitted layout creates/reuses one account-isolated, concurrency-safe `DEFAULT_BANK` version; explicit same-account layout remains exact |
| `M10-I4-F07` | owner, D4, renter-context and anti-enumeration rules protect the PDF route; OpenAPI has exactly seven method-path pairs |
| `M10-I4-F08` | PDF loads the stored exact layout/result only, never engine, live rules or a newer layout; null legacy layout is `409` |
| `M10-I4-F09` | owner cockpit normalizes complete euro/percent inputs, then case hand-off shows seven KPIs, both sensitivity axes, twelve schedule rows and PDF download |
| `M10-I4-F10` | entitlement/role states, partial copy and visible liquidity-only red/amber/green styling expose no score, ranking, recommendation or default target return |

## 5. Inputs

| Group | Inputs and units |
| --- | --- |
| Purchase | `kaufpreisCent > 0`, `erwerbsnebenkostenCent ≥ 0`, derived `gesamtinvestitionCent`, `bundesland` |
| Rent | `istKaltmieteMonatCent ≥ 0`, optional market-rent scenario, excluded other income, `leerstandBp 0…10000` |
| Planning costs | annual administration, actual maintenance, maintenance reserve and vacancy-risk amounts, all integer cents |
| Financing | equity and loan cents, interest Bp, either initial-repayment Bp or fixed monthly annuity, fixed-period info and provenance |
| Tax/AfA | marginal-tax Bp; building-share Bp, AfA-rate Bp, basis and annual full AfA with provenance |
| Bank header | optional address/type/year/area/units/creator, export date and versioned layout |

Cash planning expense is the sum of all four planning costs. The tax-scenario deduction is only
administration plus actual maintenance. Page 09 supplies the identities; it does not supply these
planning amounts.

## 6. The seven KPIs and conventions `14-K01…14-K19`

The KPI set is exactly:

1. Kaufpreisfaktor;
2. Bruttomietrendite;
3. Nettomietrendite;
4. DSCR;
5. Eigenkapitalrendite before and after tax;
6. Cashflow before and after tax; and
7. Break-Even-Miete before and after tax.

| ID | Binding Page-07 choice |
| --- | --- |
| `14-K01` | factor uses purchase price and actual annual cold rent |
| `14-K02` | gross yield is the reciprocal convention on purchase price |
| `14-K03` | net yield uses effective rent less full cash planning costs over total investment |
| `14-K04` | DSCR is NOI divided by full annual debt service, before tax; target band 1.20–1.35 is unverified |
| `14-K05` | absent linked data, 75% building share and 2% linear AfA are labelled assumptions |
| `14-K06` | linked Page-03 R13 wins, then explicit wizard values, then assumptions |
| `14-K07` | KPIs use a normalized full year: annual full AfA and first twelve full loan payments |
| `14-K08` | equity return is shown before and after tax, both including repayment; cash-on-cash without repayment is tooltip only |
| `14-K09` | reserve and vacancy risk reduce cashflow but not the flat tax scenario |
| `14-K10` | break-even holds planning-cost euro amounts constant |
| `14-K11` | comparisons may mark the better value per row, never an overall winner; any traffic light compares only with the user's own target return, with no recommendation, ranking or default target |
| `14-K12` | factor/gross use actual rent; the other five KPIs use vacancy-adjusted effective rent |
| `14-K13` | editable 42% marginal-tax default; no derived income, solidarity surcharge or church tax |
| `14-K14` | Bank-PDF is self-disclosure; LTV uses purchase price; no valuation or renter names |
| `14-K15` | Bank-PDF is a deterministic view with no recalculation |
| `14-K16` | financing is labelled by assumption/indication/offer provenance, defaults to assumption before an offer, and keeps the three rent KPIs separate from the four financing-dependent KPIs |
| `14-K17` | five-step interest sensitivity replaces single-rate false precision |
| `14-K18` | the Pitch-MVP interactive axes separate interest stress from repayment structure, show liquidity and debt reduction together, and clamp at the R3 guard |
| `14-K19` | liquidity colours: DSCR red `<1.00`, amber `1.00–1.19`, green `≥1.20`; after-tax monthly cashflow red `<0`, amber `0…49.99 EUR`, green `≥50 EUR`; applies only under the user's assumptions and is not a risk grade or bank promise |

Every convention and threshold remains `verify-before-production` even where fixture arithmetic is
green.

## 7. Calculation order `R1…R10`

Global rounding: integer additions are exact. Each fractional step uses one half-up rounding to an
integer. Percent results use basis points; factor and DSCR use hundredths.

### R1 — effective annual cold rent

```text
annual_actual_rent = monthly_actual_rent * 12
effective_annual_rent = half_up(annual_actual_rent * (10000 - vacancy_bp) / 10000)
```

### R2 — NOI

```text
cash_costs = administration + actual_maintenance + reserve + vacancy_risk
deductible_costs = administration + actual_maintenance
NOI = effective_annual_rent - cash_costs
```

NOI may be negative.

### R3 — twelve full annuity payments

```text
monthly_annuity = fixed_monthly_annuity
  or half_up(loan * (interest_bp + initial_repayment_bp) / 120000)
balance = loan
for month 1..12:
  interest = half_up(balance * interest_bp / 120000)
  repayment = monthly_annuity - interest
  repayment <= 0 -> HARD BLOCK
  balance -= repayment
annual_debt_service = monthly_annuity * 12
annual_interest + annual_repayment == annual_debt_service
```

A zero loan yields zero interest, repayment and debt service; DSCR is `n/a (kein Fremdkapital)`.

### R4 — AfA reference

Linked Page-03 R13 values win. Otherwise:

```text
basis = half_up(total_investment * building_share_bp / 10000)
annual_full_afa = half_up(basis * afa_rate_bp / 10000)
```

These derived values remain acquisition assumptions, not real AfA.

### R5 — flat tax scenario

```text
tax_base = effective_annual_rent - deductible_costs - interest - annual_full_afa
tax = half_up(tax_base * marginal_tax_bp / 10000)
```

The unresolved Page-03 R13/R3-interest ambiguity applies. Negative tax is scenario arithmetic only.

### R6 — cashflow

```text
cashflow_before_tax_year = effective_annual_rent - cash_costs - debt_service
cashflow_after_tax_year = cashflow_before_tax_year - tax
monthly values = half_up(annual / 12)
```

### R7 — KPI formulas

```text
factor_hundredths = half_up(purchase_price * 100 / annual_actual_rent)
gross_yield_bp = half_up(annual_actual_rent * 10000 / purchase_price)
net_yield_bp = half_up(NOI * 10000 / total_investment)
dscr_hundredths = half_up(NOI * 100 / annual_debt_service)
equity_return_before_bp = half_up((cashflow_before_year + repayment) * 10000 / equity)
equity_return_after_bp = half_up((cashflow_after_year + repayment) * 10000 / equity)
break_even_before_year = cash_costs + debt_service
break_even_after_year = half_up((cash_costs + debt_service
  - half_up(marginal_tax_bp * (deductible_costs + interest + annual_full_afa) / 10000))
  * 10000 / (10000 - marginal_tax_bp))
```

### R8 — completeness

Factor/gross need price and rent. Net also needs acquisition costs and planning costs. DSCR needs
financing. After-tax cashflow and break-even also need tax/AfA provenance. Equity return additionally
needs equity. Any missing requirement returns `—` and “Daten unvollständig”.

### R9 — Bank-PDF view

LTV to purchase price and total investment is half-up in Bp. A zero/missing loan yields `—` and a
soft note. The view uses the frozen R1–R8/R10 outputs and fixed block order from §4.6.

### R10 — sensitivity

Each interest or repayment step is a complete R3–R7 rerun. Only the selected axis changes. The
interest table has five rows and highlights the base assumption. Factor, gross and net stay fixed.

## 8. Edge cases `14-E01…14-E15`

| ID | Required behavior | Fixture |
| --- | --- | --- |
| `14-E01` | price+rent only computes factor/gross; all else `—` | `14-F06` |
| `14-E02` | zero/missing denominator returns `—`, not zero/error | rule |
| `14-E03` | all equity: debt values zero; DSCR `n/a`; other results compute | `14-F04` |
| `14-E04` | negative NOI/cashflow and negative flat-tax scenario are valid fixed-point results | `14-F10` |
| `14-E05` | vacancy affects effective-rent KPIs, never factor/gross | `14-F07` |
| `14-E06` | linked Page-03 AfA wins and is labelled | `14-F08` |
| `14-E07` | fixed monthly annuity is used directly | `14-F03` |
| `14-E08` | non-positive repayment hard-blocks | `14-F09` |
| `14-E09` | zero tax rate makes before/after cashflow equal | rule |
| `14-E10` | non-12-month period is inapplicable; KPIs always normalized full year | rule |
| `14-E11` | unrealistic acquisition costs warn, never block | rule |
| `14-E12` | partial/no-financing Bank-PDF remains renderable with `—` | `14-F12` |
| `14-E13` | LTV is permanently labelled to purchase price, not lending value | `14-F12` |
| `14-E14` | pre-offer financing computes with assumption badge and sensitivity | `14-F13` |
| `14-E15` | control clamps at E08 and shows guard text | `14-F14` |

## 9. Fixture coverage

The data-only oracle preserves exactly 14 fixtures:

| Fixture | Coverage |
| --- | --- |
| `14-F01` | reference inputs, all seven KPIs and before/after-tax results |
| `14-F02` | 12-row initial-repayment annuity branch and both reconciliation probes |
| `14-F03` | fixed-monthly-annuity branch |
| `14-F04` | all-equity case |
| `14-F05` | two equity-return columns plus tooltip |
| `14-F06` | partial input |
| `14-F07` | 5% vacancy |
| `14-F08` | Page-03 AfA provenance wins |
| `14-F09` | non-positive repayment guard |
| `14-F10` | negative cashflow and negative flat-tax scenario |
| `14-F11` | factor/gross reciprocal check |
| `14-F12` | Bank-PDF/LTV data and partial-data behavior |
| `14-F13` | five-step interest sensitivity |
| `14-F14` | four-step repayment trade-off |

## 10. Non-Goals and source exclusions

The eight Page-07 `Non-Goals V1` are preserved exactly as groups:

1. no multi-year projection, resale, IRR, NPV or appreciation;
2. no AfA calculation or 15% guard;
3. no solidarity surcharge, church tax, progression or loss-offset limits;
4. no variable rates, refinancing, forward loan or prepayment optimization;
5. no parking/other income in rent KPIs and no commercial units with VAT;
6. no purchase/investment recommendation, winner or default target return;
7. Bank-PDF has no lending/market value, credit information, appraisal or automatic sending; and
8. no real bank-rate retrieval, comparison calculator or financing-broker connection.

The source Page's eight Out-of-Scope groups are also preserved: long-hold/exit metrics; AfA
derivation; tax export/Anlage V/DATEV; financing beyond the first twelve fixed payments; surcharge,
church-tax, progression and loss-offset rules; other/commercial income and pre-purchase development
calculation; purchase/ranking recommendations; and Bank-PDF valuation/credit/application claims.

## 11. Unresolved production blockers

- every default, threshold and KPI convention in the register;
- how often a linked Page-03 AfA record is available during acquisition;
- the editable marginal-tax default and all flat-tax scenario limits;
- the capital-markets permission claim;
- every missing concept from the two absent source files; and
- real AfA availability and financing provenance at the time a Prüfobjekt is evaluated.

Round 4 settled the Page-03 R13/Page-07 R3 interest choice and the target-return/default policy.
The still Berkay-answerable re-delivery of the two absent source files is routed to
`FRAGEN-an-Berkay-05.md`. Legal verification and all remaining production blockers stay in this
owning document.

## 12. Source coverage ledger

| Source surface | Destination |
| --- | --- |
| Page metadata, purpose, legal basis and 19 conventions | §§1–6 and oracle identifier surfaces |
| inputs and provenance | §§4–5 |
| `R1…R10` | §7 and recomputed fixtures |
| `KPI-E01…E15` | §8 / `14-E01…E15` |
| `KPI-F01…F14` | §9 / `14-F01…F14` |
| eight Page Out-of-Scope groups | §10 |
| eight Page-07 Non-Goals | §10 |
| 18 register rows | §3 and `PAGE_07_REGISTER_ROWS` |
| arithmetic audit | §1 and `ARITHMETIC_AUDIT` |
| M10-I2 technical persistence decision accepted 12.09.2026 | §4.7 and migration `0045` fixtures |

`docs/03` Appendix D is the single historical correspondence-retirement ledger. It records no
Page-07 rule; current Page-07 authority is fully covered above.
