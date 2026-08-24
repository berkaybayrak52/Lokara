# LEAD-HANDOFF.md — U0 merged; U1 (the pure uvi-engine) is next

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status` and
`git log` before acting. Git remains authoritative.

## Current state — 24.08.2026

- **M6 is complete and locally merged.** C3c's landlord *Zahlungen* screen closed M6-C and with it
  M6.
- **G1 is complete and locally merged.** `55c97b1`, `f0c3583` and `a8deb9a` merged as `6c257f8`,
  finalized by `b5e380e`. W2 executes the unified six-year MessEV Eichfrist.
- **U0 is complete and locally merged.** The round-4 UVI transcription `cd36deb` closes the two
  blockers `docs/16` had carried since 21.08: the monthly degree-day dataset and the Block C
  rounding order. No golden value moved.
- `main` is ahead of `origin/main`, which is still `f372f67`. **Nothing is pushed.**
- Preserve the untracked `Antwort-an-Emir_04.md`. Never stage with `git add -A`.
- `slice/m6-c3c-zahlungen`, `slice/g-shared-guard-foundation` and
  `slice/u0-round4-uvi-transcription` are merged and can be deleted whenever Emir wants.

## What U0 shipped

`docs/16` § 7.1 names the monthly dataset: DWD `hdd_3807`, monthly degree-day sums per VDI 3807,
heating limit 15 °C, reference room temperature 20 °C, unit Kelvin × day, station-based with the
coordinates in the file itself. § 7.2 is Lokara's own station-to-PLZ `Konvention`, because DWD
publishes PLZ-level values only for the annual climate factors: nearest candidate station with at
least 25 valid days, the same station in both compared months, persisted per `(PLZ, month)` with
station id and distance, visibly labelled beyond 50 km, and never recomputed — § 6a is a
Nachweispflicht and an archived UVI must stay reproducible.

§ 4 carries the decided rounding order: round the displayed kWh first, then derive delta and
percentage from the displayed values, so every figure on a consumer document is reproducible from
the figures printed beside it. All four approved examples were re-verified; Block C is the only
divergent path and its example already printed `-52 / 952 = -5.5 %`.

§ 8.2 adds the six-step K13 Heizspiegel vintage maintenance with its 1 October trigger. Step 6 is
the one that had only been implied: a UVI for month M uses the vintage valid at M, never the newest.

The oracle gained `DWD_MONTHLY_DEGREE_DAY_CONTRACT`, `DWD_STATION_ASSIGNMENT_CONTRACT`,
`UVI_DISPLAY_ROUNDING_RULE` and `HEIZSPIEGEL_VINTAGE_MAINTENANCE`, and resolved the two `None`
fields in `DWD_ANNUAL_IMPORT_CONTRACT`. It stays data-only and claims no engine.

`FRAGEN-an-Berkay-05.md` requests five register rows: the monthly dataset, the station convention,
the display-rounding rule and the two MessEV entries left over from G1. The CSV was not edited.

---

# Next slice — U1: the pure uvi-engine

## Why this slice, and why it is not blocked

U1 turns the nine data-only cases in `UVI_EXAMPLES` into `packages/uvi-engine`, exactly as G1 turned
the nine `12-Fxx` cases into `packages/guard-engine`. `docs/16` is now a complete calculation
contract; nothing in it is unresolved that the arithmetic needs.

**The unchosen PLZ geodataset does not block this slice.** The engine receives degree days,
Heizspiegel rows and comparable units as caller-supplied normalized inputs, the same way
`evaluate_meter_calibration` receives a `MeterCalibrationRuleBundle`. Choosing a geodataset and
importing DWD files is adapter and importer work for a later slice. Do not let it into U1.

`docs/16` § 12 still gates *production*: implementing the engine clears none of the
`verify-before-production` flags and produces no sendable document.

## Lanes and mechanics

Three lanes, because `.claude/hooks/write-scope.sh:93-99` limits `engine-implementer` to
`packages/*/src/*` — it cannot create a package or edit build files.

**Step 1 — the main session scaffolds.** Five places, all verified:

1. `packages/uvi-engine/pyproject.toml`, modeled on `packages/guard-engine/pyproject.toml`:
   name `lokara-uvi-engine`, `dependencies = ["lokara-domain"]`, hatchling, wheel package
   `src/lokara_uvi_engine`.
2. Root `pyproject.toml`, four lists: `[tool.uv.workspace] members`, the `dev` dependency group,
   `[tool.uv.sources]`, `[tool.mypy] files` (both `src` and `tests`) and
   `[tool.pytest.ini_options] testpaths`.
3. `scripts/check_engine_purity.py` `LAYERS`: add `packages/uvi-engine/src` with the crown-jewel
   `forbidden_internal` set — `lokara_rules_store`, `lokara_adapters`, `lokara_db`, `lokara_api`,
   `lokara_pdf`, `lokara_nk_engine`, `lokara_heating_engine`, `lokara_matching_engine`,
   `lokara_guard_engine`.
4. `scripts/gate.sh:85-88`, the `fast` pure-package pytest list.
5. `uv sync`, so the new member is installed editable.

**Step 2 — `spec-scribe` writes the executable fixture** at
`packages/uvi-engine/tests/test_page_uvi_u1_golden.py`. Follow
`packages/guard-engine/tests/test_page05_g1_golden.py`: it **restates** the fixture values as module
constants and asserts them through production code. Do **not** import `berkay_uvi_golden` across
package boundaries — that oracle is rules-store's own data evidence, and a cross-package test import
depends on pytest's `sys.path` insertion order. Two files, two jobs.

This opens the mandatory red window. Write `.lokara-red` with one line naming the slice and the
reason, e.g. `slice/u1-uvi-engine · docs/16 Block A-D2 fixtures land before the engine`. It is
untracked and gitignored; `fast` announces it and does not block, `full` and `demo` treat it as a
hard failure. Fewer than 10 characters is rejected as an anonymous off switch.

**Step 3 — `engine-implementer` writes `packages/uvi-engine/src/lokara_uvi_engine/`** until the
fixture is green, then deletes `.lokara-red`. It may not touch the tests. Split `models.py` and
`evaluators.py` the way `lokara_guard_engine` does, and ship `py.typed`.

## What the engine must implement

Frozen `slots=True` dataclasses in, deterministic results out. `decimal.Decimal` with
`ROUND_HALF_UP`, never `float`. No rules-store import, no ambient clock, no I/O.

| `docs/16` | Case in the oracle | Rule |
| --- | --- | --- |
| § 5 | `emir_spec_block_a_kwh` | reading movement ×1000 → whole kWh |
| § 6 | `emir_spec_block_b_previous_month` | previous-month delta and percent |
| § 7 | `emir_spec_block_c_weather_adjusted` | degree-day adjustment; **round the displayed kWh first**, then derive delta and percent from the displayed values (§ 4) |
| § 7 | `approved_block_c_raw_weather_fallback` | missing or zero degree days → raw comparison labelled “nicht witterungsbereinigt”; never an implicit factor `1.00` |
| § 8.1 | `emir_spec_block_d_building_cross_section` | building cross-section; at least three valid units **including** the target, else no Block D |
| § 8.2 | `approved_block_d2_heat_only` | Heizspiegel heat-only after the warm-water deduction, degree-day share, area; `(mittel − ww) <= 0` refuses rather than renders |
| § 3 | `approved_hkv_provisional` | provisional unit kWh from HKV units; a missing building total returns blocked, not zero |
| § 3 | `approved_linear_mid_month_interpolation` | linear by elapsed days, provenance retained on the result |

Reuse the domain value objects instead of inventing parallels: `lokara_domain.meter`
(`MeasurementUnit`, `ReadingReason`, `ReadingSource`) and `lokara_domain.energy`
(`EnergyReference`). German output strings are part of the result, per `docs/16` § 11.

## Must not do

- No importer, adapter, schema, migration, API, UI, PDF, scheduler or delivery code. U1 is the pure
  engine and its fixture, nothing else.
- **Do not reuse `packages/rules-store/src/lokara_rules_store/rules/degree_days.py`.** That is the
  VDI 2067 Gradtagszahl mid-period apportionment table for § 9b HeizkostenV (Zehntelpromille summing
  to 10,000) — a different dataset from § 6a Block C monthly degree days, and the trap this slice is
  most likely to fall into.
- Do not choose the PLZ geodataset, and do not implement station assignment. Both are later work and
  both remain `verify-before-production`.
- Do not change a value in `docs/16` or the rules-store oracle. If the engine disagrees with a
  printed example, stop and ask — `CLAUDE.md` § 4.
- Do not pull the heat-pump 8 kWh/(m²·a) deduction to `geprüft`.
- Do not edit `berkay-work/`. The CSV stays at 180 rows.
- Do not stage `Antwort-an-Emir_04.md`. Never `git add -A`.
- Do not run `scripts/verify_demo_path.sh --fresh`; U1 needs no schema and it destroys local
  Postgres.

## Acceptance and stop condition

```bash
uv run pytest packages/uvi-engine/tests -q
scripts/gate.sh full
```

The full gate must run with `.lokara-red` deleted; it is fatal there by design. Stop when the gate
is green and `git status` shows only the scaffolding files, `packages/uvi-engine/` and the untracked
`Antwort-an-Emir_04.md`.

**Then show Emir the diff and wait. Do not commit.** Per `AGENTS.md` § 4, an agent past roughly
40 turns without its deliverable stops and reports what it has rather than spending further.

---

## Database state

Unchanged: development matches migration `0021` and Alembic is at `0021`. G1, U0 and U1 require no
schema change. Do not reset the Docker volume. The validated backup remains at
`/tmp/lokara-m6c3a-pre-migration-20260824.dump`.

## Evidence

For U0 as merged, `scripts/gate.sh fast` is green with 566 pure-package tests, and the full gate is
green including 84 web tests. Strict mypy and engine purity are clean. `uv run pytest
packages/rules-store/tests -q` passes 124 tests. No rendered output changed, so no statement review
was required and the normalized PDF fingerprint stays `88eb8434eda65f8d7ff82826fc837a58` at
149269 bytes.

## Recorded, not fixed

- `require_owner` answers 403 with the English, route-inaccurate detail
  `"Only owners may create buildings"` (`authorization.py`), which the client prints verbatim.
- The ledger renders `created_at` through a timezone-naive string split, so a late-evening booking
  on a UTC server can show the previous calendar day. Backend/timezone decision.
- `match_proposal.convention_version` is persisted but not exposed by `_candidate_json` or
  `list_proposals`, so the *Zahlungen* screen's `Rechtsstand` stamp is a page-level constant. That
  payload gap is C3a's.
- The error copy *"Bitte API und Datenbank prüfen"* is developer-facing, but it is the house
  convention in seven other screens; diverging on one screen would be worse.
- `Ablehnen` and `Dublette` write an immutable record with no confirmation step, and a decided
  proposal does not link to the journal entry it produced.
- The *Zahlungen* screen has never been exercised against a live API: the four queries and the 409
  conflict path are unverified at runtime.
- Berkay's own round-4 rounding verification checks Block D2 against the superseded `467 / 1733`
  figures. The rule holds for the current `1368 / +132 / +9.6 %`; `docs/16` § 4 records this rather
  than restating his row as current.

## Unresolved authority — technical closure is not legal approval

- **U0 cleared exactly two UVI items.** Production Blocks C and D2 remain blocked by the unchosen
  PLZ geodataset and by three missing UVI register rows. U1 does not change that.
- The heat-pump `8 kWh/(m²·a)` deduction stays the convention `24 / JAZ 3` and
  `verify-before-production`. Round 4 explicitly refuses to confirm it; the co2online reply is open.
- CSV rows 128 and 129 still print the superseded five-year Eichfrist readings. Two new register
  rows are requested; nobody restores five years in the meantime.
- W4's year-round versus heating-season duty, the exact monthly § 6a content list, and whether the
  BAnz notice under GEG § 82 is legally the intended § 6a notice all remain open.
- Page-08 weights and thresholds stay `verify-before-production` at `Rechtsstand 07/2026`; the
  180-day AIS consent window still has no register row; the § 4 stored-reference signal stays inert.
