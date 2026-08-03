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
| 3 | **Berechnung des Anteils des Mieters** | ◐ **half** in the **Betriebskosten** table — every figure is on the page, the calculation joining them is not (spelled out below) · ❌ in the **heating** table — no key, no Bemessung, no denominator at all (see *"The heating table is not ◐ — it is ❌"*) |
| 4 | **Abzug der geleisteten Vorauszahlungen** → **Saldo** | ❌ **absent by decision** — blocked on the M6 Payment Ledger, not on rendering ([why](#4-is-blocked-on-the-m6-ledger-by-decision)) |

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

### The heating table is not ◐ — it is ❌

The ◐ above is a statement about the **Betriebskosten** table only. Verified 03.08.2026 by reading the
rendered PDF (`packages/pdf/output/nk-heating-statement-demo.pdf`), not the template source: in the
heating section the page prints six euro columns and **nothing else**.

- No Umlageschlüssel for any of the four money columns.
- No Bemessung column, therefore no per-party numerator.
- No Gesamtbemessung, therefore no denominator.
- No §§ 7/8 base/consumption ratio — the demo runs 30/70 and the page never says so.
- No § 9 warm-water separation.
- No Gradtagszahlen: the 585/415 ‰ split exists on the page **only** as the ratio between two printed
  euro amounts (786,24 / 557,76). Text search over the rendered PDF: `HeizkostenV` **0**, `585` **0**,
  `415` **0**, `‰` **0**.

So for heating the defect is not "the operator is missing" (that is the Betriebskosten state). There is
no equation on the page to be missing an operator from. The spec that closes it is
[Heizkostenabrechnung — the heating table's disclosure](#heizkostenabrechnung--the-heating-tables-disclosure)
below.

**#4 is the point of the document for the tenant:** advances paid − share owed = **Nachzahlung oder
Guthaben**. The data model already anticipates it (`docs/02`: the statement's Nachzahlung/Guthaben
becomes a `Payment` in the Ledger); it is simply not on the page.

### #4 is blocked on the M6 ledger, by decision

> **Rechtsstand 08/2026** (recorded 03.08.2026). No legal value enters `packages/rules-store` from
> this section — it records what may **not** be computed, and why. Standard caveat of this file
> applies (`docs/07`).

> **DECISION (settled, 03.08).** Minimum #4 stays **❌ by decision, not by oversight**. It is blocked
> on the **M6 Payment Ledger**, not on rendering, and the contractual-figure shortcut
> (`advance_payment_cents × months`) is **explicitly rejected**. Nothing renders a Saldo before M6.

**The shortcut computes the wrong quantity.** `advance_payment_cents × months` is the **agreed**
(Soll) figure. § 556 Abs. 3 BGB and the BGH minimum above require the deduction of the **geleisteten**
(Ist) Vorauszahlungen — what the renter actually paid. The two diverge exactly where the document
matters most: a renter in arrears receives a statement **understating their Nachzahlung**. That is a
wrong document, not a rounding difference, and it is wrong in the landlord's favour on its face while
being against his interest in substance — settled case law treats Sollvorschüsse silently entered in
place of the Istvorauszahlungen as costing the landlord the unpaid advances once the § 556 Abs. 3
Abrechnungsfrist has run.

**The Ist figure is not derivable from anything in the tree today.**

- **There is no `Payment` table.** `docs/02` puts the whole Payment Ledger at **M6**.
- The `BankGateway` is a **stub** (`packages/adapters/src/lokara_adapters/bank.py`) carrying **one
  January transaction per renter**, with rent and NK **fused into a single amount** (`117000` =
  950,00 € Miete + 220,00 € NK) and the split recorded nowhere. Even a real AIS feed gives a
  transaction, not an allocation; the ledger is what turns one into the other.

**The demo hides both problems — this is the thing that will tempt someone.** All three seeded
tenancies begin and end on **month boundaries** and none has an advance change, so `monthly × months`
happens to be exact for 2025 (2.640,00 / 900,00 / 1.320,00 €) and the shortcut would look right on
the pitch PDF. It is right by coincidence of the fixture. A **mid-month move-out** has no defined
answer under that formula at all — and the legal question was never "how many months" but "what was
received".

**Second dependency, same milestone.** Even the Soll side is not currently expressible over time:
`Tenancy.advance_payment_cents` is a scalar, though § 560 Abs. 4 BGB lets either party adjust the
advance after every statement — recorded as a named defect in `docs/02` → *"DEFECT:
`Tenancy.advance_payment_cents` is a scalar on a temporal row"*, with the temporal
`AdvancePaymentPeriod` that replaces it also owned by M6.

The ledger design is **not** re-derived here; `docs/02` → "Payment Ledger" already sketches it. What
this section fixes is only that the gap is deliberate and what would close it.

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

## Heizkostenabrechnung — the heating table's disclosure

> **Rechtsstand 08/2026** (transcribed 03.08.2026). This section introduces **no legal value** into
> `packages/rules-store` and computes nothing new: every figure it specifies is either already in the
> engine result or is an intermediate the engine already computes and currently discards (named below).
> The statutory references — §§ 7, 8, 9, 9a, 9b HeizkostenV and § 7 CO2KostAufG — were checked against
> the consolidated texts as of 08/2026. Standard caveat of this file applies (`docs/07`): confirm with
> a Fachanwalt before real tenants.

**What this section is for.** A Betriebskostenabrechnung is legible on the page since the reference
totals landed; the Heizkostenabrechnung is not (see *"The heating table is not ◐ — it is ❌"*). The
rule the whole document is built on — *a tenant must be able to re-perform the calculation, not just
read its result* — applies to the heating section exactly as it applies to the NK section, and the
heating section has more of it to disclose: two cost pots, four money columns, three different
denominators and one apportionment convention.

### The fact that shapes every slice below: `HeatingResult` cannot supply these figures

Verified against `packages/heating-engine/src/lokara_heating_engine/` on 03.08.2026. `HeatingResult`
carries exactly `lines`, `co2`, `estimated_unit_ids`, `consumption_fallback_to_area`, `total`. Every
intermediate this spec needs is computed in `engine.py` as a local and then dropped:

| Discarded today | Where | Needed for |
| --- | --- | --- |
| `q_ww` (warm-water energy) and the § 9 formula inputs applied | `_separate_warm_water` | § 9 disclosure |
| `ww_pot` / `heating_pot` | `_separate_warm_water` | § 9 disclosure |
| `heat_base_pot` / `heat_cons_pot`, `ww_base_pot` / `ww_cons_pot` | `calculate_heating_statement` | §§ 7/8 disclosure |
| `rules.consumption_share` (the ratio actually applied) + the bounds | input, never echoed | §§ 7/8 disclosure |
| `_Party.base_weight` | `_build_parties` | per-party Bemessung (Fläche·Tage) |
| the consumption weights from `_consumption_weights` | local list | per-party Bemessung (Verbrauch) |
| `_Party.degree_day_promille` and its per-unit total | `_build_parties` | the 585/415 ‰ |
| `_Party.days` | `_build_parties` | day-apportionment of WW/base at a Nutzerwechsel |
| `total_co2_kg`, `co2_cost`, `heated_area_sqm`, the selected step's band | `_apply_co2` / `co2.py` | § 7 Abs. 3 CO2KostAufG Berechnungsgrundlagen |

**Consequence:** the renderer *cannot* show any of this today, and no amount of template work changes
that. The engine result must carry it first — a pure-package change under CLAUDE.md rule 1
(framework-free, golden fixtures, `mypy --strict`, `Decimal`/cents), then a template change. The
proposed split at the end of this section is built on that seam.

**A rule the template must not break to get around it:** the disclosure figures come from the **engine
result**, never from the engine *input* passed alongside it. Two sources drift; the page would then
state a ratio that was not the one applied. This is the same rule the heating footer already follows
("Both euro figures come from the engine result … Nothing here is a new calculation").

### The worked example (the demo building, 01.01.–31.12.2025)

Every figure below is the real output of `packages/pdf/src/lokara_pdf/demo.py` re-run on 03.08.2026 —
not a hand calculation. It is the source for the golden fixtures of the slices below.

Building: A 50 m², B 30 m², C 20 m²; Bernd Muster leaves B on 30.06.2025 (B vacant Jul–Dec).
Gesamtkosten Heizung + Warmwasser **10.300,00 €**; Gesamtenergie **20.000 kWh**; Warmwasser
**40 m³** gemessen; Wärmeverbrauch A/B/C **600 / 250 / 150** (Anzeige der Erfassungsgeräte);
Warmwasserverbrauch A/B/C **20 / 12 / 8 m³**; CO₂ **2.000 kg**, CO₂-Kosten **300,00 €**.

| Stage | Figures |
| --- | --- |
| CO₂ (§ 7 CO2KostAufG) | Intensität 2.000 kg ÷ 100 m² = **20 kg CO₂/m²/a** → Vermieteranteil **20 %** = **60,00 €**, Mieteranteil **240,00 €** |
| umlagefähig nach Abzug | **10.240,00 €** |
| § 9 Trennung | Q(WW) = 2,5 × 40 × (60 − 10) = **5.000 kWh** von 20.000 kWh → Warmwasser **2.560,00 €**, Heizung **7.680,00 €** |
| §§ 7/8 bei 30/70 | Heizung: Grund **2.304,00 €** / Verbrauch **5.376,00 €** · Warmwasser: Grund **768,00 €** / Verbrauch **1.792,00 €** |
| Grundkosten-Bemessung | A 18.250 · B-Mieter 5.430 · B-Vermieter 5.520 · C 7.300 · **Σ 36.500 m²·Tage** |
| Wärmeverbrauchs-Bemessung | A 600 · B-Mieter 146,25 · B-Vermieter 103,75 · C 150 · **Σ 1.000** (Einheit noch nicht mitgeführt — siehe Lücke) |
| Warmwasser-Bemessung | A 20 · B-Mieter 5,95 · B-Vermieter 6,05 · C 8 · **Σ 40 m³** |
| Gradtagszahlen B | 01.01.–30.06. **585 ‰ von 1.000 ‰** · 01.07.–31.12. **415 ‰ von 1.000 ‰** |
| Tage B (Grund + WW) | **181 von 365** bzw. **184 von 365** |

Party totals (already rendered): 5.657,60 / 1.509,84 / 1.293,36 / 1.779,20 € — Σ 10.240,00 €, plus the
60,00 € CO₂-Vermieteranteil = 10.300,00 €.

### 1 — Umlageschlüssel and Gesamtbemessung per money column

The heating table's four money columns **do not share a denominator**, and that is the whole reason the
NK solution (one label appended to the cost header row) does not transfer:

| Money column | Umlageschlüssel | Gesamtbemessung (demo) |
| --- | --- | --- |
| Grundkosten Heizung | Wohnfläche (m²·Tage) — § 7 Abs. 1 HeizkostenV | 36.500 m²·Tage |
| Verbrauch Heizung | Erfasster Wärmeverbrauch (Nutzerwechsel: Gradtagszahlen) | **withheld** — unit not carried, see gap |
| Grundkosten Warmwasser | Wohnfläche (m²·Tage) — § 8 Abs. 1 HeizkostenV | 36.500 m²·Tage |
| Verbrauch Warmwasser | Erfasster Warmwasserverbrauch (m³) | 40 m³ |

**Decision: two disclosure blocks beneath the table, not more columns.** Four Umlageschlüssel + four
Gesamtbemessungen + up to three per-party Bemessung values cannot go into a table that already carries
six money columns on A4 portrait: at three extra columns the amounts start wrapping, and `docs/05`
("Restraint over reduction … reduce ornament, never clarity") does not license a nine-column grid at
8 pt. The money table stays as it is. Directly beneath it, in this order:

1. **Block A — "Aufteilung der Gesamtkosten"** — how 10.300,00 € became the four pots (§§ 7, 8, 9 and
   the CO₂ deduction). This is the *vertical* half of the calculation and it is the part that is
   currently invisible.
2. **Block B — "Bemessungsgrundlagen"** — a second, narrow table: one row per column stating its
   Umlageschlüssel + Gesamtbemessung, then one row per party with its Bemessung values. This is the
   *horizontal* half — the analogue of the NK table's `18.250`.
3. **Block C** — the Nutzerwechsel/Gradtagszahlen note (only when a unit has more than one party).
4. Then the existing CO₂ block and the existing § 9a notes, unchanged in position.

#### Required rendered text — Block A

German UI copy (CLAUDE.md). Amounts via `format_eur`, other figures via `format_number_de`.

```
Aufteilung der Gesamtkosten (HeizkostenV)

Gesamtkosten Heizung und Warmwasser                                  10.300,00 €
− CO₂-Vermieteranteil (§ 7 Abs. 1 CO2KostAufG)                           60,00 €
= umlagefähige Kosten                                                10.240,00 €

§ 9 HeizkostenV — Trennung von Heizung und Warmwasser
Q(WW) = 2,5 kWh/(m³·K) × 40 m³ × (60 °C − 10 °C) = 5.000 kWh von 20.000 kWh Gesamtenergie
→ Warmwasser 2.560,00 € · Heizung 7.680,00 €

§§ 7, 8 HeizkostenV — Grund- und Verbrauchskosten: angewendet 30 % Grundkosten / 70 % Verbrauch
(zulässiger Rahmen: 50 % bis 70 % Verbrauchskosten, § 7 Abs. 1 HeizkostenV)
Heizung:     Grundkosten 2.304,00 € · Verbrauchskosten 5.376,00 €
Warmwasser:  Grundkosten   768,00 € · Verbrauchskosten 1.792,00 €
```

Rules the copy encodes:

- **The CO₂ line is a deduction, not a share.** It repeats what the footer already says, in the place
  where the arithmetic happens. It renders **only** when `heating.co2` is present; without it the block
  opens directly at `umlagefähige Kosten = Gesamtkosten`.
- **The § 9 line prints the formula it applied, with its operands** — see item 3 below for the fallback
  branch, which prints a *different* formula and must never print this one.
- **`angewendet 30 % / 70 %` and the bound are two different facts** and are printed as two: what was
  used, and what the law permits. A statement that prints only "70 %" tells the tenant nothing about
  whether that was lawful; a statement that prints only the bound hides what was applied.
- Percentages are derived from the resolved rule value (`consumption_share`, `split_bounds`), never
  written as literals in the template.

#### Required rendered text — Block B

```
Bemessungsgrundlagen

Spalte                    Umlageschlüssel                       Gesamtbemessung
Grundkosten Heizung       Wohnfläche (m²·Tage)                  36.500 m²·Tage
Grundkosten Warmwasser    Wohnfläche (m²·Tage)                  36.500 m²·Tage
Verbrauch Warmwasser      Erfasster Warmwasserverbrauch (m³)    40 m³

Partei                                        Fläche·Tage   Verbrauch Warmwasser
Wohnung A — Anna Beispiel                          18.250                  20 m³
Wohnung B — Bernd Muster (Auszug 30.06.2025)        5.430                5,95 m³
Wohnung B — Leerstand ab 01.07.2025 → Vermieter     5.520                6,05 m³
Wohnung C — Clara Vorlage                           7.300                   8 m³
Gesamtbemessung                                    36.500                  40 m³
```

- The token stays **`Bemessung` / `Gesamtbemessung`**, matching the NK table — same concept, same word.
- The de-scaling rule of the reference-totals section applies unchanged: `36.500`, never `3.650.000`;
  the **sum** is de-scaled once, never per line.
- **Invariant, asserted over rendered text:** each Bemessung column's printed values sum exactly to the
  printed Gesamtbemessung of that column. Same invariant as the NK reference totals.
- The **Verbrauch Heizung** column is absent from both halves of Block B until the measurement unit is
  carried (gap below). Its euro column stays in the money table; only its Bemessung is withheld.

#### Display rounding of a fractional Bemessung (new — the NK weights were all integral)

`5,950684931506849…` is a real Bemessung (12 m³ × 181/365). The NK section never needed a rule because
every NK weight is an integer. The rule:

1. Display with **at most 2 decimals**, trailing zeros suppressed (`20`, not `20,00`; `5,95`).
2. Round the values of a column with **largest remainder** across that column's parties, so the printed
   values sum exactly to the printed Gesamtbemessung — the same idiom the engine uses for cents
   (`docs/03` → Rounding), ties by stable party order. Rounding each value independently breaks the
   invariant above on a document that is supposed to add up.
3. Where a value was **derived** rather than measured (an apportionment at a Nutzerwechsel), the
   derivation is printed in Block C (`12 m³ × 181 von 365 Tagen`). The 2-decimal figure is the readable
   one; the derivation is the exact one, so the tenant can reproduce the cent.

### 2 — §§ 7/8 HeizkostenV: the applied ratio, stated

- **The ratio is a resolved rule value, not a constant.** `HeatingRules.consumption_share` is supplied
  per building; `packages/rules-store` supplies only the **bounds** (`hkvo.heating-split-bounds`,
  source *§ 7 Abs. 1 HeizkostenV*, `Rechtsstand 03/1989`, min 0,5 / max 0,7) and a
  `DEFAULT_CONSUMPTION_SHARE` of 0,7. The engine rejects any share outside the bounds
  (`HeatingInputError`). The page prints the **applied** share and the **bounds**, both from the result.
- §§ 7 and 8 are cited separately because they are separate rules: § 7 governs the heating cost split,
  § 8 the warm-water cost split. The engine applies the *same* share to both pots
  (`distribute_cents(ww_pot, [1 - share, share])`), which is the common configuration — **not** a legal
  identity. If a building ever configures them differently, the disclosure prints two ratios and the
  input grows a second field; that is out of scope here and is named so it is not assumed away.
- `docs/03` phrases the range as "configurable 30/70 … 50/50" (base/consumption); the store phrases it
  as consumption share ∈ [0,5; 0,7]. Same rule, two spellings — **no contradiction**, and the page uses
  the store's direction ("Verbrauchskosten") with both numbers printed.

### 3 — § 9 HeizkostenV: warm-water separation

Two branches, and they print **different** text. Which one ran is not currently recoverable from the
result — the engine must carry it.

**Measured volume** (`WarmWaterInput.volume_m3` is not None) — the demo case:

```
Q(WW) = 2,5 kWh/(m³·K) × 40 m³ × (60 °C − 10 °C) = 5.000 kWh von 20.000 kWh Gesamtenergie
```

Operands from `WarmWaterFormula` (`hkvo.warm-water-formula`, source *§ 9 Abs. 2 HeizkostenV*,
`Rechtsstand 01/2009`): `factor_kwh_per_m3_kelvin` 2,5 · `hot_temp_c` 60 · `cold_temp_c` 10.

**Unmeasured volume** — § 9 Abs. 2 area fallback:

```
Warmwasserverbrauch nicht gemessen — Ersatzwert nach § 9 Abs. 2 HeizkostenV:
32 kWh je m² Wohnfläche und Jahr × 100 m² × 365 von 365 Tagen = 3.200 kWh von 20.000 kWh
```

- The fallback is **legally weaker than a measurement and must read as one** — the words
  *"nicht gemessen"* and *"Ersatzwert"* carry that; the tenant is entitled to know the number was not
  measured. The measured branch must never render the word Ersatzwert and vice versa.
- The pro-rating (`× days / 365`) is printed because the engine performs it; a 12-month period prints
  `365 von 365 Tagen`, which is honest rather than noise — it shows the tenant the factor exists.
- Both branches print the resulting **euro** pots, because that is what the tenant can check against the
  money table.

### 4 — Degree-day apportionment at a Nutzerwechsel (Block C)

Rendered only for a unit with more than one party in the period. Demo:

```
Nutzerwechsel Wohnung B — Aufteilung des erfassten Verbrauchs

Wohnung B wurde im Abrechnungszeitraum von mehreren Parteien genutzt. Der für die Einheit
erfasste Wärmeverbrauch wurde nach monatlichen Gradtagszahlen auf die Nutzungszeiträume
aufgeteilt: 01.01.–30.06.2025 585 ‰ von 1.000 ‰ · 01.07.–31.12.2025 415 ‰ von 1.000 ‰.
Grundkosten und Warmwasserverbrauch werden nach Tagen aufgeteilt:
12 m³ × 181 von 365 Tagen = 5,95 m³ · 12 m³ × 184 von 365 Tagen = 6,05 m³.

Gradtagszahlen sind eine anerkannte Konvention (VDI-Promilletabelle), keine gesetzliche
Vorgabe (Rechtsstand 01/1981).
```

- **`585 ‰ von 1.000 ‰` — never a bare `585 ‰`.** The promille of a segment is a fraction of the
  *heating year*; over a partial billing period the parties' promille sum to **less than 1.000**, and a
  bare figure would then read as wrong. Printing own/total is the same Bemessung/Gesamtbemessung shape
  the rest of the document uses, and it degrades correctly (`120 ‰ von 300 ‰`).
- **The caveat sentence is mandatory and is the point of this item.** `rules/degree_days.py` marks the
  table *"anerkannte Gradtagszahlen-Promilletabelle (VDI) — verify before production"*. A disclosure
  that presents a convention as law is worse than no disclosure: it invites a tenant to check a
  statute that does not contain the number. The convention caveat renders **wherever a ‰ figure
  renders**, not only in the footer.
- The copy states **no fact the data does not carry**. In particular it must not say "no interim
  reading exists" — `HeatingUnit` carries one consumption value per unit and cannot express an interim
  reading at all, so the engine does not know whether one was taken.
- **The method's statutory basis (§ 9b HeizkostenV) is a prerequisite, not an assumption.** § 9b Abs. 2
  is what permits apportioning an unread period by Gradtagszahlen, and Abs. 3 is what puts Grund- and
  Warmwasserkosten on Zeitanteile — exactly what `engine.py` does. **`packages/rules-store` does not
  record that citation**: the degree-day rule's `source` names only the VDI table. Either the store's
  `source` is extended to name § 9b (a one-line rules-store change, `engine-implementer` lane, listed
  in the split below) **and the copy cites it**, or the citation stays out of the copy. The page must
  not cite a paragraph the store does not carry.
- The internal marker `— verify before production` is a developer note and **never renders**. Asserted
  absent from the PDF.

### 5 — § 7 Abs. 3 CO2KostAufG: what already works, and the remainder only

§ 7 Abs. 3 CO2KostAufG requires the landlord to show, **in the Heizkostenabrechnung**, the tenant's CO₂
share, the building's **Einstufung**, and the **Berechnungsgrundlagen** of that Einstufung.

**Already discharged by the existing `co2_block`** (`statement.py` → `.co2`) — do not respec, do not
re-render:

- the tenant's and the landlord's amounts (240,00 € / 60,00 €) and that the landlord's is deducted
  before allocation;
- the landlord percentage (20 %);
- the intensity (20 kg CO₂/m²/Jahr);
- the citation *CO2KostAufG* with `Rechtsstand 01/2023`.

**The remainder** — the Berechnungsgrundlagen, i.e. the two inputs the intensity was computed from and
the band it selected. Appended to the existing block, same surface, no new block:

```
Berechnungsgrundlagen: CO₂-Emissionen des Gebäudes 2.000 kg · beheizte Fläche 100 m²
→ 20 kg CO₂/m²/Jahr · Einstufung: 17 bis unter 22 kg CO₂/m²/Jahr · CO₂-Kosten 300,00 €
```

- **The Einstufung is printed as its intensity band, not as a step number.** `Co2Step` carries
  `max_intensity_exclusive` and `landlord_share_percent` and **no ordinal**; the band is derivable
  (previous step's bound → this step's bound), a step number would be invented. If the Anlage's own
  numbering is wanted on the page it is transcribed into `packages/rules-store` first — **not** counted
  off the tuple index.
- `total_co2_kg`, `co2_cost` and `heated_area_sqm` are engine inputs today and reach `Co2Result`
  nowhere; they must be carried on the result, for the same drift reason as everything else here.

### 6 — M2: every `Rechtsstand` names its statute

**Presentation only. Nothing in `packages/rules-store` changes and no resolution changes.**

The footer prints `Rechtsstand 03/1989 · Rechtsstand 01/2009 · Rechtsstand 01/1981 · Rechtsstand
01/2023` — four bare dates. `HeizkostenV` appears nowhere on the page. `Rechtsstand 01/1981` is the
Gradtagszahl table and no reader could know that; worse, an unlabelled 1981 date next to three others
reads as *law from 1981*, which is exactly what the degree-day table is not.

Required form — label **·** stamp, one per resolved rule, in resolution order:

```
Rechtsstand: § 7 Abs. 1 HeizkostenV 03/1989 · § 9 Abs. 2 HeizkostenV 01/2009 ·
Gradtagszahlen-Promilletabelle (VDI-Konvention, keine Rechtsnorm) 01/1981 ·
§ 5 Abs. 1 i. V. m. Anlage CO2KostAufG 01/2023 · Erstellt mit Lokara.
```

- The three statutory labels are **verbatim `ResolvedRule.source`** from the store — they already read
  `§ 7 Abs. 1 HeizkostenV`, `§ 9 Abs. 2 HeizkostenV`, `§ 5 Abs. 1 i. V. m. Anlage CO2KostAufG`. Nothing
  is invented; the label was simply thrown away by the caller.
- The degree-day `source` is *"Anerkannte Gradtagszahlen-Promilletabelle (VDI) — verify before
  production"*. The part after the em dash is an internal marker: **it never renders**, and the
  qualifier *(VDI-Konvention, keine Rechtsnorm)* renders in its place. The label is fixed copy in the
  template layer, listed here so it is not re-derived elsewhere.
- Mechanically: `StatementData.rechtsstaende` becomes label+stamp pairs instead of bare stamps, and the
  caller (`demo.py`, later the API) builds them from the `ResolvedRule`s it already holds. No engine
  change, no rules change — which is why this ships on its own.

### Typographic floor for legally required disclosure

Measured on the current page (WCAG ratios against the `docs/05` tokens): the Umlageschlüssel +
Gesamtbemessung line (`.key-label`) is **8,5 pt Slate on Mint = 4,81:1** — AA with 0,31 to spare, and
the **smallest, lowest-contrast text on the page**. Legally required content must not be the hardest
thing to read; a disclosure the tenant squints at is a disclosure in form only. Contrast of the
available token pairs:

| Pair | Ratio | Use |
| --- | --- | --- |
| Petrol Ink on Mint | **13,91** | legally required text on a tinted surface — default |
| Forest Deep on Mint | **10,01** | legally required text, secondary emphasis |
| Petrol Ink on Paper | **15,72** | legally required text on the page ground |
| Slate on Paper | **5,44** | non-legal secondary framing text only |
| Slate on Mint | **4,81** | ⚠️ **not permitted** for legally required text |
| Lokara Grün on Mint | 5,89 | decorative per `docs/05` — never body text |

The floor, for everything this file marks as legally required (the four BGH minimums, every disclosure
in this section, the `Rechtsstand` footer):

1. **Size ≥ 9 pt**, and never smaller than the smallest non-legal text on the page. The existing 8,5 pt
   `.key-label` and `tfoot .foot-note` come up to 9 pt with it — same class, same rule.
2. **Contrast ≥ 7:1** on its own background → Petrol Ink or Forest Deep. Slate is retired from
   legally required text; it keeps its role for non-legal secondary text on Paper.
3. **Line-height ≥ 1,4**, weight ≥ 400, no all-caps and no negative letter-spacing at these sizes.
4. Numeric columns keep `font-variant-numeric: tabular-nums` so figures align for comparison.
5. Tokens only (`docs/05`) — no ad-hoc hex, and no new colour is needed for any of the above.

Checkable in `packages/pdf/tests/` against `statement_html()`: the classes carrying legal disclosure
are enumerated in the test, and each must declare a size ≥ 9 pt and an ink/forest colour token. This is
a stylesheet-level assertion, deliberately not a pixel one.

### Gaps — not invented here

- **The unit of the heating-consumption Bemessung.** `HeatingUnit.heat_consumption` is a bare `Decimal`
  documented as "heat-meter units": at a Wärmemengenzähler that is **kWh**, at a Heizkostenverteiler it
  is dimensionless **HKV-Einheiten**, and nothing in the input distinguishes them. This is the same gap
  the NK `CONSUMPTION` reference total is blocked on, and the same resolution applies: **no
  Gesamtbemessung and no Bemessung column for `Verbrauch Heizung` until the unit is carried.** Warm
  water is *not* affected — `ww_consumption_m3` / `volume_m3` fix m³ by type, `CANONICAL_UNITS` maps
  `WARM_WATER → CUBIC_METRE`, and § 9's formula is defined per m³; that unit is derived, not guessed.
  **Sub-question for the lead, deliberately left open:** whether the withholding rule extends to a
  *unit-free* figure (`Gesamtbemessung 1.000`, no unit), which states nothing false but invites an
  assumption. Until it is answered, the conservative reading applies — withhold.
- **German spellings of `MeasurementUnit`** (display copy, no legal value, no `Rechtsstand`; this
  closes the *spellings* half of the `CONSUMPTION` gap recorded above — the *plumbing* half stays open):

  | `MeasurementUnit` | Rendered | Note |
  | --- | --- | --- |
  | `KWH` | `kWh` | Wärmemengenzähler; the § 9 energy denominator |
  | `CUBIC_METRE` | `m³` | Wasserzähler |
  | `HKV_UNITS` | `Einheiten (Heizkostenverteiler)`, short `HKV-Einheiten` | dimensionless allocator reading |

- **Zählerstände (start/end readings) are not specified here and must not be improvised.** HeizkostenV
  gives the tenant a right to check the readings, and the gap is listed under *"Also missing from the
  tenant document"* — but the engine takes a *resolved consumption value*, not readings: there is no
  `meter_id`, no start, no end anywhere in `HeatingInput`. Rendering readings therefore needs a data
  path that does not exist (M3's Zähler slice), plus a decision on where the consistency check
  `Ende − Anfang == Verbrauch` lives. Named, not designed.
- **CO₂ intensity over a non-annual period.** `split_co2_cost` divides `total_co2_kg` by area with no
  pro-rating, while the Einstufung bands are *per year*. For a short (interim) or long period the
  intensity — and therefore possibly the step — is off. Not touched by this spec; recorded in the open
  questions below so it is not discovered on a real statement.
- **§§ 7/8 with different shares for heating and warm water** — see item 2; the input cannot express it
  today.

### Proposed implementation split

Recorded here because the seams are a property of the spec, not of a sprint. **Five slices**; four are
needed for the six items above, the fifth unblocks the one column they cannot ship.

| # | Lands | Lane | Independent? |
| --- | --- | --- | --- |
| 1 | `Rechtsstand` labels (item 6) | `app-implementer` (`packages/pdf/src`) | yes |
| 2 | Typographic floor for legal disclosure | `app-implementer` (`packages/pdf/src`) | yes — but **before** 4 |
| 3 | `HeatingResult` carries its intermediates (+ `Co2Result` Berechnungsgrundlagen, + § 9b in the degree-day `source`) | `engine-implementer` (`packages/{heating-engine,rules-store}/src`) | yes |
| 4 | Blocks A / B / C render (items 1–5) | `app-implementer` (`packages/pdf/src`) | **strictly after 3** (and after 2) |
| 5 | `MeasurementUnit` carried meter → statement; `Verbrauch Heizung` Bemessung column; NK `CONSUMPTION` reference total | `engine-implementer` then `app-implementer` | yes — strictly before the heating-consumption column |

Slice 3 is **deliberately not demo-visible**; that is the cost of the seam, and it is the right cost.
The alternative — pairing each disclosure with the fields it needs — means four separate edits to the
same dataclass and four fixture rewrites, with the tree in a half-carried state in between.

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
- [ ] Exact **Vorauszahlung → Saldo** block wording and arithmetic — **blocked on M6** (the ledger
      supplies the *geleistete* figure; `advance × months` is rejected, see "#4 is blocked on the M6
      ledger, by decision")
- [x] Which reference totals accompany each allocation key → **"Reference totals (Gesamtbemessung)"**
      above. One open sub-question remains: the **unit** of a `CONSUMPTION` total (see the gap there).
- [x] Heating: how consumption values and the CO₂ split are presented to the tenant →
      **"Heizkostenabrechnung — the heating table's disclosure"** above (Umlageschlüssel +
      Gesamtbemessung per column, §§ 7/8, § 9, Gradtagszahlen, § 7 Abs. 3 CO2KostAufG). Still open:
      **the CO₂-Vermieteranteil as a visible row** in the heating table, which the footer reword is
      standing in for; and the sub-questions that section names —
      **the unit of the heating-consumption Bemessung** (withhold vs. unit-free figure),
      **Zählerstände** (no data path into the engine),
      **CO₂ intensity over a non-annual period** (no pro-rating in `split_co2_cost`),
      **§§ 7/8 with different shares for heating and warm water** (not expressible in the input)
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
