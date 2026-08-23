# 03 — NK and heating/CO₂ engines

This is Lokara's canonical, living specification for operating-cost allocation and the Page 01b
heating/CO₂ calculation. It states the active contract, the bounded capabilities already shipped,
and the exact work still needed for end-to-end closure. Superseded implementation chronology and
full earlier arguments remain available with
`git show 635acf9:docs/03-nk-heating-engines.md`.

The authoritative heating source is
`berkay-work/Spec-Seiten/01b · Heizkosten- & CO₂-Verteilung 3a95fd420731814e9e5be043028d4856.md`,
the authoritative 47 matching rows in
`berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv`, and the approved supersession history
below. The CSV wins for structured values and flags. Appendix D is historical only.
`docs/08-statement-document.md` owns the document projection. This file owns the calculation.

## Reading guide and status vocabulary

Statuses describe repository delivery, not legal certainty. A shipped value can still be
`verify-before-production`; `geprüft` means its primary source was checked, not lawyer approval.

| Status | Meaning |
| --- | --- |
| **Shipped** | Present on `main` in production source and covered by the current gates. |
| **Capability shipped** | A bounded pure behavior is implemented and green, but the complete Page 01b workflow is not closed. |
| **Specified** | Documented as the implementation contract; its review state is stated separately. A data-only oracle validates transcription, not production behavior. |
| **Prepared but unmerged** | Implemented and verified on another branch, but absent from `main`. |
| **Future** | Ownership is known, but the final interface or rule is not yet approved or shipped. |

## 0. Compatibility guide for the Page 01b trace

### 0.3 Source coverage and fixture gate

The complete source-section map and all 34 fixture IDs are in Appendices A and B. This preserves the
former § 0.3 reference used by other documents without keeping fixture status inside the active
calculation flow.

### 0.4 Register inventory, conflicts, and dependencies

All 47 Page 01b register rows are in Appendix C. Current conflicts and dependencies are numbered in
§ 7; the correspondence-retirement trace is in Appendix D. This preserves the former § 0.4 reference.

## 1. Shared pure-engine boundary and data flow

### 1.1 Round 4 — reductions and Block (c) (source: `Antwort-an-Emir_04.md` §§ 1.1–1.2, Rechtsstand 08/2026)

This supersedes the unresolved prose in § 7 items 12 and 14, but does **not** implement an automatic
deduction. It is an implementation contract for a later owner lane. The cumulation result is
`Konvention`, `verify-before-production`, Anwaltspunkt: no BGH decision or settled literature line
was supplied. The three components stay independently switchable.

```text
reduction = half_up(non_consumption_cost_share × 15%)
          + half_up(total_cost_share × 3%) [§ 12(1) S. 2: one hardware ground]
          + half_up(total_cost_share × 3%) [§ 12(1) S. 3: missing/incomplete § 6a information]
```

All three summands use their own **unreduced** base and never cascade. The two 3% grounds may
cumulate (maximum 6%); 3% and 15% may cumulate only across their distinct cost masses. The overall
ceiling is 21%. From two simultaneous grounds, emit the non-blocking warning: “Zwei
Kürzungsgründe gleichzeitig — bitte prüfen Sie, ob beide zutreffen. Die Kürzungen wirken
nebeneinander.” The output never represents § 5(2) and § 5(3) as two separate 3% rights.

#### § 12 reduction result boundary (implementation contract)

`calculate_page01b_statement` returns a separate, audit-only `section12_reduction` result. It
does not replace the existing warning-only API, PDF, or web projection in this slice. For each
Mietverhältnis it retains, in cents, `gross_claim`, the separately half-up rounded
`non_consumption_15_percent`, `remote_readability_3_percent`, and
`section_6a_information_3_percent`, their `total_deduction`, and `net_claim`. The result also
lists the active § 12 grounds and, from two active grounds, exactly this non-blocking warning:
“Zwei Kürzungsgründe gleichzeitig — bitte prüfen Sie, ob beide zutreffen. Die Kürzungen wirken
nebeneinander.” `co2_disclosure_missing` remains an independent warning risk and is never a § 12
component.

For self-billing, the 15% base is each allocation line's existing non-consumption positions
(`heating_base + ww_base`); the engine must not infer a different share or recalculate a line. For
MDL, the caller supplies one non-consumption position per renter alongside the confirmed gross
positions. A missing split, a length mismatch, a negative supplied value, or a supplied split
above its confirmed renter position yields an explicit **incomplete** § 12 result and no net
claim; it neither guesses a split nor recalculates MDL raw inputs. A complete result preserves
gross values even where every component is zero, satisfies `gross_claim − total_deduction =
net_claim` per renter, and applies the 21% ceiling after the three independently rounded,
non-cascading components have been calculated. This remains `Konvention`,
`verify-before-production`, and an Anwaltspunkt (Rechtsstand 08/2026); the values belong in a
versioned rule surface rather than an unversioned production-law assertion.

Block (c) is a mandatory audit value, never a second pot: `printed owner residual − sum(separately
rounded origins)`. It is a subline of the owner residual, with no Bemessung or quota. Print only a
non-zero value, but always retain it in the audit log. The required text is
“Rundungsdifferenz aus der zeilenweisen Verteilung — keiner Einheit zurechenbar” for the vacancy
schedule and “davon Rundungsdifferenz” below the owner row in the statement. This is `Konvention`,
with no external source and no `verify-before-production` requirement.

Both engines are pure Python packages. They import no web framework, database model, vendor SDK, or
rules-store implementation. Adapters normalize persisted and supplier data first; callers resolve
versioned legal values and pass plain domain shapes into the engines.

```text
DB / supplier / MDL
        │ adapters normalize values, dates, units and provenance
        ▼
domain value objects + resolved rules
        ├── NK input ───────────────► nk-engine ────────────┐
        └── plant/device/invoice ──► heating-engine ───────┤
                                                           ▼
                                  normalized result + warnings/readiness
                                                           │
                                  audience projection in docs/08
                                                           ▼
                                             API / landlord PDF
```

| Boundary | Contract |
| --- | --- |
| Inputs | Frozen dataclasses or equivalent plain normalized values. Dates and units travel with the values they qualify. |
| Money | Integer cents. Intermediate quotients use `decimal.Decimal`, never `float`. |
| Rules | Versioned values are resolved by the caller with an as-of date. Engines receive domain shapes and never import `rules-store`. |
| Outputs | Deterministic result objects with renter shares, one unconditional owner residual where applicable, calculation intermediates, and reconciliation totals. |
| Rendering | De-scale fixed-point integers only at the presentation boundary; never format engine storage units directly. |
| Tax | Anlage-V mappings do not enter either engine. They belong to the later tax/export handoff. |

The live interfaces are
[`packages/nk-engine/src/lokara_nk_engine/inputs.py`](../packages/nk-engine/src/lokara_nk_engine/inputs.py),
[`packages/heating-engine/src/lokara_heating_engine/inputs.py`](../packages/heating-engine/src/lokara_heating_engine/inputs.py),
and the shared value objects under
[`packages/domain/src/lokara_domain`](../packages/domain/src/lokara_domain).

## 2. NK engine contract and current Slice C boundary

[`calculate_nk_statement`](../packages/nk-engine/src/lokara_nk_engine/engine.py) is **shipped**. It
allocates day-weighted operating costs using the current normalized input:

| Input | Required behavior |
| --- | --- |
| `billing_period` | Bounded half-open engine period. The Page 01 caller separately blocks a residential statement longer than 12 months. |
| `units` | Stable input order; `area_sqm_x100`, and `mea_x10000` when MEA is selected. |
| `occupancies` | Dated renter, vacancy, and self-use segments. Unbilled unit-days remain on the owner side. |
| `costs` | Cost identity, label, integer cents, per-period key, and an exact direct target where `DIRECT` applies. |
| `person_counts` | Dated person counts for the `PERSONS` key. |
| `consumptions` | Normalized values with one compatible measurement unit for a checkable denominator. |

