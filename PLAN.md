# PLAN.md — Lokara Web App roadmap (milestones)

> Build **iteratively**. Each milestone has a Definition of Done (DoD). Do not start a milestone
> before the previous one's DoD is met. **Engines + golden fixtures always come before UI.**
> Canonical dates from `lokara-arch.md`: pitch **06.08**, public launch **~08.09** (web + native
> iOS/Android together). (Earlier freeze/web-only dates of 23.07/25.07 are now historical.)
>
> **Status: M0–M4 are built and green** on the v4 Python stack (FastAPI + SQLAlchemy/RLS + Bun/shadcn).
> The migration is complete except **Phase G** (Expo skeleton): Phase H removed the pre-migration
> TypeScript, so there is now one backend and it is Python — see `MIGRATION-PLAN.md`.

## Pitch plan (target: 06.08) — push for maximum breadth

**Decision:** attempt **M4 → M10** before the pitch, ordered by investor value ÷ risk, with
**Berkay's calculation specs written in parallel** so the spec-dependent milestones aren't guesswork.
Stubs stay stubbed where APIs cost money (finAPI, Vision/OCR, email, billing).

> ⚠️ **Read this before starting anything below.** This is a deliberately ambitious run. Most of
> M6–M10 is normally months of work. The plan is therefore written to **degrade gracefully**: value
> lands first, everything spec-dependent is gated, and there is an explicit cut list. **A working demo
> beats a broader broken one — every time.**

### Execution order (not milestone order)

Build in this sequence, because it front-loads what an investor reacts to:

| # | Work | Why here | Risk |
| --- | --- | --- | --- |
| 1 | **M4** canned doc-extraction | Vision stub already exists (Phase D); mostly review UI. The "AI-assisted UX" pillar. | low |
| 1.5 | **FK-Isolation slice**: composite FKs on `(id, account_id)` | One migration across most tables. Inside M5 (identity + roles + portals + RLS at once) a failure would be impossible to attribute — and this work needs nothing from M5. | medium |
| 2 | **M5a** identity schema + isolation (`person` RLS, `landlord`/`self_use_period` coverage, roles/shape) | Pure schema + policy. Split out for the same reason as 1.5: mixing a migration with routers and screens makes a failure impossible to attribute. Closes the last 2 `check_rls_coverage.py` problems. | low |
| 2.5 | **M5 remainder** roles in the API, portals, URL-carried context, switcher | Unlocks **persona 4** — one login: Vermieter + Mieter + Investor — your strongest differentiator (`docs/06`). | medium |
| 3 | **M10-slice**: read-only Mieter + StB portals | Completes the persona demo; no tickets/activation yet. | medium |
| 4 | **M9-slice**: §556 deadline Wächter + reminders | Visible, date-driven, needs no new legal math. | medium |
| 5 | **M6** bank + Payment Ledger (finAPI stubbed) | Unlocks the two-time-axes story; adds Redis/workers. | high |
| 6 | **M7** tax export + AfA | 🔒 **gated on specs** — see below. | high |
| 7 | **M8** document/clause engine | 🔒 **gated on specs**. | high |
| 8 | **M10 remainder**: tickets, activation codes, investment cockpit | Broad surface, lower per-hour demo value. | high |
| 9 | **Phase G** native/Expo | Largest surface, least pitch payoff — "at launch" is a fine answer. | highest |

*The FK slice is numbered **1.5**, and M5's split reuses row 2 + a new **2.5**, deliberately: the cut
list below refers to these indices, so renumbering 3–9 would silently repoint it. Milestone
identifiers (M4, M5, …) never move — M5a is a slice of M5, not a new milestone.*

### Hard rules for this run

1. **🔒 No calculation without its spec.** M7/M8 (AfA rates, Anlage-V lines, DATEV encoding, clause
   versions) must not start until Berkay's page exists, is transcribed into `docs/`, and its worked
   example is a golden fixture. Guessing German tax law is the one failure this product cannot absorb.
   If a spec isn't ready, **build the adapter/stub and move on** — never invent the numbers.
2. **The demo path is sacred.** Every milestone ends with the full path re-verified end to end
   (clean DB → seed → statement → PDF). If a change breaks it, fix or revert before moving on.
3. **Tag every green state** (`git tag demo-green-<n>`). At any moment you must be able to check out a
   tag and demo. This is the whole safety net.
