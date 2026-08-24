# 08 — Statement document contract

This is Lokara's canonical, living specification for the Page 01 statement and the document-side
projection of Page 01b. It separates the approved output contract from what the current landlord PDF
actually ships. Superseded arguments, closed defect narratives and slice chronology remain available
with `git show 7b08f2b:docs/08-statement-document.md`; they are not part of the active contract.

The authoritative Page 01 source is
`berkay-work/Spec-Seiten/01 · Die Abrechnung 3a95fd420731816c9048ed7a517c3e9e.md`, read with the
26 matching rows in `berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv` and the approved
method corrections here and in `docs/03`. Structured values and flags follow the CSV.

## Reading guide, ownership and status

Statuses describe repository delivery, not legal certainty. `geprüft` means the primary source was
checked, not lawyer approval. `verify-before-production` remains a production block even when the
related arithmetic or rendering capability is green.

| Status | Meaning |
| --- | --- |
| **Shipped** | Present on `main` in current source and covered by the repository gates. |
| **Capability shipped** | A bounded behavior is implemented, but the complete tenant-statement workflow is not closed. |
| **Specified** | Approved implementation contract; data-only oracles validate transcription, not production behavior. |
| **Future** | Ownership is known, but the final contract or implementation is not shipped. |

Ownership is split deliberately:

- this file owns document audiences, content, copy, disclosure carriers, pagination and the Page 01
  fixture/source trace;
- [`docs/02-data-model.md`](02-data-model.md) owns the durable statement, ledger and finalization
  model;
- [`docs/03-nk-heating-engines.md`](03-nk-heating-engines.md) owns calculation rules, Page 01b
  arithmetic and its current implementation gaps;
- [`docs/05-design-system.md`](05-design-system.md) owns accessibility thresholds; this file assigns
  statement carriers to those tiers;
- [`docs/07-compliance.md`](07-compliance.md) owns cross-cutting compliance and claim strength.

## 1. Delivery status at a glance

### Shipped landlord overview

The current PDF is the internal **Vermieter-Gesamtübersicht**, a live building-wide calculation and
QA view. It is not a tenant document and must not be sent to a renter.

The current render includes:

- operating-cost and heating money tables from engine results;
- one `Anteile je Partei` summary with one final `Eigentümeranteil` row;
- NK reference totals and heating Blocks A, B and C;
- the §§ 7/8 ratio, § 9 separation, § 9b change-of-user disclosure and § 9a branches;
- CO₂ split, classification basis and labelled `Rechtsstand` entries;
- tagged-PDF structure, German document language, title and searchable text required by the demo gate.

These are **Shipped** capabilities. They do not turn the landlord overview into a complete
Mieter-Einzelabrechnung.

### Shipped Page 01 application path

Slice B closed the application side of Page 01 — the persisted path from entered data to a projected
result. These are **Shipped**, and each is a capability, not the finished tenant document:

| Capability | What now exists |
| --- | --- |
| Real object and period selection | The statement route takes a `building_id` and a billing period instead of a demo preset. `period_to` is **inclusive** in the URL, as a human reads a billing period, and half-open internally; both dates or neither. |
| D0 person-day denominator | The fictional vacancy occupancy is derived per run from persisted `person_count` history and the building's Fiktivbelegung mode, and reaches the engine as a landlord-side weight. Layering, modes and the waiver are owned by `docs/02` § 5 "D0 Fiktivbelegung". |
| CONSUMPTION values reach the engine | A CONSUMPTION-keyed NK cost is allocated from persisted per-unit readings with its Maßeinheit, instead of being folded away unused. A unit without a usable value contributes no consumption row and the statement says so. |
| Server-side audience projection | `OWNER`, `TENANT(tenancy_id)` and `TAX` are selected from the one computed result **before** rendering (`StatementProjection`). A `TENANT` projection carries no owner residual and no building-wide findings; a `TAX` projection carries only owner-side rows. |
| German refusals for bad input | An invalid billing window (missing half, reversed dates, more than 12 months) and an overlapping occupancy both return `422` with a German sentence naming the defect and the landlord's next action. `404` stays for "no data" and for an unknown or zero-usage-day tenancy — a missing or foreign `tenancy_id` never falls back to the owner view. |

Scope limits that this does **not** move:

- **The existing live PDF route has no tenant PDF.** M6-B separately renders owner-only tenant
  archives from frozen data. The live PDF route is landlord audience and `to_pdf_data` deliberately
  has **no** audience parameter, because a
  Mieter-Einzelabrechnung is a separate, independently rendered document (§ 3) and adding a flag to
  the existing route is exactly the "render everything and hide rows" shape § 3 forbids.
- **Slice C applies renter-side half-up rounding and one owner residual to NK.** Its applicable
  Page-02 authority remains production-blocking; heating uses the same rounding shape.
- Remaining live-preview gaps stay separate from the shipped M6-B final archive described next.

### Specified Page 01 and shipped M6-A/M6-B archive output

The complete Page 01 contract and exact `08-F01…F24` data-only oracle are **Specified and approved**.
M6-A/M6-B ship confirmed actual advances, Saldo/Nachzahlung/Guthaben branches, immutable
finalization, archived bytes/hashes, isolated rendered tenant archives and the formal-minimum #3
carrier. M6-C1/M6-C2 ship bank-matching logic, ledger/cash persistence and owner endpoints, and
M6-C3-0 verifies their database invariants. C3a's service and final `0021` are technically complete,
development-synchronized and locally merged; C3b's job entrypoints are technically complete and
locally merged, and so is the C3c landlord *Zahlungen* screen, which changes no statement figure
and no rendered byte. Renter
delivery/portal remains M10. These archives are owner-only technical
records, not legal-production or renter delivery output.

### Future dependencies

Detailed BetrKV production classification belongs to `docs/09`; tax and Anlage-V mappings to future
`docs/11`; reusable deadline orchestration to `docs/12`; bank matching to `docs/15`; and UVI/DWD
rules to approved `docs/16`. This file records their boundaries and does not duplicate or
invent their contracts.

## 2. Page 01 source coverage and output contract

### Source-section coverage

