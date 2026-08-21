# Investment KPIs — planning calculations and deterministic bank view

**Status:** D2 transcription for review; not implemented

**Rechtsstand:** 07/2026

**Authoritative Page:**
`berkay-work/Spec-Seiten/07 · Investment-KPIs 3a95fd4207318157a94ec8b5474bedba.md`

**Fixtures:** exactly `14-F01`–`14-F14` in
`packages/rules-store/tests/berkay_14_golden.py`

**Implementation status:** specification and data-only oracle only. This slice adds no schema,
migration, API, engine, UI, PDF renderer, pricing or bank integration.

This document defines a future planning calculation for a **Prüfobjekt**: a property being
considered for purchase. It produces exactly seven KPIs and a deterministic Bank-PDF view. The
results are conventions and scenarios, not a valuation, credit decision, bank application,
investment recommendation, tax export or promise of a tax result.

## 1. Sources, precedence, identifiers and audit

The transcription uses the complete Page 07, all 18 Page-07 rows in the authoritative 180-row
`Rechtsstand-Register.csv`, the eight Page-07 entries in `Non-Goals V1`, the
`README-for-Emir.md` arithmetic audit and the exact seven-file correspondence ledger. The CSV
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

## 4. Future logical contracts — no schema approval

All money is integer cents. Rates and ratios are integer basis points. KPI ratios are integer
hundredths. `Decimal` with `ROUND_HALF_UP` is used exactly at specified division or multiplication
boundaries; no float crosses the contract.

### 4.1 Prüfobjekt input snapshot

A future immutable snapshot groups object/purchase data, monthly cold rent and vacancy assumption,
four user-entered operating amounts, financing assumptions, tax/AfA provenance, optional Bank-PDF
header data and rule/layout versions. It records `finanzierungQuelle` as `annahme`, `indikativ` or
`angebot`. Missing data stays missing; it is never replaced by zero.

### 4.2 Financing and AfA provenance

Each financing value records whether it is a pre-offer assumption, indication or offer. Each AfA
value records whether it came from Page-03 R13, a future wizard input or the acquisition-phase
default. A linked Page-03 record wins. The snapshot must retain both source and version.

### 4.3 Partial KPI result

Each of the seven KPI slots returns either a fixed-point value or `—`, required-input gaps,
before/after-tax label, assumption badges and source versions. Missing inputs produce “Daten
unvollständig”; no fabricated zero. No overall score or purchase decision is returned.

### 4.4 Twelve-month annuity schedule

The future schedule contains exactly twelve ordered rows with opening balance, rounded monthly
interest, repayment and closing balance, plus annual interest, repayment, debt service and closing
balance. Every row reconciles and the annual sums reconcile. Non-positive repayment hard-blocks.

### 4.5 Sensitivity axes

The interest axis reruns R3–R7 at five configured steps, default `−100/−50/0/+50/+100` basis points.
The repayment axis varies initial repayment at constant interest and must show liquidity and debt
reduction together. Interest is a stress axis; repayment is a financing-structure trade-off.

### 4.6 Deterministic Bank-PDF view

The future view is `f(frozen KPI snapshot, versioned layout) → bytes`. It performs no
recalculation. Blocks are ordered: header/disclosure, investment, financing/LTV, rent and planning
costs, seven KPIs, sensitivity, twelve-month schedule, assumptions/method including the `14-K01`
through `14-K13` definitions, and disclosure. Missing KPIs remain `—`. LTV is labelled “Auslauf zum
Kaufpreis, nicht zum Beleihungswert”. The view includes no renter names and is not a tax export,
archive, valuation, credit decision or bank application.

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
- the Page-03 R13 deductible-interest versus Page-07 R3 planning-interest choice;
- how often a linked Page-03 AfA record is available during acquisition;
- the editable marginal-tax default and all flat-tax scenario limits;
- the capital-markets permission claim;
- the target-return/default policy and every missing concept from the two absent source files; and
- real AfA availability and financing provenance at the time a Prüfobjekt is evaluated.

No new question file is created in D2. These gaps remain blocked before production.

## 12. Source coverage and correspondence ledger

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

The exact retirement ledger has seven paths. A repository search finds no Page-07 settlement in
any of them, so each maps to “no Page-07 content”; none is deleted or edited here:

1. `FEEDBACK-to-Berkay-01b.md`;
2. `FRAGEN-an-Berkay-02.md`;
3. `FRAGEN-an-Berkay-03.md`;
4. `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_01b-Uebergabe.md`;
5. `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md`;
6. `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_03.md`; and
7. `berkay-work/Spec-Seiten/Antworten/08_BankMatching_F03_Patch.md`.
