# LEAD-HANDOFF.md — U1 merged; U1b (engine provenance) is next

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status` and
`git log` before acting. Git remains authoritative.

## Current state — 24.08.2026

- **M6 is complete and locally merged.** C3c's landlord *Zahlungen* screen closed M6-C and with it
  M6.
- **G1 is complete and locally merged.** `6c257f8`, finalized by `b5e380e`. W2 executes the unified
  six-year MessEV Eichfrist.
- **U0 is complete and locally merged.** The round-4 UVI transcription, `738e048`, finalized by
  `0efbc7f`.
- **U1 is complete and locally merged.** The pure `packages/uvi-engine` — slice commit `afc723c`.
- `main` is ahead of `origin/main`, which is still `f372f67`. **Nothing is pushed.**
- Preserve the untracked `Antwort-an-Emir_04.md`. Never stage with `git add -A`.
- `slice/m6-c3c-zahlungen`, `slice/g-shared-guard-foundation`, `slice/u0-round4-uvi-transcription`
  and `slice/u1-uvi-engine` are merged and can be deleted whenever Emir wants.

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

---

# Next slice — U1b: result provenance and labelled suppression

## Why this slice, and why it comes before U2

The required `statement-reviewer` pass on U1 verified all nine German strings byte-exactly against
`docs/16` and found no wording defect. It found a structural one: **the engine has no provenance
channel.**

`packages/guard-engine`, merged one slice earlier, already solved this. Its `models.py` carries
`GuardSourceIdentity`, `RuleEvidence` with `source`, `register_row`, `legal_basis`, `rechtsstand`
and `verification_status`, and `RuleConflict` with `production_blocking`; every bundle carries them
and `GuardResult` returns them. `packages/uvi-engine` carries none of it, because the U1 brief did
not ask for it. That omission is mine, not the implementer's — U1 built exactly what it was briefed
to build, and its arithmetic is correct.

Five consequences, each verified against the merged code:

1. **The unconfirmed Wärmepumpe deduction renders as settled.** `BlockD2Input` takes
   `warm_water_deduction_kwh_m2a: Decimal` with no status, so a heat-pump D2 is indistinguishable
   from a gas D2. `docs/16` § 8.2 requires the `24 / JAZ 3` convention to be *"visibly labelled as
   an assumption"* and `verify-before-production`. `CLAUDE.md` § 6 requires `Rechtsstand MM/JJJJ` on
   legal output; `BlockD2Result.heizspiegel_vintage` is the only as-of value in any result type.
2. **The § 8.2 over-500 fallback label has nowhere to travel.** Row selection is correctly the
   rules data's job, not the engine's — that is U2. But `building_size_class` is an input that never
   reaches the result, so an over-500 Wärmepumpe building borrowing the 250–500 row renders exactly
   like a genuine 250–500 building. § 8.2 adds that the fallback *"is not guaranteed conservative"*.
3. **Block C carries no DWD attribution, station or distance.** § 7.1 makes
   `Quelle: Deutscher Wetterdienst` mandatory under GeoNutzV, and § 7.2 requires the distance to be
   carried and visibly labelled above 50 km. `BlockCResult` has no field for any of it, while
   `BlockD2Result` does carry `attribution_de` — the asymmetry is the tell.
4. **Block A cannot carry the § 5 provisional label.** § 5 places
   `provisorisch, Endwert erst zur Jahresabrechnung` on Block A's HKV branch. The engine splits that
   into `evaluate_hkv_provisional`, which is defensible, but `BlockAResult` has no `label_de`, so a
   caller composing the two has no typed obligation to carry the label onto the figure it prints.
5. **Blocked results still carry renter-facing labels.** `evaluate_hkv_provisional` returns
   `label_de=None` on two blocked branches (`evaluators.py:325-339`) and `label_de=_HKV_LABEL` on
   the other two (`evaluators.py:344-358`). The blocked D2 branch (`evaluators.py:289-301`) returns
   `basis_de`, `label_de` and `attribution_de` populated under a suppressed comparison.

This runs **before U2** so the Heizspiegel resolver is written against a settled input type instead
of being rewritten once U1b lands.

## Lanes and mechanics

Two lanes. No build-file scaffolding: `packages/uvi-engine` and `packages/domain` are both already
workspace members, already in `[tool.mypy] files`, already in `testpaths` and already in the fast
gate's pure list at `scripts/gate.sh:85-89`.

**Step 1 — `spec-scribe`** extends `packages/uvi-engine/tests/test_page_uvi_u1_golden.py` and adds
`packages/domain/tests/` coverage for the new value objects. **Every existing assertion and every
existing golden number stays exactly as it is.** This slice changes result *shape*, never result
*arithmetic*. Then open the red window: write `.lokara-red` with one line naming the slice and
reason, e.g. `slice/u1b-uvi-provenance · docs/16 provenance fixtures land before the fields`. It is
untracked and gitignored; `fast` announces it, `full` and `demo` treat it as a hard failure; fewer
than 10 characters is rejected as an anonymous off switch.

**Step 2 — `engine-implementer`** writes `packages/domain/src/lokara_domain/provenance.py` and
extends `packages/uvi-engine/src/lokara_uvi_engine/{models,evaluators}.py` until green, then deletes
the sentinel. It may not touch the tests.

## What to build

**`lokara_domain.provenance`** — one home, not a second definition. Mirror the guard engine's field
names exactly so the two can be consolidated later without a third spelling:

| Type | Fields |
| --- | --- |
| `SourceIdentity` | `source_type`, `source_id` |
| `RuleEvidence` | `source`, `register_row`, `legal_basis`, `rechtsstand`, `verification_status` |
| `RuleConflict` | `code`, `description`, `production_blocking`, `applies_to_media` |

Frozen `slots=True` dataclasses, no imports beyond the standard library. Leave
`packages/guard-engine` **untouched**: it is merged and statement-reviewed, and adopting the shared
types there is a separate cleanup recorded in `PLAN.md`, not part of this slice.

**`packages/uvi-engine`** — every evaluator takes a caller-supplied bundle carrying
`evidence: tuple[RuleEvidence, ...]` and `unresolved_conflicts: tuple[RuleConflict, ...]`, and every
result returns the evidence it used, exactly as `GuardResult.rule_evidence` does. Then, per block:

| Type | Change |
| --- | --- |
| `BlockAResult` | add `label_de: str \| None` so the § 5 provisional label rides on the Block A figure |
| `BlockCInput` | add the degree-day provenance the § 7.2 convention produces: station id, distance in km, dataset attribution, as-of |
| `BlockCResult` | return `attribution_de`, `station_id`, `distance_km` and a boolean for the over-50 km case |
| `BlockD2Input` | the warm-water deduction arrives inside a resolved-row bundle carrying its evidence, not as a bare `Decimal` |
| `BlockD2Result` | return the size class actually used, an optional caller-supplied `fallback_label_de`, and the bundle's evidence |
| every blocked result | no renter-facing label. `basis_de`, `label_de` and `attribution_de` become `str \| None` where they are not already, and are `None` when `status` is `blocked` |

## Must not do

- **Do not change a single number.** Every golden value in `UVI_EXAMPLES` and every existing
  assertion stays. If a number moves, the slice is wrong — stop and ask.
- **Do not invent German wording.** Four texts are missing from `docs/16` and are asked in
  `FRAGEN-an-Berkay-05.md`: the over-500 label's trailing full stop, the zero-denominator
  suppression texts for Blocks C, D and D2, the interpolation notice, and a neutral alternative to
  `liegt im ersten Bezugsjahr noch nicht vor`. The 50 km label has no prescribed wording either.
  Until Berkay answers, the engine carries a **flag or a caller-supplied string**, never a phrase
  Lokara wrote.
- **Do not import `lokara_guard_engine` or `lokara_rules_store` into the engine.**
  `scripts/check_engine_purity.py` forbids both, and that boundary is the point. Shared shapes go to
  `lokara_domain`.
- Do not select the Heizspiegel row or resolve a vintage. That is U2.
- Do not implement station assignment or read a DWD file. That is U3, and the PLZ geodataset is
  still unchosen.
- Do not pull the heat-pump `8 kWh/(m²·a)` deduction to `geprüft`. Carrying its
  `verification_status` is exactly the opposite of confirming it.
- Do not edit `berkay-work/`. The CSV stays at 180 rows.
- Do not stage `Antwort-an-Emir_04.md`. Never `git add -A`.
- Do not run `scripts/verify_demo_path.sh --fresh`; U1b needs no schema and it destroys local
  Postgres.

## Acceptance and stop condition

```bash
uv run pytest packages/uvi-engine/tests packages/domain/tests -q
scripts/gate.sh full
```

The full gate must run with `.lokara-red` deleted; it is fatal there by design. Stop when the gate
is green and `git status` shows only `packages/domain/`, `packages/uvi-engine/` and the untracked
`Antwort-an-Emir_04.md`.

**Then show Emir the diff and wait. Do not commit.** Per `AGENTS.md` § 4, an agent past roughly
40 turns without its deliverable stops and reports what it has rather than spending further.

## After U1b

`PLAN.md` § U carries the full order: U2 the Heizspiegel rules data, U3 the DWD adapters, U4 the
schema and RLS, U5 the renter document. Two items are not agent work and gate the milestone
regardless of code: Emir chooses the PLZ geodataset, and Berkay supplies the three missing UVI
register rows and the four missing texts.

---

## Database state

Unchanged: development matches migration `0021` and Alembic is at `0021`. G1, U0, U1, U1b and U2
require no schema change; U4 does. Do not reset the Docker volume. The validated backup remains at
`/tmp/lokara-m6c3a-pre-migration-20260824.dump`.

## Evidence

For U1 as merged, `scripts/gate.sh full` is green, including 84 web tests, and `fast` is green with
583 pure-package tests, up 17 from U0's 566. Strict mypy and engine purity are clean.
`uv run pytest packages/uvi-engine/tests -q` passes 17 tests. No rendered output changed, so the
normalized PDF fingerprint stays `88eb8434eda65f8d7ff82826fc837a58` at 149269 bytes.

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
  after U1b puts the shared shapes in `lokara_domain`. Consolidating them is a later cleanup; it
  would churn a merged, statement-reviewed slice for no behavioural gain.
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
