# 08 — The Abrechnung document (formal content)

> **Status: ⏳ spec pending.** This file records the **known gaps** found by reviewing the first
> rendered statement, so they aren't lost. The full layout spec replaces the body below when it lands;
> build from this file, not from a pasted spec.
>
> ⚠️ **Not legal advice.** The requirements below are the well-established formal minimums; confirm the
> specifics with a Fachanwalt/Steuerberater before shipping to real tenants (`docs/07`).

---

## Why this file exists

`docs/03` specifies the **math** in depth; nothing specified the **document**. So the first PDF renders
the engine's output faithfully and is still not an Abrechnung a landlord could send. The math is the
hard part and it's correct — what's missing is document completeness, not new calculation.

## The four formal minimum requirements

Settled BGH case law: a Betriebskostenabrechnung must contain all four.

| # | Requirement | Current render |
| --- | --- | --- |
| 1 | **Zusammenstellung der Gesamtkosten** (per cost type) | ✅ |
| 2 | **Angabe + Erläuterung des Verteilerschlüssels** | ✅ — e.g. "Wohnfläche (m²·Tage)" |
| 3 | **Berechnung des Anteils des Mieters** | ◐ **half** — every figure is on the page, the calculation joining them is not (spelled out below) |
| 4 | **Abzug der geleisteten Vorauszahlungen** → **Saldo** | ❌ **missing** |

Markers: **✅** rendered · **◐** partly rendered — what is and is not on the page is named exactly,
never left to the reader · **❌** absent.

### #3 is half closed, and this is which half

The share the engine computes is `Anteil = Gesamtkosten × Bemessung ÷ Gesamtbemessung`. Checked
against the rendered PDF (`packages/pdf/output/nk-heating-statement-demo.pdf`), **all four figures of
that equation are now printed**:

