# CLAUDE.md — Lokara Web App

> This is the operating contract for anyone (human or AI — Artificial Intelligence) building Lokara.
> Read this first, then `PLAN.md`, then the relevant file under `docs/`.
> The single deepest source of truth is `lokara-arch.md` (canonical architecture, v3).

> **The stack is v4.** A **Python FastAPI** backend (`apps/api`) + **Python** engine packages
> (`packages/*-engine`), **Supabase Postgres**, a **Bun** TS/JS (TypeScript/JavaScript) workspace for
> web + mobile (`apps/web`, `packages/ui`), and **shadcn/ui**. There is one backend and it is Python.
> `MIGRATION-PLAN.md` records how the tree got here. When code and docs disagree, the docs win.

---

## What Lokara is (one line)

A modern, trustworthy SaaS (Software as a Service) for **legally-compliant German Nebenkosten- /
Betriebskostenabrechnung** (operating-cost & heating-cost statements) for private landlords **and**
property managers (Hausverwaltungen) — from 1 unit upward, no cap — competing on **domain depth,
fair pricing, and AI-assisted UX** (User Experience) against objego, immocloud, vermietet.de.

We are building the **responsive Web App first**. Native iOS/Android come at public launch (separate,
later milestone). No desktop apps.

---

## The three rules that override everything

1. **The money/legal math is the product — keep it in pure, framework-free Python engine packages
   with golden tests (pytest).** Engines (`packages/*-engine`, Python) import no web framework, no
   vendor SDK (Software Development Kit), no database. They take normalized inputs (plain dataclasses
   / Pydantic models) and return deterministic outputs. A wrong framework choice later costs an app
   rewrite; it must never touch an engine or the data.

2. **Correctness and auditability beat features.** Every legally-relevant record (statements, ledger
   entries, exports, IBAN (International Bank Account Number) history, email delivery, contracts) is
   **immutable + versioned** — new version, never overwrite. Store hashes where legally relevant
   (GoBD — Grundsätze zur ordnungsmäßigen Führung und Aufbewahrung von Büchern, Aufzeichnungen und
   Unterlagen in elektronischer Form sowie zum Datenzugriff; § 147 AO — Abgabenordnung, the German
   Fiscal Code).

3. **Multi-tenant isolation is not optional.** Every domain row carries `accountId`. Scope every
   query by it. Enforce isolation **twice**: in app logic **and** in Postgres Row-Level Security
   (RLS). Hiding a UI (User Interface) link protects nothing — the endpoint must independently verify
   the caller holds the relationship in the URL (Uniform Resource Locator).

   > **What it means.** *Multi-tenant* = one deployment and one database serving every paying
   > customer at once; here a "tenant" is an **Account** (a private landlord, or a Hausverwaltung).
   > Two competing Hausverwaltungen's buildings, renters and statements live in the **same tables, in
   > adjacent rows**, separated by nothing but `account_id`. *Isolation* is the guarantee that one can
   > never read the other's rows.
   >
   > *Not optional* is about cost of failure. A wrong figure in a statement is a bug you fix; showing
   > Account A the renters of Account B is a personal-data breach under the DSGVO
   > (Datenschutz-Grundverordnung) — reportable within 72 hours, and fatal to a product sold on
   > trustworthiness. So it is never traded against a deadline the way a feature is.
   >
   > *Twice*, because the first enforcement is human: one forgotten `WHERE account_id = …`, on one
   > tired evening, leaks rows. RLS does not get tired. That is what `scripts/check_rls_coverage.py`
   > guards, and why nothing in it may be relaxed.
   >
   > *Hiding a UI link protects nothing*, because a hidden button is only a button that is not drawn
   > — anyone can still type `GET /buildings/123`. The endpoint must verify ownership of `123` on
   > every request rather than trust that the client only asks for what it was offered.
   >
   > The M5 pre-context read (`docs/02` → "The pre-context read") is the one sanctioned hole in this
   > fence: `GET /me` must read *before* any account context exists. The whole design effort there
   > went into keeping it exactly one hole, and `scripts/check_pre_context_reads.py` counts them.

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

