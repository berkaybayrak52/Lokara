# UVI — monthly consumption information and comparisons

**Status:** complete D2 transcription; approved and merged 21.08.2026; UVI
calculation/readings/document remain specification only; G1's pure W4 evaluator is prepared but
unmerged

**Rechtsstand:** 07/2026 unless a row below carries its own date. `geprüft` means that the
primary text was read, not that a lawyer approved the rule. Every `verify-before-production` flag
remains effective.

**Authoritative sources:**

- `berkay-work/Spec-Seiten/Anlagen/Emir_Spec_UVI.md`
- `berkay-work/Spec-Seiten/Anlagen/DWD-Klimafaktoren-Import-Spec.md`
- `berkay-work/Spec-Seiten/Anlagen/LETZTER-STAND.md`
- `berkay-work/Spec-Seiten/Anlagen/Heizspiegel_2025_Vergleichswerte.csv`
- `berkay-work/Spec-Seiten/01b · Heizkosten- & CO₂-Verteilung
  3a95fd420731814e9e5be043028d4856.md`
- `berkay-work/Spec-Seiten/05 · Wächter Fristen 3a95fd42073181038246e579777508f9.md`
- `berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv`

The structured register controls values and production flags. Approved supersessions in this
document control explicit method corrections. The data-only oracle is
`packages/rules-store/tests/berkay_uvi_golden.py`; its checks prove transcription and arithmetic,
not implementation or legal approval. The oracle uses source names instead of inventing a
`16-Fxx` namespace.

## 1. Scope, corrections and hard boundaries

This document owns the monthly consumption information under § 6a HeizkostenV: monthly reading
derivation, Blocks A–D2, weather inputs, the tenant document, archive/delivery evidence and the
labelled fallbacks. `docs/12` W4 owns cadence and guard state; the prepared G1 evaluator supplies
that cadence result. `docs/03` owns the annual heating
money allocation and Page 01b annual comparison. `docs/08` owns the annual statement projection.

The later sources settle these corrections:

1. The DWD annual climate-factor plausibility range is **0.40–1.80**. The old test instruction
   starting at `0.50` is superseded because the verified file contains `0.49`.
2. DWD rolling 12-month climate factors and UVI monthly degree-day values are different datasets.
   The annual importer in § 9 cannot satisfy Block C or the D2 monthly share.
3. D2 compares heat with heat. Subtract `24 kWh/(m²·a)` for gas, oil, district heat and pellets;
   subtract `8 kWh/(m²·a)` for heat pumps. A result at or below zero blocks the value.
4. Missing over-500 m² heat-pump or pellet data uses the 250–500 m² class with a visible fallback
   label. It is never omitted, silently substituted or extrapolated.
5. The current D2 result is **1,368 kWh, +132 kWh, +9.6%**. The earlier heat-plus-hot-water result
   exists only in the supersession ledger in § 16.
6. A renter is a Person/Tenancy domain context. `RENTER` is never a `Membership` role. Membership
   roles remain `OWNER`, `EMPLOYEE` and `TAX_ADVISOR`.
7. UVI introduces no money allocation. It does not add a heating largest-remainder path. Heating
   money remains renter half-up plus the unconditional owner residual in `docs/03`; Slice C aligns
   NK with the same residual shape.
8. Block D normalizes by area and requires at least three valid comparable-category units,
   **including the target**. Two other valid units plus the target meet the threshold.
9. Mid-month readings interpolate linearly by elapsed days, and the output retains interpolation
   provenance.
10. HKV-only monthly kWh provisionally distributes a measured rolling building heat total by HKV
    units, carries a provisional label, and blocks if that measured building total is missing.
11. Missing monthly weather data produces a raw comparison labelled
    “nicht witterungsbereinigt”. It never inserts an implicit factor of `1.00`.

The exact monthly DWD degree-day dataset and station-to-PLZ mapping remain
`verify-before-production`. That missing authority blocks production Blocks C and D2, but not this
transcription.

## 2. Legal and register inventory

The twelve relevant CSV rows are reproduced with their flags intact. Approved method corrections
below do not silently change a CSV flag.

