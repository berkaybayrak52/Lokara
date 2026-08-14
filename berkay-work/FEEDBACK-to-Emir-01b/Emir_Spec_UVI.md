# Lokara — Build Spec: UVI (§ 6a HeizkostenV), full end-to-end (Variant C)

**Emir:** Paste this into your Claude in the Lokara repo as the build spec. Scope is the
complete § 6a UVI: monthly cadence, ingestion, weather source, computation, tenant portal,
delivery. Build on the existing billing engine (§§ 7–9, § 9b, CO2KostAufG) — do **not** touch
or refactor it except through the additive seams named here. Keep the engine-purity discipline
(`scripts/check_engine_purity.py`) intact: all new computation goes in pure packages, all I/O
in `packages/adapters`.

This spec references the actual code as it stands on `main` (per the status report). Where a
file path is named, that is where the work lands.

**Document map:** §1–§3 build the substrate (cadence, ingestion, weather data). §4 is the
computation — four calculation modules written in the 7-point template, each WORKED EXAMPLE
becoming a golden test. §5–§6 are the tenant-facing plumbing (portal, delivery). §7 is the
correctness gates, §8 the build order, §9 the decisions Emir must record.

---

## 0. What "done" means

§ 6a is a duty **toward the tenant**. It is met only when, for a building with remotely readable
devices, a tenant can log in and see — every month — their consumption plus the three mandatory
comparisons, and the system has provably provided it (archive + delivery log). The build is not
done until that full path works for a real multi-unit building with imported history **and** for
a first-time cold-start building.

---

## 1. Data & cadence foundation

The reading model is annual by use, monthly-capable by schema. This layer makes it monthly.

**1.1 Monthly readings.** Keep `MeterReading` append-only and point-in-time. Add a monthly
consumption derivation alongside the existing annual `meter_gateway.py` fold: given consecutive
readings for a meter, produce per-month consumption. Do not overload the annual path — add a
sibling (e.g. `monthly_gateway.py`) so annual billing stays untouched and golden-tested.
- Handle mid-month readings by interpolation to month boundaries (linear vs. degree-day
  weighted — DECISION §9.6; feeds Block A).
- Handle `reason ∈ INTERIM / TENANT_CHANGE / DEVICE_CHANGE / CORRECTION` cleanly: a device
  change resets the counter; a correction supersedes; a tenant change splits the month.

**1.2 New fields.**
- `Unit.occupant_count` (or an occupancy-period model on `Tenancy`/`TenancyParty` that yields a
  monthly headcount) — required for per-occupant average-user normalization (Block D). The area
  normalizer `Unit.area_sqm_x100` already exists; occupancy does not.
- `MeterReading` — add a period label only if the monthly gateway cannot derive it from
  `read_at`; prefer deriving it. Do not add `monat_uvi` as redundant state.
- `Meter.is_allocator` (bool) instead of inferring HKV from `measurement_unit=HKV_UNITS` — the
  UVI needs this per Block A / Block D.

**1.3 Migrations.** Alembic, additive only. Every new tenant table carries composite
`(id, account_id)` FKs and `FORCE` RLS, matching the existing pattern in `packages/db`.

---

## 2. Ingestion (feeds the monthly cadence)

Manual entry is the only working path today. Monthly UVI without ingestion means a landlord
typing every meter every month — build the real edges. All of this lives in `packages/adapters`
behind the existing `MeterGateway` Protocol; replace `StubMeterGateway`.

**2.1 ARGE HeiWaKo 3.10 parser.** The real MDL format. Implement the record sets that carry
consumption and CO2 (A/B/D/E/K/L/M). Resolves the `TODO(provider)` in
`packages/adapters/src/lokara_adapters/meter.py`. Parse into normalized `MeterReading`s. HeiWaKo
delivery must be enabled per customer account by the MDL — surface a clear "activation required
by your metering service" state, with CSV/PDF as fallback.

**2.2 CSV import with per-provider mapping templates.** Radio-platform self-abrechners
(Casameta, ZENNER, KUGU, Pironex, baeren.io) export monthly values. Mapping layer
(column → normalized field), a template per provider, plus a generic manual-mapping UI.

**2.3 PDF/OCR seeding.** Reuse the Vision adapter currently wired to invoice upload (M4) and add
a target that extracts prior-period readings from an MDL statement — the primary cold-start seed
for the year-on-year comparison.