4. **One milestone per session**, each ending green (tests + CI). No half-merged subsystems.
5. **Stubs stay stubs.** finAPI, Vision, email, billing behind adapters — no vendor SDK, no real keys.

### Cut list (drop in this order if time runs short)

**9 → 8 → 7 → 6 → 4.** Cut early and deliberately rather than shipping something half-built: an
honest roadmap slide beats a broken screen. M5 and the persona story are the last things to give up —
they carry the differentiator.

### Stop-building checkpoint

**Two days before the pitch, stop feature work.** Merge to `main`, rehearse from `DEMO-RUNBOOK.md` on
a clean checkout, and fix only what the rehearsal breaks. Nothing new goes in after that line.

---

## M0 — Foundations & scaffolding — ✅ done (Python stack)

> **What exists today:** M0 stands on the v4 Python stack — FastAPI + SQLAlchemy/Alembic + Bun/shadcn
> — re-established by `MIGRATION-PLAN.md` Phases A–F. The interim TypeScript build (NestJS + Prisma)
> that originally satisfied M0 was removed in Phase H, which is now merged to `main`. It survives only
> at the **`pre-migration`** tag (`c5fadab`) — that tag, not a branch, is the historical fallback.
> `apps/mobile` (Expo) is the one part of the spec below that is still outstanding — Phase G.

**Goal:** an empty but correct skeleton everything else hangs off.

- Polyglot monorepo: **Bun + Turborepo** (TS) + **uv** (Python). **`apps/web` (Next.js) +
  `apps/mobile` (Expo, skeleton) + `apps/api` (FastAPI)** + `packages/*` layout
  (see `docs/04-web-app-structure.md`).
- TS `strict` + ESLint/Prettier/Husky + Vitest; Python **Ruff + mypy strict + pytest**; Turbo pipelines; CI.
- Tailwind wired to the **design tokens** from `docs/05-design-system.md` (colors, Montserrat/Manrope);
  **shadcn/ui** initialized and themed to the tokens.
- Supabase project (EU/Frankfurt) provisioned; **SQLAlchemy + Alembic initialized inside `apps/api`**
  against Supabase Postgres. `apps/web` / `apps/mobile` call the API over HTTP and never touch the DB.
- **FastAPI skeleton**: a Supabase-JWT auth **dependency** + RLS-context, one health endpoint, and a
  typed HTTP client (with the shared `api.ts` auth/refresh interceptor) in `apps/web`.
  (No workers/webhooks yet — those arrive at M6.)
- **Temporal core schema** migrated (Alembic): `Building → Unit → Tenancy` with `validFrom/validTo`,
  integer-cents money, immutable-statement pattern. (Identity layer stubbed; full RBAC is M5.)
- PDF service skeleton (headless Chrome / **Playwright for Python**) that renders a "hello" statement.

**DoD:** `bun dev` runs web (+ mobile) and `uv run` runs the api; the web app reaches the API through
the auth dependency; `bun run test` (Turbo → Vitest) + `pytest` run; one Alembic migration applied; a
trivial PDF renders.

---

## M1 — NK / operating-cost engine (⭐ pitch core) — ✅ built (Python, migration Phase C)

> Built 2026-07-24 in `packages/nk-engine` (`lokara_nk_engine`): the €1,200 fixture passes
> byte-exact; all keys incl. DIRECT/MEA; interim (<12 mo) and 18-month periods covered.

**Goal:** the crown-jewel calculation, provably correct.

- `packages/nk-engine` — **pure**, no framework/DB imports.
- Day-weighted allocation; vacancy → landlord; **largest-remainder rounding** reconciling to the cent.
- All allocation keys incl. **DIRECT** (Direktzuordnung) and **MEA**; keys freely changeable without
  deleting entered data (per-period `AllocationKeyAssignment`, never on the cost row).
- Golden fixtures — the **€1,200 garbage-cost example** (`docs/03-nk-heating-engines.md`) passes exactly.

**DoD:** golden tests green; totals reconcile; changing a key re-runs cleanly and destroys no data.

---

## M2 — Heating + CO₂ engine — ✅ built (Python, migration Phase C)

> Built 2026-07-24 in `packages/heating-engine` (`lokara_heating_engine`): §§7/8 + §9 + §9a +
> degree days + CO₂ 10-step with `Rechtsstand` from the rules store. Golden fixtures green.

