# PLAN.md — Lokara Web App roadmap (milestones)

> Build **iteratively**. Each milestone has a Definition of Done (DoD). Do not start a milestone
> before the previous one's DoD is met. **Engines + golden fixtures always come before UI.**
> **There is no deadline in this plan, deliberately.** Dates that exist elsewhere
> (`lokara-arch.md`, the Wiki) are **communication events — when something gets shown — not planning
> inputs.** Nothing here is ordered, cut, or rushed because of one. If a date needs hitting, that is
> a decision about what to *show* on the day, taken against whatever is green then; it never
> reorders the work below. This replaced a pitch-plan framing (target date, cut list, stop-building
> checkpoint) that had ordered the whole file around a single demo.
>
> **Status: M0–M4 are built and green** on the v4 Python stack (FastAPI + SQLAlchemy/RLS + Bun/shadcn).
> The v4 migration is **complete**: it removed the pre-migration TypeScript, so there is now one
> backend and it is Python. Its only unstarted phase, the Expo skeleton, moved into **M10** below.
> `MIGRATION-PLAN.md` and `PHASE-H-PLAN.md` were **deleted** with the migration. The record is
> `git log --oneline pre-migration..phase-h-done` — one range, because Phase H merged `--no-ff` and
> is tagged.
>
> *Why they were deleted rather than kept as history:* they had started to mislead. `MIGRATION-PLAN`
> §0a still announced `main` untouched at `c5fadab` with "remaining: **G** (mobile) · **H**
> (cutover)", contradicting its own Phase H section forty lines later, which marks H done and merged.
> Its §4 body still called the NestJS/Prisma backend a coexisting reference, and its run instructions
> still warned that `turbo run dev` starts that backend on `:3001` — a port collision that stopped
> existing when Phase H deleted it. A doc that misleads is worse than no doc, and a reader cannot tell
> which half of a self-contradicting file to believe. `PHASE-H-PLAN.md` went with it: every prompt in
> its section 6 is spent, including H4, which `slice/m5-pre-context-read` superseded.
>
> Nothing live was lost. Its Appendix A (largest-remainder with its tie-break, the day-weighting rule,
> the €1,200 expected values) is in `docs/03` and in the `distribute_cents` docstring; Appendix B's
> RLS recipe is in `docs/02`, in more depth; §8's one **live** rule — *every new tenant table needs an
> RLS policy and a line in the isolation test* — moved to `AGENTS.md`, next to the gate that enforces
> it, and the six code docstrings that cited the file now cite its replacement. Phase G was the only
> unstarted phase and is an M10 bullet below.

## Execution order — what closes the legally-required surface first

**The ranking optimises for one thing: closing the surface a Mieter can legally cut the bill over.**
Three exposures are live in the product today — a missing **UVI** (unterjährige
Verbrauchsinformation) costs **3 %** of the heating cost, a missing **CO₂ disclosure** costs another
**3 %**, and a statement that is not **verbrauchsabhängig** costs **15 %** (§ 12 Abs. 1 HeizkostenV).
The differentiator is legal correctness, so legal correctness is what gets built first.

Berkay's spec is the other reason the order moved: **pages 06, 07 and 08 now exist, so M6, M8 and
M10 have specs where they had none.** M7's 🔒 comes off with a caveat that has to be carried into the
milestone itself, not just noted here (row 11).

*(This replaced an "investor value ÷ risk" ordering written for a pitch. See the no-deadline note at
the top of this file: the principle below is not a deadline argument and does not become one if a
date reappears.)*

