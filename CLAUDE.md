# CLAUDE.md — Lokara Web App

> This is the operating contract for anyone (human or AI) building Lokara.
> Read this first, then `PLAN.md`, then the relevant file under `docs/`.
> The single deepest source of truth is `lokara-arch.md` (canonical architecture, v3).

> **The stack is v4.** A **Python FastAPI** backend (`apps/api`) + **Python** engine packages
> (`packages/*-engine`), **Supabase Postgres**, a **Bun** TS/JS workspace for web + mobile
> (`apps/web`, `packages/ui`), and **shadcn/ui**. There is one backend and it is Python.
> `MIGRATION-PLAN.md` records how the tree got here. When code and docs disagree, the docs win.

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

1. **The money/legal math is the product — keep it in pure, framework-free Python engine packages
   with golden tests (pytest).** Engines (`packages/*-engine`, Python) import no web framework, no
   vendor SDK, no database. They take normalized inputs (plain dataclasses / Pydantic models) and
   return deterministic outputs. A wrong framework choice later costs an app rewrite; it must never
   touch an engine or the data.

2. **Correctness and auditability beat features.** Every legally-relevant record (statements, ledger
   entries, exports, IBAN history, email delivery, contracts) is **immutable + versioned** — new
   version, never overwrite. Store hashes where legally relevant (GoBD / §147 AO).

3. **Multi-tenant isolation is not optional.** Every domain row carries `accountId`. Scope every
   query by it. Enforce isolation **twice**: in app logic **and** in Postgres Row-Level Security
   (RLS). Hiding a UI link protects nothing — the endpoint must independently verify the caller holds
   the relationship in the URL.

---

## The calculation spec lives in `berkay-work/` and is the source of truth

For **calculation rules**, the precedence is `berkay-work/` → `docs/` → the engines.
Berkay's spec supersedes `docs/` and the code where they disagree. (`lokara-arch.md` stays
canonical for *architecture*; this rule is about numbers, formulas and legal values.)

1. **`berkay-work/` is committed and immutable.** Nobody edits anything under it — not a typo, not
   a broken table, not a value that looks wrong. It stays exactly as exported so a transcription can
   always be diffed against what he actually wrote. The moment someone "fixes" a value in there, the
   transcriptions lose their oracle. Findings about its content go in a report, never in the file.

2. **Do not copy his `.md` files into `docs/` — transcribe them.** They are Notion exports with hash
   suffixes and URL-encoded links to `.csv` files that will not exist; they address "Seite 01b", not
   `docs/03`; their section 6 is 183 worked examples that belong in `tests/`, not in a doc; and the
   Non-Goals page has broken HTML tables he flagged himself. A verbatim copy also creates two
   unsynced copies of every rule — exactly the drift `docs-reconciler` exists to find.
   **Every transcribed `docs/` file carries a header line naming its source file in `berkay-work/`.**

3. **One exception: the Rechtsstand register.** `berkay-work/Calculations/Rechtsstand-Register …csv`
   is already structured data — a CSV (Comma-Separated Values) file of 179 rows: Wert, Betrag/Satz,
   Flag, Quelle, Rechtsgrundlage, Rechtsnatur, Rechtsstand. Import it into `rules-store` nearly
   as-is — no prose transformation.

4. **Every value lands with its flag intact.** Rechtsnatur (Gesetz / Verordnung / Konvention /
   Heuristik), Rechtsstand, source URL, and `verify-before-production` vs `geprüft`. **137 of 180 are
   `verify-before-production`.** His `README-for-Emir.md` lists what must **not** be treated as
   verified: Anlage-V line numbers, SKR03/SKR04 (Standardkontenrahmen) accounts, DATEV EXTF
   (the DATEV export text format) parameters, and three BFH (Bundesfinanzhof, the Federal Fiscal
   Court) case numbers marked `ZITAT UNSICHER`. **Transcribing a flagged value as fact is the error
   to avoid** —
   the computation paths are right, the numbers are placeholders of realistic magnitude.

5. **Do not be conservative about editing existing `.md` files.** `docs/03`, `docs/06`, this file,
   `DEMO-RUNBOOK.md` and `.claude/agents/statement-reviewer.md` all carry rules his spec overrides.
   Change them. Record the reason for each change in the transcribed `docs/` file, so that a later
   reader does not "restore" a rule that was deliberately superseded.

---

## Locked tech decisions (MVP defaults — see `docs/01-tech-stack-and-decisions.md`)