Supported keys are `AREA`, `PERSONS`, `CONSUMPTION`, `UNITS`, `DIRECT`, and `MEA`. `DIRECT` bypasses
proportional allocation. Each cost reconciles independently. Current output is a stable tuple of
`ShareLine(cost_id, unit_id, tenancy_id, weight, amount)`, a total, and the resolved consumption
measurement unit.

### Canonical €1,200 fixture

Garbage cost: **€1,200.00**, period 2025, key `AREA`.

| Party | Area | Days | m²·days | Share |
| --- | ---: | ---: | ---: | ---: |
| Unit A — renter 1 | 50 m² | 365 | 18,250 | €600.00 |
| Unit B — renter 2, through 30 June | 30 m² | 181 | 5,430 | €178.52 |
| Unit B — vacant, July–December | 30 m² | 184 | 5,520 | €181.48 to owner |
| Unit C — renter 3 | 20 m² | 365 | 7,300 | €240.00 |
| **Total** |  |  | **36,500** | **€1,200.00** |

The current engine uses renter-half-up rounding and one owner residual. This exact fixture also
produces the same cents under the former largest-remainder method, so it remains a stable oracle.

### Slice C technical closure and production boundary

`docs/09-betrkv-catalogue.md` is merged with the Page 02 contract and exact `09-F01`–`09-F32` data
oracle. Slice C technically implements that contract. It does not prove legal production approval:

- NK uses renter-half-up rounding and one owner residual;
- technical eligibility and classification behavior is implemented, while its flagged legal inputs
  remain production-blocking;
- every missing register assignment and unresolved classification remains
  `verify-before-production`;
- `DIRECT`, `PERSONS`, `CONSUMPTION`, period validation, and end-to-end Page 02 fixtures are covered
  by Slice C; their applicable flagged authority remains `verify-before-production`.

The Page 08 bank-matching contract is **approved and merged** in `docs/15`. That approved doc and
its oracle resolve `BANKMATCH-F03`, and all thirteen cases are executable. This
specification status does not change any current NK or heating behavior.

## 3. Page 01b current decisions

The following four headings are compatibility anchors for code, tests, `docs/06`, and `docs/08`.
They state the current rule without retaining the implementation diary that led to it.

### Seite 01b decision (1) Rounding — `round_half_up` per share plus `Verteilungsrest`

Heating rounds every renter share once, half up, at assignment. The block remainder goes to one
Liegenschafts-Residuum. The line always exists, including `0.00 EUR`, may be negative, and is not a
party, quota, or separately weighted amount. K9 keeps its `verify-before-production` flag for the
rounding convention; the destination is Berkay's fixed model rule.

### Seite 01b decision (2) K3 — VDI 2067 Blatt 1, Ausgabe 12/1983, Tabelle 22

The degree-day table is stored as **Zehntelpromille**, sum `10,000`:

| Month | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Display ‰ | 170 | 150 | 130 | 80 | 40 | 13.3 | 13.3 | 13.4 | 30 | 80 | 120 | 160 |
| Stored tenth-promille | 1700 | 1500 | 1300 | 800 | 400 | 133 | 133 | 134 | 300 | 800 | 1200 | 1600 |

Display divides by ten. K3 is a VDI convention and remains `verify-before-production`. Its shipped
money consequence is the current demo pair `776.52 EUR / 554.74 EUR` for the affected unit-B heating
rows; the allocation method did not cause that change.

### Seite 01b decision (3) CO₂ short billing period — annualise before lookup

For `nTage` other than 365 or 366:

```text
raw specific intensity = (CO₂ grams / 1,000,000) / heated area m²
annualised intensity   = raw specific intensity × 365 / nTage
classified intensity   = round_half_up(annualised intensity, 1 decimal)
step                   = lookup10(classified intensity, unshortened table)
```

The one-decimal value is both classified and printed, including a trailing zero. A period over 12
months is refused before annualisation. The flat divisor 365 and the 365/366 trigger are transcribed
as written and remain conflict item 8 in § 7.

#### Divisor and 365/366 trigger

Use flat 365 for a short period and do not annualise a period of exactly 365 or 366 days. This is the
transcribed Page 01b convention, including the unusual non-calendar 366-day case; it is not silently
replaced by an anchored reference year.

#### Why a period > 12 months is refused rather than scaled

Page 01 already makes such a residential billing period invalid. Scaling or capping would invent a
legal classification and could shift CO₂ cost to either side. The engine therefore raises a German
input error before H2 while unrelated operating-cost work may continue through its own valid path.

#### ⛔ SUPERSEDED — The Stufenmodell is a per-year table

The old method shortened every finite table bound by the billing-period fraction and printed a
period intensity against a per-year label. It selected the same mathematical step but disclosed a
non-statutory shortened band. It is superseded by H2/R8 above. The full old argument is available at
commit `635acf9`; it is not an active alternative.

### Seite 01b decision (4) Ho/Hu — the reference travels with the number

The K4 mass fallback pairs energy and emission factor only when both declare the same reference,
`Ho` or `Hu`. There is no implicit conversion and no default. A mismatch is a hard
`EnergyReferenceMismatchError`. Where the supplier states the CO₂ mass, no factor is read and the
reference is irrelevant.

| Fuel | kg CO₂/kWh | Reference | Register status |
| --- | ---: | --- | --- |
| Natural gas K4 | 0.201 | Hu | `geprüft`, convention, register review 07/2026 |
| Natural gas K4 | 0.181 | Ho | `geprüft`, convention, conversion metadata 0.903 |
| Heating oil EL K4 | 0.266 | Hu | `geprüft`, convention |
| LPG K4 | 0.236 | Hu | `geprüft`, convention |

No Ho factor exists in the register for oil or LPG; none is invented. The public resolved-rule
provenance contains the common EBeV citation and rule effective date, not internal register-review or
gas-only conversion metadata.

### What did not move

| Rule | Current value |
| --- | --- |
| CO₂ step bounds | 12 / 17 / 22 / 27 / 32 / 37 / 42 / 47 / 52, left-closed and right-open |
| CO₂ landlord shares | 0 / 10 / 20 / 30 / 40 / 50 / 60 / 70 / 80 / 95 percent |
| § 9 Abs. 2 volume equation | `Q = 2.5 × V × (tw − 10)`; at 60 °C, 125 kWh/m³ |
| § 9 Abs. 3 area fallback | `Q = 32 × A_Wohn` |
| §§ 7/8 consumption band | 50–70 percent consumption-based |
| K1 default | 30 percent base / 70 percent consumption; configurable base 30–50 percent |

Exactly `12.0` selects the second step and exactly `52.0` selects the open-ended top step.

### Where `total_co2_kg` and `co2_cost` come from

Both figures normally come from the supplier under § 3 Abs. 1 CO2KostAufG:

| Supplier figure | Engine input | Current behavior |
| --- | --- | --- |
| Brennstoffemissionen in kg CO₂ | `Co2Input.total_co2_kg` | Use unchanged. If missing, only the mass may fall back through K4 with matching Ho/Hu and visible provenance/risk still required. |
| CO₂ price component | `Co2Input.co2_cost` in cents | Use unchanged. If missing, refuse. Never derive cents from a certificate price. |
| Heating-value emission factor | `EmissionFactor` only on mass fallback | Carries its energy reference. |
| Energy content in kWh | `HeatingInput.total_energy_kwh` | Carries `energy_reference` only where the mass fallback needs it. |

Reference values such as the 2025 certificate price, VAT, or EBeV factors may check fixture
plausibility; they never calculate the supplier's CO₂ cost. The 2026 price has no single fixed value.
Whether a renter-facing pass-through itself attracts VAT is outside this engine and remains
unverified.

