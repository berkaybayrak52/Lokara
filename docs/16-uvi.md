# UVI — monthly consumption information and comparisons

**Status:** U0 completed the source transcription. U1–U5 are technically implemented: pure UVI
calculation and provenance, versioned Heizspiegel rules, annual/monthly DWD normalization,
account-scoped UVI persistence, owner-side generation, immutable run archives and a separate
German renter document downloadable by the owner. This engineering status is not production
clearance, renter publication, scheduled delivery, email delivery or legal approval.

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
- `Antwort-an-Emir_04.md` § 7

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

Round 4 specifies the monthly DWD degree-day dataset and Lokara's station-to-PLZ assignment rule.
Production Blocks C and D2 remain blocked by the unchosen PLZ geodataset and the three missing UVI
register rows requested in `FRAGEN-an-Berkay-05.md`. The transcription itself is not blocked.

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
| 35 | K12 annual DWD factor: TRY Potsdam/location, about 8,200 PLZ, rolling 12-month periods, about six-week delay, GeoNutzV attribution; the monthly degree-day dataset has no register row yet | DWD · § 6a Abs. 3 S. 3 HeizkostenV with § 82 Abs. 3 GEG | Konvention · `verify-before-production` · 07/2026 |
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

The internal interpolation method `linear_by_elapsed_days` is rendered to renters only as
“linear nach verstrichenen Tagen interpoliert”. The internal identifier never appears in a UVI.

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

### 3.1 U4b — durable normalized inputs before generation

U5 receives only tenancy and target month. It resolves every calculation input server-side; the
request never supplies degree days, energy source, Heizspiegel values, conversion factors or HKV
totals.

`uvi_monthly_degree_day` is immutable and account-scoped. Each row links to the persisted
`UviStationAssignment` and carries its station and month, exact monthly Kd as `Decimal`, valid-day
count, DWD source file and source identity, provenance, `Rechtsstand` and verification status. It
may carry a source-backed monthly share of the annual degree-day total for D2. This share is never
silently derived: this specification supplies no authoritative annual denominator. A missing share
blocks D2 and remains `verify-before-production`. A correction inserts a row with
`supersedes_degree_day_id`; it must retain the same account, assignment, station and month. One row
has at most one direct successor, self-reference and branching are refused, and the current value
is the unique leaf of that correction chain. The predecessor is never updated.

`building_uvi_configuration` is effective-dated and append-only. Each account-scoped version binds
a building to one U2 canonical energy-source identifier, `EnergyReference`, the explicit HKV
allocator marker, an optional exact `Decimal` calorific factor, the complete source identity pair
`source_type` plus `source_id`, `Rechtsstand` and verification status. A changed configuration
inserts a row with `supersedes_configuration_id`; it
does not close or update the predecessor. The predecessor must belong to the same account and
building, one row has at most one direct successor, and self-reference, branching and cycles are
refused. A successor's `valid_from` is strictly later than its predecessor's. For month M,
resolution first selects the deepest successor whose `valid_from` is on or before M. Only that
selected row is then checked against its optional originally supplied `valid_to`. If its `valid_to`
excludes M, generation blocks; an older superseded ancestor is never resurrected as a fallback. An
open-ended predecessor may therefore be superseded by INSERT without mutation. Neither
`HeatingCostEntry.label` nor `MeasurementUnit` determines any configuration fact. The
whole-building size class remains derived from the sum of the building's unit areas; it is not
duplicated here.

`uvi_building_monthly_evidence` is the immutable building-side counterpart to a unit's normalized
month. It carries account, building, calendar month, the selected building-level main meter and
the complete source identity pair `source_type` plus `source_id`, non-empty raw provenance, and at
least one of: exact measured building heat as
`measured_building_heat_kwh_x1000` (`BigInteger`) or the building HKV movement × 1000. There is no
Decimal-to-integer rounding step at this boundary. The main meter must belong to the same
account/building, have `unit_id IS NULL`, `kind = HEAT` and `measurement_unit = KWH`; no tenancy or
unit is fabricated for it.

