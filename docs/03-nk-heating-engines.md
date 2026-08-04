# 03 — NK & heating/CO₂ engines (the crown jewel)

> These are the product. **Pure Python packages, no web-framework/DB/vendor imports.** Deterministic,
> cent-exact, golden-tested (pytest). Built at M1 (NK) and M2 (heating/CO₂), before any UI.
>
> The **document** these engines feed is specified separately in `docs/08-statement-document.md`.

## Shared engine contract

- Input: **normalized** value objects — plain dataclasses / Pydantic models (no SQLAlchemy models, no
  vendor types). Adapters map DB → these.
- Money: integer **cents**; intermediate math with `decimal.Decimal`; **largest-remainder rounding** so
  the sum of allocated shares reconciles to the input **to the cent**.
- Output: a plain result object (shares per party + a reconciliation total) — the PDF layer formats it.
- ⚠️ **De-scale at the render boundary.** Engine values are **scaled integers** (money = cents;
  areas/weights = ×100 fixed-point). The presentation layer must convert back before display, or a
  Bemessung of `18.250 m²·Tage` renders as `1.825.000`. Tests comparing integers stay green through this
  bug — **read the rendered PDF** before calling an output done.
- Every legal ratio/table (HKVO, CO₂ 10-step) comes from the **versioned rules store**, passed in as a
  parameter with an as-of law date. Engines never hardcode a legal number, and never import
  `rules-store` — the caller resolves the values and passes them in; the value *shapes* live in `domain`.
- **Anlage-V line mappings** also live in `rules-store`, but they're **tax-export data (M7)**, not engine
  input — the NK/heating engines never see them.

---

## `packages/nk-engine` (M1)

### Responsibilities

- Day-weighted allocation over an _Abrechnungszeitraum_.
- All allocation keys: `AREA`, `PERSONS`, `CONSUMPTION`, `UNITS`, `DIRECT`, `MEA`.
- **Vacancy → landlord**: any day a unit is not `RENTED` (and not billable to a renter) lands on the
  landlord side.
- **DIRECT**: a cost assigned to exactly one unit/tenancy bypasses proportional allocation.
- Keys are read from a **per-period assignment**, so re-running with a different key destroys no data.
- Largest-remainder rounding; totals reconcile exactly.

### Canonical golden fixture — MUST pass byte-for-byte

Garbage cost **€1,200.00** for 2025 (365 days), key = area, one mid-year move-out + vacancy:

| Party                          | Area  | Days | m²·days | Share              |
| ------------------------------ | ----- | ---- | ------- | ------------------ |
| Unit A — Renter 1              | 50 m² | 365  | 18,250  | €600.00            |
| Unit B — Renter 2 (out Jun 30) | 30 m² | 181  | 5,430   | €178.52            |
| Unit B — **VACANT** (Jul–Dec)  | 30 m² | 184  | 5,520   | €181.48 → landlord |
| Unit C — Renter 3              | 20 m² | 365  | 7,300   | €240.00            |
| **Total**                      |       |      | 36,500  | **€1,200.00** ✓    |

Renter 2 pays only their 181 days; the vacant half-year lands on the landlord; A and C aren't
overcharged; largest-remainder rounding sums to exactly €1,200.00. **This fixture is the M1 DoD.**

### Additional fixtures to add

- `DIRECT` cost to a single unit (no spread).
- `PERSONS` key with a mid-period person-count change.
- `CONSUMPTION` key from metered readings.
- Interim statement (<12 months) and >12-month period (domain-depth differentiators).
  ⚠️ **Neither fixture exists yet, and the >12-month half is now partly contradicted below.** The CO₂
  split *refuses* a period longer than a year (§ 5 Abs. 1 S. 4 shortens the table only *downward*; see
  "Why a period > 12 months is refused rather than scaled"). NK is unaffected and heating still
  computes when `co2 is None`, so the refusal bites in exactly one place: a **Gewerbe** building with a
  CO₂ split. § 556 Abs. 3 S. 1 BGB's 12-month cap is Wohnraum-only and CO2KostAufG **§ 8** governs
  Nichtwohngebäude, so that combination is lawful and we currently reject it. Recorded as drift, not
  resolved: closing it means either dropping >12 months as a differentiator, or specifying what the
  Einstufung means over such a period — which needs a source we do not have.