| # | Work | Why here | Risk |
| --- | --- | --- | --- |
| 1 | ~~**Wire R1/R5/K9 + Ho/Hu into `heating-engine`**~~ — ✅ **done** 13.08.2026, `slice/wire-01b-rules` | Existed because `CLAUDE.md` DoD 4 described a legal rounding rule the code did not follow: `distribute_cents_half_up` had **zero production callers** and no boundary refused an Ho/Hu mismatch. Six of the ten sites moved to half-up, four provably could not move money, and one heating case (**no landlord party**) deliberately stays largest-remainder — the map is `docs/03` § 9. The demo pair did **not** move. | medium |
| 2 | **The Eigentümer-Residuum** — one reconciliation line per Liegenschaft and Kostenart, always printed | **Unblocked 14.08.2026, and larger than it was written.** Berkay did not confirm our model, he **replaced** it (`berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md` § 1): the Eigentümeranteil is **not a party** and is **never derived from occupancy** — it is a pure residual, `gesamt − Σ mieteranteile`, per Kostenart (Seite 01 D12, *"ALWAYS as a residual, NEVER computed separately"*). So the per-unit landlord parties **collapse into one** line, and **both** conventions in `docs/03` § 9.2 die: "residual to the first party" becomes moot, and the largest-remainder path for a fully-let building is explicitly rejected (*"soll nicht verwendet werden"*). It also has a **numeric** consequence, not just a layout one — where a figure can be computed two ways, the residual is the one that ships (`09-F07`: 1858, not the separately computed 1859). Touches `docs/02`, `docs/03` § 9, `docs/08`, the engine and the PDF. Until it lands, R1/R5/K9 governs only buildings with a vacancy. | medium |
| 3 | **§ 5 Abs. 1 S. 3 CO₂ rounding** — classify *after* rounding to one decimal | The engine classifies the raw `Decimal`, so 11,96 lands in a different Stufe than the 12,0 the statute says to classify — a wrong number on a legal document, § 7 Abs. 4 exposure. Small, isolated, no dependencies. `docs/03` → *"Known gap, deliberately not implemented here"*. | low |
| 4 | **M5 remainder** — roles in the API, portals, URL-carried context, switcher | Everything tenant-facing sits behind it. `slice/m5-pre-context-read` still carries the **25 pre-context-read fixtures**; the two things it was also carrying have since been taken off it and shipped on their own — the `gate.sh` skip-hole fix (`338dece`, on `main`) and the **ENVIRONMENT guard** (`slice/environment-guard`, `docs/01` D9). Neither depended on the role model, and holding them behind it was holding a security guard behind a feature. | medium |
| 5 | **Page 02 → `docs/09`** + BetrKV catalogue in `rules-store` | Two **built** screens take a free-text `Kostenart` today (`kosten/costs-page.tsx`, `beleg/review-step.tsx`), so nothing validates that a cost is even umlagefähig — and **M4 deliberately refuses to derive an Umlageschlüssel** because the catalogue does not exist. Catalogue import: structured data, not prose. | low |
| 6 | **M6** bank + Payment Ledger (finAPI stubbed) — **and BGH formal minimum #4** | The ledger closes the **Abzug der Vorauszahlungen**, the last of the four settled BGH minimums (`docs/08`). Until it exists the statement is formally *incomplete*, not merely thin. Page 08 (Bank-Matching) is specced. | high |
| 7 | **Page 05 → `docs/12`** — the Wächter set | § 556 Frist, Eichfrist, UVI-Turnus. One guard mechanism, three uses (`CLAUDE.md`: Guard/Wächter is one reusable pattern, not bespoke code each time). | medium |
| 8 | **Copy-and-citation slice** | The accumulated `statement-reviewer` findings — ligatures, blank space, footer citations. Genuinely polish, and it is *now* polish rather than a gap, because the rows above closed the substance. | low |
| 9 | **Block D2 — Heizspiegel-Vergleichswert** (K13 in `rules-store`) | **Unblocked 14.08.2026** by `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md` §§ 2–4, and deliberately **not** folded into row 2. Three decisions arrived at once: D2 compares **heating only**, so the Normwert has warm water subtracted (`mittel − ww_kwh_m2`, his § 2 — this **supersedes his own earlier D2 spec**, which compared against Wärme+WW); the deduction is **24 kWh/(m²·a)** per Energieträger except **Wärmepumpe ≈ 8**, because Heizspiegel heat-pump values are electricity after COP (his § 2.2, a `Konvention` on a JAZ assumption, to be confirmed with co2online) plus a `(mittel − ww) <= 0` guard; and the co2online licence is **no longer a gate** (§ 4 — build it, counter-sign a real §6a output later). Open and handled: `über-500` for Wärmepumpe and Holzpellets does not exist in any public table, so the MVP ships a **labelled fallback to the 250–500 class** and extrapolates nothing (§ 3). | medium |
| 10 | **UVI** — unterjährige Verbrauchsinformation | **Legally mandatory monthly** (§ 6a HeizkostenV); a missing one costs **3 %**. Needs row 4 for the tenant surface, monthly readings, and row 9 for the comparison value — **Berkay's K13 answer is now in hand** (14.08.2026), so this is no longer blocked on an input we do not have. | medium |
| 11 | **M7** tax export + AfA (pages 03 + 04) | Specced, **not production-ready**. See the caveat below and in the M7 milestone. | high |
| 12 | **M8** clause engine · **M10 remainder** (tickets, activation codes, investment cockpit) · **mobile skeleton** | Broadest surface, furthest from the legal core. | high |

**Row 11's caveat, stated here and repeated in M7 because it is the expensive one to forget:**
Berkay's `README-for-Emir.md` marks **Weg B**, **all Anlage-V line numbers**, the **SKR03/SKR04
accounts** and the **DATEV EXTF parameters** as placeholders of realistic magnitude — the computation
paths are right, the numbers are not verified. M7 may be built against them; **nothing derived from
them ships to a real Steuerberater** without the values being confirmed first.

### Hard rules

1. **🔒 No calculation without its spec.** A calculation must not start until Berkay's page exists, is
   transcribed into `docs/`, and its worked example is a golden fixture. Guessing German tax law is
   the one failure this product cannot absorb. If a spec isn't ready, **build the adapter/stub and
   move on** — never invent the numbers. Since page 01b landed, the lock is off M6/M7/M8/M10 in the
   sense that specs now exist; it is **not** off any value his register still flags
   `verify-before-production` (**130 of 180** — `CLAUDE.md` → the `berkay-work/` precedence rule).
   *(Was "137 of 180" until 15.08.2026. That was the count in the earlier export, now preserved in
   Git history. The authoritative `berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv` has
   130 flagged and 50 `geprüft`. `CLAUDE.md` names quoting 137 as the first symptom of reading the
   superseded export, so it does not get to sit in the hard rules.)*
