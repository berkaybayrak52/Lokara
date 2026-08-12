# Collision map — Seite 01b vs. the built heating engine

Value-by-value comparison of Berkay's page 01b against `packages/heating-engine`,
`packages/rules-store` and `packages/domain` as they stand on `main`. Written before any
transcription so the blast radius is visible up front.

**Classification:** `SAME` no change · `MOVES` value changes, money changes ·
`TYPE` the shape of the data changes · `CONFLICT` the two specs disagree on method ·
`NEW` Berkay has it, the code does not.

---

## 1. SAME — already correct, no work

| Rule | Berkay | Code | Where |
| --- | --- | --- | --- |
| CO₂ 10-step bounds | 12/17/22/27/32/37/42/47/52, left-closed right-open | identical, `max_intensity_exclusive` | `rules/co2_split.py` |
| CO₂ landlord shares | 0/10/20/30/40/50/60/70/80/95 % | identical | `rules/co2_split.py` |
| § 9 Abs. 2 substitute equation | `Q = 2,5 × V × (tw − 10)`, tw = 60 °C | identical (125 kWh/m³) | `rules/warm_water.py` |
| § 9 Abs. 3 fallback | `Q = 32 × A_Wohn` | identical | `rules/warm_water.py` |
| §§ 7/8 statutory band | 50–70 % consumption | `min 0,5 / max 0,7` | `rules/heating_split.py` |
| K1 default | Grundkosten 30 % (= consumption 70 %) | `DEFAULT_CONSUMPTION_SHARE = 0.7` | `rules/heating_split.py` |

Nine of the values already in `rules-store` survive the audit untouched. That is worth
knowing: the engine's legal core was right.

---

## 2. MOVES — value changes, and money changes with it

### K3 — the degree-day table  ⚠️ highest impact

| Month | Built | Berkay (VDI 2067 Bl. 1, 12/1983, Tab. 22) |
| --- | --- | --- |
| Jun | 15 | **13,3** |
| Jul | 10 | **13,3** |
| Aug | 10 | **13,4** |
| Dez | 165 | **160** |

Eight months agree; four do not. Both sum to 1000.

**Consequence:** Jan–Jun goes 585,0 ‰ → **583,3 ‰**. Unit B's heating split moves
`778,79 € / 552,47 €` → **`776,52 € / 554,74 €`**. That is the third re-base of this pair,
and it touches `assert_statement_pdf.py`, `DEMO-RUNBOOK.md`, `docs/06`, and
`.claude/agents/statement-reviewer.md`.

The built table carries `TODO(verify)` and is sourced to nothing. Berkay's is sourced.
**Decision taken: adopt Berkay's.**

---

## 3. TYPE — the data shape changes

### `DegreeDayTable` must hold tenths of a promille

Berkay's values are fractional (13,3 / 13,3 / 13,4), so he stores **Zehntelpromille,
Σ = 10 000**: `1700 1500 1300 800 400 133 133 134 300 800 1200 1600`.

`packages/domain/src/lokara_domain/legal_values.py` currently declares:

```python
promille_by_month: tuple[int, ...]        # and __post_init__ raises unless sum == 1000
```

Both the field semantics and the invariant change, and every consumer of
`degree_day_weight()` with them. This is a `domain` change, which by `CLAUDE.md` rule 1
means golden fixtures move before code does.

---

## 4. CONFLICT — the two specs disagree on method

### 4a. Rounding and the residual  ⚠️ affects every distributed cent

| | Berkay (R1, R5, K9) | Code (`docs/03` → Rounding) |
| --- | --- | --- |
| Per share | `round_half_up` at assignment | floor, then largest-remainder |
| Leftover | `Blockbetrag − Σ Anteile = Verteilungsrest` → **owner bucket**, ±1 ct per block | distributed to the largest fractional remainders; **no residual exists** |
| Reconciliation | owner absorbs the difference | `sum(shares) == input_total` by construction |

These are different algorithms and they assign different cents to different parties. Both
reconcile; they do not agree per party.

`K9` is flagged `Konvention` / `verify-before-production`, and its stated justification is
*"folgt dem Residuum-Prinzip der Seite 01 (D12)"* — i.e. it is chosen for consistency with
his statement layout, not derived from a norm. `CLAUDE.md`'s definition of done names
largest-remainder explicitly.

**This needs a decision before transcription.** Adopting R5/K9 changes every allocation in
both engines, not just heating — the NK engine uses largest-remainder for the canonical
€1.200 fixture, which is a `CLAUDE.md` definition-of-done and cannot move.

### 4b. Short billing period — same step, different disclosed figure

| | Berkay (H2) | Code (`co2.py`, § 5 Abs. 1 S. 4) |
| --- | --- | --- |
| Method | annualise the intensity: `spezifisch × 365 / nTage`, then look up | shorten the table: `bound × period_factor`, intensity stays the period value |
| Step selected | identical — `i × (365/d) < b` ⟺ `i < b × (d/365)` | identical |
| Figure printed | the **annualised** kg/m²/a | the **period** kg/m² |