- `packages/heating-engine` — pure. §§7/8 HKVO 30/70–50/50 split, §9 warm-water separation,
  §9a estimation, degree-day apportionment on renter change, **CO₂ 10-step model (CO2KostAufG)**
  with Vermieter/Mieter split.
- HKVO ratios + CO₂ 10-step table live in the **versioned rules store**, not in code.

**DoD:** heating + CO₂ golden fixtures pass; a statement shows the landlord/renter CO₂ split with `Rechtsstand`.

---

## M3 — Web-app vertical slice + PDF (⭐ pitch demoable end-to-end) — ✅ done

> **All six pages are built and the fixtures are gone.** Semantic tokens + `StatusNote`; the
> URL-scoped portal (`/a/{accountId}`) with `account_session_for_path` (independent Membership check
> + RLS backstop, cross-account 403 tested); `GET /me`-derived nav; one-click **Demo-Szenario
> laden**; **Objekte** (Building → Unit → Tenancy) and **Einheit** with the occupancy timeline
> (Leerstand and Eigennutzung as labelled segments); **Kosten erfassen** with the key held in
> append-only `AllocationKeyAssignment` rows; **Zähler** with meters, Eichfrist guard and create-only
> readings; **Abrechnung erstellen** → both statements, cent-exact reconciliation, PDF download.
>
> **Every number on the statement now comes from entered rows.** `statement_service.py` holds no
> fixture constants: the €1.200 Müll cost is a `CostEntry`, the €10.300 heating invoice and its CO₂
> figures are a `HeatingCostEntry`, and all consumptions (20.000 kWh, 40 m³, 600/250/150 units) are
> folded from `MeterReading` rows through the Phase D `MeterGateway` port. Verified end to end from
> an empty database.

**Goal:** a landlord can walk the full happy path live.

- **Vermieter portal**: create Building → Unit → Tenancy; enter cost entries + meter readings; pick
  allocation keys; run the statement; render a **NK + heating/CO₂ PDF**.
- Seeded **demo scenarios** from `docs/06-demo-scenarios.md` load with one click.
- Apple-like, WCAG-AA UI using the design system. German copy. Autosave (no data loss on abort).

**DoD:** from a clean login, produce a correct NK+heating PDF for the seeded solo-landlord scenario
without touching a database by hand.

---

## M4 — Doc-extraction (OCR/Vision) pipeline — canned demo for pitch ✅ done

- One **upload → prefill → confirm** flow, shared by NK-receipt OCR **and** migration import.
- **Vision adapter is stubbed** for the pitch: canned sample invoices return prefilled fields from
  fixtures; real EU+AVV provider is flagged behind the same adapter interface.
- Review UI where the user confirms/corrects extracted fields before they hit the ledger.

**DoD:** uploading a sample invoice pre-fills a cost entry the user confirms — demonstrable with canned data.

**Built** (`docs/04` → "Beleg-Upload"): `/a/{id}/beleg` and
`POST /a/{id}/buildings/{id}/extractions`. Extraction **writes nothing** — the confirm step goes
through the ordinary Kosten erfassen endpoint, sharing one form contract with the manual screen.
Confidence is **per field**, and the `needs_review` threshold lives on the API. Deliberately **not**
built: any mapping from cost type to Umlageschlüssel — that needs the BetrKV catalogue, still a
pending spec (`docs/08`), and the response reports the key as *not extracted* instead of guessing.
`vendor_name` / `invoice_date` are shown but not stored: they belong to a Beleg record (file + hash,
GoBD), which needs object storage and its own spec.

---

## FK-Isolation slice — composite FKs on `(id, account_id)` (runs before M5)

> **Split out of M5** (decision, 02.08). M5 is already identity + roles + portals + RLS; a single
> migration touching most tables *inside* it makes any failure impossible to attribute. The FK work
> needs nothing from identity, so it ships as its own slice, sequenced first.

**Goal:** make a cross-account foreign key **unrepresentable in Postgres** — not merely something the
application does not write.

- Postgres enforces referential integrity with **RLS bypassed**. A row that stamps its own
  `account_id` correctly satisfies `WITH CHECK` and can still point a parent link at another
  account's row. `WITH CHECK` is **necessary but not sufficient** — the full argument lives in
  `docs/02-data-model.md` → "Isolation rule".