| Page 01 source | Transcription home | Golden evidence |
| --- | --- | --- |
| § 1 purpose and three projections | § 3 and § 8 below | `08-F01`, F06, F17, F21 |
| § 2 legal basis and conventions | §§ 4–7; Appendices B/C | register inventory and fixture table |
| § 3.1 object/period inputs | `docs/02`; this section | F01, F14–F15, F18–F20 |
| § 3.2 tenancy inputs | `docs/02`; § 8 | F01–F05, F10, F16–F19 |
| § 3.3 cost-line inputs | § 5 | F01, F05, F08, F11–F12 |
| § 3.4 heating/CO₂ inputs | `docs/03`; § 6 | F05, F07–F09, F24 |
| § 3.5 vacancy inputs | `docs/02`; Eigentümer row and annex below | F01, F06, F21–F23 |
| D0 fictional occupancy | `docs/02`; Eigentümer row | F01, F21–F23 |
| D1 audience selection | § 3 | F06, F17, F21 |
| D2 fixed tenant order | output contract below | F02–F05, F07, F09, F18–F19 |
| D3 cost line/reference totals | §§ 4–5 | F01, F08, F11–F14, F16, F20 |
| D4 party subtotal | `Ihr Anteil gesamt` | F01–F05, F08, F10, F12, F16, F18–F19, F24 |
| D5 actual advances/Saldo | § 4 and § 8 | F01–F04, F08, F10, F12, F14, F16, F18–F19, F24 |
| D6 heating verification | § 6 | F07–F08, F24 |
| D7 CO₂ box | § 6 | F09, F24 |
| D8 § 35a block | output contract below | F01–F05, F24 |
| D9 deadline result | output contract below; cadence waits for `docs/12` | F14, F18–F19 |
| D10 footer/disclaimer/page breaks | §§ 5 and 7 | all rendered cases |
| D11 owner overview | Eigentümer row | F01, F06, F08, F12, F17, F21–F24 |
| D12 vacancy annex | Eigentümer row and annex | F21–F23 |
| § 5 E1–E21 | active contract below | F05, F08, F10–F23; E15/E16/E20/E21 retain stated dependencies |
| § 6 F01–F24 | Appendix A | `berkay_01_golden.py`, `test_berkay_01_complete_coverage.py` |
| § 7 ownership/out of scope | §§ 1 and 9 | documentation-only scope checks |

### Page 01 output contract

- **One calculation, three projections.** `OWNER` produces the internal
  Vermieter-Gesamtübersicht, `TENANT(tenancy_id)` one Mieter-Einzelabrechnung, and `TAX` the
  Leerstandsaufstellung. Selection happens before rendering. A missing or foreign tenancy fails and
  never falls back to an owner view.
- **Fixed tenant order.** Anschreiben; object/period; costs; party subtotal; heating evidence and CO₂
  where applicable; actual advances and Saldo; § 35a only when non-zero; payment/credit handling;
  notices; disclaimer; `Rechtsstand`.
- **No document-layer money math.** Every cost line receives engine output: total, applied key,
  numerator, denominator with unit, and rounded share. Credits stay separate negative lines. A zero
  consumption denominator gives renters `0` and leaves the cost with the owner; it never silently
  changes to an area key.
- **Saldo uses actual payments.** `saldo = party subtotal − geleistete Vorauszahlungen`. Missing
actual advances hard-block a tenant document; confirmed zero is valid. The current contractual
Soll scalar is not a substitute.

**M6-A preview boundary (23.08.2026).** Before finalization, the existing owner-only statement flow
may show a selected tenancy's `subtotal`, reconciliation state, and — only after an explicit current
advance reconciliation — confirmed actual advances and arithmetic Saldo. The persistence and
versioning contract is `docs/02` “M6-A temporal advances and confirmed actual-advance preview”.
No reconciliation means that advances and Saldo are omitted rather than estimated from contractual
Soll. This preview is not a renter document and must not use legal payment-result wording; it does
not change the PDF, tenant portal, finalization, receivables, bank matching or tax-export boundary.
- **Deadline behavior.** A late landlord `Nachforderung` is suppressed while the arithmetic remains
  visible as `Rechnerischer Saldo`; a renter `Guthaben` remains payable. A landlord exception needs
  an explicit reason. Cadence and escalation belong to `docs/12`.
- **Period boundary.** A shorter Rumpfperiode is day-exact. More than 12 months hard-blocks before an
  engine run or render. Leap years keep their actual days. The NK engine enforces this as a
  billing-window precondition (`08-F15`), so an over-long period fails before any cost is allocated;
  no golden fixture may assert shares for one.
- **Tenancy changes create separate documents.** Each uses only its own clipped dates, actual
  advances and result. Zero clipped usage days produces no tenant document or portal item and is not
  itself vacancy.
- **The owner view reconciles.** It contains every covered tenancy and one unconditional owner
  residual per cost type, including `0,00 €` and negative values. It never shares a tenant delivery
  channel.
- **The vacancy annex keeps origin.** Block (a) itemises vacancy by unit and cost type; block (b)
  carries non-allocable costs; block (c) carries the rounding difference and no economic item.
- **Heating and CO₂ project `docs/03`.** MDL pass-through and self-billing are different inputs.
  `08-F01` and `08-F24` are different paths, not competing expected results.
- **§ 35a is line-wise.** Round each eligible line half-up to cents, then add; omit the block at zero.
- **Copy and pagination are binding.** Never use `rechtssicher`, never split an indivisible
  statement, and never place another renter's data on a tenant copy.

### Inputs and immutable result shape

Money is integer cents, dates are inclusive/day-granular, and areas are fixed-point decimal m². The
normalized statement input carries object/period identity, rule/register versions, addressee and
delivery data, clipped tenancy facts, actual advances, cost results, the complete applicable
heating/CO₂ result, vacancy origins, warnings and provenance.

`docs/02` owns persistence. Preview is live. Finalization stores immutable normalized inputs,
results, engine/rule versions, every applicable `Rechtsstand`, timestamps, hashes and separately
archived documents. A finalized version is never rebuilt from current mutable rows.

## 3. Audience split and privacy boundary

### Two documents from one calculation

| Document | Audience | Contents | Delivery status |
| --- | --- | --- | --- |
| **Vermieter-Gesamtübersicht** | landlord/internal | all parties and the full reconciliation | **Shipped** live preview, rendered |
| **Mieter-Einzelabrechnung archive** | exactly one covered tenancy | only that tenancy's share, advances, Saldo and notices | **Shipped** as an owner-only M6-B technical archive; no renter portal/delivery or legal-production approval |
| **Leerstandsaufstellung** | landlord/tax evidence | origin-preserving vacancy/non-allocable/rounding blocks | **Capability shipped** as a server-side projection over owner-side rows; the rendered annex and the tax handoff stay **Specified**, M6/tax handoff |

The server constructs each projection from the selected result before rendering. It never renders an
all-renters PDF and crops, covers or hides rows afterward; hidden PDF structure is still a disclosure.

The shipped projection enforces that boundary by type rather than by a flag: what a renderer is not
given, it cannot leak. The `TENANT` projection contains no owner residual, no other party's line and
none of the building-wide findings, and an unknown, foreign or zero-usage-day tenancy is refused
instead of falling back to the owner view. The live demo still renders only the landlord audience.
M6-B independently renders tenant archives from frozen data; it does not create a renter route,
portal item or delivery.