**2.4 Radio/API adapters.** `ReadingSource.RADIO` — implement at least one real platform adapter
(Casameta or ZENNER first; KUGU ingest-only, it sends its own UVI). Normalized output.

**2.5 Onboarding/seeding wizard.** Front-end flow (AfA-wizard pattern): on setup, ask for the
last statement, run it through 2.1–2.3, seed history so the time comparisons are populated from
day one. If no history is supplied, the comparisons are legitimately absent (Blocks B/C edge
cases).

---

## 3. Weather-adjustment data source

The existing degree-day logic (`degree_days.py`, static 1981 promille table in `rules-store`)
serves **§ 9b tenant-change apportionment only** and has **no year or location dimension**. It
**cannot** serve the UVI. Do not reuse it for the UVI; do not modify it for § 9b.

Add a new source of **year- and location-specific degree days**:
- DWD open data (Gradtagszahlen per station) mapped by building PLZ, or a licensed VDI 3807
  dataset — DECISION §9.4. Adapter in `packages/adapters`; values versioned in `rules-store`
  with the as-of / year dimension the store already supports.
- Keep it as data, not engine constants — same discipline as the legal ratios. Consumed by
  Block C.

---

## 4. UVI computation (pure package)

New pure module — `packages/heating-engine/src/lokara_heating_engine/uvi.py` or a sibling
package `packages/uvi-engine`. No framework, no DB, no clock, no I/O — inputs in, result out,
enforced by the purity script. The four modules below are written in the 7-point calculation
template; each WORKED EXAMPLE becomes a golden test in `packages/.../tests/`.

**Shared rounding rule (all blocks):** compute on unrounded values; round the final consumption
figure to whole kWh, half-up; round the final comparison percentage to one decimal place,
half-up. Money figures (if shown) follow the billing engine: integer cents, `Decimal`,
largest-remainder.

**Shared reference building (Blocks B–D):** Building B, 3 units, all heat meters in kWh,
month = **January 2025**.

| Unit | Area (m²) | Jan 2025 (kWh) | Dec 2024 (kWh) | Jan 2024 (kWh) |
| --- | --- | --- | --- | --- |
| 1 | 80 | 900 | 850 | 1000 |
| 2 | 100 | 1300 | — | — |
| 3 | 120 | 1560 | — | — |

Degree-days (DWD, by building PLZ): Jan 2024 = **620 Kd**, Jan 2025 = **590 Kd**.

---

### Block A — Monthly consumption per unit (kWh)

**1. Purpose** — Turn a unit's raw monthly meter movement into a kWh consumption figure, the
input for all three § 6a comparisons, for the tenant of that unit.

**2. Legal basis** — § 6a HeizkostenV (Rechtsstand 12/2021, letzte Änderung; verify current
before production). The requirement to express consumption in kWh derives from § 6a + EED
Annex VIIa. ⚠️ **CONVENTION, not law:** the calorific conversion factors and the HKV→kWh method
(see edge cases) are implementation choices, not statutory numbers — verify before production.

**3. Inputs**
- Two consecutive `MeterReading.value_x1000` for the meter (scaled integer ×1000) — from meter,
  bank of readings, or ingestion (§2).
- `Meter.measurement_unit` ∈ `KWH | CUBIC_METRE | HKV_UNITS` — from meter.
- `Meter.is_allocator` (bool, §1.2) — from meter.
- Calorific factor (kWh per m³ / per litre) for gas/oil — from `rules-store`, as-of dated.
- For HKV only: building heat total (kWh) for the elapsed period — derived, not directly known
  mid-year (see edge cases).
- `read_at` dates for both readings (day-granular) — to place the movement in the month.

**4. Formula**
1. `movement = (reading_end.value_x1000 − reading_start.value_x1000) / 1000`.
2. If `KWH`: `kwh = movement`.
3. If `CUBIC_METRE`: `kwh = movement × calorific_factor` (≈10 kWh per m³ gas; use the
   rules-store value).
4. If `HKV_UNITS`: `kwh = building_total_kwh_for_period × (unit_units / building_units)` —
   provisional distribution (see edge case, CONVENTION).
5. Round per shared rule → whole kWh.

**5. Edge cases**
- Missing start or end reading → no consumption; downstream comparisons omit this month (not
  zero). Do not estimate for the UVI.
