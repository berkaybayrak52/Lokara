# 03 — NK & heating/CO₂ engines (the crown jewel)

> **Source for the heating/CO₂ half of this file:**
> `berkay-work/Calculations/Spec-Seiten/01b · Heizkosten- & CO₂-Verteilung 3a95fd420731814e9e5be043028d4856.md`
> and `berkay-work/Calculations/Rechtsstand-Register 388f942f178942e9954f8e68238f91cd_all.csv`.
> Transcribed, not copied (`CLAUDE.md` → *"The calculation spec lives in `berkay-work/`"*, rule 2).
> `berkay-work/` is **immutable**: findings about it go in a report, never into the file.
> Where this file and his page disagree on a number, formula or legal value, **his page wins**.

> These are the product. **Pure Python packages, no web-framework/DB/vendor imports.** Deterministic,
> cent-exact, golden-tested (pytest). Built at M1 (NK) and M2 (heating/CO₂), before any UI.
>
> The **document** these engines feed is specified separately in `docs/08-statement-document.md`.

## Shared engine contract

- Input: **normalized** value objects — plain dataclasses / Pydantic models (no SQLAlchemy models, no
  vendor types). Adapters map DB → these.
- Money: integer **cents**; intermediate math with `decimal.Decimal`. Rounding is **per engine**
  (`CLAUDE.md` DoD 4): **heating** uses `round_half_up` per **renter** share at assignment with the
  `Verteilungsrest` to the **Liegenschafts-Residuum** (R1/R5/K9 — see *"Rounding & reconciliation"*
  below and § 9 for the site-by-site wiring); **NK** stays largest-remainder until Berkay's Seite 02
  is transcribed into `docs/09`. Every block reconciles to the input **to the cent once the residual
  is counted**.
- Output: a plain result object (shares per Mietverhältnis, **one Eigentümer-Residuum**, and a
  reconciliation total) — the PDF layer formats it. The Eigentümer line is not a party and exists
  unconditionally, `0,00 €` included (`docs/02`, § 9.2).
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
  carries a **"verify before production"** marker in `rules-store`, unlike the HKVO ratios and the CO₂
  table which are legally fixed. The rule's `source` names both halves, separated — see `docs/08` →
  *"§ 9b HeizkostenV is a prerequisite"*. The stamp dates the **table**; § 9b's own in-force date is
  not asserted anywhere and would need the BGBl. history of the HeizkostenV to establish.
  **Updated 12.08.2026 (K3):** the table is now **VDI 2067 Blatt 1, Ausgabe 12/1983, Tabelle 22**,
  stored as **Zehntelpromille with Σ = 10 000**, `Rechtsstand 12/1983` — replacing the unsourced
  `01/1981` table. See *"Seite 01b … (2) K3"* below for the values, the type change and the money
  consequence.
- External MDL (Messdienstleister) data feeds in through the meter adapter as normalized readings —
  the engine never knows the source.

### CO₂ cost split (CO2KostAufG) — mandatory, part of Tier-1

- **10-step model**: the building's CO₂ intensity (kg CO₂/m²/yr) selects a step; the step sets the
  **landlord vs renter percentage split** of the CO₂ price portion of heating cost.
- The 10-step table lives in the **versioned rules store** (`Rechtsstand` shown on output).
- Missing/incorrect CO₂ split = tenant's **3% reduction right** (§7 Abs. 4 CO2KostAufG) — so this is
  correctness-critical, not cosmetic.

#### Where `total_co2_kg` and `co2_cost` come from — § 3 CO2KostAufG, and never from us

> **Rechtsstand 08/2026** (transcribed 05.08.2026). Sources checked against the consolidated texts on
> gesetze-im-internet.de on 05.08.2026: **§ 3 Abs. 1 und Abs. 3 CO2KostAufG**, **§ 10 Abs. 2 BEHG**,
> **Anlage 2 Teil 4 EBeV 2030**. **No value in this section enters `packages/rules-store`, and no
> engine reads any of them** — that is the point of the section. Standard caveat of `docs/07` applies.

**The engine must never derive the CO₂ cost from a price.** § 3 Abs. 1 CO2KostAufG puts both figures on
the **fuel or heat supplier's invoice**, and the landlord copies them:

| § 3 Abs. 1 Nr. | The supplier states | Our input |
| --- | --- | --- |
| 1 | *"die Brennstoffemissionen der Brennstoff- oder Wärmelieferung in Kilogramm Kohlendioxid"* | `Co2Input.total_co2_kg` |
| 2 | *"den … Preisbestandteil der Kohlendioxidkosten"* | `Co2Input.co2_cost` (cents) |
| 3 | *"den heizwertbezogenen Emissionsfaktor … in Kilogramm Kohlendioxid pro Kilowattstunde"* | not carried today — see the gap in `docs/08` |
| 4 | *"den Energiegehalt … in Kilowattstunden"* | `HeatingInput.total_energy_kwh` |

So a certificate price **must not** become a rules-store value that an engine multiplies by. A landlord
who is billed a different figure than the national fixed price (fixed-price prepayment, a Wärmeliefer­
vertrag, an installment plan) would then receive a statement that contradicts the invoice he is
required to pass through. Any price table we hold is **fixture provenance and plausibility checking**,
never a computation input.

**The reference figures, for checking a fixture's plausibility only.**

| Quantity | Value | Legal basis |
| --- | --- | --- |
| Preis je Emissionszertifikat 2025 (= 1 t CO₂) | **55,00 €** | § 10 Abs. 2 BEHG — *"im Zeitraum vom 1. Januar 2025 bis zum 31. Dezember 2025: 55 Euro"* |
| 2026 | **kein Festpreis** — Versteigerung im Preiskorridor 55,00 € bis 65,00 € | § 10 Abs. 2 BEHG |
| Umsatzsteuer auf diesen Betrag | **+ 19 %** ⇒ **65,45 €/t** für 2025 | § 3 Abs. 3 CO2KostAufG — der Preisbestandteil ergibt sich *"durch Multiplikation der Brennstoffemissionen … mit dem … Preis der Emissionszertifikate … **zuzüglich einer auf diesen Betrag anfallenden Umsatzsteuer**"* |
| Emissionsfaktor Erdgas (heizwertbezogen, H<sub>i</sub>) | **0,0558 t CO₂/GJ = 0,20088 kg CO₂/kWh** | Anlage 2 Teil 4 EBeV 2030 (in Kraft seit 01.01.2023) |
| Emissionsfaktor Gasöl zu Heizzwecken (Heizöl EL) | **0,074 t CO₂/GJ = 0,2664 kg CO₂/kWh** | as above |
| Emissionsfaktor Flüssiggas | **0,0655 t CO₂/GJ = 0,2358 kg CO₂/kWh** | as above |

- **The figure a renter sees on a heating invoice is the gross one.** § 3 Abs. 3 says *zuzüglich
  Umsatzsteuer* in so many words, so for 2025 the invoice rate is **65,45 €/t**, not 55,00 €/t. A
  fixture that implies the bare certificate price is understating the cost being split by 16 %.
- Conversion: `t CO₂/GJ × 3,6 = kg CO₂/kWh` (1 kWh = 3,6 MJ). The invoice factor is **heizwertbezogen**
  (H<sub>i</sub>) because § 3 Abs. 1 Nr. 3 says so; the brennwertbezogene figure (Erdgas 0,1820
  kg CO₂/kWh<sub>Hs</sub>) belongs to energy certificates and must not be used here.
- Real supplier factors vary with gas quality (Erdgas H/L) around the EBeV standard value; a demo
  fixture within roughly ±1 % of it is plausible, one at half of it is not.

**⚠️ Not verified, deliberately:** whether the *renter's* share of the CO₂ cost is itself subject to
USt when the landlord passes it on (kalte vs. warme Betriebskosten, Kleinunternehmer, gewerbliche
Vermietung). Nothing in the engine depends on it and nothing on the statement asserts it. Resolving it
needs a Steuerberater, not reasoning.

#### ⛔ SUPERSEDED — The Stufenmodell is a **per-year** table — a short Abrechnungszeitraum shortens the table