#### Preview versus finalization (M6)

- Preview reads current inputs, recalculates and creates no archive.
- Finalization creates an immutable account/building/period/version snapshot with inputs, outputs,
  rule versions, `Rechtsstand`, party lines, timestamps and hashes.
- It archives one owner overview and one independently rendered tenant document for every eligible
  tenancy with more than zero clipped usage days.
- Corrections append `vN+1`, retain/supersede `vN`, and preserve referenced inputs and bytes.

## 4. The four formal minimum requirements

| # | Requirement | Current landlord render |
| --- | --- | --- |
| 1 | **Zusammenstellung der Gesamtkosten** per cost type | ✅ rendered |
| 2 | **Angabe und Erläuterung des Verteilerschlüssels** | ✅ rendered |
| 3 | **Berechnung des Anteils des Mieters** | ◐ live preview remains unchanged; M6-B final archive prints the operator/numerator carrier |
| 4 | **Abzug der geleisteten Vorauszahlungen → Saldo** | ❌ live preview remains unchanged; M6-A/M6-B final archive uses confirmed actual advances and Saldo |

Markers describe the current PDF only. The approved Page 01 specification contains all four.

### #3 is partly closed, and this is which part

The page prints `Gesamtkosten`, the applied key, party `Bemessung`, `Gesamtbemessung` with unit and
the euro share. It still must print the relationship
`Anteil = Gesamtkosten × Bemessung ÷ Gesamtbemessung` and derive a numerator such as
`5.430 m²·Tage = 30 m² × 181 Tage`. Both gaps apply to NK and heating.

Slice B did not move this marker. It closed the application path into the render (object/period
selection, the D0 denominator, CONSUMPTION values and the audience projection) and changed nothing
about what the page prints for a share. The operator and the numerator derivation remain missing and
stay with M6.

### #4 technical implementation boundary

Minimum #4 deducts **geleistete** Ist advances. `advance_payment_cents × months` is contractual Soll,
fails for arrears, changes and partial periods, and is forbidden. M6-A/M6-B satisfy the final archive
with frozen, explicitly confirmed actual advances. M6-C1/M6-C2 now supply matching logic,
receivables, accepted-allocation persistence and the immutable ledger boundary. C3a's application
service is technically complete, development-synchronized and locally merged; C3b's jobs are
technically complete and locally merged. The live landlord preview still omits
minimum #4; the separate M6-B final archive prints its frozen Saldo branch.

## 5. Shared rendered-document rules

### The disclaimer states what Lokara is, never that this Abrechnung is complete

Fixed footer copy, tier 2:

```text
Lokara ist ein Werkzeug für die rechtskonforme Betriebs- und Heizkostenabrechnung, keine Rechts- oder Steuerberatung.
```

The subject is Lokara. The sentence is not an attestation that this artifact is complete. Never use
`rechtssicher`, a StBerG warning, an `ohne Gewähr` disclaimer or a lawyer/tax-adviser approval claim.

### `Ihr Anteil gesamt` — the per-party total, and why it is never a Saldo

`Anteil gesamt = Betriebskosten-Anteil + Heizungs-Anteil` after each engine's cent rounding. It moves
no euro and adds no new rounding rule.

#### The label is `Anteil`. `Saldo` is forbidden, and so is everything that implies one

Until actual advances render, the block uses `Anteil`, never `Saldo`, `Nachzahlung`, `Guthaben`,
`zu zahlen`, `offener Betrag` or `fällig`.

#### The one sentence that has to accompany it

```text
Der Anteil gesamt ist die Summe der in derselben Zeile ausgewiesenen Anteile; geleistete
Vorauszahlungen sind darin nicht berücksichtigt.
```

#### Where it renders, and why there

It is the last body block after heating disclosures, CO₂ and § 9a notes, immediately before the
footer. Both addends have then appeared, and nothing is inserted between the heating money table and
Block A. M6 extends this location with actual advances and Saldo; `Anteil gesamt` remains the first
line and the explanatory sentence is removed when it becomes false.

#### Which parties get a row, and which label

The owner overview has one row per renter-side party in stable money-table order and one final
`Eigentümeranteil` row. The tenant document uses the second-person `Ihr Anteil gesamt` for its single
addressee. The owner overview uses the neutral column header `Anteil gesamt`.

#### Required rendered text

| Partei | Betriebskosten | Heiz- und Warmwasserkosten | Anteil gesamt |
| --- | ---: | ---: | ---: |
| Wohnung A — Anna Beispiel | 600,00 € | 5.603,97 € | **6.203,97 €** |
| Wohnung B — Bernd Muster | 178,52 € | 1.493,26 € | **1.671,78 €** |
| Wohnung C — Clara Vorlage | 240,00 € | 1.762,32 € | **2.002,32 €** |
| Eigentümeranteil | 181,48 € | 1.283,37 € | **1.464,85 €** |
| **Summe der Anteile** | **1.200,00 €** | **10.142,92 €** | **11.342,92 €** |

Each column reconciles over the rendered rows. The heating sum excludes the separately deducted
157,08 € CO₂ landlord share. Without heating, that column is absent and the block still renders.

#### Carrier, tier and page breaks

`.party-total` is tier 1. It may break between rows, never inside a row; its title stays with the
first following row and it uses `orphans: 2; widows: 2`.

### Die Eigentümerzeile — always printed, never a Quote

The owner amount is one Liegenschafts residual, not a party, occupancy share or separately weighted
quota. The engine/model contract lives in `docs/02` and `docs/03`; this section owns presentation.

The numbered headings below are compatibility anchors. Existing code and test references to
`docs/08` → "Die Eigentümerzeile" §§ 1–6 resolve within this section; § 3a remains the party-total
specialization of § 3.

#### 1 — The row renders unconditionally, including at 0,00 €

It renders last even at `0,00 €` and may be negative. A missing row is not a zero. It belongs to the
owner overview and vacancy/tax projection, never a tenant document.

#### 2 — No Quote, ever. What goes in the Bemessung column

- with vacancy/self-use, show aggregated fictional occupancy in the column's unit;
- when fully let, leave the cell empty, not `0` or `—`;
- never print `%`, `‰`, `Quote` or `x von y` on the owner residual row.

The Bemessung explains origin; it does not derive the amount. The residual wins over a separately
rounded vacancy calculation.

#### 3 — The heating table: one Eigentümer row across all four blocks

One final `Eigentümeranteil` row carries heating base, heating consumption, warm-water base,
warm-water consumption and total. Block B uses the same aggregated label. Block C decomposes a
single unit and therefore retains per-segment landlord labels. Liegenschaft-level tables aggregate;
single-unit timelines preserve origin.

