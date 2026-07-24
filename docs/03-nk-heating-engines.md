# 03 — NK & heating/CO₂ engines (the crown jewel)

> These are the product. **Pure Python packages, no web-framework/DB/vendor imports.** Deterministic,
> cent-exact, golden-tested (pytest). Built at M1 (NK) and M2 (heating/CO₂), before any UI.

## Shared engine contract

- Input: **normalized** value objects — plain dataclasses / Pydantic models (no SQLAlchemy models, no
  vendor types). Adapters map DB → these.
- Money: integer **cents**; intermediate math with `decimal.Decimal`; **largest-remainder rounding** so
  the sum of allocated shares reconciles to the input **to the cent**.
- Output: a plain result object (shares per party + a reconciliation total) — the PDF layer formats it.
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

---

## `packages/heating-engine` (M2)

### Responsibilities

- **§§7/8 HKVO** split between base and consumption cost — configurable **30/70** … **50/50**
  (from rules store).
- **§9** warm-water separation from heating.
- **§9a** estimation when readings are missing.
- **Degree-day (Gradtags) apportionment** on renter change mid-period. Apportionment basis:
  **consumption** cost splits by **degree-days**; **base + warm-water** costs split by **days**.
- ⚠️ **The degree-day promille table is a VDI convention, not a statute** — it carries a
  **"verify before production"** marker in `rules-store` (with its `Rechtsstand`), unlike the HKVO
  ratios and CO₂ table which are legally fixed.
- External MDL (Messdienstleister) data feeds in through the meter adapter as normalized readings —
  the engine never knows the source.

### CO₂ cost split (CO2KostAufG) — mandatory, part of Tier-1

- **10-step model**: the building's CO₂ intensity (kg CO₂/m²/yr) selects a step; the step sets the
  **landlord vs renter percentage split** of the CO₂ price portion of heating cost.
- The 10-step table lives in the **versioned rules store** (`Rechtsstand` shown on output).
- Missing/incorrect CO₂ split = tenant's **3% reduction right** (§7 Abs. 4 CO2KostAufG) — so this is
  correctness-critical, not cosmetic.

### Heating/CO₂ golden fixtures

- A central-heating building with consumption meters → base/consumption split + WW separation.
- The same building → CO₂ 10-step selection + landlord/renter split, with `Rechtsstand MM/JJJJ`.
- A mid-period renter change apportioned by degree-days.

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