| Area                                                    | Decision                                                                                                                                                                                                                                                                        |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Language                                                | **Python** (backend + engines, `mypy` strict) + **TypeScript** (frontend + mobile, `strict: true`)                                                                                                                                                                             |
| Repo                                                    | Polyglot monorepo: **Bun + Turborepo** for the TS side (web, mobile, ui); **uv** for the Python side (api, engines)                                                                                                                                                            |
| Web                                                     | Next.js (App Router) + React + Tailwind + Framer Motion + **shadcn/ui** — **frontend only** (no direct DB access)                                                                                                                                                              |
| Mobile                                                  | **Expo / React Native** — same API + shared patterns as web. `react-native-ease` (animation), **secure storage + Bearer JWT**, i18n, theme, responsive from the start                                                                                                          |
| Client state / data / forms                             | **Jotai** (client state) + **TanStack Query** (server state) + **React Hook Form + Zod** (forms) — on **both** web and mobile                                                                                                                                                   |
| Money math                                              | Pure Python packages: integer **cents** + `decimal.Decimal`; never floats                                                                                                                                                                                                     |
| DB / Auth / Storage                                     | **Supabase Cloud, EU region (Frankfurt)** + signed DPA (revisit self-hosted before real tenant data)                                                                                                                                                                           |
| ORM                                                     | **SQLAlchemy 2.0 + Alembic** (migrations) against Supabase Postgres; RLS underneath. **The DB layer lives in `apps/api`, never in a client app.**                                                                                                                              |
| Backend / API                                           | **FastAPI (`apps/api`, Python) from day 1** — one standalone HTTP/JSON API that both the web app **and** the launch-day native iOS/Android apps consume. Routers per domain (modular monolith); **FastAPI dependencies** for Supabase-JWT auth + RLS context. Async workers (Celery/Arq on Redis) added when M6 needs them. |
| Runtime validation                                      | **Pydantic** (backend) + **Zod** (frontend/mobile) — validate at every boundary                                                                                                                                                                                               |
| Infra                                                   | **Redis** — rate-limiting + caching. **Locust** — load testing (simulate ~100 concurrent users)                                                                                                                                                                               |
| PDF                                                     | HTML→PDF via headless Chrome (**Playwright for Python**)                                                                                                                                                                                                                       |
| Paid/expensive APIs (finAPI, Vision/OCR, email, payments) | **Stubbed behind adapters** for the pitch. Payments: **Stripe (web) + RevenueCat (mobile IAP)**. Real providers are flagged, EU + AVV required. Never hardcode a vendor SDK into an engine or domain module.                                                                  |
| Hosting (prod)                                          | EU/DE (target Hetzner). Local/dev is fine anywhere.                                                                                                                                                                                                                            |
| UI copy language                                        | **German**. Code, comments, docs, identifiers: **English**.                                                                                                                                                                                                                   |

Anything marked "to confirm" in `lokara-arch.md` has a pragmatic default locked in
`docs/01-tech-stack-and-decisions.md`. Build around the default; don't reopen it without a reason.

---

## Cross-cutting rules (apply everywhere)

- **Never hardcode a legal rule.** AfA rates, HKVO ratios, CO₂ 10-step table, Anlage-V line numbers
  per year, Grunderwerbsteuer per Bundesland, clause versions → a **versioned rules/config store**
  with an "as-of law date". Show `Rechtsstand MM/JJJJ` in every legal output.
- **Adapters at every external edge.** Bank (finAPI), meter platforms/MDL, DATEV, Destatis, AI/Vision
  each normalize to an internal model _before_ any engine sees it.
- **"Tool, not advice."** Every legal/tax output carries a consistent
  _"rechtskonform, keine Rechts- oder Steuerberatung"_ disclaimer. Keep the StBerG line out of the product.
- **Guard/Wächter is one reusable pattern.** §556 deadline, Eichfrist, 15%-AfA, UVI, arrears → all
  "compute a warning from existing data" → one guard+reminder mechanism, not bespoke code each time.
- **Temporal by default.** Anything that changes _during_ a period is a row with `validFrom/validTo`,
  never a scalar (tenancies, allocation keys, meters, self-use, IBANs…). See `docs/02-data-model.md`.
- **Two financial time-axes never merge.** NK billing = accrual/period-based. Tax = cash basis
  (§11 EStG, payment date). Distinct subsystems, one clean handoff. See `docs/02-data-model.md` §"Two time-axes".
- **Auth tokens differ per client, one flow.** Web stores the JWT in an **HttpOnly cookie**; mobile
  stores it in **secure storage** and sends it as a **Bearer** token. Access/refresh handled in one
  shared **`api.ts` interceptor**: on a 401, refresh once, replay the failed requests, and never
  double-fire. The auth hook layer is separate per platform (cookie vs secure storage); the API
  verifies the Supabase JWT the same way for both.