#### 3a — The party-totals block gets one Eigentümer row, not two

The final owner summary row adds all NK and heating residuals. Slice C applies the Page-02 residual
model to NK. M6-B ships the tenant document as an owner-only technical archive; presenting it *to*
a renter is M10 delivery/portal work, not M6.

#### 4 — Required rendered text (Gesamtübersicht)

```text
Der Eigentümeranteil ist der Restbetrag: umlagefähige Heiz- und Warmwasserkosten abzüglich der
Summe der Mieteranteile. Er enthält den auf Leerstand und Eigennutzung entfallenden Anteil sowie
die zeilenweise Rundungsdifferenz. Er wird nicht aus einer Quote berechnet.
```

#### 5 — The Leerstandsaufstellung (D12): (a) / (b) / (c)

| Block | Meaning | Granularity |
| --- | --- | --- |
| (a) | vacancy amount for Werbungskosten evidence | per empty unit and cost type |
| (b) | non-allocable costs | per cost position; reference value corrected to **100.800 ct** |
| (c) | `owner residual − Σ(a)` rounding difference | no unit; no economic item |

The reference case prints `(a) 17.531`, `(b) 100.800`, `(c) 0`, total `118.331` ct. A separate
counterfactual vacancy calculation gives `17.536`; it does not replace the residual. Required
convention copy:

#### 5a — Round 4 final Block-(c) rendering

Block (c) is only a subline of the owner residual. It never has a separate pot, amount addition,
Bemessung or quota. Render it only when its cents are non-zero; retain the mandatory value in the
audit log at zero too. The landlord/statement text below the owner row is “davon
Rundungsdifferenz”; the tax-adviser vacancy-schedule text is “Rundungsdifferenz aus der
zeilenweisen Verteilung — keiner Einheit zurechenbar”. This is a `Konvention` (Darstellungswahl,
no external source); it does not upgrade any legal flag.

For the Round-4 § 12 HeizkostenV reduction convention, show separately identified non-cascading
15%/3%/3% components only after the later calculation lane has made them available. At two or more
grounds, show the specified non-blocking review warning; this document neither calculates nor
silently aggregates a reduction.

```text
Hinweis: Der Abzug als Werbungskosten setzt eine fortbestehende Einkünfteerzielungsabsicht voraus
(§§ 9, 21 EStG; BFH IX R 68/10). Die Feststellungslast liegt bei Ihnen (§ 90 AO). Diese Aufstellung
dient dem Nachweis gegenüber dem Finanzamt; sie ist keine gesetzlich vorgeschriebene Form.
```

#### 6 — The result-shape contract

`HeatingResult.lines` contains renter-side lines. Required `owner_residual` contains the four money
blocks, total, origin tuple, rounding difference and optional aggregated Bemessungen. It is never
`None` and carries no quota field. Reconciliation is structural:

```text
Σ renter lines + owner residual + CO₂ landlord deduction = total cost
```

#### The one asymmetry this slice leaves, deliberately

Heating ships one residual. The NK money table still contains per-unit landlord-side lines until the
reviewed Page 02 production method changes renter rounding and the owner result together. Display
aggregation must not pretend those current NK lines were calculated as a residual.

### Reference totals (Gesamtbemessung) — one per allocation key

Print the denominator the engine actually used, beside each applied key:

| Key | Printed Gesamtbemessung | Unit/de-scale |
| --- | --- | --- |
| `AREA` | Σ `area_sqm_x100 × days` | m²·Tage, ÷100 |
| `PERSONS` | Σ `people × days` | Personen·Tage |
| `UNITS` | Σ `1 × days` | Einheiten·Tage |
| `MEA` | Σ `mea_x10000 × days` | MEA·Tage, ÷10000 |
| `CONSUMPTION` | Σ period-resolved values | carried `MeasurementUnit`; no day weighting |
| `DIRECT` tenancy | none | single party; denominator 1 is noise |
| `DIRECT` unit | Σ segment days | Tage |

De-scale the sum once. `36.500 m²·Tage` must never render as `3.650.000`. A tenant copy shows its own
Bemessung and the object-level Gesamtbemessung; it never needs another renter's value.

#### Rounding

Fixed-point denominators de-scale exactly. Fractional displayed Bemessungen follow the rule under
`Display rounding of a fractional Bemessung` below.

### `MeasurementUnit` travels with the value — the plumbing decision (slice 5)

The value and its unit travel together through meter/domain input, engine result and statement. A
side-channel display-unit mapping is forbidden because it can disagree with the number. The table
restores the stable rule numbers used by code and tests without reviving the implementation diary:

| Existing compatibility anchor | Binding rule |
| --- | --- |
| `MeasurementUnit` rule 1 | The unit travels on the dataclass that carries the value, through input, engine result and statement. |
| `MeasurementUnit` rule 2 | One summable key has one unit; mixed declared units are an input error, never a display choice. |
| `MeasurementUnit` rule 3 | A missing contributing unit propagates to `None`; the renderer keeps the explicit withholding branch. |
| `MeasurementUnit` rule 4 | Under § 9a Abs. 2, `None` means no consumption Bemessung was applied; render the area key and denominator instead of the withholding copy. |
| `MeasurementUnit` rule 5 | A genuinely missing unit withholds the unit-free denominator; it never prints a bare plausible number. |
| `MeasurementUnit` rule 6 | Compact and long German spellings follow "Which spelling goes where" below. |
| `MeasurementUnit` rule 7 | The demo uses flat values `600/250/150` HKV units, total `1.000`; the building meter's `20.000 kWh` is the § 9 energy denominator, not that Bemessung. |

This carrying decision moves no euro.

#### Which spelling goes where

| Unit | Compact numeric form | Long heating-key form |
| --- | --- | --- |
| `KWH` | `kWh` | `Erfasster Wärmeverbrauch in kWh am Wärmemengenzähler` |
| `HKV_UNITS` | `HKV-Einheiten` | `Erfasster Wärmeverbrauch in Einheiten eines Heizkostenverteilers` |
| `CUBIC_METRE` | `m³` | no heating form; rejected for `MeterKind.HEAT` |

NK names the unit but not a device. Warm water remains m³ by the typed § 9 path.

### Heating table footer — the figure is the Gesamtkosten, not the column's sum

#### Required rendered text (heating footer)

With CO₂:

```text
Gesamtkosten Heizung und Warmwasser (inkl. CO₂-Vermieteranteil)          10.300,00 €
Summe der oben ausgewiesenen Anteile: 10.142,92 €. Die Differenz von 157,08 € ist der
CO₂-Vermieteranteil; er wird vor der Umlage abgezogen (§ 7 Abs. 1 CO2KostAufG).
```