| CSV row | Value | Source and basis | Nature · flag · Rechtsstand |
| ---: | --- | --- | --- |
| 4 | UVI monthly from 01.01.2022 only with remotely readable equipment | `gesetze-im-internet.de/heizkostenv/__6a.html` · § 6a Abs. 1 Nr. 2 | Verordnung · `geprüft` · 07/2026 |
| 11 | BMWi/BMI notice: CSV still says existence unverified | same § 6a source · § 6a Abs. 3 S. 4 | Verordnung · `verify-before-production` · 07/2026 |
| 17 | 3% reduction risk for missing remotely readable equipment | `gesetze-im-internet.de/heizkostenv/__12.html` · § 12 Abs. 1 S. 2 | Verordnung · `verify-before-production` · 07/2026 |
| 21 | K13 co2online average-user values; monthly UVI may not use the annual-statement online-reference escape | Heizspiegel method · § 6a Abs. 2 Nr. 3, Abs. 3 S. 1 Nr. 4 | Konvention · `verify-before-production` · 07/2026 |
| 29 | annual § 6a block: source mix, THG/primary energy, taxes/fees, equipment/readout/billing costs, contacts, dispute notice, average-user and graphical prior-year comparison | `gesetze-im-internet.de/heizkostenv/__6a.html` · § 6a Abs. 3 S. 1 Nr. 1–5 | Verordnung · `geprüft` · 07/2026 |
| 30 | retrofit deadline 31.12.2026 | consolidated HeizkostenV · § 5 Abs. 2 | Verordnung · `geprüft` · 07/2026 |
| 35 | K12 DWD factor: TRY Potsdam/location, about 8,200 PLZ, rolling 12-month periods, about six-week delay, GeoNutzV attribution | DWD · § 6a Abs. 3 S. 3 HeizkostenV with § 82 Abs. 3 GEG | Konvention · `verify-before-production` · 07/2026 |
| 43 | 3% reduction risk for missing/incomplete § 6a information | `gesetze-im-internet.de/heizkostenv/__12.html` · § 12 Abs. 1 S. 3 with § 6a | Verordnung · `verify-before-production` · 07/2026 |
| 45 | comparison includes heat and hot water; weather-adjust heat only and show hot water raw | § 6a Abs. 3 S. 2–3 | Verordnung · `verify-before-production` · 07/2026 |
| 50 | closed § 7 Abs. 2 heating-cost catalogue, including § 6a information costs; § 8 Abs. 2 adds water costs | §§ 7 Abs. 2/4 and 8 Abs. 2/4 | Verordnung · `verify-before-production` · 07/2026 |
| 51 | non-consumption/readings billing requires only § 6a Abs. 3 Nr. 2 and 3 | § 6a Abs. 5 | Verordnung · `verify-before-production` · 07/2026 |
| 117 | W4 due at month end; year-round versus heating-season-only remains uncertain | § 6a Abs. 1 Nr. 2 | Konvention · `verify-before-production` · 10/2023 |

The approved source trace identifies the BMWi/BMI notice as “Regeln für Energieverbrauchswerte im
Wohngebäudebestand”, 29.03.2021, BAnz AT 16.04.2021 B1. Its direction supports K12. Whether the
notice published under GEG § 82 is legally the intended § 6a notice remains pre-legal and does not
clear row 11. The notice's 36-month/three-factor energy-certificate method must not enter either
the annual two-year comparison or monthly UVI.

## 3. Cadence, readings and normalized inputs

The prepared G1 W4 evaluator from `docs/12` supplies one due occurrence per renter context in a
remotely readable building:
month-end due date, in-app/email escalation, `uvi_sent` resolution and the unresolved
year-round/heating-season legal flag. This document consumes that occurrence; it does not create a
second scheduler rule.

`MeterReading` remains append-only and point-in-time. A monthly gateway derives calendar-month
movements beside the annual fold; it does not overload or change annual billing. A reading carries
meter, scaled value, `read_at`, source and reason. The gateway handles:

- `INTERIM`: retain the point and derive by the approved interpolation rule;
- `TENANT_CHANGE`: split provenance by tenancy without losing the physical meter series;
- `DEVICE_CHANGE`: close the old counter and start the new counter; never subtract across reset;
- `CORRECTION`: append a superseding record and retain the corrected record's identity.

For a boundary between two readings, interpolate linearly by elapsed days. Interpolate both month
boundaries from the surrounding spans, subtract the boundary values and attach the source reading
IDs, dates, interpolation method and any tenancy/device split. Never call a six-week movement one
month.

Normalized computation inputs are:

- target renter context, tenancy, unit and building PLZ;
- `area_sqm_x100` and the chosen comparable device category;
- ordered readings and meter unit `KWH | CUBIC_METRE | HKV_UNITS`;
- explicit allocator marker; do not infer HKV solely from the measurement unit;
- versioned calorific factors when a physical volume must become kWh;
- measured rolling building heat total for the HKV provisional path;
- current/prior monthly heat kWh, current/prior-month heat kWh;
- location/year/month-specific degree days for Block C and D2;
- versioned Heizspiegel row, heat-only deduction and visible source metadata.

Occupancy count was an unresolved alternative in the annex. The approved Block D convention is
area normalization, so no occupant-count number enters the V1 calculation. Future occupancy work
must not silently change the comparison basis.

## 4. Shared calculation and output rules

UVI calculation is pure: normalized values in, deterministic result and warnings out. It imports no
database, framework, adapter, clock or vendor library. Legal/conventional values are resolved from
versioned rules data by the caller and retain their as-of date.

Calculate with exact decimal values. Round the final consumption/delta to whole kWh, half up. Round
the final percentage to one decimal place, half up. The Block C annex text says to compute on
unrounded values, but its worked result calculates `-52 / 952 = -5.5%` from displayed rounded
values. The oracle preserves the printed result and flags that rounding-order inconsistency for
resolution before implementation. A missing value is absent, not zero. A zero denominator
suppresses only the percentage and keeps the absolute value.

Blocks A–D2 are heat-consumption comparisons. They allocate no cents. Any required price/cost
information is normalized factual content from its source; no UVI module redistributes the annual
heating bill.

## 5. Block A — monthly heat consumption

For consecutive compatible readings:

```text
movement = (end.value_x1000 - start.value_x1000) / 1000
KWH:          heat_kwh = movement
CUBIC_METRE:  heat_kwh = movement * versioned_calorific_factor
HKV_UNITS:    heat_kwh = measured_rolling_building_heat_kwh
                         * unit_hkv_units / building_hkv_units
```

The HKV branch is provisional and must print
“provisorisch, Endwert erst zur Jahresabrechnung”. It requires a measured rolling building heat
total covering the same elapsed period. A fuel purchase, annual estimate or missing building total
does not qualify. Without it, Block A and downstream comparisons block for that unit.

Missing boundary readings produce no month. Zero movement is valid. A negative movement is accepted
only as a correctly segmented device change; otherwise it is an error and no UVI is rendered. Gas
or oil conversion factors are as-of-dated rules values, never engine constants. The source Block A
example is `12,340,000 → 13,240,000`, producing **900 kWh**.

## 6. Block B — previous-month comparison

```text
delta = current_heat_kwh - previous_month_heat_kwh
percent = delta / previous_month_heat_kwh * 100
```

For `900` current and `850` previous, output **+50 kWh, +5.9%**. Missing prior month prints
“liegt für den Vormonat noch nicht vor”. Prior month zero prints the absolute delta and
“kein Vormonatsverbrauch”, without a percentage. Current zero is valid and can print `-100.0%`.
Block B is raw; weather never enters it.

## 7. Block C — same month last year, weather-adjusted

Block C uses **monthly, location-specific degree days**, not the annual DWD climate factor:

```text
prior_adjusted = prior_year_heat_kwh
                 * monthly_degree_days_current / monthly_degree_days_prior_year
delta = current_heat_kwh - prior_adjusted
percent = delta / prior_adjusted * 100
```

