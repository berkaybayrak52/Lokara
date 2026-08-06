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
| `CONSUMPTION` | the metered value (already period-resolved upstream — **no day weighting**) | Σ weights | the key's own `MeasurementUnit`, compact spelling — `kWh` / `m³` / `HKV-Einheiten` ([how it gets there](#measurementunit-travels-with-the-value--the-plumbing-decision-slice-5)) | 1 |
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

### The gap this was blocked on — closed by slice 5

**Was:** the *unit* of a `CONSUMPTION` reference total was not derivable from the engine result.
`ConsumptionValue` (`nk-engine/inputs.py`) carried `unit_id`, `tenancy_id`, `value` — no unit of
measure — and `_ALLOCATION_KEY_LABELS` spelled `CONSUMPTION` as bare `"Verbrauch"` with no unit.
`MeasurementUnit` (`domain/meter.py`: `KWH`, `CUBIC_METRE`, `HKV_UNITS`) was the right type, but
nothing carried it from the meter into the statement and it had no German display spelling anywhere.
No `CONSUMPTION` reference total was specified and none was fixture-tested, because a guessed unit on
a Verbrauchsabrechnung is a defect that reaches a tenant.

**Now:** the unit is carried on `ConsumptionValue` and surfaced on `NkResult`, and the German
spellings are fixed. See *["`MeasurementUnit` travels with the value — the plumbing decision (slice
5)"](#measurementunit-travels-with-the-value--the-plumbing-decision-slice-5)* below, which also
records **why the resolution written here first — "the caller passes the display unit into
`StatementData` per cost" — was refined rather than implemented as written.**

## `MeasurementUnit` travels with the value — the plumbing decision (slice 5)

> **Rechtsstand 08/2026** (transcribed 06.08.2026, lead's decision of the same day). This is a
> **carrying/contract decision, not a calculation** — the same standing as the *"Heating table
> footer"* section: it introduces **nothing** into `packages/rules-store`, resolves **no** dated rule,
> and moves **no euro**. Every figure it lets onto the page is one the engine already divided by; all
> it adds is the unit that figure was always in. The legal purpose is BGH formal minimum **#2/#3** — a
> denominator a renter is meant to check has to be a *quantity*, and a quantity has a unit. The German
> display copy below is this file's ruling, per the lead's instruction of 06.08.2026. Standard caveat
> of this file applies (`docs/07`).

**The defect this closes, in one line:** a value travelled from the meter to the statement **without
its unit**, so the document could print the denominator only by guessing what it meant — and withheld
it instead (*"The withheld cell is a sentence, not a blank"*).

### 1 — The unit travels with the value, on the dataclass that carries the value

| Where | Field | Type |
| --- | --- | --- |
| `packages/heating-engine/.../inputs.py` → `HeatingUnit` | `heat_consumption_unit` | `MeasurementUnit \| None = None` |
| `packages/heating-engine/.../inputs.py` → `HeatingResult` | `heat_consumption_unit` | `MeasurementUnit \| None` (**required**, no default) |
| `packages/nk-engine/.../inputs.py` → `ConsumptionValue` | `measurement_unit` | `MeasurementUnit \| None = None` |
| `packages/nk-engine/.../inputs.py` → `NkResult` | `consumption_unit` | `MeasurementUnit \| None` (**required**, no default) |

**Why on the value's own dataclass, and not beside it.** The defect being closed *is* a value that
travelled without its unit. A side channel — a per-cost `dict[str, MeasurementUnit]` handed to
`StatementData` by the caller — reintroduces exactly that failure mode one layer up: the value and its
unit then arrive by two routes, and two routes can disagree. The disagreement is silent, survives
every integer-comparing test, and surfaces as a *wrong unit* on a Verbrauchsabrechnung, which is worse
than the withheld cell it replaced. Carrying the unit on the row that carries the number makes the
pair inseparable by construction.

> ⚠️ **This refines an earlier sentence of this file.** The *"Gap — not invented here"* note above
> proposed: *"the caller (which resolves meters) passes the display unit into `StatementData` per
> cost."* That resolution is **superseded**: the unit is carried on the **engine input** and
> *surfaced* on the **engine result**, so the renderer **reads** the unit off the result rather than
> being **told** it by a second party. Two reasons, both already rules of this file: the disclosure
> figures come from the engine result and never from something passed alongside it (the drift rule at
> the head of *"Heizkostenabrechnung — the heating table's disclosure"*), and a statement may not
> state a unit the engine did not divide in. Recorded as a refinement, with its reason, so the change
> of direction is visible rather than quietly applied.

**`MeasurementUnit` lives in `packages/domain`** (`lokara_domain.meter`), which both engines already
import; nothing about this crosses a purity boundary (`scripts/check_engine_purity.py` forbids an
engine importing `rules-store`, not `domain`).

**The input default is `None`, and that is a deliberate exception** to the carried-intermediates
rule *"every new field is required — no default value"*. That rule exists because a default lets a
caller silently omit a legally required disclosure figure. Here the omission is **not** silent: by
rule 3 below an absent unit propagates to the printed sentence *"ohne Maßeinheit — nicht
ausgewiesen"* plus its explaining paragraph. A default that lands the renter on an honest disclosure
is a different thing from a default that lands them on a blank. On the **result** the field keeps the
contract's rule and carries no default.

### 2 — One key, one unit; a mixed key is an input error

**All parties supplying a value for the same consumption key must agree on the unit.** Two or more
distinct units on one key → `HeatingInputError` / `NkInputError`. Never a silent pick, never a
majority vote, never "the first one wins".

**Why it is an error and not a display problem.** The Gesamtbemessung is a **sum**. `600 kWh + 250
HKV-Einheiten` is a number that means nothing, and BGH formal minimum #3 requires the denominator to
be *checkable* — a denominator that cannot lawfully be summed fails it before it is ever printed. A
statement that picked one of the two units would state a false unit for some parties' Bemessung and a
false total for all of them.

**And it is a real configuration, not a hypothetical.** `MeterKind.HEAT` covers **both** a building
Wärmemengenzähler counting kWh **and** flat Heizkostenverteiler counting dimensionless Einheiten —
`packages/domain/src/lokara_domain/meter.py` says exactly that, and `CANONICAL_UNITS` deliberately
gives `HEAT` no default unit for that reason. A building that swapped some flats' allocators for
heat-meters mid-modernisation produces this input.

Resolution, in the order the engine applies it:

| Heating — `HeatingResult.heat_consumption_unit` | |
| --- | --- |
| two or more distinct `heat_consumption_unit` values among `HeatingInput.units` | raise `HeatingInputError` (in `_validate`, i.e. **before** any branch runs — validation that depends on which branch ran can be skipped by an unrelated data problem) |
| `heat_fallback_to_area` is `True` (§ 9a Abs. 2) | `None` — see rule 4 |
| every unit that supplied a `heat_consumption` value carries a unit, and at least one unit carries one | that unit |
| otherwise | `None` — see rule 3 |

| NK — `NkResult.consumption_unit` | |
| --- | --- |
| two or more distinct non-`None` `measurement_unit` values in `NkInput.consumptions` | raise `NkInputError` |
| any row of `consumptions` carries no unit | `None` |
| exactly one distinct unit and no row missing it | that unit |
| `consumptions` is empty | `None` |

- **The two rules differ in one place, on purpose.** In heating, a unit with `heat_consumption=None`
  contributes **no measured value**: § 9a estimates it from the measured units, so the estimate is by
  construction in *their* unit and that row need not declare one. NK has no estimation branch — every
  `ConsumptionValue` row is a supplied value — so every row must carry the unit. The *mixing* check,
  by contrast, runs over **declarations** in both engines, including a heating unit with no reading:
  a declared kWh device in a building of HKV allocators makes next period's denominator unsummable
  and would label this period's estimate with the wrong unit.
- **`NkResult.consumption_unit` is one field because `NkInput.consumptions` is one flat tuple**,
  shared by every `CONSUMPTION` cost on the statement — "one key" is literally true today. **Named,
  not designed:** when a second, independently-metered consumption key becomes expressible, this
  field becomes a mapping keyed by that key's identity, and the reference-totals rule *"one per
  allocation key, and they are not interchangeable"* is what it has to satisfy.

### 3 — Absence propagates, and the withholding branch survives

**If any contributing value lacks a unit, the resolved unit for that key is `None`, and the renderer
withholds exactly as it does today.** The existing copy — the cell `ohne Maßeinheit — nicht
ausgewiesen` and the explaining paragraph beneath the column table — stays **byte-identical**, keeps
its place, and keeps a golden fixture that exercises it.

> **Lead, 06.08.2026:** *"The placeholder copy is good and should not simply vanish. If a building
> genuinely has no Maßeinheit recorded, the honest disclosure still has to appear — slice 5 removes
> the cause, not the branch."*

That is the whole shape of this slice: the demo building stops reaching the branch because it now
records its Maßeinheit (rule 6), and a building that records none still gets the sentence rather than
a blank, a dash or a zero. The fixture for the branch therefore moves off the demo composition onto a
deliberately unit-less one; it is not deleted, and none of its assertions is weakened.

### 4 — Under § 9a Abs. 2 the resolved unit is `None`, and that is *not* the withholding branch

When `heat_fallback_to_area` is `True`, no consumption Bemessung was applied at all: the pot went on
the area key. `HeatingLine.heat_consumption_weight` is already `None` in that branch for exactly that
reason, and `heat_consumption_unit` follows it — **`None` means "not applied", never "not carried"**,
the contract's own rule. A unit stated there would be the unit of a Bemessung that determined no euro.

The two `None`s never collide on the page, because the renderer branches on `heat_fallback_to_area`
**first**: that row then states `Wohnfläche (m²·Tage) — § 9a Abs. 2 HeizkostenV` and the
`36.500 m²·Tage` printed two rows above, and nothing is withheld (*"The `Verbrauch Heizung` row under
§ 9a Abs. 2"*). The withheld sentence and the § 9a row must stay distinguishable — they have
different causes, and one of them is a legal fact about the allocation.

### 5 — The open sub-question is answered: withhold

The gap note below (*"The unit of the heating-consumption Bemessung"*) left one sub-question open for
the lead: whether the withholding rule extends to a **unit-free figure** (`Gesamtbemessung 1.000`, no
unit), which states nothing false but invites an assumption. **Answered 06.08.2026: withhold.**

With rules 1–3 the unit is known whenever it exists, so the question now arises **only** where the
Maßeinheit genuinely is not recorded — and there the conservative reading the note already named is
the right one, for the reason it already gave: a bare `1.000` in a column headed *Gesamtbemessung*,
between two rows reading `36.500 m²·Tage` and `40 m³`, invites the renter to assume a unit, and the
two candidate units differ by three orders of magnitude in what they mean. The sub-question is
**closed**, not deferred.

### 6 — Which spelling goes where

Two forms of every unit, and they are not interchangeable.

| `MeasurementUnit` | Compact (a numeric cell) | Long (names the device) |
| --- | --- | --- |
| `KWH` | `kWh` | `Erfasster Wärmeverbrauch in kWh am Wärmemengenzähler` |
| `HKV_UNITS` | `HKV-Einheiten` | `Erfasster Wärmeverbrauch in Einheiten eines Heizkostenverteilers` |
| `CUBIC_METRE` | `m³` | — not reachable on the heating column, see below |

**The Bemessung cells use the compact form**, because they are numeric cells: `1.000 HKV-Einheiten`
sits in a column beside `36.500 m²·Tage` and `40 m³`, and the long form wraps a figure column into
prose. **The long form appears exactly once, in the `Verbrauch Heizung` Umlageschlüssel cell** —
naming the device is what BGH minimum #2 means by *Angabe **und Erläuterung** des Verteilerschlüssels*.
`Erfasster Wärmeverbrauch` alone says *what* was measured; `… in Einheiten eines
Heizkostenverteilers` says *by what*, and that is the difference between a renter who can check the
key and one who cannot.

Exact rendered German, settled here:

| Cell | Unit known | Unit not recorded (unchanged) |
| --- | --- | --- |
| Block B, `Verbrauch Heizung` **Umlageschlüssel** | `Erfasster Wärmeverbrauch in Einheiten eines Heizkostenverteilers` (`HKV_UNITS`) · `Erfasster Wärmeverbrauch in kWh am Wärmemengenzähler` (`KWH`) | `Erfasster Wärmeverbrauch` |
| … with a Nutzerwechsel | the same, then ` (Nutzerwechsel: Gradtagszahlen)` | `Erfasster Wärmeverbrauch (Nutzerwechsel: Gradtagszahlen)` |
| Block B, `Verbrauch Heizung` **Gesamtbemessung** | `1.000 HKV-Einheiten` | `ohne Maßeinheit — nicht ausgewiesen` |
| Block B, party table **column header** | `Verbrauch Heizung` | column absent |
| Block B, party **Bemessung** cell | `600 HKV-Einheiten` · `146,25 HKV-Einheiten` | cell absent |
| NK cost header **Umlageschlüssel** (`CONSUMPTION`) | `Verbrauch (m³)` · `Verbrauch (kWh)` · `Verbrauch (HKV-Einheiten)` | `Verbrauch` |
| NK cost header **Gesamtbemessung** | `Gesamtbemessung: 40 m³` | no reference total printed |

- **No parentheses in the long form**, so it composes with the `(Nutzerwechsel: Gradtagszahlen)`
  parenthetical without producing a second bracket or a nested one. That constraint is what picked
  *"in kWh am Wärmemengenzähler"* over *"(kWh, Wärmemengenzähler)"*.
- **The party Bemessung cells repeat the unit**, exactly as the `Verbrauch Warmwasser` column already
  does (`20 m³`, `rd. 5,95 m³`). One idiom, two columns; a figure column whose unit appears only in
  its footer is a column a renter has to reconstruct.
- **The withheld branch keeps the bare key label.** Naming a device in the Umlageschlüssel cell while
  the cell beside it says *ohne Maßeinheit* would be the page contradicting itself in one row.
- **`CUBIC_METRE` gets no long form and no heating spelling.** A m³ device is not a heat meter:
  `MeterCreate._unit_matches_kind` (`apps/api/.../schemas.py`) already rejects `HEAT` + `CUBIC_METRE`,
  so the combination cannot reach an engine. Inventing a third spelling for a rejected configuration
  is inventing copy for a case that does not exist.
- **The NK label names no device**, and that is deliberate: outside the heating column the
  `MeasurementUnit` does **not** determine the device — `m³` is a Kalt- *or* a Warmwasserzähler — so
  a device name there would be a fact the data does not carry. In the heating column the pair
  (`MeterKind.HEAT`, unit) *does* determine it, which is precisely the point `docs/02` →
  *"Meters: `MeterKind` and `MeasurementUnit` are independent axes"* makes.
- **Scope: this table is the statement document's copy.** The meter screen's `unit_symbol`
  (`apps/api/.../routers/meters.py`, `UNIT_SYMBOLS`) spells `HKV_UNITS` as bare `Einheiten` beside a
  device whose type is on the same screen; that is a different surface with a different context and
  is **not** harmonised by this table.
- **Warm water is unaffected, and is derived rather than guessed.** `ww_consumption_m3` /
  `volume_m3` fix m³ by type, `CANONICAL_UNITS` maps `WARM_WATER → CUBIC_METRE`, and § 9's formula is
  defined per m³. The `Erfasster Warmwasserverbrauch (m³)` copy does not change.

### 7 — The demo values this is worked against

Verified 06.08.2026 against `packages/adapters/src/lokara_adapters/meter.py` → `_SPEC`, which is the
demo building's register values:

| Meter | Unit | Opening → closing | Verbrauch |
| --- | --- | --- | --- |
| `met_heat_a` | `HKV_UNITS` | 1200 → 1800 | **600** |
| `met_heat_b` | `HKV_UNITS` | 3400 → 3650 | **250** |
| `met_heat_c` | `HKV_UNITS` | 880 → 1030 | **150** |
| `met_heat_main` | `KWH` | 148500 → 168500 | 20.000 (the § 9 denominator, not a Bemessung) |

- Flat heat allocators, `MeasurementUnit.HKV_UNITS`: **600 / 250 / 150**, Σ **1.000** → the cell reads
  **`Gesamtbemessung: 1.000 HKV-Einheiten`**, and after the Nutzerwechsel split the party column reads
  `600` · `146,25` · `103,75` · `150` HKV-Einheiten, Σ `1.000`.
- Flat warm water, `CUBIC_METRE`: 20 / 12 / 8, Σ **40 m³** — unchanged, already on the page.
- **The demo's Σ 1.000 could not have been kWh anyway.** The building's own meter reads 20.000 kWh
  over the same period; three flats whose devices counted kWh would sum to roughly that, not to
  1.000. The fixture was HKV-Einheiten all along — it simply could not say so.

⚠️ **Flagged, not resolved here:** `docs/06` → *"Scenario 2 — the fuel, the emissions and the CO₂
price"* describes the demo building as having *"one Wärmemengenzähler per unit, one shared
warm-water meter"*. Both halves disagree with `_SPEC` (the flats carry **Heizkostenverteiler**, and
each flat has its **own** warm-water meter beside the building one), and `DEMO-RUNBOOK.md` →
*"Screen 4 — Zähler"* agrees with `_SPEC`, not with `docs/06`: *"the building's **Wärmemengenzähler**
(20.000 kWh) and one flat's **Heizkostenverteiler** (600 Einheiten)"*. The device type is a fixture
fact, not a legal one, and the code, the runbook and the arithmetic above all point one way — but per
`CLAUDE.md` the contradiction is **reported to the lead, not silently rewritten** in either
direction.

### 8 — What this section does not do

- **It does not print Zählerstände.** Start/end readings remain the separate, unspecified gap below;
  the engine still takes a resolved consumption value and knows of no reading at all.
- **It does not touch the § 9 energy denominator.** `total_energy_kwh` is kWh by type and by statute
  and was never part of this gap.
- **It moves no euro.** Every Bemessung it lets onto the page is a weight the engine already
  allocated by; the party totals, the pots and the canonical €1.200 allocation are byte-identical.

## Heating table footer — the figure is the Gesamtkosten, not the column's sum

> **Rechtsstand 08/2026** (transcribed 03.08.2026). A **document-copy rule**: it introduces nothing
> into `packages/rules-store` and reads no dated rule. The one legal value involved — the CO₂ split —
> is resolved by the heating engine from the store and already carries its own `Rechtsstand` on the
> page. The statutory reference in the copy below was checked against the consolidated text of the
> CO2KostAufG as of 08/2026; standard caveat of this file applies (`docs/07`).

**The defect.** The heating `tfoot` currently reads *"Summe Heiz- und Warmwasserkosten (inkl.
CO₂-Vermieteranteil, stimmt centgenau mit den Gesamtkosten überein)" — 10.300,00 €*. The sentence is
literally true: 10.300,00 € **is** the Gesamtkosten. But it sits under a column of four party amounts
that sum to **10.142,92 €** (5.603,97 + 1.495,53 + 1.281,10 + 1.762,32). The 157,08 € difference is the
CO₂-Vermieteranteil, which is deducted **before** the renter-facing split (§ 7 Abs. 1 CO2KostAufG) and
is **not a row in the table**. So the column visibly does not add up while the footer appears to assert
that it does. (Figures re-based 05.08.2026 with the CO₂ fixture — see *"The worked example"* below;
the defect and the wording that fixes it are unchanged.)

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
Summe der oben ausgewiesenen Anteile: 10.142,92 €. Die Differenz von 157,08 € ist der
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