| Plausibility reference | Value | Use |
| --- | --- | --- |
| 2025 BEHG certificate | 55.00 EUR/t CO₂ | Fixture plausibility only |
| 2025 amount including 19 percent VAT | 65.45 EUR/t CO₂ | Supplier-invoice plausibility only |
| 2026 | Auction corridor rather than one fixed price | Confirms why no price fallback is safe |
| Natural gas EBeV Hu conversion | 0.20088 kg/kWh; CSV stores 0.201 | Check source scale; CSV value controls K4 |
| Heating oil EL EBeV Hu conversion | 0.2664 kg/kWh; CSV stores 0.266 | Check source scale; CSV value controls K4 |
| LPG EBeV Hu conversion | 0.2358 kg/kWh; CSV stores 0.236 | Check source scale; CSV value controls K4 |

## 4. Normalized heating contract and H0–H8 pipeline

The live end-to-end input and result are defined in
[`inputs.py`](../packages/heating-engine/src/lokara_heating_engine/inputs.py). A2 device handling,
A3 plant/CO₂ assessment, and A4 self-billing calculations are **capability shipped** in separate pure
modules. They are green but not yet integrated into one Page 01b result.

### Input and result shapes

| Shape | Current fields and boundary |
| --- | --- |
| `HeatingInput` | Billing period, total cost, total energy, normalized units, occupancies, resolved rules, optional central WW, optional CO₂, and optional energy reference. **Shipped end-to-end core.** |
| `HeatingUnit` | Unit, `area_sqm_x100`, heat consumption plus unit, and optional WW volume. It cannot represent the full segmented device history by itself. |
| `HeatingRules` | Consumption share, statutory bounds, WW formula, K3 table, optional CO₂ table and Rechtsstand. |
| `HeatingResult` | Renter-only lines, required owner residual, optional CO₂ result, estimation/fallback flags, all four pots and vertical-split intermediates, applied share/bounds, WW separation, and measurement unit. It has no shared readiness/provenance/risk channel. |
| A2 device capability | `HeatingDevice`, `DeviceReadingSpan`, stable device lines, party/owner/unit totals, annual unsegmented totals, and estimated-device IDs. **Capability shipped.** |
| A3 plant capability | Explicit energy source, building type, connected state, proof-gated protection/exclusion, applicability switches, and plausibility warning. **Capability shipped.** |
| A4 self-billing capability | Cost aggregation, invoice overlap, oil stock/consumption, WW separation, four pots, and owner-burden preview. **Capability shipped.** |

The legal/conventional inputs K1–K14 remain individually visible:

| ID | Meaning | Status |
| --- | --- | --- |
| K1 | Base-cost share default 30 percent, configurable 30–50 | `verify-before-production` |
| K2 | Base-cost allocation by m²-days, including vacancy | `verify-before-production` |
| K3 | VDI degree-day table in tenth-promille | `verify-before-production` |
| K4 | Fuel emission-factor mass fallback with Ho/Hu | Register row status retained per fuel; fallback classification remains a convention |
| K5 | WW temperature default 60 °C | `verify-before-production` |
| K6 | CO₂ plausibility band 5–70 kg/m²/a, warning only | `verify-before-production` |
| K7 | Oil heating value and stock consumption method | `verify-before-production` |
| K8 | Invoice overlap allocated linearly by days | `verify-before-production` |
| K9 | Half-up residual rounding direction | `verify-before-production`; destination is fixed model rule |
| K10 | Device list on renter output | `verify-before-production` |
| K11 | Device units rounded half up to one decimal | `verify-before-production` |
| K12 | Versioned DWD annual climate factor | `verify-before-production`; exact annual import specified in approved `docs/16` |
| K13 | Average-user comparison source/method | `verify-before-production`; corrected heat-only D2/UVI contract specified in approved `docs/16` |
| K14 | MDL amounts are validated and passed through, never recalculated | `verify-before-production` |

### H0–H8

**H0 — select one path.** `MDL` runs H7 only; self-billing runs H1–H6. Both converge on one heating
amount per tenancy. They are never added and their source fixtures are not asserted against each
other. `calculate_page01b_statement(...)` now enforces this choice and returns one typed readiness,
value, finding, provenance, device-evidence, risk and annual-comparison result.

**H1 — aggregate plant costs.** Sum normalized fuel/district-heat and operating positions. H1a
allocates partial invoice overlap by inclusive days with half-up cents and a non-dismissible coverage
warning. H1b values oil as opening stock plus purchases minus closing stock, using weighted cost and
calculating energy/CO₂ mass only on consumption. It never invents CO₂ cents.

**H2 — CO₂ before distribution.** Supplier-stated cost is mandatory. The mass is supplier-stated or
uses the proof-carrying K4 mass fallback. Apply annualise → R8 one-decimal rounding → step lookup;
non-residential uses 50/50. Proof-gated protection halves the landlord percentage; proof-gated full
exclusion sets it to zero; heat pumps and biomass turn the module and disclosure off. Deduct the
statutory landlord amount before H3–H6.

**H3 — separate warm water for a connected plant.** Priority is measured WW energy, then the
volume equation, then the 32 kWh/m² fallback with warning. A non-connected plant stays one heating
block. The WW pot is half-up; heating is its exact complement.

**H4 — form four pots.** Apply the configured base share to heat and WW separately. Round the base
pot half up; consumption is the complement. A changed base ratio carries the exact owner-burden
preview before save.

**H5 — aggregate devices before money.** For every usage segment:
`round_half_up((closing − opening) × valuation_factor, 1 decimal)`. Reject a negative delta; never
take `abs()`. Sum rounded device values. Tenant change needs both outgoing and incoming readings;
otherwise the unsegmented period goes through K3. The pure capability is shipped; persistence and
integration into `HeatingInput`/H6 are shipped through migration `0006`, the normalized adapter and
the Page 01b orchestrator. K11 remains `verify-before-production` as recorded above.

**H6 — distribute four blocks.** Base blocks use m²-days including vacancy. Heat consumption uses
HKV units or heat-meter kWh, with K3 for an unread change segment. WW consumption uses unit m³ over
the measured central denominator; the unassigned difference remains with the owner. A zero
denominator is a blocking readiness error, never an automatic area fallback. The lawful § 9a branch
is distinct and must be explicitly selected.

**H7 — MDL.** Validate and pass through; never recompute MDL amounts. A confirmed net statement gets
no second CO₂ deduction. A gross statement runs H2 and rescales every position using the exact
quotient; a one-cent source residual is accepted and reconciled to the owner. The gross rescaling
capability is shipped. Net passthrough, branch-specific control sums and F29/F30 risk/readiness
output are now part of the shared orchestrator. Confirmed MDL OCR/API ingestion stays outside this
slice and remains Slice B work.

**H8 — annual comparison.** Heat is weather-adjusted; WW remains raw. Missing climate data produces
a labelled fallback, never an implicit factor of one. The annual import contract and resolved
range/date inputs are in approved `docs/16`. The pure annual comparison now accepts normalized
annual DWD factors, validates the approved range and returns either adjusted values, an explicitly
raw-labelled fallback or a no-prior notice. Monthly import, scheduling and UVI remain future work.

Compact arithmetic, with every quotient kept as exact `Decimal`:

| Step | Formula |
| --- | --- |
| H1 | `total = sum(invoice/cost positions)` after H1a overlap allocation |
| H1a | `allocated cents = round_half_up(invoice cents × overlap days / invoice days)` |
| H1b | `consumed litres = opening + purchases − closing`; weighted stock cost follows the available stock |
| H2 | `billable = total − round_half_up(supplier CO₂ cents × landlord percent / 100)` |
| H3 | measured energy, else `2.5 × volume × (tw − 10)`, else `32 × area`; `WW pot = round_half_up(billable × qWW / total energy)` |
| H4 | `base pot = round_half_up(block × base percent / 100)`; consumption pot is the exact complement |
| H5 | `device segment = round_half_up((closing − opening) × factor, 1 decimal)` |
| H6 | `renter = round_half_up(block × renter weight / full denominator)`; owner is the committed residual |
| H7 gross | `position = round_half_up(source position × billable / MDL total)` using the exact quotient for every position |