- All **15** tenant-to-tenant foreign keys become composite: each parent gains
  `UNIQUE (id, account_id)`, each child FK spans `(parent_id, account_id)`. `MATCH SIMPLE`, so
  nullable links (`meter.unit_id`, `building.landlord_id`, the `direct_*` columns) keep their
  "unset" meaning — never `MATCH FULL`.
- **DECISION (closed): `building_assignment` gets an `account_id` column**, not an app-level check.
  (a) Every other tenant table has one; transitive scoping is the odd case out. (b) An app-level
  check is exactly what gets forgotten when the next endpoint is written. (c) The usual objection to
  denormalising `account_id` is drift — and the composite FK
  `(membership_id, account_id) → membership (id, account_id)` makes drift **structurally
  impossible**: the column cannot disagree with its membership. Its RLS policy then compares the
  local column instead of joining `membership`, and its `EXEMPT` entry in
  `scripts/check_rls_coverage.py` becomes dead code, to be removed with the migration.
- **Completeness is a gate, not a test count.** `scripts/check_fk_isolation.py` (lead-owned, not yet
  written) fails on any tenant-to-tenant FK that is not composite, so every *new* FK inherits the
  rule. `packages/db/tests/test_rls_isolation.py::TestCrossAccountForeignKeys` carries the
  behavioural proof on three representative shapes — a NOT NULL child (`unit.building_id`), a
  nullable link (`meter.unit_id`), and the transitive-scope case
  (`building_assignment.building_id`) — deliberately not one test per edge.

**DoD:** the three `TestCrossAccountForeignKeys` tests go green **without their assertions changing**
— an insert that stamps its own `account_id` correctly but points a FK at another account's parent is
rejected by the database; `check_fk_isolation.py` passes over all 15 edges plus the 2 on
`building_assignment`; `check_rls_coverage.py` reports **no new problem** with `building_assignment`
in the tenant-table loop instead of `EXEMPT` — it still exits 1 on `landlord` + `self_use_period`,
which are M5a's and cannot close here; the demo path (clean DB → seed → statement → PDF) is
re-verified.

---

## M5a — Identity schema + isolation (schema and policies only) — execution row 2

> **Split out of M5** (decision, 03.08), for the same reason the FK slice became row 1.5: M5 was
> identity **and** roles **and** RLS **and** routers **and** portal screens. A migration that changes
> row visibility, landing in the same milestone as the API and UI that consume it, makes any failure
> impossible to attribute. M5a is schema + policy, no HTTP surface, no React.

- Three-layer model: **Person / Account / Membership** + `Landlord`, `Renter`, `SelfUsePeriod`
  (`docs/02-data-model.md`). Supabase Auth maps onto `Person`.
- Roles OWNER / EMPLOYEE / TAX_ADVISOR on Membership and `AccountShape` SOLO / HAUSVERWALTUNG are
  **already shipped** — Python enums in `models.py`, PG enum types `role` / `account_shape` created in
  migration `0001`, `membership.role` and `account.shape` both `NOT NULL` (verified against
  `pg_enum`, 03.08). Nothing to build; nothing to test that would not pass on arrival.
- Composite FKs on `(id, account_id)` are **not** part of M5a — they shipped in the FK-Isolation slice
  (row 1.5); M5a builds on a schema where **tenant-to-tenant** cross-account edges are already
  impossible.
- **`landlord` + `self_use_period`** are the last two problems `scripts/check_rls_coverage.py` reports.
  Both already carry a FORCEd policy from `0001` — the reported failure is check **4**, *not named in
  the isolation test*, i.e. the policy was never exercised. `self_use_period` is the substantive one:
  a `SELF_USED` row on a foreign unit silently removes that area from the other account's allocation
  base.
- **`person` is the edge the FK slice could not reach — the READ half is M5a's.** `person` is global
  and carries **no RLS today** (verified live against `0004`: `relrowsecurity = f`, zero policies), so
  `lokara_app` in any one account reads every human in the database. A composite FK cannot fix it —
  `person` has no `account_id` to compose with and must not get one, since one human legitimately
  belongs to many accounts, which is the whole reason Person / Account / Membership are three tables.
  `scripts/check_fk_isolation.py` is silent here **by construction** (it inspects tenant-to-tenant
  edges only), so a green gate says nothing about `person`.
  - The mechanism is **RLS with an `EXISTS` over `membership`**, deny-by-default. Full spec,
    including the two open sub-decisions and the one way it must **not** be fixed:
    `docs/02-data-model.md` → "The `person` edge splits: READ is a policy (M5a), WRITE is an ordering
    rule (M10)".
  - ⚠️ **Do not relax the policy to make an unscoped login lookup work.** Adding
    `OR current_setting('app.account_id', true) IS NULL` switches the policy off for every unscoped
    connection in the system. The bootstrap read gets its own path (row 2.5 names it).