Without CO₂, both printed figures are equal and no difference sentence renders. The footer says
`Gesamtkosten`, not `Summe`, because the CO₂ landlord deduction is not a party row. The NK footer
keeps `Summe Betriebskosten (stimmt centgenau mit den Gesamtkosten überein)` while that claim remains
true.

## 6. Heizkostenabrechnung — the heating table's disclosure

The renderer uses engine **results**, never parallel inputs, for every disclosed operand. It does not
recalculate ratios, pots, Bemessungen, CO₂ classification or legal branches.

The numbered headings in this section are compatibility anchors: existing references to heating
items 1–6 mean the matching headings below. References to 4a/4b retain their current carrier and
pagination meaning.

### The worked example

Demo period 01.01.–31.12.2025: 100 m²; total cost 10.300,00 €; 20.000 kWh gas; 40 m³ warm water;
heat-device values 600/250/150 HKV units; warm-water values 20/12/8 m³; 4.000 kg CO₂; CO₂ cost
261,80 €.

| Stage | Current result |
| --- | --- |
| CO₂ | 40,0 kg CO₂/m²/Jahr; landlord 60 % = 157,08 €; renter side 104,72 € |
| billable after deduction | 10.142,92 € |
| § 9 separation | Q(WW) 5.000 of 20.000 kWh; WW 2.535,73 €; heating 7.607,19 € |
| 30/70 split | heating 2.282,16/5.325,03 €; WW 760,72/1.775,01 € |
| area denominator | 18.250 / 5.430 / 5.520 / 7.300 = 36.500 m²·Tage |
| heat denominator | 600 / rd. 145,8 / rd. 104,2 / 150 = 1.000 HKV-Einheiten |
| WW denominator | 20 / 5,950684… / 6,049315… / 8 = 40 m³ |
| unit-B degree days | 583,3 / 416,7 ‰ of 1.000 ‰ |

Unit B's heating-consumption amounts are 776,39/554,87 €. Page 01b K3 rounds the renter's
145,825 device units to one decimal and assigns the 104,2 device-unit residual to the landlord.
The pot remains 1.331,26 €.

### 1 — Umlageschlüssel and Gesamtbemessung per money column

| Money column | Applied key | Gesamtbemessung |
| --- | --- | --- |
| Grundkosten Heizung | Wohnfläche — § 7 Abs. 1 HeizkostenV | 36.500 m²·Tage |
| Verbrauch Heizung | recorded heat unit; Nutzerwechsel uses degree days | 1.000 HKV-Einheiten |
| Grundkosten Warmwasser | Wohnfläche — § 8 Abs. 1 HeizkostenV | 36.500 m²·Tage |
| Verbrauch Warmwasser | recorded m³ | 40 m³ |

**All four rows render. The withholding is of one cell, never of a row.**

#### The withheld cell is a sentence, not a blank

When `heat_consumption_unit is None` and area fallback is false:

```text
ohne Maßeinheit — nicht ausgewiesen
```

```text
Für den erfassten Wärmeverbrauch wird keine Gesamtbemessung ausgewiesen: Die Maßeinheit der
Erfassungsgeräte (kWh oder Einheiten eines Heizkostenverteilers) liegt dieser Abrechnung nicht vor.
Der Verbrauchsanteil wurde gleichwohl nach den erfassten Werten verteilt.
```

No digit, zero, dash or unit-free denominator substitutes for the missing unit.

#### The `Verbrauch Heizung` row under § 9a Abs. 2 — it states Wohnfläche, not Wärmeverbrauch

When the consumption key fell back, print
`Wohnfläche (m²·Tage) — § 9a Abs. 2 HeizkostenV` and `36.500 m²·Tage`. The same rule applies to the
warm-water consumption column. No consumption Bemessung renders for a pot allocated by area.

#### Required rendered text — Block A

Block A, `Aufteilung der Gesamtkosten`, prints:

1. total cost, optional CO₂ landlord deduction and billable cost;
2. the applied § 9 measured or area-fallback formula and resulting WW/heating pots;
3. applied base/consumption percentages and permitted bounds;
4. the four euro pots.

The CO₂ line exists only when a split exists. Without central warm water, there is no § 9 paragraph
or WW line. Percentages and operands come from the result.

Demo copy and figures:

```text
Gesamtkosten Heizung und Warmwasser                                  10.300,00 €
− CO₂-Vermieteranteil (§ 7 Abs. 1 CO2KostAufG)                          157,08 €
= umlagefähige Kosten                                                10.142,92 €

§ 9 HeizkostenV — Trennung von Heizung und Warmwasser
Q(WW) = 2,5 kWh/(m³·K) × 40 m³ × (60 °C − 10 °C) = 5.000 kWh von 20.000 kWh Gesamtenergie
→ Warmwasser 2.535,73 € · Heizung 7.607,19 €

§§ 7, 8 HeizkostenV — angewendet 30 % Grundkosten / 70 % Verbrauch
Heizung: Grundkosten 2.282,16 € · Verbrauchskosten 5.325,03 €
Warmwasser: Grundkosten 760,72 € · Verbrauchskosten 1.775,01 €
```

#### Required rendered text — Block B

Block B, `Bemessungsgrundlagen`, has the four key/denominator rows followed by party Bemessungen.
Each displayed column sums to its displayed Gesamtbemessung. Column and row order follow the money
table. The withholding branch removes the heat Bemessung column, not its key row.

#### Display rounding of a fractional Bemessung (new — the NK weights were all integral)

Display at most two decimals and suppress trailing zeroes. Use largest remainder across the displayed
column so printed party values sum to the printed denominator. Derived rounded values carry `rd.`;
exact values do not.

#### The rounding is disclosed — `rd.`, one sentence, and an operator that is the operation

```text
Wohnung B — Bernd Muster: 12 m³ × (181 von 365 Tagen) = rd. 5,95 m³
```

Use `= rd.`, not a false exact equality and not `≈`. Directly below Block B:

```text
Gerundete Bemessungen sind mit rd. gekennzeichnet; gerechnet wird mit dem exakten Wert, sodass eine
Nachrechnung aus dem angezeigten Wert um wenige Cent abweichen kann.
```

### 2 — §§ 7/8 HeizkostenV: the applied ratio, stated

Print what was applied and the permitted range. The current model applies one consumption share to
both pots; that is a product shape, not a legal identity. Different configured shares require a
future input shape and two printed ratios.

### 3 — § 9 HeizkostenV: warm-water separation

Measured branch:

```text
Q(WW) = 2,5 kWh/(m³·K) × 40 m³ × (60 °C − 10 °C) = 5.000 kWh von 20.000 kWh Gesamtenergie
```

Area fallback:

```text
Warmwasserverbrauch nicht gemessen — Ersatzwert nach § 9 Abs. 2 HeizkostenV:
32 kWh je m² Wohnfläche und Jahr × 100 m² × (365 von 365 Tagen) = 3.200 kWh von 20.000 kWh
```

The branch that ran and its exact operands are carried on the result. `nicht gemessen` and
`Ersatzwert` never appear on the measured branch.

### 4 — Degree-day apportionment at a Nutzerwechsel (Block C)

#### The method's statutory basis (§ 9b HeizkostenV) is a prerequisite, not an assumption.

The rule source separates law from convention:

```text
§ 9b Abs. 2 und Abs. 3 HeizkostenV; Gradtagszahlen nach anerkannter Promilletabelle
(VDI-Konvention, keine Rechtsnorm) — verify before production
```

The internal flag never renders. The VDI table remains `verify-before-production`.

#### Block C — the rendered form

For each unit with more than one party, show party-labelled `N von M ‰` lines where degree days were
applied, day-derived base/WW lines, and the adjacent convention caveat. Under heat area fallback no
promille line renders because degree days moved no euro. Without central warm water, show only the
day fraction.

```text
Nutzerwechsel — Aufteilung des erfassten Verbrauchs

Wohnung B — Bernd Muster (Auszug 30.06.2025): 583,3 ‰ von 1.000 ‰
Wohnung B — Leerstand ab 01.07.2025 → Vermieter: 416,7 ‰ von 1.000 ‰
Wohnung B — Bernd Muster (Auszug 30.06.2025): 12 m³ × (181 von 365 Tagen) = rd. 5,95 m³
Wohnung B — Leerstand ab 01.07.2025 → Vermieter: 12 m³ × (184 von 365 Tagen) = rd. 6,05 m³

Gradtagszahlen sind eine anerkannte Konvention (VDI-Promilletabelle), keine gesetzliche Vorgabe.
```

The current result lacks segment dates and a unit display label, so Block C uses the stable party
labels it carries. It **states no fact the data does not carry**. Adding dates requires `HeatingLine`
to carry its `Period`; adding a unit heading requires a caller-supplied unit-label mapping.

### 4a — The rendered form (slice 4): carriers, order, and where the copy outran the data

**Carriers, and their tier.** `.cost-split`, `.basis-table` and `.party-change` are separate tier-1
elements in this order immediately after the heating money table. Then come CO₂ and § 9a notes.
Glyphs are fixed copy: `−` minus, `·` separator, `→` result.

#### Two branch forms the items above leave open

- Without CO₂, both the total and `= umlagefähige Kosten` lines remain with equal figures; the
  missing deduction is visible without an equality claim in prose.
- When either consumption pot falls back under § 9a Abs. 2, its Block B row shows the area key,
  citation and area denominator, and no consumption Bemessung for that pot.

### 4b — Pagination: which blocks may break, and what may never be separated

Break at seams, never inside a statement:

| Element | Rule |
| --- | --- |
| `.cost-split`, `.basis-table`, `.party-change`, `.party-total` | no `break-inside: avoid`; they may exceed a page |
| `tr` | `break-inside: avoid` |
| `thead`, `.disclosure-title` | stay with the first following row |
| `.apportionment li` | never split |
| disclosure carriers | `orphans: 2; widows: 2` |

Nothing is inserted between the money table and Block A. Page-count/fill-ratio goldens are forbidden;
they encode the fixture rather than the layout rule.

#### What is pinned, and what honestly cannot be

Template tests pin the declarations above. They do not pin a page count, fill ratio or a universal
claim that a money table and every disclosure fit on one sheet; those properties depend on party
count. Visual review checks the rendered result without turning one demo size into a layout rule.

### 5 — § 7 Abs. 3 CO2KostAufG: current rule

Current H2/R8 behavior is binding: annualise the period intensity, round to one decimal, classify
that rounded value against the **unshortened** Anlage table, and print the same one-decimal value and
band. Never restore the superseded shortened-band method.

The CO₂ block prints renter and landlord amounts, landlord percentage, total emissions, heated area,
CO₂ cost, the one-decimal annualised intensity and its band. Heat pump/biomass paths render no CO₂
block. The template performs no classification arithmetic.

### 6 — M2: every `Rechtsstand` names its statute

Required footer form:

```text
Rechtsstand: § 7 Abs. 1 HeizkostenV 03/1989 · § 9 Abs. 2 HeizkostenV 01/2009 ·
Gradtagszahlen-Promilletabelle (VDI-Konvention, keine Rechtsnorm) 12/1983 ·
§ 5 Abs. 1 i. V. m. Anlage CO2KostAufG 01/2023 · Erstellt mit Lokara.
```

Labels and stamps travel together. `— verify before production` never renders. A bare list of dates
is forbidden.

### The carried-intermediates contract (slice 3)

The shipped frozen result carries every operand needed by Blocks A–C and CO₂. Required invariants:

- required disclosure fields have no silent defaults;
- `None` means the branch was not applied, except the explicitly visible missing-unit branch;
- money is `Cents`; scaled names state their scale;
- the renderer reads results, never parallel inputs;
- `WarmWaterSeparation` identifies method and operands;
- `HeatingResult` carries billable cost, pots, applied share/bounds, fallbacks and unit;
- `HeatingLine` carries days, unit total, area-day weight, consumption weights and degree-day
  numerator/denominator;
- `Co2Result` carries emissions, heated area, CO₂ cost, band, day counts and annualisation factor;
- `OwnerResidual` retains origins and is always present.

The live dataclasses in `packages/heating-engine` are the exact shipped field/type source. This
contract prevents a renderer from recomputing discarded intermediates.

## 7. Which text on the statement is legally required

This file assigns carriers; `docs/05` owns thresholds.

| Content | Carrier | Tier |
| --- | --- | --- |
| BGH totals, keys, shares and advances | cost rows, `.key-label`, `tfoot` | 1 |
| NK key and Gesamtbemessung | `.key-label` | 1 |
| heating Blocks A/B/C | `.cost-split`, `.basis-table`, `.party-change` | 1 |
| heating footer reconciliation | `tfoot .foot-note` | 1 |
| § 9a estimation/fallback | `.note` | 1 |
| CO₂ split/basis | `.co2` | 1 |
| party totals and no-advances sentence | `.party-total` | 1 |
| labelled `Rechtsstand` and disclaimer | `footer` | 2 |

Every carrier is in exactly one tier. `.note` is tier 1 because it changes how the renter reads the
applied key or whether a value is measured. Ordinary metadata and framing remain body/secondary copy
under the normal AA requirement. This assignment is current artifact evidence, not product-wide
accessibility certification.

## 8. Mieter-Einzelabrechnung and finalization contract

### Page 01b output reconciliation