## 5. Rounding & reconciliation

| ID | Active rule |
| --- | --- |
| R1 | Money is integer cents; round half up once when assigning a share. |
| R2 | Quotients stay exact `Decimal`; recompute them and never reuse a rounded factor. |
| R3 | Energy is rounded half up to three decimal places where the formula requires it. |
| R4 | Emission mass is integer grams internally and displays in kg with one decimal; classification is governed by R8. |
| R5 | Owner residual per block is `block − sum(rounded renter shares)` and may have either sign. |
| R6 | Apply statutory percentages to cents with half-up rounding. |
| R7 | Device units round half up to one decimal per device; the unit total sums rounded devices. |
| R8 | Annualise specific CO₂ intensity, round half up to one decimal, classify that value, and print the same value. Tie mode is a Lokara convention. |

### API consequence for the allocation primitives

[`money.py`](../packages/domain/src/lokara_domain/money.py) deliberately exposes three distinct
operations: `distribute_cents` for NK largest remainder, `distribute_cents_half_up` for a named
two-pot complement, and `distribute_cents_owner_residual` for renter allocation plus a structurally
separate owner result. Callers must not emulate one operation by reshaping another.

### Owner residual and separate statutory CO₂ deduction

For each heating block:

```text
renter_i = round_half_up(block × renter_weight_i / full_denominator)
owner    = block − sum(renter_i)
```

The denominator includes applicable vacancy/self-use bases. The owner is not in the numerator list.
One `OwnerResidual` reconciles all four heating blocks, always exists, and keeps per-unit origins plus
`rounding_difference = total − sum(origins)`. The committed residual wins over a separately rounded
origin calculation.

The CO₂ landlord share is different: it is a statutory deduction made before the four block
allocations. It is rounded half up by its percentage and the renter side is the exact complement.
Never merge this deduction into the owner residual or deduct it twice.

### Units, scaling, and display

| Quantity | Engine representation | Display rule |
| --- | --- | --- |
| Money | integer cents | divide by 100 and print two decimals |
| Area | `area_sqm_x100` | divide by 100 |
| m²-days | `base_weight_sqm_days_x100` | divide by 100; never print the stored integer as m²-days |
| Degree days | tenth-promille, total 10,000 | divide by 10 for ‰ |
| Device units | `Decimal`, one decimal per device | preserve the measurement unit and one-decimal precision |
| CO₂ mass | integer grams internally / carried kg result | print kg with one decimal where required |
| CO₂ intensity | annualised one-decimal `Decimal` | fixed one decimal, including `12.0` |

Rendering must de-scale explicitly. Integer-based tests can stay green while a PDF shows values 100
times too large, so the rendered statement remains part of output verification.

## 6. Edge cases, refusals, and warnings

| # | Case | Required behavior | Fixture |
| --- | --- | --- | --- |
| E1 | Supplier omits CO₂ mass and/or cost | Mass only: matching K4 factor plus provenance/warning. Cost: hard refusal; never derive cents. | `01b-F02` |
| E2 | Specific intensity exactly 12.0 or 52.0 | Left-closed boundary selects the higher step. | `01b-F03`, `01b-F04` |
| E3 | Raw value rounds up to a boundary | Annualise, round to one decimal, classify and print that rounded value. | `01b-F05` |
| E4 | Billing period is not 365/366 days | Annualise by `365 / nTage`, then R8, then classify. | `01b-F06` |
| E5 | Non-residential building | Flat 50/50; mixed building uses the step model. | `01b-F07` |
| E6 | Monument/milieu protection or full exclusion | Halve only with stored protection proof; set zero only with stored exclusion proof. | `01b-F08`, `01b-F09` |
| E7 | Heat pump or biomass | CO₂ module, Pflichtausweis, and step indicator all off. | `01b-F10` |
| E8 | WW not measurable | Use area fallback and emit the required warning. | `01b-F12` |
| E9 | Plant not connected | No WW split; one heat block. | `01b-F13` |
| E10 | Base share changed to 50 percent | Valid setting; show exact owner-burden change before save (`32.85 EUR → 54.78 EUR` in F14). | `01b-F14` |
| E11 | Tenant change with interim readings | Separate measured segments for both tenancies. | `01b-F01`, `01b-F27` |
| E12 | Tenant change without complete interim readings | Use K3 for heat consumption and days for base/WW; owner receives the vacancy segment. | `01b-F16` |
| E13 | One device failure affecting at most 25 percent of area | § 9a Abs. 1 estimate; retain amount and visible provenance. | `01b-F17` |
| E14 | Failure affects more than 25 percent of area | § 9a Abs. 2 makes the complete consumption distribution area-based; no § 12 deduction. | `01b-F18` |
| E15 | Oil purchase differs from oil consumption | Use stock logic; energy and CO₂ mass follow consumed quantity. | `01b-F19` |
| E16 | District heat | Carry supplier disclosures; step model still applies when applicable. | `01b-F20` |
| E17 | Consumption denominator is zero | Blocking readiness error; never silently switch to area. | `01b-F21` |
| E18 | Reading delta is negative | Reject; represent replacement devices as separate valid segments. Never `abs()`. | `01b-F22` |
| E19 | CO₂ intensity outside K6 band 5–70 | Non-blocking warning with the same R8 value; an efficient building remains billable. | `01b-F23` |
| E20 | Invoice only partly overlaps billing period | Day-linear allocation plus non-dismissible coverage warning. | `01b-F24` |
| E21 | Missing remote-readability/UVI/CO₂ disclosure duties | Show each 15/3/3 percent risk separately; never auto-deduct or sum uncertain rights. | `01b-F25` |
| E22 | Sum of unit WW meters differs from central volume | Use central volume as denominator; owner keeps the gap. At most 10 percent silent, over 10 notice, over 20 legal-risk warning. | `01b-F26`, `01b-F26b`, `01b-F26c` |
| E23 | Vacancy within the period | Keep applicable basis in the denominator and send the resulting residual to the owner. | `01b-F01` |
| E24 | Period over 12 months | Validation error inherited from Page 01. | — |
| E25 | Several devices with different valuation factors | Aggregate rounded device segments; retain and print the device evidence. | `01b-F27` |
| E26 | MDL statement already contains CO₂ split | Net path; no second deduction. | `01b-F28a` |
| E27 | MDL statement lacks CO₂ split | Gross path; H2 plus exact proportional rescaling; accepted one-cent source residual to owner. | `01b-F28b` |
| E28 | OCR decimal shift | Branch-specific control sum blocks the run. | `01b-F29` |
| E29 | MDL statement has no CO₂ evidence | Show separate § 7 Abs. 4 risks before dispatch; no automatic deduction. | `01b-F30` |
| E30 | § 6a Abs. 3 block incomplete | Show the separate 3 percent risk. | `01b-F31` |
| E31 | No preceding comparison period | Print a labelled note, not an empty graph or invented factor. | `01b-F31` |

Warnings never substitute for hard refusals. Proof-gated branches, missing supplier CO₂ cost,
periods over 12 months, negative readings, zero denominators, and MDL control-sum failure block.
Plausibility, coverage, lawful estimation provenance, threshold notices, and missing comparison data
remain visible non-blocking outputs with their required dismissibility.

## 7. Conflicts and unresolved dependencies

No item silently selects a missing legal value. Resolved items stay here because existing tests and
documents reference their numbers.