The annex arithmetic case uses `900`, `1,000`, `590` and `620`: adjusted prior year
`951.6129… → 952 kWh`, delta `-51.6129… → -52 kWh`, **-5.5%** from the displayed `-52 / 952`.
The source's exact-value instruction would instead yield `-5.4%`; that unresolved rounding-order
conflict is explicit. The two degree-day inputs are an arithmetic fixture, not approved production
DWD rows.

Missing prior-year consumption prints “liegt im ersten Bezugsjahr noch nicht vor”. Missing or zero
prior-year monthly degree days falls back to `current / prior` and visibly prints
“nicht witterungsbereinigt”. It never supplies `1.00`. Interpolated prior-year consumption retains
its interpolation notice.

Production is blocked until an authoritative monthly DWD dataset and station-to-PLZ mapping are
specified, versioned and covered. The annual climate-factor files in § 9 do not resolve this.

## 8. Block D and D2 — average user

### 8.1 Block D: building cross-section

Use only valid monthly values in the target's comparable device category. Do not mix physical
heat-meter kWh with provisionally distributed HKV kWh. Count the target plus other valid units.
When the count is at least three:

```text
intensity_i = other_unit_heat_kwh / other_unit_area_sqm
average_intensity = mean(intensity_i)
expected_target = average_intensity * target_area_sqm
delta = target_heat_kwh - expected_target
percent = delta / expected_target * 100
```

The source case has target `80 m² / 900 kWh` and other units `100 / 1,300` and `120 / 1,560`.
Both other intensities are `13.0`, so the target reference is **1,040 kWh**, delta **-140 kWh**,
percentage **-13.5%**. A missing/zero target area blocks with a data-quality flag. Expected zero
suppresses the percentage.

### 8.2 Block D2: normed fallback

Fewer than three valid units including the target selects D2. Use the whole building's area class
and the annual Heizspiegel `mittel` value. D2 is a **normierter, gebäudebezogener Richtwert** for
information under § 6a, never an apartment-efficiency or cost-appropriateness verdict.

First remove the source's warm-water component so both sides are heat-only:

| Energy source | Warm-water deduction kWh/(m²·a) | Status |
| --- | ---: | --- |
| Erdgas, Heizöl, Fernwärme, Holzpellets | 24 | co2online method; verify per Heizspiegel year |
| Wärmepumpe | 8 | JAZ-based convention; `verify-before-production` |

Then calculate:

```text
heat_only_mittel = heizspiegel_mittel - warm_water_deduction
if heat_only_mittel <= 0: block with data-quality flag
norm_annual = heat_only_mittel * target_area_sqm
norm_month = norm_annual * monthly_degree_day_share
delta = target_heat_kwh - norm_month
percent = delta / norm_month * 100
```

The current example is gas, 250–500 m²: `114 - 24 = 90`; `90 * 80 = 7,200`;
`7,200 * 0.19 = 1,368`; target heat `1,500`. Output **1,368 kWh, +132 kWh, +9.6%**.

Every D2 output must print “Quelle: co2online gGmbH (Heizspiegel)”. The source permission is no
longer a build blocker, but the finished § 6a sample output and licence record must be archived.

The source has 18 rows:

| Building area | Energy | low | middle | high | too high from |
| --- | --- | ---: | ---: | ---: | ---: |
| 80–150 | Erdgas | 62 | 121 | 207 | 208 |
| 80–150 | Heizöl | 100 | 165 | 263 | 264 |
| 80–150 | Fernwärme | 38 | 89 | 191 | 192 |
| 80–150 | Wärmepumpe | 20 | 36 | 82 | 83 |
| 80–150 | Holzpellets | 74 | 148 | 249 | 250 |
| 150–250 | Erdgas | 64 | 116 | 187 | 188 |
| 150–250 | Heizöl | 92 | 142 | 220 | 221 |
| 150–250 | Fernwärme | 41 | 94 | 169 | 170 |
| 150–250 | Wärmepumpe | 18 | 33 | 77 | 78 |
| 150–250 | Holzpellets | 72 | 126 | 219 | 220 |
| 250–500 | Erdgas | 61 | 114 | 185 | 186 |
| 250–500 | Heizöl | 78 | 123 | 197 | 198 |
| 250–500 | Fernwärme | 36 | 112 | 203 | 204 |
| 250–500 | Wärmepumpe | 17 | 30 | 69 | 70 |
| 250–500 | Holzpellets | 60 | 113 | 196 | 197 |
| over 500 | Erdgas | 59 | 115 | 177 | 178 |
| over 500 | Heizöl | 68 | 127 | 198 | 199 |
| over 500 | Fernwärme | 46 | 87 | 144 | 145 |

