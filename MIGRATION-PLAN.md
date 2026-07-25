# Lokara — Code Migration Plan (v4 stack)

> **Scope:** turn the current **TypeScript** scaffold (NestJS + Prisma + pnpm/Turbo) into the **v4
> target** the docs now describe: **FastAPI (Python) backend + Python engines**, **Supabase Postgres**
> (kept) via **SQLAlchemy + Alembic**, a **Bun + Turborepo** TS workspace for web + mobile, **shadcn/ui**,
> plus Redis, RevenueCat, Locust.
> This is a **plan, not code**. Pair it with `CLAUDE.md`, `PLAN.md`, and `lokara-arch.md`.

---

## 0. Timing & risk (read first)

- **Pitch day is 6 August.**
- **What's built:** only **M0** (foundations/scaffolding) — on the **interim TS stack** (NestJS +
  Prisma). M1→M3 (NK engine, heating/CO₂, web slice + PDF) are **not built yet**.
- **Chosen path:** **migrate M0 to Python now** (Phases A–F), **then build M1→M3 in Python** — Phase C
  is where M1/M2 get built. The crown-jewel engines are unbuilt, so this builds them once and the pitch
  runs on the target stack.
- **Sequencing to the pitch:** Phases A–B (toolchain + DB) → **Phase C = M1 + M2 engines** → Phase E
  (API) → Phase F + the M3 pages = the pitch demo. Phases G/H (mobile, cutover cleanup) come after.
- **Honest risk:** with M1→M3 built only in Python, the pitch now **depends on this path reaching M3**.
  The TS M0 stays on `main` as a safety net, but it's M0-only — not a full demo. Mitigation: do Phase C
  first and gate on the €1,200 fixture; if the plumbing (A/B/E) snags badly, the escape hatch is to add
  the engines to the TS M0 for the pitch instead.
- **The codebase is small** (~1,800 LOC; engines are 30–150 lines each), so the rebuild is limited in scope.

---

## 0a. Current status (as of 2026-07-25)

Branch: **`feat/py-migration`**. `main` is untouched at `c5fadab` (tag `pre-migration`) and stays
demo-able. Phase details are in the per-phase blockquotes in §4.

**Phases:** ✅ **A** (toolchain) · ✅ **B** (DB + RLS) · ✅ **C** (engines ⭐) · ✅ **D**
(adapters + PDF) · ✅ **E** (FastAPI) · ✅ **F** (web) — remaining: **G** (mobile) · **H** (cutover).
C ran before B and E/F before D, per §7 — none depended on the phase it jumped.

**Verified gates**

- **The €1,200 fixture is byte-exact in pytest** (`packages/nk-engine/tests`):
  `60000 / 17852 / 18148 / 24000` cents (€600.00 · €178.52 · €181.48 → landlord · €240.00),
  Σ = `120000` = €1,200.00. Every allocation test also asserts `sum(shares) == input_total`.
- **The RLS cross-account read is blocked** (`packages/db/tests/test_rls_isolation.py`): the suite
  connects as the **non-owner `lokara_app`** role (asserted: not `rolsuper`, not `rolbypassrls`),
  seeds two accounts, and proves account A's context returns **empty** for B's rows, that **no
  context at all** returns empty (deny by default), and that cross-account **writes/updates** are
  rejected. **Mutation-checked:** disabling RLS on one table makes the test fail; re-enabling
  restores green. CI's Python lane runs it against a Postgres service with `LOKARA_REQUIRE_DB=1`,
  so it cannot silently skip.
- Full suite: **114 pytest tests** (10 need the local Postgres; 1 needs Playwright Chromium),
  `mypy --strict` clean, `ruff check .` clean, Turbo `typecheck`/`lint`/`test`/`build` green.

**What works end-to-end today**

- **FastAPI** (`apps/api`): HS256 JWT auth accepted from **either** a `Bearer` header or the
  HttpOnly `lokara_access_token` cookie · dev-token endpoint gated by `AUTH_DEV_TOKEN` ·
  **`account_session`** = live-`Membership` check **+** RLS context in one dependency (403 without
  a membership) · **`POST /calc/nk`** returns the €1,200 fixture's cents over HTTP ·
  **`GET /demo/summary`** serves the seeded demo building.