- Zero movement → 0 kWh (valid, e.g. vacant).
- Negative movement → device change or misread; `reason=DEVICE_CHANGE` resets the counter, do
  not subtract across the reset; otherwise flag as error, do not render.
- Reading not on a month boundary → interpolate to boundaries (§1.1 rule; DECISION §9.6,
  CONVENTION).
- **HKV-only building:** allocator units are dimensionless; a monthly kWh figure needs the year
  building total, unknown mid-year. ⚠️ Unresolved DECISION §9.1. Until decided, either (a)
  provisionally distribute a rolling building heat-meter total, or (b) show allocator units with
  an explicit "provisorisch, Endwert erst zur Jahresabrechnung" caveat. Mark clearly.
- Period longer/shorter than one month → normalize to the calendar month via the interpolation
  rule; never present a 6-week movement as a "month".

**6. WORKED EXAMPLE** — Unit 1, kWh meter. `reading_start = 12_340_000` (×1000 → 12 340 kWh),
`reading_end = 13_240_000` → movement `= 900 000 / 1000 = 900 kWh`. `measurement_unit = KWH` →
`kwh = 900`. Round → **900 kWh**. (HKV variant withheld until DECISION §9.1 — a worked example
there would bake in an unratified method.)

**7. Out of scope** — Annual billing consumption (existing `meter_gateway.py`, do not touch).
Cost/€ figures (Block A is kWh only). Warm-water split (§9 billing engine).

---

### Block B — Previous-month comparison

**1. Purpose** — Show the tenant how this month's consumption compares to last month, per § 6a.

**2. Legal basis** — § 6a HeizkostenV (Rechtsstand 12/2021; verify). The comparison is mandated;
its presentation (absolute + %) is convention.

**3. Inputs**
- `kwh_current` (Block A output for month M) — kWh.
- `kwh_previous` (Block A output for month M−1) — kWh.

**4. Formula**
1. `delta = kwh_current − kwh_previous` (kWh).
2. `pct = delta / kwh_previous × 100`.
3. Round per shared rule (delta → whole kWh, pct → one decimal).

**5. Edge cases**
- `kwh_previous` missing (first month, no seed) → omit with "liegt für den Vormonat noch nicht
  vor". Never fabricate.
- `kwh_previous = 0` → show absolute delta only, suppress % (division by zero), label "kein
  Vormonatsverbrauch".
- `kwh_current = 0` → valid; delta negative, e.g. "−100 %".

**6. WORKED EXAMPLE** — Unit 1: current = 900, previous (Dec 2024) = 850. `delta = 900 − 850 =
+50 kWh`. `pct = 50 / 850 × 100 = 5.882… → +5.9 %`. Expected out: **+50 kWh, +5.9 %**.

**7. Out of scope** — Weather adjustment (Block C only; month-over-month is raw). Cross-unit
comparison (Block D).

---

### Block C — Same-month-previous-year comparison, weather-adjusted

**1. Purpose** — Show the tenant this month vs. the same month last year, corrected for a
milder/harsher winter, per § 6a.

**2. Legal basis** — § 6a HeizkostenV (Rechtsstand 12/2021; verify). ⚠️ **CONVENTION, not law:**
the EED requires the comparison be "witterungsbereinigt" but does **not** prescribe the formula.
The degree-day ratio method below is a convention — verify acceptance before production, and it
is distinct from the § 9b promille table (do not reuse that).

**3. Inputs**
- `kwh_current` (Block A, month M this year) — kWh.
- `kwh_prev_year` (Block A, month M last year) — kWh; from seeded history/ingestion.
- `degree_days_current`, `degree_days_prev_year` (Kd) for the building's location — DWD source
  (§3), year- and location-specific, from `rules-store` as-of dated.

**4. Formula**
1. `kwh_prev_year_adj = kwh_prev_year × (degree_days_current / degree_days_prev_year)`.
2. `delta = kwh_current − kwh_prev_year_adj`.
3. `pct = delta / kwh_prev_year_adj × 100`.
4. Round per shared rule (compute on unrounded, then round adj-kWh, delta, pct).

**5. Edge cases**
- `kwh_prev_year` missing (year 1, no seed) → omit with "liegt im ersten Bezugsjahr noch nicht
  vor". Never estimate.
- `degree_days_prev_year = 0` or missing for the location → cannot adjust; either fall back to
  the raw comparison **clearly labelled "nicht witterungsbereinigt"**, or omit. DECISION §9.4.
