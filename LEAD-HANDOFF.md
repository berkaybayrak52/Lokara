# LEAD-HANDOFF.md — U2 is green but uncommitted; three U slices remain, U3 first

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status` and
`git log` before acting. Git remains authoritative.

## Current state — 24.08.2026

- **M6 is complete and locally merged.** C3c's landlord *Zahlungen* screen closed M6-C and with it
  M6.
- **G1 is complete and locally merged.** `6c257f8`, finalized by `b5e380e`. W2 executes the unified
  six-year MessEV Eichfrist.
- **U0 is complete and locally merged.** The round-4 UVI transcription, `738e048`, finalized by
  `0efbc7f`.
- **U1 is complete and locally merged.** The pure `packages/uvi-engine` — `afc723c` and the brief
  commit `0a60721`, merged as `d02c838`.
- **U1b is complete, reviewed and locally merged.** Feature commit `ed82202` was merged as
  `ee83535`. Its statement-review finding is resolved and the closing full gate is green.
- **U2 is complete, reviewed, green and not committed.** Its three-file diff sits on
  `slice/u2-heizspiegel-rules` at base `ab875d2`. Do not start U3 until U2 is landed.
- `main` is ahead of `origin/main`, which is still `f372f67`. **Nothing is pushed.**
- Preserve the untracked `Antwort-an-Emir_04.md`. Never stage with `git add -A`.
- `slice/m6-c3c-zahlungen`, `slice/g-shared-guard-foundation`, `slice/u0-round4-uvi-transcription`
  `slice/u1-uvi-engine` and `slice/u1b-uvi-provenance` are merged and can be deleted whenever Emir
  wants.

## What U1 shipped

`packages/uvi-engine` executes `docs/16` Blocks A, B, C with its raw fallback, D, D2, the HKV
provisional path and linear mid-month interpolation, against the nine `UVI_EXAMPLES` cases. Frozen
`slots=True` dataclasses in, deterministic results out, `Decimal` with `ROUND_HALF_UP` and no
`float`.

Block C follows the § 4 display-rounding decision: the weather-adjusted reference is rounded to
whole kWh first, then delta and percent are derived from the displayed values. Missing or zero
degree days give a raw comparison labelled `nicht witterungsbereinigt`, never an implicit `1.00`.
Block D's three-valid-unit minimum including the target cannot be lowered by the caller. Block D2
refuses a non-positive heat-only reference. The HKV path returns blocked, not zero, when the
building total is missing.

The engine imports `lokara_domain` only. It does not reuse `rules/degree_days.py`, which is the
VDI 2067 § 9b apportionment table and a different dataset.

**U1 satisfies exactly one of `PLAN.md` § U's five `Done when` conditions.** No importer, adapter,
schema, API, UI, PDF or delivery code exists. Production Blocks C and D2 stay blocked by the
unchosen PLZ geodataset and the three missing UVI register rows.

## What U1b shipped — reviewed, green and locally merged

U1b closed the structural gap the U1 statement review found. It is complete, reviewed and locally
merged as `ee83535`; nothing is pushed.

`packages/domain/src/lokara_domain/provenance.py` is the one home for the shared shapes:
`SourceIdentity`, `RuleEvidence` (`source`, `register_row`, `legal_basis`, `rechtsstand`,
`verification_status`) and `RuleConflict` (`code`, `description`, `production_blocking`,
`applies_to_media`), frozen and slotted, with the guard engine's exact field names so the two can be
consolidated later without a third spelling. `packages/guard-engine` was left untouched, as briefed.

In `packages/uvi-engine`, every evaluator now takes a caller-supplied `UviRuleBundle` as its second
argument and every result returns `rule_evidence` and `unresolved_conflicts`. Per block:
`BlockAResult` gained `label_de`; `BlockCInput`/`BlockCResult` carry the § 7.2 DWD attribution,
station id, distance and a `station_distance_over_50_km` boolean derived from the distance, not a
label; `BlockD2Input` takes a `ResolvedHeizspiegelRow` — energy source, requested and actual size
class, mittel, deduction, vintage, `fallback_label_de` and its own evidence — instead of bare
`Decimal`s; `BlockD2Result` returns the size class actually used and the caller's fallback label.
Suppression is consistent: a blocked result carries **no** renter-facing label, with `basis_de`,
`label_de` and `attribution_de` all `None`, and one test walks every blocked branch of A, D and HKV
to assert exactly that. No arithmetic changed and no golden value moved — `Decimal(114)`,
`Decimal(24)` and the heat-pump `Decimal(8)` are all still there, now inside the resolved row.

The required `statement-reviewer` pass verified suppression and the exact ready-state labels. It
found one provenance defect: Block D2 dropped distinct bundle evidence when its resolved row carried
different evidence. A separate failing fixture proved the defect; the engine now returns bundle
evidence followed by resolved-row evidence with equal entries deduplicated. Both blocked and ready
D2 paths are covered.

`scripts/gate.sh full` is green on this tree with 1,278 Python and 84 web tests.
`uv run pytest packages/uvi-engine/tests packages/domain/tests -q` passes 121.

Two things are recorded, not fixed, and both belong to a later slice:

- `BlockAResult.label_de` exists but **no evaluator populates it**. The § 5 provisional label is
  produced by `evaluate_hkv_provisional`, so the caller composing the two in U5 must carry it onto
  the Block A figure. Nothing enforces that today.
- `SourceIdentity` is defined and exported but no UVI type consumes it. It is there for U4's
  `uvi_run` archive identity.

---

# U2 closure and the remaining U work — U3 to U5

U2 is green but uncommitted. Land it before U3; otherwise U3's diff would contain the Heizspiegel
rules module and fixture.

Work them **top to bottom, one at a time.** Each slice is self-contained and each ends the same
way: the full gate green with `.lokara-red` deleted, then **show Emir the diff and wait. Do not
commit, merge or push.** Emir authorizes every commit; `AGENTS.md` § 8 is explicit that nothing is
merged automatically. Do not start the next slice until he says so.

Per `AGENTS.md` § 4, an agent past roughly 40 turns without its deliverable stops and reports what
it has rather than spending further. A slice that turns out to be bigger than it looked is split,
not rushed.

## Standing rules for every slice below

- **Two lanes, never one agent.** `spec-scribe` writes the spec and the failing fixture;
  `engine-implementer` or `app-implementer` makes it pass. `.claude/hooks/write-scope.sh` enforces
  this: `engine-implementer` may write `packages/*/src/*` and `packages/db/alembic/*` only
  (`:93-99`), and it may not touch a test. `PLAN.md` hard rule 1: no calculation without its golden
  fixture first.
- **The red window is mandatory.** When the fixture lands before the code, write `.lokara-red` with
  one line naming the slice and the reason. It is untracked and gitignored; `fast` announces it and
  does not block, `full` and `demo` treat it as a hard failure. Fewer than 10 characters is rejected
  as an anonymous off switch. Delete it before the closing full gate.
- **No golden value moves.** If the code disagrees with a printed example in `docs/16` or the
  oracle, stop and ask — `CLAUDE.md` § 4. Do not choose silently.
- **No invented German.** `docs/16` leaves five renter-facing texts unspecified (below). Carry a
  flag or a caller-supplied string; never a phrase Lokara wrote.
- **No flag is cleared.** Nothing in U clears a `verify-before-production` marker. Blocks C and D2
  stay production-blocked until Emir chooses the PLZ geodataset and Berkay supplies the three
  missing register rows.
- Do not edit `berkay-work/`. The CSV stays at 180 rows.
- Do not stage `Antwort-an-Emir_04.md`. Never `git add -A`.
- Do not run `scripts/verify_demo_path.sh --fresh` for U2 or U3 — neither needs a schema and it
  destroys local Postgres. U4 and U5 touch the database; ask Emir before any reset.

## U2 delivered — the versioned Heizspiegel rules data

### Why

`docs/16` § 12 requires that "all 18 Heizspiegel rows, deductions, heat-pump exception, non-positive
guard, over-500 fallback and attribution are versioned and tested". U2 now carries them in
production rules data and resolves the fixed U1b target `ResolvedHeizspiegelRow`.

### Lanes

No build-file scaffolding — `packages/rules-store` is already a workspace member, already in
`[tool.mypy] files`, already in `[tool.pytest.ini_options] testpaths` and already in the fast gate's
pure list at `scripts/gate.sh:85-89`.

`spec-scribe` wrote `packages/rules-store/tests/test_heizspiegel_rules.py`, restating the 18 rows,
the five deductions and the D2 contract as module constants and asserting them through code that
does not exist yet. **Restate; do not import `berkay_uvi_golden`.** That oracle is the
transcription's own data evidence, and a test importing it proves only that two copies of one file
agree. It then opened the red window.

`engine-implementer` wrote `packages/rules-store/src/lokara_rules_store/rules/heizspiegel.py`,
exported it from `rules/__init__.py` in the existing alphabetical style, and deleted the sentinel.

### What the data must carry

Follow `rules/co2_emission_factors.py` as the house pattern: a module docstring naming the source,
the flags and what is deliberately not smoothed over; `Final`; `MappingProxyType` for the tables;
and `RuleSet`/`RuleVersion` from `..store` so an as-of lookup resolves a vintage.

| `docs/16` § 8.2 | Contract |
| --- | --- |
| the table | all 18 rows, `(size class, energy source) -> low / mittel / hoch / zu hoch ab`, integer `kWh/(m²·a)`, no `float` |
| size classes | exactly `80-150`, `150-250`, `250-500`, `ueber-500`; a changed boundary is a schema change, not a data update |
| warm water | 24 for Erdgas, Heizöl, Fernwärme and Holzpellets; **8 for Wärmepumpe**, the `24 / JAZ 3` convention |
| import guard | `(mittel − ww) <= 0` for **every** size-class × energy-source pair stops the import; the engine's own per-call guard does not replace it |
| over 500 m² | Wärmepumpe and Holzpellets have no row; resolve to the `250-500` row and carry the fallback label through `ResolvedHeizspiegelRow.fallback_label_de` |
| attribution | every D2 output prints `Quelle: co2online gGmbH (Heizspiegel)` |
| vintage | Heizspiegel 2025, billing year 2024, as of 09/2025; a UVI for month M resolves the vintage valid at M, never the newest |

Every resolved row is handed to the engine as a `ResolvedHeizspiegelRow`, whose `evidence` tuple
carries `RuleEvidence` with the register source, the `Rechtsstand` and the verification status.
`requested_size_class` and `actual_size_class` differ exactly when the over-500 fallback fired. The Wärmepumpe deduction's status is
`verify-before-production`; carrying it is the opposite of confirming it.

### Must not do

- **Do not import this module from `packages/uvi-engine`.** `scripts/check_engine_purity.py`
  forbids `lokara_rules_store` there, and that boundary is the point of the slice.
- No importer, adapter, schema, API, UI or PDF code. DWD is U3; the schema is U4.

### Acceptance

```bash
uv run pytest packages/rules-store/tests -q
scripts/gate.sh full
```

Both commands are green: 135 rules-store tests and the full gate with 1,289 Python and 84 web
tests. The required statement review found two provenance gaps; separate failing fixtures and the
engine fix now retain each future vintage's own row identity plus both publication and effective
Rechtsstand. The re-review has no open U2 finding. The heat-pump deduction remains a visible
`verify-before-production` convention for U5 to render without invented German wording.

---

## 2. U3 — the DWD adapters

### Why

`docs/16` § 12 requires the annual import guards and the § 7 monthly dataset and station assignment.
Two different DWD datasets, deliberately not interchangeable: § 9 is the **annual PLZ climate
factor** for Page 01b's yearly comparison, § 7.1 is the **monthly `hdd_3807` degree-day sum** for
Block C. Neither is `rules/degree_days.py`, which is the VDI 2067 § 9b apportionment table.

Split this into two slices if the annual guards run long. They are independent.

### Lanes

`spec-scribe` writes `packages/adapters/tests/test_dwd_import.py`; `engine-implementer` writes
`packages/adapters/src/lokara_adapters/dwd.py` and exports it from `lokara_adapters/__init__.py`.
Follow `adapters/destatis.py`: a `Protocol` port, a frozen normalized dataclass, a stub returning
fixture data, and a `TODO(provider)` marking where the real fetch plugs in. Only the adapter knows
the vendor format — `CLAUDE.md` § 6.

### 3a — the § 9 annual climate-factor import

Source `derived_germany/techn/monthly/climate_correction_factor/recent`, v22.3, GeoNutzV with
`Quelle: Deutscher Wetterdienst` mandatory. `KF_<VON>_<BIS>.csv` point-decimal preferred, `_k.csv`
comma-decimal, XML equivalent with `VON_DATUM`, `BIS_DATUM`, `KLFK_POLZ`, `KLIMAFAKTOR`. All eight
guards `docs/16` § 12 names, each its own test:

1. header shape `DatAnf;DatEnd;PLZ;KF`;
2. leading zeroes — the source omits them, left-pad to five characters;
3. completeness — at least 7,000 rows; the verified 2025 file has 8,234;
4. duplicates;
5. range — accept `0.40` through `1.80` inclusive, exact decimal;
6. idempotency — identity `(plz, period_from, period_to)`, upsert, never delete an old period;
7. missing PLZ — labelled raw comparison, never a silent `1.00`;
8. direction — a milder period means `KF > 1` and raises adjusted heat; inversion is forbidden.

The nine verified `01.01–31.12.2025` fixtures are in `docs/16` § 9 and
`DWD_ANNUAL_CLIMATE_FACTOR_PLZ_FIXTURES`. The latest verified file is `KF_20250601_20260531`,
period 01.06.2025–31.05.2026, published 15.07.2026; the April headline is history, not current
state.

### 3b — the § 7.1 monthly parse and the § 7.2 station assignment

Parse `hdd_3807`: monthly degree-day sums per VDI 3807, heating limit 15 °C, reference room
temperature 20 °C, unit Kelvin × day, station-based, nine columns, one file per month, coordinates
in the file itself.

Then the § 7.2 assignment, as a **deterministic pure function**, not a fetch:

```text
1. PLZ -> centroid (latitude/longitude) from a caller-supplied, versioned PLZ geodataset
2. candidates = stations with a valid value in the target month (valid-day count >= 25)
3. assignment = nearest candidate by great-circle distance on the DWD file's own coordinates
4. return station id and distance in km for persistence per (PLZ, month)
```

Use the same station in both compared months; if none has a valid value in both, walk the
next-nearest fallback chain. Return the distance and a flag above 50 km — **not** a label, whose
wording nobody has supplied. Never maintain a second station-coordinate source.

### Must not do

- **Do not choose the PLZ geodataset and do not ship one.** It is Emir's open decision; the centroid
  table is a caller-supplied input to this function. Shipping a dataset would decide it silently.
- Do not persist anything. Persistence is U4; this slice returns values.
- Do not merge the two datasets or reuse `rules/degree_days.py`.

### Acceptance

```bash
uv run pytest packages/adapters/tests -q
scripts/gate.sh full
```

---

## 3. U4 — schema, persistence and renter isolation

### Why

`docs/16` § 12 requires that "renter isolation has a negative cross-unit test and every new tenant
table has composite account isolation, RLS and `FORCE` RLS", and that "archive and delivery evidence
is append-only and retry-safe". This is the first U slice that touches the database.

### Lanes

`spec-scribe` writes the tests, including the RLS isolation lines; `engine-implementer` writes
`packages/db/src/lokara_db/models.py` and the migration under `packages/db/alembic/versions/`. The
next number is `0022`; development and Alembic are both at `0021`. **Ask Emir before any database
reset** and do not run `scripts/verify_demo_path.sh --fresh` on your own.

### What to build

| Table | Purpose |
| --- | --- |
| monthly readings | the § 3 normalized monthly readings the engine consumes, with reading reason and source |
| `uvi_run` | the append-only archive: inputs, results, the resolved Heizspiegel vintage, the station id and distance, and a hash |
| station assignment | `(PLZ, month) -> station id, distance km`, persisted once and **never recomputed** — an archived UVI must stay reproducible and a renter's figure must not move because a station dropped out |
| climate factors | the § 9 annual `(plz, period_from, period_to)` rows, upserted idempotently, old periods retained |
| delivery ledger | generated / published / emailed / failed with timestamps; a retry **appends** status evidence and never rewrites the original UVI |

Every table carries `account_id`, composite foreign keys that preserve account isolation, RLS and
`FORCE` RLS, and a policy with a `WITH CHECK` clause — `USING` alone filters reads while still
allowing an INSERT stamped with someone else's account. Legally relevant rows are immutable and
versioned: create a new version, never overwrite (`CLAUDE.md` § 3.2).

### Verification this slice must run itself

`scripts/gate.sh` does **not** run these — they are explicit commands:

```bash
uv run python scripts/check_rls_coverage.py
uv run python scripts/check_fk_isolation.py
```

`check_rls_coverage.py` requires each new table to be named in
`packages/db/tests/test_rls_isolation.py` **inside a test that attempts a cross-account write**. A
mere import satisfying "named" is exactly the gap the 23.08.2026 audit found behind six defects.
Never weaken the script to make the gate pass (`CLAUDE.md` § 3.3).

Then request `boundary-auditor` (`AGENTS.md` § 7). It proves a finding **inside a transaction that
is rolled back** — never a committed probe row in an append-only table.

### Must not do

- No renter-facing endpoint, portal route or document. That is U5 and M10.
- Do not weaken or exempt a table in `check_rls_coverage.py`.

### Acceptance

```bash
uv run alembic -c packages/db/alembic.ini upgrade head
uv run python scripts/check_rls_coverage.py
uv run python scripts/check_fk_isolation.py
scripts/gate.sh full
```

---

## 4. U5 — generation and the renter document

### Why

The last of `PLAN.md` § U's engineering conditions: the UVI document exists and is tenant-isolated.

### Lanes

`spec-scribe` writes the tests; `app-implementer` writes the router under
`apps/api/src/lokara_api/routers/` and the template in `packages/pdf/src/lokara_pdf/`. Follow the
existing shape: `statements.py` and `portal.py` for the router, `statement.py` and `render.py` for
the document, `rechtsstand.py` for the as-of stamp.

### What to build

Landlord-side monthly generation that composes the U1b engine results, the U2 Heizspiegel bundle and
the U3 degree days — including the one obligation the engine cannot enforce: carry
`evaluate_hkv_provisional`'s `provisorisch, Endwert erst zur Jahresabrechnung` onto the Block A
figure through `BlockAResult.label_de`, which no evaluator populates. Generation writes one
immutable `uvi_run` and renders **one separate German renter document** carrying the `docs/16` § 11
mandatory content: the target month and unit, Block A, the three mandatory comparisons or their
exact labelled absence or fallback state, the basis
`Vergleich im Gebäude` or `normierter Durchschnittsnutzer`, every source and provenance label, and
the legal content applicable to a monthly UVI. Add `Rechtsstand MM/JJJJ` — `CLAUDE.md` § 6 requires
it on every legal output and no UVI result carries one today.

Authorization is by the Person's account-scoped tenancy relationship, never a new Membership role,
and every read is scoped in app logic **and** RLS. A hidden link is not authorization. The
landlord's all-party calculation view is never exposed to a renter.

### Boundaries that are not this slice

- **Renter portal publication is M10** and **scheduled delivery is M9** (`docs/16` § 10,
  `CLAUDE.md` § 3.3, `PLAN.md`). U5 generates, archives and renders; it does not publish or send.
- Register row 29's checked annual § 6a list is not permission to assume the monthly list is
  identical. The exact monthly content list stays `verify-before-production` and must be versioned
  with an as-of date before production.
- Reduction rights appear as separate risks. Lokara never deducts 3 % or 15 % automatically.

### Reviews

`statement-reviewer` on the rendered document (`AGENTS.md` § 7), and
`scripts/pdf_fingerprint.sh` recorded before and after, since this slice changes rendered output.

### Acceptance

```bash
scripts/gate.sh demo
```

---

## What U still needs that no agent can deliver

- **Emir chooses the PLZ geodataset.** `docs/16` § 7.2 names OpenStreetMap-based PLZ centroids or a
  commercial dataset, and records that geocoding the building address would be cleaner but larger.
  A rural centroid can sit several kilometres from the building, so for V1 the centroid is
  sufficient only when labelled as a convention.
- **Berkay supplies the three missing UVI register rows** — the monthly `hdd_3807` dataset, the
  station-to-PLZ convention and the Block C display rounding — requested in
  `FRAGEN-an-Berkay-05.md`. The CSV stays at 180 rows until he answers.
- **Berkay supplies five missing German texts:** the over-500 label's trailing full stop, the
  zero-denominator suppression texts for Blocks C, D and D2, the interpolation notice, the
  over-50 km distance label, and a neutral alternative to
  `liegt im ersten Bezugsjahr noch nicht vor`, which today also prints for a data gap, a device
  change or a renter change.

Until the first two land, Blocks C and D2 stay production-blocked however much of this list is
built. Finishing all five slices closes U's engineering, not its authority.

---

## Database state

Unchanged: development matches migration `0021` and Alembic is at `0021`. U1b, U2 and U3 require
no schema change; U4 adds `0022` and U5 builds on it. Do not reset the Docker volume.
The validated backup remains at `/tmp/lokara-m6c3a-pre-migration-20260824.dump`.

## Evidence

On the working tree that carries U2, `scripts/gate.sh full` is green with 1,289 Python and 84 web
tests. Strict mypy and engine purity are clean; the U2 focused suite passes 11 and all rules-store
tests pass 135. Nothing in U renders yet, so the normalized PDF fingerprint stays
`88eb8434eda65f8d7ff82826fc837a58` at 149269 bytes.

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
- `docs/16` prescribes no German wording for four renter-facing cases the U1 review surfaced: the
  zero-denominator suppression in Blocks C, D and D2, the interpolation notice, the over-50 km
  distance label, and whether the § 8.2 over-500 label ends in a full stop. They are asked in
  `FRAGEN-an-Berkay-05.md`; until answered, U1b carries flags and caller-supplied strings only.
- `liegt im ersten Bezugsjahr noch nicht vor` is `docs/16` § 7's prescribed text for any missing
  prior-year value, so it also prints for a data gap, a device change or a renter change. A
  fourth-year renter then reads something untrue. The engine matches the doc; the wording is
  Berkay's to change and is asked.
- `packages/guard-engine` keeps its own `GuardSourceIdentity`, `RuleEvidence` and `RuleConflict`
  now that U1b has put the shared shapes in `lokara_domain`. The field names are identical, so the
  duplication is inert. Consolidating them is a later cleanup; it would churn a merged,
  statement-reviewed slice for no behavioural gain.
- `BlockAResult.label_de` and `lokara_domain.SourceIdentity` both exist with no producer or consumer
  yet. U5 must populate the first; U4 uses the second for the `uvi_run` archive identity.
- Berkay's own round-4 rounding verification checks Block D2 against the superseded `467 / 1733`
  figures. The rule holds for the current `1368 / +132 / +9.6 %`; `docs/16` § 4 records this rather
  than restating his row as current.

## Unresolved authority — technical closure is not legal approval

- **U1 cleared no flag.** Production Blocks C and D2 remain blocked by the unchosen PLZ geodataset
  and by three missing UVI register rows. Neither U1b nor U2 changes that.
- The heat-pump `8 kWh/(m²·a)` deduction stays the convention `24 / JAZ 3` and
  `verify-before-production`. Round 4 explicitly refuses to confirm it; the co2online reply is open.
- CSV rows 128 and 129 still print the superseded five-year Eichfrist readings. Two new register
  rows are requested; nobody restores five years in the meantime.
- W4's year-round versus heating-season duty, the exact monthly § 6a content list, and whether the
  BAnz notice under GEG § 82 is legally the intended § 6a notice all remain open.
- Page-08 weights and thresholds stay `verify-before-production` at `Rechtsstand 07/2026`; the
  180-day AIS consent window still has no register row; the § 4 stored-reference signal stays inert.