---

## `packages/heating-engine` (M2)

### Responsibilities

- **§§7/8 HKVO** split between base and consumption cost — configurable **30/70** … **50/50**
  (from rules store).
- **§9** warm-water separation from heating.
- **§9a** estimation when readings are missing — **only** in the case §9a actually covers: an individual
  unit's device failed, estimated by the prescribed methods (comparable period / comparable rooms).
  ⚠️ **This is not licence to guess a missing building-level total.** If the energy/cost total or a
  denominator is absent, the API **refuses and explains, in German** — a Heizkostenabrechnung built on a
  guessed total isn't approximately right, it's wrong. The Betriebskosten still compute, so one missing
  meter never blocks the whole statement. Don't "fix" the refusal by adding a fallback estimate.
- **Degree-day (Gradtags) apportionment** on renter change mid-period — **§ 9b HeizkostenV**: Abs. 2
  permits apportioning an unread period by Gradtagszahlen, Abs. 3 puts Grund- und Warmwasserkosten on
  Zeitanteile. Apportionment basis therefore: **consumption** cost splits by **degree-days**;
  **base + warm-water** costs split by **days**.
- ⚠️ **The method is statutory (§ 9b), the promille table is not.** The table is a VDI convention and
  carries a **"verify before production"** marker in `rules-store` (with its `Rechtsstand 01/1981`),
  unlike the HKVO ratios and the CO₂ table which are legally fixed. The rule's `source` names both
  halves, separated — see `docs/08` → *"§ 9b HeizkostenV is a prerequisite"*. The `01/1981` stamp dates
  the **table**; § 9b's own in-force date is not asserted anywhere and would need the BGBl. history of
  the HeizkostenV to establish.
- External MDL (Messdienstleister) data feeds in through the meter adapter as normalized readings —
  the engine never knows the source.

### CO₂ cost split (CO2KostAufG) — mandatory, part of Tier-1

- **10-step model**: the building's CO₂ intensity (kg CO₂/m²/yr) selects a step; the step sets the
  **landlord vs renter percentage split** of the CO₂ price portion of heating cost.
- The 10-step table lives in the **versioned rules store** (`Rechtsstand` shown on output).
- Missing/incorrect CO₂ split = tenant's **3% reduction right** (§7 Abs. 4 CO2KostAufG) — so this is
  correctness-critical, not cosmetic.

#### The Stufenmodell is a **per-year** table — a short Abrechnungszeitraum shortens the table

> **Rechtsstand 01/2023** (CO2KostAufG of 05.12.2022, in force 01.01.2023; text checked against
> gesetze-im-internet.de on 04.08.2026). Rule owner: `co2kostaufg.stufenmodell` in
> `packages/rules-store`. The engine hardcodes no bound and no divisor — both arrive as parameters.

**Inputs**

| Input | Where from | Note |
| --- | --- | --- |
| `total_co2_kg` | `Co2Input` | Emissions **of the Abrechnungszeitraum**, already converted to it per § 5 Abs. 1 S. 5 (see below) |
| `heated_area_sqm` | Σ unit `area_sqm_x100` / 100 | Wohnfläche of the supplied units |
| `co2_cost` | `Co2Input` | The CO₂-price portion of the heating cost, in cents |
| `table` | rules store, `Co2Table` | Anlage CO2KostAufG, bounds in **kg CO₂/m²/a** |
| **`billing_period`** | `HeatingInput.billing_period` | **the input this section adds** — the split is not period-free |

**Formula**

```
intensity      = total_co2_kg / heated_area_sqm      # over the Abrechnungszeitraum, NOT per year
period_factor  = days(billing_period) / days(reference year)     # ≤ 1, see convention below
bound_i(scaled) = bound_i × period_factor            # every finite bound of the Anlage table
step           = first step with intensity < bound_i(scaled)   (open-ended step: no bound, no scaling)
landlord_share = step.landlord_share_percent
landlord, renter = largest_remainder(co2_cost, [share, 100 − share])
```

For a full-year period `period_factor == 1` and every number is exactly what it was before — the
factor is a no-op on the demo path.

**Legal basis — the statute is _not_ silent here.** § 5 Abs. 1 S. 4 CO2KostAufG, verbatim:

> *"Ist ein Abrechnungszeitraum von unter einem Jahr vereinbart, so sind die Werte der
> Einstufungstabelle in der Anlage anteilig zu kürzen."*

and the Anlage's own column header — *"Kohlendioxidausstoß des vermieteten Gebäudes oder der Wohnung
pro Quadratmeter Wohnfläche **und Jahr**"*, unit **`kg CO2/m2/a`** — is what makes the factor
necessary at all. Comparing a six-month emission figure against a per-year bound puts every short
period one or more Stufen too low, i.e. the **landlord's** share too small and the **renter's** too
large, on a document the renter is entitled to rely on. Exposure: § 7 Abs. 4 CO2KostAufG, the 3 %
Kürzungsrecht (§ 7 Abs. 3 requires the *Einstufung* and the *Berechnungsgrundlagen* to be shown, and a
wrong Einstufung is not a shown one).

**The statute shortens the table; it does not extrapolate the consumption.** The two are
arithmetically identical for step *selection* (`i < b·f` ⇔ `i/f < b`) but not for what is **disclosed**,
and the disclosed value is what § 7 Abs. 3 is about. We follow the statute's own mechanic:

- `Co2Result.intensity_kg_per_sqm` stays the **period** figure (kg CO₂/m² *over the
  Abrechnungszeitraum*). It is **not** annualised. No extrapolated emission figure is ever computed —
  extrapolating consumption is precisely what the legislator did not write.
- Therefore, for a period shorter than a year, the PDF label `kg CO₂/m²/Jahr` and the printed
  Einstufung band become **wrong**, because they claim a per-year quantity for a period figure. That is
  a rendering defect, tracked in `docs/08` § *"§ 7 Abs. 3 CO2KostAufG"*; it does not touch the demo,
  whose period is a full calendar year. The engine must therefore also expose the applied
  `period_factor` on `Co2Result`, or the PDF cannot print the gekürzt band without recomputing law.

**Convention (statute silent) — the divisor.** § 5 Abs. 1 S. 4 says *anteilig* and defines neither the
numerator nor the denominator; no BMWSB/BMWK Arbeitshilfe or Aufteilungsrechner documentation found
(04.08.2026) states one either. Commentary only ever gives the clean case ("bei einem halben Jahr
beginnt die oberste Stufe schon bei 26 statt 52 kg/m²"). Chosen convention, **labelled as a convention,
not as statute** — the same status as the VDI Gradtagszahlen table in `packages/rules-store`:

```
period_factor = min(1, days(billing_period) / days(reference year))
reference year = [valid_from, same calendar date one year later)   # 366 if it spans a 29 Feb
                                                                   # 29 Feb start → 1 Mar
```

- **Days, not months.** The engine is day-based everywhere else (§§ 7/8 base costs are m²·days), and a
  day count needs no calendar-alignment assumption. The alternative reading, *Monate/12*, differs
  slightly — a Jan–Jul period is `181/365 = 0,4959` here vs `0,5000` there — and can in principle move
  a band at the margin. **Risk accepted and recorded here**; it is the kind of point a Mietrechtler
  should confirm before production.
- **Anchoring the reference year on `valid_from`** makes any full 12-month period, leap or not, come out
  at exactly `1` — a 2024-01-01…2025-01-01 period is 366/366, not 366/365. Without the anchor a leap
  full year would be *lengthened* past the table, which § 5 Abs. 1 S. 4 does not authorise.
- **Rump periods vs *vereinbarte* periods.** S. 4 literally addresses a period *"von unter einem Jahr
  **vereinbart**"*. Our short periods usually arise as a one-off Rumpfperiode (first/last year of a
  tenancy, a changed Abrechnungszeitraum) rather than an agreed short cycle. Applying S. 4 to those as
  well is an interpretation; it is the tenant-protective one and the only one that does not
  systematically under-classify buildings, so we take it. Named here so it is a decision, not an
  accident.

**Edge cases**