- Prior-year month based on an interpolated/partial reading → carry the interpolation caveat.

**6. WORKED EXAMPLE** — Unit 1: current = 900, prev-year (Jan 2024) = 1000; DD current = 590,
DD prev = 620. `kwh_prev_year_adj = 1000 × (590 / 620) = 951.61… → 952 kWh`. `delta = 900 − 952 =
−52 kWh`. `pct = −52 / 952 × 100 = −5.46… → −5.5 %`. Expected out: **adjusted prior year
952 kWh, −52 kWh, −5.5 %**.

**7. Out of scope** — § 9b tenant-change apportionment (separate, static promille table, do not
reuse). Non-weather comparisons (Blocks B, D).

---

### Block D — Average-user (cross-section) comparison

**1. Purpose** — Show the tenant how their consumption compares to an average comparable unit in
the same building this month, per § 6a ("Durchschnittsnutzer derselben Nutzerkategorie").

**2. Legal basis** — § 6a HeizkostenV (Rechtsstand 12/2021; verify). The law allows a
"normierten **oder** durch Vergleich ermittelten" average user — this block uses the
*durch-Vergleich* variant (building cross-section). ⚠️ **CONVENTION, not law:** the normalization
basis (per m² vs. per occupant) and the minimum-unit threshold are implementation choices —
DECISIONS §9.2 and §9.3.

**3. Inputs**
- `kwh_current` for the target unit (Block A, month M) — kWh.
- For every **other** comparable unit in the building: its Block A `kwh_current` for month M and
  its normalizer (`Unit.area_sqm_x100` for per-m², or `occupant_count` (§1.2) for per-occupant).
- `n_comparable` = count of other units with a valid reading this month.
- Minimum-unit threshold `T` (DECISION §9.3, e.g. 3) — from config/rules-store.

**4. Formula** (per-m² basis shown; swap normalizer for per-occupant if that is the chosen basis)
1. For each other unit i: `intensity_i = kwh_i / area_i` (kWh/m²).
2. `avg_intensity = mean(intensity_i over other units)`.
3. `expected = avg_intensity × area_target`.
4. `delta = kwh_current − expected`; `pct = delta / expected × 100`.
5. Round per shared rule.

**5. Edge cases**
- `n_comparable < T` → do **not** use the cross-section; **fall back to Block D2** (normed
  average user). Never average over one unit. The old "nicht aussagekräftig / omit" behaviour is
  **retired**: § 6a Abs. 2 Nr. 3 has **no** escape clause, so a compliant value must always be shown.
- A comparable unit missing this month's reading → exclude it, recompute `n_comparable`.
- Target `area = 0`/missing → cannot normalize; omit with a data-quality flag.
- Mixed device categories (heat meter vs. HKV) in one building → only compare within the same
  category; do not mix kWh from meters with distributed HKV kWh.
- `expected = 0` → suppress %, show absolute only.

**6. WORKED EXAMPLE** — target Unit 1 (80 m², 900 kWh); others: Unit 2 (100 m², 1300 kWh),
Unit 3 (120 m², 1560 kWh); T = 3, so 2 others + target = 3 units → meets T.
`intensity_2 = 1300 / 100 = 13.0`; `intensity_3 = 1560 / 120 = 13.0`; `avg_intensity = 13.0
kWh/m²`. `expected = 13.0 × 80 = 1040 kWh`. `delta = 900 − 1040 = −140 kWh`. `pct = −140 / 1040 ×
100 = −13.46… → −13.5 %`. Expected out: **average comparable 1040 kWh, −140 kWh, −13.5 %**.

**7. Out of scope** — Time comparisons (Blocks B, C). (Standardized reference profiles for
buildings below threshold T are **now in scope** — see Block D2. The earlier "no cheap source"
assumption was wrong: co2online granted written permission to use the Heizspiegel values with
attribution, so a normed average user is available.)

---

### Block D2 — Normed average-user fallback (below threshold T)

**1. Purpose** — Satisfy § 6a Abs. 2 Nr. 3 in **every** building, including those with too few
comparable units for Block D, using the *normiert* variant of the "Durchschnittsnutzer". Replaces
the retired "nicht aussagekräftig" omission.