- **Never trust the client.** Validate every request body with **Pydantic** on the backend; mirror the
  shape with **Zod** on the client. The backend is the authority.

---

## Naming traps (get these wrong and the schema rots)

- **Account** = the paying SaaS customer / isolation boundary. **Renter** = the German _Mieter_.
  Never call a renter a "tenant" in the schema ("tenant" is overloaded).
- **Role lives on the Membership, never on the Account.** `AccountShape` (SOLO / HAUSVERWALTUNG) is a
  property of the account; a personal role (OWNER / EMPLOYEE / TAX_ADVISOR) is a Membership.
- **Landlord (Vermieter)** = a data entity (the legal lessor on statements), _not_ a role.
- **Eigennutzung (self-use)** is a `SelfUsePeriod` (m²-based, over time), **never** a Renter row.

---

## Definition of done for any engine work

1. Pure Python package, no web-framework/DB/vendor imports.
2. Golden fixtures committed (pytest); output is byte-/cent-exact and deterministic.
3. The canonical **€1,200 garbage-cost allocation example** (`docs/03-nk-heating-engines.md`) passes.
4. Rounding is **`round_half_up` per share at assignment**; the **Verteilungsrest**
   (`Blockbetrag − Σ Anteile`) goes to the **owner bucket**, together with the vacancy share.
   ±1 ct per block is expected and correct. Totals reconcile to the input to the cent **once the
   residual is counted** — the owner absorbs the difference.
   *Changed from largest-remainder (Berkay R1/R5/K9, `docs/03`; see the precedence rule above). The
   canonical €1,200 fixture is identical under both methods — 600,00 / 178,52 / 181,48 / 240,00,
   residual exactly 0 — so this change did not move it, and nobody may claim it did.*
5. `mypy --strict` clean; money is `decimal.Decimal` + integer cents, never `float`.

## Definition of done for any UI work

1. Uses the design tokens in `docs/05-design-system.md` (no ad-hoc colors/fonts); shadcn components are
   themed to those tokens, never left on their defaults.
2. Meets **WCAG 2.1 AA / BFSG**: contrast, visible focus states, scalable type, keyboard nav.
3. German UI copy; labels are explicit (Apple-style reduction is aesthetic only, never at the cost of
   a clear label or contrast).
4. Meets the **Look & feel / motion principles** in `docs/05` — one primary action per screen, 8px
   spacing, calm surfaces, 150–250ms ease-out motion (transform/opacity only). "Modern, minimal,
   Apple-like" is a requirement, not a later polish pass; a screen that feels flat or cluttered isn't done.

---

## How to work

- **`AGENTS.md` is how work is executed here** — the deterministic gates (`scripts/gate.sh`,
  `scripts/verify_demo_path.sh`, the purity/RLS/PDF checks) and the six agents with disjoint write
  scopes. No agent may both write a test and satisfy it.
- Follow `PLAN.md`. Milestone DoDs are binding; **engines + fixtures before UI**. Before the 06.08
  pitch the build order is the **execution order** in `PLAN.md` (value ÷ risk), not the milestone
  numbering — and its **hard rules** apply: no calculation without its transcribed spec + golden
  fixture, the demo path is re-verified every milestone, tag each green state, stubs stay stubs.
- **Never leave the demo path broken.** If a change breaks clean-DB → seed → statement → PDF, fix or
  revert before moving on. A working demo beats a broader broken one.
- When a decision isn't covered here or in `docs/`, prefer the choice that (a) keeps engines pure,
  (b) keeps data immutable/versioned, (c) keeps `accountId` scoping intact — in that order.

- **Never implement a calculation from a pasted spec or from memory.** Transcribe it into the matching
  `docs/` file first — inputs, formula, edge cases, legal basis, **`Rechtsstand`** — then turn its
  worked example into a golden fixture, then write the code. If no `docs/` file fits, add one and link
  it from `README.md`.
- **If a new spec contradicts `docs/`, stop and ask.** Don't silently pick one; a `docs/` rule may
  encode a decision the newer spec hasn't caught up with.
- **The session writes its end-of-task summary to `LAST_OUTPUT.md`** at the repo root, overwriting it
  each time — same content as the chat summary (what was built, decisions worth knowing, gates,
  what's next). It's the handoff other tools read. Gitignored on purpose: it's scratch, not project
  history.
  **This is the session's file, not an agent's.** A subagent reports to the session and never writes
  it: it sees one lane, and a handoff composed from one lane is the stale handoff `check_handoff.sh`
  exists to catch. `.claude/hooks/write-scope.sh` therefore blocks every agent from creating it, and
  that is correct — an agent that hits the block should report the conflict, not widen its lane.
  Composing the agents' reports into one handoff is the session's job.