> **SUPERSEDED 12.08.2026 by Berkay's H2** — see *"Seite 01b … (3) CO₂ short billing period"* below.
> The rule now is: **annualise the intensity (`spezifisch × 365 / nTage`) and look it up against the
> UNSHORTENED Anlage table.** Both readings select the **same step**, so no Einstufung and no euro
> moves on selection; they differ in the **figure that is printed**, and the printed figure is what
> § 7 Abs. 3 CO2KostAufG is about.
>
> **This section is kept, marked, and deliberately not deleted.** It quotes § 5 Abs. 1 S. 4 verbatim
> and was argued carefully; without this banner someone reading it would "fix" the engine back to the
> shortened-table reading. If you are about to do that: read § 1 (3) below first, then talk to the
> lead. Everything under this heading describes the **old** behaviour.

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
- ⛔ **SUPERSEDED — Interim period (< 1 year) → the Anlage table is shortened**
  (`test_co2_period_factor.py`). The rule is now H2 (annualise the intensity, unshortened table); this
  file's fixtures move with it in slice 2. Description of the **old** behaviour follows: 1.950 kg
  over 100 m² in a 181-day period is **19,5 kg/m²**, which reads as Stufe *17 – < 22* (Vermieter 20 %)
  against the unscaled table and as Stufe *37 – < 42* (Vermieter 60 %) against the table shortened by
  `181/365` — 18,35 … 20,83. Both readings sit clear of their bounds, so the fixture pins a band change
  and not a rounding accident: **60,00 €/240,00 € wrong vs 180,00 €/120,00 € right** on 300,00 € CO₂
  cost. Companion cases in the same file: a full year and a full leap year (factor exactly 1, nothing
  moves), a building already in the open-ended top step (95 % either way — no over-correction), and a
  > 12-month period, which is refused.

---

# Seite 01b — Heizkosten- & CO₂-Verteilung (transcribed)

> **Source:** `berkay-work/…/01b · Heizkosten- & CO₂-Verteilung ….md`, Status *Fertig*, last edited
> 29.07.2026. **Rechtsstand 07/2026** for the HeizkostenV/CO2KostAufG rules below unless a row says
> otherwise. Fixture IDs are his page numbers (`01b-Fxx`) and are kept, so a fixture in `tests/` can
> always be diffed back against the paragraph it came from.
>
> **Flag discipline (`CLAUDE.md` precedence rule 4):** every convention `K1…K14` below is
> `verify-before-production` in the Rechtsstand-Register. None of them is law. The *methods* are
> statutory; the *numbers* attached to a `K` are ours until verified.
>
> **Scope note.** This page owns the heating math. The document that prints it is `docs/08`. The
> interface is **one € amount per Mietverhältnis**, which fills `heizkostenMessdienstCent` in the NK
> engine — one cost block, never two, never a double deduction.

## 1. What changed on this branch, and why it must not be reverted

Four rules moved. Each is recorded with its reason, because each replaces something that was
deliberately argued for and will otherwise be "restored" by a later reader.

### (1) Rounding — `round_half_up` per share + `Verteilungsrest` to the owner (R1/R5/K9)

**Replaces:** largest-remainder allocation (`distribute_cents`, this file's old *"Rounding &
reconciliation"*, `CLAUDE.md` DoD item 4).
**Reason:** Berkay's R1 rounds a share **once, at the moment it is assigned**, and R5/K9 give the
leftover (`Blockbetrag − Σ Anteile`) to the **owner bucket**, together with the vacancy share. The two
algorithms both reconcile, but they assign different cents to different parties; largest-remainder
moves a cent to whichever *renter* has the largest fraction, which is a silent transfer between
tenants that nothing on the statement can explain. The residual convention can be explained in one
line, and it is the same principle the statement layout already uses for the Eigentümer row
(Seite 01 D12). **±1 ct per block is expected and correct**, and the owner bucket may go slightly
negative (`01b-F01` verbrauchHz: −1 ct).

> **Amended 14.08.2026 — the *destination* is now defined, the *rounding* is unchanged.** "The owner
> bucket" is **one residual line per Liegenschaft**, not a landlord party derived from vacancy; it
> exists even when nothing is vacant. `Antwort-an-Emir_02.md` § 1, `docs/02`, § 9.2 below. R1/R5 as
> stated in this paragraph were confirmed, not changed.

> **VERIFIED BY THE LEAD — do not re-derive.** The canonical €1.200 garbage fixture is **identical
> under both methods**: 600,00 / 178,52 / 181,48 / 240,00, residual **exactly 0**. This change did not
> move the canonical fixture and nobody may claim it did. `CLAUDE.md` DoD item 4 already records this.

`K9` is `Konvention` / `verify-before-production`; the register records *"keine — reine Hauskonvention.
Recherche 27.07.2026: keine externe Quelle vorhanden"*. It is a house rule chosen for explainability,
**not** a norm, and the statement must never present it as one.

### (2) K3 — the degree-day table is VDI 2067 Bl. 1, Ausgabe 12/1983, Tab. 22

**Replaces:** the unsourced table `170 150 130 80 40 15 10 10 30 80 120 165` that carried
`TODO(verify)` in `packages/rules-store`.
**Reason:** the old table was sourced to nothing; Berkay's is sourced to a named VDI edition and table
number. Eight months agree, four do not (Jun, Jul, Aug, Dez). § 9b Abs. 2 HeizkostenV demands
*"Gradtagszahlen nach anerkannten Regeln der Technik"* and does not print a table, so the table is a
convention either way — but a convention with a citation beats one without.

| Month | Jan | Feb | Mär | Apr | Mai | Jun | Jul | Aug | Sep | Okt | Nov | Dez |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ‰ (display) | 170 | 150 | 130 | 80 | 40 | 13,3 | 13,3 | 13,4 | 30 | 80 | 120 | 160 |
| **Zehntelpromille (stored)** | 1700 | 1500 | 1300 | 800 | 400 | 133 | 133 | 134 | 300 | 800 | 1200 | 1600 |

**This is a type change, not a value change.** Jun/Jul/Aug are 400/3 and cannot be represented as
integer promille, so the stored unit is **Zehntelpromille with `Σ = 10 000`**:

- `packages/domain` → `DegreeDayTable.promille_by_month: tuple[int, …]` with `sum == 1000`
  becomes `DegreeDayTable.tenth_promille_by_month: tuple[int, …]` with `sum == 10_000`.
  **Field name and invariant both move**, and every consumer of `degree_day_weight()` with them —
  including `HeatingLine.degree_day_promille`, whose unit becomes Zehntelpromille.
- Display value = stored ÷ 10. Never store the ‰ integer.
- `packages/rules-store` → the rule's `valid_from` dates the **table**: `12/1983` (VDI 2067 Blatt 1,
  Ausgabe 12/1983, Tabelle 22), replacing the unsourced `01/1981`. Flag stays
  `verify before production`; § 9b's own in-force date is still not asserted anywhere.

**Money consequence, expected and correct:** Jan–Jun goes **585,0 ‰ → 583,3 ‰**, Jul–Dez
**415,0 ‰ → 416,7 ‰**. The demo's unit-B heating row therefore re-bases
**778,79 € / 552,47 € → 776,52 € / 554,74 €**. Recomputed under *both* rounding methods: the demo
chain is **identical** under largest-remainder and under R5/K9, so this pair moves once, because of
K3, and for no other reason.

### (3) CO₂ short billing period — annualise the intensity (H2), do not shorten the table

**Replaces:** the § 5 Abs. 1 S. 4 reading in `packages/heating-engine/.../co2.py` and the section
*"The Stufenmodell is a per-year table"* below, which is now **SUPERSEDED**. That section quotes the
norm verbatim and was carefully argued — it is kept in place, marked, rather than deleted, so nobody
re-derives it and "fixes" the engine back.

```
if periode.nTage not in (365, 366):
    spezifisch_kg_pro_m2_a = (co2Gramm / 1e6) / gesamtflaecheM2 × 365 / nTage
step = lookup10(spezifisch_kg_pro_m2_a)      # against the UNSHORTENED Anlage table
```