**2. Legal basis** — § 6a Abs. 2 Nr. 3 HeizkostenV permits a "**normierten** oder durch Vergleich
ermittelten" average user. Block D is the *durch-Vergleich* path; Block D2 is the *normiert* path.
**License:** co2online gGmbH granted written permission (e-mail on file — archive it as the license
record) to use the Heizspiegel comparison values, **conditional on attribution**. The line
`Quelle: co2online gGmbH (Heizspiegel)` is **mandatory** wherever a D2 value is shown.
⚠️ **Disclaimer to respect:** co2online states the Heizspiegel is a **whole-building** reference and
is *not* meant to evaluate a single apartment in a centrally-heated building or to judge cost
*appropriateness* (SGB). Therefore label the D2 output as a **normierter, gebäudebezogener Richtwert**
(informational, § 6a) — never as an appropriateness verdict — and confirm with the co2online contact
that this specific § 6a-UVI use is covered by the granted permission.

**3. Inputs**
- `energy_source` of the building's heating (Erdgas / Heizöl / Fernwärme / Wärmepumpe / …).
- `size_class` = the **whole building's** total living area, bucketed into the Heizspiegel 2025
  bands: **80–150 / 150–250 / 250–500 / über 500 m²** (re-check the bands each year — they change).
- `heizspiegel[year][energy_source][size_class].mittel` — the **`mittel`** band value ("Gebäude
  liegt im Durchschnitt") in **kWh/(m²·a)**, imported once per year into `rules-store` (K13, as-of
  year). Values **include Raumwärme + Warmwasser** → compare against the unit's Wärme+WW, not Wärme
  alone. Source table: `Klimafaktoren/Heizspiegel_2025_Vergleichswerte.csv`.
- `area_target` (m²) of the unit; month `M`.
- `dd_share(M)` = degree-day share of month M in the year for the building's PLZ =
  `DD(M) / Σ DD(year)` (reuse K3 / the same DD source as Block C); `Σ dd_share = 1`.

**4. Formula**
1. `norm_annual = heizspiegel[...].mittel × area_target`   (kWh/a for this unit)
2. `norm_month  = norm_annual × dd_share(M)`            (kWh for month M)
3. `delta = kwh_current − norm_month`; `pct = delta / norm_month × 100`
4. Round per shared rule.

**5. Selection rule** (in Block D) — `n_comparable ≥ T` → Block D (cross-section); else → Block D2
(normed). Always label the basis used ("Vergleich im Gebäude" vs. "normierter Durchschnittsnutzer").
When D2 is shown, render the co2online attribution.

**6. Edge cases**
- `energy_source`/`size_class` not in the table → nearest documented class + flag, or omit with a
  data-quality flag if none fits.
- Heizspiegel year not yet imported → omit + `TODO(import Heizspiegel <year>)`; never silently
  reuse a stale year without labelling it.
- `area_target = 0`/missing → cannot normalize; omit with flag.

**7. Out of scope** — Building-specific realism (that is Block D). D2 is a **normed** reference by
design — legally sufficient for the UVI, not a claim about this exact building.

**8. WORKED EXAMPLE** — Erdgas building, size class 250–500 m², Heizspiegel 2025 `mittel` = 114
kWh/(m²·a); target unit 80 m²; month M = January, `dd_share(Jan) = 0.19`. `norm_annual = 114 × 80 =
9 120 kWh/a`. `norm_month = 9 120 × 0.19 = 1 732.8 → 1 733 kWh`. Unit's `kwh_current = 2 200`.
`delta = 2 200 − 1 733 = 467 kWh`; `pct = 467 / 1 733 × 100 = 26.95… → 27.0 %`. Expected out:
**normierter Durchschnittsnutzer 1 733 kWh, +467 kWh, +27.0 %, Quelle: co2online gGmbH (Heizspiegel)**.

---

### 4.5 Mandatory legal content beyond the comparisons

Beyond the three comparisons, § 6a / EED Annex VII prescribe further UVI content (energy-source
mix, price/cost info, contact points for consumer advice, etc.). Pull the exact current list
into `rules-store` under an as-of date and render all mandatory elements. **Verify the list
against the current § 6a text before production** — `TODO(verify)` until checked.

---

## 5. Tenant surface (Mieterportal)

There is no renter surface at all today — no `RENTER` role, no renter route. § 6a cannot be
delivered without it. Build the minimum renter portal that carries the UVI.