## Locked tech decisions (MVP — Minimum Viable Product — defaults; see `docs/01-tech-stack-and-decisions.md`)

| Area                                                    | Decision                                                                                                                                                                                                                                                                        |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Language                                                | **Python** (backend + engines, `mypy` strict) + **TypeScript** (frontend + mobile, `strict: true`)                                                                                                                                                                             |
| Repo                                                    | Polyglot monorepo: **Bun + Turborepo** for the TS side (web, mobile, ui); **uv** for the Python side (api, engines)                                                                                                                                                            |
| Web                                                     | Next.js (App Router) + React + Tailwind + Framer Motion + **shadcn/ui** — **frontend only** (no direct DB (database) access)                                                                                                                                                   |
| Mobile                                                  | **Expo / React Native** — same API (Application Programming Interface) + shared patterns as web. `react-native-ease` (animation), **secure storage + Bearer JWT** (JSON Web Token; JSON = JavaScript Object Notation), i18n (internationalization), theme, responsive from the start |
| Client state / data / forms                             | **Jotai** (client state) + **TanStack Query** (server state) + **React Hook Form + Zod** (forms) — on **both** web and mobile                                                                                                                                                   |
| Money math                                              | Pure Python packages: integer **cents** + `decimal.Decimal`; never floats                                                                                                                                                                                                     |
| DB / Auth / Storage                                     | **Supabase Cloud, EU (European Union) region (Frankfurt)** + signed DPA (Data Processing Agreement) (revisit self-hosted before real tenant data)                                                                                                                              |
| ORM (Object-Relational Mapper)                          | **SQLAlchemy 2.0 + Alembic** (migrations) against Supabase Postgres; RLS underneath. **The DB layer lives in `apps/api`, never in a client app.**                                                                                                                              |
| Backend / API                                           | **FastAPI (`apps/api`, Python) from day 1** — one standalone HTTP (HyperText Transfer Protocol) / JSON API that both the web app **and** the launch-day native iOS/Android apps consume. Routers per domain (modular monolith); **FastAPI dependencies** for Supabase-JWT auth + RLS context. Async workers (Celery/Arq on Redis) added when M6 needs them. |
| Runtime validation                                      | **Pydantic** (backend) + **Zod** (frontend/mobile) — validate at every boundary                                                                                                                                                                                               |
| Infra                                                   | **Redis** — rate-limiting + caching. **Locust** — load testing (simulate ~100 concurrent users)                                                                                                                                                                               |
| PDF (Portable Document Format)                          | HTML (HyperText Markup Language) → PDF via headless Chrome (**Playwright for Python**)                                                                                                                                                                                        |
| Paid/expensive APIs (finAPI, Vision/OCR (Optical Character Recognition), email, payments) | **Stubbed behind adapters** for the pitch. Payments: **Stripe (web) + RevenueCat (mobile IAP — In-App Purchase)**. Real providers are flagged, EU + AVV (Auftragsverarbeitungsvertrag, the data-processing agreement) required. Never hardcode a vendor SDK into an engine or domain module. |
| Hosting (prod)                                          | EU/DE — European Union / Germany (target Hetzner). Local/dev is fine anywhere.                                                                                                                                                                                                                                  |
| UI copy language                                        | **German**. Code, comments, docs, identifiers: **English**.                                                                                                                                                                                                                   |

Anything marked "to confirm" in `lokara-arch.md` has a pragmatic default locked in
`docs/01-tech-stack-and-decisions.md`. Build around the default; don't reopen it without a reason.

---

## Cross-cutting rules (apply everywhere)

- **Never hardcode a legal rule.** AfA (Absetzung für Abnutzung — tax depreciation) rates, HKVO
  (Heizkostenverordnung) ratios, CO₂ 10-step table, Anlage-V line numbers per year,
  Grunderwerbsteuer per Bundesland, clause versions → a **versioned rules/config store**
  with an "as-of law date". Show `Rechtsstand MM/JJJJ` (Monat/Jahr) in every legal output.