- **Web** (`apps/web` on Bun + Next.js): shadcn-style kit in `packages/ui` themed to the docs/05
  tokens; TanStack Query + Jotai + RHF/Zod wired; the **`api.ts` interceptor** Zod-parses responses
  and, on a 401, refreshes once via the `/api/session` route handler (which sets the HttpOnly
  cookie server-side) and replays once — concurrent 401s share a single refresh. Verified headless:
  `401 → POST /api/session → replay 200` renders live API data.
- **Adapters + PDF** (`packages/adapters`, `packages/pdf`): six external-edge `Protocol` ports with
  fixture stubs, and `uv run lokara-pdf-demo` renders the real NK + heating/CO₂ statement (engine
  results, `Rechtsstand` stamps, disclaimer) via Playwright Chromium.

**Next step:** the migration itself has only **G** (Expo mobile skeleton) and **H** (cutover:
remove the TS backend, merge to `main`) left — but the pitch path (§0) now runs through the
**M3 pages** (docs/04): the six Vermieter-portal screens on the live API, ending in the PDF
that `packages/pdf` already renders.

**Known open items**

- **No semantic status colors** — the brand board has no red/amber/green, so shadcn's `destructive`
  variant ships omitted. `TODO(M3)`: add `danger`/`warning`/`success` tokens (docs/05).
- **`TODO(supabase)`** touchpoints: no Supabase project is wired — docker-compose Postgres and the
  dev-token endpoint stand in; the real session exchange lands at M5 (check HS256 vs JWKS then).
- **The M3 pages are not built** (`docs/04`): Dashboard, Objekte, Einheit, Kosten erfassen, Zähler,
  Abrechnung erstellen. Phase F shipped the stack + a demo page, not the product screens.
- TS backend (NestJS/Prisma) still coexists as reference; it comes out at Phase H.

**How to run it**

```bash
export PATH="$HOME/.bun/bin:$PATH"      # Homebrew's bun 1.1 shadows ~/.bun/bin (needs ≥ 1.3)
docker compose up -d                    # Postgres on :54322 (container lokara-db)
uv sync && bun install
uv run alembic -c packages/db/alembic.ini upgrade head
uv run lokara-seed-demo                 # demo account/building/renters + the OWNER membership
uv run lokara-api                       # FastAPI on 127.0.0.1:3001
bun run --filter @lokara/web dev        # web on :3000
uv run lokara-pdf-demo                  # NK+heating statement → packages/pdf/output/
```

> ⚠️ Use the **filtered** web command, not bare `bun dev` — `turbo run dev` still starts the **old
> NestJS `apps/api`** on **:3001**, which collides with `uv run lokara-api`. Resolved at Phase H when
> the TS backend comes out.

Gates: `uv run pytest` · `uv run mypy` · `uv run ruff check .` · `bun run test` ·
`bun run typecheck` · `bun run lint` · `bun run build`.

---

## 1. Fresh start vs migrate — the decision you asked about

**Recommendation: a *targeted rebuild*, not a full nuke. Don't delete everything.**

Split the repo into two halves and treat them differently:

| Part | Verdict | Why |
| --- | --- | --- |
| **Backend + engines + db** (`apps/api`, `packages/{nk-engine,heating-engine,domain,adapters,rules-store,db,pdf}`) | **Rebuild fresh in Python** | The language is changing (TS→Python), so "converting" line-by-line buys nothing — you're re-implementing anyway. A clean Python scaffold avoids carrying TS-shaped decisions across. Keep the old TS code as **read-only reference** and the **golden fixtures as the spec** until the Python versions pass. |
| **Web frontend** (`apps/web`, design tokens, PDF templates) | **Keep and evolve** | Next.js stays. Deleting it gains nothing and throws away the working design-token wiring + statement template. Just move it to Bun, add shadcn + Jotai/TanStack/RHF/Zod. |
| **Mobile** (`apps/mobile`) | **New** | Didn't exist; scaffold fresh (Expo). |

So "delete all the code" is the wrong frame. **"Delete and re-do the backend fresh; keep and upgrade
the frontend"** is the right one — and it's essentially Phases C–F below.

- **Why not a full clean slate?** You'd re-scaffold a working Next.js app + re-derive the brand tokens
  and PDF layout for no gain. The value in `apps/web` is real; the value in the TS *backend* is only
  its fixtures (which you keep as the test spec anyway).