**Reason to prefer H2, and the honest statement of what it costs.** Both readings select the **same
step** — `i × (365/d) < b` ⇔ `i < b × (d/365)` — so no Einstufung changes and no euro moves on step
selection. They differ only in **which figure is printed**, and the printed figure is what § 7 Abs. 3
CO2KostAufG is about. The old reading printed a *period* figure (kg CO₂/m² over 275 days) under a
column header that says **`kg CO₂/m²/a`**, and printed a *shortened* band (`20,34 – 24,11`) that
appears in no statute annex. H2 prints an annualised figure against the statute's own bounds
(`27 – 32`), which is the pair a tenant can check against the published Anlage. Berkay's page records
verification against the norm text on 26.07.2026.

Engine consequences:

- `Co2Result.intensity_kg_per_sqm` becomes the **annualised** kg/m²/a.
- `Co2Result.period_factor` (the bound-shortening factor, ≤ 1) is replaced by
  `Co2Result.annualisation_factor` = `365 / nTage`, which is **≥ 1** for a short period and exactly
  `1` when `nTage ∈ {365, 366}`. Renaming is deliberate: leaving the old name attached to an inverted
  meaning is how a renderer silently prints the wrong band.
- `band_min_inclusive` / `band_max_exclusive` become the **unscaled** Anlage bounds.
- The two day counts (`period_days`, `reference_year_days`) stay — the disclosure copy needs them.

**Divisor:** Berkay's H2 uses a flat **365**, and triggers on `nTage ∉ {365, 366}`. This is *not* the
anchored reference year the old convention used (`[valid_from, same date +1 year)`). A 366-day
non-calendar period is left un-annualised under his rule. Transcribed as written; noted as a
convention, flagged below.

**Periods > 12 months are still refused**, and that is consistent, not a leftover: his page E24 makes
a period > 12 months a **validation error inherited from Seite 01 (E6)**, so annualisation never sees
one. The German refusal message in the engine stays.

### (4) Ho/Hu — the energy reference travels with the number (NEW)

**Adds** something the code has nothing for, and Berkay says harden it **before** any real CO₂ split.

German gas invoices bill in **Brennwert (Ho)** kWh. The EBeV 2030 fallback emission factor is
**Heizwert (Hu)**-based (§ 3 Abs. 1 Nr. 3 CO2KostAufG demands the *heizwertbezogene* factor
explicitly). Multiplying Ho-kWh by a Hu factor overstates emissions by roughly **11 %**. At a step
boundary that is a whole Stufe, systematically **against the landlord**, on a document the tenant may
rely on — and it **fails silently**: every intermediate looks plausible.

**Design (his, adopted as given):**

- The factor object carries `bezug: "Ho" | "Hu"`. The input kWh carries the **same** reference.
- Invoices are Ho → use the **Ho factor** directly.
- **No conversion step anywhere.** That is the whole point: a `× 0,903` correction is a step someone
  forgets, or applies twice. There is no place in the engine where a reference is converted.
- A reference mismatch is a **hard error**, never a silent coercion. `EnergyReferenceMismatchError`,
  refused at the boundary, explained in German.

**Two register additions, transcribed:**

1. The rule is **generic**. Whenever the engine derives kWh itself — from m³ of gas, from litres of
   oil (K7, 10 kWh/l) — it uses the **same reference the invoice uses**. The reference is a property
   of the quantity, not of the fuel.
2. The **Abrechnungsbrennwert is printed on the invoice**. If OCR pulls it, use it instead of a flat
   default. A flat default is the last resort, not the normal path.

**Scope — this matters.** The K4 factors are `nur Fallback`: they apply **only** where the supplier has
not stated the mass under § 3 CO2KostAufG. Where the supplier states it (the normal case, and the demo
case), no factor is read at all and the Ho/Hu question does not arise.

**Values — taken from the Rechtsstand-Register, as-is (precedence rule 3), with flags intact.**

| Fuel | kg CO₂/kWh | Bezug | Flag | Source |
| --- | --- | --- | --- | --- |
| Erdgas (K4) | **0,201** | Hu | `verify-before-production`, Konvention | EBeV 2030 Anlage 2 Teil 4 Nr. 6 |
| Erdgas (K4) | **0,181** | Ho | `verify-before-production`, Konvention | same row, *"alternativ direkt 0,181 kg CO₂/kWh(Ho)"* |
| Heizöl EL (K4) | **0,266** | Hu | `verify-before-production`, Konvention | EBeV 2030 Anlage 2 Teil 4 Nr. 3b |
| Flüssiggas (K4) | **0,236** | Hu | `verify-before-production`, Konvention | EBeV 2030 Anlage 2 Teil 4 Nr. 5b (corrected 27.07.2026 from 0,234) |

⚠️ **The register states no Ho counterpart for Heizöl or Flüssiggas.** None is invented here. Until
one is sourced, an Ho quantity of oil or LPG has **no factor** and must be refused rather than
converted — which is exactly the behaviour the hard error gives.

## 2. What did **not** move — nine values independently confirmed

Worth recording, because a reader who sees four rules move will otherwise assume everything did. The
lead's value-by-value audit (`berkay-work/COLLISION-MAP-01b.md` § 1) found the engine's legal core
already correct:

| Rule | Value | Where it already lives |
| --- | --- | --- |
| CO₂ 10-step **bounds** | 12 / 17 / 22 / 27 / 32 / 37 / 42 / 47 / 52, left-closed right-open | `rules-store/rules/co2_split.py` |
| CO₂ 10-step **landlord shares** | 0 / 10 / 20 / 30 / 40 / 50 / 60 / 70 / 80 / 95 % | same |
| § 9 Abs. 2 substitute equation | `Q = 2,5 × V × (tw − 10)` [kWh/a], `tw` 60 °C ⇒ 125 kWh/m³ | `rules-store/rules/warm_water.py` |
| § 9 Abs. 3 fallback | `Q = 32 × A_Wohn` | same |
| §§ 7/8 statutory band | 50–70 % consumption-based | `rules-store/rules/heating_split.py` |
| K1 default | Grundkosten 30 % (consumption 70 %), configurable 30–50 % | same |

Interval semantics confirmed on both sides: **left-closed, right-open** — exactly `12,00` is step 2
(10 %), exactly `52,00` is step 10 (95 %).

## 3. Inputs (§ 3 of the page, condensed)

Money is **integer cents**. Dates are **day-granular, both boundary days inclusive**. Areas are m²
with two decimals. Emissions are **integer grams** internally (R4); the step lookup uses the
**unrounded** value.

| Group | Fields that reach the engine |
| --- | --- |
| Plant | `energietraeger` {erdgas, heizoel, fluessiggas, fernwaerme, waermepumpe, biomasse} · `verbundeneAnlage` · `gebaeudeTyp` {wohn, nichtwohn, gemischt} · `denkmalschutz` / `milieuschutz` / `ausschlussNachweis` (each requires a stored document) · `grundkostenAnteilProzent` 30–50, default 30 (K1) |
| Invoices | `zeitraumVon/Bis` · `mengeKwh` **with its energy reference (Ho/Hu)** · `betragCent` · `co2Gramm` (nullable → K4 fallback) · `co2KostenCent` (nullable) · `energiemix`, `thgGprokWh`, `primaerenergiefaktor`, `steuernCent` (§ 6a Abs. 3 Nr. 1 disclosure) · `tankAnfangL` / `tankEndeL` (oil) |
| Operating costs | `betriebsstromCent`, `wartungCent`, `messungCent`, `ausstattungCent`, `sonstigeCent` |
| Meters | `heizgeraet.typ` {hkv, waermezaehler, wwZaehler} · `nummer` · `raum` · **`bewertungsfaktor`** (K-Wert, 2 dp) · `ablesung.wertAlt/wertNeu` (1 dp) · `ablesung.datum/anlass` {jahres, zwischen, einzug, auszug} · `vWwM3` · `tw` (default 60 °C, K5) · `wohnung.wwM3` · `fernablesbar` |
| Rules tables | `co2PreisCentProTonne` · `emissionsfaktor` **+ its Bezug** · `co2Stufentabelle` · `gradtagstabelle` (**Zehntelpromille, Σ 10 000**) · `klimafaktor` (PLZ, Periodenende) |