The complete calculation contract remains in `docs/03`. Its document projection is:

| Page 01b output | Required statement behavior |
| --- | --- |
| four heating pots and keys | show §§ 7/8/9 split, ratio, every denominator and party Bemessung |
| owner residual | one unconditional owner row; no quota; zero/negative allowed; never on tenant copy |
| CO₂ duty | show renter amount, landlord deduction, one-decimal annualised/classified intensity, unchanged band and reproducible operands; no block for heat pump/biomass |
| supplier fallback | label derived mass and warn; internal rule metadata retains the direct `0,201` Hu and `0,181` Ho paths, but statement requirements expose only the shared EBeV provenance at `Rechtsstand 01/2023`; never print `0,903`, `geprüft` or the register-review date `07/2026`, and never derive cost |
| device evidence | device, room, old/new reading, factor and one-decimal units; label § 9a estimates/basis |
| readiness/reduction risks | show 15 % and each 3 % separately; never auto-deduct or combine while sources conflict; hard stop means no statement |
| WW central/unit difference | leave unmetered use in owner residual; show 10 % notice and 20 % warning without blocking |
| MDL | confirm every extracted field; net never double-deducts CO₂; gross rescales exactly and records accepted residuals; excess blocks |
| § 6a annual information | source/THG/primary energy, taxes/charges, equipment/readout/billing fees, contact, dispute notice, average-user information and graphical prior-year comparison |
| prior-year graph | adjust heat with each year's DWD factor; keep WW raw; label unadjusted fallback; no empty graph; source line required |

The BAnz notice identity under § 6a Abs. 3 S. 4 remains pre-legal. The UVI has a different
no-omission contract owned by approved `docs/16`.

The Page 01 contract required M6 to add, without reinterpreting Page 01:

- addressee and creation date;
- the rendered operator and numerator derivation needed to close minimum #3;
- start/end meter evidence and consistency provenance;
- actual paid advances and positive/negative/zero Saldo branches;
- late-Nachforderung and Guthaben notices;
- payment/credit details;
- one isolated document per eligible tenancy;
- immutable snapshot, archived bytes/keys and hashes.

### M6-B final renderer and archive boundary

**Status:** shipped technical archive boundary. **Rechtsstand:** 08/2026. This closes the technical
carriers for formal minimum #3 (operator/numerator derivation) and #4 (deduction of confirmed
actual advances), but does not clear the register's `verify-before-production` labels or authorize
delivery. The current live landlord preview and demo PDF remain unchanged; M6-B introduces a
separate final-document renderer only.

The renderer receives one preselected final snapshot, not live account rows. It independently renders
the owner archive and each tenant archive. It must never build an all-renters PDF and redact/crop it
afterwards.

| Archive | Required contents | Forbidden contents |
| --- | --- | --- |
| Owner overview | complete owner overview; landlord-only vacancy schedule; every covered party/reconciliation line; zero-day tenancy footnote; applicable notices/disclaimer/`Rechtsstand` | tenant delivery address or another tenant's isolated letter as a substitute for the owner view |
| Tenant document | exactly one eligible tenancy's addressee and creation date; object/period; that tenancy's cost lines and `Anteil`; printed operator and numerator derivation; meter evidence and provenance; confirmed actual advances; Saldo branch; payment/credit instruction; applicable notices; disclaimer; `Rechtsstand` | owner residual, vacancy schedule, building-wide findings, another tenancy's identity, address, advances, share, Saldo or document metadata |

The tenant Saldo branch is determined from the frozen confirmed advances and party subtotal:

- positive, timely: show `Nachzahlung` and the frozen payment instruction; archive one
  `RECEIVABLE` settlement;
- zero: show `Saldo 0,00 €`; create no settlement;
- negative: show payable `Guthaben` and the frozen credit instruction; archive one
  `CREDIT_REFUND` settlement;
- late positive without an explicit finalization exception reason: show only `Rechnerischer Saldo`;
  create no receivable or payment-demand wording;
- late positive with a non-blank explicit exception reason: preserve that reason in the snapshot and
  settlement, then use the positive branch. The reason is an auditable override, not a legal answer.

The required calculation carrier is visible per allocated line:
`Anteil = Gesamtkosten × Bemessung ÷ Gesamtbemessung`; where day weighting applies, it also shows the
numerator derivation such as `5.430 m²·Tage = 30 m² × 181 Tage`. All figures come from the frozen
result; document code performs no new money calculation. Meter evidence/provenance is printed as
provided by the final result, including source and consistency state, rather than inferred during
rendering.

Page 01b additionally requires supplier-fallback provenance, device evidence, readiness/reduction
risks, WW central/unit difference notices, MDL confirmation and § 6a annual information as specified
in `docs/03`. A hard-stop run produces no statement; risk amounts are never auto-deducted.

## 9. Open dependencies — not permission to invent

- **Remaining M6:** none. C3a is technically complete, development-synchronized and locally
  merged, and C3b's three job entrypoints and C3c's landlord *Zahlungen* screen are technically
  complete and locally merged. Renter delivery/portal is M10.
- **Live demo PDF:** operator/numerator derivation and actual-advance Saldo remain absent; M6-B's separate archive has them.
- **Meters:** start/end readings and their consistency path are not carried to the statement.
- **Heating:** § 9 leap-year fallback divisor and the source-backed convention questions remain in
  `docs/03`; different §§ 7/8 shares need a future input shape.
- **Page 01b implementation:** derived-mass provenance, § 7 Abs. 4/readiness risks, device evidence
  and annual comparison remain exactly as `docs/03` records.
- **D2 owners:** `docs/09` classification; `docs/11` tax mapping; `docs/12` guards; `docs/15` bank
  matching rules and remaining workflow; `docs/16` UVI/DWD and the unresolved § 6a notice identity.
- **Page 01 E16/E21:** tenant disclosure and tax timing remain unguessed and visibly open.

## Interim framing

The shipped demo is described only as:

> This is the landlord's calculation view — every party, reconciling to the cent. The tenant letter,
> with actual advance payments and the resulting balance, is a later document from the same engine.

Do not present the current PDF as a tenant statement.

## Appendix A — fixture coverage, exactly `08-F01` through `08-F24`

The data-only oracle is `packages/domain/tests/berkay_01_golden.py`; completeness/arithmetic checks
are in `test_berkay_01_complete_coverage.py`. Green oracle tests prove transcription, not application
closure.