- **Why not a pure incremental "port"?** Because a TS→Python line-by-line port is slower and messier
  than re-implementing 30–150-line engines from a fixture spec. For the backend, fresh *is* the fast path.

---

## 2. Guiding principles

1. **The €1,200 golden fixture is the gate.** Port it to **pytest** first; nothing merges until it
   passes byte-for-byte in Python. Correctness is the product.
2. **Rebuild in a branch (`feat/py-migration`)**; keep `main` demo-able until parity is proven.
3. **Engines + DB first, framework last.** The pure math and the schema carry the value.
4. **Delete old backend only after parity** — FastAPI + SQLAlchemy pass the same tests and render the
   same PDF before NestJS/Prisma come out.
5. **One green build per phase.** Never a half-migrated `main`.

---

## 3. Old → new mapping

| Current (TS)                     | Target (v4)                          | Approach                                                     |
| -------------------------------- | ------------------------------------ | ----------------------------------------------------------- |
| `apps/api` (NestJS)              | `apps/api` (**FastAPI**, Python)     | Fresh. Routers per domain; auth + RLS as dependencies.      |
| `packages/db` (Prisma)           | `packages/db` (**SQLAlchemy 2.0 + Alembic**) | Fresh models from docs/02; port RLS policies.       |
| `packages/nk-engine` (TS)        | `packages/nk-engine` (**Python**)    | Re-implement from fixtures; `decimal.Decimal` + int cents.  |
| `packages/heating-engine` (TS)   | `packages/heating-engine` (**Python**) | Re-implement; §§7/8, §9, §9a, CO₂ 10-step.                 |
| `packages/domain` (TS)           | `packages/domain` (**Python**)       | Value objects → dataclasses / Pydantic.                     |
| `packages/adapters` (TS)         | `packages/adapters` (**Python**)     | Ports as `Protocol`; stub impls.                            |
| `packages/rules-store` (TS)      | `packages/rules-store` (**Python**)  | Versioned rules + as-of dates.                              |
| `packages/pdf` (TS/Playwright)   | `packages/pdf` (**Playwright-Python**) | Same templates.                                           |
| `apps/web` (Next.js, pnpm)       | `apps/web` (Next.js, **Bun**) + shadcn + Jotai/TanStack/RHF/Zod | **Keep & evolve.**             |
| `packages/ui` (custom)           | `ui/` (**shadcn**, themed to tokens) | Overwrite defaults with brand tokens.                       |
| — (none)                         | `apps/mobile` (**Expo**)             | New skeleton.                                               |
| pnpm + Turbo · Vitest            | **Bun + Turbo** (TS) + **uv** (Python) · **pytest** + Vitest | Two workspaces, one repo.            |

---

## 3a. M0 decisions to preserve in the migration

These were settled while building the TS M0 (they weren't in the original docs — now they are, in the
files noted). **Carry them across; don't re-derive or lose them.**

- [ ] **DB layer in `packages/db`, imported by `apps/api` only** — SQLAlchemy models + Alembic here;
      no client app touches the DB. *(Phase B · docs/04)*
- [ ] **Non-owner app role for runtime** — owner/superuser **bypasses RLS**. Request traffic uses a
      restricted role (`lokara_app`); migrations may run as owner. `DATABASE_URL` (app) vs `DIRECT_URL`
      (migrations). **Verify a cross-account read fails as the app role.** *(Phase B · docs/02)*
- [ ] **`TenancyParty` join present from M0** — Renter↔Tenancy is a join entity (multi-party leases),
      not a direct FK; `account_id`-scoped; unique `(tenancy_id, renter_id)`. *(Phase B · docs/02)*
- [ ] **Statement versioning encoding** — `version` + `DRAFT/FINALIZED/SUPERSEDED` status + unique
      `(building, period, version)`; a correction inserts version n+1 and marks the prior SUPERSEDED;
      **never UPDATE a FINALIZED row.** *(Phase B/C · docs/02)*
- [ ] **Local auth** — auth dependency verifies **HS256** vs `SUPABASE_JWT_SECRET`; dev-only
      `POST /auth/dev-token` gated by `AUTH_DEV_TOKEN=true` (never prod); `TODO(supabase)` at every
      touchpoint. When wiring real Supabase, check HS256 vs asymmetric JWKS. *(Phase E · docs/01 D2)*