⚠️ **`bewertungsfaktor` does not exist in our data model.** H5 cannot be implemented without it; that
is a `docs/02` change and its own slice.

## 4. Formula (H1 … H8)

**H1 — Gesamtkosten der Anlage (§ 7 Abs. 2 HeizkostenV)**

```
gesamtCent = Σ rechnung.betragCent          (allocated per K8, see H1a)
           + betriebsstromCent + wartungCent + messungCent + ausstattungCent + sonstigeCent
```

- **H1a — period allocation (K8).** An invoice overlapping the billing period only partly contributes
  `round_half_up(betragCent × überlappungstage / rechnungstage)`. Coverage is reported; `< 100 %`
  raises a **non-dismissible** warning. K8 is linear in *days*, not degree-days, so a Nov/Dez gap
  **understates** heating cost — which is why the warning may not be click-away.
- **H1b — oil (K7).** `verbrauchtL = tankAnfangL + Σ zukaufL − tankEndeL`; cost basis is the weighted
  average price over `tankAnfangL + Σ zukaufL`. **CO₂ is computed on the consumed quantity, never on
  the purchased quantity** (`01b-F19`).

**H2 — CO₂ split, deducted before everything else**

```
co2Gramm = Σ rechnung.co2Gramm                      # fallback K4 only on § 3 breach
co2Cent  = Σ rechnung.co2KostenCent                 # see the open collision in § 7 below
spezifisch = (co2Gramm / 1e6) / gesamtflaecheM2                                [R2, R4]
if nTage not in (365, 366): spezifisch ×= 365 / nTage        # annualise BEFORE the lookup

gebaeudeTyp wohn|gemischt → vermieterAnteil = lookup10(spezifisch)   # Anlage CO2KostAufG
gebaeudeTyp nichtwohn     → vermieterAnteil = 50                     # § 8 CO2KostAufG
energietraeger ∈ {waermepumpe, biomasse} → CO₂ module OFF, Abzug = 0
denkmalschutz || milieuschutz            → vermieterAnteil /= 2      # § 9 Abs. 1
ausschlussNachweis                       → vermieterAnteil = 0       # § 9 Abs. 2

co2AbzugVermieterCent = round_half_up(co2Cent × vermieterAnteil / 100)         [R1, R6]
umlagefaehigCent      = gesamtCent − co2AbzugVermieterCent
```

**H3 — Warmwasser-Abtrennung (§ 9 HeizkostenV), only if `verbundeneAnlage`**

```
a) WW-Wärmezähler present   → qWwKwh = measured kWh              # § 9 Abs. 2 S. 1, priority
b) WW volume meter present  → qWwKwh = 2,5 × vWwM3 × (tw − 10)   # § 9 Abs. 2 S. 2      [R3]
c) no measurement           → qWwKwh = 32 × gesamtflaecheM2      # § 9 Abs. 3 + warning [R3]

anteilWw     = qWwKwh / verbrauchKwhGesamt                                     [R2]
kostenWwCent = round_half_up(umlagefaehigCent × anteilWw)                      [R1]
kostenHzCent = umlagefaehigCent − kostenWwCent          # complement, so the sum is exact
```

Path c) carries a warning: the flat 32 kWh/m² **systematically overstates** warm water in efficient
buildings and penalises frugal users (`01b-F12`: Weber +7,04 €, Muster −16,33 € against `01b-F01`).

**H4 — Grund-/Verbrauchskosten per block (§ 7 Abs. 1, § 8 Abs. 1, K1)**

```
grundHzCent     = round_half_up(kostenHzCent × grundkostenAnteilProzent / 100)
verbrauchHzCent = kostenHzCent − grundHzCent
grundWwCent     = round_half_up(kostenWwCent × grundkostenAnteilProzent / 100)
verbrauchWwCent = kostenWwCent − grundWwCent
```

**H5 — Geräteaggregation (before H6)**

```
einheitenGeraetSegment = round_half_up((wertNeu − wertAlt) × bewertungsfaktor, 1 dp)   [R7, K11]
if wertNeu < wertAlt → REJECT the reading. Never abs().
einheitenMietverhaeltnis = Σ segment values of that unit, per usage segment
nenner = Σ einheitenWohnung over the plant
```

