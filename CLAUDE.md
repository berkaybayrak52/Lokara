# CLAUDE.md — Lokara Web App

> This is the operating contract for anyone (human or AI) building Lokara.
> Read this first, then `PLAN.md`, then the relevant file under `docs/`.
> The single deepest source of truth is `lokara-arch.md` (canonical architecture, v3).

---

## What Lokara is (one line)

A modern, trustworthy SaaS for **legally-compliant German Nebenkosten- / Betriebskostenabrechnung**
(operating-cost & heating-cost statements) for private landlords **and** property managers
(Hausverwaltungen) — from 1 unit upward, no cap — competing on **domain depth, fair pricing, and
AI-assisted UX** against objego, immocloud, vermietet.de.

We are building the **responsive Web App first**. Native iOS/Android come at public launch (separate,
later milestone). No desktop apps.

---

## The three rules that override everything

1. **The money/legal math is the product — keep it in pure, framework-free engine packages with
   golden tests.** Engines (`packages/*-engine`) import no framework, no vendor SDK, no database.
   They take normalized inputs and return deterministic outputs. A wrong framework choice later costs
   an app rewrite; it must never touch an engine or the data.

2. **Correctness and auditability beat features.** Every legally-relevant record (statements, ledger
   entries, exports, IBAN history, email delivery, contracts) is **immutable + versioned** — new
   version, never overwrite. Store hashes where legally relevant (GoBD / §147 AO).

3. **Multi-tenant isolation is not optional.** Every domain row carries `accountId`. Scope every
   query by it. Enforce isolation **twice**: in app logic **and** in Postgres Row-Level Security
   (RLS). Hiding a UI link protects nothing — the endpoint must independently verify the caller holds
   the relationship in the URL.

---

## Locked tech decisions (MVP defaults — see `docs/01-tech-stack-and-decisions.md`)

| Area | Decision |
|---|---|
| Language | TypeScript everywhere, `strict: true` |
| Repo | Turborepo + pnpm monorepo |
| Web | Next.js (App Router) + React + Tailwind + Framer Motion — **frontend only** (no direct DB access) |
| Money math | Pure packages: integer **cents** + `decimal.js`; never floats |
| DB / Auth / Storage | **Supabase Cloud, EU region (Frankfurt)** + signed DPA (revisit self-hosted before real tenant data) |
| ORM | Prisma against Supabase Postgres; RLS underneath. **Prisma lives in `apps/api`, never in `apps/web`.** |
| Backend / API | **NestJS (`apps/api`) from day 1** — one standalone HTTP/JSON API that both the web app **and** the launch-day native iOS/Android apps consume. Modules per domain; guards for Supabase-JWT auth + RLS context. Workers/webhooks (BullMQ) added when M6 needs them. |
| PDF | HTML→PDF via headless Chrome (Playwright) |
| Paid/expensive APIs (finAPI, Vision/OCR, email, Stripe) | **Stubbed behind adapters** for the pitch. Real providers are flagged, EU + AVV required. Never hardcode a vendor SDK into an engine or domain module. |
| Hosting (prod) | EU/DE (target Hetzner). Local/dev is fine anywhere. |
| UI copy language | **German**. Code, comments, docs, identifiers: **English**. |

Anything marked "to confirm" in `lokara-arch.md` has a pragmatic default locked in
`docs/01-tech-stack-and-decisions.md`. Build around the default; don't reopen it without a reason.

---

## Cross-cutting rules (apply everywhere)

- **Never hardcode a legal rule.** AfA rates, HKVO ratios, CO₂ 10-step table, Anlage-V line numbers
  per year, Grunderwerbsteuer per Bundesland, clause versions → a **versioned rules/config store**
  with an "as-of law date". Show `Rechtsstand MM/JJJJ` in every legal output.
- **Adapters at every external edge.** Bank (finAPI), meter platforms/MDL, DATEV, Destatis, AI/Vision
  each normalize to an internal model *before* any engine sees it.
- **"Tool, not advice."** Every legal/tax output carries a consistent
  *"rechtskonform, keine Rechts- oder Steuerberatung"* disclaimer. Keep the StBerG line out of the product.
- **Guard/Wächter is one reusable pattern.** §556 deadline, Eichfrist, 15%-AfA, UVI, arrears → all
  "compute a warning from existing data" → one guard+reminder mechanism, not bespoke code each time.
- **Temporal by default.** Anything that changes *during* a period is a row with `validFrom/validTo`,
  never a scalar (tenancies, allocation keys, meters, self-use, IBANs…). See `docs/02-data-model.md`.
- **Two financial time-axes never merge.** NK billing = accrual/period-based. Tax = cash basis
  (§11 EStG, payment date). Distinct subsystems, one clean handoff. See `docs/02-data-model.md` §"Two time-axes".

---

## Naming traps (get these wrong and the schema rots)

- **Account** = the paying SaaS customer / isolation boundary. **Renter** = the German *Mieter*.
  Never call a renter a "tenant" in the schema ("tenant" is overloaded).
- **Role lives on the Membership, never on the Account.** `AccountShape` (SOLO / HAUSVERWALTUNG) is a
  property of the account; a personal role (OWNER / EMPLOYEE / TAX_ADVISOR) is a Membership.
- **Landlord (Vermieter)** = a data entity (the legal lessor on statements), *not* a role.
- **Eigennutzung (self-use)** is a `SelfUsePeriod` (m²-based, over time), **never** a Renter row.

---

## Definition of done for any engine work

1. Pure package, no framework/DB/vendor imports.
2. Golden fixtures committed; output is byte-/cent-exact and deterministic.
3. The canonical **€1,200 garbage-cost allocation example** (`docs/03-nk-heating-engines.md`) passes.
4. Rounding uses **largest-remainder**; totals reconcile to the input to the cent.

## Definition of done for any UI work

1. Uses the design tokens in `docs/05-design-system.md` (no ad-hoc colors/fonts).
2. Meets **WCAG 2.1 AA / BFSG**: contrast, visible focus states, scalable type, keyboard nav.
3. German UI copy; labels are explicit (Apple-style reduction is aesthetic only, never at the cost of
   a clear label or contrast).
4. Meets the **Look & feel / motion principles** in `docs/05` — one primary action per screen, 8px
   spacing, calm surfaces, 150–250ms ease-out motion (transform/opacity only). "Modern, minimal,
   Apple-like" is a requirement, not a later polish pass; a screen that feels flat or cluttered isn't done.

---

## How to work

- Follow `PLAN.md` milestones **in order**. Don't start a later milestone before its predecessor's
  Definition of Done is met. **Engines + fixtures before UI.**
- The **pitch cutline is M0→M3 solid + M4 as a canned demo** (see `PLAN.md`). Everything past that is
  post-pitch foundation.
- When a decision isn't covered here or in `docs/`, prefer the choice that (a) keeps engines pure,
  (b) keeps data immutable/versioned, (c) keeps `accountId` scoping intact — in that order.