Field-by-field, that table is resolved in **"The carried-intermediates contract (slice 3)"** below —
names, types, demo values, and which statute makes each one required rather than merely useful.

**Consequence:** the renderer *cannot* show any of this today, and no amount of template work changes
that. The engine result must carry it first — a pure-package change under CLAUDE.md rule 1
(framework-free, golden fixtures, `mypy --strict`, `Decimal`/cents), then a template change. The
proposed split at the end of this section is built on that seam.

**A rule the template must not break to get around it:** the disclosure figures come from the **engine
result**, never from the engine *input* passed alongside it. Two sources drift; the page would then
state a ratio that was not the one applied. This is the same rule the heating footer already follows
("Both euro figures come from the engine result … Nothing here is a new calculation").

### The worked example (the demo building, 01.01.–31.12.2025)

Every figure below is the real output of the two engines on the demo inputs. It is the source for the
golden fixtures of the slices below.

> **⚠️ Re-based 05.08.2026 — the CO₂ figures of the demo were wrong on their face.** `2.000 kg` and
> `300,00 €` implied **150 €/t** (2025: 55,00 € + USt = 65,45 €/t) and, against the demo's own
> 20.000 kWh, **0,1 kg CO₂/kWh** — about half of Erdgas. The corrected fixture, its fuel and the
> statutory figures it was checked against: `docs/06` → *"Scenario 2 — the fuel, the emissions and the
> CO₂ price"* and `docs/03` → *"Where `total_co2_kg` and `co2_cost` come from"*. Because the
> CO₂-Vermieteranteil is deducted **before** the renter-facing split, every heating euro below moved;
> the **585/415 ‰ ratio, every Bemessung and the canonical €1.200 NK example did not**.

Building: A 50 m², B 30 m², C 20 m²; Bernd Muster leaves B on 30.06.2025 (B vacant Jul–Dec).
Gesamtkosten Heizung + Warmwasser **10.300,00 €**; Gesamtenergie **20.000 kWh** Erdgas; Warmwasser
**40 m³** gemessen; Wärmeverbrauch A/B/C **600 / 250 / 150** (Anzeige der Erfassungsgeräte);
Warmwasserverbrauch A/B/C **20 / 12 / 8 m³**; CO₂ **4.000 kg**, CO₂-Kosten **261,80 €**.

