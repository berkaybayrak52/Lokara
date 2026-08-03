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

| # | Requirement | First render |
| --- | --- | --- |
| 1 | **Zusammenstellung der Gesamtkosten** (per cost type) | ✅ |
| 2 | **Angabe + Erläuterung des Verteilerschlüssels** | ✅ — e.g. "Wohnfläche (m²·Tage)" |
| 3 | **Berechnung des Anteils des Mieters** | ✅ — day-weighted, cent-exact |
| 4 | **Abzug der geleisteten Vorauszahlungen** → **Saldo** | ❌ **missing** |

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
- ~~**Reference totals so the share is verifiable**~~ — **specified below** ("Reference totals
  (Gesamtbemessung)"); one per allocation key, each with its own unit. Not yet rendered.
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
- [ ] Heating: how consumption values and the CO₂ split are presented to the tenant
- [ ] Required legal notices (§556 frist, Einwendungsfrist, disclaimer placement)
- [ ] BetrKV cost-type catalogue + default keys + non-umlagefähig flags
- [ ] A **worked example** with real numbers → becomes the golden fixture for the document layer

## Interim framing for the 06.08 pitch

The current PDF is the **landlord's calculation view**, and it's honest to present it as such:

> *"This is the landlord's calculation view — every party, reconciling to the cent. The tenant letter,
> with advance payments and the resulting balance, is the next document off the same engine."*

True, and it reads as roadmap rather than gap. Do **not** present it as the document a tenant receives.