The values are kWh/(m²·a), Heizspiegel 2025, billing year 2024, as of 09/2025, and originally
include heat plus hot water. For over-500 m² Wärmepumpe and Holzpellets only, use the 250–500 row
and print: “Vergleichswert der Größenklasse 250–500 m²; für über 500 m² liegt für diesen
Energieträger noch kein Wert vor.” This fallback is not guaranteed conservative.

## 9. DWD rolling 12-month climate-factor import

This importer serves Page 01b's annual comparison. It does not provide Block C monthly degree days.

| Property | Contract |
| --- | --- |
| source | DWD CDC `derived_germany/techn/monthly/climate_correction_factor/recent`, v22.3 |
| licence | GeoNutzV; “Quelle: Deutscher Wetterdienst” required |
| files | `KF_<VON>_<BIS>.csv` point-decimal preferred; `_k.csv` comma-decimal; XML equivalent |
| period | rolling 12 months; calendar-year use needs `YYYY0101–YYYY1231` |
| CSV format | `DatAnf;DatEnd;PLZ;KF`, semicolon, ASCII/Latin-1 safe |
| XML fields | `VON_DATUM`, `BIS_DATUM`, `KLFK_POLZ`, `KLIMAFAKTOR` |
| PLZ | source omits leading zero; left-pad to five characters |
| factor | exact decimal, accepted only from 0.40 through 1.80 inclusive |
| completeness | at least 7,000 rows; verified 2025 calendar file has 8,234 |
| identity | `(plz, period_from, period_to)`; upsert idempotently; never delete old periods |
| direction | milder period means KF > 1 and raises adjusted heat; inversion is forbidden |
| missing PLZ | labelled raw comparison; never silent `1.00` |
| operation | monthly attempt after expected publication; failure alerts and preserves old data |

The exact nine verified fixtures for `01.01–31.12.2025` are:

| PLZ | KF | PLZ | KF | PLZ | KF |
| --- | ---: | --- | ---: | --- | ---: |
| 01067 | 1.14 | 01099 | 1.02 | 01328 | 0.98 |
| 01773 | 0.83 | 02625 | 1.05 | 03042 | 1.12 |
| 04103 | 1.15 | 04109 | 1.14 | 06108 | 1.15 |

The latest-state annex first headlines the April-ending file published 15.06.2026. Its later
13.08.2026 correction controls: the latest verified file there is
`KF_20250601_20260531`, period 01.06.2025–31.05.2026, published **15.07.2026**. The stale April
headline remains history, not current state.

## 10. Ingestion, tenant context and delivery

The eventual adapter surface remains behind the existing meter gateway protocol:

- ARGE HeiWaKo 3.10 A/B/D/E/K/L/M record sets, with a clear MDL activation-required state;
- provider-mapped CSV templates for Casameta, ZENNER, KUGU, Pironex and baeren.io, plus generic
  manual mapping;
- PDF/OCR cold-start seeding from a prior MDL statement;
- at least one normalized radio/API adapter, with KUGU ingest-only where it sends its own UVI;
- onboarding that asks for prior history and legitimately leaves B/C absent when none exists.

These are specified future implementation seams. The dated Non-Goals file deferred ARGE and bved
until after its pitch date; the later UVI annex brings ingestion into the UVI implementation scope.
OCR internals remain outside this document.

The renter surface is authorized through a Person's account-scoped tenancy relationship, not a new
Membership role. It needs current-month UVI, archive/history and mandatory content. RLS and app
authorization must scope every read to that renter context and unit; UI filtering is insufficient.
The landlord's all-party calculation view is never exposed to a renter.