| Stage | Figures |
| --- | --- |
| CO₂ (§ 7 CO2KostAufG) | Intensität 4.000 kg ÷ 100 m² = **40 kg CO₂/m²/a** → Vermieteranteil **60 %** = **157,08 €**, Mieteranteil **104,72 €** |
| umlagefähig nach Abzug | **10.142,92 €** |
| § 9 Trennung | Q(WW) = 2,5 × 40 × (60 − 10) = **5.000 kWh** von 20.000 kWh → Warmwasser **2.535,73 €**, Heizung **7.607,19 €** |
| §§ 7/8 bei 30/70 | Heizung: Grund **2.282,16 €** / Verbrauch **5.325,03 €** · Warmwasser: Grund **760,72 €** / Verbrauch **1.775,01 €** |
| Grundkosten-Bemessung | A 18.250 · B-Mieter 5.430 · B-Vermieter 5.520 · C 7.300 · **Σ 36.500 m²·Tage** |
| Wärmeverbrauchs-Bemessung | A 600 · B-Mieter 146,25 · B-Vermieter 103,75 · C 150 · **Σ 1.000 HKV-Einheiten** (die Maßeinheit wird seit Slice 5 mitgeführt) |
| Warmwasser-Bemessung | A 20 · B-Mieter 5,950684… · B-Vermieter 6,049315… · C 8 · **Σ 40 m³** |
| Gradtagszahlen B | 01.01.–30.06. **585 ‰ von 1.000 ‰** · 01.07.–31.12. **415 ‰ von 1.000 ‰** |
| Tage B (Grund + WW) | **181 von 365** bzw. **184 von 365** |

Party totals: 5.603,97 / 1.495,53 / 1.281,10 / 1.762,32 € — Σ 10.142,92 €, plus the 157,08 €
CO₂-Vermieteranteil = 10.300,00 €.

Unit B's heating-consumption cells — the figures `DEMO-RUNBOOK.md` and `docs/06` point at — are
**778,79 € / 552,47 €**, still exactly 585 : 415.

### 1 — Umlageschlüssel and Gesamtbemessung per money column

The heating table's four money columns **do not share a denominator**, and that is the whole reason the
NK solution (one label appended to the cost header row) does not transfer:

| Money column | Umlageschlüssel | Gesamtbemessung (demo) |
| --- | --- | --- |
| Grundkosten Heizung | Wohnfläche (m²·Tage) — § 7 Abs. 1 HeizkostenV | 36.500 m²·Tage |
| Verbrauch Heizung | Erfasster Wärmeverbrauch in Einheiten eines Heizkostenverteilers (Nutzerwechsel: Gradtagszahlen) | 1.000 HKV-Einheiten — **withheld** where a building records no Maßeinheit, see *"The withheld cell is a sentence, not a blank"* below |
| Grundkosten Warmwasser | Wohnfläche (m²·Tage) — § 8 Abs. 1 HeizkostenV | 36.500 m²·Tage |
| Verbrauch Warmwasser | Erfasster Warmwasserverbrauch (m³) | 40 m³ |

**All four rows render. The withholding is of one cell, never of a row.**

> **Rechtsstand 08/2026** (transcribed 05.08.2026, after `statement-reviewer` finding **F1**). A
> **document-copy rule**: it introduces nothing into `packages/rules-store`, resolves no rule and
> computes nothing. The statutory references are the ones the table above already carries.

The first render of Block B dropped the whole `Verbrauch Heizung` row, and the consequence was worse
than the gap it was avoiding: the **largest pot on the page** — 5.325,03 €, **52 %** of the umlagefähige
Kosten — then had **no Umlageschlüssel named anywhere**, in a block titled *Bemessungsgrundlagen*. Four
money columns, three rows. A renter comparing the two cannot tell whether the column was forgotten or
allocated by a key nobody wrote down.

What was not derivable when this was written is the **unit** of the heating-consumption Bemessung (kWh
at a Wärmemengenzähler, dimensionless HKV-Einheiten at a Heizkostenverteiler). That blocked **one
cell**: the Gesamtbemessung. It never blocked the Umlageschlüssel, which is a name, not a figure, and
which is BGH formal minimum **#2** in its own right.

**Slice 5 carries the unit** (*"`MeasurementUnit` travels with the value"* above), so on a building
that records its Maßeinheit the cell now prints its figure. The withholding branch **stays** for a
building that records none, with its copy unchanged — the cause is removed, not the branch.

#### The withheld cell is a sentence, not a blank

**When this branch renders (updated 06.08.2026):** only where the Maßeinheit of the heat-recording
devices is **genuinely not recorded** — i.e. `HeatingResult.heat_consumption_unit is None` while
`heat_fallback_to_area` is `False`. Slice 5 removed the *cause* on any building that records its
devices (*"`MeasurementUnit` travels with the value"*), and deliberately kept the *branch*: an
unrecorded unit is an honest disclosure, not a blank. Every word below is unchanged.

The cell prints, verbatim:

```
ohne Maßeinheit — nicht ausgewiesen
```

and directly beneath the column table, once, whenever that row rendered in this form:

```
Für den erfassten Wärmeverbrauch wird keine Gesamtbemessung ausgewiesen: Die Maßeinheit der
Erfassungsgeräte (kWh oder Einheiten eines Heizkostenverteilers) liegt dieser Abrechnung nicht vor.
Der Verbrauchsanteil wurde gleichwohl nach den erfassten Werten verteilt.
```

Every word of the cell is carrying something:

- **It contains no digit and no dash used as a figure.** `—`, `0`, `–` or an empty cell all read as
  *zero* in a numeric column, and a zero denominator is not merely wrong, it is unreadable — it would
  make the renter's own share look undefined.
- **`nicht ausgewiesen`** is an act of the landlord's, in the same register § 7 Abs. 3 CO2KostAufG uses
  for *ausweisen*. It says *this was not stated*, which is true, rather than *there is none*, which is
  false: the denominator exists and the engine divided by it.
- **`ohne Maßeinheit`** is the reason, in two words, and it is the only reason that makes a figure
  unprintable rather than merely absent. Without it the cell is exactly the *"omission a renter would
  take for an error"*.
- **The second sentence of the note is not optional.** Without it a renter can read the withheld
  denominator as a withheld *method* and conclude the column was not consumption-allocated at all —
  which would be a § 7 Abs. 1 HeizkostenV defect rather than a display gap.
- The note says **nothing** about who should have supplied the unit and asserts **no** right of
  inspection. Both would be claims this document has not transcribed.

**Rejected: printing the unit-free figure `1.000`.** A bare `1.000` in a column headed
*Gesamtbemessung*, between two rows reading `36.500 m²·Tage` and `40 m³`, invites the renter to assume
a unit, and the two candidate units differ by three orders of magnitude in what they mean. The
withholding stays; only its wording is fixed here. **This was the open sub-question for the lead, and
it is answered — withhold** (06.08.2026, *"`MeasurementUnit` travels with the value"* → rule 5). With
the unit now carried, the branch is reached only where no Maßeinheit is recorded at all, and there
this reasoning is the whole of it.

#### The `Verbrauch Heizung` row under § 9a Abs. 2 — it states Wohnfläche, not Wärmeverbrauch

`heat_fallback_to_area` means the consumption key **was replaced**: more than 25 % of the area had no
reading and § 9a Abs. 2 HeizkostenV put that pot on the area key. Then the applied Umlageschlüssel of
the `Verbrauch Heizung` column **is Wohnfläche (m²·Tage)**, its denominator is the `36.500 m²·Tage`
already printed two rows above, and there is no measurement-unit problem at all — the withholding
reason has evaporated with the key it applied to.

| `heat_fallback_to_area` | Umlageschlüssel cell | Gesamtbemessung cell |
| --- | --- | --- |
| `False` | `Erfasster Wärmeverbrauch` (+ `(Nutzerwechsel: Gradtagszahlen)`, see below) | `ohne Maßeinheit — nicht ausgewiesen` |
| `True` | `Wohnfläche (m²·Tage) — § 9a Abs. 2 HeizkostenV` | `36.500 m²·Tage` |

- The citation in the fallback branch is **§ 9a Abs. 2**, not § 7 Abs. 1: § 7 Abs. 1 is why there is a
  consumption pot at all, § 9a Abs. 2 is why *this* pot was distributed by area. Naming § 7 Abs. 1
  there would send a renter to a paragraph that does not contain the rule that decided their share.
- The same rule applies to the **`Verbrauch Warmwasser`** row under `ww_fallback_to_area`, which 4a
  already put on `Wohnfläche (m²·Tage)`: it carries the same **`— § 9a Abs. 2 HeizkostenV`** citation,
  for the same reason. The `.note` at the foot of the section says the same thing in prose; the row is
  where a renter looks for the key of *their* column, and the two must agree.
- **`(Nutzerwechsel: Gradtagszahlen)` renders only when a Nutzerwechsel happened** — i.e. exactly when
  Block C renders its ‰ lines. On a building with one party per unit the parenthetical names a method
  that was not applied, which is the rule this whole section is built on.

**The two Wohnfläche rows carry their citations.** `— § 7 Abs. 1 HeizkostenV` on *Grundkosten Heizung*,
`— § 8 Abs. 1 HeizkostenV` on *Grundkosten Warmwasser*, exactly as the table above assigns them. The
first render dropped both. They are separate paragraphs for separate pots (see item 2), and a renter
who wants to check *why* their base costs go by area has nowhere else on the page to look —
`Rechtsstand: § 7 Abs. 1 HeizkostenV 03/1989` in the footer dates a rule, it does not attach it to a
column. **`Verbrauch Warmwasser` carries no citation** in the measured branch, because the table above
assigns it none; § 8 Abs. 1 governs that split too, but transcribing a citation the spec did not write
is inventing law, and the place to fix it is this table, not the renderer.

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
− CO₂-Vermieteranteil (§ 7 Abs. 1 CO2KostAufG)                          157,08 €
= umlagefähige Kosten                                                10.142,92 €

§ 9 HeizkostenV — Trennung von Heizung und Warmwasser
Q(WW) = 2,5 kWh/(m³·K) × 40 m³ × (60 °C − 10 °C) = 5.000 kWh von 20.000 kWh Gesamtenergie
→ Warmwasser 2.535,73 € · Heizung 7.607,19 €

§§ 7, 8 HeizkostenV — Grund- und Verbrauchskosten: angewendet 30 % Grundkosten / 70 % Verbrauch
(zulässiger Rahmen: 50 % bis 70 % Verbrauchskosten, § 7 Abs. 1 HeizkostenV)
Heizung:     Grundkosten 2.282,16 € · Verbrauchskosten 5.325,03 €
Warmwasser:  Grundkosten   760,72 € · Verbrauchskosten 1.775,01 €
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

The demo building, which records its Maßeinheit (slice 5):