Each evidence row has at least one immutable account-scoped
`uvi_building_monthly_evidence_source` link to a real `MeterReading`. Composite foreign keys bind
the link to its evidence/account/main meter and its reading/account/meter, so every linked reading
comes from exactly the selected main meter. The evidence parent exposes the needed composite
identity, and `MeterReading` exposes `(id, account_id, meter_id)` as a unique parent key. A
`DEFERRABLE INITIALLY DEFERRED` database constraint trigger checks the minimum-one-link invariant,
so the evidence and its links may be inserted in either order within one transaction but cannot be
committed incomplete. Links are append-only, RLS-scoped evidence; they are not a caller-supplied
JSON substitute. Once linked, the referenced `MeterReading` rejects UPDATE and DELETE even when no
normalized unit-month source link also references it. While any building-month evidence references
a main meter, changes to that meter's `id`, `account_id`, `building_id`, `unit_id`, `kind` or
`measurement_unit` are refused because they would alter the archived evidence identity or its
eligibility. This narrow guard does not freeze unrelated meter metadata.

A correction inserts `supersedes_evidence_id` with the same account, building and month, but may
select a replacement main meter that independently satisfies the eligibility rules. There is one
root chain per account/building/month, independent of meter identity, and each row has at most one
direct successor. The unique correction head is deterministic; self-reference, branching and
cross-context predecessors are refused. Existing evidence and source links are never updated or
deleted.

The pure normalized-month Block A boundary consumes the persisted monthly movement plus its
measurement unit, energy reference and optional calorific factor. It never fabricates cumulative
start/end readings. HKV additionally requires the explicit allocator, the same-month measured
building-level heat total × 1000 and the unit/building HKV movements from the current
`uvi_building_monthly_evidence` leaf. The existing raw-reading links remain the audit evidence
behind the normalized unit movement.

## 4. Shared calculation and output rules

UVI calculation is pure: normalized values in, deterministic result and warnings out. It imports no
database, framework, adapter, clock or vendor library. Legal/conventional values are resolved from
versioned rules data by the caller and retain their as-of date.

Calculate on unrounded values up to the last figure that is displayed. Round the displayed
adjusted/expected consumption and delta to whole kWh, half up, then derive every adjacent displayed
figure from those displayed values. In particular, compute the displayed percentage from the
rounded kWh and round it to one decimal place, half up. This makes every value reproducible from the
figures printed beside it; the renter does not have the unrounded intermediates.

This presentation rule is a `Konvention`, Rechtsstand 08/2026 (source:
`Antwort-an-Emir_04.md` § 7.2). All four approved examples were re-verified without changing a
golden value:

| Block | via rounded values | via exact values | doc example |
| --- | --- | --- | --- |
| B | `50 / 850 = 5.88 -> +5.9%` | identical; no intermediate rounding | `+5.9%` |
| C | `-52 / 952 = -5.46 -> -5.5%` | `-51.61 / 951.61 = -5.42 -> -5.4%` | `-5.5%` |
| D | `-140 / 1040 = -13.46 -> -13.5%` | identical; `13.0` is exact | `-13.5%` |
| D2 | `132 / 1368 = 9.649 -> +9.6%` | identical; `1368` is exact | `+9.6%` |

Block C is the only divergent path, and its approved example already uses the displayed values.
Berkay's round-4 verification row for D2 used the superseded `467 / 1733 = +27.0%` figures; the
current approved `1368 / +132 / +9.6%` figures above remain unchanged and follow the same rule. A
missing value is absent, not zero. A zero denominator suppresses only the percentage and keeps the
absolute value.

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
The former exact-value wording would instead yield `-5.4%`; round 4 resolves the conflict in favour
of the reproducible displayed result. The two degree-day inputs remain an arithmetic fixture, not
production DWD rows.

Missing prior-year consumption prints “liegt im ersten Bezugsjahr noch nicht vor”. Missing or zero
prior-year monthly degree days falls back to `current / prior` and visibly prints
“nicht witterungsbereinigt”. It never supplies `1.00`. Interpolated prior-year consumption retains
its interpolation notice.

### 7.1 Round 4 — monthly degree-day dataset (source: `Antwort-an-Emir_04.md` § 7.1, Rechtsstand 08/2026)