- **Gesamtkosten** of the cost — on the cost header row (that is minimum #1);
- **Bemessung** of the party — e.g. `5.430` on Wohnung B's line;
- **Gesamtbemessung** of that cost's key, with its unit — `36.500 m²·Tage`, added by the
  reference-totals slice below;
- **Anteil** in euro; plus the **Umlageschlüssel** label (minimum #2).

Two things are missing, and #3 is a *Berechnung* — something the tenant re-performs — until both are
there:

1. **The operator is nowhere on the page.** Nothing states that those four figures stand in the
   relation `Anteil = Gesamtkosten × Bemessung ÷ Gesamtbemessung`. A reader who does not already know
   the formula reads four unrelated numbers.
2. **The numerator is not derived.** `5.430` is printed as a bare Bemessung. That it is
   `30 m² × 181 Tage` appears nowhere — neither the `30 m²` nor the `181 Tage` is next to it. The
   tenant can re-use the figure but cannot check it, so a wrong area or a wrong move-out date is
   invisible in the document.

**#4 is the point of the document for the tenant:** advances paid − share owed = **Nachzahlung oder
Guthaben**. The data model already anticipates it (`docs/02`: the statement's Nachzahlung/Guthaben
becomes a `Payment` in the Ledger); it is simply not on the page.

## Two documents from one calculation ⚠️

The first render shows **every party's name and share to everyone**. That is right for the landlord and
**wrong — and a DSGVO problem — for the tenant**.

| Document | Audience | Contents |
| --- | --- | --- |
| **Vermieter-Gesamtübersicht** | landlord (internal) | all parties, full reconciliation — *what the first render already is* |
| **Mieter-Einzelabrechnung** | one tenant (the envelope) | **only that tenant's** share, their advances, their balance. **No other tenant's name or amount.** |

Both derive from the same engine result — this is a rendering split, not a second calculation.

## Also missing from the tenant document

- **Addressee block + date** — the statement is addressed to one tenant (name, address).
- ~~**Reference totals so the share is verifiable**~~ — specified below ("Reference totals
  (Gesamtbemessung)"), one per allocation key with its own unit, and **rendered** since `b404173`.
  It makes the share *checkable against a denominator*; it does not by itself close BGH #3 (see the
  ◐ note above).
- **Heating consumption values** — meter start/end readings (HeizkostenV gives the tenant a right to
  check); wire from `Zähler` data, not fixtures.
- **§556 deadline context** — the 12-month Abrechnungsfrist, and the tenant's Einwendungsfrist.
- **Payment details** — IBAN/reference for a Nachzahlung, or how a Guthaben is settled.
- **Multiple cost types** — the engine handles n; the demo seeds one. See below.

## Reference totals (Gesamtbemessung) — one per allocation key

> **Rechtsstand 08/2026** (transcribed 03.08.2026). This is a **document-layout rule**, not a legal
> value: it introduces nothing into `packages/rules-store` and reads no dated rule. Every figure it
> prints is already in the engine result. The legal *purpose* is BGH formal minimum **#2/#3** above —
> settled case law, cited here exactly as loosely as the table above cites it; confirm with a
> Fachanwalt before real tenants (`docs/07`).

**Why.** Minimum #3 is *"Berechnung des Anteils des Mieters"* — a **calculation**, not a result. The
tenant sees `€600.00` and their own `18.250 m²·Tage`; without the **denominator** those two numbers
prove nothing. `600 = 1200 × 18.250 / 36.500` is only checkable once `36.500` is on the page. The
share alone is unverifiable, which is precisely the formal defect that makes statements
challengeable.

**This section does not close #3** — it supplies the denominator and nothing else. The page still
states no operator, and it still prints the numerator (`18.250`) without the `50 m² × 365 Tage` it
comes from; see *"#3 is half closed, and this is which half"* above. What would close #3 is a rendered
per-party calculation that names the operation **and** derives the Bemessung from its factors. A
future slice owns that; it is deliberately not designed here.

**What the row is.** For each cost on the statement, the **sum of the allocation weights of all
parties of that cost**, de-scaled to the human figure, printed with its unit next to that cost's
Umlageschlüssel. It is the denominator the engine actually divided by — not a stock building figure.

**One per allocation key, and they are not interchangeable.** The keys have different denominators
*and* different units. A statement with two keys prints two reference totals. A single figure is
correct only while a statement carries exactly one key, which is a property of today's demo, not of
the product.

Derived from `packages/nk-engine/src/lokara_nk_engine/engine.py` (`_segment_parties`,
`_persons_parties`, `_consumption_parties`, `_direct_parties`) and the unit spellings already in
`_ALLOCATION_KEY_LABELS` / `_WEIGHT_DISPLAY_DIVISORS` in `packages/pdf/src/lokara_pdf/statement.py`:

| Key | Engine weight per party | Reference total | Unit | De-scale ÷ |
| --- | --- | --- | --- | --- |
| `AREA` | `area_sqm_x100 × Tage` | Σ weights ÷ 100 | **m²·Tage** | 100 |
| `PERSONS` | `Personen × Tage` | Σ weights | **Personen·Tage** | 1 |
| `UNITS` | `1 × Tage` | Σ weights | **Einheiten·Tage** | 1 |
| `MEA` | `mea_x10000 × Tage` | Σ weights ÷ 10000 | **MEA·Tage** | 10000 |
| `CONSUMPTION` | the metered value (already period-resolved upstream — **no day weighting**) | Σ weights | ⚠️ **unit not derivable — see gap below** | 1 |
| `DIRECT` → a tenancy | `1` (single party) | **none** | — | — |
| `DIRECT` → a unit | `1 × Tage` per segment | Σ weights | **Tage** | 1 |

Two notes on `DIRECT`, because "DIRECT allocates nothing proportionally" is only half true:

- `direct_tenancy_id` → exactly one party, weight `1`. A denominator of `1` is noise; print **no**
  reference total. Proposed copy: *"Direktzuordnung — vollständig dieser Partei zugeordnet"*.
- `direct_unit_id` → the engine **does** day-split within that unit (renter vs. vacancy/Eigennutzung,
  `_segment_parties(..., key_value=1)`). That split has a denominator: the unit's **Tage** in the
  billing window. Print it.

### Required rendered text

German UI copy (CLAUDE.md), on the cost's header row, appended after the Umlageschlüssel:

```
Umlageschlüssel: Wohnfläche (m²·Tage) · Gesamtbemessung: 36.500 m²·Tage
Umlageschlüssel: Personenzahl (Personen·Tage) · Gesamtbemessung: 1.638 Personen·Tage
Umlageschlüssel: Einheiten (Einheiten·Tage) · Gesamtbemessung: 1.095 Einheiten·Tage
```

The token is **`Gesamtbemessung`**, matching the existing `Bemessung` column header — it is the
column's total, and it is day-weighted, so it is *not* the bare `Gesamtfläche` in m². 100 m² is not
the number `600,00 €` was computed from; `36.500 m²·Tage` is. (The earlier gap note said
"Gesamtfläche / Gesamteinheiten / Gesamtverbrauch"; that named the *idea*. Bare m² would not make the
share verifiable, so the label carries the day-weighted unit. `Gesamtverbrauch` survives unchanged
for `CONSUMPTION`, which is genuinely not day-weighted.)

Formatting: `format_number_de` (German grouping), the figure and its unit separated by a space
(normal or non-breaking — both render identically and `assert_statement_pdf.py` flattens whitespace).

### Rounding

Divide the **sum** by the de-scale divisor; never round per line and then sum. Divisors are 100 /
10000 over integer weights, so the division is exact and no rounding rule is needed. The invariant —
the same one every allocation test asserts for money — is that the printed Gesamtbemessung equals the
sum of the printed Bemessung values of that cost's lines, exactly.

### ⚠️ De-scaling (carried over from `docs/03`)

The AREA figure is **`36.500`**, never **`3.650.000`**; a line is **`18.250`**, never **`1.825.000`**.
`docs/03` states outright that *tests comparing integers stay green through this bug* — which is why
the assertion lives over **rendered text** (`packages/pdf/tests/`, and `scripts/assert_statement_pdf.py`
over the PDF), not over engine values. The scaled form is asserted **absent** as a canary, not merely
the de-scaled form present.

### Both documents

The Mieter-Einzelabrechnung shows **the tenant's own** Bemessung plus the Gesamtbemessung — that pair
is the whole point, and it leaks nothing about other tenants. The Vermieter-Gesamtübersicht keeps it
as the column total it already visually implies.

### Gap — not invented here

The **unit of a `CONSUMPTION` reference total is not derivable from the engine result.**
`ConsumptionValue` (`nk-engine/inputs.py`) carries `unit_id`, `tenancy_id`, `value` — no unit of
measure — and `_ALLOCATION_KEY_LABELS` spells `CONSUMPTION` as bare `"Verbrauch"` with no unit.
`MeasurementUnit` (`domain/meter.py`: `KWH`, `CUBIC_METRE`, `HKV_UNITS`) is the right type, but
nothing carries it from the meter into the statement, and it has no German display spelling anywhere
(`kWh` / `m³` / `Einheiten` are unwritten). **Resolution:** the caller (which resolves meters) passes
the display unit into `StatementData` per cost, and the German spellings of `MeasurementUnit` are
written down — in this file — first. Until then no `CONSUMPTION` reference total is specified and
none is fixture-tested; a guessed unit on a Verbrauchsabrechnung is a defect that reaches a tenant.

## Heating table footer — the figure is the Gesamtkosten, not the column's sum

> **Rechtsstand 08/2026** (transcribed 03.08.2026). A **document-copy rule**: it introduces nothing
> into `packages/rules-store` and reads no dated rule. The one legal value involved — the CO₂ split —
> is resolved by the heating engine from the store and already carries its own `Rechtsstand` on the
> page. The statutory reference in the copy below was checked against the consolidated text of the
> CO2KostAufG as of 08/2026; standard caveat of this file applies (`docs/07`).

**The defect.** The heating `tfoot` currently reads *"Summe Heiz- und Warmwasserkosten (inkl.
CO₂-Vermieteranteil, stimmt centgenau mit den Gesamtkosten überein)" — 10.300,00 €*. The sentence is
literally true: 10.300,00 € **is** the Gesamtkosten. But it sits under a column of four party amounts
that sum to **10.240,00 €** (5.657,60 + 1.509,84 + 1.293,36 + 1.779,20). The 60,00 € difference is the
CO₂-Vermieteranteil, which is deducted **before** the renter-facing split (§ 7 Abs. 1 CO2KostAufG) and
is **not a row in the table**. So the column visibly does not add up while the footer appears to assert
that it does.

Two things make it worse than a loose phrase:

- The word **`Summe`** is itself part of the claim. A `tfoot` labelled *Summe* under a column of
  amounts means "these amounts, added up". Here it is not that.
- The Betriebskosten footer uses the **identical parenthetical** for a row where the claim is true.
  Same wording, two meanings, one page — a reader who verifies the first will trust the second.

### Required rendered text (heating footer)

German UI copy (CLAUDE.md), in the heating table's `tfoot` label cell. Two lines in **one** cell; the
footer's amount column carries **exactly one figure**, the Gesamtkosten.

With a CO₂ split (`heating.co2` present):

```
Gesamtkosten Heizung und Warmwasser (inkl. CO₂-Vermieteranteil)          10.300,00 €
Summe der oben ausgewiesenen Anteile: 10.240,00 €. Die Differenz von 60,00 € ist der
CO₂-Vermieteranteil; er wird vor der Umlage abgezogen (§ 7 Abs. 1 CO2KostAufG).
```

Without a CO₂ split (`heating.co2 is None` — the two figures are then equal by construction):

```
Gesamtkosten Heizung und Warmwasser                                      10.300,00 €
Summe der oben ausgewiesenen Anteile: 10.300,00 €.
```

Rules the copy encodes:

- **State what the figure is, never that a column sums to it.** `Gesamtkosten`, not `Summe`.
- **The reconciliation is printed as figures, in both branches** — sum of the shares, and (when there
  is one) the difference, named and cited. No branch asserts an equality in words; the reader adds two
  printed numbers. One code path, so the no-CO₂ case cannot drift back into a claim.
- The label is **fixed copy**, not derived from `StatementData.heating_cost_label` — that field
  spells the heading *"Heiz- und Warmwasserkosten"*, which would render as
  *"Gesamtkosten Heiz- und Warmwasserkosten"*.
- Both euro figures come from the engine result (Σ `HeatingLine.total`, `Co2Result.landlord_amount`),
  formatted with `format_eur`. Nothing here is a new calculation.

Gate: `packages/pdf/tests/test_statement_heating_footer.py` — asserts the claim per section (present
on the Betriebskosten footer, absent from the heating one), the copy above with both figures derived
from the engine, and the arithmetic that motivates it: the **rendered** party amounts sum to strictly
less than the footer figure, by exactly the CO₂-Vermieteranteil. A future change that drops the CO₂
deduction — making the column add up and the old wording true again — surfaces there rather than
silently.

### The Betriebskosten footer keeps its current wording ⚠️

*"Summe Betriebskosten (stimmt centgenau mit den Gesamtkosten überein)"* stays **exactly as it is**.
There the claim holds: the indented party rows sum to the printed figure to the cent, and that
reconciliation is the engine's core invariant (`docs/03` → Rounding). Do **not** "harmonise" the two
footers back into identical wording — the wordings differ because the facts differ. (The cost-header
rows in that table sit in the same column but are group totals, not addends; the addends are the
indented lines.)

If a pre-split deduction is ever introduced on the Betriebskosten side, the same rule applies there
and the claim comes out.

### The eventual fix is a row, not a wording — and it is not this slice

The better long-term answer is that the CO₂-Vermieteranteil becomes a **visible row in the heating
table** (a landlord-side party line), so the column literally adds up to the Gesamtkosten and no
explanatory sentence is needed. That belongs with the heating table's full treatment — the open
question *"Heating: how consumption values and the CO₂ split are presented to the tenant"* below. It is
recorded here so the reword is understood as an interim honest state, and it is **not** specified or
designed in this section.

## BetrKV cost-type catalogue (to specify)

`BetrKV §2` enumerates the umlagefähige Betriebskosten (Grundsteuer, Wasser, Abwasser, Aufzug,
Straßenreinigung, Müllbeseitigung, Gebäudereinigung, Gartenpflege, Beleuchtung, Schornsteinreinigung,
Sach-/Haftpflichtversicherung, Hauswart, Gemeinschaftsantenne, Wäschepflege, sonstige Betriebskosten).
Needed from the Notion page: the **canonical list with default allocation keys per type**, and which are
**not** umlagefähig (Instandhaltung, Verwaltung) so the UI can warn rather than silently allocate them.

→ lands in `packages/rules-store` with a `Rechtsstand`, never hardcoded in an engine.

**Two screens are already waiting on it**, and both currently take a free-text label rather than a
type: *Kosten erfassen*, and the M4 *Beleg-Upload* review step. The extraction returns a category
(`Müllabfuhr`) but deliberately derives **no** Umlageschlüssel from it — it reports the key as *not
extracted* (`docs/04` → "Beleg-Upload"). Once the catalogue exists, that mapping becomes a suggested
key with a `Rechtsstand`, and the non-umlagefähig types become a warning on entry. Until then a
suggestion would be invented law, not a convenience.

## Open questions the spec must answer

- [ ] Layout of the Mieter-Einzelabrechnung (sections, order, what appears per cost type)
- [ ] Exact **Vorauszahlung → Saldo** block wording and arithmetic
- [x] Which reference totals accompany each allocation key → **"Reference totals (Gesamtbemessung)"**
      above. One open sub-question remains: the **unit** of a `CONSUMPTION` total (see the gap there).
- [ ] Heating: how consumption values and the CO₂ split are presented to the tenant — **including
      the CO₂-Vermieteranteil as a visible row** in the heating table, which is the eventual fix the
      footer reword above is standing in for
- [ ] What closes BGH minimum #3: a rendered per-party calculation (the operator, and the Bemessung
      derived from its factors) — see the ◐ note under the four-minimums table
- [ ] Required legal notices (§556 frist, Einwendungsfrist, disclaimer placement)
- [ ] BetrKV cost-type catalogue + default keys + non-umlagefähig flags
- [ ] A **worked example** with real numbers → becomes the golden fixture for the document layer

## Interim framing for the 06.08 pitch

The current PDF is the **landlord's calculation view**, and it's honest to present it as such:

> *"This is the landlord's calculation view — every party, reconciling to the cent. The tenant letter,
> with advance payments and the resulting balance, is the next document off the same engine."*

True, and it reads as roadmap rather than gap. Do **not** present it as the document a tenant receives.