```
Bemessungsgrundlagen

Spalte                    Umlageschlüssel                              Gesamtbemessung
Grundkosten Heizung       Wohnfläche (m²·Tage) — § 7 Abs. 1 Heizkos…   36.500 m²·Tage
Verbrauch Heizung         Erfasster Wärmeverbrauch in Einheiten        1.000 HKV-Einheiten
                          eines Heizkostenverteilers
                          (Nutzerwechsel: Gradtagszahlen)
Grundkosten Warmwasser    Wohnfläche (m²·Tage) — § 8 Abs. 1 Heizkos…   36.500 m²·Tage
Verbrauch Warmwasser      Erfasster Warmwasserverbrauch (m³)           40 m³

Partei                             Fläche·Tage  Verbrauch Heizung  Verbrauch Warmwasser
Wohnung A — Anna Beispiel               18.250   600 HKV-Einheiten                20 m³
Wohnung B — Bernd Muster (Ausz…)         5.430   146,25 HKV-Einh…           rd. 5,95 m³
Wohnung B — Leerstand ab 01.07.…         5.520   103,75 HKV-Einh…           rd. 6,05 m³
Wohnung C — Clara Vorlage                7.300   150 HKV-Einheiten                 8 m³
Gesamtbemessung                         36.500  1.000 HKV-Einheiten               40 m³

Gerundete Bemessungen sind mit rd. gekennzeichnet; gerechnet wird mit dem exakten Wert, sodass eine
Nachrechnung aus dem angezeigten Wert um wenige Cent abweichen kann.
```