- **Note for the lead (script is lead-owned, not edited here):** once `person` is under RLS, its entry
  in `scripts/check_rls_coverage.py` stays in `EXEMPT` — that set is about *tables with no
  `account_id` column*, which `person` still is — but the module docstring's *"`person` … is
  deliberately not under RLS"* becomes false and should be reworded.

**DoD:** `packages/db/tests/test_rls_isolation.py` is fully green, specifically:
`TestLandlordAndSelfUseIsolation` (4 tests: read blocked, non-vacuous own-context control, and
`WITH CHECK` on both inserts) and `TestGlobalPersonIsolation` (3 tests: `person` ENABLEd **and**
FORCEd; a caller sees a `person` row only where an account is shared, asserted in **both** directions
against a control person who holds a Membership in the reading account; and zero rows with no context
set). `scripts/check_rls_coverage.py` exits **0** — `verify_demo_path.sh` clears its RLS step. The
demo path (clean DB → seed → statement → PDF) is re-verified.

---

## M5 remainder — roles in the API, portals, context switching — execution row 2.5

- Portals + **URL-carried context** (`/a/{accountId}/…`, `/renter/{tenancyId}/…`); switcher only when
  a Person holds >1 context. Menu is navigation, not authorization — every request independently
  verifies the relationship in the URL, then scopes the query.
- Enforce roles in app logic on top of M5a's RLS backstop: an EMPLOYEE is limited to their
  `BuildingAssignment`s (zero assignments ⇒ sees nothing); TAX_ADVISOR is read-only.
- **Name the bootstrap path for `person`.** M5a's policy denies by default, so the login lookup
  (find the Person behind a Supabase Auth user, before any account context exists) must run through a
  `SECURITY DEFINER` function or a dedicated role. Pick one and record it in `docs/02`.
- **Guard the `renter.person_id` ordering rule with an artifact, not a comment.** The column is
  written by **exactly one** path — M10's activation-code redemption — so at this milestone the
  provable statement is a **negative**: no API route sets `person_id`, asserted over the OpenAPI paths
  the same way create-only `meter_reading` asserts the absence of PUT/PATCH.

**DoD:** an EMPLOYEE with no building assignments sees nothing; a renter context exposes zero landlord
data (verified in app logic **and** RLS); a Person holding two contexts can switch between them by URL
and each request re-verifies; the OpenAPI surface contains no write path that sets `renter.person_id`.

---

## M6 — Bank + Payment Ledger (async layer enters here)

- Add the **Celery/Arq worker + webhook layer on Redis** to the existing FastAPI API (the API itself
  has been there since M0). Redis also backs caching + rate-limiting from here on.
- **finAPI stubbed** (fake transactions) behind an AIS adapter; fuzzy matching (IBAN/amount/purpose) →
  payment status. Store transactions + IBAN→Renter mappings in our own DB (versioned IBAN history).
- **Payment Ledger** (append-only, payment-date mandatory) — source of truth for tax.
- **`AdvancePaymentPeriod`** — the temporal NK-Vorauszahlung (`tenancy_id`, `amount_cents`,
  `valid_from`, `valid_to`) replacing the `Tenancy.advance_payment_cents` scalar. § 560 Abs. 4 BGB
  lets either party adjust the advance after every statement, so it changes *during* a tenancy by
  design. Migration + backfill (every existing tenancy → one open-ended period) + the API
  create/read shapes. See `docs/02` → "DEFECT: `Tenancy.advance_payment_cents` is a scalar on a
  temporal row".
- **BGH formal minimum #4 — the Saldo block on the statement — is M6 work, not earlier.** It needs
  *both* the ledger (the **geleistete** Vorauszahlungen; `advance × months` is the agreed figure and
  is rejected — `docs/08` → "#4 is blocked on the M6 ledger, by decision") **and** the temporal
  advance above. It is not a rendering task and must not be shipped as one.
- Background jobs (Celery/Arq on Redis): sync, 180-day reconsent cleanup, deadline watchers.