2. **The demo path is sacred.** Every milestone ends with the full path re-verified end to end
   (clean DB → seed → statement → PDF). If a change breaks it, fix or revert before moving on.
3. **Tag every green state** (`git tag demo-green-<n>`). At any moment you must be able to check out a
   tag and demo. This is the whole safety net, and it is what makes a demo date cheap: you show the
   last green tag, you do not reorder work to reach one.
4. **One milestone per session**, each ending green (tests + CI). No half-merged subsystems.
5. **Stubs stay stubs.** finAPI, Vision, email, billing behind adapters — no vendor SDK, no real keys.
6. **A documented rule that the code does not follow is a defect, not a to-do.** Row 1 exists because
   `CLAUDE.md` described a rounding rule `heating-engine` did not implement. When that happens again,
   the fix is to wire it or to mark it — never to leave the contract asserting it.

---

## M0 — Foundations & scaffolding — ✅ done (Python stack)

> **What exists today:** M0 stands on the v4 Python stack — FastAPI + SQLAlchemy/Alembic + Bun/shadcn
> — re-established by the v4 migration. The interim TypeScript build (NestJS + Prisma) that
> originally satisfied M0 was removed at the end of it, which is now merged to `main`. It survives only
> at the **`pre-migration`** tag (`c5fadab`) — that tag, not a branch, is the historical fallback.
> `apps/mobile` (Expo) is the one part of the spec below that is still outstanding; it is now an
> **M10** bullet.

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

## M1 — NK / operating-cost engine (⭐ the product's core) — ✅ built (Python, migration Phase C)

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

## M3 — Web-app vertical slice + PDF (⭐ demoable end-to-end) — ✅ done

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

## M4 — Doc-extraction (OCR/Vision) pipeline — canned demo ✅ done

- One **upload → prefill → confirm** flow, shared by NK-receipt OCR **and** migration import.
- **Vision adapter is stubbed**: canned sample invoices return prefilled fields from
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

## M5a — Identity schema + isolation (schema and policies only) — ✅ done

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

## M5 remainder — roles in the API, portals, context switching

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

> ⚠️ **Specced, but not production-ready — the 🔒 came off the spec, not off the numbers.**
> Berkay's pages 03 + 04 give the computation paths, and those are right. His
> `README-for-Emir.md` marks the *values* as placeholders of realistic magnitude:
> **Weg B**, **every Anlage-V line number**, the **SKR03/SKR04 accounts** and the
> **DATEV EXTF parameters** — plus three BFH case numbers flagged `ZITAT UNSICHER`.
> Build against them; **nothing derived from them goes to a real Steuerberater or a
> Finanzamt** until each value is confirmed and its register flag flips from
> `verify-before-production` to `geprüft`. Transcribing a flagged value as fact is the
> specific error this milestone is exposed to (`CLAUDE.md` → the `berkay-work/` precedence rule).

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
  - **Mobile skeleton first** (was Phase G of the v4 migration, moved here verbatim when
    `MIGRATION-PLAN.md` was retired — it was the only phase never started):
    `apps/mobile` (Expo): same Jotai/TanStack/RHF/Zod, `react-native-ease`, secure storage +
    Bearer JWT, i18n + theme; consume the same FastAPI.
    **DoD:** Expo app logs in and reads one screen.
    Expo profiling belongs here too, not to the retired Phase H.
- **Billing wired:** Stripe (web subscription) + **RevenueCat** (mobile in-app purchases).
- **Load test with Locust** (~100 concurrent users) before launch to confirm the API holds.

**DoD:** renter onboards via code and sees only their tenancy; investment cockpit computes KPIs from
the annuity schedule. Plus the redemption invariant, proven as a test: a valid single-use code sets
`renter.person_id`; a spent code, a code bound to another tenancy, and a direct write outside
redemption all leave it untouched.

---

## Reality flag (from the arch doc)

A lot has been pulled into V1 (native apps + OCR + contract engine + investment module) for a small
team. That is a deliberate stretch, taken with eyes open — but it is a **scope** observation, not a
schedule one, and nothing above is ordered around fitting it into a window.

**The floor, at any moment:** M0→M4 is built, green and demoable *today* — a correct CO₂-compliant
NK/heating statement from user-entered data, with tenant isolation proven. Everything above it is
upside. That floor is what makes a demo date cheap to answer: you show the last `demo-green` tag.

So: guard the sequence — correctness first, breadth second. Keep a **`demo-green` tag** at all times,
and never let integration or native-app work cannibalise engine capacity or destabilise the working
path. If work has to stop early, stop at a green tag; there is no pre-agreed drop order, because the
rows above are ranked by legal exposure and dropping from the bottom is already the answer.