Mathematically the same classification; a different number on the page. The code's reading
quotes § 5 Abs. 1 S. 4 verbatim (*"so sind die Werte der Einstufungstabelle in der Anlage
anteilig zu kürzen"* — the **table** is shortened) and notes that § 7 Abs. 3 governs
disclosure. Berkay's page also claims verification against the norm text.

Low stakes for the demo (full calendar year, factor 1). Needs settling before an interim
statement ships. Worth asking Berkay directly rather than deciding here.

---

## 5. NEW — Berkay specifies it, the code has nothing

Ordered by how much of the engine each one touches.

| # | What | Norm / ID | Notes |
| --- | --- | --- | --- |
| 1 | **H7 — the whole MDL path** | § 4.7, K14 | OCR ingest, control-sum validation, pass-through. `M2` rescale when the MDL has not shown CO₂. `StubMeterGateway` is a fixture, not this. |
| 2 | **H8 — the UVI comparison** | § 6a Abs. 3 Nr. 5 | DWD Klimafaktoren (K12), heat weather-adjusted, warm water **not**. Confirms the status report: nothing exists. Referenced import spec `DWD-Klimafaktoren-Import-Spec.md` is **not in the folder**. |
| 3 | **Building type on the CO₂ path** | § 8 CO2KostAufG | `nichtwohn` → flat 50 %. `co2.py` has no building type at all. |
| 4 | **Denkmal- / Milieuschutz** | § 9 Abs. 1/2 CO2KostAufG | halve the landlord share, or zero it on proof. Not modelled. |
| 5 | **Heat pump / biomass** | — | CO₂ module OFF entirely. Not modelled. |
| 6 | **H5 — device aggregation** | K11, R7 | `round((wertNeu − wertAlt) × bewertungsfaktor, 1)`. **`bewertungsfaktor` does not exist in the data model.** Reject `wertNeu < wertAlt`, never `abs()`. |
| 7 | **Two readings per tenant change** | § 9b Abs. 1 | Auszug **and** Einzug; with one reading the vacancy month cannot be separated. |
| 8 | **H1a — invoice period allocation** | K8 | day-linear pro-rata by overlap; coverage < 100 % raises a non-dismissible warning. |
| 9 | **H1b — oil valuation** | K7 | weighted average over opening stock + purchases; CO₂ on **consumed**, never purchased. |
| 10 | **Denominator-zero guard** | E17 | blocking readiness error; a silent fallback to area distribution is **forbidden**. Distinct from the § 9a Abs. 2 fallback the engine already has. |
| 11 | **Emissions as integer grams** | R4 | internal unit is gram; `Co2Result.total_co2_kg` is a `Decimal`. The step lookup must use the **unrounded** value. |
| 12 | **Ho vs. Hu on the gas factor** | K4 register entry | invoices state Brennwert (Ho) kWh, the 0,201 factor is Heizwert (Hu)-based. Without `× 0,903` the emissions are **10,8 % too high**. |

---

## 6. Open, and not ours to decide

- **CO₂ price from 2026.** No single price exists — corridor 55–65 €/t, Verkaufsphase 68 €,
  Nachkauf 70 €. Berkay's Non-Goals record this as *"Entscheidung offen — To-Do Berkay"*.
  The 2025 fixture (55 € + 19 % USt = 65,45 €/t) is unaffected.
- **§ 6a Abs. 3 S. 4 Bekanntmachung** — the BMWi/BMI simplification notice that would give
  the Vermutungswirkung is marked *"nicht gefunden"* in his own Rechtsgrundlage table.
- **K13 average user.** The link-instead-of-data approach is legal for the **annual
  statement only** — § 6a Abs. 3 Nr. 4 does not permit it for the UVI. Own data needs a
  four-digit object count (Non-Goals).

---

## 7. What this implies for sequencing

1. **Settle 4a (rounding/residual) first.** It is the only item that reaches outside
   heating — the NK engine's canonical €1.200 fixture is a `CLAUDE.md` definition of done
   and cannot move. If R5/K9 wins, that is a two-engine change; if largest-remainder wins,
   Berkay's fixtures must be re-derived before they are used as oracles.
2. **Then K3 + the `DegreeDayTable` type change**, as one slice. Fixtures move first,
   `domain` and `rules-store` after, then the three doc/agent files carrying the old pair.
3. **Then the NEW list, smallest first.** Items 3, 4, 5 and 10 are each a few lines and
   close real legal gaps. Items 1, 2 and 6 are their own slices — the MDL path, the UVI,
   and the `bewertungsfaktor` data-model change.
4. **Ask Berkay about 4b** rather than deciding it here. Both readings select the same
   step; only the printed figure differs, and he has the norm text in front of him.