1. **Resolved natural-gas factor.** CSV `0.201 Hu / 0.181 Ho`, metadata `0.903`, status `geprüft`,
   register review `07/2026` replaces the stale `0.2016 / 0.1820` answer.
2. **Separately rounded Hu/Ho values.** `0.201 × 0.903 = 0.181503`, while the direct CSV Ho value is
   `0.181`. Both remain source metadata; the engine selects rather than derives.
3. **Conversion metadata is not coercion.** Retain `0.903` as provenance, but never apply it silently
   or twice in the engine.
4. **No Ho factor for oil or LPG.** None exists in the register; an Ho quantity for either fuel is
   refused rather than converted.
5. **CO₂ cost fallback is refused.** Only supplier-stated cost is accepted. K4 remains a mass-only
   fallback and never derives cents from a price.
6. **F19 counter-example typo.** CO₂ on purchased oil would produce 90,121 ct, not 90,204 ct. The
   current asserted mass/cost path uses consumed oil; the wrong-path figure is not an oracle.
7. **F16/F26 display inconsistency.** A separately rounded origin can differ by one cent from the
   committed residual. The residual-derived amount controls because it reconciles the block.
8. **Annualisation convention.** H2 uses flat 365 and skips annualisation for every 365- or 366-day
   period, including a non-calendar 366-day period. This remains transcribed, not independently
   settled.
9. **Pre-legal § 6a notice identity.** The BAnz notice supports the DWD direction, but whether it is
   the notice intended by GEG § 82 for § 6a remains for legal review.
10. **CO₂ price from 2026.** There is no single fixed price. This does not affect supplier-stated
    cost and may not revive the cost fallback.
11. **MDL and self-billing fixture separation.** `08-F01` and `01b-F01` are different data paths and
    must not be asserted against each other, even where confirmed net positions converge.
12. **Where block (c) is disclosed.** Define `(c) = printed residual − sum(separately rounded origin
    amounts)`. With exactly one empty unit it may be zero even when a counterfactual separate
    calculation differs by five cents. This definition is current; a clarifying source sentence
    would close the prose/rendering mismatch. Existing references intentionally retain item 12.
13. **Fixture-ID drift.** Arithmetic cited as `08-F21 / 08-F22 / 08-F06` in correspondence now maps
    to Page 02 `09-F19 / 09-F07 / 09-F08+09-F19`. Preserve both identifiers where that arithmetic is
    used; do not re-derive it.
14. **Unresolved reduction cumulation.** Page F25 forbids summing the three 3 percent rights and the
    15 percent right; one CSV entry says the 3 percent rights cumulate. Show each separately.
15. **K12/DWD dependency.** Approved `docs/16` resolves the annual importer boundary to
    `0.40–1.80` and the latest-state note to the May-ending file. H8 now consumes normalized annual
    factors; the monthly importer/scheduler remains future work and the § 6a notice identity remains
    pre-legal.
16. **K13/D2 dependency.** Approved `docs/16` specifies the corrected heat-only
    comparison, guards and source. Annual statement comparison and UVI are related consumers, not
    one calculation; annual DWD factors are not monthly degree-day inputs.
17. **Resolved F18 oracle.** Only WE-03 is affected, `58 / 194 = 29.90 percent`; Berkay's printed
    totals control and no general per-block override is inferred.
18. **Scope exclusion.** No MDL raw-input recalculation, automatic legal reduction, proprietary
    average-user dataset, renovation ROI, floor-heating reimbursement, or device installation audit
    is introduced by this engine contract.

## 8. Shipped capabilities and end-to-end gaps

| Area | Exact repository status | Closure owner |
| --- | --- | --- |
| Core heating allocation, K3, H2/R8, Ho/Hu refusal, owner residual, disclosure intermediates | **Shipped** and green for their current interfaces | Preserve through Slice A |
| A2 device and segmented-reading aggregation | **Integrated**; migration `0006`, adapter and orchestrator cover F01/F15/F16/F17/F22/F27 | Preserve through later meter work |
| A3 plant/CO₂ assessment | **Integrated**; F07–F10 and F23 reach the shared result | Preserve through Slice B ingestion |
| A4 self-billing aggregation | **Integrated**; F11–F14, F19, F20 and F24 reach H5/H6 and output | Preserve through later application work |
| Exact F18 area fallback | **Shipped** executable oracle | Preserve through integrated pipeline |
| F28b gross MDL rescaling | **Integrated** with exact quotient and owner reconciliation | Slice B later supplies confirmed MDL input |
| H5 persistence and integration | **Shipped**: exact device factor, segment metadata, adapter and `HeatingInput` handoff | K11 remains `verify-before-production` |
| H7 net/control/risk behavior | **Shipped in the pure orchestrator**: net/gross branches, control sum, F29 block and F30 risks | Confirmed OCR/API input remains Slice B |
| Shared readiness/provenance/risk channel | **Shipped** for F02, F12, F17, F20, F21, F23–F26c, F30/F31 | Final wording/cumulation choices remain provisional |
| H8 annual comparison | **Shipped for normalized annual factors and raw/no-prior fallbacks** | Monthly import, scheduling and UVI remain future work |

Slice A supplies one H0–H7 pipeline, the shared readiness channel, normalized-factor H8, all 34
fixture obligations executable end to end and statement projection. This is technical closure, not
production approval: every `verify-before-production` register flag, both open Page 01b choices,
confirmed MDL ingestion and the future monthly DWD/UVI work remain explicit.

## 9. Wiring R1/R5/K9 and Ho/Hu into the engine — current split-site map

The active implementation links below replace old line-number and commit diaries. Pot complements,
party allocations, statutory CO₂ deduction, and owner residual are different operations and must
keep different shapes.

### 9.1 Which of the ten split sites switch

| # | Live operation | Active primitive/model | Residual destination |
| ---: | --- | --- | --- |
| 1 | Heating pot → base/consumption | half-up base plus exact complement | consumption pot |
| 2 | Heating base → renters by m²-days | renter half-up + `OwnerResidual` | Liegenschafts-Residuum |
| 3 | Heating consumption § 9a area fallback → renters | renter half-up + `OwnerResidual` | Liegenschafts-Residuum |
| 4 | Heating consumption → renters by units/kWh | renter half-up + `OwnerResidual` | Liegenschafts-Residuum |
| 5 | WW pot → base/consumption | half-up base plus exact complement | consumption pot |
| 6 | WW base → renters by m²-days | renter half-up + `OwnerResidual` | Liegenschafts-Residuum |
| 7 | WW consumption § 9a area fallback → renters | renter half-up + `OwnerResidual` | Liegenschafts-Residuum |
| 8 | WW consumption → renters by m³ | renter half-up + `OwnerResidual` | Liegenschafts-Residuum |
| 9 | Billable cost → WW/heating | half-up WW plus exact complement | heating pot |
| 10 | CO₂ cost → statutory landlord/renter sides | half-up landlord deduction plus exact complement | renter statutory side; no owner residual |

Sites 1, 5, 9, and 10 are two-way complements. Sites 2, 3, 4, 6, 7, and 8 allocate to renters and
therefore use the owner-residual model. NK now uses the corresponding owner-residual path.

### 9.2 The owner bucket is one Liegenschafts-Residuum — and it always exists

One line per property and cost type replaces two rejected conventions:

1. **Convention 1, rejected:** choose one of several owner parties to absorb the rest.
2. **Convention 2, rejected:** use largest remainder when a fully let property has no owner party.

Neither convention is valid because the residual is not a party and exists in both cases.

For heating, the same line carries all four blocks. It may be zero or negative. Its `origins` retain
vacancy/self-use evidence for the landlord-only annex; `rounding_difference` belongs to no unit. It
has no percentage field. Renter-facing projections must not expose the owner row.

#### What actually moves in the engine