Monthly generation produces a separate renter document, publishes it to the renter context and may
email it when opted in. The archive is append-only. A delivery ledger records generated, published,
emailed and failed states with timestamps. A retry appends status evidence; it does not rewrite the
original UVI. Scheduled delivery remains M9 and portal publication remains M10 under `PLAN.md`.

## 11. Mandatory content and German output

The UVI document contains the target month and unit, Block A, the three mandatory comparisons or
their exact labelled absence/fallback states, the basis “Vergleich im Gebäude” or
“normierter Durchschnittsnutzer”, all source/provenance labels and the legal content applicable to
monthly UVI. All tenant-facing text is German.

Register row 29 is the checked annual § 6a Abs. 3 list, not permission to assume that the monthly
list is identical. The exact current monthly § 6a/EED content list remains
`verify-before-production`; it must be versioned with an as-of date before production. Row 51's
reduced annual list for non-consumption-based billing is preserved and must not be broadened.
Reduction rights are shown as separate risks only. Lokara never deducts 3% or 15% automatically.

## 12. Correctness and production gates

Implementation is complete only when:

- the pure UVI computation has no framework, database, vendor or clock imports;
- every source-named calculation and fallback fixture is executable against production code;
- annual DWD import guards cover headers, leading zeroes, completeness, duplicates, range,
  idempotency, missing PLZ and factor direction;
- the monthly dataset/station mapping authority exists and Blocks C/D2 are no longer red;
- all 18 Heizspiegel rows, deductions, heat-pump exception, non-positive guard, over-500 fallback
  and attribution are versioned and tested;
- renter isolation has a negative cross-unit test and every new tenant table has composite account
  isolation, RLS and `FORCE` RLS;
- archive and delivery evidence is append-only and retry-safe;
- strict typing, lint, pure-package tests and the required statement/UI review pass.

No engine, adapter, schema, API, UI, PDF, scheduler or delivery implementation is part of this D2
slice.

## 13. Source-named fixture map

| Oracle key/source | Exact behavior |
| --- | --- |
| `emir_spec_block_a_kwh` | `12,340,000 → 13,240,000 = 900 kWh` |
| `emir_spec_block_b_previous_month` | `900 - 850 = +50 kWh; +5.9%` |
| `emir_spec_block_c_weather_adjusted` | arithmetic-only `590/620` case: `952, -52, -5.5%` |
| `emir_spec_block_d_building_cross_section` | three valid units including target: `1,040, -140, -13.5%` |
| `approved_block_d2_heat_only` | `114 - 24`, then `1,368, +132, +9.6%` |
| `approved_hkv_provisional` | measured rolling building total, visible provisional label, missing-total block |
| `approved_block_c_raw_weather_fallback` | raw `-100, -10.0%`, visibly not weather-adjusted |
| `approved_linear_mid_month_interpolation` | elapsed-day boundaries and provenance; February `280 kWh` |
| `DWD_ANNUAL_CLIMATE_FACTOR_PLZ_FIXTURES` | all nine PLZ values including leading zero |
| `DWD_ANNUAL_IMPORT_CONTRACT` | headers, range, completeness, duplicate, idempotency and direction guards |
| `HEIZSPIEGEL_2025_ROWS` | all 18 source rows exactly |
| `HEIZSPIEGEL_D2_CONTRACT` | deductions, heat-pump exception, non-positive guard, fallback and attribution |
| `UVI_REGISTER_ROWS` | exact 12-row identity and every production flag |
| `UVI_SOURCE_SECTIONS` | annex/Page/W4/register/non-goal/audit coverage |

## 14. Explicit non-goals and boundaries

All eleven Page 01b entries in Non-Goals V1 remain preserved:

1. recalculate or overrule an MDL statement from its raw inputs;
2. floor-heating renter CO₂ reimbursement calculator;
3. non-residential CO₂ logic beyond the current 50/50 split;
4. renovation or amortization numbers behind the traffic light;
5. ARGE 3.10/bved as part of the dated pitch scope; later UVI ingestion ownership is recorded in
   § 10 without rewriting that history;