**DoD:** seeded bank transactions auto-match to renters; an NK Nachzahlung becomes a ledger Payment;
a tenancy's advance can change mid-lease without ending the tenancy, and a statement's Saldo deducts
the **paid** advances, not the agreed ones.

---

## M7 — Tax export + AfA

- `packages/export-engine` (pure): **Anlage V** (PDF+CSV) + **DATEV EXTF** (Windows-1252, `;`, CRLF)
  from the ledger; Readiness-Check; immutable export archive with hash+timestamp.
- `packages/afa-engine` + AfA-Wizard; 15%-Wächter; Loan entity → interest prefill.

**DoD:** byte-exact DATEV + Anlage-V golden tests; export archived immutably.

---

## M8 — Document / letter engine (Vertragsgenerator)

- **Versioned clause blocks**; a contract = a composition of clause versions, stored. BGH change →
  new version + flag affected contracts. Mieterhöhung, Kündigung, Mahnung, SEPA-Mandat.
- VPI via Destatis GENESIS API; Mietspiegel provider stub.

**DoD:** generate a contract from versioned clauses; a clause update flags affected contracts.

---

## M9 — Reminder/trigger + email delivery + checklists

- Trigger/state-machine engine: **§556 countdown + Zugangs-Wächter**, arrears, move-in/out chains, UVI.
- **Email delivery subsystem** (Modell A: own domain, From-name = landlord) with delivery-status
  ledger → 3-colour Zustell-Ampel (§556 proof of receipt). **Email provider stubbed** for now.
- Data-driven checklist library that spawns reminders.

**DoD:** §556 deadline counts down and escalates; delivery states render on the Ampel.

---

## M10 — Portals & modules + native apps at launch

- Mieterportal (activation codes bound to Tenancy, per-person, single-use), Tickets (Mängel),
  StB guest access, **Investment add-on** (Prüfobjekt → Kanban → becomes Building; 7-KPI cockpit).
- **M10 owns the write half of the `person` edge** (moved here from M5, 03.08). `renter.person_id`
  is NULL at creation and is written by **exactly one** path: redeeming an ActivationCode bound to one
  of that renter's tenancies. This is an **ordering rule plus a null default — no trigger, no CHECK,
  no foreign key.** The old M5 DoD line *"an insert of `renter(person_id = a person with no
  relationship to this account)` is rejected"* is **withdrawn**: the person being linked has, by
  definition, no prior relationship to the account (that is what activation *is*), and enforcing it
  would break persona 4 — one login as Vermieter in account A **and** Mieter in account B, execution
  row 2.5's whole differentiator. Reasoning in full: `docs/02-data-model.md` → "The `person` edge
  splits: READ is a policy (M5a), WRITE is an ordering rule (M10)".
- Also decide here whether `renter.person_id` may ever be **repointed** once set — silently moving a
  link from one human to another hands over portal access to a tenancy's statements. Unlike the
  creation case, immutability-once-set **is** expressible; it is not specified yet, so do not assume it.
- Native **iOS/Android** at public launch (Expo/RN; Capacitor/PWA fallback if native slips) — shared
  stack with web (Jotai, TanStack Query, RHF+Zod, i18n, theme), `react-native-ease` motion, secure
  storage + Bearer JWT.
- **Billing wired:** Stripe (web subscription) + **RevenueCat** (mobile in-app purchases).
- **Load test with Locust** (~100 concurrent users) before launch to confirm the API holds.

**DoD:** renter onboards via code and sees only their tenancy; investment cockpit computes KPIs from
the annuity schedule. Plus the redemption invariant, proven as a test: a valid single-use code sets
`renter.person_id`; a spent code, a code bound to another tenancy, and a direct write outside
redemption all leave it untouched.

---

## Reality flag (from the arch doc)

A lot has been pulled into V1 (native apps + OCR + contract engine + investment module by ~Sept) for a
small team, and the pre-pitch plan above now attempts **M4→M10** on top of that. That is a deliberate
stretch, taken with eyes open.

**The floor, if everything else slips:** M0→M3 is built, green and demoable *today* — a correct
CO₂-compliant NK/heating statement from user-entered data, with tenant isolation proven. That alone is
a legitimate pitch. Everything above it is upside.

So: guard the sequence — correctness first, breadth second. Use the **cut list**, keep a
**`demo-green` tag** at all times, and never let integration or native-app work cannibalise
Tier-1 (engine) capacity or destabilise the working path.