| Case | Behaviour | Why |
| --- | --- | --- |
| Period = exactly one year (365 or 366 days) | `period_factor = 1`, table unscaled | S. 4 applies only *unter einem Jahr*; demo path unchanged |
| Period < one year | table bounds × factor | § 5 Abs. 1 S. 4 |
| Period **> 12 months** with a CO₂ split | **refuse** — `HeatingInputError`, explained in German | see below |
| Open-ended top step (`max_intensity_exclusive is None`) | never scaled | it has no bound to shorten; a building already at 95 % stays at 95 % |
| `heated_area_sqm <= 0` | `HeatingInputError` (existing) | no denominator |
| Emissions invoiced over a different period than the agreed one | **input-side**, not the engine's: § 5 Abs. 1 S. 5 requires the invoiced Brennstoffemissionen to be *umgerechnet* to the agreed period **before** they arrive as `total_co2_kg`. The engine trusts its input and must not re-derive it | § 5 Abs. 1 S. 5 |

**Why a period > 12 months is refused rather than scaled.** S. 4 shortens the table for periods *under*
a year and says nothing about longer ones, and for Wohnraum a longer Abrechnungszeitraum is not lawful
in the first place (§ 556 Abs. 3 S. 1 BGB — *jährlich* abzurechnen). Extending the factor upward would
enlarge the bounds, push the building into a **lower** Stufe and shift cost onto the renter — inventing
a legal number in the one direction the 3 % Kürzungsrecht punishes. Leaving the factor at 1 instead
over-classifies and overcharges the landlord. Neither is defensible, so the engine refuses the CO₂
split for such a period and says so in German; the Heizkosten themselves still compute, exactly as with
a missing meter (`docs/03` § 9a rule above). A conscious decision, open to being overruled by the lead.

**Known gap, deliberately not implemented here.** § 5 Abs. 1 S. 3 requires the specific emission value
to be **rounded to one decimal place** (*"auf die erste Nachkommastelle zu runden"*) — the engine
currently classifies the unrounded `Decimal`. At a bound (e.g. 11,96 → 12,0) rounding *before*
classification changes the Stufe, so it needs its own spec and its own fixture and is **not** folded
into this one. Recorded, not guessed.

**Uncertain / would resolve it:** whether *anteilig* is meant day-exact or month-exact, and whether S. 4
applies to a Rumpfperiode that was never *vereinbart*. A published BMWSB Arbeitshilfe, the source of the
official Aufteilungsrechner, or a Mietrechtler's sign-off would resolve both. Until then the two
conventions above stand as conventions.

### Heating/CO₂ golden fixtures

- A central-heating building with consumption meters → base/consumption split + WW separation.
- The same building → CO₂ 10-step selection + landlord/renter split, with `Rechtsstand MM/JJJJ`.
- A mid-period renter change apportioned by degree-days.
- **The disclosure intermediates the result must carry** (`test_heating_disclosure.py`): the pots of
  the §§ 7/8/9 vertical split, the per-party Bemessungen of the horizontal one, the § 9 branch that
  ran with its operands, and the CO₂ Berechnungsgrundlagen incl. the Einstufung band. Contract:
  `docs/08` → *"The carried-intermediates contract (slice 3)"*. Nothing it pins renders yet and no
  euro figure moves — the fixtures exist so that the numbers the tenant will be shown are the numbers
  the engine actually used.
- **Interim period (< 1 year) → the Anlage table is shortened** (`test_co2_period_factor.py`): 1.950 kg
  over 100 m² in a 181-day period is **19,5 kg/m²**, which reads as Stufe *17 – < 22* (Vermieter 20 %)
  against the unscaled table and as Stufe *37 – < 42* (Vermieter 60 %) against the table shortened by
  `181/365` — 18,35 … 20,83. Both readings sit clear of their bounds, so the fixture pins a band change
  and not a rounding accident: **60,00 €/240,00 € wrong vs 180,00 €/120,00 € right** on 300,00 € CO₂
  cost. Companion cases in the same file: a full year and a full leap year (factor exactly 1, nothing
  moves), a building already in the open-ended top step (95 % either way — no over-correction), and a
  > 12-month period, which is refused.

---

## Rounding & reconciliation (applies to both engines)

1. Compute exact fractional shares with `decimal.Decimal`.
2. Floor each to cents.
3. Distribute the leftover cents by **largest fractional remainder** (ties: stable order).
4. Assert `sum(shares) == input_total` — fail loudly if not. No statement ships that doesn't reconcile.

## Why this ordering (engines before UI)

A wrong framework call later costs an app rewrite but never touches these packages or their fixtures.
The pitch's credibility rests entirely on the numbers being right — so the numbers get built and
tested first.