6. OCR model, prompts, extraction and confidence internals;
7. automatic application of 15% or 3% reduction rights;
8. inspection of device installation, calibration or K-values;
9. document-inspection workflow exposing other renters' consumption;
10. proprietary average-user values aggregated from Lokara customers; and
11. a guessed CO₂-price table fallback from 2026.

Annual billing consumption, annual heating-money allocation, § 9 warm-water money splitting,
contract/letter content, legal advice, an appropriateness verdict and a second identity-role model
are also outside this document.

## 15. Complete source ledger

| Source | Destination | Disposition |
| --- | --- | --- |
| UVI annex metadata and §§ 0–3 | §§ 1, 3, 9–10 | done/delivery definition, cadence substrate, ingestion and weather-source boundary complete |
| UVI annex § 4 Blocks A–D2 and § 4.5 | §§ 4–8, 11, 13 | every formula, edge, example, label and legal-content blocker mapped |
| UVI annex §§ 5–9 | §§ 1, 3, 10–12 | renter context corrected; delivery, gates, build dependencies and all six decisions mapped |
| DWD importer §§ 1–7 | § 9 and oracle | complete source, format, target identity, importer guards, nine fixtures, operation and attribution |
| DWD latest-state note | § 9 and oracle | stale April headline retained; later verified May-ending file controls |
| Heizspiegel CSV | § 8 and oracle | all 18 data rows, two absent combinations and all source warnings preserved |
| Page 01b H8, F31 and out-of-scope | §§ 1, 7, 9, 14 | annual/monthly split; heat-only direction and labelled fallback; no duplicated money allocation |
| Page 05 W4 | §§ 1, 3 | approved cadence consumed; year-round/heating-season flag retained |
| register CSV rows 4, 11, 17, 21, 29, 30, 35, 43, 45, 50, 51, 117 | § 2 and oracle | every value/source/basis/nature/Rechtsstand/flag retained |
| Non-Goals V1 Page 01b | § 14 and oracle | all eleven entries mapped; dated deferral preserved |
| README-for-Emir | introduction, §§ 2, 12 | arithmetic evidence retained; no red flag cleared |
| Historical correspondence | `docs/03` Appendix D | single retirement ledger; all UVI corrections above remain durable |

## 16. Compact supersession and unresolved ledger

| Historical rule/result | Current disposition |
| --- | --- |
| DWD lower bound 0.50 | superseded by 0.40 after observed 0.49 |
| April 2026 end date as latest DWD state | superseded inside the same note by May 2026 end date, published 15.07.2026 |
| annual DWD factor reused as monthly weather data | rejected; annual factor and monthly degree days stay separate |
| `RENTER` Membership role | rejected; renter is Person/Tenancy context |
| UVI money using largest remainder | rejected; UVI allocates no money and does not alter `docs/03` |
| Block D threshold as three other units | corrected to three valid units including the target |
| D2 compares target heat with Wärme+WW | superseded by heat-with-heat |
| old D2 result `1,733 kWh, +467 kWh, +27.0%` | historical only; current result is in § 8.2 |
| missing over-500 heat-pump/pellet value omitted or extrapolated | use 250–500 with visible label |
| W4 month-end means settled year-round duty | not settled; retain year-round/heating-season uncertainty |
| exact monthly DWD dataset and station-to-PLZ map | unresolved; `verify-before-production` and blocks production C/D2 |
| Block C exact-value instruction versus printed `-52 / 952 = -5.5%` | unresolved; oracle preserves printed result and blocks silent implementation choice |
| Wärmepumpe deduction 8 and annual deduction freshness | convention/year-specific source check remains `verify-before-production` |
| BAnz notice under GEG § 82 is legally the intended § 6a notice | pre-legal; specialist review remains open |

## 17. Approval and implementation boundary

The approved D2 slice was documentation plus data-only fixtures and changed no production, schema,
migration, API, engine, adapter, UI or PDF code. G1 now prepares only the pure W4 cadence evaluator;
it adds no UVI reading, calculation, document, scheduling, delivery or portal consumer. Passing
oracle or G1 tests does not demonstrate a working UVI, clear the unresolved monthly DWD authority,
or authorize production use.