| Property | Contract |
| --- | --- |
| source | `opendata.dwd.de/climate_environment/CDC/derived_germany/techn/monthly/heating_degreedays/hdd_3807/`; `recent/` from 2019-01-01, `historical/` before |
| content | monthly degree-day sums per **VDI 3807** |
| heating limit | **15 °C**; only days whose daily mean is below it count |
| reference room temperature | **20 °C** |
| unit | **Kelvin × day (Kd)** |
| level | **station-based**; coordinates are in the file |
| columns | station id · latitude · longitude · station name · month (`yyyymm`) · valid-day count · monthly degree days · heating-day count · ten-year mean |
| structure | one file per month, updated monthly |
| licence | DWD terms / **GeoNutzV**; “Quelle: Deutscher Wetterdienst” is mandatory |

The dataset is an external DWD source. The annual PLZ climate factors in § 9 remain a different
dataset and cannot supply Block C monthly degree days.

### 7.2 Round 4 — station-to-PLZ assignment (source: `Antwort-an-Emir_04.md` § 7.1, Rechtsstand 08/2026)

DWD publishes PLZ-level values only for the annual climate factors in § 9, for about 8,200 delivery
PLZ, rolling 12-month periods and the Potsdam reference. Degree days exist only per station; there
is no official PLZ-to-degree-day dataset. Lokara therefore uses its own deterministic, versioned
`Konvention`:

```text
1. PLZ -> centroid (latitude/longitude) from a versioned PLZ geodataset
2. candidates = stations with a valid value in the target month
                (valid-day count >= 25; fewer means the month is incomplete)
3. assignment = nearest candidate by great-circle distance on coordinates from
                the DWD file, never a separately maintained station list
4. persist per (PLZ, month) with station id and distance in km
```

- **Persist, never recompute.** A renter's comparison figure must not move because a station drops
  out, and an archived UVI must remain reproducible.
- **Treat a station change between compared months as a data-quality case.** Use a station with a
  valid value in both months. If none exists, walk the next-nearest fallback chain. Attach a visible
  label when the distance exceeds **50 km**.
- **Carry the distance and display it when large.** Distance is part of the quality evidence.
- **Use the DWD file's own coordinates.** Do not maintain a second station-coordinate source.

`[UNSICHER]` The PLZ geodataset is not chosen. Candidates are OpenStreetMap-based PLZ centroids or
a commercial dataset. Large rural-area centroids may sit several kilometres from the building;
geocoding the building address would be cleaner. For V1, the centroid is sufficient only when
labelled as a convention.

Dataset nature: external source (DWD, GeoNutzV). Assignment nature: `Konvention`. Both carry
Rechtsstand 08/2026 and `verify-before-production`. Production Blocks C and D2 remain blocked by
the open PLZ-geodataset choice and the three missing UVI register rows, not by a missing monthly
dataset.

U4b persists the selected station's normalized monthly Kd beside the assignment as specified in
§ 3.1. Persisting the value does not resolve the open PLZ-geodataset choice or clear either
production flag.

Generation resolves Block D before demanding weather or Heizspiegel inputs. If three valid
same-category building units make Block D ready, a missing target or prior-year degree-day row does
not block the run: Block C uses its approved raw fallback “nicht witterungsbereinigt”. A persisted
station assignment without a selected normalized degree-day row remains ingestion evidence, but it
is not archived as a calculation station snapshot. In that raw case the `uvi_run` assignment id,
station id and distance are all null. The three snapshot fields are always all present or all null.
If degree-day rows exist but the target row has no annual share, Block D still completes; the share
is required only after the fewer-than-three-unit branch selects D2.

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

The monthly degree-day share is a resolved, source-backed U4b input. It is not calculated from an
assumed annual denominator. If no such share is stored for the target month, D2 blocks; Block D may
still be used when its own three-valid-unit condition is met.

Block D is selected before a Heizspiegel vintage is resolved. Its archived `heizspiegel_vintage`
is therefore null. D2 alone requires and archives a resolved Heizspiegel vintage and row.

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

#### Round 4 — K13 Heizspiegel vintage maintenance (source: `Antwort-an-Emir_04.md` § 7.3, Rechtsstand 08/2026)

co2online usually publishes the Heizspiegel in autumn for the previous billing year. Check for a
new vintage every year on **1 October**:

1. Pull the new comparison table as a **new file**. Retain all old vintages so archived UVIs remain
   reproducible.
2. Check the size-class boundaries. Changed boundaries are a **schema change**, not only a data
   update.
3. Re-read the method's warm-water surcharge. The `24` value is vintage-dependent and must never be
   carried forward without checking the new method.
4. Recompute `ww_wp = ww_verbrenner / JAZ_assumption`. If the combustion surcharge changes, the
   heat-pump value changes with it. JAZ `3` remains a `Konvention` until co2online supplies another
   source.
5. Run `(mittel - ww) <= 0` for every energy-source x size-class combination. Any hit stops the
   import; do not render.
6. Store the vintage in the rules store with its as-of year. A UVI for month M always uses the
   vintage valid at M, never the newest vintage.

Berkay owns source and values; Emir owns import, guard and test. A delivered UVI must never change
retroactively: its vintage binds to the UVI record, not retrieval time.

Round 4 does **not** confirm the heat-pump `8 kWh/(m²·a)` deduction. It remains the convention
`24 / JAZ 3`, visibly labelled as an assumption and `verify-before-production`; the co2online reply
is outstanding, and the published heat-pump value Berkay found is euro-based rather than kWh-based.

## 9. DWD rolling 12-month climate-factor import

This importer serves Page 01b's annual comparison. It does not provide Block C monthly degree days;
those come from § 7.1.

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

U5 monthly generation produces and archives a separate German renter document and exposes it only
through an owner-authorized download. It does not publish that document to a renter context and
does not schedule or send email. Portal publication remains M10; scheduled and email delivery
remain M9. The U5 archive and `GENERATED` event are append-only; later delivery events must append
evidence and must never rewrite the original UVI.

Before U5 generation, U4b persists the exact server-side inputs in § 3.1. Generation resolves the
configuration effective in each normalized month separately: target month, previous month and the
same month in the prior year. It archives every resolved identity and value in `uvi_run`.
Configuration resolution chooses the deepest successor eligible by `valid_from` before checking
that selected row's `valid_to`; it never resurrects an ancestor. Generation resolves the unique
correction leaf separately for every monthly reading and building-month evidence row it uses, and
for each target/prior-year degree-day row. This applies to the target month, previous month and
same month in the prior year, not only to the target month. Generation does not accept these values
from the client or infer them from display labels.

Target and Block D comparable selection admits only `kind = HEAT`. All selected rows use one
compatible device category; water rows are never target readings or comparables even when their
measurement unit could otherwise be converted.

For all three normalized months, the immutable archive contains the normalized head and raw source
ids, meter id/kind/unit, effective building-configuration identity and values, and the applicable
building-month evidence identity and values. It also contains the target unit area; every selected
normalized reading head and its raw source ids; and, for Block D, each comparable unit id, area,
meter identity/category/unit, normalized head, raw source ids and computed heat. It also retains
the normalized inputs to Blocks A–D/D2, the selected degree-day row identities and their complete
source/provenance status, station-assignment identity when a degree-day value was selected, the
building-configuration identity, and the resolved U2/Heizspiegel row and evidence when D2 was
used. These identities participate in the canonical run hash, so replacing even a numerically
equivalent comparable or source changes the hash without mutating an older run.

Applicable `RuleEvidence` and `RuleConflict` remain structured archive data. This includes the
configuration source, selected DWD rows, the station-assignment convention and the Heizspiegel
source when used. The § 12 Abs. 1 S. 2 and S. 3 reduction risks are archived as structured codes
with their verification status and an explicit no-automatic-deduction flag. No unapproved German
renter wording is derived from those codes; `legal_risks_de` may remain empty until exact wording
is approved.

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

Missing U4b prerequisites are data-quality or production blocks, not permission to invent a
renter-facing absence sentence. The archive retains their structured flags; only approved exact
labels or caller-supplied approved German copy may render.

## 12. Engineering completion and production clearance

### U1–U5 engineering completion

The implemented technical path is complete only while:

- the pure UVI computation has no framework, database, vendor or clock imports;
- every source-named calculation and fallback fixture is executable against production code;
- annual DWD import guards cover headers, leading zeroes, completeness, duplicates, range,
  idempotency, missing PLZ and factor direction;