All six renter-allocation sites use the same required residual shape. The four complement/statutory
sites keep their named complement. Every consumer of `HeatingResult.lines` must therefore treat it
as renter-only and add `owner_residual` exactly once; the consumer fan-out below is the current map.

### 9.3 Why the CO₂ statutory split gets its own answer

The H2 landlord amount is a statutory deduction, not a weighted party allocation. Round the named
landlord percentage half up and use the renter amount as the exact complement. At an exact half cent
the deduction rounds in the renter-favorable direction. The later pro-rata distribution of the
renter CO₂ amount may create an owner residual, but it is a separate Page 01 step and must not be
collapsed into H2.

### 9.4 Complement sites do not create an owner line

A two-element split with complementary weights produces a named rounded side and an exact other pot.
It moves no amount into `OwnerResidual`. This applies to sites 1, 5, 9, and 10. Their equivalence to
the former two-element allocation is a property of complements, not permission to model the owner as
a party.

### 9.5 The Ho/Hu boundary — what the engine must accept and what it must refuse

| Situation | Behavior |
| --- | --- |
| Supplier mass stated, no factor | Accept; reference is not read. |
| Supplier mass stated and fallback factor supplied | Refuse; K4 is fallback-only and the unused factor may not survive silently. |
| Mass absent, no factor | Refuse; no mass may be guessed. |
| Mass absent, factor present, reference absent | Refuse; never default Ho/Hu. |
| Mass absent and references differ | Propagate `EnergyReferenceMismatchError` unchanged. No conversion or warning-and-continue. |
| Mass absent and references match | Derive integer grams from energy and matching factor; H2 annualises and R8 classifies. |
| Supplier CO₂ cost absent | Refuse independently of the mass path. Never derive cents. |

At 20,000 kWh and 100 m², the register's natural-gas factors demonstrate why: `0.201 Hu` gives
4,020 kg and 40.2 kg/m²/a (60 percent landlord), while `0.181 Ho` gives 3,620 kg and 36.2 kg/m²/a
(50 percent). Both are plausible; only the invoice reference decides which is valid.

### Consumer fan-out

| Consumer | Current responsibility |
| --- | --- |
| [`packages/domain/src/lokara_domain/money.py`](../packages/domain/src/lokara_domain/money.py) | Largest-remainder, complement-half-up, and owner-residual primitives. |
| [`packages/heating-engine/src/lokara_heating_engine/engine.py`](../packages/heating-engine/src/lokara_heating_engine/engine.py) | Sites 1–9, renter-only lines, one required `OwnerResidual`, and reconciliation. |
| [`packages/heating-engine/src/lokara_heating_engine/co2.py`](../packages/heating-engine/src/lokara_heating_engine/co2.py) | H2/R8, period refusal, statutory site 10, and Ho/Hu mass fallback boundary. |
| [`packages/heating-engine/src/lokara_heating_engine/device_readings.py`](../packages/heating-engine/src/lokara_heating_engine/device_readings.py) | A2 H5/R7 device and segment capability. |
| [`packages/heating-engine/src/lokara_heating_engine/plant_co2.py`](../packages/heating-engine/src/lokara_heating_engine/plant_co2.py) | A3 applicability, proof, protection/exclusion, and warning capability. |
| [`packages/heating-engine/src/lokara_heating_engine/self_billing.py`](../packages/heating-engine/src/lokara_heating_engine/self_billing.py) | A4 H1–H4 pure self-billing capabilities. |
| [`packages/heating-engine/src/lokara_heating_engine/mdl.py`](../packages/heating-engine/src/lokara_heating_engine/mdl.py) | F28b gross rescaling capability. |
| [`packages/heating-engine/src/lokara_heating_engine/page01b.py`](../packages/heating-engine/src/lokara_heating_engine/page01b.py) | H0–H8 orchestration, typed readiness, findings, provenance, risks and annual comparison. |
| [`packages/adapters/src/lokara_adapters/meter.py`](../packages/adapters/src/lokara_adapters/meter.py) and migration `0006` | Corrections, device changes, tenancy segments, estimates, factors and provenance. |
| [`packages/pdf/src/lokara_pdf/statement.py`](../packages/pdf/src/lokara_pdf/statement.py) and [`heating_disclosure.py`](../packages/pdf/src/lokara_pdf/heating_disclosure.py) | De-scaling, one owner row, disclosure intermediates, Rechtsstand, and landlord-facing projection. |
| [`apps/api/src/lokara_api/routers/portal.py`](../apps/api/src/lokara_api/routers/portal.py) and [`apps/web/src/features/portal/statement.tsx`](../apps/web/src/features/portal/statement.tsx) | Shared-result API shape and German landlord-facing projection; risks stay separate. |

Every consumer that iterates `HeatingResult.lines` must remember that the tuple contains renters
only. Reconciliation is `sum(lines.total) + owner_residual.total == result.total`.

## Appendix A — complete Page 01b source-section coverage

| Page 01b source section | Canonical destination | Golden evidence |
| --- | --- | --- |
| § 1 purpose and MDL/self-billing interface | §§ 1, 4 H0/H7, 8 | `berkay_01b_golden.py`; F01, F28a/b |
| § 2 legal basis and K1–K14 | §§ 3–7 and Appendix C | Rule-store tests plus Appendix B |
| § 3.1 plant inputs | § 4 input table and H2/H3 | F07–F10, F13–F14, F20 |
| § 3.2 invoices and operating costs | § 4 H1/H2 | F02, F19, F20, F24 |
| § 3.3 meters and readings | § 4 H3/H5/H6 | F11–F18, F21–F22, F26–F27 |
| § 3.4 rule tables | §§ 3–5 and 9.5 | F02–F06, F16, F19, F23, F31 |
| § 3.5 MDL input | § 4 H0/H7 and § 9 | F28a/b, F29–F30 |
| § 4 R1–R7 and H0–H8 | §§ 4–5 and 9 | F01–F31, including suffix variants |
| § 5 E1–E31 | § 6 | Appendix B |
| § 6 worked examples | Appendix B | Data oracle and focused executable tests |
| § 7 owned/deferred/out of scope | §§ 7–8 | Documentation scope assertions |

The source trace is complete. That does not make all values production-safe or all fixtures
executable end to end.

## Appendix B — all 34 Page 01b fixture IDs and current status

Every ID has a data oracle in
[`berkay_01b_golden.py`](../packages/heating-engine/tests/berkay_01b_golden.py). The coverage test
checks the exact 34-ID set, readiness shape and allocation reconciliation. Every row below now
reaches one durable orchestrator result; the status text also retains the narrower capability or
production limitation that matters after technical closure.