- [ ] **Tailwind v4 `@theme`** — CSS-first tokens (not `tailwind.config` `theme.extend`); shadcn
      variables read from them. *(Phase F · docs/05)*

## 4. Phased plan (each phase ends green)

### Phase A — Branch & toolchain — ✅ done
- Branch `feat/py-migration`; the v4 doc edits were committed as its first commit (they were uncommitted).
- **uv** workspace (root `pyproject.toml`) with an **explicit member list** (`apps/api` + the Python
  `packages/*`), **not** a `packages/*` glob — so the TS `packages/ui` is excluded. **Python 3.13**
  pinned via `.python-version`. Ruff + mypy + pytest config.
- **Bun** ≥ 1.3 for the TS side (`apps/web`, `apps/mobile`, `packages/ui`) + Turbo; pnpm scripts migrated.
  Note: a stale Homebrew `bun` can shadow `~/.bun/bin/bun` — prepend it on PATH.
- CI runs both lanes: `bun install && bun run test` (Turbo → Vitest, **not** Bun's native runner) ·
  `uv sync && pytest`.
- **Coexistence:** Python skeletons are built **in place** beside the TS packages; TS stays as reference
  until each phase reaches parity, removed at Phase H.
- **DoD:** both installs succeed; CI green on both lanes.

### Phase B — DB: Prisma → SQLAlchemy + Alembic — ✅ done
> Built 2026-07-24 on `feat/py-migration` (after Phase C, per §7): 12 SQLAlchemy 2.0 models
> (identity three-layer + temporal core + SelfUsePeriod), Alembic migration `0001` with FORCEd RLS
> on all 11 tenant tables (USING + WITH CHECK; snake_case tables coexist with the Prisma ones until
> Phase H). **The cross-account isolation test passes as the non-owner `lokara_app` role** and was
> mutation-checked (disabling RLS makes it fail). CI's Python lane now runs it against a Postgres
> service with `LOKARA_REQUIRE_DB=1`, so the gate can't silently skip. Validity columns are
> day-granular `DATE` (matches the engines' `Period`); docs/02's sketch says datetime — deliberate.
- `packages/db`: SQLAlchemy 2.0 models from `docs/02` (identity + temporal core + SelfUsePeriod + enums).
- `alembic init`; first migration = temporal core; **port RLS policies** into Alembic `op.execute` SQL.
- Local docker-compose Postgres fallback; config via `pydantic-settings`.
- **DoD:** `alembic upgrade head` clean; a cross-account read **fails** (RLS) in a test.

### Phase C — Engines + rules-store + domain ⭐ — ✅ done (done before Phase B, per §7)
> Built 2026-07-24 on `feat/py-migration`: 67 pytest tests green, €1,200 fixture byte-exact
> (60000/17852/18148/24000), mypy --strict clean, engines import only stdlib + `lokara-domain`.
> Rule-value shapes live in `domain` (engines depend only on domain); Anlage-V lines deferred to M7.
> Degree-day promille table is marked verify-before-production.
- Port `domain` (dataclasses/Pydantic), `rules-store` (HKVO, CO₂ 10-step, Anlage-V lines + as-of dates).
- `nk-engine`: day-weighted allocation, all keys incl. DIRECT/MEA, vacancy→landlord, largest-remainder
  rounding with `decimal.Decimal`.
- `heating-engine`: §§7/8 split, §9 WW, §9a estimation, degree-days, CO₂ split.
- **Port fixtures to pytest first**, incl. the **€1,200 example** → must reconcile to €1,200.00.
- **DoD:** `pytest` green; €1,200 fixture byte-exact; `mypy --strict` clean; no framework/DB/vendor imports.

### Phase D — Adapters + PDF — ✅ done
> Built 2026-07-25 on `feat/py-migration`. **Adapters:** six ports as Python `Protocol`s with
> fixture stubs — Bank (AIS; § 11 EStG booking date), Vision/OCR (canned M4 Beleg flow), Email
> (immutable receipts for the Zustell-Ampel), Meter/MDL (one normalized `MeterReading` for
> manual/HeiWaKo/radio; register diffs reproduce the heating fixture), Destatis (VPI), DATEV
> (transport only — EXTF generation stays in the pure export-engine, M7). Stubs are consumed
> through their Protocol types in tests, so mypy strict enforces conformance; the flow test runs
> the vision stub's extraction through the NK engine and reproduces the €1,200 allocation
> byte-exact. **PDF:** `packages/pdf` renders the first real Betriebs-/Heizkostenabrechnung via
> Playwright-Python Chromium (`uv run lokara-pdf-demo`): rules resolved from the rules-store
> as-of the billing date, both engines on the canonical fixtures with one coherent occupancy
> timeline (B's vacancy → landlord in both sections, consumption degree-day-apportioned 585/415 ‰),
> Bemessung at human scale (18.250 m²·Tage), CO₂ block, `Rechtsstand` stamps + the
> "keine Rechts- oder Steuerberatung" disclaimer. Template content is golden-tested without a
> browser; CI installs Chromium and sets `LOKARA_REQUIRE_PDF=1` so the render test can't silently
> skip (mutation-checked: skip without the flag, fail with it, pass with the browser).
- `adapters`: ports as `Protocol` (Bank/Vision/Email/MDL/Destatis/DATEV) + fixture stubs.
- `pdf`: Playwright-for-Python HTML→PDF; NK/heating template with `Rechtsstand` + disclaimer.
- **DoD:** a stub txn flows through an adapter; a placeholder PDF renders.

### Phase E — FastAPI backend — ✅ done
> Built 2026-07-24 on `feat/py-migration` (before Phase D — the API needed no adapters/PDF):
> `uv run lokara-api` serves; **a JWT-auth'd `POST /calc/nk` returns the €1,200 fixture byte-exact
> over HTTP** (60000/17852/18148/24000). HS256 auth dependency + dev-token (AUTH_DEV_TOKEN-gated,
> `TODO(supabase)` markers), `account_session` verifies a live Membership under the RLS context
> (403 without), guarded `/demo/summary` keeps the TS camelCase contract; demo seed ported to the
> snake_case schema incl. the OWNER membership (`uv run lokara-seed-demo`). DB routes are sync
> `def` (threadpool) so the blocking driver never stalls the event loop — async engine can land
> later without changing the contract.
- `apps/api`: FastAPI, per-domain routers; **auth dependency** verifies Supabase JWT, sets RLS context,
  yields a scoped session; Pydantic at every boundary; async discipline (no blocking calls in async).
- **DoD:** `uv run` serves the API; a JWT-auth’d NK request returns the fixture's numbers.

### Phase F — Web on Bun + shadcn + data stack — ✅ done
> Built 2026-07-24 on `feat/py-migration` (before Phase D). shadcn-style kit in `packages/ui`
> (Button/Card/Table on cva + Radix Slot; shadcn variables mapped to brand tokens per docs/05,
> Tailwind v4 `@theme` — default palette never ships; no destructive variant until the brand board
> gets a semantic red). `apps/web`: TanStack Query + Jotai + RHF/Zod; **`api.ts` interceptor** with
> HttpOnly-cookie session (`/api/session` Next route mints it from the dev-token endpoint,
> TODO(supabase) at M5), Zod-parsed responses, 401 → refresh once → replay once, concurrent 401s
> share one in-flight refresh — 7 vitest tests pin that. FastAPI additionally accepts the JWT from
> the `lokara_access_token` cookie (same verification as Bearer). **DoD verified headless:** the
> demo page 401s, mints the cookie, replays, and renders the seeded Musterstraße-12 data live.
- Move `apps/web` to Bun; init shadcn in `ui/` themed to brand tokens (overwrite defaults as needed).
- Add TanStack Query + Jotai + RHF/Zod; shared **`api.ts` interceptor** (cookie JWT; 401 → refresh once
  → replay, no double-fire); feature-based folders.
- **DoD:** `bun dev` runs; demo page reads live data from FastAPI via the interceptor.

### Phase G — Mobile skeleton (optional pre-launch)
- `apps/mobile` (Expo): same Jotai/TanStack/RHF/Zod, `react-native-ease`, secure storage + Bearer JWT,
  i18n + theme; consume the same FastAPI.
- **DoD:** Expo app logs in and reads one screen.

### Phase H — Cutover & cleanup
- Confirm parity (pytest green, PDF identical, web/(mobile) on FastAPI).
- **Remove** NestJS `apps/api` + Prisma `packages/db`. Pre-commit + CI: Ruff/mypy/pytest +
  ESLint/Prettier/Husky; React Compiler on; React Scan + Expo profiling.
- Merge → `main`; remove the migration-status banners from the docs.
- **DoD:** clean `main` green on both lanes; no NestJS/Prisma left; docs and code agree.

### Later (M6+)
- Redis (cache + rate-limit) + Celery/Arq workers; Stripe (web) + RevenueCat (mobile) behind an adapter;
  Locust load test (~100 users) before launch.

---

## 5. Scenario tree

- **Base case (chosen):** migrate M0 to Python now on a branch, build M1→M3 in Python for the pitch.
  *Confirms:* €1,200 fixture green in Python + M3 demo by 6 August. *Escape hatch:* if plumbing snags,
  add the engines to the TS M0 for the pitch.
- **Bull case:** engines port quickly, mobile skeleton lands in the same pass, cutover before the pitch.
  *Confirms:* Phase C done with no rounding drift.
- **Bear case:** RLS porting or Bun/Next-Expo friction. *Invalidates "cheap".* → keep TS build for the
  pitch; land RLS as raw SQL with an explicit isolation test; per-command Node fallback for Bun.

## 6. Top risks & mitigations

- **Rounding drift TS→Python** (`decimal.js` vs `decimal.Decimal`). → fixtures first; cent-exact assert;
  one fixture per allocation key.
- **RLS regression** — the easiest silent multi-tenant leak. → migrate policies explicitly; a
  cross-account read must fail a test before cutover.
- **Betting the pitch on the rebuild.** → don't; TS build is the fallback until Python is green.
- **Bun rough edges with Next/Expo.** → per-command Node fallback; don't re-platform over one tool.

## 7. Highest-leverage next action

**Start now:** branch `feat/py-migration`, do Phases A–B (toolchain + DB), then **Phase C — the engines
+ the €1,200 pytest fixture — and gate on it.** The engines are the riskiest and highest-value part, so
front-load them; once the numbers reconcile in Python, M3 and the rest are plumbing.

## 8. Driving Claude Code (one phase per session)

- **One phase per session.** End each with "stop and summarize, don't start the next phase."
- **Gate the high-risk phases.** Demand the €1,200 pytest output at Phase C; demand the RLS isolation
  test (a cross-account read blocked **as the `lokara_app` role**, plus a mutation check) at Phase B.
  The pitch's credibility is the numbers and the tenant isolation.
- **Reject vendor SDKs in engines/domain.** If it proposes one inside `packages/*-engine` or `domain`,
  that violates the adapter rule in `CLAUDE.md` — vendor code belongs in `adapters` only.
- **Keep it in sequence.** If it jumps ahead (native app, bank, contracts) before its phase/milestone,
  point it back to `PLAN.md` / this file — engines and correctness first.
- **Every new tenant table needs an RLS policy + a line in the isolation test.** A table without a
  policy is a silent leak.

---

## Appendix A — Phase C engine checklist (concrete)

Do these in order. Each fixture is a `pytest` test committed **before** the code that satisfies it.

### A.1 Order of fixtures (write tests first)
1. **€1,200 garbage-cost, key = AREA** (the canonical one, `docs/03`) — mid-year move-out + vacancy.
2. **DIRECT** — a cost assigned to exactly one unit; no spread; other units get €0.00.
3. **PERSONS** with a mid-period person-count change (day-weighted).
4. **CONSUMPTION** from metered readings.
5. **Interim period (<12 months)** and **>12-month period** (domain-depth differentiators).
6. **Heating (M2):** §§7/8 base/consumption split; §9 warm-water separation; **CO₂ 10-step** split with
   `Rechtsstand`; a mid-period renter change apportioned by degree-days.

### A.2 The rounding primitive (get this exactly right — it's the whole game)

Integer cents in, integer cents out; **largest-remainder** so the sum reconciles to the input:

```python
from decimal import Decimal

def largest_remainder(total_cents: int, weights: list[Decimal]) -> list[int]:
    """Split total_cents across weights; sum(result) == total_cents, exactly."""
    wsum = sum(weights)
    if wsum == 0:
        return [0] * len(weights)
    exact  = [Decimal(total_cents) * w / wsum for w in weights]
    floors = [int(x // 1) for x in exact]                 # floor to whole cents
    leftover = total_cents - sum(floors)                   # 0..n-1 cents remain
    # rank by fractional remainder desc; ties broken by original index (stable)
    order = sorted(range(len(exact)),
                   key=lambda i: (exact[i] - floors[i], -i), reverse=True)
    for i in order[:leftover]:
        floors[i] += 1
    assert sum(floors) == total_cents                      # never ships if this fails
    return floors
```

### A.3 Day-weighting rule
- A party's weight = `key_value × days_active_in_period` (e.g. `m² × days` for AREA).
- Any day a unit is **not `RENTED`** and not billable to a renter → its weight goes to the
  **landlord bucket** (vacancy + self-use). One landlord line collects them.
- Build weights from the temporal rows (`Tenancy.valid_from/valid_to`, `SelfUsePeriod`), never a scalar.

### A.4 Expected values for the €1,200 fixture (assert these)
365-day period, key = AREA:

| Party | m²·days | Cents |
| --- | --- | --- |
| Unit A — Renter 1 (50 m², 365 d) | 18,250 | 60000 |
| Unit B — Renter 2 (30 m², 181 d) | 5,430 | 17852 |
| Unit B — VACANT → landlord (30 m², 184 d) | 5,520 | 18148 |
| Unit C — Renter 3 (20 m², 365 d) | 7,300 | 24000 |
| **Total** | 36,500 | **120000** |

### A.5 Phase C Definition of Done
- `pytest` green; **€1,200 fixture byte-exact** (cents match the table above).
- `sum(shares) == input_total` asserted in every allocation test.
- `mypy --strict` clean; money is `int` cents + `decimal.Decimal`, **never `float`**.
- **No** import of a web framework, DB, or vendor SDK anywhere under `packages/*-engine`.

---

## Appendix B — Phase B RLS migration (concrete)

Postgres RLS is the isolation backstop. The pattern: a per-request session variable holds the caller's
`account_id`; every policy checks it.

### B.1 Enable RLS + policy per tenant table (Alembic `op.execute`)

```python
# migrations/versions/xxxx_rls.py
def upgrade():
    for table in ("account", "membership", "landlord", "renter", "building", "unit", "tenancy",
                  "self_use_period", "building_assignment"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")

    # account row itself is scoped by its own id; all others by their account_id column
    op.execute("""
        CREATE POLICY account_isolation ON account
        USING (id = current_setting('app.account_id', true));
    """)
    for table in ("membership", "landlord", "renter", "building", "unit", "tenancy",
                  "self_use_period"):
        op.execute(f"""
            CREATE POLICY {table}_isolation ON {table}
            USING (account_id = current_setting('app.account_id', true));
        """)
    # building_assignment has no account_id → scope via its membership
    op.execute("""
        CREATE POLICY building_assignment_isolation ON building_assignment
        USING (EXISTS (SELECT 1 FROM membership m
                       WHERE m.id = building_assignment.membership_id
                         AND m.account_id = current_setting('app.account_id', true)));
    """)
```

> `current_setting('app.account_id', true)` — the `true` = "don't error if unset" (returns NULL, which
> matches nothing → deny by default). Use the DB **app role**, not the Postgres superuser/owner, at
> runtime — owners bypass RLS.

### B.2 Set the context per request (FastAPI dependency)

```python
async def scoped_session(claims = Depends(verify_supabase_jwt)) -> AsyncSession:
    account_id = resolve_account_for_caller(claims)      # from the URL /a/{accountId}, re-checked
    async with SessionLocal() as session:
        # SET LOCAL lives only for this transaction — no leakage across requests
        await session.execute(text("SELECT set_config('app.account_id', :aid, true)"),
                              {"aid": account_id})
        yield session
```

The URL carries the context (`/a/{accountId}/…`); the dependency independently verifies the caller holds
that relationship **before** setting the GUC — the menu is navigation, not authorization.

### B.3 Isolation test (must fail the leak, before cutover)

```python
async def test_rls_blocks_cross_account(session_factory):
    # seed Account A with a building; Account B empty
    await set_context(session, account_id="B")
    rows = (await session.execute(select(Building))).scalars().all()
    assert rows == []          # B must NOT see A's building — this is the whole ballgame
```

### B.4 Phase B Definition of Done
- `alembic upgrade head` clean; RLS + `FORCE ROW LEVEL SECURITY` on every tenant table.
- Runtime connects as a **non-owner** app role.
- The cross-account isolation test passes (i.e. the leak is blocked) — **no cutover without this**.