A building that records **no** Maßeinheit — the branch slice 5 kept (*"The withheld cell is a
sentence, not a blank"*). Only the two heat cells differ; the `Verbrauch Heizung` Bemessung column is
absent from the party table, and the note sits between the two tables:

```
Verbrauch Heizung         Erfasster Wärmeverbrauch                     ohne Maßeinheit —
                          (Nutzerwechsel: Gradtagszahlen)              nicht ausgewiesen

Für den erfassten Wärmeverbrauch wird keine Gesamtbemessung ausgewiesen: Die Maßeinheit der
Erfassungsgeräte (kWh oder Einheiten eines Heizkostenverteilers) liegt dieser Abrechnung nicht vor.
Der Verbrauchsanteil wurde gleichwohl nach den erfassten Werten verteilt.
```

(The `§ 7 Abs. 1 Heizkos…` above is this file's column width, not an ellipsis on the page — the row
prints the citation in full.)

- The token stays **`Bemessung` / `Gesamtbemessung`**, matching the NK table — same concept, same word.
- The de-scaling rule of the reference-totals section applies unchanged: `36.500`, never `3.650.000`;
  the **sum** is de-scaled once, never per line.
- **Invariant, asserted over rendered text:** each Bemessung column's printed values sum exactly to the
  printed Gesamtbemessung of that column. Same invariant as the NK reference totals.
- **The `Verbrauch Heizung` row is always in the column table.** Its Gesamtbemessung cell and its
  party-table Bemessung column are present when the Maßeinheit is recorded (slice 5) and withheld
  together when it is not — the row itself states the key that was applied (BGH #2) in either case.
  See *"All four rows render"* above for the copy and *"The `Verbrauch Heizung` row under § 9a Abs. 2"*
  for the branch where the consumption key was replaced and nothing is withheld at all.
- **The party table's Bemessung columns follow the same order**: `Fläche·Tage` (the denominator of
  both Grundkosten columns), then `Verbrauch Heizung`, then `Verbrauch Warmwasser`. Each column is
  present exactly when its Gesamtbemessung is.
- **Row order is the money table's column order** — Grundkosten Heizung, Verbrauch Heizung, Grundkosten
  Warmwasser, Verbrauch Warmwasser. A renter reads across the money table and down this one; a
  different order makes them search.

#### Display rounding of a fractional Bemessung (new — the NK weights were all integral)

`5,950684931506849…` is a real Bemessung (12 m³ × 181/365). The NK section never needed a rule because
every NK weight is an integer. The rule:

1. Display with **at most 2 decimals**, trailing zeros suppressed (`20`, not `20,00`; `5,95`).
2. Round the values of a column with **largest remainder** across that column's parties, so the printed
   values sum exactly to the printed Gesamtbemessung — the same idiom the engine uses for cents
   (`docs/03` → Rounding), ties by stable party order. Rounding each value independently breaks the
   invariant above on a document that is supposed to add up.
3. Where a value was **derived** rather than measured (an apportionment at a Nutzerwechsel), the
   derivation is printed in Block C. The 2-decimal figure is the readable one; the derivation shows
   the operands, so the tenant can reproduce it.
4. A rounded figure is marked **`rd.`** and the rounding is disclosed **once**, in one place. Rules
   below.

#### The rounding is disclosed — `rd.`, one sentence, and an operator that is the operation

> **Rechtsstand 08/2026** (transcribed 05.08.2026, after `statement-reviewer` finding **F2**). A
> **document-copy rule**: nothing enters `packages/rules-store`, no rule is resolved, no figure moves.
> The legal purpose is BGH minimum **#3** — a *Berechnung* the renter re-performs — and the copy
> ruling is this file's, per the lead's instruction of 05.08.2026.

**The three defects, and the one the lead already ruled on.** Block C printed
`12 m³ × 181 von 365 Tagen = 5,95 m³`.

1. `12 × 181 ÷ 365 = 5,9506849…`, so **`=` states a false identity**. **Lead's ruling (05.08.2026):**
   keep reusing Block B's rounded figure — *two different figures for one quantity is worse than one
   rounded figure*. What comes out is the **assertion of equality**, not the figure.
2. **The rounding was disclosed nowhere**, and the arithmetic makes that expensive. The printed
   Verbrauchskosten Warmwasser ÷ the printed Gesamtbemessung 40 m³ gives a price per m³ that
   reproduces Wohnung A and Wohnung C **exactly** and misses **both Nutzerwechsel parties by ~3 ct**.
   The renter checking the uncontested line succeeds; the renter checking the contested line fails.
   That is the worst possible distribution of that error and it is *why* the disclosure is mandatory
   rather than tidy.
3. `× 181 von 365 Tagen` **is not multiplication by a number.** Read literally it says `12 × 181 =
   2.172`.

**Ruling 1 — the operator is `= rd.`, not `≈`.**

```
Wohnung B — Bernd Muster (Auszug 30.06.2025): 12 m³ × (181 von 365 Tagen) = rd. 5,95 m³
```

- **`rd.`** is the conventional German abbreviation for *rund* and is what a renter already meets on
  bank, utility and insurance statements. It is a **word**, in the document's own language, and needs
  no notation to be known.
- **`= rd. X` is not a false identity.** `rd.` qualifies the figure, so the sentence reads *"ergibt
  gerundet 5,95 m³"* — which is true. Removing `=` entirely would also remove the statement that the
  left side *produces* the right side, and that statement is exactly what BGH #3 asks for.
- **`≈` is rejected.** It is a glyph, not a word: it presumes mathematical notation the reader is not
  required to know, it has no spoken German form on a legal document, and U+2248 is one more code
  point that has to survive PDF font subsetting. Every other glyph this document fixes (`−`, `·`, `→`)
  is typographic; none carries meaning a word could carry.
- **`rd.` marks the value, not the line.** It renders **only where the printed value differs from the
  exact one**. Wohnung A's `20 m³` is exact and prints bare; `rd. 20 m³` would state a rounding that
  did not happen — the same discipline as *`None` means not applied*. This is the rule that makes the
  marker informative: `rd.` on every figure is decoration, `rd.` on the two derived ones is a fact.
- It applies **wherever a rounded Bemessung is printed** — Block C's derivation lines *and* Block B's
  party table. It is a property of the figure, so it travels with the figure.

**Ruling 2 — one disclosure sentence, in Block B, directly beneath the party table:**

```
Gerundete Bemessungen sind mit rd. gekennzeichnet; gerechnet wird mit dem exakten Wert, sodass eine
Nachrechnung aus dem angezeigten Wert um wenige Cent abweichen kann.
```

- **One sentence, one place.** Not one per block: a caveat repeated per block is a caveat nobody
  reads, and it invites the two copies to drift.
- **Why Block B and not Block C.** The rounded figures *originate* in Block B — it is the Bemessung
  table, and `warm_water_display_weights` is computed once there and re-read by Block C. Block C is
  conditional (it renders only at a Nutzerwechsel) while a raw meter reading can be fractional without
  any Nutzerwechsel at all, so a sentence living in Block C would be missing exactly when it is still
  needed.
- **Directly beneath the table it qualifies**, not two paragraphs away. The reviewer's note on the VDI
  caveat sitting away from the ‰ lines it qualifies is the mistake being avoided; adjacency is part of
  the rule, not layout preference.
- **It renders whenever Block B prints a Bemessung column at all** — one code path, no branch. It
  states the *display convention*, which is true whether or not a given figure needed it; `rd.` is
  what marks the instance. A conditional caveat is a branch that can be wrong about itself.
- **The last clause is the point.** *"…sodass eine Nachrechnung aus dem angezeigten Wert um wenige Cent
  abweichen kann"* is what defect 2 above costs the renter, said out loud, before they discover it on
  the one line they are most likely to contest.

**Ruling 3 — `× (N von M Tagen)`, parenthesised.**

The document's single share idiom is `A von B` — `585 ‰ von 1.000 ‰`, `5.000 kWh von 20.000 kWh`,
`365 von 365 Tagen`. The defect is not the idiom, it is **operator binding**: `×` binds to `181`
instead of to the share. Parentheses fix precisely that and teach the renter nothing new:

```
12 m³ × (181 von 365 Tagen) = rd. 5,95 m³
```

- Rejected: `12 m³ × 181/365 Tage` (the unit dangles off a fraction and the "von" idiom is abandoned in
  one place only) and `12 m³ × 181 ÷ 365 Tage` (two operators where one share is meant, and `÷` is a
  glyph again).
- **The same fix applies to § 9's area-fallback line in Block A**, which has the identical defect:
  `32 kWh je m² Wohnfläche und Jahr × 100 m² × (365 von 365 Tagen) = 3.200 kWh von 20.000 kWh`. That
  result is exact, so it carries **no `rd.`** — which is the marker doing its job in the one branch
  where a reader could otherwise not tell.
- `585 ‰ von 1.000 ‰` and `5.000 kWh von 20.000 kWh Gesamtenergie` are **not** parenthesised and must
  not be: no `×` precedes them, so nothing binds wrongly, and bracketing them would imply an operator
  that is not there.

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
32 kWh je m² Wohnfläche und Jahr × 100 m² × (365 von 365 Tagen) = 3.200 kWh von 20.000 kWh
```

- The parentheses around the day share, and the absence of `rd.` on an exact result, are the rule of
  *"The rounding is disclosed"* above; this line is one of the two places it applies.
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
  Warmwasserkosten on Zeitanteile — exactly what `engine.py` does. **Decided 04.08.2026 (lead):** the
  store's `source` is extended to name § 9b, and the copy may therefore cite it. Exact new value of
  `DEGREE_DAY_TABLE`'s single `RuleVersion.source` (`packages/rules-store`, slice 3):

  ```
  § 9b Abs. 2 und Abs. 3 HeizkostenV; Gradtagszahlen nach anerkannter Promilletabelle
  (VDI-Konvention, keine Rechtsnorm) — verify before production
  ```

  (one line, no newline; pinned by `packages/rules-store/tests/test_rule_data.py`). Three things this
  string is careful about, and none of them is optional:
  - **The statute and the table are separated by the semicolon.** § 9b is law; the promille numbers are
    not. A source reading *"§ 9b HeizkostenV"* alone would present the VDI table as statutory.
  - **`valid_from` and the `Rechtsstand` stamp do not move.** `Rechtsstand 01/1981` dates the *promille
    table*. We have **not** verified when § 9b entered the HeizkostenV, so the pair
    *"§ 9b HeizkostenV 01/1981"* must never be printed as a Rechtsstand — which is exactly why item 6
    keeps the degree-day footer label as the template's own fixed copy (VDI qualifier, no paragraph).
    Resolving it needs the BGBl. history of the HeizkostenV; until then, no in-force date is asserted.
  - **The `— verify before production` marker stays**, last, after the only em dash in the string, so
    the existing "everything after the em dash is internal and never renders" rule keeps working.
- The internal marker `— verify before production` is a developer note and **never renders**. Asserted
  absent from the PDF.

### 4a — The rendered form (slice 4): carriers, order, and where the copy outran the data

> **Rechtsstand 08/2026** (transcribed 04.08.2026). Introduces **no legal value** into
> `packages/rules-store`, resolves no rule and computes nothing. It fixes *where* items 1–4 render and
> closes the places where the drafted copy above names a fact the **engine result does not carry** —
> the copy, the figures and the legal basis stay exactly as items 1–4 state them. Written before the
> template change; golden fixtures `packages/pdf/tests/test_statement_heating_disclosure.py`, red on
> purpose, plus the three carrier rows this section adds to
> `packages/pdf/tests/test_statement_legal_typography.py`.

**Carriers, and their tier.** Each block is one element with one class, so the disclosure is
addressable by a gate and by the stylesheet:

| Block | Carrier | Surface | Tier |
| --- | --- | --- | --- |
| A — *Aufteilung der Gesamtkosten* | `.cost-split` | Paper | **1** |
| B — *Bemessungsgrundlagen* | `.basis-table` | Paper | **1** |
| C — *Nutzerwechsel* | `.party-change` | Paper | **1** |

All three are **tier 1**: a reader recomputes their own share from them, which is the whole test in
`docs/05` → *"Assigning a carrier to a tier"*. The thresholds are not repeated here — `docs/05` owns
them — and the three rows are added to *"Which text on the statement is legally required"* below, so
the partition guard covers them rather than a new class sliding past it. **Paper, not the `.co2`
block's Mint:** three tinted slabs stacked under the money table is ornament, not clarity
(`docs/05` → *Restraint over reduction*), and Paper carries the higher-contrast pairs of the two.

**Order is the numbered list above** (A, B, C, then the existing `.co2` block, then the existing
`.note`s) and is asserted as document order, not merely as presence.

**Glyphs are part of the copy.** `−` is U+2212 MINUS SIGN (an operator, not a hyphen), the separator
is `·` U+00B7, the result arrow `→` U+2192. Transcribed here because a hyphen in
`− CO₂-Vermieteranteil` turns a deduction into a dash.

#### Four places where the drafted copy names something the result cannot supply

Each names what renders **instead** and what would restore the drafted form. None of them is a change
of substance: no figure moves and no citation changes.

1. **Block C identifies each segment by party label, not by date range.** Item 4 prints
   `01.01.–30.06.2025 585 ‰ von 1.000 ‰`; the date range needs a per-party `Period` and `HeatingLine`
   carries `days` / `unit_total_days` and no dates at all. Taking the dates from the engine *input*
   alongside the result is exactly the drift this section forbids at its head. What renders is the
   **party label the money table already prints**, beside that party's own `585 ‰ von 1.000 ‰` — and
   the day derivation keeps item 4's operands exactly (`12 m³ × 181 von 365 Tagen = 5,95 m³`), one
   line per party instead of one `·`-joined sentence. **Restores the dates:** `HeatingLine` carrying
   its segment `Period` (an engine slice). Not invented here.
   For the same reason the heading carries **no unit name**: there is no unit label anywhere —
   `StatementData.party_labels` is keyed per *party*, and `unit-b` is an internal id that never
   reaches a renter. The heading is `Nutzerwechsel — Aufteilung des erfassten Verbrauchs`, one block
   per affected unit, and the parties named inside it are what identify the unit. **Closes it:** a
   `unit_labels` mapping on `StatementData`, supplied by the caller that already supplies the party
   labels.
2. **Block C's convention caveat renders without a `Rechtsstand` stamp.** Item 4's draft ends
   `(Rechtsstand 01/1981)`. Item 6 leaves the raw `Rechtsstand MM/JJJJ` form in exactly **one** place
   (the CO₂ block), the footer already carries the labelled degree-day stamp, and no degree-day stamp
   reaches `HeatingResult` at all — the template would have to hardcode the date or re-resolve the
   rule, and both are the drift rule again. The **mandatory** sentence therefore renders as
   *"Gradtagszahlen sind eine anerkannte Konvention (VDI-Promilletabelle), keine gesetzliche
   Vorgabe."* The caveat is kept — it is the point of item 4 — and only the duplicated stamp is
   dropped.
3. **No ‰ figure renders when § 9a Abs. 2 replaced the consumption key.** With
   `heat_fallback_to_area` the degree-day apportionment determined **no euro on the page**, so
   printing it would disclose a method that was not applied — item 4's own rule ("states no fact the
   data does not carry") and the contract's `None`-means-not-applied rule. The day apportionment of
   Grund- und Warmwasserkosten still renders: `base_weight_sqm_days_x100` is day-weighted in every
   branch.
4. **Block A without central warm water prints no § 9 paragraph and no Warmwasser line.**
   `warm_water_separation is None` means nothing was separated, and `ww_base_pot` / `ww_cons_pot` are
   `0` by construction — a printed `Warmwasser: Grundkosten 0,00 €` would state a warm-water split
   that does not exist. The two Heizung lines render unchanged.

#### Block C — the rendered form

Item 4 owns the copy, the figures and the legal basis; this is the same block with corrections 1–3
applied, spelled out so the seam leaves no design decision open. One block per unit with more than
one party. Demo:

```
Nutzerwechsel — Aufteilung des erfassten Verbrauchs

Diese Einheit wurde im Abrechnungszeitraum von mehreren Parteien genutzt. Der für die Einheit
erfasste Wärmeverbrauch wurde nach monatlichen Gradtagszahlen auf die Nutzungszeiträume aufgeteilt:
Wohnung B — Bernd Muster (Auszug 30.06.2025): 585 ‰ von 1.000 ‰
Wohnung B — Leerstand ab 01.07.2025 → Vermieter: 415 ‰ von 1.000 ‰
Grundkosten und Warmwasserverbrauch werden nach Tagen aufgeteilt:
Wohnung B — Bernd Muster (Auszug 30.06.2025): 12 m³ × (181 von 365 Tagen) = rd. 5,95 m³
Wohnung B — Leerstand ab 01.07.2025 → Vermieter: 12 m³ × (184 von 365 Tagen) = rd. 6,05 m³

Gradtagszahlen sind eine anerkannte Konvention (VDI-Promilletabelle), keine gesetzliche Vorgabe.
```

The parenthesised day share and the `rd.` marker are the ruling in *"The rounding is disclosed —
`rd.`, one sentence, and an operator that is the operation"* above; the disclosure **sentence** does
not repeat here — it lives once, under Block B's party table.

Three parts, each rendered only when it was applied:

| Part | Renders when | Otherwise |
| --- | --- | --- |
| the Gradtagszahlen sentence + one `‰ von ‰` line per party | `heat_consumption_weight` is not `None` | absent — correction 3 |
| the Tage sentence + one derivation line per party | always (the base Bemessung is day-weighted in every branch) | — |
| the convention caveat | wherever a `‰` figure renders | absent with the ‰ lines |

Without central warm water (or with `ww_fallback_to_area`) the Tage sentence reads
*"Grundkosten werden nach Tagen aufgeteilt:"* and each derivation line is the day fraction alone —
`Wohnung B — Bernd Muster (Auszug 30.06.2025): 181 von 365 Tagen`. The m³ operands are the withheld
Bemessung of a column that was not applied, and printing them would be the false disclosure the
contract's `None` rule exists to prevent.

#### Two branch forms the items above leave open

- **Block A without a CO₂ split.** The `−` line is dropped; the `Gesamtkosten` line **and** the
  `= umlagefähige Kosten` line both stay, with equal figures. Item 1 says the block then "opens
  directly at `umlagefähige Kosten = Gesamtkosten`" — this is that identity, *printed*, for the same
  reason the heating footer prints both of its figures in both branches: one code path, the reader
  adds the printed numbers, and no branch asserts an equality in words. A reader sees that no
  deduction was made instead of having to notice a missing line.
- **Block B when a column fell back to the area key (§ 9a Abs. 2).** `ww_fallback_to_area` ⇒
  `ww_consumption_weight_m3` is `None` on every line, so the `Verbrauch Warmwasser` row states
  **`Wohnfläche (m²·Tage) — § 9a Abs. 2 HeizkostenV` / `36.500 m²·Tage`** — the key that *was* applied,
  with the paragraph that replaced the original one — and no m³ Bemessung is printed anywhere in the
  block. The `Verbrauch Heizung` row is unaffected by that fallback and states its own key and its own
  Gesamtbemessung. (Superseded in two respects, both later: the `Verbrauch Heizung` **row** renders —
  *"All four rows render"* under item 1 — and its Gesamtbemessung is withheld only where no Maßeinheit
  is recorded, since slice 5 carries the unit. Where both absences do occur at once they must still not
  be read as one: a § 9a fallback is a citation-carrying figure, an unrecorded unit is the sentence
  `ohne Maßeinheit — nicht ausgewiesen`.)

#### Not in this slice, deliberately

Item 5's **short-period** wording (`… im Abrechnungszeitraum (181 von 365 Tagen)` and the
`anteilig gekürzt` band) — item 5 assigns it a rendering slice of its own, the demo period is a full
calendar year and nothing on the demo path exercises it. What *is* in this slice from item 5 is the
full-year `Berechnungsgrundlagen:` line appended to the existing `.co2` block.

### 4b — Pagination: which blocks may break, and what may never be separated

> **Rechtsstand 08/2026** (transcribed 05.08.2026, after `statement-reviewer` finding **I1**, promoted
> by the lead). A **layout rule**: nothing enters `packages/rules-store`, no rule is resolved, no
> figure moves. The legal purpose is BGH minimum **#3** — the calculation and the figure it justifies
> have to be readable together. Thresholds and inks stay in `docs/05`; this section fixes only which
> element may be split by a page break.

**The defect.** The rendered demo is **3 pages and roughly 40 % blank**: page 1 ends at ~78 % height,
page 2 at ~57 %, page 3 at ~48 %. Cause: `break-inside: avoid` on `.cost-split` and `.party-change`.
Each block refuses to split, does not fit the remaining space, and takes a fresh page — pushing itself
down and leaving the space above it empty.

**The consequence is legal, not cosmetic.** BGH minimum #3 ends up on a **different sheet of paper**
from the numbers it justifies: a renter reads their share in the money table on page 1 and must turn
the page to find the basis it was computed from. A statement whose *Berechnung* is not next to its
result is the formal defect this whole section exists to close, reintroduced by a stylesheet
declaration.

**And it is backwards.** `.basis-table` — the carrier of minimums #2 **and** #3, and the only block
containing *two* tables where the second's column meanings are defined by the first — was the one
carrier **without** `break-inside: avoid`. It was not triggered on this fixture. It will be as soon as
a real building has eight parties.

#### The rule

| Element | Declaration | Why |
| --- | --- | --- |
| `.cost-split`, `.basis-table`, `.party-change` | **must not declare `break-inside: avoid`** | These blocks grow with the number of parties. A block that may not split cannot be laid out at all beyond one page, and long before that it strands the page above it. Breaking a disclosure block across pages is *normal*; stranding it is the defect. |
| every `tr` | `break-inside: avoid` | A party's label and their Bemessung are one statement. Split across a page boundary, a renter reads a figure with no name or a name with no figure. |
| every `thead` | `break-after: avoid` | A column header separated from its first row leaves a page of unlabelled numbers — and in `.basis-table` the *first* table is what gives the second's `Fläche·Tage` / `Verbrauch Warmwasser` columns their meaning. |
| `.disclosure-title` (Blocks A, B, C) | `break-after: avoid` | A heading alone at the foot of a page is the "justification separated from its figures" defect at its smallest scale, and the cheapest one to prevent. |
| `.apportionment li` | `break-inside: avoid` | One derivation line — `… × (181 von 365 Tagen) = rd. 5,95 m³` — is one statement and is never legible in halves. |
| the disclosure carriers | `orphans: 2; widows: 2` | A single stranded line of running prose carries no verification content and reads as an error. |

The shape of the rule is *"break at the seams, never inside a statement"*. `break-inside: avoid` is
correct on the **smallest** element that is one indivisible claim (a row, a list item) and wrong on
every container above it.

#### What is pinned, and what honestly cannot be

Pinned in `packages/pdf/tests/test_statement_pagination.py`, over the template's own stylesheet — the
same idiom as `test_statement_legal_typography.py`, and for the same reason: rendering the PDF and
measuring boxes would be testing Chromium, and a page-count golden over one demo fixture is deleted
the first time a real building has eight units.

**Not pinned, deliberately — say so rather than fake it:**

- **"The money table and its disclosure are on the same sheet."** This is the property the defect
  actually violates, and it is **not expressible**: it depends on the party count, and for a building
  with enough parties it is simply false — the money table alone will exceed a page. It cannot be a
  test, so it is a *design constraint* on any future change: nothing may be inserted between the
  heating money table and Block A.
- **A page-count or fill-ratio assertion on the demo PDF.** Brittle by construction (it encodes the
  fixture's size, not a rule) and it would go red for a *correct* reason — an extra unit — which is
  how a gate gets deleted instead of fixed.
- **Whether the corrected stylesheet actually produces a denser document.** That is a rendering
  outcome, verified by looking at `packages/pdf/output/nk-heating-statement-demo.pdf` after the
  change, not by a golden.

### 5 — § 7 Abs. 3 CO2KostAufG: what already works, and the remainder only

§ 7 Abs. 3 CO2KostAufG requires the landlord to show, **in the Heizkostenabrechnung**, the tenant's CO₂
share, the building's **Einstufung**, and the **Berechnungsgrundlagen** of that Einstufung.

**Already discharged by the existing `co2_block`** (`statement.py` → `.co2`) — do not respec, do not
re-render:

- the tenant's and the landlord's amounts (104,72 € / 157,08 €) and that the landlord's is deducted
  before allocation;
- the landlord percentage (60 %);
- the intensity (40 kg CO₂/m²/Jahr);
- the citation *CO2KostAufG* with `Rechtsstand 01/2023`.

**The remainder** — the Berechnungsgrundlagen, i.e. the two inputs the intensity was computed from and
the band it selected. Appended to the existing block, same surface, no new block:

```
Berechnungsgrundlagen: CO₂-Emissionen des Gebäudes 4.000 kg · beheizte Fläche 100 m²
→ 40 kg CO₂/m²/Jahr · Einstufung: 37 bis unter 42 kg CO₂/m²/Jahr · CO₂-Kosten 261,80 €
```

- **The Einstufung is printed as its intensity band, not as a step number.** `Co2Step` carries
  `max_intensity_exclusive` and `landlord_share_percent` and **no ordinal**; the band is derivable
  (previous step's bound → this step's bound), a step number would be invented. If the Anlage's own
  numbering is wanted on the page it is transcribed into `packages/rules-store` first — **not** counted
  off the tuple index.
- `total_co2_kg`, `co2_cost` and `heated_area_sqm` are engine inputs today and reach `Co2Result`
  nowhere; they must be carried on the result, for the same drift reason as everything else here.

**`kg CO₂/m²/Jahr` is a false label on any period shorter than a year.** `docs/03` §*"The Stufenmodell
is a per-year table"* follows § 5 Abs. 1 S. 4 CO2KostAufG literally: the **Anlage table is shortened**
by the period factor and the emission figure is **not** extrapolated. So
`Co2Result.intensity_kg_per_sqm` is the emission **of the Abrechnungszeitraum** per m², and for an
interim period both the unit above (`statement.py`, the `co2` block) and the Einstufung band in the
Berechnungsgrundlagen line above print a per-year claim for a per-period number — the tenant reads
*19,5 kg CO₂/m²/Jahr · Einstufung: 17 bis unter 22* where the applied Einstufung was *37 bis unter 42*.
Required form once a short period can reach the PDF:

```
Emissionsintensität 19,5 kg CO₂/m² im Abrechnungszeitraum (181 von 365 Tagen)
Einstufung: 18,3 bis unter 20,8 kg CO₂/m² — Werte der Anlage anteilig gekürzt (§ 5 Abs. 1 Satz 4 CO2KostAufG)
```

- **Nothing on the demo path changes.** Its period is the full calendar year 2025, factor exactly 1;
  the label, the band and every figure `scripts/assert_statement_pdf.py` pins stay as they are. The
  full-year wording above this bullet is the one that renders, and it is correct — this is the
  short-period branch only.
- The renderer must **not** recompute the factor from the period: the engine carries it
  (`Co2Result.period_factor`, per `docs/03`), the same way the ratio and the Rechtsstand are carried.
  A second implementation of a legal rule in the template layer is how the two drift apart.
- Scope: a rendering slice of its own, after the engine carries the factor. Listed here so the defect
  is on the record and not rediscovered from a tenant's complaint.

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
- **This supersedes the bare `Rechtsstand MM/JJJJ` form on the page.** Once item 6 ships, the raw string
  renders in exactly one place: the CO₂ block of item 5, where the citation already stands beside it.
  Any check that looks for a bare stamp in the footer — or page-wide, which the footer used to satisfy —
  is asserting the defect and is removed, not restated. The stamps are covered footer-side by
  `packages/pdf/tests/test_statement_rechtsstand_labels.py`, block-side by
  `packages/pdf/tests/test_statement_template.py`, both resolved from `packages/rules-store`.

### The carried-intermediates contract (slice 3)

> **Rechtsstand 08/2026** (transcribed 04.08.2026). Introduces **no legal value** into
> `packages/rules-store` and changes **no arithmetic**: every field below is already computed inside
> `engine.py` / `co2.py` and dropped before the result object is built. Slice 3 is therefore a pure
> engine-package change (CLAUDE.md rule 1: no framework/DB/vendor import, `mypy --strict`, `Decimal` +
> integer cents) and is **not demo-visible** — the rendered PDF must come out byte-identical, no golden
> in `scripts/assert_statement_pdf.py` moves, nothing under `packages/pdf/` changes.

Items 1–5 above name the figures in prose. This is the same list in the form the engine has to take, so
that `engine-implementer` has no design decision left to make. Golden fixtures, written first and red
on purpose: `packages/heating-engine/tests/test_heating_disclosure.py` plus the `source` assertions in
`packages/rules-store/tests/test_rule_data.py`.

**Rules that apply to all four tables below:**

1. **Every new field is required — no default value.** A default lets a caller construct a result that
   silently omits a legally required disclosure figure, and the omission then shows up as a blank on a
   tenant's statement instead of as a `TypeError` in CI.
2. **`None` means "this figure was not applied", never "not carried".** Where a branch did not run, its
   operands are `None` and the fixtures assert that they are — a template that prints the wrong branch
   then prints `None`, loudly, rather than a plausible wrong formula (item 3's hard rule).
3. **Money is `Cents`.** Weights and areas keep the engine's existing fixed-point convention; a field
   carrying a ×100 value **says so in its name**, because `docs/03`'s de-scaling warning is precisely
   about values that look right as integers and render wrong (`18.250` vs `1.825.000`).
4. **Nothing here is recomputed at render time**, and nothing is read from the engine *input* alongside
   the result — the drift rule stated at the top of this section.
5. **Two existing engine conventions stay exactly as they are in this slice.** The result *echoes what
   the engine divided by*; it does not harmonise it. Namely: § 9's area fallback pro-rates over a flat
   `365` while the CO₂ period factor anchors its reference year on `valid_from` (366 in a leap year).
   That inconsistency is real and is recorded in the gaps below — **it is not fixed here**, because
   changing it would move a euro figure in a slice whose whole point is that no euro figure moves.

#### `WarmWaterSeparation` — new frozen dataclass (§ 9 HeizkostenV), item 3

Lives in `packages/heating-engine/src/lokara_heating_engine/inputs.py` next to the other result shapes
and is exported from the package. It records **which § 9 branch ran and with which operands** — today
not recoverable from the result at all.

| Field | Type | Demo value | Required by |
| --- | --- | --- | --- |
| `method` | `Literal["MEASURED", "AREA_FALLBACK"]` | `"MEASURED"` | item 3: the two branches print different text and the wrong one must be unprintable |
| `q_ww_kwh` | `Decimal` | `5000` | § 9 Abs. 2 — the separated warm-water energy, the result of the printed formula |
| `total_energy_kwh` | `Decimal` | `20000` | the denominator the copy prints (`… von 20.000 kWh Gesamtenergie`) |
| `volume_m3` | `Decimal \| None` | `40` | measured branch operand |
| `factor_kwh_per_m3_kelvin` | `Decimal \| None` | `2.5` | measured branch operand (`WarmWaterFormula`, resolved rule value — never a literal in the template) |
| `hot_temp_c` | `Decimal \| None` | `60` | measured branch operand |
| `cold_temp_c` | `Decimal \| None` | `10` | measured branch operand |
| `area_fallback_kwh_per_sqm_year` | `Decimal \| None` | `None` | fallback branch operand (`32 kWh je m² und Jahr`) |
| `heated_area_sqm` | `Decimal \| None` | `None` | fallback branch operand (`× 100 m²`) — the area the fallback actually used |
| `period_days` | `int \| None` | `None` | fallback branch operand (`365 von 365 Tagen`, numerator) |
| `reference_year_days` | `int \| None` | `None` | fallback branch operand (denominator — the flat `365` the engine divides by, per rule 5 above) |

In the `AREA_FALLBACK` branch the four measured-branch fields are `None` and the four fallback fields
are set; in the `MEASURED` branch, the other way round. `heated_area_sqm` is deliberately **not** hoisted
onto `HeatingResult`: outside this branch no disclosure in this section needs a bare building area, and a
field that is merely useful is a field that will drift.

#### `HeatingResult` — the vertical half (Block A), items 2 and 3

| Field | Type | Demo value | Required by |
| --- | --- | --- | --- |
| `billable_cost` | `Cents` | `1_014_292` | Block A's `= umlagefähige Kosten` line; equals `total` when `co2 is None` |
| `heating_pot` | `Cents` | `760_719` | § 9 result — `→ Heizung 7.607,19 €` |
| `ww_pot` | `Cents` | `253_573` | § 9 result — `→ Warmwasser 2.535,73 €`; `0` when there is no central warm water |
| `heat_base_pot` | `Cents` | `228_216` | §§ 7/8 — `Heizung: Grundkosten 2.282,16 €` |
| `heat_cons_pot` | `Cents` | `532_503` | §§ 7/8 — `Verbrauchskosten 5.325,03 €` |
| `ww_base_pot` | `Cents` | `76_072` | § 8 — `Warmwasser: Grundkosten 760,72 €`; `0` without central warm water |
| `ww_cons_pot` | `Cents` | `177_501` | § 8 — `Verbrauchskosten 1.775,01 €`; `0` without central warm water |
| `applied_consumption_share` | `Decimal` | `0.7` | item 2 — *what was applied*, printed as `30 % / 70 %`, derived from the resolved rule value and never a template literal |
| `split_bounds` | `HeatingSplitBounds` | `0.5 / 0.7` | item 2 — *what the law permits*, the second of the two facts; § 7 Abs. 1 HeizkostenV |
| `warm_water_separation` | `WarmWaterSeparation \| None` | see above | item 3; `None` exactly when `HeatingInput.warm_water is None` |
| `heat_fallback_to_area` | `bool` | `False` | § 9a Abs. 2 — Block B states an Umlageschlüssel **per column**, and today the result cannot say that the heating column fell back to Wohnfläche while warm water did not |
| `ww_fallback_to_area` | `bool` | `False` | as above, for the warm-water column |
| `heat_consumption_unit` *(slice 5)* | `MeasurementUnit \| None` | `HKV_UNITS` | the Maßeinheit the heating-consumption Bemessung is *in* — Block B's `1.000 HKV-Einheiten` and the device named in its Umlageschlüssel cell. `None` = not applied (§ 9a Abs. 2) or not recorded; resolution and both spellings in *"`MeasurementUnit` travels with the value"* |

`consumption_fallback_to_area` **stays and keeps its meaning** (`heat_fallback or ww_fallback`) — it is
read by existing tests and by the PDF layer, and this slice moves nothing that renders.

#### `HeatingLine` — the horizontal half (Blocks B and C), item 1 and item 4

One row per party, so every field is per party.

| Field | Type | Demo values (A · B-Mieter · B-Vermieter · C) | Required by |
| --- | --- | --- | --- |
| `days` | `int` | `365 · 181 · 184 · 365` | § 9b Abs. 3 Zeitanteile; Block C prints `181 von 365 Tagen` |
| `unit_total_days` | `int` | `365 · 365 · 365 · 365` | the denominator that was applied (`von 365`), which is a per-unit sum, not the period length |
| `base_weight_sqm_days_x100` | `Decimal` | `1_825_000 · 543_000 · 552_000 · 730_000` | Block B's `Fläche·Tage` Bemessung — §§ 7 Abs. 1 / 8 Abs. 1 HeizkostenV. **×100 fixed point**: ÷ 100 gives the printed `18.250 · 5.430 · 5.520 · 7.300`, Σ `36.500` |
| `heat_consumption_weight` | `Decimal \| None` | `600 · 146.25 · 103.75 · 150` | the consumption Bemessung actually applied to the heating pot. `None` **iff** `heat_fallback_to_area` — then the applied Bemessung was Fläche·Tage and no consumption figure may be shown |
| `ww_consumption_weight_m3` | `Decimal \| None` | `20 · 5.950684… · 6.049315… · 8` | Block B's `Verbrauch Warmwasser` Bemessung (m³, unscaled). `None` **iff** there is no central warm water or `ww_fallback_to_area` |
| `degree_day_promille` | `Decimal` | `1000 · 585 · 415 · 1000` | Block C's `585 ‰` — § 9b Abs. 2 |
| `unit_degree_day_promille_total` | `Decimal` | `1000 · 1000 · 1000 · 1000` | Block C's `von 1.000 ‰`. Never omit it: over a partial billing period a unit's parties sum to **less** than 1.000 and a bare `585 ‰` would then read as wrong |

- `degree_day_promille` is carried for **every** party, including single-party units, exactly as
  `_build_parties` already computes it; the template decides whether Block C renders (unit with > 1
  party), the engine does not. `unit_degree_day_promille_total` is the sum over that unit's parties —
  i.e. the denominator `_consumption_weights` divides by.
- **The unit-level reading (`12 m³` in Block C) is deliberately not a field.** It is the exact sum of
  that unit's parties' `ww_consumption_weight_m3` (the apportionment is `value × own/total`), so
  carrying it again would create two sources for one number. The fixture asserts the identity.

#### `Co2Result` — § 7 Abs. 3 CO2KostAufG Berechnungsgrundlagen, item 5

| Field | Type | Demo value | Required by |
| --- | --- | --- | --- |
| `total_co2_kg` | `Decimal` | `4000` | § 7 Abs. 3 — the emissions the Einstufung was computed from |
| `heated_area_sqm` | `Decimal` | `100` | § 7 Abs. 3 — the divisor. Repeated from `WarmWaterSeparation` on purpose: § 7 Abs. 3 is discharged by this object alone, and the two must be the same number (fixture asserts it) |
| `co2_cost` | `Cents` | `26_180` | § 7 Abs. 3 — the amount being split, and the only way a tenant can check `104,72 + 157,08 = 261,80` |
| `band_min_inclusive` | `Decimal \| None` | `37` | § 7 Abs. 3 *Einstufung*, printed as a band because `Co2Step` carries no ordinal. `None` = the first step, which has no lower bound (`unter 12`) |
| `band_max_exclusive` | `Decimal \| None` | `42` | as above. `None` = the open-ended top step |
| `period_days` | `int` | `365` | the short-period copy in item 5 prints `(181 von 365 Tagen)`, and `period_factor` alone cannot be un-divided back into it |
| `reference_year_days` | `int` | `365` | as above — the denominator, anchored on `valid_from` (366 in a leap year, `docs/03`) |

**How the band is derived — the one place this slice touches arithmetic-shaped code:**

```
band_max_exclusive = step.max_intensity_exclusive × period_factor   # None → None (open-ended, never scaled)
band_min_inclusive = previous_step.max_intensity_exclusive × period_factor   # first step → None
```

- Both bounds are the ones **actually compared against**, i.e. already shortened by `period_factor`
  (§ 5 Abs. 1 S. 4). The template must not multiply anything: a second implementation of a legal rule
  in the template layer is how the two drift apart. For the demo year the factor is exactly 1 and the
  band is `37` / `42` — the printed page does not move.
- `landlord_share_percent_for_intensity` keeps its current signature and behaviour; it is public and
  fixture-covered. The band is derived inside `split_co2_cost` from the same table and the same factor.
- `period_factor` is unchanged and stays on the result (it landed with the § 5 Abs. 1 S. 4 slice); it
  belongs to this picture rather than beside it, because the short-period copy in item 5 needs the
  factor **and** the two day counts together.

### Which text on the statement is legally required

**This section names the text and assigns each carrier a tier. It sets no thresholds.** The
typographic rules — the tier-1 pair (`legal-t1-size`, `legal-t1-contrast`) and the tier-2 pair
(`legal-t2-contrast`, `legal-t2-scale`, **no size floor**) — live in `docs/05-design-system.md`
§*Legally required disclosure — two tiers, split by what the content is for*, together with the
measured ratios of the brand pairs and the reason there is no absolute pt floor. A design-system rule
with two homes is a rule waiting to disagree with itself, so no number is repeated here.

On this document, the following is legally required and falls under those rules. **Every carrier is
in exactly one tier**; adding a carrier without a tier is a defect, and the test in this section
fails on it.

| Content | Carrier | Tier | Basis |
| --- | --- | --- | --- |
| The four BGH formal minimums — Gesamtkosten, Umlageschlüssel, Anteil des Mieters, Vorauszahlungen | the cost rows, `.key-label`, the `tfoot` totals | **1** | BGH-Mindestangaben, § 259 BGB |
| Umlageschlüssel + Gesamtbemessung | `.key-label` | **1** | minimum #2, and the denominator #3 rests on |
| Block A — the §§ 7/8/9 split of the Gesamtkosten into the four pots | `.cost-split` | **1** | §§ 7, 8, 9 HeizkostenV; it is the vertical half of minimum #3 |
| Block B — Umlageschlüssel + Gesamtbemessung + Bemessung per money column | `.basis-table` | **1** | minimums #2/#3 for the heating table, which the `.key-label` line does not reach |
| Block C — the Nutzerwechsel apportionment (Gradtagszahlen, Zeitanteile) | `.party-change` | **1** | § 9b Abs. 2/Abs. 3 HeizkostenV; it derives the Bemessung a renter checks |
| The heating footer's reconciliation sentence | `tfoot .foot-note` | **1** | HeizkostenV disclosure; it reconciles the Gesamtkosten a reader adds up |
| § 9a estimation / fallback disclosure | `.note` | **1** | § 9a HeizkostenV — see *Why `.note` is tier 1* below |
| The CO₂ split and its Berechnungsgrundlagen | `.co2` | **1** | § 7 Abs. 3 CO2KostAufG — the reconciliation `104,72 + 157,08 = 261,80` |
| `Rechtsstand` stamps + the "keine Rechts- oder Steuerberatung" disclaimer | `footer` | **2** | `CLAUDE.md` cross-cutting rules — **not** a BGH minimum, our own rule |

Everything else on the page — the Vermieter/period meta line, column headings, decorative framing — is
body or secondary copy and keeps the ordinary **AA** bar from `docs/05`.

**Why `.note` is tier 1.** It is emitted in exactly two places (`packages/pdf/src/lokara_pdf/statement.py`,
the `notes` list) and both are § 9a HeizkostenV notices: *"Fehlende Ablesungen wurden gemäß § 9a
HeizkostenV geschätzt …"* and *"Mehr als 25 % der Fläche ohne Ablesung — der Verbrauchsanteil wurde
nach Wohnfläche umgelegt (§ 9a Abs. 2 HeizkostenV)."* Both change **how the renter must read their own
Bemessung**. The first says the figure in the Verbrauch column is an **estimate, not a reading**. The
second says the **consumption key was replaced by the area key** — i.e. the Umlageschlüssel printed in
`.key-label` is *not* the one that was applied. A renter cannot verify their share without either
fact, which puts both squarely inside BGH minimums #2 and #3. It is not incidental copy, and its
9,0 pt setting is a defect, not a deliberate de-emphasis.

**The state of the page today** (this is the defect, not the rule): `.key-label` is **8,5 pt Slate on
Mint = 4,81:1** — below body copy (10 pt) and AA-by-0,31 where tier 1 owes AAA; `tfoot .foot-note` is
8,5 pt Slate on Paper and `.note` 9,0 pt Slate on Paper, both below body copy and both 5,44:1 against
a 7:1 bar. Slate leaves tier 1 entirely; Petrol Ink and Forest Deep are the qualifying inks. `.co2`
declares neither `font-size` nor `color`, so it inherits 10 pt Petrol Ink on Mint (13,91:1) and is
already compliant. **`footer` is now compliant**: at 8,0 pt Slate on Paper it is 5,44:1 ≥ the tier-2
4,5:1 bar, and tier 2 has no size floor — the 8,0 pt that read as a violation under the old flat tier
is the correct setting for provenance text.

Checkable in `packages/pdf/tests/test_statement_legal_typography.py` against `statement_html()`: the
carriers above are enumerated per tier, tier 1 is compared against the stylesheet's own body
font-size **and** the AAA floor, tier 2 against the AA floor **only** — the tier-2 code path has no
size branch at all, by construction. A further test asserts the two tiers partition the carrier list,
so a newly added carrier cannot fall through untested. A stylesheet-level assertion, deliberately not
a pixel one — rendering and measuring glyphs would test Chromium.

### Gaps — not invented here

- ~~**The unit of the heating-consumption Bemessung.**~~ **Closed 06.08.2026 by slice 5** —
  *"`MeasurementUnit` travels with the value — the plumbing decision"* above. `HeatingUnit` and
  `ConsumptionValue` carry the unit, `HeatingResult` and `NkResult` surface it, a mixed key is an
  input error, an absent unit still prints the withholding sentence, and the **sub-question the lead
  had left open** (withhold vs. a unit-free `1.000`) is **answered: withhold**. Warm water was never
  affected — `ww_consumption_m3` / `volume_m3` fix m³ by type, `CANONICAL_UNITS` maps
  `WARM_WATER → CUBIC_METRE`, and § 9's formula is defined per m³; that unit is derived, not guessed.
- **German spellings of `MeasurementUnit`** (display copy, no legal value, no `Rechtsstand`; the
  *spellings* half of the `CONSUMPTION` gap, closed 05.08.2026 — the *plumbing* half closed
  06.08.2026, and **which spelling goes in which cell** is settled in *"Which spelling goes where"*
  above):

  | `MeasurementUnit` | Rendered | Note |
  | --- | --- | --- |
  | `KWH` | `kWh` | Wärmemengenzähler; the § 9 energy denominator |
  | `CUBIC_METRE` | `m³` | Wasserzähler |
  | `HKV_UNITS` | `Einheiten (Heizkostenverteiler)`, short `HKV-Einheiten` | dimensionless allocator reading |

  On the statement the **compact** form (`kWh` / `m³` / `HKV-Einheiten`) is what a numeric cell takes;
  the long form appears once, as the device name in the `Verbrauch Heizung` Umlageschlüssel cell, in
  the parenthesis-free wording fixed above (`… in Einheiten eines Heizkostenverteilers`, `… in kWh am
  Wärmemengenzähler`).

- **Zählerstände (start/end readings) are not specified here and must not be improvised.** HeizkostenV
  gives the tenant a right to check the readings, and the gap is listed under *"Also missing from the
  tenant document"* — but the engine takes a *resolved consumption value*, not readings: there is no
  `meter_id`, no start, no end anywhere in `HeatingInput`. Rendering readings therefore needs a data
  path that does not exist (M3's Zähler slice), plus a decision on where the consistency check
  `Ende − Anfang == Verbrauch` lives. Named, not designed.
- **CO₂ over a non-annual period — the pro-rating itself is implemented; what remains is the rounding.**
  ~~`split_co2_cost` divides by area with no pro-rating~~ was true when this section was written and was
  fixed on 04.08.2026: § 5 Abs. 1 S. 4 CO2KostAufG shortens the **Anlage table** by
  `period_factor = min(1, days(period) / days(reference year))`, the emissions are *not* extrapolated,
  and the disclosed intensity stays the period figure. Rule + conventions + edge cases:
  `docs/03` → *"The Stufenmodell is a **per-year** table"*; fixtures
  `packages/heating-engine/tests/test_co2_period_factor.py`; `Co2Result.period_factor` carries the
  applied factor and the contract above adds the two day counts, so item 5's short-period copy renders
  without the template recomputing law. What genuinely remains open:
  - **§ 5 Abs. 1 S. 3 rounding before classification** — the statute requires the specific emission
    value to be rounded to one decimal place (*"auf die erste Nachkommastelle zu runden"*); the engine
    classifies the unrounded `Decimal`, and at a bound (11,96 → 12,0) that changes the Stufe.
    Scheduled: `PLAN.md` execution order **row 4.5**; recorded in `docs/03` → *"Known gap, deliberately
    not implemented here"*. Not folded into any slice of this section.
  - **Two conventions that are conventions, not statute**: *anteilig* read day-exact rather than
    month-exact, and S. 4 applied to a Rumpfperiode that was never *vereinbart*. A BMWSB Arbeitshilfe
    or a Mietrechtler's sign-off would resolve both (`docs/03`).
  - **A > 12-month period with a CO₂ split is refused**, which is lawful for Nichtwohngebäude
    (CO2KostAufG § 8) — recorded as drift in `docs/03` → *"Additional fixtures to add"*.
- **§ 9's area fallback divides by a flat 365, the CO₂ period factor does not.** `_separate_warm_water`
  pro-rates the 32 kWh/m²/a Ersatzwert over `days / 365`, so a leap-year statement pro-rates to
  366/365 = 1,0027 while `co2.py` anchors its reference year on `valid_from` and returns exactly 1. One
  of the two is wrong for a full leap year; § 9 Abs. 2 does not define the divisor either. Named, not
  guessed, and **not** changed by the carried-intermediates slice — the result echoes the divisor it
  used (`WarmWaterSeparation.reference_year_days`) so the page states what happened. Resolving it needs
  the same kind of source as the *anteilig* question above.
- **§§ 7/8 with different shares for heating and warm water** — see item 2; the input cannot express it
  today.
- **A party's own date range is not on the result.** `HeatingLine` carries `days` and
  `unit_total_days`; the `01.01.–30.06.2025` of item 4's drafted Block C would have to come from the
  engine *input*, which is the drift this section forbids. Block C therefore names each segment by its
  party label (4a, correction 1). Closing it means `HeatingLine` carrying its segment `Period` — an
  engine change with no legal content, deliberately not folded into a rendering slice.
- **Nothing carries a *unit* label into the statement.** `StatementData.party_labels` is keyed per
  party and `unit-b` is an internal id, so no block may print a unit name (4a, correction 1). A
  `unit_labels` mapping on `StatementData`, filled by the same caller that fills `party_labels`, is
  what closes it; until then Block C's heading names no unit and the parties inside identify it.

### Proposed implementation split

Recorded here because the seams are a property of the spec, not of a sprint. **Five slices**; four are
needed for the six items above, the fifth unblocks the one column they cannot ship.

| # | Lands | Lane | Independent? |
| --- | --- | --- | --- |
| 1 | `Rechtsstand` labels (item 6) | `app-implementer` (`packages/pdf/src`) | yes |
| 2 | Tier-1 disclosure meets `legal-t1-size` + `legal-t1-contrast`; tier 2 stays as it is (`docs/05`) | `app-implementer` (`packages/pdf/src`) | yes — but **before** 4 |
| 3 | `HeatingResult` carries its intermediates (+ `Co2Result` Berechnungsgrundlagen, + § 9b in the degree-day `source`) | `engine-implementer` (`packages/{heating-engine,rules-store}/src`) | yes |
| 4 | Blocks A / B / C render (items 1–5; rendered form, carriers and branch cases in **4a**) | `app-implementer` (`packages/pdf/src`) | **strictly after 3** (and after 2) |
| 5 | **Specified 06.08.2026** — *"`MeasurementUnit` travels with the value"*. `MeasurementUnit` carried meter → engine input → engine result → statement; `Verbrauch Heizung` Gesamtbemessung + Bemessung column; NK `CONSUMPTION` reference total; the withholding branch kept for a building that records no unit | `engine-implementer` (`packages/{heating,nk}-engine/src`) **then** `app-implementer` (`packages/pdf/src`, `packages/pdf/src/lokara_pdf/demo.py`, `apps/api/src/lokara_api/statement_service.py`) | yes — and it is what unblocked the heating-consumption column |
| 6 | The slice-4 defects: the `Verbrauch Heizung` row + its two branches and the two missing citations (item 1, *"All four rows render"*), the `rd.` / `(N von M Tagen)` / one-sentence rounding disclosure (item 1, *"The rounding is disclosed"*), the page-break rules (**4b**) | `app-implementer` (`packages/pdf/src`) | yes — after 4, independent of 5 |
| 7 | The demo's CO₂ fixture: `total_co2_kg` 2.000 → **4.000 kg**, `co2_cost` 300,00 → **261,80 €**, in `packages/pdf/src/lokara_pdf/demo.py` **and** `packages/db/src/lokara_db/seed.py` together | `app-implementer` + `db` lane, one commit | yes — but the two files must move together, or the PDF demo and the API demo state different numbers for one building (`docs/06` → "One occupancy timeline drives every engine") |

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
      above. The one open sub-question — the **unit** of a `CONSUMPTION` total — is closed by
      **"`MeasurementUnit` travels with the value — the plumbing decision (slice 5)"** (06.08.2026).
- [x] Heating: how consumption values and the CO₂ split are presented to the tenant →
      **"Heizkostenabrechnung — the heating table's disclosure"** above (Umlageschlüssel +
      Gesamtbemessung per column, §§ 7/8, § 9, Gradtagszahlen, § 7 Abs. 3 CO2KostAufG). Still open:
      **the CO₂-Vermieteranteil as a visible row** in the heating table, which the footer reword is
      standing in for; and the sub-questions that section names —
      ~~the unit of the heating-consumption Bemessung~~ (**closed 06.08.2026**: the unit is carried,
      and withhold-vs-unit-free is answered *withhold*),
      **Zählerstände** (no data path into the engine),
      **§ 5 Abs. 1 S. 3 rounding before the CO₂ classification** (`PLAN.md` row 4.5 — the period
      factor itself shipped on 04.08.2026), **§ 9's flat-365 fallback divisor**,
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