A tenant change needs **two** readings (Auszug **and** Einzug, § 9b Abs. 1). With only one, the
vacancy period cannot be separated from the following tenancy (`01b-F27`: ~54 units of somebody
else's consumption would land on the incoming tenant). A segment without its own reading is
apportioned by K3 instead (§ 9b Abs. 3).

**H6 — Distribution to Mietverhältnisse**

| Block | Key | Denominator | Tenant change |
| --- | --- | --- | --- |
| `grundHz`, `grundWw` | m²-days (K2) | `Σ wohnflaecheM2 × nutzungstage` **incl. vacancy** | automatic |
| `verbrauchHz` | HKV units or Wärmezähler kWh | Σ over all units of the plant | interim reading (§ 9b Abs. 1); else K3 (§ 9b Abs. 3) |
| `verbrauchWw` | m³ per unit | Σ m³, **or the measured central volume** (E22) | interim reading; else time-proportional (§ 9b Abs. 2) |

```
anteilCent = round_half_up(blockCent × gewicht / nenner)                       [R1, R2]
rest       = blockCent − Σ anteilCent  →  Eigentümer                           [R5, K9]
heizkostenMessdienstCent[i] = grundHz[i] + verbrauchHz[i] + grundWw[i] + verbrauchWw[i]
```

**Guard:** any denominator `= 0` → the block is **not** distributed; the engine raises a **blocking**
readiness error. A silent fallback to area distribution is **forbidden** (E17) — it would look correct
and expose the landlord to § 12 Abs. 1 S. 1 (15 %) per tenant. This is distinct from the § 9a Abs. 2
fallback the engine already has, which is the lawful path when readings are *missing*.

**H7 — MDL path (Messdienstleister).** Ingest, validate, pass through; **never recompute** (K14 — we
have no legal position to overrule a Messdienst, and two competing numbers for one tenant are a
liability). `M2`: if the statement already shows the CO₂ split, amounts are net → **no second
deduction**; otherwise run H2 on the MDL total and rescale every amount by
`umlagefaehigCent / mdl.gesamtkostenCent` — recomputing the quotient each time, never a rounded
factor. `M3` control sum is **blocking**, with `toleranz = number of amount positions read` (a
Messdienst rounds every position, so ≤ 1 ct per position is normal); the reference is
`umlagefaehigCent` in the net branch and `mdl.gesamtkostenCent` in the gross branch. An OCR decimal
shift is orders of magnitude larger and is still caught (`01b-F29`: 313,04 €).

**H8 — § 6a Abs. 3 Nr. 5 comparison.** Both years are weather-adjusted, each with its **own** DWD
Klimafaktor (K12); `KF > 1` (mild year) **raises** the adjusted value. **Only heat is adjusted; warm
water passes through unadjusted** (§ 6a Abs. 3 S. 2–3). Missing KF → print the comparison
**unadjusted with a note**, never substitute `1,00`. Output is a **graph** (§ 6a Abs. 3 S. 1 Nr. 5),
not only a percentage. Import spec for the DWD file is referenced by his page but **is not in
`berkay-work/`**. PLZ in the DWD file carry **no leading zero** — pad to five digits on import or the
adjustment silently disappears for all of eastern Germany.

## 5. Rounding rules (R1 … R7) — these are the engine's rounding contract

| ID | Rule |
| --- | --- |
| R1 | **Money** — integer cents everywhere. `round_half_up` to whole cents, **once**, at the moment a share is assigned. Never on an already-rounded value. |
| R2 | **Quotas** — never rounded. Exact `Decimal` (≥ 28 significant digits). Recompute the quotient; never reuse a rounded factor. |
| R3 | **Energy** — kWh, 3 dp, `round_half_up`. |
| R4 | **Emissions** — integer **gram** internally. Display kg with 1 dp, kg/m²/a with 2 dp. **The step lookup uses the unrounded value.** |
| R5 | **Residual** — `Blockbetrag − Σ gerundete Mieteranteile = Verteilungsrest` → the **Liegenschafts-Residuum**, together with the vacancy share. ±1 ct per block on top of that share, sign either way (K9). *Amended 14.08.2026: "owner bucket" is one line per Liegenschaft, never a derived landlord party — § 9.2, `docs/02`.* |
| R6 | **Statutory percentages** applied to cent amounts, `round_half_up`. |
| R7 | **Device units** — 1 dp, `round_half_up` (K11). The flat's total is the sum of the **rounded** device values. |

**API consequence for `packages/domain`.** `distribute_cents` (largest-remainder) is not this rule.
Two primitives implement R5, and they are not interchangeable:

```python
# Pot complements only (§ 9.1 sites #1, #5, #9, #10) — the residual is the other *pot*.
distribute_cents_half_up(total, weights, *, residual_index) -> list[Cents]
#   share_i          = round_half_up(total × w_i / Σw)   for i != residual_index
#   share_residual   = total − Σ (other shares)

# Party allocations (§ 9.1 sites #2, #3, #4, #6, #7, #8) — the residual is the
# Liegenschafts-Residuum, which is NOT a party. Added 14.08.2026.
distribute_cents_owner_residual(pot, renter_weights, *, owner_weight) -> tuple[list[Cents], Cents]
#   denominator      = Σ renter_weights + owner_weight   # D0/E19: the vacancy is in the DENOMINATOR
#   renter_i         = round_half_up(pot × w_i / denominator)
#   owner            = pot − Σ renter_i                  # may be ±1 ct off the vacancy share,
#                                                        # and may be negative
#   denominator == 0 → every renter 0, owner = pot       # Seite 01 E3, never a ZeroDivisionError
```

`Σ renter shares + owner == pot` holds **by construction**, so the reconciliation assertion every
allocation test carries does not weaken.

**Why two functions and not one with an optional index.** `residual_index` says *the owner is the
party at index i*. That is the model § 9.2 replaced, and the signature lets a caller pass the owner
as a party by accident — which is exactly the "computed separately" that Seite 01 D12 forbids. The
second signature cannot express it: there is no slot for an owner share, only for an owner *weight*
that lands in the denominator.

**~~Open design point, not decided here.~~ Answered 14.08.2026.** This paragraph used to record that
Berkay's page did not say which line absorbs the residual when nothing is vacant, and that the
fixtures *assumed* an unconditional owner line. `Antwort-an-Emir_02.md` § 1.3 Frage 1 confirms the
assumption and removes the question with it: *"Existiert die Eigentümerzeile immer? → **Ja.** Auch
bei 0,00 €, auch ohne Leerstand, auch ohne Eigennutzung."* It is now settled, not assumed — see
§ 9.2 and `docs/02`.

## 6. Edge cases (§ 5 of the page)

| # | Case | Behaviour | Fixture |
| --- | --- | --- | --- |
| E1 | Supplier states no CO₂ mass/cost (§ 3 CO2KostAufG breach) | K4 fallback + **warning** + § 7 Abs. 4 risk flag | `01b-F02` |
| E2 | `spezifisch` exactly on a bound (12,00 / 52,00) | Left-closed → the **higher** step | `01b-F03`, `01b-F04` |
| E3 | Rounds *up* to a bound but is below it | Lookup on the **unrounded** value (R4). Print the **truncated** figure (`11,99`), never `12,00` next to a 0 % share | `01b-F05` |
| E4 | Billing period ≠ 12 months | Annualise `× 365 / nTage` **before** the lookup | `01b-F06` |
| E5 | Nichtwohngebäude | Flat 50/50 (§ 8 CO2KostAufG); gemischt → step model | `01b-F07` |
| E6 | Denkmal-/Milieuschutz | Landlord share **halved** (§ 9 Abs. 1); full exclusion only with stored proof (Abs. 2 + 3) | `01b-F08`, `01b-F09` |
| E7 | Wärmepumpe / Biomasse | CO₂ module off: no deduction, **no** Pflichtausweis, **no** step indicator | `01b-F10` |
| E8 | Hot water not measurable | § 9 Abs. 3 path c + warning | `01b-F12` |
| E9 | Plant not connected | No WW split; one block | `01b-F13` |
| E10 | `grundkostenAnteilProzent` = 50 | Lawful; shifts money to large **and vacant** units — show the owner's extra burden **before** saving (32,85 € → 54,78 €) | `01b-F14` |
| E11 | Tenant change **with** interim readings | Two tenancies, measured units each | `01b-F01`, `01b-F27` |
| E12 | Tenant change **without** interim reading | § 9b Abs. 3 → K3; the vacancy segment's units go to the owner | `01b-F16` |
| E13 | Single device failure, ≤ 25 % of area | § 9a Abs. 1 estimate; arithmetic unchanged, **provenance flagged on the statement** | `01b-F17` |
| E14 | Failure affects > 25 % of area | § 9a Abs. 2 → the **entire** distribution by area; consumption blocks dissolve. § 12 Abs. 1 S. 1 does **not** apply — § 9a is the lawful path | `01b-F18` |
| E15 | Oil: purchase ≠ consumption | K7 tank logic; CO₂ on the **consumed** quantity | `01b-F19` |
| E16 | Fernwärme | Supplier states cost + CO₂ → pass through, **but the step model still runs** | `01b-F20` |
| E17 | No consumption data at all (denominator 0) | **Hard stop.** No silent area fallback | `01b-F21` |
| E18 | Negative reading delta (meter swap/rollover) | Reading **rejected**; two segments must be summed. Never `abs()` | `01b-F22` |
| E19 | `spezifisch` outside 5–70 kg/m²/a (K6) | Warning only, **never** a block — an efficient building must stay billable | `01b-F23` |
| E20 | Invoice period overlaps the billing period | K8 linear day allocation + **non-dismissible** coverage warning | `01b-F24` |
| E21 | Not remote-readable / no UVI / no CO₂ disclosure | Display the 15 % / 3 % / 3 % **risk amounts**. **Never auto-reduce** — the reduction is the tenant's right, not the landlord's calculation. Whether the three 3 % rights cumulate is `[UNSICHER]`: **do not implement summation** | `01b-F25` |
| E22 | Σ unit WW meters ≠ measured central volume | `qWwKwh` from the **central** value; distribute by unit meters against the **central** denominator; the gap stays with the owner. Thresholds: ≤ 10 % silent (Verkehrsfehlergrenze), > 10 % Hinweis, > 20 % Warnung with the legal consequence | `01b-F26`, `F26b`, `F26c` |
| E23 | Vacancy in the billing period | Falls out automatically — denominators are object-level. Owner bucket | `01b-F01` |
| E24 | Period > 12 months | Validation error, inherited from Seite 01 (E6) | — |
| E25 | Several radiators per unit, different K-Werte | H5 aggregation; the device list is stored **and printed** (K10) | `01b-F27` |
| E26/E27 | MDL statement with / without CO₂ split | Net (no second deduction) / H2 + proportional rescale, round-trip ≤ 1 ct → owner | `01b-F28a/b` |
| E28 | OCR decimal shift | Control sum M3 fails → **run blocked** | `01b-F29` |
| E29 | MDL statement with no CO₂ information at all | Pflichtausweis impossible → § 7 Abs. 4 risk per tenancy, shown before dispatch | `01b-F30` |
| E30/E31 | § 6a Abs. 3 block incomplete / no preceding period | 3 % risk; and print a note rather than an empty graph | `01b-F31` |

## 7. Open discrepancies — recorded, **not** resolved

These are for Berkay and the lead. None of them is decided in this transcription, and none of them has
a fixture asserting a chosen answer.

1. **Erdgas emission factor — two value pairs.** The lead's brief gives **Hu 0,2016 / Ho 0,1820**; the
   Rechtsstand-Register row *"Emissionsfaktor Erdgas (K4)"* gives **Hu 0,201 / Ho 0,181** with
   `× 0,903`. Both pairs are internally consistent; they differ by ~0,3 %. Precedence rule 3 says the
   register is imported as-is, so **the register values are used** and the lead's numbers are recorded
   here as the open item. Neither is treated as fact.
2. **The register's own Ho/Hu pair is not exactly reciprocal.** `0,201 × 0,903 = 0,181503`, not
   `0,181`. The register says *"beide Wege führen zum selben Ergebnis"*; they agree to about 0,3 %,
   not exactly. On 28.000 kWh that is 5.068 kg (direct Ho) vs 5.082 kg (converted) — 14 kg. This is a
   further argument for the no-conversion design, and a question for Berkay.
3. **The register row contradicts itself on whether to convert.** The *Betrag* field says Ho-kWh must
   be converted `× 0,903`; the *Rechtsgrundlage* field on the same row says the `3,2508 GJ/MWh` factor
   *"betrifft die BEHG-Meldekette des Inverkehrbringers … nicht die Rechnungsausweisung nach § 3"*.
   The adopted design (carry the reference, never convert) is consistent with the second half.
4. **No Ho factor exists for Heizöl or Flüssiggas** in the register. Not invented; an Ho quantity of
   either is refused.
5. **The CO₂ *cost* fallback is not transcribed as an engine path.** His H2 allows
   `co2Cent = co2Gramm/1e6 × co2PreisCentProTonne` when the supplier states no cost. That collides
   head-on with the rule already in this file (*"Where `total_co2_kg` and `co2_cost` come from — § 3
   CO2KostAufG, and never from us"*): a landlord billed a different figure than the national price
   would receive a statement contradicting the invoice he must pass through. Berkay flags the same
   fallback as **unsafe from 2026** (no single BEHG price: auction 55–65 €/t, sales phase 68 €,
   make-up 70 €) and says it must ask the user or block. **Two rules disagree and neither was
   pre-decided for this slice**, so the *mass* fallback (kWh × factor → gram) is specified and
   fixtured, and the *cost* fallback is not. Lead's call.
6. **`01b-F19`'s counter-example does not recompute.** The trap figure (CO₂ on purchased instead of
   consumed oil) is printed as `abzug 90.204 ct`, difference `492,40 €`. Recomputed:
   7.700 l × 10 kWh/l × 0,266 = 20.482 kg → 112.651 ct → 80 % = **90.121 ct**, difference **491,57 €**.
   The *asserted* value (40.964 ct on the consumed quantity) is correct and reproduces exactly; only
   the illustrative wrong-path number is off by 83 ct. Reported, not edited.
7. **`01b-F16` and `01b-F26` print a party's own rounded share where the residual rule gives one cent
   less.** F16 prints the vacancy segment at `692` (its own `round_half_up`), F26 the uncaptured 4 m³
   at `4.227`; his own Summenproben (`3.977` and `338.218`) confirm the residual-derived values
   `691` and `4.227`. Presentation inconsistency in the table, not a calculation error — the fixtures
   assert the residual-derived values, which are the ones his checks reconcile to.
8. **The annualisation divisor is a flat 365 with the trigger `nTage ∉ {365, 366}`.** A 366-day
   non-calendar period is therefore not annualised. Transcribed as written; worth a sentence from
   Berkay.
9. **§ 6a Abs. 3 S. 4 Bekanntmachung** (the BMWi/BMI notice that would give the Vermutungswirkung for
   weather adjustment) is marked *"nicht gefunden"* in his own Rechtsgrundlage table. K12 (DWD
   Klimafaktoren) stands as the strongest available choice until it is found.
10. **CO₂ price from 2026** — no single price exists. Open in his Non-Goals as *"Entscheidung offen —
    To-Do Berkay"*. The 2025 fixture (55 €/t + 19 % USt = 65,45 €/t) is unaffected.
11. **`08-F01` (MDL path) and `01b-F01` (self-billing path) compute the same building with one
    different input.** They are **two data paths** and must **never** be asserted against each other.
    This is repeated as a comment in the fixture file, because "unifying" them is the obvious-looking
    refactor that would be wrong.
12. **Where the 5 ct of block (c) is disclosed — his prose and his own rendering differ.**
    `Antwort-an-Emir_02.md` § 1.3 says the 17.536-vs-17.531 difference *"wird als Block (c) offen
    ausgewiesen"*. His rendered `08-F21` prints **`(c) Rundungsdifferenz 0,00`** and never prints
    17.536 at all — because with **exactly one** empty unit the per-Kostenart residual column *is*
    that unit's (a) figure, so nothing is left over. Both are consistent once (c) is *defined* as
    `Residuum − Σ (a)`, and this repo defines it that way (`docs/02`); the 17.536 is a counterfactual
    that proves the rule, not a printed figure. (c) becomes non-zero only when (a) is itemised across
    **more than one** empty unit. Recorded rather than silently smoothed over — a sentence from
    Berkay would close it.
13. **Fixture-ID drift between his pages.** His answer cites `08-F21` / `08-F22` / `08-F06`; the
    numbers behind them now live on Seite 02 as `09-F19` / `09-F07` / `09-F08`+`09-F19`. Same
    arithmetic, two page numberings. Every fixture in this repo names **both**, so the two can be
    matched later without re-deriving anything.

## 8. Known gaps — specified here, no fixture, no code

Recorded so that an absent feature is a known absence rather than a silent one.

- **H5 needs `bewertungsfaktor`** on the meter/device model (`docs/02`). Until then device
  aggregation cannot run and `01b-F27` cannot be a fixture.
- **Two readings per tenant change** (§ 9b Abs. 1, Auszug *and* Einzug) — `HeatingUnit` carries a
  single `heat_consumption` per unit, so a *measured* per-tenancy reading cannot be expressed.
  `01b-F01` is therefore fixtured at the **allocation-primitive** level (its four blocks) rather than
  end-to-end through `calculate_heating_statement`; the end-to-end fixture waits on this input shape.
- **Building type on the CO₂ path** (§ 8 CO2KostAufG, `nichtwohn` → flat 50 %) — `co2.py` has no
  building type at all.
- **Denkmal-/Milieuschutz** (§ 9 Abs. 1/2 CO2KostAufG) — not modelled.
- **Heat pump / biomass** → CO₂ module entirely off — not modelled.
- **The whole MDL path (H7)** and **the UVI comparison (H8)** — nothing exists. `StubMeterGateway` is
  a fixture, not the MDL path.

## 9. Wiring R1/R5/K9 and Ho/Hu into the engine — the site-by-site decision

> **Written 13.08.2026 before the code; wired the same day and now describes the engine.** It was
> written because two of the four rules of § 1 had been transcribed but never reached the engine:
> `distribute_cents_half_up` had **zero production callers** and `EnergyReference` was imported by
> nothing outside `domain`/`rules-store`, so **no boundary refused an Ho/Hu mismatch**. Both are
> wired now — the table below is the map of what the code does, not a plan. K3 and H2 had already
> landed and were not touched.
>
> Rechtsstand: the *methods* below are §§ 7/8/9/9b HeizkostenV and §§ 3/7 CO2KostAufG; the
> **residual convention K9** and the **K4 emission factors** are `Konvention` /
> `verify-before-production`, **Rechtsstand 07/2026** in the Rechtsstand-Register. No output may
> present either as a norm.
>
> ⚠️ **Amended 14.08.2026 — § 9.2 was replaced.** `berkay-work/Antwort-an-Emir_02.md` § 1 answers the
> two conventions § 9.2 used to carry, and answers them by **replacing the model**: the
> Eigentümeranteil is not a party derived from vacancy, it is one structural residual line per
> `(Liegenschaft, Kostenart)`. The rounding decisions in the table below are unchanged and were
> confirmed; what changed is *who* the residual is handed to and *how many* such rows exist. The
> model itself lives in `docs/02` → *"The Eigentümeranteil is a residual line, not a party"*; § 9.2
> below records what it superseded, so the old conventions are not restored by a later reader.

### 9.1 Which of the ten split sites switch

`heating-engine` calls the largest-remainder `distribute_cents` at ten places. They are not all the
same operation, so they do not all get the same answer.

| # | Site | What it splits | Decision | Who holds the residual | Reason |
| --- | --- | --- | --- | --- | --- |
| 1 | `engine.py:77` | heating pot → (Grund, Verbrauch), §§ 7/8 + K1 | **half-up**, residual on the **consumption** pot | no owner bucket — the *complement pot* | H4 is written as `grundHz = round_half_up(kostenHz × p/100)` and `verbrauchHz = kostenHz − grundHz`. The rounded side is named by the formula. |
| 2 | `engine.py:78` | `grundHz` → **renters** by m²·Tage (K2) | **half-up** | the **Liegenschafts-Residuum** (§ 9.2) | H6 + R1/R5/K9 — the archetypal Blockbetrag→Parteien allocation. |
| 3 | `engine.py:87` | heat consumption pot → renters by **area** (§ 9a Abs. 2 fallback) | **half-up** | the Liegenschafts-Residuum | § 9a Abs. 2 replaces the *key*, not the rounding rule. Same operation as #2 with different weights. |
| 4 | `engine.py:90` | `verbrauchHz` → renters by HKV-Einheiten / kWh | **half-up** | the Liegenschafts-Residuum | H6. `01b-F01`'s verbrauchHz block is the case where the residual is **−1 ct**. |
| 5 | `engine.py:99` | warm-water pot → (Grund, Verbrauch) | **half-up**, residual on the consumption pot | complement pot | H4, second line pair. |
| 6 | `engine.py:100` | `grundWw` → renters by m²·Tage | **half-up** | the Liegenschafts-Residuum | H6. |
| 7 | `engine.py:105` | ww consumption → renters by **area** (§ 9a Abs. 2) | **half-up** | the Liegenschafts-Residuum | as #3. |
| 8 | `engine.py:108` | `verbrauchWw` → renters by m³ | **half-up** | the Liegenschafts-Residuum | H6. `01b-F26`: the 4 m³ no unit meter saw stay with the owner as **4.227 ct**. |
| 9 | `engine.py:363` | umlagefähig → (Warmwasser, Heizung), § 9 | **half-up**, residual on the **heating** pot | complement pot | H3: `kostenWwCent = round_half_up(umlagefaehigCent × anteilWw)`, `kostenHzCent = umlagefaehigCent − kostenWwCent` — his own comment reads *"complement, so the sum is exact"*. |
| 10 | `co2.py:166` | CO₂ cost → (Vermieteranteil, Mieteranteil) | **half-up**, residual on the **renter** side | **no owner bucket at all** — see 9.3 | R6 + H2: `co2AbzugVermieterCent = round_half_up(co2Cent × vermieterAnteil/100)`, then `umlagefaehigCent = gesamtCent − co2Abzug`. The rounded quantity is the *deduction*; the renter side is what is left of it. |
| — | `nk-engine/engine.py:55` | an NK cost block → parties | **stays largest-remainder** | — | Out of scope by decision, not oversight: `CLAUDE.md` DoD 4 splits the rule per engine, and NK switches when Berkay's Seite 02 is transcribed into `docs/09`. The canonical €1.200 fixture is identical under both methods, so nothing is at risk in the meantime. **And the two are a package:** the residual model of § 9.2 *requires* half-up on the renter side (`docs/02`), so NK cannot take the Eigentümer line without also moving every NK figure — which is a transcription this repo does not have yet. |

**Six sites move money (#2, 3, 4, 6, 7, 8). Four provably do not (#1, 5, 9, 10)** — see 9.4. Both
halves are stated so that a reviewer who sees four sites change with no fixture behind them knows
that is intended.

**Amended 14.08.2026:** all six party-allocation sites additionally change **shape** — they allocate
to *renters*, and the Verteilungsrest lands on one `OwnerResidual` per Liegenschaft rather than on a
row inside the party list. The rounding column above is unaffected; § 9.2 has the reason.

### 9.2 The owner bucket is **one Liegenschafts-Residuum** — and it always exists

> ⛔ **SUPERSEDED 14.08.2026.** The two conventions this section used to state are dead. They were
> **ours**, written 13.08.2026 as a stopgap, and put to Berkay in `FRAGEN-an-Berkay-02.md`. He
> answered in `berkay-work/Antwort-an-Emir_02.md` § 1 — not by picking one, but by replacing the
> model they were both stopgaps for. **Do not restore either.** They are printed below, struck, so a
> later reader recognises them as removed rather than missing.
>
> | | The dead convention | Why it is dead |
> | --- | --- | --- |
> | 1 | *Several landlord parties → the residual goes to the **first** in deterministic party order, the same one in all four blocks* | **Unnecessary.** There are no longer several buckets to choose between; there is exactly one line per Liegenschaft, so the question "which party" cannot be asked. § 1.2: *"Nicht ‚erste Partei in deterministischer Reihenfolge', sondern **eine** Residuumszeile, die es strukturell immer gibt."* |
> | 2 | *No landlord party at all (fully let) → no owner bucket exists, so the block **keeps largest-remainder*** | **Explicitly rejected.** § 1.3 Frage 3: *"Euer Largest-Remainder-Vorschlag für den Rest ist damit **nicht** nötig und soll **nicht** verwendet werden."* His model has no Fall B: the line exists at `0,00 €` too, so a fully-let block has somewhere to put its rest and never needs a second allocation method. |

**The rule now.** One residual line per `(Liegenschaft, Kostenart)`; for heating that is **one line
across all four blocks** — § 1.3 Frage 3: *"der Rest geht in das Liegenschafts-Residuum, in **allen
vier Blöcken in dieselbe Zeile**"*. The line always exists, may be `0,00 €`, may be negative, and is
**never computed from a weight**:

```
eigentuemerCent[block] = blockbetragCent[block] − Σ mieteranteilCent[block]
```

The engine's derived landlord parties **collapse** into it. Their per-unit figures are not thrown
away — they survive as `OwnerResidual.origins`, block **(a)** of the Leerstandsaufstellung, because
the landlord needs the vacancy share per object for Anlage V (§ 1.4). The difference between the
printed residual and Σ origins is block **(c)**, the Rundungsdifferenz, which belongs to no unit.
Full model, shape and legal basis: `docs/02` → *"The Eigentümeranteil is a residual line, not a
party"*; document rules: `docs/08` → *"Die Eigentümerzeile"*.

**Rechtsnatur.** This is Berkay's **fixed model rule**, not a convention of ours: § 1.4 —
*"Das ist meine feste Modellregel, keine offene Konvention … setzt es fest um."* It carries no
`verify-before-production` flag. K9 keeps its flag for what remains of it (the `round_half_up`
direction); the **destination** of the Verteilungsrest is no longer ours to choose. See `docs/02`
→ *"One register row may need re-wording"*.

**What actually moves in the engine.** Measured across the whole suite before the change: the demo
path does **not** move (the demo building has a vacancy on `unit-b`, one landlord party, and its
amount already *is* the residual), so `scripts/assert_statement_pdf.py` and its 776,52 / 554,74
goldens hold. Seven blocks move, all in **fully-let** fixtures, all by 1 ct, all with the Eigentümer
line at **−0,01 €**. That sign is expected: half-up biases the renter shares upward, so Σ Mieter
tends to exceed the pot by a cent and the owner absorbs it negatively.

Reconciliation is unchanged and non-negotiable: `Σ Mieteranteile + Eigentümeranteil == Blockbetrag`
by construction, and the assertion in `calculate_heating_statement` stays — it now sums the renter
lines **and** the residual.

### 9.3 Why `co2.py:166` gets its own answer

It looks like the others and is not the same operation. It splits **one amount between two roles by
a statutory percentage**; it does not allocate a pot across parties by weight. Consequences:

- **There is no owner bucket here** — and, since 14.08.2026, no Liegenschafts-Residuum either. The
  CO₂-Vermieteranteil is a **statutory deduction** under § 7 CO2KostAufG taken *before* the
  renter-facing split; the Eigentümer-Residuum is what is left of a Blockbetrag *after* it. Two
  different figures with the same bearer, never one. Nothing in the pair is an Eigentümer row absorbing a
  distribution rest; the "residual holder" is only the complement the formula defines. The owner
  bucket appears one level further down — in the **per-tenant** pro-rata of the renters' CO₂ share
  (Rechtsstand-Register, *"CO₂-Mieteranteil — Pro-rata-Ableitung (D7 Schritt 6)"*: *"Zeilenweise
  round_half_up; der Verteilungsrest landet beim Eigentümer und wird NIE still verteilt"*), which is
  a Seite-01 step this engine does not implement at all. Do not conflate the two.
- **The switch is therefore about direction, not about a bucket.** R6 says the *statutory
  percentage* is what gets `round_half_up`, and H2 makes the landlord's **deduction** the rounded
  quantity. Under largest-remainder that holds only by an accident of the two-element case and of
  the tie-break preferring index 0; swap the two list entries and the deduction silently rounds the
  other way at an exact half cent. Naming the complement removes that.
- At an exact half cent the deduction rounds **up**, i.e. the tenant-favourable direction — the
  landlord bears more of the CO₂ cost, not less. Worth knowing before anyone "corrects" it.

### 9.4 Sites #1, #5, #9, #10 move no money, and no fixture may claim they do

For a **two-element** split whose weights are complements, largest-remainder and
`round_half_up`-on-index-0-plus-complement are the **same allocation**: the two exact quotas sum to
the total, so their fractional parts sum to 1, so the single leftover cent goes to the element whose
fraction exceeds ½ — which is exactly what rounding that element half up does — and at exactly ½ the
tie-break picks index 0, which is again half **up**. Verified by brute force over 300.000 random
weight pairs (integer and fractional) and by running the entire existing suite against a simulated
post-change engine: **278 tests, no value moved, including the demo chain and the PDF goldens.**

So these four sites cannot have a RED fixture, and their absence is not an omission. What is pinned
instead: the equivalence itself (`packages/domain/tests/test_residual_rounding.py`) and the exact
half-cent direction at #10 (`packages/heating-engine/tests/test_berkay_01b_residual_wiring.py`),
which is what would break if the two elements were ever reordered.

**Re-read 14.08.2026 and unaffected by the model change.** The proof above is about **pot
complements** — two-element splits whose weights sum to the whole — and the Eigentümer-Residuum is
not one of those: it is the rest of a *party* allocation whose weight list is the renters. Sites #1,
#5 and #9 split a pot into two named pots, and #10 splits one amount between two statutory roles;
none of the four allocates to parties, so none of them acquires an Eigentümer line and none of their
figures moves. The four stay `distribute_cents_half_up(..., residual_index=_COMPLEMENT)` — that
signature keeps naming a *complement*, which is what it does there, and it must not be swapped for
the new owner-residual primitive, which names something else.

### 9.5 The Ho/Hu boundary — what the engine must accept and what it must refuse

§ 1 (4) adopted the design; nothing consumes it. The boundary that has to refuse a mismatch is the
**CO₂ mass fallback (K4/E1)** — the only place in the engine where a kWh quantity meets an emission
factor. Where the supplier states the Brennstoffemissionen (§ 3 Abs. 1 Nr. 1 — the normal case and
the demo case) **no factor is read and the Ho/Hu question does not arise**; that path must keep
working untouched, and no default reference may be invented for it.

**Input contract** (the minimal shape; it adds no legal value and no conversion):

```python
Co2Input.total_co2_kg: Decimal | None        # § 3 Abs. 1 Nr. 1, supplier-stated — the normal path
Co2Input.emission_factor: EmissionFactor | None = None   # K4 fallback; carries its own Bezugsgröße
HeatingInput.energy_reference: EnergyReference | None = None   # the Bezug of total_energy_kwh
```

| Situation | Behaviour |
| --- | --- |
| mass stated, no factor | unchanged — the reference is never read, `energy_reference` may stay `None` |
| mass stated **and** a factor supplied | `HeatingInputError` (German). K4 is *nur Fallback*; a factor that sits next to a stated mass is **refused, not ignored** — a silently ignored factor is how the wrong one survives in the data |
| mass absent, no factor | `HeatingInputError` (German) — the § 3 breach is reported, never guessed around |
| mass absent, factor present, `energy_reference is None` | `HeatingInputError` (German) — an undeclared Bezugsgröße is refused, **never** defaulted. Defaulting to Hu on an Ho invoice is precisely the silent 11 % error this rule exists to stop |
| references **differ** | `EnergyReferenceMismatchError`, propagated **unwrapped** so its German text and its type both reach the API boundary. No coercion, no warning-and-continue, no `× 0,903` |
| references match | `total_co2_kg = co2_grams_from_energy(total_energy_kwh, reference, factor) / 1000` — R4 integer grams, then the unrounded value into the step lookup |

**Why the mismatch is worth a hard error, as one fixture pair.** Same building, same invoice of
20.000 kWh, Erdgas, 100 m² beheizte Fläche:

| Bezug | Factor (K4, register, `verify-before-production`) | Emissions | kg CO₂/m²/a | Stufe | Vermieteranteil |
| --- | --- | --- | --- | --- | --- |
| Hu | **0,201** kg CO₂/kWh | 4.020 kg | 40,2 | 37 – < 42 | **60 %** |
| Ho | **0,181** kg CO₂/kWh | 3.620 kg | 36,2 | 32 – < 37 | **50 %** |

Both rows are lawful; which one is right depends only on what the invoice's kWh means. Multiplying
the Ho quantity by the Hu factor reads 40,2 where the truth is 36,2 — **a whole Stufe, against the
landlord**, on a document the tenant may rely on (§ 7 Abs. 3/Abs. 4 CO2KostAufG). Nothing in the
intermediates looks wrong, which is why it must be refused rather than checked for.

**Deliberately not in this slice**, so the absence is known rather than silent:

- the **CO₂ cost fallback** (`co2Cent` from a price) — two rules disagree and neither was decided;
  § 7 open discrepancy 5 stands. Only the *mass* fallback is wired;
- E1's **warning + § 7 Abs. 4 risk flag** when the fallback ran, and any provenance field saying the
  printed Brennstoffemissionen were derived rather than stated. `HeatingResult` has no warning
  channel at all; that is a `docs/08` slice. **Until it exists, the fallback path prints a § 3
  Abs. 1 Nr. 1 figure the supplier never stated** — a real gap, recorded here;
- an **Ho factor for Heizöl or Flüssiggas**: the register states none, none is invented, and an Ho
  quantity of either is refused by the same mismatch error.

---

## Rounding & reconciliation (applies to both engines)

> **Superseded 12.08.2026** by R1/R5/K9 above (Berkay Seite 01b, § 4). Kept, marked, so the change is
> visible rather than silently overwritten. The old rule was **largest-remainder**:
> *floor each exact `Decimal` share to cents, then give the leftover cents to the largest fractional
> remainders (ties: stable order)*, with `sum(shares) == input_total` true by construction.
> `distribute_cents` still implements it and stays for its own callers: **`nk-engine` keeps it**
> (`CLAUDE.md` DoD 4). ~~and so does a heating block that has no landlord party to hold the
> residual~~ — **struck 14.08.2026**: that was § 9.2 convention 2, which Berkay rejected in
> `Antwort-an-Emir_02.md` § 1.3. In `heating-engine`, **no** allocation of a Blockbetrag to parties
> uses largest-remainder any more, fully-let buildings included.

1. Compute exact fractional shares with `decimal.Decimal` (**unchanged** — R2).
2. `round_half_up` each **renter** share to whole cents, once, at assignment (R1). The Eigentümer is
   not in the weight list — its Bemessung is in the **denominator** (D0/E19), never in the
   numerator of a share of its own.
3. `Verteilungsrest = Blockbetrag − Σ Mieteranteile` → the **Liegenschafts-Residuum** (R5/K9,
   Seite 01 D12). It carries the vacancy/self-use share *and* the rounding rest in one figure,
   because it **is** one figure. ±1 ct per block on top of the vacancy share, either sign; on a
   fully-let building the whole line is typically −0,01 € and may be exactly 0,00 €.
4. Assert `Σ Mieteranteile + Eigentümeranteil == input_total` — fail loudly if not. **Unchanged and
   non-negotiable:** no statement ships that doesn't reconcile. The residual is *inside* that sum,
   not an exception to it — and under this model it is the only term that can absorb a difference,
   which is exactly why it may never be recomputed from a weight.

## Why this ordering (engines before UI)

A wrong framework call later costs an app rewrite but never touches these packages or their fixtures.
The pitch's credibility rests entirely on the numbers being right — so the numbers get built and
tested first.