- the monthly dataset and station-assignment contracts in § 7 execute without silently choosing a
  PLZ geodataset or clearing their production flags;
- all 18 Heizspiegel rows, deductions, heat-pump exception, non-positive guard, over-500 fallback
  and attribution are versioned and tested;
- renter isolation has a negative cross-unit test and every new tenant table has composite account
  isolation, RLS and `FORCE` RLS;
- generation and archive evidence is append-only and retry-safe; publication and delivery remain
  outside U5;
- U4b monthly degree-day, building-month evidence, raw-reading source links and effective
  building-configuration records are immutable, account-safe, source-backed and resolved through
  deterministic append-only correction chains for every month used;
- normalized Block A consumes a monthly movement directly, preserves rule evidence/conflicts and
  blocks missing conversion or HKV prerequisites without fake cumulative readings;
- strict typing, lint, pure-package tests and the required statement/UI review pass.

### Additional production clearance

Technical U1–U5 completion does not clear production use. Production Blocks C and D2 remain blocked
until Emir chooses the versioned PLZ geodataset and the three requested UVI register rows exist.
The exact monthly § 6a/EED content list must be confirmed, versioned and dated. The intended legal
identity of the notice published under GEG § 82, the year-round versus heating-season cadence, the
flagged § 12 reduction risks, the heat-pump deduction convention and every remaining
`verify-before-production`, `[UNSICHER]`, primary-source/legal check or missing Berkay wording keep
their recorded status. None is cleared by a green technical path.

No engine, adapter, schema, API, UI, PDF, scheduler or delivery implementation is part of the U0
round-4 transcription slice. After that historical U0 boundary, U1–U5 implemented the bounded
engineering path described above; M9 delivery and M10 renter publication remain separate work.

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
| `DWD_MONTHLY_DEGREE_DAY_CONTRACT` | monthly VDI 3807 dataset, thresholds, structure and attribution |
| `DWD_STATION_ASSIGNMENT_CONTRACT` | deterministic persisted station assignment and open PLZ-geodataset choice |
| `UVI_DISPLAY_ROUNDING_RULE` | displayed-value rule, four-block re-verification and superseded D2 row |
| `HEIZSPIEGEL_VINTAGE_MAINTENANCE` | annual 1 October check, six maintenance steps and vintage-at-M invariant |
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
| `Antwort-an-Emir_04.md` § 7 | §§ 4, 7.1, 7.2, 8.2 and oracle | monthly dataset, assignment convention, display rounding and K13 vintage maintenance transcribed |

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
| exact monthly DWD dataset and station-to-PLZ rule | resolved by round 4; hdd_3807 plus the persisted nearest-valid-station convention |
| Block C exact-value instruction versus printed `-52 / 952 = -5.5%` | resolved by round 4; displayed values win, so `-5.5%` remains |
| PLZ geodataset and three requested UVI register rows | unresolved; `verify-before-production` and blocks production C/D2 |
| Wärmepumpe deduction 8 | unconfirmed convention; co2online reply remains open and `verify-before-production` |
| W4 year-round/heating-season flag | unresolved |
| exact monthly § 6a content list | unresolved; versioned source required before production |
| BAnz notice under GEG § 82 is legally the intended § 6a notice | pre-legal; specialist review remains open |

## 17. Approval and implementation boundary

U0 is documentation plus data-only fixtures and changes no production, schema, migration, API,
engine, adapter, UI, PDF, scheduler or delivery code. G1 supplies only the pure W4 cadence evaluator;
it adds no UVI reading, calculation, document, scheduling, delivery or portal consumer. Passing the
oracle or G1 tests does not demonstrate a working UVI, choose the PLZ geodataset, create the missing
UVI register rows or authorize production use. After that historical U0 boundary, U1–U5 technically
implement the engine/provenance channel, versioned Heizspiegel resolution, annual/monthly DWD
normalization, account-scoped persistence, owner-side generation, immutable archive and separate
German renter document downloadable by the owner. This does not clear the production blockers in
§ 12, schedule or email delivery under M9, publish to the renter portal under M10, or establish legal
approval.