| Fixture | Required result | Current executable status |
| --- | --- | --- |
| `01b-F01` | Full self-billing; four renter totals plus owner reconcile to 338,218 ct | Orchestrator E2E green; A2/device and allocation primitives remain lower-level evidence |
| `01b-F02` | Missing mass uses matching K4 factor; missing supplier cost refuses | Orchestrator E2E green with provenance and separate § 7 Abs. 4 risk; K4 flag retained |
| `01b-F03` | Exact 12.0 boundary selects 10 percent | Exact executable green |
| `01b-F04` | Exact 52.0 boundary selects 95 percent | Exact executable green |
| `01b-F05` | Annualise, R8 to 12.0, classify at 10 percent; deduction 1,280 ct, renter CO₂ 11,523 ct, billable 349,320 ct | Exact executable green |
| `01b-F06` | 275-day annualisation before R8 gives 28.7 | Exact executable green |
| `01b-F07` | Non-residential 50/50 | Orchestrator E2E and A3 capability green |
| `01b-F08` | Protected building halves landlord percentage only with proof | Orchestrator E2E and proof-gated A3 capability green |
| `01b-F09` | Proven full exclusion, disclosure retained | Orchestrator E2E and proof-gated A3 capability green |
| `01b-F10` | Heat pump/biomass turns CO₂ module and disclosure off | Orchestrator E2E and A3 capability green |
| `01b-F11` | Measured WW energy priority, 9,100 kWh | Orchestrator E2E through H1–H6 and dedicated PDF disclosure branch |
| `01b-F12` | 32 kWh/m² fallback plus warning | Orchestrator E2E with shared warning output; K5 flag retained |
| `01b-F13` | Non-connected plant, one heat block | Orchestrator E2E through integrated distribution |
| `01b-F14` | 50/50 choice and owner-impact preview | Orchestrator E2E with owner-impact output |
| `01b-F15` | Heat-meter kWh weights retain unit | Orchestrator E2E; A2 unit-preservation capability retained |
| `01b-F16` | Missing interim reading uses K3 and owner vacancy segment | Orchestrator E2E; exact K3 and A2 regressions retained |
| `01b-F17` | At most 25 percent estimated with visible provenance | Orchestrator E2E with device evidence and provenance |
| `01b-F18` | WE-03-only failure; all consumption blocks dissolve to area | Exact executable green with Berkay's printed cents |
| `01b-F19` | Oil stock/weighted cost; CO₂ on consumption; no cost fallback | Orchestrator E2E with provenance; K7 flag retained |
| `01b-F20` | District-heat pass-through, step model and § 6a fields | Orchestrator E2E with supplier provenance |
| `01b-F21` | Zero denominator hard stop | Orchestrator E2E as explicit `BLOCKED` readiness |
| `01b-F22` | Negative delta rejected; replacement segments summed | Orchestrator E2E; structural negative input still raises |
| `01b-F23` | K6 plausibility warning carries R8 values 74.7 / 4.1 | Orchestrator E2E on shared warning channel; K6 flag retained |
| `01b-F24` | Day-linear overlap plus non-dismissible coverage warning | Orchestrator E2E with non-dismissible finding; K8 flag retained |
| `01b-F25` | Four risks separate; never auto-deducted or summed | Orchestrator, API, web and PDF keep every risk separate; cumulation unresolved |
| `01b-F26` | 5.13 percent WW gap silent; 4,227 ct remains with owner | Orchestrator E2E with central-meter owner residual |
| `01b-F26b` | 11.54 percent WW gap produces non-blocking notice | Orchestrator E2E on shared notice channel |
| `01b-F26c` | 21.79 percent WW gap produces legal-risk warning | Orchestrator E2E on shared warning channel |
| `01b-F27` | Device rounding/aggregation and two change readings | Orchestrator E2E plus migration/adapter integration; K10/K11 flags retained |
| `01b-F28a` | MDL net branch; no second CO₂ deduction | Orchestrator E2E; confirmed MDL ingest remains Slice B |
| `01b-F28b` | MDL gross exact rescale, accepted one cent, owner residual | Orchestrator E2E and exact gross-rescaling capability green |
| `01b-F29` | OCR decimal shift blocks against net-branch control sum | Orchestrator E2E as explicit `BLOCKED`; OCR connection remains Slice B |
| `01b-F30` | No CO₂ evidence: separate 3 percent risks, no deduction | Orchestrator E2E; risks remain separate and unapplied |
| `01b-F31` | Heat-adjusted/WW-raw graph with labelled missing-data fallback | Orchestrator and web/PDF output green for normalized annual factors and raw/no-prior fallbacks |

## Appendix C — all 47 Page 01b register rows and flags

The authoritative CSV has 20 `geprüft` rows and 27 `verify-before-production` rows affecting Page
01b. Each row retains its own value, source, legal nature, Rechtsstand, and flag in the CSV; grouping
here does not merge them.

| Status | Exact CSV rows |
| --- | --- |
| `geprüft` | BEHG CO₂-Preis 2025 · Emissionsfaktor Erdgas (K4) · UVI-Turnus · Emissionsfaktor Flüssiggas (K4) · Warmwasser-Pauschale ohne Messung · CO₂-Aufteilung Nichtwohngebäude · CO₂-Stufenmodell Wohngebäude · Denkmal-/Milieuschutz — vollständiger Ausschluss · CO₂-Pflichtangaben in der Abrechnung · Kürzungsrecht — nicht verbrauchsabhängig abgerechnet · Emissionsfaktor Heizöl (K4) · § 9a-Schwelle für Schätzungen · § 6a Abs. 3 — Pflichtinformationen zur Abrechnung · Nachrüstfrist fernablesbare Ausstattung · Denkmal-/Milieuschutz — Halbierung · Leerstand bleibt im Gesamtverteiler · Warmwasser-Ersatzgleichung · CO₂-Kürzungsrecht · Belegeinsicht und Beweislast der Erfassung · Verbrauchsabhängiger Anteil — gesetzliche Bandbreite |
| `verify-before-production` | Plausibilitätsband CO₂ (K6) · Abweichungsschwelle Warmwasserzähler · Vermutungswirkung Witterungsbereinigung · Gradtagszahltabelle VDI (K3) · Geräteeinheiten — Rundung (K11) · Kürzungsrecht — fehlende fernablesbare Ausstattung · Warmwassertemperatur tw (K5) · Durchschnittsnutzer-Vergleichswerte (K13) · Rundungsweg (Seite 01 / docs/03 § 6) · BEHG CO₂-Preis 2026 · Geräteliste auf der Mieterausfertigung (K10) · Heizwert Heizöl (K7) · Rechnungsabgrenzung (K8) · Klimafaktoren DWD (K12) · Verteilungsrest (K9) · Grundkostenanteil (K1) · Kürzungsrecht — fehlende oder unvollständige § 6a-Information (UVI + Abrechnungs-Infoblock) · Verbrauchsvergleich — Umfang und Bereinigung · Grundkosten-Verteilung nach m²-Tagen (K2) · MDL-Beträge werden nie nachgerechnet (K14) · Schätzung bei Geräteausfall · CO₂-Ausweispflicht des Brennstofflieferanten · Umlagefähige Betriebskosten der Heizanlage · Informationspflichten bei nicht verbrauchsbasierter Abrechnung · Nutzerwechsel im Abrechnungszeitraum · Kürzungsrecht — CO₂-Anteil nicht ausgewiesen · CO₂-Mieteranteil — Pro-rata-Ableitung (D7 Schritt 6) |

## Appendix D — correspondence-retirement disposition ledger

This is the single historical ledger for all seven files retired in D3. Git preserves their former
contents; current authority comes from the original Pages and annexes, the Rechtsstand register and
approved `docs/00`–`docs/16`. Every former section has one durable destination below. Exact retired
filenames appear nowhere else in the live repository except the retirement checker denylist.