| Fixture | Current rule/result |
| --- | --- |
| `08-F01` | MDL reference: `1.072.600` total, `1.055.069` allocated, `17.531` owner residual |
| `08-F02` | `288.577 − 288.000 = 577` Nachzahlung |
| `08-F03` | `116.007 − 120.000 = −3.993` Guthaben |
| `08-F04` | zero Saldo at advances `288.577` |
| `08-F05` | heat pump/no labor: heating `93.876`, total `293.453`, no CO₂/§35a |
| `08-F06` | owner overview reconciles and prints owner column including zeros |
| `08-F07` | MDL evidence passes through; device delta does not move money |
| `08-F08` | area fallback `40.034`; mixed-path overhang `9.034` hard-warns |
| `08-F09` | CO₂ `30.954 = 12.382 + 18.572`; tenant shares sum `18.572` |
| `08-F10` | NULL actual advances hard-block; confirmed zero yields `288.577` Nachzahlung |
| `08-F11` | separate gross/credit rounding `10.943 − 882 = 10.061`; net-first forbidden |
| `08-F12` | zero consumption leaves `126.000` with owner; Erika `−24.871` |
| `08-F13` | 31-day overlap over-allocates `2.294` m²-days and blocks |
| `08-F14` | 275 days: `12.412 / 53.350`, share `22.800`, Saldo `1.800` |
| `08-F15` | 455 days hard-blocks |
| `08-F16` | isolated documents `245.571/15.571` and `116.007/−3.993` |
| `08-F17` | zero clipped usage: no document/portal item and not vacancy |
| `08-F18` | late positive `577` becomes `Rechnerischer Saldo` |
| `08-F19` | late negative `−3.993` remains payable Guthaben |
| `08-F20` | leap year uses 366 days / `71.004` area-days |
| `08-F21` | block (a) `17.531`; counterfactual `17.536`; block (b) `100.800`; (c) `0` |
| `08-F22` | fictional occupancy moves `1.858` to owner; total `62.000` |
| `08-F23` | full-year vacancy remains in denominators: owner `37.381` tax, `20.667` waste |
| `08-F24` | self-billing: heating `338.218`, allocated `1.076.002`, owner `20.816` |

### M6-B executable fixture map

These M6-B fixtures are green implementation evidence. They extend, rather than replace, the
Page-01 data oracle above. They are technical archive fixtures; green results do not approve legal
production or delivery.

| Fixture | Required result |
| --- | --- |
| `M6B-F02` | A tenant subtotal/confirmed advances of `28.857/28.000` freezes Saldo `857`, produces a timely `RECEIVABLE`, and archives owner plus that tenant document. |
| `M6B-F03` | `28.857/28.857` freezes zero Saldo and creates no settlement. |
| `M6B-F04` | `28.857/30.000` freezes Saldo `−1.143`, prints `Guthaben`, and produces `CREDIT_REFUND` for `1.143`. |
| `M6B-F10` | Missing reconciliation hard-blocks all writes; an explicitly confirmed empty allocation set is valid zero. |
| `M6B-F14` | A 275-day clipped tenancy archives its own `22.800` share/`1.800` Saldo and carries the visible numerator derivation. |
| `M6B-F16` | Mid-period tenancies produce separate documents; each serialized tenant PDF contains neither the other tenancy's identity nor financial data. |
| `M6B-F17` | A zero-clipped-day tenancy has no archive/settlement and no portal item; the owner archive contains the zero-day footnote. |
| `M6B-F18` | A late positive `577` has only `Rechnerischer Saldo` and no settlement unless a non-blank exception reason is frozen. |
| `M6B-F19` | A late negative `−3.993` remains a payable `Guthaben` and creates `CREDIT_REFUND` `3.993`. |
| `M6B-IMM` | Snapshot, archive bytes/hash/MIME/filename and selected address/instruction values remain byte-for-byte unchanged after later source versions. |
| `M6B-CORR` | Only an explicit correction of the latest final version yields `vN+1`; predecessor snapshots/documents stay readable and the predecessor is `SUPERSEDED`. |
| `M6B-ISO` | RLS/composite edges and owner-only endpoints refuse foreign account/building/tenancy access; an employee or renter has no finalization/history/download/address/instruction access. |

## Appendix B — Page 01 register inventory

The 26 Page 01 rows are **11 `geprüft`** and **15 `verify-before-production`**.

| Status | Exact CSV rows |
| --- | --- |
| `geprüft` | CO₂-Stufenmodell Wohngebäude · CO₂-Pflichtangaben in der Abrechnung · § 35a-Ausweis für den Mieter · Kürzungsrecht — nicht verbrauchsabhängig abgerechnet · Abrechnungsfrist Betriebskosten · § 6a Abs. 3 — Pflichtinformationen zur Abrechnung · Leerstand bleibt im Gesamtverteiler · CO₂-Kürzungsrecht · Belegeinsicht und Beweislast der Erfassung · Einwendungsfrist des Mieters · Belegeinsicht — elektronische Bereitstellung zulässig (Wohnraum) |
| `verify-before-production` | Fiktivbelegung bei Leerstand · Gradtagszahltabelle VDI (K3) · Kürzungsrecht — fehlende fernablesbare Ausstattung · Rundungsweg (Seite 01 / docs/03 § 6) · Geräteliste auf der Mieterausfertigung (K10) · Zahlungsfrist bei Nachzahlung · Verteilungsrest (K9) · Grundkostenanteil (K1) · Kürzungsrecht — fehlende oder unvollständige § 6a-Information (UVI + Abrechnungs-Infoblock) · Verbrauchsvergleich — Umfang und Bereinigung · Grundkosten-Verteilung nach m²-Tagen (K2) · § 35a-Block auf der Betriebskostenabrechnung · Wording Leerstandsaufstellung · Kürzungsrecht — CO₂-Anteil nicht ausgewiesen · CO₂-Mieteranteil — Pro-rata-Ableitung (D7 Schritt 6) |

K9's rounding direction remains a flagged convention. Approved `docs/03` § 9.2 separately fixes
the owner-residual destination as a model rule. Neither status erases the other.

**Zahlungsfrist bei Nachzahlung — how the flag is honoured in code (M6-C2).** The register records
no statutory deadline: the claim falls due on receipt of a proper statement, and the customary
30 days is a `Konvention` anchored only in § 286 Abs. 3 BGB. The Page-01 handoff in
`apps/api/src/lokara_api/routers/payments.py` therefore takes the due date from the caller and
refuses the request without it, rather than defaulting the 30 days. A default would turn a flagged
convention into Lokara's answer on every statement, silently and at scale, which is precisely what
`verify-before-production` is meant to prevent. The flag stays open; only its consequence in code
is now settled.

## Appendix C — historical source disposition

`docs/03` Appendix D is the single historical correspondence-retirement ledger. Current statement
authority here comes from original Page 01, approved `docs/02`/`docs/03`, the register rows above and
the committed `08-F01…F24` oracle. The heat-only UVI correction remains owned by approved `docs/16`.