- **Adapters at every external edge.** Bank (finAPI), meter platforms/MDL (Messdienstleister —
  metering services such as Techem, ista), DATEV, Destatis (Statistisches Bundesamt), AI/Vision
  each normalize to an internal model _before_ any engine sees it.

  > **What an adapter is.** The module that sits where we touch something we do not control, whose
  > one job is translation: the outside format becomes *our* shape before anything else sees it, and
  > the adapter is the only file in the tree that knows the foreign format exists. Two halves — the
  > **port**, a `Protocol` stating the shape we demand (`MeterGateway.list_readings(...) ->
  > tuple[MeterReading, ...]` in `packages/adapters/src/lokara_adapters/meter.py`), and the
  > **implementation** satisfying it: `StubMeterGateway` on fixtures today, the real provider later.
  > Six ports exist: bank, vision, meter, datev, destatis, email.
  >
  > **Why it is a rule.** (1) It is what keeps rule 1 true — if the heating engine parsed HeiWaKo
  > (the ARGE/bved metering-exchange format) itself, swapping ista for Techem would mean editing the
  > file that computes money. (2) A vendor swap stays in one file; `meter.py` says it outright:
  > *"only this module ever parses that format"*. (3) Downstream stops branching — a hand-typed
  > reading, an MDL delivery and a radio self-read all arrive as one `MeterReading`, so persistence,
  > statement and tests have one case, not three. (4) The demo and CI run with no network, no
  > credentials and no invoice, because the stub **is** the pitch implementation and the real one
  > merely replaces it. (5) It localizes the legal question: every external provider is a
  > sub-processor needing an AVV, and when adapters are the only outbound edges, the list of what
  > leaves the system is a directory listing.
- **"Tool, not advice."** Every legal/tax output carries a consistent
  _"rechtskonform, keine Rechts- oder Steuerberatung"_ disclaimer. Keep the StBerG
  (Steuerberatungsgesetz) line out of the product.
- **Guard/Wächter is one reusable pattern.** § 556 deadline, Eichfrist, 15 %-AfA, UVI (unterjährige
  Verbrauchsinformation), arrears → all "compute a warning from existing data" → one guard+reminder
  mechanism, not bespoke code each time.
- **Temporal by default.** Anything that changes _during_ a period is a row with `validFrom/validTo`,
  never a scalar (tenancies, allocation keys, meters, self-use, IBANs…). See `docs/02-data-model.md`.
- **Two financial time-axes never merge.** NK (Nebenkosten) billing = accrual/period-based. Tax =
  cash basis (§ 11 EStG — Einkommensteuergesetz, payment date). Distinct subsystems, one clean
  handoff. See `docs/02-data-model.md` §"Two time-axes".
- **Auth tokens differ per client, one flow.** Web stores the JWT in an **HttpOnly cookie**; mobile
  stores it in **secure storage** and sends it as a **Bearer** token. Access/refresh handled in one
  shared **`api.ts` interceptor**: on a 401 (HTTP Unauthorized), refresh once, replay the failed
  requests, and never double-fire. The auth hook layer is separate per platform (cookie vs secure
  storage); the API verifies the Supabase JWT the same way for both.
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
2. Meets **WCAG (Web Content Accessibility Guidelines) 2.1 level AA / BFSG
   (Barrierefreiheitsstärkungsgesetz)**: contrast, visible focus states, scalable type, keyboard nav.
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
- Follow `PLAN.md`. Milestone DoDs (Definitions of Done) are binding; **engines + fixtures before
  UI**. Before the 27.08 pitch the build order is the **execution order** in `PLAN.md` (value ÷ risk),
  not the milestone numbering — and its **hard rules** apply: no calculation without its transcribed
  spec + golden fixture, the demo path is re-verified every milestone, tag each green state, stubs
  stay stubs.
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