| Source section | Canonical destination | Disposition |
| --- | --- | --- |
| `FEEDBACK-to-Berkay-01b.md` summary and §§ 1–4 | §§ 3, 5, 7 and Appendices B/C | F19 correction, F16/F26 residual reading and K3 remain current; the older factor disagreement is superseded by CSV `0.201 Hu / 0.181 Ho` |
| `FEEDBACK-to-Berkay-01b.md` § 5 | `CLAUDE.md` § 4 and this ledger | Historical transcription rationale; the old promise to keep the correspondence folder immutable is superseded by D3 |
| `FEEDBACK-to-Berkay-01b.md` § 6 | Appendix B and committed fixtures | Historical demo delta; current K3 rule and exact arithmetic remain in approved fixtures |
| `FEEDBACK-to-Berkay-01b.md` § 7 | `docs/09` §§ 4 and 9 | Current boundary: no inferred allocation key before the approved catalogue is implemented |
| `FEEDBACK-to-Berkay-01b.md` § 8 item 1 | § 7 items 5/10 and § 9.5 | Superseded by the current supplier-cost refusal; no price-derived cost fallback exists |
| `FEEDBACK-to-Berkay-01b.md` § 8 item 2 | § 7 item 9; `docs/16` §§ 2 and 16 | Notice evidence is preserved; legal identity remains in its owning legal-review ledger |
| `FEEDBACK-to-Berkay-01b.md` § 8 item 3 | `docs/16` § 9 | Annual DWD importer source, corrections and fixtures are transcribed |
| `FEEDBACK-to-Berkay-01b.md` § 8 item 4 | `docs/16` §§ 8 and 16 | K13/D2 source and remaining authority gaps are transcribed |
| `FEEDBACK-to-Berkay-01b.md` § 9 | `docs/02` § 5; § 9.2; `docs/08` § 5 “Die Eigentümerzeile” | Superseded question: one unconditional Liegenschafts-Residuum always exists |
| `FRAGEN-an-Berkay-02.md` § 1 | `docs/02` § 5; § 9.2; `docs/08` § 5 “Die Eigentümerzeile” | Superseded by the fixed unconditional owner-residual model |
| `FRAGEN-an-Berkay-02.md` §§ 2–4 | `docs/16` §§ 1, 8 and 16 | Superseded by heat-only comparison, labelled over-500 fallback and approved source handling |
| `FRAGEN-an-Berkay-02.md` § 5 | `CLAUDE.md` § 4 and Appendix C | Historical export-naming request; one canonical CSV and current `geprüft` semantics govern |
| `FRAGEN-an-Berkay-02.md` “Was bei uns …” | §§ 3, 7 and 9.2; `docs/16` | Historical implementation checklist; durable rules are routed to their approved owners |
| `FRAGEN-an-Berkay-03.md` § 1 | § 9.2 and Appendix C | Fixed residual destination is current; half-up direction remains flagged |
| `FRAGEN-an-Berkay-03.md` § 2 | `docs/08` `08-F21`; `docs/09` `09-F19` | Superseded question; Page 01 block (b) is 100,800 ct |
| `FRAGEN-an-Berkay-03.md` § 3 | `docs/16` §§ 8 and 16 | Superseded question; D2 compares heat with heat |
| `FRAGEN-an-Berkay-03.md` § 4 | § 7 item 1 and Appendix C | Settled history: CSV values/flags control; the conflicting pair is superseded |
| `FRAGEN-an-Berkay-03.md` § 5 | §§ 3, 7 item 5 and 9.5 | Missing supplier CO₂ cost refuses; mass-only fallback survives |
| `FRAGEN-an-Berkay-03.md` § 6 | § 3 decision 3 and § 5 R8 | Annualise, round one decimal, classify and print the same value |
| `FRAGEN-an-Berkay-03.md` “Was bei uns läuft” | § 9.2; `docs/08`; `docs/16` | Historical implementation checklist; settled rules and open implementation status remain with their owning docs |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_01b-Uebergabe.md` §§ 0–3 | §§ 3, 7 and 9.5; Appendices B/C | F19 correction and F16/F26 confirmation are current; task narration is historical |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_01b-Uebergabe.md` § 4a | § 3 decision 4 and Appendix C | Register values `0.201 Hu / 0.181 Ho` and reference selection control |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_01b-Uebergabe.md` § 4b | Appendix C; `docs/10` § 2; `docs/13` § 2 | Current CSV controls heating, AfA and § 556d flags; checked means primary text read, not lawyer approval |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_01b-Uebergabe.md` §§ 5–6 | `docs/16` §§ 2, 5–7, 9 and 16 | DWD importer correction and notice evidence transcribed; legal notice identity remains in its owning legal-review ledger |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_01b-Uebergabe.md` §§ 7–8 | §§ 7 and 9.5; `docs/16` §§ 8 and 16 | Supplier-cost rule and K13/D2 history transcribed; remaining source choices are current questions |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_01b-Uebergabe.md` §§ 9–11 | approved owning docs and this ledger | Old implementation tasks/package inventory are historical; no independent calculation authority remains |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md` §§ 1–1.4 | `docs/02` § 5; § 9.2; `docs/08` § 5 “Die Eigentümerzeile” | One structural residual, always printed, no quote, with per-unit origin retained |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md` §§ 2–2.4 | `docs/16` §§ 8.2, 12 and 16 | Heat-only deduction, heat-pump convention, guard and golden arithmetic transcribed |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md` § 3 | `docs/16` §§ 8.2 and 16 | Missing over-500 values use the labelled 250–500 fallback; no extrapolation |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md` § 4 | `docs/16` §§ 8.2 and 11 | Source label/licence decision transcribed; no independent permission claim is promoted |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md` § 5 and `geprüft` section | `CLAUDE.md` § 4 and Appendix C | One canonical register; checked means primary text read, not lawyer approval |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md` § 6 | §§ 7–8; `docs/16` §§ 8 and 12 | Arithmetic evidence split by owning rule; it does not clear flags |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md` checklist | approved owning docs | Historical build checklist; no independent authority remains |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_03.md` process section | `CLAUDE.md`, `AGENTS.md` | Historical process advice superseded by current repository governance |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_03.md` §§ 1–3 | § 9.2; `docs/08` `08-F21`; `docs/16` §§ 8 and 16 | Residual, block-(b) and heat-only D2 corrections are current in approved docs |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_03.md` § 4 | § 7 item 1 and Appendix C | Superseded by the authoritative CSV values and flags |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_03.md` §§ 5–6 | §§ 3, 5, 7 and 9.5 | Cost fallback refuses; annualise then round/classify/print is current |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_03.md` summary | approved owning docs | Historical build checklist; every settled rule above has a durable owner |
| `berkay-work/Spec-Seiten/Antworten/08_BankMatching_F03_Patch.md` context and E12 amendment | `docs/15` §§ 1, 4 and 8 | Current correction: potential duplicate requires Review; identical provider ID dedupes before scoring |
| `berkay-work/Spec-Seiten/Antworten/08_BankMatching_F03_Patch.md` `BANKMATCH-F03` | `docs/15` § 7 and `packages/rules-store/tests/berkay_15_golden.py` | Exact executable F03 inputs, outcomes and summation checks preserved |

## Appendix E — compact supersession ledger

| Superseded method/value | Current disposition and reason |
| --- | --- |
| Heating largest-remainder party allocation | Renter half-up plus unconditional owner residual; avoids silent cent transfer between renters. Slice C aligns NK with that residual model. |
| Unsourced K3 table `170 150 130 80 40 15 10 10 30 80 120 165` | VDI 2067 12/1983 Table 22 in tenth-promille, sum 10,000. |
| Short-period table-bound scaling and period-intensity display | H2 annualises intensity, R8 rounds it, and lookup uses unshortened statutory bounds. |
| Raw/unrounded F05 classification | `11.999… → 12.0 → step 2`; landlord deduction 1,280 ct. |
| Natural-gas `0.2016 / 0.1820` and older flag | CSV `0.201 Hu / 0.181 Ho`, metadata 0.903, `geprüft`. |
| Silent Ho/Hu conversion or default | Reference travels with quantity and factor; mismatch/absence refuses. |
| CO₂ cost derived from BEHG price | Refused; only supplier-stated cents are accepted. Mass fallback remains separate. |
| Owner as one or several weighted parties | One structural Liegenschafts-Residuum, always present and never weighted. |
| Fully-let heating falling back to largest remainder | Rejected; the zero/negative owner residual still exists. |
| F18 all-units-unread interpretation and derived replacement table | Only WE-03 affected, 58/194; Berkay's printed totals remain authoritative. |
| F19 illustrative wrong-path 90,204 ct | Typo; recomputed trap is 90,121 ct. It is not a current cost oracle because missing supplier cost refuses. |
| F16/F26 separately rounded display inconsistency | Reconciled residual-derived results control; committed owner residual wins. |

No implementation diary, branch state, historical gate count, or old line-number map is part of the
active specification. Git at `635acf9` retains that evidence.
