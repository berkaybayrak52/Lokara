# PLAN.md — Lokara Web App roadmap (milestones)

> Build **iteratively**. Each milestone has a Definition of Done (DoD). Do not start a milestone
> before the previous one's DoD is met. **Engines + golden fixtures always come before UI.**
> Canonical dates from `lokara-arch.md`: MVP freeze **23.07**, pitch **27.07**, web-only focus until
> **25.07**, public launch **~08.09** (web + native iOS/Android together).

## Pitch cutline (5-day target)

For the **27.07 investor pitch** the app should be _mostly real_ with **stubs where APIs cost money**
(finAPI, Vision/OCR, email, billing) and **seeded example scenarios** for the common cases
(edge cases deferred). Concretely:

```
PITCH TARGET = M0 → M3 solid, + M4 shown as a canned demo
```

Everything from **M5 onward is the full-foundation build after the pitch**, staged in the order below.

---

## M0 — Foundations & scaffolding

**Goal:** an empty but correct skeleton everything else hangs off.

- Turborepo + pnpm; **`apps/web` (Next.js) + `apps/api` (NestJS)** + `packages/*` layout
  (see `docs/04-web-app-structure.md`).
- TypeScript `strict`; ESLint/Prettier; Vitest as the test runner; Turbo pipelines; CI.
- Tailwind wired to the **design tokens** from `docs/05-design-system.md` (colors, Montserrat/Manrope).
- Supabase project (EU/Frankfurt) provisioned; **Prisma initialized inside `apps/api`** against
  Supabase Postgres. `apps/web` calls the API over HTTP and never touches the DB.
- **NestJS API skeleton**: a Supabase-JWT auth guard + RLS-context middleware, one health endpoint,
  and a typed HTTP client in `apps/web`. (No workers/webhooks yet — those arrive at M6.)
- **Temporal core schema** migrated: `Building → Unit → Tenancy` with `validFrom/validTo`,
  integer-cents money, immutable-statement pattern. (Identity layer stubbed; full RBAC is M5.)
- PDF service skeleton (headless Chrome / Playwright) that renders a "hello" statement.

**DoD:** `pnpm dev` runs web + api; the web app reaches the API through the auth guard; `pnpm test`
runs; one Prisma migration applied; a trivial PDF renders.

---

## M1 — NK / operating-cost engine (⭐ pitch core)

**Goal:** the crown-jewel calculation, provably correct.

- `packages/nk-engine` — **pure**, no framework/DB imports.
- Day-weighted allocation; vacancy → landlord; **largest-remainder rounding** reconciling to the cent.
- All allocation keys incl. **DIRECT** (Direktzuordnung) and **MEA**; keys freely changeable without
  deleting entered data (per-period `AllocationKeyAssignment`, never on the cost row).
- Golden fixtures — the **€1,200 garbage-cost example** (`docs/03-nk-heating-engines.md`) passes exactly.

**DoD:** golden tests green; totals reconcile; changing a key re-runs cleanly and destroys no data.

---

## M2 — Heating + CO₂ engine

- `packages/heating-engine` — pure. §§7/8 HKVO 30/70–50/50 split, §9 warm-water separation,
  §9a estimation, degree-day apportionment on renter change, **CO₂ 10-step model (CO2KostAufG)**
  with Vermieter/Mieter split.
- HKVO ratios + CO₂ 10-step table live in the **versioned rules store**, not in code.

**DoD:** heating + CO₂ golden fixtures pass; a statement shows the landlord/renter CO₂ split with `Rechtsstand`.

---

## M3 — Web-app vertical slice + PDF (⭐ pitch demoable end-to-end)

**Goal:** a landlord can walk the full happy path live.

- **Vermieter portal**: create Building → Unit → Tenancy; enter cost entries + meter readings; pick
  allocation keys; run the statement; render a **NK + heating/CO₂ PDF**.
- Seeded **demo scenarios** from `docs/06-demo-scenarios.md` load with one click.
- Apple-like, WCAG-AA UI using the design system. German copy. Autosave (no data loss on abort).

**DoD:** from a clean login, produce a correct NK+heating PDF for the seeded solo-landlord scenario
without touching a database by hand.

---

## M4 — Doc-extraction (OCR/Vision) pipeline — canned demo for pitch

- One **upload → prefill → confirm** flow, shared by NK-receipt OCR **and** migration import.
- **Vision adapter is stubbed** for the pitch: canned sample invoices return prefilled fields from
  fixtures; real EU+AVV provider is flagged behind the same adapter interface.
- Review UI where the user confirms/corrects extracted fields before they hit the ledger.

**DoD:** uploading a sample invoice pre-fills a cost entry the user confirms — demonstrable with canned data.

---

## M5 — Identity, accounts, roles, RLS (start of full foundation)

- Three-layer model: **Person / Account / Membership** + `Landlord`, `Renter`, `SelfUsePeriod`
  (`docs/02-data-model.md`). Supabase Auth maps onto `Person`.
- Roles: OWNER / EMPLOYEE / TAX_ADVISOR on Membership; `AccountShape` SOLO / HAUSVERWALTUNG.
- Portals + **URL-carried context** (`/a/{accountId}/…`, `/renter/{tenancyId}/…`); switcher only when
  a Person holds >1 context. **Postgres RLS** enforced as the isolation backstop.

**DoD:** an EMPLOYEE with no building assignments sees nothing; renter context exposes zero landlord data
(verified in app logic **and** RLS).

---

## M6 — Bank + Payment Ledger (async layer enters here)

- Add the **BullMQ worker + webhook layer** to the existing NestJS API (the API itself has been there
  since M0).
- **finAPI stubbed** (fake transactions) behind an AIS adapter; fuzzy matching (IBAN/amount/purpose) →
  payment status. Store transactions + IBAN→Renter mappings in our own DB (versioned IBAN history).
- **Payment Ledger** (append-only, payment-date mandatory) — source of truth for tax.
- Background jobs (Graphile Worker/BullMQ): sync, 180-day reconsent cleanup, deadline watchers.

**DoD:** seeded bank transactions auto-match to renters; an NK Nachzahlung becomes a ledger Payment.

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
- Native **iOS/Android** at public launch (Expo/RN; Capacitor/PWA fallback if native slips).

**DoD:** renter onboards via code and sees only their tenancy; investment cockpit computes KPIs from
the annuity schedule.

---

## Reality flag (from the arch doc)

A lot has been pulled into V1 (native apps + OCR + contract engine + investment module by ~Sept) for a
small team. **The pitch (27.07) only needs M0→M3 + a canned M4.** Guard the sequence: engines and
correctness first; the launch surface stages in behind them. Don't let native-app or integration work
cannibalise Tier-1 (engine) capacity.