**5.1 Role & auth.** Add `RENTER` to `Role` (`packages/db/.../models.py`). Auth per the agreed
model: full password account **and** magic-link login. Onboarding via QR code at contract signing
plus a Bestandsmieter access code.

**5.2 Routes & screens.** `/renter/...` routes (none exist). Screens: UVI current month, UVI
history/archive, and the mandatory § 6a content (§4.5). Next.js App Router + shadcn/ui, TanStack
Query, HTTP-only to the API, matching `apps/web`.

**5.3 DSGVO / isolation — hard requirement.** The landlord calculation view exposes every party
(`docs/08`). A renter must see **only their own** unit's data. Enforce with RLS scoped to the
renter's `tenancy`/`unit`, not just UI filtering. Add renter-scoped RLS policies with the same
`FORCE` discipline. Verify with a test that a renter token cannot read another unit.

---

## 6. Delivery / Versand

**6.1 Wire the email edge.** `EmailGateway` exists as a Protocol with an in-memory
`StubEmailGateway` that is **not referenced in the API**. Implement a real EU-hosted provider
adapter and wire it into the API.

**6.2 Monthly generation.** A scheduled worker generates each unit's monthly UVI on cadence,
renders the PDF (reuse `packages/pdf`, Playwright/Chromium), publishes it to the renter portal,
and — where the tenant opted for it — emails it. Electronic provision via the portal is
EED-conform; email is additive.

**6.3 Archive & audit.** Append-only PDF archive per UVI plus a delivery-status ledger
(generated / published / emailed / failed, with timestamps). This is the evidence that the § 6a
duty was met — part of "done", not optional.

---

## 7. Non-functional / correctness gates

- **Engine purity** preserved: `scripts/check_engine_purity.py` passes; UVI computation imports
  no framework/DB/clock.
- **Money** (any cost figures in the UVI): integer cents + `Decimal`, largest-remainder
  rounding, reconciles to the cent — same as the billing engine.
- **Legal values** (calorific factors, degree-day tables, § 6a content list) live in
  `rules-store` with as-of dates and `TODO(verify)` until checked against source. Never
  hard-coded in engine code.
- **Golden tests** for: each of the three comparisons (Blocks B–D worked examples), Block A kWh
  conversion, weather normalization, cold-start omission, small-building "not meaningful",
  HKV-only monthly conversion (once §9.1 decided), tenant-change mid-month, DSGVO isolation.
- **mypy --strict**, `ruff`, `pytest`, `vitest` green.
- **RLS** `FORCE` + composite `(id, account_id)` FKs on every new tenant table; renter-scoped
  policies tested.
- All tenant-facing text in German.

---

## 8. Build sequence (execution order, dependencies)

1. **Foundation** (§1, §3) — monthly cadence + occupancy + year/location degree-day source.
   Everything else depends on this.
2. **UVI engine** (§4) — pure, golden-tested against seeded/fixture data. Parallel with §5 once
   §1 lands.
3. **Ingestion** (§2) — HeiWaKo + CSV + OCR seeding + onboarding wizard; unblocks real monthly
   data and cold-start.
4. **Tenant portal** (§5) — role, auth, routes, screens, DSGVO isolation.
5. **Delivery** (§6) — email edge, monthly scheduler, archive, delivery log.
6. **Hardening** (§7) — edge cases, legal-content verification, end-to-end on a real imported
   building and a cold-start building.

---

## 9. Decisions Emir must make and record (correctness, not scheduling)

1. **HKV-only monthly kWh** (Block A) — how a building with only allocators expresses a monthly
   UVI in kWh mid-year. Hardest question; block on it. Block A's HKV worked example / golden test
   is written only after this is set.
2. **Average-user normalization basis** (Block D) — area, occupant, or both.
3. **Small-building threshold `T`** (Block D) — minimum comparable units for a meaningful
   cross-section.
4. **Weather-data granularity & fallback** (§3, Block C) — DWD station→PLZ mapping vs. licensed
   VDI 3807; and whether a missing prior-year degree-day falls back to a raw labelled comparison
   or omits.
5. **§ 6a content list** (§4.5) — verify the full mandatory-content list against current text.
6. **Interpolation rule** (§1.1, Block A) — linear vs. degree-day weighting for mid-month
   readings.

Report your resolution of these six back to us — they change what the UVI actually says, so we
decide them together, not silently in code.
